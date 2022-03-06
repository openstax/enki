from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.service.jobs import jobs_service
from app.data_models.models import JobCreate, JobUpdate, Job
from app.db.utils import get_db

router = APIRouter()


@router.get("/", response_model=List[Job])
def list_jobs(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 50,
):
    """List jobs - page 0"""
    return list_job_page(db, 0, limit)


@router.get("/pages/{page}", response_model=List[Job])
def list_job_page(
        db: Session = Depends(get_db),
        page: int = 0,
        limit: int = 50,
):
    """List jobs by page"""
    skip = page * limit
    order_by = jobs_service.schema_model.created_at.desc()
    jobs = jobs_service.get_items_order_by(db,
                                           skip=skip,
                                           limit=limit,
                                           order_by=[order_by])
    return jobs


@router.get("/{id}", response_model=Job)
def get_job(
        *,
        db: Session = Depends(get_db),
        id: int
):
    """Get a single job"""
    job = jobs_service.get(db, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/", response_model=Job)
def create_job(
        *,
        db: Session = Depends(get_db),
        job_in: JobCreate
):
    """Create new job"""
    job = jobs_service.create(db, job_in)
    return job


@router.put("/{id}", response_model=Job)
def update_job(
        *,
        db: Session = Depends(get_db),
        id: int,
        job_in: JobUpdate
):
    """Update an existing job"""
    job = jobs_service.get(db_session=db, obj_id=id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # If current job status is completed state
    if int(job.status_id) in [4,5,6]:
        # Pipelines will try to override an completed state with
        # assigned, processing status if unlucky
        # Only allow updating to completed states to prevent this
        # Don't raise HTTPException since other fields are likely valid
        incoming_status = int(job_in.status_id)
        job_in.status_id = incoming_status if incoming_status in [4,5,6] else job.status_id
    job = jobs_service.update(db, job, job_in)
    return job
