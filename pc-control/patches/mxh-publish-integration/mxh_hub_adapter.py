from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
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
    """Loopback-only V7 adapter to the existing Hub/MXH publisher.

    No MXH GUI automation is used. The adapter deliberately reuses Hub plan,
    mutation guard, idempotency, native scheduling and provider receipt logic.
    """

    def __init__(self, base_url: str = HUB_BASE_URL, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        if base_url.rstrip("/") != HUB_BASE_URL:
            raise MxhHubError("MXH_HUB_HOST_NOT_ALLOWED")
        self.base_url = HUB_BASE_URL
        self.timeout = max(1, min(int(timeout), 120))

    def execute(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if action == "status":
            return {"ok": True, "action": action, "result": self.status()}
        if action == "readiness":
            return {"ok": True, "action": action, "result": self.readiness(int(arguments.get("limit", 20)))}
        if action == "list_edited":
            rows = [asdict(item) for item in self.edited_videos(int(arguments.get("limit", 200)))]
            return {"ok": True, "action": action, "result": {"entries": rows}}
        if action == "resolve_title":
            item = self.resolve_exact_title(str(arguments.get("title", "")), limit=int(arguments.get("limit", 200)))
            return {"ok": True, "action": action, "result": asdict(item)}
        if action == "content_readback":
            result = self.read_content(str(arguments.get("video_sha256", "")), int(arguments.get("flow_id", 0)))
            return {"ok": True, "action": action, "result": result}
        if action == "plan_readback":
            result = self.read_plan(str(arguments.get("plan_id", "")), summary=True)
            return {"ok": True, "action": action, "result": result}
        if action == "job_readback":
            result = self.job(str(arguments.get("job_id", "")))
            return {"ok": True, "action": action, "result": result}
        if action == "schedule_exact_title":
            result = self.schedule_exact_title(
                title=str(arguments.get("title", "")),
                flow_id=int(arguments.get("flow_id", 0)),
                platforms=tuple(arguments.get("platforms") or ()),
                scheduled_at=str(arguments.get("scheduled_at", "")),
                timezone_name=str(arguments.get("timezone") or DEFAULT_TIMEZONE),
                caption=(None if arguments.get("caption") is None else str(arguments.get("caption"))),
                hashtags=str(arguments.get("hashtags") or ""),
                timeout_seconds=int(arguments.get("timeout_seconds", 1200)),
                wait_seconds=float(arguments.get("wait_seconds", 10)),
            )
            return {"ok": True, "action": action, "result": result}
        if action == "create_or_reuse_plan":
            req = ScheduleRequest(
                artifact_job_id=str(arguments.get("artifact_job_id", "")),
                title=str(arguments.get("title", "")),
                caption=str(arguments.get("caption", "")),
                hashtags=str(arguments.get("hashtags", "")),
                platforms=tuple(arguments.get("platforms") or ()),
                flow_id=int(arguments.get("flow_id", 0)),
                scheduled_at=str(arguments.get("scheduled_at", "")),
                timezone=str(arguments.get("timezone") or DEFAULT_TIMEZONE),
            )
            result = self.create_or_reuse_plan(
                req,
                idempotency_key=str(arguments.get("idempotency_key") or self.stable_key(
                    req.artifact_job_id, req.title, str(req.flow_id), req.scheduled_at
                )),
            )
            return {"ok": True, "action": action, "result": result}
        if action == "native_schedule":
            result = self.native_schedule(
                str(arguments.get("plan_id", "")),
                tuple(arguments.get("platforms") or ()),
                idempotency_key=str(arguments.get("idempotency_key") or self.stable_key(
                    str(arguments.get("plan_id", "")),
                    ",".join(sorted(str(p) for p in arguments.get("platforms") or ())),
                    "native_schedule",
                )),
                timeout_seconds=int(arguments.get("timeout_seconds", 1200)),
            )
            return {"ok": True, "action": action, "result": result}
        raise MxhHubError("MXH_ACTION_INVALID")

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
                return json.loads(raw) if "json" in ctype else raw
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

    def readiness(self, limit: int = 20) -> dict[str, Any]:
        snapshot = self.status()
        videos = self.edited_videos(max(1, min(int(limit), 50)))
        return {
            "bridge": "V7_HUB_DIRECT_V2",
            "hub_ready": True,
            "catalog_ready": True,
            "edited_count": len(videos),
            "sample_titles": [item.title for item in videos[:5]],
            "hub": snapshot.get("hub"),
            "capabilities": snapshot.get("capabilities"),
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
            title = str(
                entry.get("title")
                or entry.get("publishTitle")
                or entry.get("caption")
                or self._title_from_filename(name)
            ).strip()
            if artifact_id and path and name and len(sha) == 64:
                videos.append(EditedVideo(artifact_id, path, name, sha, title))
        return videos

    def resolve_exact_title(self, title: str, *, limit: int = 200) -> EditedVideo:
        wanted = title.strip()
        if not wanted:
            raise MxhHubError("MXH_TITLE_REQUIRED")
        matches: list[EditedVideo] = []
        for item in self.edited_videos(limit):
            candidates = {item.title.strip(), self._title_from_filename(item.name)}
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
        token = str(self._request("GET", "/api/dashboard/csrf")).strip()
        if len(token) < 8 or len(token) > 256:
            raise MxhHubError("MXH_CSRF_INVALID")
        return token

    def create_or_reuse_plan(self, request: ScheduleRequest, *, idempotency_key: str) -> dict[str, Any]:
        self._validate_flow(request.flow_id)
        platforms = self._platforms(request.platforms, request.flow_id)
        title = self._clean_text(request.title, "title", 1, 160)
        caption = self._clean_text(request.caption, "caption", 1, 2200)
        hashtags = self._clean_text(request.hashtags, "hashtags", 0, 800)
        scheduled_at = self._validate_iso(request.scheduled_at)
        timezone_name = self._bounded(request.timezone, "timezone", 1, 80)
        artifact_job_id = self._bounded(request.artifact_job_id, "artifact_job_id", 1, 128)
        key = self._bounded(idempotency_key, "idempotency_key", 8, 160)
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
            headers={"idempotency-key": key, "x-hub-csrf": self._csrf()},
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
                "x-hub-csrf": self._csrf(),
            },
        )

    def schedule_exact_title(
        self,
        *,
        title: str,
        flow_id: int,
        platforms: Iterable[str],
        scheduled_at: str,
        timezone_name: str = DEFAULT_TIMEZONE,
        caption: str | None = None,
        hashtags: str = "",
        timeout_seconds: int = 1200,
        wait_seconds: float = 10,
    ) -> dict[str, Any]:
        """Resolve one edited video by exact title and schedule it through Hub.

        This is the fast path used by V7. It never automates the MXH GUI, never
        retries a platform already verified by Hub, and never reports success
        without authoritative plan readback.
        """
        self._validate_flow(flow_id)
        requested = self._platforms(platforms, flow_id)
        video = self.resolve_exact_title(title)
        normalized_schedule = self._validate_iso(scheduled_at)

        content = self.read_content(video.sha256, flow_id)
        content_title = self._find_text(content, ("title", "publishTitle", "publish_title"))
        if content_title and content_title.casefold() != video.title.casefold():
            raise MxhHubError("MXH_CONTENT_TITLE_MISMATCH")
        resolved_caption = caption
        if resolved_caption is None:
            resolved_caption = self._find_text(content, ("caption", "publishCaption", "publish_caption"))
        if not resolved_caption:
            resolved_caption = video.title

        request = ScheduleRequest(
            artifact_job_id=video.artifact_job_id,
            title=video.title,
            caption=resolved_caption,
            hashtags=hashtags,
            platforms=requested,
            flow_id=flow_id,
            scheduled_at=normalized_schedule,
            timezone=timezone_name,
        )
        plan_key = self.stable_key(
            "direct-v2",
            video.sha256,
            str(flow_id),
            normalized_schedule,
            ",".join(requested),
            video.title,
        )
        plan = self.create_or_reuse_plan(request, idempotency_key=plan_key)
        plan_id = self._extract_identifier(plan, ("id", "planId", "plan_id"))
        if not plan_id:
            raise MxhHubError("MXH_PLAN_ID_MISSING")

        before = self.read_plan(plan_id, summary=True)
        verified_before = self.verified_platforms(before)
        missing = tuple(platform for platform in requested if platform not in verified_before)
        if not missing:
            return {
                "status": "SCHEDULED_VERIFIED",
                "schedule_verified": True,
                "submitted": False,
                "video": {
                    "artifact_job_id": video.artifact_job_id,
                    "title": video.title,
                    "sha256": video.sha256,
                },
                "flow_id": flow_id,
                "plan_id": plan_id,
                "requested_platforms": list(requested),
                "verified_platforms": sorted(verified_before),
                "submitted_platforms": [],
                "job_id": None,
                "job_state": None,
            }

        native_key = self.stable_key(
            "direct-v2-native",
            plan_id,
            ",".join(missing),
            normalized_schedule,
        )
        job_receipt = self.native_schedule(
            plan_id,
            missing,
            idempotency_key=native_key,
            timeout_seconds=timeout_seconds,
        )
        job_id = self._extract_identifier(job_receipt, ("id", "jobId", "job_id"))
        job_snapshot: Any = job_receipt
        job_state = self._job_state(job_snapshot)
        wait_for = max(0.0, min(float(wait_seconds), 30.0))
        deadline = time.monotonic() + wait_for
        terminal = {"succeeded", "success", "done", "completed", "failed", "error", "cancelled", "canceled"}

        while job_id and wait_for > 0 and job_state not in terminal and time.monotonic() < deadline:
            time.sleep(min(0.75, max(0.05, deadline - time.monotonic())))
            job_snapshot = self.job(job_id)
            job_state = self._job_state(job_snapshot)

        after = self.read_plan(plan_id, summary=True)
        verified_after = self.verified_platforms(after)
        is_verified = all(platform in verified_after for platform in requested)
        failed = job_state in {"failed", "error", "cancelled", "canceled"}
        status = "SCHEDULED_VERIFIED" if is_verified else ("FAILED" if failed else "SUBMITTED_UNVERIFIED")
        return {
            "status": status,
            "schedule_verified": is_verified,
            "submitted": True,
            "video": {
                "artifact_job_id": video.artifact_job_id,
                "title": video.title,
                "sha256": video.sha256,
            },
            "flow_id": flow_id,
            "plan_id": plan_id,
            "requested_platforms": list(requested),
            "verified_platforms": sorted(verified_after),
            "submitted_platforms": list(missing),
            "job_id": job_id,
            "job_state": job_state,
        }

    def job(self, job_id: str) -> dict[str, Any]:
        job_id = self._bounded(job_id, "job_id", 1, 128)
        result = self._request("GET", f"/api/jobs/{urllib.parse.quote(job_id, safe='')}")
        if not isinstance(result, dict):
            raise MxhHubError("MXH_JOB_READBACK_INVALID")
        return result

    @staticmethod
    def verified_platforms(plan_summary: Any) -> set[str]:
        if not isinstance(plan_summary, dict):
            return set()
        rows: Any = plan_summary.get("platforms")
        if isinstance(rows, list) and rows and all(isinstance(row, str) for row in rows):
            rows = None
        if not isinstance(rows, list):
            native = plan_summary.get("nativeSchedules") or plan_summary.get("native_schedule_json")
            rows = native.get("platforms") if isinstance(native, dict) else None
        if not isinstance(rows, list):
            return set()
        verified: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            platform = str(row.get("platform") or "").lower()
            status = str(row.get("status") or "").lower()
            if status == "scheduled" and row.get("scheduleVerified") is True:
                verified.add(platform)
        return verified

    @classmethod
    def schedule_verified(cls, plan_summary: Any, required_platforms: Iterable[str]) -> bool:
        verified = cls.verified_platforms(plan_summary)
        return all(str(platform).lower() in verified for platform in required_platforms)

    @classmethod
    def _extract_identifier(cls, payload: Any, keys: tuple[str, ...]) -> str | None:
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, (str, int)) and str(value).strip():
                    return str(value).strip()
            for key in ("plan", "job", "result", "data"):
                nested = payload.get(key)
                found = cls._extract_identifier(nested, keys)
                if found:
                    return found
        return None

    @classmethod
    def _job_state(cls, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("status", "state"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().lower()
            for key in ("job", "result", "data"):
                state = cls._job_state(payload.get(key))
                if state:
                    return state
        return None

    @classmethod
    def _find_text(cls, payload: Any, keys: tuple[str, ...]) -> str | None:
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in payload.values():
                found = cls._find_text(value, keys)
                if found:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = cls._find_text(value, keys)
                if found:
                    return found
        return None

    @staticmethod
    def stable_key(*parts: str) -> str:
        canonical = "|".join(part.strip() for part in parts)
        return "v7-mxh-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:40]

    @staticmethod
    def flow1_time(flow2_iso: str, days: int = 2) -> str:
        instant = datetime.fromisoformat(flow2_iso.replace("Z", "+00:00"))
        return (instant + timedelta(days=max(2, int(days)))).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _title_from_filename(name: str) -> str:
        value = str(name).removesuffix(".mp4")
        if "__" in value:
            parts = value.split("__")
            if len(parts) >= 2 and parts[0].replace("-", "").isdigit():
                value = parts[1]
        for suffix in ("__edited", "_edited", " - edited"):
            if value.casefold().endswith(suffix.casefold()):
                value = value[: -len(suffix)]
        return value.strip()

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
        if name in {"title", "caption"} and ("__edited" in lowered or "__final" in lowered):
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
    def _validate_iso(value: str) -> str:
        text = str(value).strip()
        try:
            instant = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MxhHubError("MXH_SCHEDULE_INVALID") from exc
        if instant.tzinfo is None:
            raise MxhHubError("MXH_SCHEDULE_OFFSET_REQUIRED")
        return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
