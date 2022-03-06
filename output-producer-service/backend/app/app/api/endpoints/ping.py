from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def pong():
    return {"message": "pong"}
