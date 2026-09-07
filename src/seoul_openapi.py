from __future__ import annotations
from typing import Any
import pandas as pd
import requests

BASE_URL = "http://openapi.seoul.go.kr:8088"

def fetch_seoul_openapi_rows(
    service_key: str,
    service_name: str,
    start_index: int = 1,
    end_index: int = 1000,
    response_type: str = "json",
    timeout: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    url = f"{BASE_URL}/{service_key}/{response_type}/{service_name}/{start_index}/{end_index}/"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    if service_name not in data:
        raise RuntimeError(f"{service_name} 응답을 찾을 수 없습니다: {data}")
    payload = data[service_name]
    result = payload.get("RESULT", {})
    if result.get("CODE") != "INFO-000":
        raise RuntimeError(f"{service_name} API 오류: {result}")

    return payload.get("row", []), int(payload.get("list_total_count", 0))


def fetch_all_seoul_openapi_rows(
    service_key: str,
    service_name: str,
    page_size: int = 1000,
) -> pd.DataFrame:
    first_rows, total_count = fetch_seoul_openapi_rows(
        service_key=service_key,
        service_name=service_name,
        start_index=1,
        end_index=page_size,
    )
    rows = list(first_rows)

    for start_index in range(page_size + 1, total_count + 1, page_size):
        end_index = min(start_index + page_size - 1, total_count)
        page_rows, _ = fetch_seoul_openapi_rows(
            service_key=service_key,
            service_name=service_name,
            start_index=start_index,
            end_index=end_index,
        )
        rows.extend(page_rows)

    return pd.DataFrame(rows)
