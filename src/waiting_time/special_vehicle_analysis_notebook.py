"""Build the special-vehicle wait-time analysis notebook.

The generated notebook follows the broad analysis flow used in the rental taxi
analysis notebook, with request-type candidate columns added for special
vehicles.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NOTEBOOK_PATH = (
    PROJECT_ROOT
    / "notebooks_waiting_time"
    / "04_special_vehicle_wait_time_analysis.ipynb"
)


def _md(source: str):
    return new_markdown_cell(dedent(source).strip() + "\n")


def _code(source: str):
    return new_code_cell(dedent(source).strip() + "\n")


def build_special_vehicle_analysis_notebook(
    output_path: str | Path = DEFAULT_NOTEBOOK_PATH,
) -> Path:
    """Create a Jupyter notebook for special-vehicle wait-time analysis."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cells = [
        _md(
            """
            # 특장차 대기시간 분석

            이 노트북은 `03_wait_time_data_preprocessing.ipynb`에서 생성한 특장차 분석용 데이터셋을 불러와 대기시간을 분석한다.

            특장차는 `바로콜`, `전일접수`, `심야시간 사전예약`, `기타 예약성/미분류`가 함께 존재하므로 접수유형 후보별로 분석 대상을 분리한다. 정기접수는 고객 식별자가 없어 확정 분류하지 않고 `정기접수_가능패턴여부` 보조 플래그로만 확인한다.
            """
        ),
        _code(
            """
            import json
            import platform
            from pathlib import Path

            import pandas as pd
            import matplotlib.pyplot as plt
            import seaborn as sns

            if platform.system() == "Darwin":
                plt.rcParams["font.family"] = "AppleGothic"
            elif platform.system() == "Windows":
                plt.rcParams["font.family"] = "Malgun Gothic"
            else:
                plt.rcParams["font.family"] = "NanumGothic"

            plt.rcParams["axes.unicode_minus"] = False
            sns.set_theme(style="whitegrid")
            """
        ),
        _code(
            """
            PROJECT_ROOT = Path.cwd()
            if not (PROJECT_ROOT / "data").exists() and (PROJECT_ROOT.parent / "data").exists():
                PROJECT_ROOT = PROJECT_ROOT.parent

            processed_dir = PROJECT_ROOT / "data" / "processed"

            final_dataset_path = processed_dir / "특장차_대기시간_전처리_접수유형분류.csv"
            final_summary_path = processed_dir / "특장차_대기시간_전처리_접수유형분류_요약.csv"

            print("final_dataset_path", final_dataset_path.exists(), final_dataset_path)
            print("final_summary_path", final_summary_path.exists(), final_summary_path)
            """
        ),
        _code(
            """
            datetime_cols = [
                "접수일시",
                "예정일시",
                "배차일시",
                "승차일시",
                "하차일시",
                "취소일시",
                "접수일자",
                "예정일자",
                "배차일자",
                "승차일자",
                "하차일자",
            ]

            def read_special_dataset(path):
                df = pd.read_csv(path)
                for col in datetime_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                return df

            df_special = read_special_dataset(final_dataset_path)
            special_analysis_dataset_summary = pd.read_csv(final_summary_path)

            request_type_col = "특장차_접수유형_후보_최종"
            if request_type_col not in df_special.columns:
                request_type_col = "특장차_접수유형_후보_보완"

            special_ride_valid = df_special[
                df_special["특장차_탑승완료_시간논리정상여부"].fillna(False)
            ].copy()

            special_ride_baro_call = special_ride_valid[
                special_ride_valid[request_type_col].eq("바로콜 후보")
            ].copy()

            special_ride_previous_day = special_ride_valid[
                special_ride_valid[request_type_col].eq("전일접수 후보")
            ].copy()

            special_ride_night_reservation = special_ride_valid[
                special_ride_valid[request_type_col].eq("심야시간 사전예약 후보")
            ].copy()

            special_ride_other = special_ride_valid[
                special_ride_valid[request_type_col].eq("기타 예약성/미분류")
            ].copy()

            special_cancel = df_special[df_special["취소일시"].notna()].copy()

            print(f"특장차 전처리 전체: {len(df_special):,}건")
            print(f"특장차 탑승완료 정상: {len(special_ride_valid):,}건")
            print(f"접수유형 분류 컬럼: {request_type_col}")
            display(special_analysis_dataset_summary)
            """
        ),
        _md(
            """
            ## 1. 전처리 결과 및 분석 데이터셋 재확인

            분석에 들어가기 전에 전처리 결과와 분석용 데이터셋 건수를 확인한다. 특히 접수유형 후보별 승차 완료 데이터셋과 취소 데이터셋을 분리해서 사용한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 분석용 데이터셋 건수와 핵심 대기시간 유효 표본 수를 재확인한다.

            analysis_dataset_summary = pd.DataFrame({
                "데이터셋": [
                    "df_special",
                    "special_ride_valid",
                    "special_ride_baro_call",
                    "special_ride_previous_day",
                    "special_ride_night_reservation",
                    "special_ride_other",
                    "special_cancel",
                ],
                "용도": [
                    "특장차 전체 전처리 결과",
                    "특장차 탑승완료 정상 건",
                    "특장차 바로콜 후보 승차 대기시간 분석",
                    "특장차 전일접수 후보 대기시간 분석",
                    "특장차 심야시간 사전예약 후보 분석",
                    "특장차 기타 예약성/미분류 확인",
                    "특장차 취소 전체 분석",
                ],
                "건수": [
                    len(df_special),
                    len(special_ride_valid),
                    len(special_ride_baro_call),
                    len(special_ride_previous_day),
                    len(special_ride_night_reservation),
                    len(special_ride_other),
                    len(special_cancel),
                ],
            })

            wait_cols = [
                "접수_배차_분",
                "접수_승차_분",
                "접수_취소_분",
                "배차_취소_분",
                "배차_승차_분",
            ]

            wait_valid_summary = pd.DataFrame({
                "컬럼명": wait_cols,
                "유효건수": [df_special[col].notna().sum() for col in wait_cols],
                "결측건수": [df_special[col].isna().sum() for col in wait_cols],
            })

            display(analysis_dataset_summary)
            display(wait_valid_summary)
            """
        ),
        _md(
            """
            ## 2. 접수유형 후보별 기본 현황

            접수유형 후보별 건수와 대기시간 분포를 비교한다. 특장차는 접수유형에 따라 `접수→승차`의 의미가 달라지므로 전체를 한 번에 해석하지 않는다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 접수유형 후보별 탑승완료 건수와 핵심 대기시간 요약을 확인한다.

            request_type_summary = (
                special_ride_valid
                .groupby(request_type_col, observed=False)
                .agg(
                    건수=("접수_승차_분", "count"),
                    접수_배차_중앙값=("접수_배차_분", "median"),
                    접수_배차_90분위수=("접수_배차_분", lambda x: x.quantile(0.90)),
                    접수_승차_중앙값=("접수_승차_분", "median"),
                    접수_승차_90분위수=("접수_승차_분", lambda x: x.quantile(0.90)),
                    배차_승차_중앙값=("배차_승차_분", "median"),
                    배차_승차_90분위수=("배차_승차_분", lambda x: x.quantile(0.90)),
                )
                .reset_index()
            )

            request_type_summary["비율(%)"] = (
                request_type_summary["건수"] / request_type_summary["건수"].sum() * 100
            )

            display(request_type_summary.sort_values("건수", ascending=False))
            """
        ),
        _code(
            """
            # 코드 셀 목적: 접수유형 후보별 건수와 접수→배차 90분위수를 함께 시각화한다.

            from matplotlib.ticker import FuncFormatter

            plot_data = request_type_summary.sort_values("건수", ascending=False).reset_index(drop=True)
            x = range(len(plot_data))

            fig, axes = plt.subplots(1, 2, figsize=(15, 5))

            axes[0].bar(x, plot_data["건수"], color="#bab0ab")
            for i, row in plot_data.iterrows():
                axes[0].text(
                    i,
                    row["건수"],
                    f'{row["건수"]:,}',
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

            axes[0].set_title("특장차 접수유형 후보별 탑승완료건수")
            axes[0].set_xlabel("접수유형 후보")
            axes[0].set_ylabel("건수")
            axes[0].set_xticks(list(x))
            axes[0].set_xticklabels(plot_data[request_type_col], rotation=20)
            axes[0].yaxis.set_major_formatter(FuncFormatter(lambda value, position: f"{int(value):,}"))
            axes[0].set_ylim(0, plot_data["건수"].max() * 1.12)
            axes[0].grid(axis="y", alpha=0.3)

            axes[1].plot(x, plot_data["접수_배차_중앙값"], marker="o", label="중앙값", color="#4c78a8")
            axes[1].plot(x, plot_data["접수_배차_90분위수"], marker="o", label="90분위수", color="#e45756")
            axes[1].set_title("특장차 접수유형 후보별 접수→배차 대기시간")
            axes[1].set_xlabel("접수유형 후보")
            axes[1].set_ylabel("접수→배차 대기시간(분)")
            axes[1].set_xticks(list(x))
            axes[1].set_xticklabels(plot_data[request_type_col], rotation=20)
            axes[1].grid(axis="y", alpha=0.3)
            axes[1].legend()

            plt.tight_layout()
            plt.show()
            """
        ),
        _md(
            """
            ## 3. 특장차 바로콜 승차 대기시간 분석

            바로콜 후보를 대상으로 `접수→배차`, `접수→승차`, `배차→승차`를 비교한다. 바로콜에서는 이용자가 체감하는 전체 대기시간인 `접수→승차`와, 공급 부족 가능성을 보여주는 `접수→배차`가 핵심 지표다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 바로콜 후보의 승차 대기시간 요약을 확인한다.

            ride_wait_cols = ["접수_배차_분", "접수_승차_분", "배차_승차_분"]
            baro_wait_summary = []

            for col in ride_wait_cols:
                values = special_ride_baro_call[col].dropna()
                baro_wait_summary.append({
                    "구간": col.replace("_", "→").replace("분", "").rstrip("→"),
                    "건수": values.count(),
                    "평균": values.mean(),
                    "중앙값": values.median(),
                    "75분위수": values.quantile(0.75),
                    "90분위수": values.quantile(0.90),
                    "95분위수": values.quantile(0.95),
                    "99분위수": values.quantile(0.99),
                    "최대값": values.max(),
                })

            baro_wait_summary = pd.DataFrame(baro_wait_summary)
            display(baro_wait_summary)
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 바로콜 후보의 대기시간 구간별 분포를 시각화한다.

            plot_data = baro_wait_summary.copy()
            x = range(len(plot_data))

            fig, ax = plt.subplots(figsize=(9, 5))
            ax.bar(x, plot_data["중앙값"], color="#76b7b2", label="중앙값")
            ax.scatter(x, plot_data["75분위수"], color="#f58518", s=70, zorder=3, label="75분위수")
            ax.scatter(x, plot_data["90분위수"], color="#e45756", s=70, zorder=3, label="90분위수")
            ax.set_title("특장차 바로콜 후보 승차 대기시간 구간별 분포")
            ax.set_ylabel("대기시간(분)")
            ax.set_xticks(list(x))
            ax.set_xticklabels(plot_data["구간"])
            ax.grid(axis="y", alpha=0.3)
            ax.legend()
            plt.tight_layout()
            plt.show()
            """
        ),
        _md(
            """
            ## 4. 전일접수 후보 대기시간 분석

            전일접수 후보는 접수 시점과 실제 탑승 예정시각 사이에 하루 정도의 간격이 있으므로, `접수→배차`나 `접수→승차`를 일반적인 대기시간으로 해석하면 안 된다.

            전일접수의 실제 운영 지연 여부는 `예정일시`를 기준으로 확인한다. 여기서 `예정일시`는 탑승예정시간이므로, 계산 방향은 다음과 같이 둔다.

            ```text
            예정대비_배차_분 = 배차일시 - 예정일시
            예정대비_승차_분 = 승차일시 - 예정일시
            배차_승차_분 = 승차일시 - 배차일시
            ```

            해석 기준은 다음과 같다.

            ```text
            예정대비 값 > 0  → 예정시각보다 늦게 배차/승차
            예정대비 값 = 0  → 예정시각과 동일하게 배차/승차
            예정대비 값 < 0  → 예정시각보다 먼저 배차/승차
            ```

            따라서 이 분석에서는 `예정→배차`처럼 방향이 모호한 이름 대신 `예정대비_배차_분`, `예정대비_승차_분`을 사용한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 전일접수 후보의 예정시각 대비 배차·승차 지연시간을 확인한다.

            previous_day_data = special_ride_previous_day.copy()

            previous_day_data["예정일시"] = pd.to_datetime(previous_day_data["예정일시"], errors="coerce")
            previous_day_data["배차일시"] = pd.to_datetime(previous_day_data["배차일시"], errors="coerce")
            previous_day_data["승차일시"] = pd.to_datetime(previous_day_data["승차일시"], errors="coerce")
            previous_day_data["배차_승차_분"] = pd.to_numeric(
                previous_day_data["배차_승차_분"],
                errors="coerce",
            )

            previous_day_data["예정대비_배차_분"] = (
                previous_day_data["배차일시"] - previous_day_data["예정일시"]
            ).dt.total_seconds() / 60

            previous_day_data["예정대비_승차_분"] = (
                previous_day_data["승차일시"] - previous_day_data["예정일시"]
            ).dt.total_seconds() / 60

            previous_day_wait_cols = ["예정대비_배차_분", "예정대비_승차_분", "배차_승차_분"]
            previous_day_wait_labels = {
                "예정대비_배차_분": "예정대비 배차",
                "예정대비_승차_분": "예정대비 승차",
                "배차_승차_분": "배차→승차",
            }
            previous_day_wait_summary = []

            for col in previous_day_wait_cols:
                values = previous_day_data[col].dropna()
                previous_day_wait_summary.append({
                    "구간": previous_day_wait_labels[col],
                    "건수": values.count(),
                    "평균": values.mean(),
                    "중앙값": values.median(),
                    "75분위수": values.quantile(0.75),
                    "90분위수": values.quantile(0.90),
                    "95분위수": values.quantile(0.95),
                    "최소값": values.min(),
                    "최대값": values.max(),
                })

            previous_day_wait_summary = pd.DataFrame(previous_day_wait_summary)
            display(previous_day_wait_summary)
            """
        ),
        _md(
            """
            ## 5. 심야시간 사전예약 후보 분석

            심야시간 사전예약 후보는 월별 분포와 시간대별 최대 3명 기준을 검증한다. 이 기준은 후보 제외 조건이 아니라 운영 기준과 데이터가 얼마나 맞는지 확인하는 지표다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 심야시간 사전예약 후보의 월별·시간대별 분포와 3명 기준 초과 여부를 확인한다.

            night_data = special_ride_night_reservation.copy()
            night_data["승차월"] = night_data["승차일시"].dt.to_period("M").astype(str)

            night_month_summary = (
                night_data
                .groupby("승차월", observed=False)
                .size()
                .reset_index(name="심야시간사전예약_후보건수")
            )

            night_capacity_summary = (
                night_data
                .groupby(["승차일자", "승차시간대"], observed=False)
                .size()
                .reset_index(name="탑승완료건수")
            )
            night_capacity_summary["시간대별_3명초과여부"] = night_capacity_summary["탑승완료건수"].gt(3)

            display(night_month_summary)
            display(night_capacity_summary.sort_values("탑승완료건수", ascending=False).head(30))
            """
        ),
        _md(
            """
            ## 6. 취소 대기시간 분석

            취소 건은 승차일시가 없을 수 있으므로 승차 완료 접수유형 후보와 같은 방식으로 확정 분류하지 않는다. 우선 특장차 취소 전체를 대상으로 `접수→취소`, `배차→취소` 시간을 확인한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 취소 전체의 취소 대기시간 요약과 배차 전후 취소 건수를 확인한다.

            cancel_wait_summary = []
            for col in ["접수_취소_분", "배차_취소_분"]:
                values = special_cancel[col].dropna()
                cancel_wait_summary.append({
                    "구간": col.replace("_", "→").replace("분", "").rstrip("→"),
                    "건수": values.count(),
                    "평균": values.mean(),
                    "중앙값": values.median(),
                    "75분위수": values.quantile(0.75),
                    "90분위수": values.quantile(0.90),
                    "95분위수": values.quantile(0.95),
                    "99분위수": values.quantile(0.99),
                    "최대값": values.max(),
                })

            cancel_dispatch_summary = pd.DataFrame({
                "구분": ["취소 전체", "배차 후 취소", "배차 전 취소 또는 배차일시 미기록 취소"],
                "건수": [
                    len(special_cancel),
                    special_cancel["배차일시"].notna().sum(),
                    special_cancel["배차일시"].isna().sum(),
                ],
            })
            cancel_dispatch_summary["비율(%)"] = cancel_dispatch_summary["건수"] / len(special_cancel) * 100

            display(pd.DataFrame(cancel_wait_summary))
            display(cancel_dispatch_summary)
            """
        ),
        _md(
            """
            ## 7. 접수시간대별 대기시간 분석

            접수시간대별로 바로콜 후보의 `접수→배차`, `접수→승차`, `배차→승차` 90분위수를 확인한다. 90분위수는 평균보다 극단값 영향이 작으면서 장시간 대기 구간을 볼 수 있는 지표다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 바로콜 후보의 접수시간대별 대기시간을 집계하고 시각화한다.

            hourly_baro_summary = (
                special_ride_baro_call
                .groupby("접수시간대", observed=False)
                .agg(
                    승차완료건수=("접수_승차_분", "count"),
                    접수_배차_중앙값=("접수_배차_분", "median"),
                    접수_배차_90분위수=("접수_배차_분", lambda x: x.quantile(0.90)),
                    접수_승차_중앙값=("접수_승차_분", "median"),
                    접수_승차_90분위수=("접수_승차_분", lambda x: x.quantile(0.90)),
                    배차_승차_중앙값=("배차_승차_분", "median"),
                    배차_승차_90분위수=("배차_승차_분", lambda x: x.quantile(0.90)),
                )
                .reset_index()
                .sort_values("접수시간대")
            )

            hourly_baro_summary["접수시간대_HH"] = hourly_baro_summary["접수시간대"].astype(str).str.slice(0, 2)

            display(hourly_baro_summary)

            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(hourly_baro_summary["접수시간대_HH"], hourly_baro_summary["접수_배차_90분위수"], marker="o", label="접수→배차 90분위수")
            ax.plot(hourly_baro_summary["접수시간대_HH"], hourly_baro_summary["배차_승차_90분위수"], marker="o", label="배차→승차 90분위수")
            ax.set_title("특장차 바로콜 후보 접수시간대별 장시간 대기 원인 비교")
            ax.set_xlabel("접수시간대")
            ax.set_ylabel("90분위수 대기시간(분)")
            ax.grid(axis="y", alpha=0.3)
            ax.legend()
            plt.tight_layout()
            plt.show()
            """
        ),
        _md(
            """
            ## 8. 요일별 대기시간 분석

            요일별로 특장차 바로콜 후보의 승차 완료건수와 대기시간을 비교한다. 평일과 주말은 이용 목적과 차량 운영 패턴이 다를 수 있다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 바로콜 후보의 요일별 승차완료건수와 대기시간을 확인한다.

            weekday_order = ["월", "화", "수", "목", "금", "토", "일"]
            special_ride_baro_call["접수요일"] = pd.Categorical(
                special_ride_baro_call["접수요일"],
                categories=weekday_order,
                ordered=True,
            )

            weekday_baro_summary = (
                special_ride_baro_call
                .groupby("접수요일", observed=False)
                .agg(
                    승차완료건수=("접수_승차_분", "count"),
                    접수_배차_중앙값=("접수_배차_분", "median"),
                    접수_배차_90분위수=("접수_배차_분", lambda x: x.quantile(0.90)),
                    접수_승차_중앙값=("접수_승차_분", "median"),
                    접수_승차_90분위수=("접수_승차_분", lambda x: x.quantile(0.90)),
                )
                .reset_index()
            )

            display(weekday_baro_summary)
            """
        ),
        _md(
            """
            ## 9. 출발구별·이동유형별 대기시간 분석

            출발구와 세부이동유형을 함께 보아 지역별 차량 접근성과 광역 이동 부담을 확인한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 출발구별·세부이동유형별 접수→배차 90분위수와 승차완료건수를 확인한다.

            district_movement_baro_summary = (
                special_ride_baro_call
                .groupby(["출발구", "세부이동유형"], observed=False)
                .agg(
                    승차완료건수=("접수_배차_분", "count"),
                    접수_배차_중앙값=("접수_배차_분", "median"),
                    접수_배차_90분위수=("접수_배차_분", lambda x: x.quantile(0.90)),
                    접수_승차_중앙값=("접수_승차_분", "median"),
                    접수_승차_90분위수=("접수_승차_분", lambda x: x.quantile(0.90)),
                )
                .reset_index()
            )

            display(district_movement_baro_summary.sort_values(["접수_배차_90분위수", "승차완료건수"], ascending=False).head(30))

            heatmap_data = district_movement_baro_summary.pivot_table(
                index="출발구",
                columns="세부이동유형",
                values="접수_배차_90분위수",
                aggfunc="median",
            )

            fig, ax = plt.subplots(figsize=(9, 10))
            sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap="Reds", linewidths=0.5, ax=ax)
            ax.set_title("특장차 바로콜 후보 출발구별·이동유형별 접수→배차 90분위수")
            ax.set_xlabel("세부이동유형")
            ax.set_ylabel("출발구")
            plt.tight_layout()
            plt.show()
            """
        ),
        _md(
            """
            ## 10. 승차거리에 따른 대기시간 분석

            승차거리가 길어질수록 배차가 늦어지는지 확인한다. 장거리 이동은 기사 입장에서 운행 및 회차 부담이 커질 수 있으므로 `접수→배차`를 핵심 지표로 본다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 승차거리구간별 특장차 바로콜 후보의 대기시간을 확인한다.

            distance_baro_summary = (
                special_ride_baro_call
                .groupby("승차거리구간", observed=False)
                .agg(
                    승차완료건수=("접수_배차_분", "count"),
                    접수_배차_중앙값=("접수_배차_분", "median"),
                    접수_배차_90분위수=("접수_배차_분", lambda x: x.quantile(0.90)),
                    접수_승차_중앙값=("접수_승차_분", "median"),
                    접수_승차_90분위수=("접수_승차_분", lambda x: x.quantile(0.90)),
                    배차_승차_중앙값=("배차_승차_분", "median"),
                    배차_승차_90분위수=("배차_승차_분", lambda x: x.quantile(0.90)),
                )
                .reset_index()
            )

            display(distance_baro_summary)

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(distance_baro_summary["승차거리구간"].astype(str), distance_baro_summary["접수_배차_90분위수"], marker="o", label="접수→배차 90분위수")
            ax.plot(distance_baro_summary["승차거리구간"].astype(str), distance_baro_summary["접수_승차_90분위수"], marker="o", label="접수→승차 90분위수")
            ax.set_title("특장차 바로콜 후보 승차거리구간별 대기시간")
            ax.set_xlabel("승차거리구간")
            ax.set_ylabel("대기시간(분)")
            ax.tick_params(axis="x", rotation=20)
            ax.grid(axis="y", alpha=0.3)
            ax.legend()
            plt.tight_layout()
            plt.show()
            """
        ),
        _md(
            """
            ## 11. 장시간 대기 건 특징 분석

            바로콜 후보 중 `접수→배차` 90분위수 이상인 장시간 대기 건이 특정 시간대, 요일, 지역, 이동유형, 승차거리구간에 집중되는지 확인한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 바로콜 후보 중 접수→배차 장시간 대기 건의 특징을 확인한다.

            dispatch_delay_cutoff = special_ride_baro_call["접수_배차_분"].quantile(0.90)
            long_dispatch_baro = special_ride_baro_call[
                special_ride_baro_call["접수_배차_분"].ge(dispatch_delay_cutoff)
            ].copy()

            print(f"접수→배차 장시간 기준(90분위수): {dispatch_delay_cutoff:.1f}분")
            print(f"장시간 대기 건수: {len(long_dispatch_baro):,}건")

            feature_cols = ["접수시간대", "접수요일", "출발구", "세부이동유형", "승차거리구간"]
            for col in feature_cols:
                print(f"\\n[{col}]")
                display(
                    long_dispatch_baro[col]
                    .value_counts(dropna=False)
                    .reset_index(name="장시간대기건수")
                    .head(20)
                )
            """
        ),
        _md(
            """
            ## 12. 취소율과 대기시간 관계 분석

            취소율은 승차 완료건수와 취소건수를 함께 보아야 한다. 이 단계에서는 접수시간대, 요일, 출발구, 세부이동유형별 취소율을 확인한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 조건별 특장차 취소율을 계산한다.

            def summarize_cancel_rate(ride_df, cancel_df, group_col):
                ride_summary = (
                    ride_df.groupby(group_col, observed=False)
                    .size()
                    .reset_index(name="승차완료건수")
                )
                cancel_summary = (
                    cancel_df.groupby(group_col, observed=False)
                    .size()
                    .reset_index(name="취소건수")
                )
                summary = ride_summary.merge(cancel_summary, on=group_col, how="outer")
                summary["승차완료건수"] = summary["승차완료건수"].fillna(0).astype(int)
                summary["취소건수"] = summary["취소건수"].fillna(0).astype(int)
                summary["전체접수건수"] = summary["승차완료건수"] + summary["취소건수"]
                summary["취소율(%)"] = summary["취소건수"] / summary["전체접수건수"] * 100
                return summary.sort_values(["취소율(%)", "전체접수건수"], ascending=False).reset_index(drop=True)

            cancel_rate_by_hour = summarize_cancel_rate(special_ride_baro_call, special_cancel, "접수시간대")
            cancel_rate_by_weekday = summarize_cancel_rate(special_ride_baro_call, special_cancel, "접수요일")
            cancel_rate_by_district = summarize_cancel_rate(special_ride_baro_call, special_cancel, "출발구")
            cancel_rate_by_movement = summarize_cancel_rate(special_ride_baro_call, special_cancel, "세부이동유형")

            display(cancel_rate_by_hour)
            display(cancel_rate_by_weekday)
            display(cancel_rate_by_district.head(20))
            display(cancel_rate_by_movement)
            """
        ),
        _md(
            """
            ## 13. 배차 지연형과 배차 후 지연형 분리

            바로콜 후보의 장시간 대기가 차량 배정 단계에서 발생하는지, 배차 후 차량 접근 단계에서 발생하는지 분리한다.
            """
        ),
        _code(
            """
            # 코드 셀 목적: 특장차 바로콜 후보의 지연유형을 접수→배차와 배차→승차 90분위수 기준으로 분리한다.

            dispatch_delay_cutoff = special_ride_baro_call["접수_배차_분"].quantile(0.90)
            pickup_delay_cutoff = special_ride_baro_call["배차_승차_분"].quantile(0.90)

            special_ride_baro_call["접수_배차_장시간여부"] = special_ride_baro_call["접수_배차_분"].ge(dispatch_delay_cutoff)
            special_ride_baro_call["배차_승차_장시간여부"] = special_ride_baro_call["배차_승차_분"].ge(pickup_delay_cutoff)

            special_ride_baro_call["지연유형"] = "일반"
            special_ride_baro_call.loc[
                special_ride_baro_call["접수_배차_장시간여부"] & ~special_ride_baro_call["배차_승차_장시간여부"],
                "지연유형",
            ] = "배차 지연형"
            special_ride_baro_call.loc[
                ~special_ride_baro_call["접수_배차_장시간여부"] & special_ride_baro_call["배차_승차_장시간여부"],
                "지연유형",
            ] = "배차 후 지연형"
            special_ride_baro_call.loc[
                special_ride_baro_call["접수_배차_장시간여부"] & special_ride_baro_call["배차_승차_장시간여부"],
                "지연유형",
            ] = "복합 지연형"

            delay_type_summary = (
                special_ride_baro_call
                .groupby("지연유형", observed=False)
                .agg(
                    건수=("접수_승차_분", "count"),
                    접수_배차_중앙값=("접수_배차_분", "median"),
                    접수_배차_90분위수=("접수_배차_분", lambda x: x.quantile(0.90)),
                    배차_승차_중앙값=("배차_승차_분", "median"),
                    배차_승차_90분위수=("배차_승차_분", lambda x: x.quantile(0.90)),
                    접수_승차_중앙값=("접수_승차_분", "median"),
                    접수_승차_90분위수=("접수_승차_분", lambda x: x.quantile(0.90)),
                )
                .reset_index()
            )
            delay_type_summary["비율(%)"] = delay_type_summary["건수"] / delay_type_summary["건수"].sum() * 100

            display(delay_type_summary.sort_values("건수", ascending=False))
            """
        ),
    ]

    nb = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": ".venv (Python 3.12)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
    )
    nbformat.write(nb, output_path)
    return output_path


if __name__ == "__main__":
    notebook_path = build_special_vehicle_analysis_notebook()
    print(notebook_path)
