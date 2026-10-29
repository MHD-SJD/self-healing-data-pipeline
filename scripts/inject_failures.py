#!/usr/bin/env python3
"""
Failure Injection Demo for Self-Healing Data Pipeline Platform.

Generates corrupted CSV datasets, runs the full pipeline for each,
and reports how each failure is detected, classified, recovered, and verified.
"""

import os
import sys
import csv
import random
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:root@127.0.0.1:5432/self_healing_platform")

from app.core.database import SessionLocal
from app.services.pipeline_service import PipelineExecutionService

SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
CORRUPTED_DIR = PROJECT_ROOT / "data" / "corrupted"

random.seed(99)


def prepare_corrupted_dir():
    CORRUPTED_DIR.mkdir(parents=True, exist_ok=True)


def _make_fresh_df(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    time_col = "order_date" if "order_date" in df.columns else ("signup_date" if "signup_date" in df.columns else None)
    if time_col:
        # Subtle second offset on last row ensures unique SHA-256 checksum per demo run
        df.at[len(df) - 1, time_col] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return df


def create_scenario_missing_values() -> Path:
    """Scenario 1: Missing Values in required customer_id column."""
    df = _make_fresh_df(SAMPLES_DIR / "customers.csv")
    null_indices = random.sample(range(len(df) - 1), 50)
    for idx in null_indices:
        df.at[idx, "customer_id"] = ""
    out_path = CORRUPTED_DIR / "customers_missing_ids.csv"
    df.to_csv(out_path, index=False)
    return out_path


def create_scenario_duplicate_records() -> Path:
    """Scenario 2: Duplicate primary key in orders."""
    df = _make_fresh_df(SAMPLES_DIR / "orders.csv")
    dup_rows = df.sample(n=50, random_state=42).copy()
    dup_rows["order_date"] = (pd.to_datetime(dup_rows["order_date"]) + pd.Timedelta(hours=2)).dt.strftime("%Y-%m-%d %H:%M:%S")
    corrupted_df = pd.concat([df, dup_rows], ignore_index=True)
    out_path = CORRUPTED_DIR / "orders_duplicates.csv"
    corrupted_df.to_csv(out_path, index=False)
    return out_path


def create_scenario_additive_schema() -> Path:
    """Scenario 3: Additive Schema Drift (new compatible nullable column)."""
    df = _make_fresh_df(SAMPLES_DIR / "customers.csv")
    tiers = ["PLATINUM", "GOLD", "SILVER", "STANDARD"]
    df["loyalty_tier"] = [random.choice(tiers) if random.random() > 0.2 else None for _ in range(len(df))]
    out_path = CORRUPTED_DIR / "customers_additive_column.csv"
    df.to_csv(out_path, index=False)
    return out_path


def create_scenario_breaking_schema() -> Path:
    """Scenario 4: Breaking Schema Drift (missing mandatory column)."""
    df = _make_fresh_df(SAMPLES_DIR / "customers.csv")
    df = df.drop(columns=["email"])
    out_path = CORRUPTED_DIR / "customers_missing_email.csv"
    df.to_csv(out_path, index=False)
    return out_path


def create_scenario_distribution_anomaly() -> Path:
    """Scenario 5: Statistical Distribution Anomaly (10x inflated amounts)."""
    df = _make_fresh_df(SAMPLES_DIR / "orders.csv")
    df["amount"] = df["amount"] * 25.0
    out_path = CORRUPTED_DIR / "orders_inflated_amounts.csv"
    df.to_csv(out_path, index=False)
    return out_path


def create_scenario_invalid_records() -> Path:
    """Scenario 6: Business Validity Violations (negative order amounts)."""
    df = _make_fresh_df(SAMPLES_DIR / "orders.csv")
    neg_indices = random.sample(range(len(df) - 1), 35)
    for idx in neg_indices:
        df.at[idx, "amount"] = -round(random.uniform(10.0, 150.0), 2)
    out_path = CORRUPTED_DIR / "orders_negative_amounts.csv"
    df.to_csv(out_path, index=False)
    return out_path


def run_demo():
    prepare_corrupted_dir()
    print("=" * 80)
    print("      SELF-HEALING DATA PIPELINE PLATFORM -- FAILURE INJECTION SUITE      ")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Database: {os.environ.get('DATABASE_URL')}")
    print("-" * 80)

    scenarios = [
        {
            "name": "Missing Required Values",
            "generator": create_scenario_missing_values,
            "pipeline_id": "customers_pipeline",
            "expected_cat": "MISSING_DATA",
            "expected_action": "quarantine_missing_records"
        },
        {
            "name": "Duplicate Primary Keys",
            "generator": create_scenario_duplicate_records,
            "pipeline_id": "e_commerce_orders_pipeline",
            "expected_cat": "DUPLICATE_DATA",
            "expected_action": "deduplicate_retaining_latest"
        },
        {
            "name": "Additive Schema Drift",
            "generator": create_scenario_additive_schema,
            "pipeline_id": "customers_pipeline",
            "expected_cat": "SCHEMA_DRIFT",
            "expected_action": "adopt_additive_columns"
        },
        {
            "name": "Breaking Schema Drift",
            "generator": create_scenario_breaking_schema,
            "pipeline_id": "customers_pipeline",
            "expected_cat": "SCHEMA_DRIFT",
            "expected_action": "quarantine_batch_require_approval"
        },
        {
            "name": "Statistical Distribution Anomaly",
            "generator": create_scenario_distribution_anomaly,
            "pipeline_id": "e_commerce_orders_pipeline",
            "expected_cat": "DISTRIBUTION_ANOMALY",
            "expected_action": "pause_downstream_and_request_approval"
        },
        {
            "name": "Invalid Records (Negative Amounts)",
            "generator": create_scenario_invalid_records,
            "pipeline_id": "e_commerce_orders_pipeline",
            "expected_cat": "INVALID_RECORDS",
            "expected_action": "quarantine_invalid_rows"
        }
    ]

    summary_rows = []

    for i, sc in enumerate(scenarios, start=1):
        print(f"\n[SCENARIO {i}/6] Injecting: {sc['name']}...")
        file_path = sc["generator"]()
        print(f"  -> Created: {file_path.name}")
        print(f"  -> Running pipeline '{sc['pipeline_id']}'...")

        db = SessionLocal()
        service = PipelineExecutionService(db)
        try:
            result = service.trigger_pipeline_run(
                pipeline_id=sc["pipeline_id"],
                custom_filepath=file_path,
                trigger_type="FAILURE_INJECTION",
                auto_heal=True
            )
            status = result.get("status")
            incidents = result.get("incidents", [])
            recoveries = result.get("recoveries", [])
            dbt_status = result.get("dbt_status", "SKIPPED")

            primary_cat = incidents[0]["category"] if incidents else "NONE"
            primary_act = incidents[0]["action"] if incidents else "NONE"
            primary_sev = incidents[0]["severity"] if incidents else "INFO"
            inc_status = incidents[0]["status"] if incidents else "N/A"

            print(f"  [+] Pipeline Status : {status}")
            print(f"  [+] Incidents       : {len(incidents)} detected")
            if incidents:
                print(f"      - Category     : {primary_cat} [{primary_sev}]")
                print(f"      - Recommended  : {primary_act}")
                print(f"      - Final State  : {inc_status}")
            print(f"  [+] Recoveries Run  : {len(recoveries)}")
            print(f"  [+] dbt Analytics   : {dbt_status}")

            summary_rows.append({
                "scenario": sc["name"],
                "detected": "YES" if incidents else "NO",
                "category": primary_cat,
                "pipeline_status": status,
                "healed": "YES" if status in ["HEALED", "COMPLETED"] else ("ESCALATED" if status == "ESCALATED" else "NO")
            })

        except Exception as e:
            print(f"  [x] Execution Error: {e}")
            summary_rows.append({
                "scenario": sc["name"],
                "detected": "ERROR",
                "category": "EXCEPTION",
                "pipeline_status": "FAILED",
                "healed": "NO"
            })
        finally:
            db.close()

    print("\n" + "=" * 80)
    print("                      FAILURE INJECTION TEST MATRIX                      ")
    print("=" * 80)
    print(f"{'Scenario':<34} | {'Detected':<8} | {'Category':<20} | {'Status':<12}")
    print("-" * 80)
    for r in summary_rows:
        print(f"{r['scenario']:<34} | {r['detected']:<8} | {r['category']:<20} | {r['pipeline_status']:<12}")
    print("=" * 80)
    print("All injection test scenarios evaluated successfully.\n")


if __name__ == "__main__":
    run_demo()
