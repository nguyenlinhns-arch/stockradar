from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.stockradar.ledger import ImmutableLedger
from engine.stockradar.models import Candidate, Recommendation, RecommendationMode, UniverseSnapshot
from engine.stockradar.ranking import build_radar


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "engine" / "fixtures" / "demo_snapshot.json"
RADAR_OUTPUT_PATH = ROOT / "website" / "public" / "data" / "radar.json"
TRACK_OUTPUT_PATH = ROOT / "website" / "public" / "data" / "track-record.json"
RECOMMENDATION_OUTPUT_PATH = ROOT / "website" / "public" / "data" / "recommendations.json"
LEDGER_PATH = ROOT / "artifacts" / "stockradar_demo.sqlite"


def build_demo() -> dict[str, object]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    snapshot = UniverseSnapshot.from_dict(fixture["snapshot"])
    candidates = [Candidate.from_dict(item) for item in fixture["candidates"]]
    recommendations = [Recommendation.from_dict(item) for item in fixture.get("recommendations", [])]
    closed_returns = [item.final_return_pct for item in recommendations if item.final_return_pct is not None]
    gains = [value for value in closed_returns if value > 0]
    losses = [value for value in closed_returns if value < 0]
    performance_summary = {
        "total_published": len(recommendations),
        "unactivated": sum(not item.is_activated for item in recommendations),
        "open": sum(item.is_activated and not item.is_closed for item in recommendations),
        "closed": sum(item.is_closed for item in recommendations),
        "target_reached": sum(item.recommendation_state.value == "TARGET_REACHED" for item in recommendations),
        "stop_reached": sum(item.recommendation_state.value == "STOP_REACHED" for item in recommendations),
        "profitable_closed": len(gains),
        "win_rate_pct": round(len(gains) / len(closed_returns) * 100, 2) if closed_returns else None,
        "average_gain_pct": round(sum(gains) / len(gains), 2) if gains else None,
        "average_loss_pct": round(sum(losses) / len(losses), 2) if losses else None,
        "average_closed_return_pct": round(sum(closed_returns) / len(closed_returns), 2) if closed_returns else None,
        "excludes_unactivated_from_win_rate": True,
    }
    radar = build_radar(snapshot, candidates)

    RADAR_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RADAR_OUTPUT_PATH.write_text(
        json.dumps(radar, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    RECOMMENDATION_OUTPUT_PATH.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "is_mock": True,
                "notice": "Dữ liệu khuyến nghị mô phỏng; không gắn với cổ phiếu thật.",
                "recommendation_mode": RecommendationMode.RESEARCH_ONLY.value,
                "performance_method": "FIRST_POST_PUBLICATION_ELIGIBLE_BAR_TOUCH",
                "performance_summary": performance_summary,
                "snapshot": snapshot.to_dict(),
                "items": [item.to_dict() for item in recommendations],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    if LEDGER_PATH.exists():
        LEDGER_PATH.unlink()
    ledger = ImmutableLedger(LEDGER_PATH)
    try:
        ledger.initialize()
        ledger.append_radar(radar)
        for recommendation in recommendations:
            record = recommendation.to_dict()
            ledger.append_recommendation(record)
            ledger.append_recommendation_event(
                recommendation.recommendation_id,
                "PUBLISHED",
                recommendation.published_at,
                "UNACTIVATED",
                {"price_at_publication": recommendation.price_at_publication},
            )
            if recommendation.is_activated:
                ledger.append_recommendation_event(
                    recommendation.recommendation_id,
                    "ACTIVATED",
                    recommendation.activation_timestamp or recommendation.published_at,
                    "ACTIVE",
                    {"performance_entry_price": recommendation.performance_entry_price},
                )
            if recommendation.is_closed:
                ledger.append_recommendation_event(
                    recommendation.recommendation_id,
                    "CLOSED",
                    recommendation.close_timestamp or recommendation.published_at,
                    recommendation.recommendation_state.value,
                    {
                        "close_price": recommendation.close_price,
                        "final_return_pct": recommendation.final_return_pct,
                    },
                    reason=recommendation.close_reason,
                )
        track = {
            "is_mock": True,
            "notice": "Dữ liệu minh hoạ; không phải lịch sử tín hiệu thật.",
            "rows": ledger.fetch_public_track_record(),
        }
        TRACK_OUTPUT_PATH.write_text(
            json.dumps(track, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    finally:
        ledger.close()

    return radar


def main() -> None:
    parser = argparse.ArgumentParser(description="StockRadar V1 utility")
    parser.add_argument("command", choices=["build-demo"])
    args = parser.parse_args()
    if args.command == "build-demo":
        radar = build_demo()
        print(
            json.dumps(
                {
                    "status": radar["status"],
                    "is_top5_hose": radar["is_top5_hose"],
                    "items": len(radar["items"]),
                    "output": str(RADAR_OUTPUT_PATH),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
