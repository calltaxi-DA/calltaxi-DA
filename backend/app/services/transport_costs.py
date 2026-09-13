"""사용자가 기록한 교통비를 저장하고 기간별로 집계한다."""

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from app.api.contracts import (
    DailyTransportCostResponse,
    DailyTransportCostSummary,
    Location,
    MonthlyTransportCostResponse,
    TransportCostRecord,
    TransportCostTotals,
    TransportType,
)


class TransportCostRepositoryError(RuntimeError):
    """교통비 저장소를 사용할 수 없을 때 발생한다."""


class SqliteTransportCostRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def add(
        self,
        *,
        travel_date: date,
        actual_cost_won: int,
        recommended_cost_won: int,
        selected_transport_type: TransportType,
        recommended_transport_type: TransportType,
        origin: Location,
        destination: Location,
    ) -> TransportCostRecord:
        created_at = datetime.now(timezone.utc)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO transport_cost_records (
                        travel_date, actual_cost_won, recommended_cost_won,
                        selected_transport_type, recommended_transport_type,
                        origin_json, destination_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        travel_date.isoformat(), actual_cost_won, recommended_cost_won,
                        selected_transport_type.value, recommended_transport_type.value,
                        origin.model_dump_json(), destination.model_dump_json(), created_at.isoformat(),
                    ),
                )
                record_id = cursor.lastrowid
        except (OSError, sqlite3.Error) as exc:
            raise TransportCostRepositoryError("교통비 기록을 저장하지 못했습니다.") from exc
        if record_id is None:
            raise TransportCostRepositoryError("교통비 기록 ID를 생성하지 못했습니다.")
        return TransportCostRecord(
            id=record_id, travel_date=travel_date, actual_cost_won=actual_cost_won,
            recommended_cost_won=recommended_cost_won,
            potential_savings_won=max(actual_cost_won - recommended_cost_won, 0),
            selected_transport_type=selected_transport_type,
            recommended_transport_type=recommended_transport_type,
            origin=origin, destination=destination, created_at=created_at,
        )

    def daily(self, target_date: date) -> DailyTransportCostResponse:
        records = self._list("travel_date = ?", (target_date.isoformat(),))
        return DailyTransportCostResponse(date=target_date, records=records, totals=_totals(records))

    def monthly(self, month: str) -> MonthlyTransportCostResponse:
        records = self._list("substr(travel_date, 1, 7) = ?", (month,))
        grouped: dict[date, list[TransportCostRecord]] = {}
        for record in records:
            grouped.setdefault(record.travel_date, []).append(record)
        summaries = [
            DailyTransportCostSummary(date=day, record_count=len(items), **_totals(items).model_dump())
            for day, items in sorted(grouped.items())
        ]
        return MonthlyTransportCostResponse(month=month, daily_summaries=summaries, totals=_totals(records))

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transport_cost_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                travel_date TEXT NOT NULL,
                actual_cost_won INTEGER NOT NULL CHECK(actual_cost_won >= 0),
                recommended_cost_won INTEGER NOT NULL CHECK(recommended_cost_won >= 0),
                selected_transport_type TEXT NOT NULL,
                recommended_transport_type TEXT NOT NULL,
                origin_json TEXT NOT NULL,
                destination_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        return connection

    def _list(self, where_clause: str, params: tuple[str, ...]) -> list[TransportCostRecord]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    f"SELECT * FROM transport_cost_records WHERE {where_clause} ORDER BY travel_date, id", params
                ).fetchall()
            return [_to_record(row) for row in rows]
        except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
            raise TransportCostRepositoryError("교통비 기록을 조회하지 못했습니다.") from exc


def _to_record(row: sqlite3.Row) -> TransportCostRecord:
    actual = int(row["actual_cost_won"])
    recommended = int(row["recommended_cost_won"])
    return TransportCostRecord(
        id=row["id"], travel_date=row["travel_date"], actual_cost_won=actual,
        recommended_cost_won=recommended, potential_savings_won=max(actual - recommended, 0),
        selected_transport_type=row["selected_transport_type"],
        recommended_transport_type=row["recommended_transport_type"],
        origin=Location.model_validate(json.loads(row["origin_json"])),
        destination=Location.model_validate(json.loads(row["destination_json"])),
        created_at=row["created_at"],
    )


def _totals(records: list[TransportCostRecord]) -> TransportCostTotals:
    return TransportCostTotals(
        actual_cost_won=sum(item.actual_cost_won for item in records),
        recommended_cost_won=sum(item.recommended_cost_won for item in records),
        potential_savings_won=sum(item.potential_savings_won for item in records),
    )
