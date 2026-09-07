from __future__ import annotations
from typing import Any
from urllib.parse import unquote

import pandas as pd
import requests
from src.config import MOBILITY_API_BASE_URL, MOBILITY_API_KEY

def fetch_mobility_openapi(
    operation: str,
    *,
    service_key: str | None = None,
    base_url: str | None = None,
    response_type: str = "json",
    timeout: int = 30,
    **params: Any,
) -> dict[str, Any]:
    """공공데이터포털 교통약자 API를 호출합니다.
    예시 URL 구조:
        https://apis.data.go.kr/B553766/wksn/{operation}?serviceKey=...&type=json
    operation 이름과 추가 파라미터는 API 문서의 세부 endpoint에 맞춰 전달합니다.
    """
    api_key = service_key or MOBILITY_API_KEY
    if not api_key:
        raise RuntimeError("MOBILITY_API_KEY 환경변수가 .env에 설정되어 있지 않습니다.")

    url = f"{(base_url or MOBILITY_API_BASE_URL).rstrip('/')}/{operation.lstrip('/')}"
    query_params = {"serviceKey": unquote(api_key), **params}

    if response_type:
        query_params.setdefault("type", response_type)

    response = requests.get(url, params=query_params, timeout=timeout)
    response.raise_for_status()

    if response_type.lower() == "json":
        return response.json()

    return {"raw": response.text}


def fetch_mobility_items(
    operation: str,
    *,
    item_path: tuple[str, ...] = ("response", "body", "items", "item"),
    **params: Any,
) -> pd.DataFrame:
    """교통약자 API 응답에서 item 목록을 DataFrame으로 변환합니다."""
    data = fetch_mobility_openapi(operation, **params)
    items: Any = data

    for key in item_path:
        if not isinstance(items, dict):
            items = []
            break
        items = items.get(key, [])

    if isinstance(items, dict):
        items = [items]

    return pd.DataFrame(items)
