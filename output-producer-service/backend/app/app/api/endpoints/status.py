from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data_models.models import Status
from app.db.utils import get_db
from app.service.status import status_service

router = APIRouter()


@router.get("/", response_model=List[Status])
def list_status(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
):
    statuses = status_service.get_items(db, skip=skip, limit=limit)
    return statuses
