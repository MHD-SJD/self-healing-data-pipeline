#!/usr/bin/env python3
"""
Seed Initial Pipeline Definitions, Schemas, Quality Rules, and Recovery Policies.
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.metadata import (
    Pipeline, DatasetSchema, DataQualityRule, RecoveryPolicy
)


def seed():
    session = SessionLocal()
    try:
        print("Seeding initial platform metadata...")

        # 1. Pipelines
        pipelines = [
            Pipeline(
                pipeline_id="e_commerce_orders_pipeline",
                name="E-Commerce Orders Pipeline",
                description="Ingests, validates, heals, and models customer orders",
                schedule_interval="@hourly",
                is_active=True
            ),
            Pipeline(
                pipeline_id="customers_pipeline",
                name="Customer Master Pipeline",
                description="Ingests, validates, and models customer records",
                schedule_interval="@daily",
                is_active=True
            ),
            Pipeline(
                pipeline_id="inventory_pipeline",
                name="Product Inventory Pipeline",
                description="Ingests, validates, and tracks product catalog & stock levels",
                schedule_interval="@hourly",
                is_active=True
            ),
        ]
        for p in pipelines:
            session.merge(p)

        # 2. Dataset Schemas (v1)
        schemas = [
            DatasetSchema(
                dataset_name="customers",
                version=1,
                schema_definition={
                    "columns": {
                        "customer_id": {"type": "string", "nullable": False, "primary_key": True},
                        "email": {"type": "string", "nullable": False},
                        "first_name": {"type": "string", "nullable": True},
                        "last_name": {"type": "string", "nullable": True},
                        "signup_date": {"type": "timestamp", "nullable": False},
                        "country": {"type": "string", "nullable": True},
                        "phone": {"type": "string", "nullable": True}
                    },
                    "allow_additive_columns": True
                },
                is_active=True
            ),
            DatasetSchema(
                dataset_name="inventory",
                version=1,
                schema_definition={
                    "columns": {
                        "product_id": {"type": "string", "nullable": False, "primary_key": True},
                        "sku": {"type": "string", "nullable": False},
                        "product_name": {"type": "string", "nullable": False},
                        "category": {"type": "string", "nullable": True},
                        "unit_price": {"type": "numeric", "nullable": False},
                        "stock_quantity": {"type": "integer", "nullable": False},
                        "warehouse_code": {"type": "string", "nullable": True},
                        "last_restocked_at": {"type": "timestamp", "nullable": True}
                    },
                    "allow_additive_columns": True
                },
                is_active=True
            ),
            DatasetSchema(
                dataset_name="orders",
                version=1,
                schema_definition={
                    "columns": {
                        "order_id": {"type": "string", "nullable": False, "primary_key": True},
                        "customer_id": {"type": "string", "nullable": False},
                        "product_id": {"type": "string", "nullable": False},
                        "order_date": {"type": "timestamp", "nullable": False},
                        "amount": {"type": "numeric", "nullable": False},
                        "status": {"type": "string", "nullable": False},
                        "shipping_address": {"type": "string", "nullable": True}
                    },
                    "allow_additive_columns": True
                },
                is_active=True
            ),
        ]
        for s in schemas:
            # Query existing schema to avoid conflict
            existing = session.query(DatasetSchema).filter_by(
                dataset_name=s.dataset_name, version=s.version
            ).first()
            if not existing:
                session.add(s)

        # 3. Data Quality Rules
        rules = [
            # Customers Rules
            DataQualityRule(
                rule_id="cust_req_id",
                dataset_name="customers",
                rule_type="completeness",
                column_name="customer_id",
                parameters={"max_null_pct": 0.0},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="cust_unique_id",
                dataset_name="customers",
                rule_type="uniqueness",
                column_name="customer_id",
                parameters={"allow_duplicates": False},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="cust_email_valid",
                dataset_name="customers",
                rule_type="validity",
                column_name="email",
                parameters={"regex": r"^[\w\.-]+@[\w\.-]+\.\w+$"},
                severity="ERROR"
            ),
            DataQualityRule(
                rule_id="cust_schema_contract",
                dataset_name="customers",
                rule_type="schema",
                column_name=None,
                parameters={"strict_types": True, "allow_additive": True},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="cust_volume_anomaly",
                dataset_name="customers",
                rule_type="distribution",
                column_name=None,
                parameters={"metric": "row_count", "z_threshold": 3.0, "min_rows": 10},
                severity="WARNING"
            ),

            # Inventory Rules
            DataQualityRule(
                rule_id="inv_req_id",
                dataset_name="inventory",
                rule_type="completeness",
                column_name="product_id",
                parameters={"max_null_pct": 0.0},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="inv_unique_sku",
                dataset_name="inventory",
                rule_type="uniqueness",
                column_name="sku",
                parameters={"allow_duplicates": False},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="inv_pos_price",
                dataset_name="inventory",
                rule_type="validity",
                column_name="unit_price",
                parameters={"min_value": 0.01},
                severity="ERROR"
            ),
            DataQualityRule(
                rule_id="inv_pos_stock",
                dataset_name="inventory",
                rule_type="validity",
                column_name="stock_quantity",
                parameters={"min_value": 0},
                severity="ERROR"
            ),

            # Orders Rules
            DataQualityRule(
                rule_id="ord_req_id",
                dataset_name="orders",
                rule_type="completeness",
                column_name="order_id",
                parameters={"max_null_pct": 0.0},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="ord_req_cust",
                dataset_name="orders",
                rule_type="completeness",
                column_name="customer_id",
                parameters={"max_null_pct": 0.0},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="ord_unique_id",
                dataset_name="orders",
                rule_type="uniqueness",
                column_name="order_id",
                parameters={"allow_duplicates": False},
                severity="CRITICAL"
            ),
            DataQualityRule(
                rule_id="ord_pos_amount",
                dataset_name="orders",
                rule_type="validity",
                column_name="amount",
                parameters={"min_value": 0.01},
                severity="ERROR"
            ),
            DataQualityRule(
                rule_id="ord_valid_status",
                dataset_name="orders",
                rule_type="validity",
                column_name="status",
                parameters={"allowed_values": ["COMPLETED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]},
                severity="WARNING"
            ),
            DataQualityRule(
                rule_id="ord_amount_anomaly",
                dataset_name="orders",
                rule_type="distribution",
                column_name="amount",
                parameters={"metric": "mean", "z_threshold": 3.0},
                severity="WARNING"
            )
        ]
        for r in rules:
            session.merge(r)

        # 4. Recovery Policies
        policies = [
            RecoveryPolicy(
                policy_id="POL-MISSING-01",
                failure_category="MISSING_DATA",
                safety_level="AUTOMATIC",
                max_retries=3,
                auto_apply=True,
                preconditions={"has_quarantine_target": True},
                action_config={"strategy": "quarantine_missing_keys", "allow_null_fill": False}
            ),
            RecoveryPolicy(
                policy_id="POL-DUP-01",
                failure_category="DUPLICATE_DATA",
                safety_level="AUTOMATIC",
                max_retries=2,
                auto_apply=True,
                preconditions={"has_primary_key": True},
                action_config={"strategy": "deduplicate_latest_record", "preserve_raw": True}
            ),
            RecoveryPolicy(
                policy_id="POL-DRIFT-01",
                failure_category="SCHEMA_DRIFT",
                safety_level="AUTOMATIC",
                max_retries=1,
                auto_apply=True,
                preconditions={"is_additive_only": True},
                action_config={"strategy": "adopt_additive_columns", "bump_schema_version": True}
            ),
            RecoveryPolicy(
                policy_id="POL-DRIFT-BREAKING",
                failure_category="SCHEMA_DRIFT",
                safety_level="REQUIRES_APPROVAL",
                max_retries=1,
                auto_apply=False,
                preconditions={"is_additive_only": False},
                action_config={"strategy": "quarantine_batch_require_approval"}
            ),
            RecoveryPolicy(
                policy_id="POL-INVALID-01",
                failure_category="INVALID_RECORDS",
                safety_level="AUTOMATIC",
                max_retries=2,
                auto_apply=True,
                preconditions={"quarantine_allowed": True},
                action_config={"strategy": "quarantine_invalid_rows", "forward_valid_subset": True}
            ),
            RecoveryPolicy(
                policy_id="POL-ANOMALY-01",
                failure_category="DISTRIBUTION_ANOMALY",
                safety_level="REQUIRES_APPROVAL",
                max_retries=1,
                auto_apply=False,
                preconditions={"baseline_available": True},
                action_config={"strategy": "pause_downstream_require_approval"}
            ),
            RecoveryPolicy(
                policy_id="POL-INGEST-01",
                failure_category="INGESTION_FAILURE",
                safety_level="AUTOMATIC",
                max_retries=3,
                auto_apply=True,
                preconditions={"is_transient": True},
                action_config={"strategy": "exponential_backoff_retry", "initial_backoff_sec": 2}
            ),
            RecoveryPolicy(
                policy_id="POL-TRANSFORM-01",
                failure_category="TRANSFORMATION_FAILURE",
                safety_level="MANUAL_ONLY",
                max_retries=1,
                auto_apply=False,
                preconditions={},
                action_config={"strategy": "halt_and_preserve_logs"}
            )
        ]
        for pol in policies:
            session.merge(pol)

        session.commit()
        print("Metadata seeding successfully completed!")
    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()

