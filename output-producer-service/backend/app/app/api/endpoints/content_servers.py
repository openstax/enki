from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data_models.models import ContentServer
from app.db.utils import get_db
from app.service.content_servers import content_server_service

router = APIRouter()


@router.get("/", response_model=List[ContentServer])
def list_content_servers(
        *,
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
):
    """List all content servers"""
    content_servers = content_server_service.get_items(db,
                                                       skip=skip,
                                                       limit=limit)
    return content_servers
