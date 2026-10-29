import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logging import logger
from app.models.metadata import IngestionBatch, PipelineRun


class BaseIngester(ABC):
    def __init__(self, db: Session, dataset_name: str, target_raw_table: str):
        self.db = db
        self.dataset_name = dataset_name
        self.target_raw_table = target_raw_table

    @staticmethod
    def calculate_file_checksum(filepath: Path) -> str:
        """Computes SHA-256 hash of the input file to ensure idempotence."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def check_idempotency(self, token: str) -> Optional[IngestionBatch]:
        """Checks if this token was already successfully processed."""
        return self.db.query(IngestionBatch).filter(
            IngestionBatch.idempotency_token == token,
            IngestionBatch.status == "INGESTED"
        ).first()

    def ingest(
        self,
        file_path: Path,
        run_id: uuid.UUID,
        idempotency_token: Optional[str] = None
    ) -> Tuple[IngestionBatch, pd.DataFrame]:
        """
        Idempotent ingestion pipeline for a dataset file.
        Returns the registered IngestionBatch metadata and the ingested DataFrame.
        """
        logger.info(f"Starting ingestion for dataset='{self.dataset_name}' from '{file_path}'")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        checksum = self.calculate_file_checksum(file_path)
        token = idempotency_token or f"{self.dataset_name}_{checksum}"

        # 1. Idempotency Check
        existing_batch = self.db.query(IngestionBatch).filter(
            IngestionBatch.idempotency_token == token
        ).first()

        if existing_batch and existing_batch.status == "INGESTED":
            logger.warning(
                f"Batch with token '{token}' has already been ingested (Batch ID: {existing_batch.batch_id}). Skipping."
            )
            df = self.load_raw_data_by_batch(existing_batch.batch_id)
            return existing_batch, df
        elif existing_batch:
            logger.info(f"Reusing existing failed/pending batch {existing_batch.batch_id} for token '{token}'")
            batch = existing_batch
            batch.run_id = run_id
            batch.status = "PENDING"
            batch.started_at = datetime.utcnow()
        else:
            batch = IngestionBatch(
                run_id=run_id,
                dataset_name=self.dataset_name,
                source_path=str(file_path),
                idempotency_token=token,
                checksum=checksum,
                status="PENDING",
                started_at=datetime.utcnow()
            )
            self.db.add(batch)
            self.db.flush()

        try:
            # 3. Read Source Data
            df = self.read_source(file_path)
            batch.input_rows = len(df)

            # 4. Write to raw PostgreSQL schema
            df_to_insert = df.copy()
            df_to_insert["_batch_id"] = str(batch.batch_id)
            df_to_insert["_ingested_at"] = datetime.utcnow()

            self.write_to_raw_storage(df_to_insert, batch.batch_id)

            batch.processed_rows = len(df)
            batch.status = "INGESTED"
            batch.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(
                f"Ingestion successful for batch {batch.batch_id}: {batch.processed_rows} rows inserted into {self.target_raw_table}"
            )
            return batch, df

        except Exception as e:
            self.db.rollback()
            batch.status = "FAILED"
            batch.completed_at = datetime.utcnow()
            self.db.add(batch)
            self.db.commit()
            logger.error(f"Ingestion failed for {self.dataset_name}: {str(e)}", exc_info=True)
            raise e

    def read_source(self, file_path: Path) -> pd.DataFrame:
        """Reads CSV file handling malformed lines safely."""
        try:
            return pd.read_csv(file_path, dtype=str, on_bad_lines="skip")
        except Exception as e:
            raise ValueError(f"Malformed or unreadable file {file_path}: {e}")

    def write_to_raw_storage(self, df: pd.DataFrame, batch_id: uuid.UUID):
        """Appends raw data to PostgreSQL table."""
        # Clean column names to lowercase and replace spaces
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        
        # Check existing columns in the target table to handle any unexpected columns
        cols_query = text(
            f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'raw_data' AND table_name = '{self.target_raw_table}'"
        )
        result = self.db.execute(cols_query).fetchall()
        existing_cols = {row[0] for row in result}

        # Handle additive columns dynamically if needed in raw schema
        for col in df.columns:
            if col not in existing_cols:
                logger.info(f"Adding new column '{col}' to raw_data.{self.target_raw_table}")
                alter_sql = text(f'ALTER TABLE raw_data.{self.target_raw_table} ADD COLUMN IF NOT EXISTS "{col}" TEXT')
                self.db.execute(alter_sql)
                existing_cols.add(col)

        self.db.commit()

        # Write data to PostgreSQL using pandas to_sql with the engine
        df.to_sql(
            name=self.target_raw_table,
            con=self.db.bind,
            schema="raw_data",
            if_exists="append",
            index=False,
            chunksize=500
        )

    def load_raw_data_by_batch(self, batch_id: uuid.UUID) -> pd.DataFrame:
        """Retrieves raw data for a specific batch ID."""
        query = text(f"SELECT * FROM raw_data.{self.target_raw_table} WHERE _batch_id = :batch_id")
        with self.db.bind.connect() as conn:
            return pd.read_sql(query, con=conn, params={"batch_id": str(batch_id)})
