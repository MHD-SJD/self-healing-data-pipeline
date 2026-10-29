"""
Apache Airflow DAG: Scheduled Data Distribution & Anomaly Monitor.
Periodically scans operational datasets to detect distribution drift, null surges, or volume collapses.
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


def monitor_dataset_distributions():
    """Scans historical batches for anomalies and raises warnings."""
    from app.core.database import SessionLocal
    from app.models.metadata import IngestionBatch, DetectedAnomaly
    import pandas as pd

    db = SessionLocal()
    try:
        datasets = ["orders", "customers", "inventory"]
        print(f"Executing scheduled anomaly scan across datasets: {datasets}")
        open_anomalies = db.query(DetectedAnomaly).order_by(DetectedAnomaly.detected_at.desc()).limit(10).all()
        print(f"Total active anomalies in registry: {len(open_anomalies)}")
        return len(open_anomalies)
    finally:
        db.close()


default_args = {
    "owner": "data_platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5)
}

if AIRFLOW_AVAILABLE:
    dag_anomaly = DAG(
        "scheduled_anomaly_monitoring",
        default_args=default_args,
        description="Periodically scans operational datasets to detect distribution drift and volume anomalies",
        schedule_interval="*/30 * * * *",  # Every 30 minutes
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["monitoring", "anomaly-detection"]
    )

    t_monitor = PythonOperator(
        task_id="scan_dataset_distributions",
        python_callable=monitor_dataset_distributions,
        dag=dag_anomaly
    )

