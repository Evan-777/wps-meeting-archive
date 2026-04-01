from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from .config import AppConfig
from .meeting_client import WpsOpenApiClient
from .people_inference import infer_people_names
from .state import SyncState
from .tag_inference import infer_tags
from .title_parser import ParsedTitle, parse_meeting_title
from .topic_extractor import extract_topic_from_recording_content
from .utils import format_date_yyyy_mm_dd, get_by_path, parse_datetime, utc_now
from .webhook import WebhookClient


@dataclass
class SyncSummary:
    seen: int = 0
    skipped: int = 0
    upserted: int = 0
    finalized: int = 0


class ArchiveSyncService:
    def __init__(self, config: AppConfig, api_client: WpsOpenApiClient, webhook_client: WebhookClient):
        self.config = config
        self.api_client = api_client
        self.webhook_client = webhook_client
        self._user_name_cache: dict[str, str] = {}

    def sync_pending(self, state: SyncState, dry_run: bool = False) -> SyncSummary:
        summary = SyncSummary()
        since = self._compute_since(state)
        meetings = self.api_client.list_meetings(since)
        seen_meeting_ids: set[str] = set()

        for meeting in meetings:
            summary.seen += 1
            candidate = self._build_candidate(meeting)
            if candidate is None:
                summary.skipped += 1
                continue
            if candidate["meetingId"] in seen_meeting_ids:
                summary.skipped += 1
                continue
            seen_meeting_ids.add(candidate["meetingId"])
            if dry_run:
                summary.upserted += 1
                continue
            self.webhook_client.call(
                self.config.airscript.upsert_pending_archive_webhook,
                candidate,
            )
            summary.upserted += 1

        state.last_sync_at = utc_now().isoformat()
        return summary

    def finalize_confirmed(self, dry_run: bool = False) -> SyncSummary:
        summary = SyncSummary()
        if dry_run:
            return summary
        self.webhook_client.call(self.config.airscript.finalize_pending_archive_webhook, {})
        summary.finalized = 1
        return summary

    def _compute_since(self, state: SyncState) -> str:
        if state.last_sync_at:
            dt = parse_datetime(state.last_sync_at)
        else:
            dt = utc_now()
        if dt is None:
            dt = utc_now()
        dt = dt - timedelta(days=self.config.meetings.safe_lookback_days)
        return dt.isoformat()

    def _build_candidate(self, meeting: dict[str, Any]) -> dict[str, Any] | None:
        fields = self.config.meetings.meeting_fields
        meeting_id = get_by_path(meeting, fields.id, "")
        if not meeting_id:
            return None

        detail = self.api_client.get_meeting_detail(str(meeting_id))
        title = get_by_path(detail, fields.title, "") or get_by_path(meeting, fields.title, "")
        created_at = get_by_path(detail, fields.created_at, "")
        start_time = get_by_path(detail, fields.start_time, "")
        initiator_user_id = str(get_by_path(detail, fields.initiator_user_id, ""))

        if not meeting_id or not title:
            return None
        mentor_user_id = self.config.meetings.mentor_user_id
        if mentor_user_id and initiator_user_id and initiator_user_id != mentor_user_id:
            return None

        minutes = self.api_client.list_minutes(str(meeting_id))
        minute = self._pick_ready_minute(minutes)
        recordings = self.api_client.list_recordings(str(meeting_id))
        recording = self._pick_recording(recordings)
        if minute is None and recording is None:
            return None

        parsed = parse_meeting_title(title, exclude_people=self.config.archive.exclude_people)
        participants = self.api_client.list_participants(str(meeting_id))
        resolved_participant_names = self._resolve_participant_names(participants)
        inferred_topic = ""
        if not parsed.has_structured_title and recording is not None:
            inferred_topic = self._extract_topic_from_recording_content(str(meeting_id), str(recording.get("id", "")))

        suggested_topic = parsed.suggested_topic if parsed.has_structured_title else inferred_topic
        inferred_people_names = infer_people_names(
            title=title,
            topic=suggested_topic,
            mapping=self.config.archive.topic_people_mapping,
        )
        suggested_people_names = (
            parsed.suggested_people_names
            or resolved_participant_names
            or inferred_people_names
        )
        suggested_tags = infer_tags(title=title, topic=suggested_topic)

        return {
            "meetingId": str(meeting_id),
            "meetingTitle": title,
            "meetingDate": format_date_yyyy_mm_dd(start_time or created_at),
            "meetingLink": self._pick_link(recording, minute),
            "suggestedPeopleNames": suggested_people_names,
            "suggestedTopic": suggested_topic,
            "suggestedType": self.config.archive.default_type,
            "suggestedTags": suggested_tags,
            # AirScript 1.0 field typing here is strict; keep optional diagnostics
            # out of the first stable write path.
            "meetingCreatedAt": "",
            "minutesGeneratedAt": "",
            "remark": "",
        }

    def _resolve_participant_names(self, participants: list[dict[str, Any]]) -> list[str]:
        exclude = set(self.config.archive.exclude_people)
        names: list[str] = []
        seen: set[str] = set()

        for participant in participants:
            user_id = str(participant.get("user_id", "")).strip()
            if not user_id:
                continue
            name = self._lookup_user_name(user_id)
            if not name or name in exclude or name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    def _lookup_user_name(self, user_id: str) -> str:
        if user_id in self._user_name_cache:
            return self._user_name_cache[user_id]
        try:
            detail = self.api_client.get_user_detail(user_id)
        except Exception:
            self._user_name_cache[user_id] = ""
            return ""
        name = str(detail.get("user_name", "")).strip()
        self._user_name_cache[user_id] = name
        return name

    def _pick_ready_minute(self, minutes: list[dict[str, Any]]) -> dict[str, Any] | None:
        ready_values = {value.lower() for value in self.config.meetings.ready_status_values}
        candidates: list[tuple[str, dict[str, Any]]] = []
        for minute in minutes:
            status = str(get_by_path(minute, self.config.meetings.minute_fields.status, "")).lower()
            url = get_by_path(minute, self.config.meetings.minute_fields.url, "")
            if ready_values and status and status not in ready_values:
                continue
            if not url:
                continue
            generated_at = str(get_by_path(minute, self.config.meetings.minute_fields.generated_at, ""))
            candidates.append((generated_at, minute))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _pick_recording(self, recordings: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates: list[tuple[str, dict[str, Any]]] = []
        for recording in recordings:
            url = get_by_path(recording, self.config.meetings.minute_fields.url, "")
            if not url:
                continue
            generated_at = str(get_by_path(recording, self.config.meetings.minute_fields.generated_at, ""))
            candidates.append((generated_at, recording))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _pick_link(self, recording: dict[str, Any] | None, minute: dict[str, Any] | None) -> str:
        if recording:
            url = get_by_path(recording, self.config.meetings.minute_fields.url, "")
            if url:
                return url
        if minute:
            return get_by_path(minute, self.config.meetings.minute_fields.url, "")
        return ""

    def _pick_generated_at(self, recording: dict[str, Any] | None, minute: dict[str, Any] | None) -> str:
        if minute:
            value = get_by_path(minute, self.config.meetings.minute_fields.generated_at, "")
            if value:
                return value
        if recording:
            return get_by_path(recording, self.config.meetings.minute_fields.generated_at, "")
        return ""

    def _extract_topic_from_recording_content(self, meeting_id: str, recording_id: str) -> str:
        if not recording_id:
            return ""

        summary_text = ""
        chapters: list[dict[str, Any]] = []
        transcript_text = ""

        try:
            summary_text = self.api_client.get_recording_summary(meeting_id, recording_id)
        except Exception:
            summary_text = ""

        try:
            chapters = self.api_client.get_recording_chapters(meeting_id, recording_id)
        except Exception:
            chapters = []

        try:
            transcript_text = self.api_client.get_recording_transcript(meeting_id, recording_id)
        except Exception:
            transcript_text = ""

        return extract_topic_from_recording_content(
            summary_text=summary_text,
            chapters=chapters,
            transcript_text=transcript_text,
        )
