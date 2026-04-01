from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import parse, request

from .config import AppConfig
from .utils import get_by_path, parse_datetime, utc_now


@dataclass
class WpsOpenApiClient:
    config: AppConfig
    access_token: str

    def _json_request(self, url: str, params: dict | None = None) -> dict:
        final_url = url
        if params:
            final_url = f"{url}?{parse.urlencode(params, doseq=True)}"
        req = request.Request(
            final_url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            method="GET",
        )
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_meetings(self, since: str) -> list[dict]:
        meetings_cfg = self.config.meetings
        query_cfg = meetings_cfg.list_query
        response_cfg = meetings_cfg.list_response

        items: list[dict] = []
        cursor = None
        since_dt = parse_datetime(since) or utc_now()
        end_dt = utc_now()
        while True:
            params = dict(query_cfg.extra_params)
            params[query_cfg.page_size_param] = meetings_cfg.page_size
            if query_cfg.start_param:
                params[query_cfg.start_param] = self._format_query_time(since_dt, query_cfg.time_format)
            if query_cfg.end_param:
                params[query_cfg.end_param] = self._format_query_time(end_dt, query_cfg.time_format)
            if meetings_cfg.mentor_user_id and query_cfg.initiator_param:
                params[query_cfg.initiator_param] = meetings_cfg.mentor_user_id
            if cursor and query_cfg.cursor_param:
                params[query_cfg.cursor_param] = cursor

            payload = self._json_request(meetings_cfg.list_endpoint, params=params)
            page_items = get_by_path(payload, response_cfg.items_path, []) or []
            items.extend(page_items)
            cursor = get_by_path(payload, response_cfg.next_cursor_path, "") if response_cfg.next_cursor_path else ""
            if not cursor:
                break
        return items

    def list_minutes(self, meeting_id: str) -> list[dict]:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.minutes_endpoint_template.format(meeting_id=meeting_id)
        payload = self._json_request(url)
        return get_by_path(payload, meetings_cfg.minutes_response.items_path, []) or []

    def get_meeting_detail(self, meeting_id: str) -> dict:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.detail_endpoint_template.format(meeting_id=meeting_id)
        payload = self._json_request(url)
        return get_by_path(payload, "data", {}) or {}

    def list_participants(self, meeting_id: str) -> list[dict]:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.participants_endpoint_template.format(meeting_id=meeting_id)
        payload = self._json_request(url)
        return get_by_path(payload, meetings_cfg.minutes_response.items_path, []) or []

    def get_user_detail(self, user_id: str) -> dict:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.user_endpoint_template.format(user_id=user_id)
        payload = self._json_request(url)
        return get_by_path(payload, "data", {}) or {}

    def list_recordings(self, meeting_id: str) -> list[dict]:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.recordings_endpoint_template.format(meeting_id=meeting_id)
        payload = self._json_request(url)
        return get_by_path(payload, meetings_cfg.minutes_response.items_path, []) or []

    def get_recording_summary(self, meeting_id: str, recording_id: str) -> str:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.recording_summary_endpoint_template.format(
            meeting_id=meeting_id,
            recording_id=recording_id,
        )
        payload = self._json_request(url)
        return str(get_by_path(payload, "data.content", "") or "")

    def get_recording_chapters(self, meeting_id: str, recording_id: str) -> list[dict]:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.recording_chapters_endpoint_template.format(
            meeting_id=meeting_id,
            recording_id=recording_id,
        )
        payload = self._json_request(url)
        return get_by_path(payload, "data.items", []) or []

    def get_recording_transcript(self, meeting_id: str, recording_id: str) -> str:
        meetings_cfg = self.config.meetings
        url = meetings_cfg.recording_transcript_endpoint_template.format(
            meeting_id=meeting_id,
            recording_id=recording_id,
        )
        payload = self._json_request(url)
        paragraphs = get_by_path(payload, "data.paragraphs", []) or []
        parts: list[str] = []
        for paragraph in paragraphs:
            for sentence in paragraph.get("sentenses") or []:
                text = str(sentence.get("text", "")).strip()
                if text:
                    parts.append(text)
        return "\n".join(parts)

    def _format_query_time(self, dt, time_format: str) -> str | int:
        if time_format == "unix_seconds":
            return int(dt.timestamp())
        if time_format == "unix_milliseconds":
            return int(dt.timestamp() * 1000)
        if time_format == "iso8601":
            return dt.isoformat()
        return dt.isoformat()
