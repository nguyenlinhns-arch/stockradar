from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.stockradar.ledger import ImmutableLedger
from engine.stockradar.models import Candidate, Recommendation, UniverseSnapshot
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
    radar = build_radar(snapshot, candidates)

    RADAR_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RADAR_OUTPUT_PATH.write_text(
        json.dumps(radar, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    RECOMMENDATION_OUTPUT_PATH.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "is_mock": True,
                "notice": "Dữ liệu khuyến nghị mô phỏng; không gắn với cổ phiếu thật.",
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
