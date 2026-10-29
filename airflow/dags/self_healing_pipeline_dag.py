"""
Apache Airflow DAG: Self-Healing Data Pipeline Orchestrator.
Orchestrates: Ingestion -> Quality Checks -> Incident Classification -> Recovery -> dbt Transforms -> Post-Verification
"""

from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add backend to path for Airflow execution
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


def execute_pipeline_stage(pipeline_id: str):
    """Executes a specific pipeline stage via PipelineExecutionService."""
    from app.core.database import SessionLocal
    from app.services.pipeline_service import PipelineExecutionService
    
    db = SessionLocal()
    try:
        service = PipelineExecutionService(db)
        result = service.trigger_pipeline_run(pipeline_id=pipeline_id, trigger_type="SCHEDULED", auto_heal=True)
        print(f"Executed stage {pipeline_id}: Status={result.get('status')}")
        if result.get("status") in ["FAILED", "ESCALATED"]:
            raise RuntimeError(f"Pipeline stage {pipeline_id} ended with status {result.get('status')}")
        return result
    finally:
        db.close()


def run_customers():
    return execute_pipeline_stage("customers_pipeline")


def run_inventory():
    return execute_pipeline_stage("inventory_pipeline")


def run_orders():
    return execute_pipeline_stage("e_commerce_orders_pipeline")


def run_marts_transformation():
    """Runs dbt marts transformations."""
    from app.core.database import SessionLocal
    from app.services.pipeline_service import PipelineExecutionService

    db = SessionLocal()
    try:
        service = PipelineExecutionService(db)
        result = service.run_dbt_transformations(select_model="marts")
        print(f"dbt marts transformation result: {result}")
        return result
    finally:
        db.close()


default_args = {
    "owner": "data_platform",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=15)
}

if AIRFLOW_AVAILABLE:
    dag = DAG(
        "self_healing_data_pipeline",
        default_args=default_args,
        description="End-to-end self-healing data pipeline with quality gates and automated recovery",
        schedule_interval="0 * * * *",  # Hourly
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["production", "self-healing", "dbt", "quality-gate"]
    )

    t_customers = PythonOperator(
        task_id="ingest_and_heal_customers",
        python_callable=run_customers,
        dag=dag
    )

    t_inventory = PythonOperator(
        task_id="ingest_and_heal_inventory",
        python_callable=run_inventory,
        dag=dag
    )

    t_orders = PythonOperator(
        task_id="ingest_and_heal_orders",
        python_callable=run_orders,
        dag=dag
    )

    t_dbt_marts = PythonOperator(
        task_id="materialize_dbt_marts",
        python_callable=run_marts_transformation,
        dag=dag
    )

    # Ingest customers & inventory first, then orders (which depends on customer & product IDs), then marts
    [t_customers, t_inventory] >> t_orders >> t_dbt_marts

