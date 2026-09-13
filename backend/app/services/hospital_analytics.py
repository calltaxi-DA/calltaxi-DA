"""검토 완료된 병원 분석 export를 읽는 서비스."""

import json
from pathlib import Path

from app.api.contracts import HospitalAnalyticsResponse

ANALYSIS_DIR = Path(__file__).resolve().parents[3] / "analysis"
DEFAULT_HOSPITAL_ANALYTICS_PATH = ANALYSIS_DIR / "hospital/hospital_analytics.json"
DEFAULT_HOSPITAL_CHART_DIR = ANALYSIS_DIR / "hospital/figures"
CHART_FILES = {
    "medical_same_vs_different_district": "medical_same_vs_different_district.png",
    "medical_within_5km_coverage": "medical_within_5km_coverage.png",
}


class HospitalAnalyticsError(RuntimeError):
    pass


class UnknownHospitalChartError(HospitalAnalyticsError):
    pass


class HospitalChartUnavailableError(HospitalAnalyticsError):
    pass


def load_hospital_analytics(path: Path = DEFAULT_HOSPITAL_ANALYTICS_PATH) -> HospitalAnalyticsResponse:
    try:
        with path.open(encoding="utf-8") as file:
            return HospitalAnalyticsResponse.model_validate(json.load(file))
    except (OSError, ValueError) as exc:
        raise HospitalAnalyticsError("hospital analytics export is unavailable") from exc


def resolve_hospital_chart(chart_id: str, chart_dir: Path = DEFAULT_HOSPITAL_CHART_DIR) -> Path:
    filename = CHART_FILES.get(chart_id)
    if filename is None:
        raise UnknownHospitalChartError("unknown hospital chart")
    path = chart_dir / filename
    if not path.is_file():
        raise HospitalChartUnavailableError("hospital chart is unavailable")
    return path
