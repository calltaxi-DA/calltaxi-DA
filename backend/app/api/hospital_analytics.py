"""병원 이동 정적 분석정보 API."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.contracts import HospitalAnalyticsResponse
from app.services.hospital_analytics import HospitalAnalyticsError, load_hospital_analytics, resolve_hospital_chart

router = APIRouter(prefix="/analytics/hospital", tags=["analytics"])


@router.get("", response_model=HospitalAnalyticsResponse)
def get_hospital_analytics() -> HospitalAnalyticsResponse:
    try:
        return load_hospital_analytics()
    except HospitalAnalyticsError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/charts/{chart_id}", response_class=FileResponse)
def get_hospital_chart(chart_id: str) -> FileResponse:
    try:
        return FileResponse(resolve_hospital_chart(chart_id), media_type="image/png")
    except HospitalAnalyticsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
