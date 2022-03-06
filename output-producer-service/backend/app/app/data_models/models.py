from datetime import datetime

from pydantic import BaseModel
from typing import Optional


class StatusBase(BaseModel):
    name: str


class Status(StatusBase):
    id: str

    class Config:
        orm_mode = True


class ContentServerBase(BaseModel):
    hostname: str
    host_url: str
    name: str


class ContentServer(ContentServerBase):
    id: str

    class Config:
        orm_mode = True


class JobTypeBase(BaseModel):
    name: str
    display_name: str

# Types:
### Archive
# 1: pdf
# 2: distribution-preview
### Git
# 3: git-pdf
# 4: git-distribution-preview
class JobType(JobTypeBase):
    id: str

    class Config:
        orm_mode = True


class JobBase(BaseModel):
    collection_id: str  # Git: '{repo}/{slug}'
    status_id: str
    pdf_url: Optional[str] = None
    worker_version: Optional[str] = None
    error_message: Optional[str] = None
    content_server_id: Optional[str] = None
    version: Optional[str] = None  # Git: ref
    style: Optional[str] = None
    job_type_id: str


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    status_id: str
    pdf_url: str = None
    worker_version: Optional[str] = None
    error_message: Optional[str] = None


class Job(JobBase):
    id: str
    created_at: datetime
    updated_at: datetime
    status: Status
    content_server: Optional[ContentServer]
    job_type: JobType

    class Config:
        orm_mode = True
