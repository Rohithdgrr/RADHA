import structlog
from fastapi import APIRouter
from app.services.lmarena_models import fetch_models_from_bridge, FALLBACK_MODELS

log = structlog.get_logger()
router = APIRouter()


@router.get("/models")
async def list_models():
    models = await fetch_models_from_bridge()
    if models is None:
        log.warning("models fallback to static — bridge unreachable")
        models = FALLBACK_MODELS
    return {"models": models}
