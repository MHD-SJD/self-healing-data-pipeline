from sqlalchemy.orm import Session
from app.ingestion.base import BaseIngester


class OrdersIngester(BaseIngester):
    def __init__(self, db: Session):
        super().__init__(db=db, dataset_name="orders", target_raw_table="raw_orders")

