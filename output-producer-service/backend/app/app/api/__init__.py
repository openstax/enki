from fastapi import APIRouter

from app.api.endpoints import (content_servers,
                               jobs,
                               ping,
                               status,
                               version)

api_router = APIRouter()
api_router.include_router(ping.router, prefix="/ping", tags=["ping"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(content_servers.router, prefix="/content-servers",
                          tags=["content_servers"])
api_router.include_router(version.router, prefix="/version", tags=["version"])
