import logging

from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import Session


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logging.info(f"Creating Database session for {request.url}")
        request.state.db = Session()
        response = await call_next(request)
        logging.info(f"Closing Database session for {request.url}")
        request.state.db.close()
        return response
