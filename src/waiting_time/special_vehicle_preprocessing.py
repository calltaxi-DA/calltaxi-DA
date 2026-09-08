"""Preprocess special vehicle wait-time data.

This module follows the common preprocessing flow used for rental taxi
wait-time analysis, but intentionally leaves the special-vehicle request type
unclassified. Special vehicles can use multiple request methods, so request
type classification should be validated in a separate step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "서울시설공단_장애인콜택시 탑승내역_정제_20251231.csv"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "특장차_대기시간_전처리.csv"
)
DEFAULT_SUMMARY_PATH = (
    PROJECT_ROOT / "data" / "processed" / "특장차_대기시간_전처리_요약.csv"
)

DATETIME_COLS = [
    "접수일시",
    "예정일시",
    "배차일시",
    "승차일시",
    "하차일시",
    "취소일시",
]

WAIT_COLS = [
    "접수_배차_분",
    "접수_승차_분",
    "접수_취소_분",
    "배차_취소_분",
    "배차_승차_분",
]

SEOUL_25 = [
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
]

WEEKDAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]
DISTANCE_BINS = [0, 5, 10, 15, 25, float("inf")]
DISTANCE_LABELS = ["0~5km", "5~10km", "10~15km", "15~25km", "25km 초과"]


def load_raw_data(input_path: str | Path = DEFAULT_INPUT_PATH) -> pd.DataFrame:
    """Load the cleaned boarding-history source file."""
    return pd.read_csv(input_path)


def filter_special_vehicle(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only special vehicle rows."""
    return df[df["차량구분"].eq("특장차")].copy()


def remove_out_of_scope(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove trips where both origin and destination are outside Seoul."""
    origin_seoul = df["출발구"].isin(SEOUL_25)
    destination_seoul = df["목적구"].isin(SEOUL_25)
    outside_to_outside = ~origin_seoul & ~destination_seoul
    removed_count = int(outside_to_outside.sum())
    return df[~outside_to_outside].copy(), removed_count


def convert_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert datetime columns used in wait-time calculations."""
    df = df.copy()
    for col in DATETIME_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def create_wait_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create wait-time columns in minutes."""
    df = df.copy()
    df["접수_배차_분"] = (
        df["배차일시"] - df["접수일시"]
    ).dt.total_seconds() / 60
    df["접수_승차_분"] = (
        df["승차일시"] - df["접수일시"]
    ).dt.total_seconds() / 60
    df["접수_취소_분"] = (
        df["취소일시"] - df["접수일시"]
    ).dt.total_seconds() / 60
    df["배차_취소_분"] = (
        df["취소일시"] - df["배차일시"]
    ).dt.total_seconds() / 60
    df["배차_승차_분"] = (
        df["승차일시"] - df["배차일시"]
    ).dt.total_seconds() / 60
    return df


def handle_invalid_time_order(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Set negative wait times to missing and return a negative-count summary."""
    df = df.copy()
    negative_summary = []

    for col in WAIT_COLS:
        negative_count = int((df[col] < 0).sum())
        negative_summary.append({"컬럼명": col, "음수건수": negative_count})
        df.loc[df[col] < 0, col] = pd.NA

    return df, pd.DataFrame(negative_summary)


def create_date_gap_column(df: pd.DataFrame) -> pd.DataFrame:
    """Create a helper column for the date gap between request and boarding."""
    df = df.copy()
    df["접수승차_날짜차이"] = (
        df["승차일시"].dt.normalize() - df["접수일시"].dt.normalize()
    ).dt.days
    return df


def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create request-hour and weekday features."""
    df = df.copy()
    df["접수시간대"] = df["접수일시"].dt.strftime("%H:00:00")
    df["접수시간대_HH"] = df["접수일시"].dt.strftime("%H")

    df["접수요일"] = pd.Categorical(
        df["접수일시"].dt.dayofweek.map(
            {
                0: "월",
                1: "화",
                2: "수",
                3: "목",
                4: "금",
                5: "토",
                6: "일",
            }
        ),
        categories=WEEKDAY_ORDER,
        ordered=True,
    )
    df["평일주말"] = df["접수요일"].map(
        {"월": "평일", "화": "평일", "수": "평일", "목": "평일", "금": "평일", "토": "주말", "일": "주말"}
    )
    return df


def create_movement_type(df: pd.DataFrame) -> pd.DataFrame:
    """Create detailed movement type based on origin and destination districts."""
    df = df.copy()
    origin_seoul = df["출발구"].isin(SEOUL_25)
    destination_seoul = df["목적구"].isin(SEOUL_25)

    df["세부이동유형"] = pd.NA
    df.loc[
        origin_seoul & destination_seoul & df["출발구"].eq(df["목적구"]),
        "세부이동유형",
    ] = "구 내 이동"
    df.loc[
        origin_seoul & destination_seoul & ~df["출발구"].eq(df["목적구"]),
        "세부이동유형",
    ] = "구 간 이동"
    df.loc[origin_seoul & ~destination_seoul, "세부이동유형"] = "서울→서울 외"
    df.loc[~origin_seoul & destination_seoul, "세부이동유형"] = "서울 외→서울"
    return df


def create_distance_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create distance in kilometers and distance bands."""
    df = df.copy()
    df["승차거리_km"] = pd.to_numeric(df["승차거리"], errors="coerce") / 1000
    df["승차거리구간"] = pd.cut(
        df["승차거리_km"],
        bins=DISTANCE_BINS,
        labels=DISTANCE_LABELS,
        right=False,
    )
    return df


def create_empty_request_type_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add placeholder request-type columns without classifying special vehicles."""
    df = df.copy()
    df["특장차_접수유형"] = pd.NA
    df["특장차_접수유형_분류상태"] = "미분류"
    df["특장차_접수유형_메모"] = pd.NA
    return df


def create_summary_tables(
    df: pd.DataFrame,
    raw_special_count: int,
    removed_outside_to_outside_count: int,
    negative_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Create a compact preprocessing summary table."""
    rows: list[dict[str, Any]] = [
        {"구분": "특장차 원자료 건수", "값": raw_special_count},
        {"구분": "서울 외→서울 외 제거 건수", "값": removed_outside_to_outside_count},
        {"구분": "서울 외→서울 외 제거 후 건수", "값": len(df)},
        {"구분": "승차일시 존재 건수", "값": int(df["승차일시"].notna().sum())},
        {"구분": "취소일시 존재 건수", "값": int(df["취소일시"].notna().sum())},
        {"구분": "특장차_접수유형 미분류 건수", "값": int(df["특장차_접수유형"].isna().sum())},
    ]

    for col in WAIT_COLS:
        rows.append({"구분": f"{col} 유효건수", "값": int(df[col].notna().sum())})
        rows.append({"구분": f"{col} 결측건수", "값": int(df[col].isna().sum())})

    for _, row in negative_summary.iterrows():
        rows.append({"구분": f"{row['컬럼명']} 음수 이상값 건수", "값": int(row["음수건수"])})

    movement_counts = df["세부이동유형"].value_counts(dropna=False)
    for movement_type, count in movement_counts.items():
        rows.append({"구분": f"세부이동유형 {movement_type} 건수", "값": int(count)})

    return pd.DataFrame(rows)


def save_outputs(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
) -> tuple[Path, Path]:
    """Save the preprocessed dataset and summary table."""
    output_path = Path(output_path)
    summary_path = Path(summary_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    return output_path, summary_path


def run_special_vehicle_preprocessing(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    save: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the special vehicle preprocessing pipeline."""
    df = load_raw_data(input_path)
    df_special = filter_special_vehicle(df)
    raw_special_count = len(df_special)

    df_special, removed_outside_to_outside_count = remove_out_of_scope(df_special)
    df_special = convert_datetime_columns(df_special)
    df_special = create_wait_time_columns(df_special)
    df_special, negative_summary = handle_invalid_time_order(df_special)
    df_special = create_date_gap_column(df_special)
    df_special = create_time_features(df_special)
    df_special = create_movement_type(df_special)
    df_special = create_distance_features(df_special)
    df_special = create_empty_request_type_columns(df_special)

    summary = create_summary_tables(
        df_special,
        raw_special_count=raw_special_count,
        removed_outside_to_outside_count=removed_outside_to_outside_count,
        negative_summary=negative_summary,
    )

    if save:
        save_outputs(df_special, summary, output_path, summary_path)

    return df_special, summary


if __name__ == "__main__":
    preprocessed_df, preprocessing_summary = run_special_vehicle_preprocessing()
    print(f"저장 완료: {DEFAULT_OUTPUT_PATH}")
    print(f"요약 저장 완료: {DEFAULT_SUMMARY_PATH}")
    print(f"저장 건수: {len(preprocessed_df):,}건")
    print(preprocessing_summary.head(20).to_string(index=False))
