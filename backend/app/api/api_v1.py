from fastapi import APIRouter
from app.api.endpoints import (
    investigations,
    deviations,
    intake,
    copilot,
    five_whys,
    fishbone,
    capas,
    audit,
    evidences,
    auth,
    config
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Identity"])
api_router.include_router(config.router, prefix="/config", tags=["Configuration"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["Investigations"])
api_router.include_router(deviations.router, prefix="/deviations", tags=["Deviations"])
api_router.include_router(intake.router, prefix="/intake", tags=["Intake"])
api_router.include_router(copilot.router, prefix="/copilot", tags=["Copilot"])
api_router.include_router(evidences.router, tags=["Evidence & Traceability"])
api_router.include_router(five_whys.router, tags=["5-Whys Analysis"])
api_router.include_router(fishbone.router, tags=["Fishbone 6M Analysis"])
api_router.include_router(capas.router, tags=["CAPA Recommendations"])
api_router.include_router(audit.router, tags=["Audit Trail"])

