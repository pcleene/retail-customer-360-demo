"""Dashboard API endpoints."""

from fastapi import APIRouter

from backend.services.dashboard_service import get_dashboard_kpis

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis")
async def dashboard_kpis():
    return await get_dashboard_kpis()
