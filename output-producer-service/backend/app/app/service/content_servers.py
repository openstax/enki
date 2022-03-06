from app.db.schema import ContentServers as ContentServerSchema
from app.data_models.models import ContentServer as ContentServerModel
from app.service.base import ServiceBase


class ContentServerService(ServiceBase):
    pass


content_server_service = ContentServerService(ContentServerSchema,
                                              ContentServerModel)
