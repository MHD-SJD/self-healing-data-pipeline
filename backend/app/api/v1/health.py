from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint validating database connectivity and services."""
    db_status = "HEALTHY"
    try:
        db.execute(text("SELECT 1")).scalar()
    except Exception as e:
        db_status = f"UNHEALTHY: {str(e)}"

    return {
        "status": "UP" if db_status == "HEALTHY" else "DEGRADED",
        "database": db_status,
        "service": "self-healing-data-platform-api"
    }

