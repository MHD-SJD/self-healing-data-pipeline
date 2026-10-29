#!/usr/bin/env python3
"""
Synthetic Data Generator for Self-Healing Data Pipeline Platform.
Generates realistic, clean base datasets for:
1. Customers (500 records)
2. Products / Inventory (100 records)
3. Orders (1000 records)

Supports reproducible seed for deterministic testing.
"""

import os
import random
import csv
from datetime import datetime, timedelta
from pathlib import Path

# Fix random seed for determinism
random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James",
    "Isabella", "Oliver", "Mia", "Benjamin", "Charlotte", "Elijah", "Amelia",
    "Lucas", "Harper", "Mason", "Evelyn", "Logan", "Alexander", "Emily", "Daniel"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson",
    "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez"
]

COUNTRIES = ["US", "CA", "GB", "DE", "FR", "AU", "JP", "NL", "SE", "CH"]

CATEGORIES = [
    "Electronics", "Home & Kitchen", "Books", "Clothing", "Sports & Outdoors",
    "Health & Personal Care", "Toys & Games", "Automotive", "Garden"
]

WAREHOUSES = ["WH-EAST-1", "WH-WEST-1", "WH-CENTRAL-1", "WH-EU-NORTH", "WH-APAC-1"]

ORDER_STATUSES = ["COMPLETED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]


def generate_customers(count: int = 500) -> list[dict]:
    customers = []
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        cid = f"CUST-{i:05d}"
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        days_offset = random.randint(0, 700)
        signup = (base_date + timedelta(days=days_offset)).strftime("%Y-%m-%d %H:%M:%S")
        country = random.choice(COUNTRIES)
        phone = f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        
        customers.append({
            "customer_id": cid,
            "email": email,
            "first_name": fn,
            "last_name": ln,
            "signup_date": signup,
            "country": country,
            "phone": phone
        })
    return customers


def generate_inventory(count: int = 100) -> list[dict]:
    products = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(1, count + 1):
        pid = f"PROD-{i:04d}"
        cat = random.choice(CATEGORIES)
        sku = f"SKU-{cat[:3].upper()}-{i:04d}"
        name = f"{cat[:-1] if cat.endswith('s') else cat} Model {chr(65 + (i % 26))}{i}"
        price = round(random.uniform(9.99, 499.99), 2)
        stock = random.randint(10, 500)
        wh = random.choice(WAREHOUSES)
        restock = (base_date + timedelta(days=random.randint(0, 300))).strftime("%Y-%m-%d %H:%M:%S")
        
        products.append({
            "product_id": pid,
            "sku": sku,
            "product_name": name,
            "category": cat,
            "unit_price": price,
            "stock_quantity": stock,
            "warehouse_code": wh,
            "last_restocked_at": restock
        })
    return products


def generate_orders(customers: list[dict], products: list[dict], count: int = 1000) -> list[dict]:
    orders = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(1, count + 1):
        oid = f"ORD-{i:06d}"
        cust = random.choice(customers)
        prod = random.choice(products)
        qty = random.randint(1, 4)
        amount = round(prod["unit_price"] * qty, 2)
        order_date = (base_date + timedelta(days=random.randint(0, 300), hours=random.randint(0, 23))).strftime("%Y-%m-%d %H:%M:%S")
        status = random.choices(ORDER_STATUSES, weights=[0.6, 0.15, 0.15, 0.05, 0.05])[0]
        addr = f"{random.randint(100, 999)} Main St, Cityville, {cust['country']}"
        
        orders.append({
            "order_id": oid,
            "customer_id": cust["customer_id"],
            "product_id": prod["product_id"],
            "order_date": order_date,
            "amount": amount,
            "status": status,
            "shipping_address": addr
        })
    return orders


def write_csv(data: list[dict], filename: str) -> Path:
    filepath = DATA_DIR / filename
    if not data:
        return filepath
    fieldnames = list(data[0].keys())
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"Generated {len(data)} records -> {filepath}")
    return filepath


def main():
    print("Generating clean synthetic datasets for Self-Healing Platform...")
    customers = generate_customers(500)
    inventory = generate_inventory(100)
    orders = generate_orders(customers, inventory, 1000)
    
    write_csv(customers, "customers.csv")
    write_csv(inventory, "inventory.csv")
    write_csv(orders, "orders.csv")
    print("Synthetic data generation complete!")


if __name__ == "__main__":
    main()

