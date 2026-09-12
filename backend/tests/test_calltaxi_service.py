import pytest

from app.services.calltaxi import (
    TmapRouteError,
    calculate_seoul_calltaxi_fare,
    parse_tmap_route_metrics,
)


@pytest.mark.parametrize(
    ("distance_meters", "expected_fare_won"),
    [
        (0, 1_500),
        (5_000, 1_500),
        (10_000, 2_900),
        (20_000, 3_600),
    ],
)
def test_calculate_seoul_calltaxi_fare(distance_meters: int, expected_fare_won: int) -> None:
    assert calculate_seoul_calltaxi_fare(distance_meters) == expected_fare_won


def test_calculate_seoul_calltaxi_fare_floors_under_100_won() -> None:
    assert calculate_seoul_calltaxi_fare(12_500) == 3_000


def test_parse_tmap_route_metrics() -> None:
    payload = {
        "features": [
            {
                "properties": {
                    "totalDistance": 12_345,
                    "totalTime": 1_234,
                }
            }
        ]
    }

    distance_meters, time_seconds = parse_tmap_route_metrics(payload)

    assert distance_meters == 12_345
    assert time_seconds == 1_234


def test_parse_tmap_route_metrics_rejects_missing_metrics() -> None:
    with pytest.raises(TmapRouteError):
        parse_tmap_route_metrics({"features": []})


def test_parse_tmap_route_metrics_rejects_negative_metrics() -> None:
    with pytest.raises(TmapRouteError):
        parse_tmap_route_metrics(
            {
                "features": [
                    {
                        "properties": {
                            "totalDistance": -1,
                            "totalTime": 1_234,
                        }
                    }
                ]
            }
        )
