"""Campaign API endpoints."""

from fastapi import APIRouter, HTTPException

from backend.services.campaign_service import (
    get_campaigns,
    get_campaign_by_id,
    get_campaign_enrollments,
)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("/")
async def list_campaigns(status: str | None = None):
    return await get_campaigns(status=status)


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/enrollments")
async def get_enrollments(campaign_id: str):
    return await get_campaign_enrollments(campaign_id)
