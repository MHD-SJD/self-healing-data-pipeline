from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from app.models.metadata import IngestionBatch, DetectedAnomaly


class StatisticalProfileMonitor:
    """Monitors statistical distributions and flags deviations against historical baselines."""

    @staticmethod
    def calculate_numeric_stats(series: pd.Series) -> Dict[str, float]:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric) == 0:
            return {"count": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        return {
            "count": float(len(numeric)),
            "mean": float(np.mean(numeric)),
            "std": float(np.std(numeric)),
            "min": float(np.min(numeric)),
            "max": float(np.max(numeric)),
            "q25": float(np.percentile(numeric, 25)),
            "q75": float(np.percentile(numeric, 75))
        }

    @staticmethod
    def detect_volume_anomaly(
        db: Session,
        dataset_name: str,
        current_rows: int,
        z_threshold: float = 3.0
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates baseline row count across previous batches and checks if current batch is an outlier.
        """
        recent_batches = db.query(IngestionBatch.input_rows).filter(
            IngestionBatch.dataset_name == dataset_name,
            IngestionBatch.status == "INGESTED",
            IngestionBatch.input_rows > 0
        ).order_by(IngestionBatch.completed_at.desc()).limit(30).all()

        counts = [b[0] for b in recent_batches if b[0] is not None]
        if len(counts) < 3:
            # Not enough historical baseline data yet
            return None

        mean = float(np.mean(counts))
        std = float(np.std(counts))
        if std == 0.0:
            std = 1.0  # Avoid division by zero

        z_score = (current_rows - mean) / std

        if abs(z_score) >= z_threshold:
            anomaly_type = "VOLUME_SPIKE" if z_score > 0 else "VOLUME_DROP"
            return {
                "metric_name": "row_count",
                "observed_metric": float(current_rows),
                "baseline_mean": round(mean, 2),
                "baseline_stddev": round(std, 2),
                "z_score": round(z_score, 2),
                "anomaly_type": anomaly_type,
                "severity": "CRITICAL" if abs(z_score) > 4.5 else "WARNING"
            }
        return None

    @staticmethod
    def detect_numeric_metric_anomaly(
        df: pd.DataFrame,
        column: str,
        expected_mean_range: Optional[Tuple[float, float]] = None,
        z_threshold: float = 3.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detects anomalies in continuous numeric metrics (e.g. order amount, product price).
        """
        if column not in df.columns:
            return None

        stats = StatisticalProfileMonitor.calculate_numeric_stats(df[column])
        if stats["count"] < 10:
            return None

        mean = stats["mean"]
        # If expected range provided:
        if expected_mean_range:
            min_mean, max_mean = expected_mean_range
            if mean < min_mean or mean > max_mean:
                return {
                    "metric_name": f"{column}_mean",
                    "observed_metric": round(mean, 2),
                    "baseline_mean": (min_mean + max_mean) / 2.0,
                    "baseline_stddev": 1.0,
                    "z_score": round(abs(mean - (min_mean + max_mean) / 2.0), 2),
                    "anomaly_type": "OUTLIER_MEAN",
                    "severity": "WARNING"
                }

        return None

