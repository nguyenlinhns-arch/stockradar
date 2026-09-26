from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

HUB_BASE_URL = "http://127.0.0.1:4310"
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
ALLOWED_PLATFORMS = ("tiktok", "facebook", "youtube")
DEFAULT_TIMEOUT_SECONDS = 20


class MxhHubError(RuntimeError):
    pass


@dataclass(frozen=True)
class EditedVideo:
    artifact_job_id: str
    path: str
    name: str
    sha256: str
    title: str


@dataclass(frozen=True)
class ScheduleRequest:
    artifact_job_id: str
    title: str
    caption: str
    hashtags: str
    platforms: tuple[str, ...]
    flow_id: int
    scheduled_at: str
    timezone: str = DEFAULT_TIMEZONE


class MxhHubAdapter:
    """Loopback-only adapter from V7 to the existing Hub/MXH publisher.

    It does not launch MXH Video Tools, does not use UI automation, and never
    accepts an arbitrary host. All write actions reuse Hub CSRF, idempotency,
    plan, mutation-guard and provider receipt enforcement.
    """

    def __init__(self, base_url: str = HUB_BASE_URL, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        if base_url.rstrip("/") != HUB_BASE_URL:
            raise MxhHubError("MXH_HUB_HOST_NOT_ALLOWED")
        self.base_url = HUB_BASE_URL
        self.timeout = max(1, min(int(timeout), 120))

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        if not path.startswith("/"):
            raise MxhHubError("MXH_HUB_PATH_INVALID")
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers = {"accept": "application/json"}
        if payload is not None:
            request_headers["content-type"] = "application/json; charset=utf-8"
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                ctype = response.headers.get("content-type", "")
                if "json" in ctype:
                    return json.loads(raw)
                return raw
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw).get("error", raw)
            except Exception:
                detail = raw
            raise MxhHubError(f"HUB_HTTP_{exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise MxhHubError(f"HUB_UNAVAILABLE: {exc.reason}") from exc

    def status(self) -> dict[str, Any]:
        return {
            "hub": self._request("GET", "/api/status"),
            "workflows": self._request("GET", "/api/workflows"),
            "capabilities": self._request("GET", "/api/capabilities"),
        }

    def edited_videos(self, limit: int = 200) -> list[EditedVideo]:
        limit = max(1, min(int(limit), 500))
        result = self._request("GET", f"/api/mxh-video-tools/edited-videos?limit={limit}")
        entries = result.get("entries", []) if isinstance(result, dict) else []
        videos: list[EditedVideo] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            artifact_id = str(entry.get("id") or "").strip()
            path = str(entry.get("path") or "").strip()
            name = str(entry.get("name") or "").strip()
            sha = str(entry.get("sha256") or "").strip().lower()
            title = str(entry.get("title") or entry.get("publishTitle") or name).strip()
            if artifact_id and path and name and len(sha) == 64:
                videos.append(EditedVideo(artifact_id, path, name, sha, title))
        return videos

    def resolve_exact_title(self, title: str, *, limit: int = 200) -> EditedVideo:
        wanted = title.strip()
        if not wanted:
            raise MxhHubError("MXH_TITLE_REQUIRED")
        matches = []
        for item in self.edited_videos(limit):
            normalized_name = item.name
            for suffix in (".mp4", "__edited", "_edited", " - edited"):
                if normalized_name.casefold().endswith(suffix.casefold()):
                    normalized_name = normalized_name[: -len(suffix)]
            candidates = {item.title.strip(), normalized_name.strip()}
            if wanted.casefold() in {value.casefold() for value in candidates if value}:
                matches.append(item)
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise MxhHubError("MXH_VIDEO_NOT_FOUND")
        hashes = {item.sha256 for item in matches}
        if len(hashes) > 1:
            raise MxhHubError("MXH_VIDEO_AMBIGUOUS_TITLE")
        return sorted(matches, key=lambda item: item.path)[0]

    def read_content(self, video_sha256: str, flow_id: int) -> Any:
        self._validate_sha(video_sha256)
        self._validate_flow(flow_id)
        query = urllib.parse.urlencode({"video_sha256": video_sha256, "flow_id": flow_id})
        return self._request("GET", f"/api/gpt-control?{query}")

    def read_plan(self, plan_id: str, *, summary: bool = True) -> Any:
        plan_id = self._bounded(plan_id, "plan_id", 1, 128)
        query = urllib.parse.urlencode({"plan_id": plan_id, **({"view": "summary"} if summary else {})})
        return self._request("GET", f"/api/gpt-control?{query}")

    def _csrf(self) -> str:
        value = self._request("GET", "/api/dashboard/csrf")
        token = str(value).strip()
        if len(token) < 8 or len(token) > 256:
            raise MxhHubError("MXH_CSRF_INVALID")
        return token

    def create_or_reuse_plan(self, request: ScheduleRequest, *, idempotency_key: str) -> dict[str, Any]:
        self._validate_flow(request.flow_id)
        platforms = self._platforms(request.platforms, request.flow_id)
        title = self._clean_text(request.title, "title", 1, 160)
        caption = self._clean_text(request.caption, "caption", 1, 2200)
        hashtags = self._clean_text(request.hashtags, "hashtags", 0, 800)
        scheduled_at = self._validate_iso_future(request.scheduled_at)
        timezone_name = self._bounded(request.timezone, "timezone", 1, 80)
        artifact_job_id = self._bounded(request.artifact_job_id, "artifact_job_id", 1, 128)
        key = self._bounded(idempotency_key, "idempotency_key", 8, 160)
        csrf = self._csrf()
        return self._request(
            "POST",
            "/api/video-publish/plans",
            body={
                "artifactJobId": artifact_job_id,
                "title": title,
                "caption": caption,
                "hashtags": hashtags,
                "titleLocked": True,
                "captionLocked": True,
                "platforms": list(platforms),
                "flowId": request.flow_id,
                "scheduledAt": scheduled_at,
                "timezone": timezone_name,
            },
            headers={"idempotency-key": key, "x-hub-csrf": csrf},
        )

    def native_schedule(
        self,
        plan_id: str,
        platforms: Iterable[str],
        *,
        idempotency_key: str,
        timeout_seconds: int = 1200,
    ) -> dict[str, Any]:
        plan_id = self._bounded(plan_id, "plan_id", 1, 128)
        requested = tuple(str(p).strip().lower() for p in platforms)
        if not requested:
            raise MxhHubError("MXH_PLATFORM_REQUIRED")
        for platform in requested:
            if platform not in ALLOWED_PLATFORMS:
                raise MxhHubError("MXH_PLATFORM_INVALID")
        key = self._bounded(idempotency_key, "idempotency_key", 8, 160)
        csrf = self._csrf()
        return self._request(
            "POST",
            "/api/jobs",
            body={
                "workflowId": "video.native_schedule",
                "mode": "live",
                "input": {
                    "planId": plan_id,
                    "platforms": list(requested),
                    "resumeIfMissing": True,
                    "timeoutSeconds": max(30, min(int(timeout_seconds), 1200)),
                },
            },
            headers={
                "idempotency-key": key,
                "x-hub-ui-intent": "user-content",
                "x-hub-csrf": csrf,
            },
        )

    def job(self, job_id: str) -> dict[str, Any]:
        job_id = self._bounded(job_id, "job_id", 1, 128)
        result = self._request("GET", f"/api/jobs/{urllib.parse.quote(job_id, safe='')}")
        if not isinstance(result, dict):
            raise MxhHubError("MXH_JOB_READBACK_INVALID")
        return result

    @staticmethod
    def schedule_verified(plan_summary: Any, required_platforms: Iterable[str]) -> bool:
        if not isinstance(plan_summary, dict):
            return False
        platforms = plan_summary.get("platforms")
        if not isinstance(platforms, list):
            native = plan_summary.get("nativeSchedules") or plan_summary.get("native_schedule_json")
            if isinstance(native, dict):
                platforms = native.get("platforms")
        if not isinstance(platforms, list):
            return False
        verified: set[str] = set()
        for row in platforms:
            if not isinstance(row, dict):
                continue
            platform = str(row.get("platform") or "").lower()
            status = str(row.get("status") or "").lower()
            schedule_verified = row.get("scheduleVerified")
            if status == "scheduled" and schedule_verified is True:
                verified.add(platform)
        return all(str(platform).lower() in verified for platform in required_platforms)

    @staticmethod
    def stable_key(*parts: str) -> str:
        canonical = "|".join(part.strip() for part in parts)
        return "v7-mxh-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:40]

    @staticmethod
    def flow1_time(flow2_iso: str, days: int = 2) -> str:
        instant = datetime.fromisoformat(flow2_iso.replace("Z", "+00:00"))
        return (instant + timedelta(days=max(2, int(days)))).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _validate_sha(value: str) -> None:
        value = value.strip().lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise MxhHubError("MXH_SHA256_INVALID")

    @staticmethod
    def _validate_flow(value: int) -> None:
        if value not in (1, 2):
            raise MxhHubError("MXH_FLOW_INVALID")

    @staticmethod
    def _bounded(value: str, name: str, minimum: int, maximum: int) -> str:
        text = str(value).strip()
        if len(text) < minimum or len(text) > maximum:
            raise MxhHubError(f"MXH_{name.upper()}_INVALID")
        return text

    @classmethod
    def _clean_text(cls, value: str, name: str, minimum: int, maximum: int) -> str:
        text = cls._bounded(value, name, minimum, maximum) if minimum else str(value).strip()
        if len(text) > maximum:
            raise MxhHubError(f"MXH_{name.upper()}_TOO_LONG")
        if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in text):
            raise MxhHubError(f"MXH_{name.upper()}_CONTROL_CHAR")
        lowered = text.casefold()
        if name in {"title", "caption"} and ("__edited" in lowered or "yyyy" in lowered):
            raise MxhHubError("MXH_TECHNICAL_METADATA_BLOCKED")
        return text

    @staticmethod
    def _platforms(values: Iterable[str], flow_id: int) -> tuple[str, ...]:
        result: list[str] = []
        for raw in values:
            platform = str(raw).strip().lower()
            if platform not in ALLOWED_PLATFORMS:
                raise MxhHubError("MXH_PLATFORM_INVALID")
            if platform not in result:
                result.append(platform)
        if not result:
            raise MxhHubError("MXH_PLATFORM_REQUIRED")
        if flow_id != 2 and "youtube" in result:
            raise MxhHubError("MXH_YOUTUBE_FLOW2_ONLY")
        return tuple(result)

    @staticmethod
    def _validate_iso_future(value: str) -> str:
        text = str(value).strip()
        try:
            instant = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MxhHubError("MXH_SCHEDULE_INVALID") from exc
        if instant.tzinfo is None:
            raise MxhHubError("MXH_SCHEDULE_OFFSET_REQUIRED")
        return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
