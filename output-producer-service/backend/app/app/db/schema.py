from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ContentServers(Base):
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    hostname = sa.Column(sa.String, nullable=False)
    host_url = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    jobs = relationship("Jobs", back_populates="content_server")

class JobTypes(Base):
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, nullable=False)
    display_name = sa.Column(sa.String, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    jobs = relationship("Jobs", back_populates="job_type")


class Jobs(Base):
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    collection_id = sa.Column(sa.String, index=True)
    status_id = sa.Column(sa.Integer, sa.ForeignKey("status.id"), default=1)
    pdf_url = sa.Column(sa.String)
    version = sa.Column(sa.String)
    style = sa.Column(sa.String)
    job_type_id = sa.Column(sa.Integer, sa.ForeignKey("job_types.id"))
    worker_version = sa.Column(sa.String)
    content_server_id = sa.Column(sa.Integer, sa.ForeignKey("content_servers.id"))
    error_message = sa.Column(sa.String)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    status = relationship("Status", back_populates="jobs", lazy="joined")
    content_server = relationship("ContentServers", back_populates="jobs", lazy="joined")
    job_type = relationship("JobTypes", back_populates="jobs", lazy="joined")


class Status(Base):
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow, index=True)

    jobs = relationship("Jobs", back_populates="status")
