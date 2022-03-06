from app.db.schema import Jobs as JobSchema
from app.data_models.models import Job as JobModel
from app.service.base import ServiceBase


class JobsService(ServiceBase):
    """If specific methods need to be overridden they can be done here.
    """
    pass


jobs_service = JobsService(JobSchema, JobModel)
