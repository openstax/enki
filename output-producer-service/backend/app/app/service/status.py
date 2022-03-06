from app.db.schema import Status as StatusSchema
from app.data_models.models import Status as StatusModel
from app.service.base import ServiceBase


class StatusService(ServiceBase):
    pass


status_service = StatusService(StatusSchema, StatusModel)
