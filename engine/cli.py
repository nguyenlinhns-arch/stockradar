from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.stockradar.ledger import ImmutableLedger
from engine.stockradar.models import Candidate, Recommendation, RecommendationMode, UniverseSnapshot
from engine.stockradar.ranking import build_radar
from engine.stockradar.ticker_lookup import TickerMaster


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "engine" / "fixtures" / "demo_snapshot.json"
TICKER_MASTER_FIXTURE_PATH = ROOT / "engine" / "fixtures" / "hose_universe_demo.json"
PUBLIC_DATA_DIR = ROOT / "website" / "public" / "data"
DEMO_DATA_DIR = ROOT / "artifacts" / "demo-data"
RADAR_OUTPUT_PATH = DEMO_DATA_DIR / "radar.json"
TRACK_OUTPUT_PATH = DEMO_DATA_DIR / "track-record.json"
RECOMMENDATION_OUTPUT_PATH = DEMO_DATA_DIR / "recommendations.json"
TICKER_MASTER_OUTPUT_PATH = DEMO_DATA_DIR / "ticker-universe.json"
STOCK_REPORT_OUTPUT_PATH = DEMO_DATA_DIR / "stock-reports.json"
TODAY_CHANGES_OUTPUT_PATH = DEMO_DATA_DIR / "today-changes.json"
JOURNAL_OUTPUT_PATH = DEMO_DATA_DIR / "recommendation-journal.json"
LEDGER_PATH = ROOT / "artifacts" / "stockradar_demo.sqlite"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_public() -> dict[str, object]:
    """Build the fail-closed payloads that are safe to publish with the website."""

    ticker_payload = json.loads(TICKER_MASTER_FIXTURE_PATH.read_text(encoding="utf-8"))
    reference = dict(ticker_payload.get("internal_reference", {}))
    snapshot = {
        "snapshot_id": reference.get("snapshot_id", "UNAVAILABLE"),
        "as_of": reference.get("as_of"),
        "exchange": "HOSE",
        "data_grade": "REFERENCE_ONLY",
    }
    securities = sorted(
        (
            item
            for item in ticker_payload.get("items", [])
            if str(item.get("ticker", "")).isalpha()
            and len(str(item.get("ticker", ""))) == 3
            and str(item.get("ticker", "")).isupper()
        ),
        key=lambda item: item["ticker"],
    )
    performance_summary = {
        "total_published": 0,
        "unactivated": 0,
        "open": 0,
        "closed": 0,
        "target_reached": 0,
        "stop_reached": 0,
        "profitable_closed": 0,
        "win_rate_pct": None,
        "average_gain_pct": None,
        "average_loss_pct": None,
        "average_closed_return_pct": None,
        "excludes_unactivated_from_win_rate": True,
    }
    payloads = {
        "radar.json": {
            "schema_version": "2.1.2",
            "status": "BLOCKED_DATA_GATE",
            "data_status": "BLOCKED_DATA_GATE",
            "is_top5_hose": False,
            "market_regime": "UNKNOWN",
            "snapshot": snapshot,
            "items": [],
        },
        "recommendations.json": {
            "schema_version": "2.1.2",
            "data_status": "BLOCKED_DATA_GATE",
            "recommendation_mode": RecommendationMode.RESEARCH_ONLY.value,
            "performance_method": "FIRST_POST_PUBLICATION_ELIGIBLE_BAR_TOUCH",
            "performance_summary": performance_summary,
            "new_recommendation_status": {
                "published": False,
                "message": "CHƯA PHÁT HÀNH",
            },
            "snapshot": snapshot,
            "items": [],
        },
        "ticker-universe.json": {
            "schema_version": "2.1.2",
            "snapshot_id": snapshot["snapshot_id"],
            "as_of": snapshot["as_of"],
            "full_universe": False,
            "data_grade": "REFERENCE_ONLY",
            "data_status": "BLOCKED_DATA_GATE",
            "public_scope": "REFERENCE_ONLY",
            "internal_reference": reference,
            "items": securities,
        },
        "stock-reports.json": {
            "schema_version": "2.1.2",
            "mode": RecommendationMode.RESEARCH_ONLY.value,
            "data_status": "BLOCKED_DATA_GATE",
            "items": [],
        },
        "today-changes.json": {
            "schema_version": "2.1.2",
            "data_status": "BLOCKED_DATA_GATE",
            "as_of": snapshot["as_of"],
            "items": [],
        },
        "recommendation-journal.json": {
            "schema_version": "2.1.2",
            "data_status": "BLOCKED_DATA_GATE",
            "items": [],
        },
        "track-record.json": {
            "schema_version": "2.1.2",
            "data_status": "BLOCKED_DATA_GATE",
            "rows": [],
        },
    }
    for filename, payload in payloads.items():
        write_json(PUBLIC_DATA_DIR / filename, payload)
    return {
        "status": "BLOCKED_DATA_GATE",
        "public_files": len(payloads),
        "lookup_items": len(securities),
        "reference_records": reference.get("record_count", 0),
        "output": str(PUBLIC_DATA_DIR),
    }


def build_demo() -> dict[str, object]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    snapshot = UniverseSnapshot.from_dict(fixture["snapshot"])
    candidates = [Candidate.from_dict(item) for item in fixture["candidates"]]
    recommendations = [Recommendation.from_dict(item) for item in fixture.get("recommendations", [])]
    ticker_master_payload = json.loads(TICKER_MASTER_FIXTURE_PATH.read_text(encoding="utf-8"))
    ticker_master = TickerMaster.from_dict(ticker_master_payload)
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
                "schema_version": "2.1.2",
                "is_mock": True,
                "notice": "Dữ liệu khuyến nghị mô phỏng; không gắn với cổ phiếu thật.",
                "recommendation_mode": RecommendationMode.RESEARCH_ONLY.value,
                "performance_method": "FIRST_POST_PUBLICATION_ELIGIBLE_BAR_TOUCH",
                "performance_summary": performance_summary,
                "new_recommendation_status": {
                    "published": False,
                    "message": "HÔM NAY KHÔNG CÓ KHUYẾN NGHỊ MỚI ĐẠT TIÊU CHUẨN."
                },
                "snapshot": snapshot.to_dict(),
                "items": [item.to_dict() for item in recommendations],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    TICKER_MASTER_OUTPUT_PATH.write_text(
        json.dumps(
            {
                **ticker_master.to_public_dict(),
                "public_scope": ticker_master_payload.get("public_scope", "REFERENCE_FIXTURE_ONLY"),
                "internal_reference": ticker_master_payload.get("internal_reference", {}),
                "notice": ticker_master_payload["notice"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    horizon_defaults = {
        "SHORT_TERM": ("CHƯA ĐỦ DỮ LIỆU", "Chờ giá, volume và thiết lập đạt chuẩn.", "INTRADAY"),
        "MEDIUM_TERM": ("CHƯA ĐỦ DỮ LIỆU", "Chờ snapshot cuối phiên và dữ liệu tăng trưởng.", "EOD"),
        "LONG_TERM": ("CHƯA ĐỦ DỮ LIỆU", "Chờ dữ liệu doanh nghiệp và định giá được cấp quyền.", "EOD_OR_EVENT"),
        "ACCUMULATION": ("CHƯA ĐỦ ĐIỀU KIỆN ĐÁNH GIÁ", "Chờ BCTC, quản trị và biên an toàn.", "PERIODIC_OR_EVENT"),
    }
    stock_reports = []
    for security in ticker_master.securities():
        views = [
            {
                "horizon": horizon,
                "assessment": assessment,
                "summary": summary,
                "freshness": freshness,
                "evaluated_at": None,
                "data_status": "INSUFFICIENT",
            }
            for horizon, (assessment, summary, freshness) in horizon_defaults.items()
        ]
        report = {
            "ticker": security.ticker,
            "company_name": security.company_name,
            "sector": security.sector,
            "snapshot_id": ticker_master.snapshot_id,
            "updated_at": ticker_master.as_of,
            "data_status": "BLOCKED_NO_LICENSED_DATA",
            "current_price": None,
            "rank": None,
            "sector_rank": None,
            "score": None,
            "horizon_views": views,
            "new_position_state": "CHƯA ĐỦ DỮ LIỆU",
            "new_position_note": "Không tạo vùng mua khi dữ liệu chưa đạt chuẩn.",
            "holding_state": "CHƯA ĐỦ DỮ LIỆU",
            "holding_note": "Không suy luận phải giữ/bán khi chưa có bằng chứng phù hợp.",
            "reasons": ["Ticker có trong fixture lookup; chưa có snapshot thị trường được cấp quyền."],
            "risks": ["Không dùng fixture này cho quyết định đầu tư."],
            "deep_report_available": False,
            "recommendation_ids": [],
            "is_mock": True,
        }
        if security.ticker == "DEMO1":
            report.update({
                "data_status": "MOCK",
                "current_price": 51.2,
                "rank": 1,
                "sector_rank": 1,
                "score": 91,
                "new_position_state": "CHỜ CỔNG KHUYẾN NGHỊ",
                "new_position_note": "Record đã kích hoạt không tự biến thành điểm mua mới.",
                "holding_state": "TIẾP TỤC THEO DÕI",
                "holding_note": "Theo dõi mục tiêu 60,0 và điều kiện vô hiệu 49,0.",
                "reasons": [
                    "Nền giá VCP co hẹp trong fixture mô phỏng.",
                    "Khối lượng và sức mạnh tương đối được tách thành evidence riêng.",
                    "Giá không bị chọn lại sau khi biết kết quả.",
                ],
                "risks": ["Market Regime mô phỏng đang VÀNG.", "Toàn bộ dữ liệu là MOCK/SHADOW."],
                "deep_report_available": True,
                "recommendation_ids": ["REC-DEMO1-SHORT-20260827"],
                "horizon_views": [
                    {"horizon": "SHORT_TERM", "assessment": "ĐANG CÓ HIỆU LỰC", "summary": "Record mô phỏng đã kích hoạt; không suy diễn thành điểm mua mới.", "freshness": "INTRADAY", "evaluated_at": "2026-09-01T14:15:00+07:00", "data_status": "MOCK"},
                    {"horizon": "MEDIUM_TERM", "assessment": "THEO DÕI", "summary": "Cần thêm xác nhận tăng trưởng và dòng tiền trung hạn.", "freshness": "EOD", "evaluated_at": "2026-09-01T15:00:00+07:00", "data_status": "MOCK"},
                    {"horizon": "LONG_TERM", "assessment": "TRUNG TÍNH", "summary": "Fixture chưa có đủ lịch sử chất lượng và định giá dài hạn.", "freshness": "EOD_OR_EVENT", "evaluated_at": "2026-08-31T15:00:00+07:00", "data_status": "MOCK"},
                    {"horizon": "ACCUMULATION", "assessment": "CHỜ VÙNG GIÁ", "summary": "Không áp stop kỹ thuật ngắn hạn cho mục tiêu tích sản.", "freshness": "PERIODIC_OR_EVENT", "evaluated_at": "2026-08-31T15:00:00+07:00", "data_status": "MOCK"},
                ],
            })
        stock_reports.append(report)

    STOCK_REPORT_OUTPUT_PATH.write_text(
        json.dumps(
            {
                "schema_version": "2.1.2",
                "mode": "RESEARCH_ONLY",
                "is_mock": True,
                "notice": "Lookup UI fixture; báo cáo sâu production cần security master và dữ liệu được cấp quyền.",
                "items": sorted(stock_reports, key=lambda item: item["ticker"]),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    journal = []
    for recommendation in recommendations:
        journal.append({
            "event_id": f"{recommendation.recommendation_id}-PUBLISHED",
            "recommendation_id": recommendation.recommendation_id,
            "ticker": recommendation.ticker,
            "timestamp": recommendation.published_at,
            "previous_state": None,
            "new_state": "UNACTIVATED",
            "event_type": "PUBLISHED",
            "old_value": None,
            "new_value": recommendation.price_at_publication,
            "reason": "Recommendation Gate đã qua trong fixture mô phỏng.",
            "snapshot_id": recommendation.snapshot_id,
            "system_version": recommendation.system_version,
            "created_by": "SYSTEM",
            "audit_reference": f"AUDIT-{recommendation.recommendation_id}-PUB",
        })
        if recommendation.is_activated:
            journal.append({
                "event_id": f"{recommendation.recommendation_id}-ACTIVATED",
                "recommendation_id": recommendation.recommendation_id,
                "ticker": recommendation.ticker,
                "timestamp": recommendation.activation_timestamp,
                "previous_state": "UNACTIVATED",
                "new_state": "ACTIVE",
                "event_type": "ACTIVATED",
                "old_value": None,
                "new_value": recommendation.performance_entry_price,
                "reason": "Lần chạm vùng mua hợp lệ đầu tiên sau công bố.",
                "snapshot_id": recommendation.snapshot_id,
                "system_version": recommendation.system_version,
                "created_by": "SYSTEM",
                "audit_reference": f"AUDIT-{recommendation.recommendation_id}-ACT",
            })
        if recommendation.is_closed:
            journal.append({
                "event_id": f"{recommendation.recommendation_id}-CLOSED",
                "recommendation_id": recommendation.recommendation_id,
                "ticker": recommendation.ticker,
                "timestamp": recommendation.close_timestamp,
                "previous_state": "ACTIVE",
                "new_state": recommendation.recommendation_state.value,
                "event_type": "CLOSED",
                "old_value": recommendation.performance_entry_price,
                "new_value": recommendation.close_price,
                "reason": recommendation.close_reason or "Đóng theo lifecycle mô phỏng.",
                "snapshot_id": recommendation.snapshot_id,
                "system_version": recommendation.system_version,
                "created_by": "SYSTEM",
                "audit_reference": f"AUDIT-{recommendation.recommendation_id}-CLOSE",
            })
    JOURNAL_OUTPUT_PATH.write_text(
        json.dumps({"schema_version": "2.1.2", "is_mock": True, "items": journal}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    TODAY_CHANGES_OUTPUT_PATH.write_text(
        json.dumps(
            {
                "schema_version": "2.1.2",
                "is_mock": True,
                "as_of": snapshot.as_of,
                "notice": "Thay đổi mô phỏng để kiểm thử view 30–60 giây.",
                "items": [
                    {"event_id": "CHANGE-001", "ticker": "DEMO3", "event_type": "STATE_CHANGED", "occurred_at": "2026-09-01T14:15:00+07:00", "title": "DEMO3 · Trung hạn", "previous_value": "ĐẠT VÙNG MUA", "new_value": "TĂNG QUÁ VÙNG MUA", "summary": "Mua mới không phù hợp; người đang nắm giữ tiếp tục theo dõi luận điểm.", "importance": 3},
                    {"event_id": "CHANGE-002", "ticker": "DEMO2", "event_type": "SCORE_CHANGED", "occurred_at": "2026-09-01T13:30:00+07:00", "title": "DEMO2 · Ngắn hạn", "previous_value": "84", "new_value": "88", "summary": "Điểm tăng nhưng Recommendation Gate vẫn chưa kích hoạt.", "importance": 2},
                    {"event_id": "CHANGE-003", "ticker": None, "event_type": "MARKET_REGIME_CHANGED", "occurred_at": "2026-09-01T11:15:00+07:00", "title": "Market Regime", "previous_value": "XANH", "new_value": "VÀNG", "summary": "Giảm mức chấp nhận rủi ro trong fixture; không phải trạng thái thị trường thật.", "importance": 3},
                ],
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
            if recommendation.review_due_at:
                ledger.append_review_schedule(
                    recommendation.recommendation_id,
                    recommendation.review_due_at,
                    recommendation.review_status.value,
                )
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
    parser = argparse.ArgumentParser(description="StockRadar V2.1.2 utility")
    parser.add_argument("command", choices=["build-public", "build-demo"])
    args = parser.parse_args()
    if args.command == "build-public":
        print(json.dumps(build_public(), ensure_ascii=False))
    else:
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
