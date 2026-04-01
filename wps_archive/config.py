from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuthConfig:
    access_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    authorization_code: str = ""
    redirect_uri: str = ""
    token_url: str = "https://openapi.wps.cn/oauth2/token"


@dataclass
class MeetingListQueryConfig:
    page_size_param: str = "page_size"
    cursor_param: str = "page_token"
    start_param: str = "start_time"
    end_param: str = "end_time"
    time_format: str = "unix_seconds"
    initiator_param: str = "host_user_id"
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeetingListResponseConfig:
    items_path: str = "data.items"
    next_cursor_path: str = "data.next_page_token"


@dataclass
class MeetingFieldsConfig:
    id: str = "id"
    title: str = "subject"
    start_time: str = "start_time"
    created_at: str = "create_time"
    initiator_user_id: str = "host_user.user_id"


@dataclass
class MinuteFieldsConfig:
    id: str = "id"
    url: str = "view_url"
    status: str = "status"
    generated_at: str = "create_time"


@dataclass
class MeetingsConfig:
    list_endpoint: str = "https://openapi.wps.cn/v7/meetings"
    detail_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}"
    participants_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}/participants"
    user_endpoint_template: str = "https://openapi.wps.cn/v7/users/{user_id}"
    minutes_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}/minutes"
    recordings_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}/recordings"
    recording_summary_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}/recordings/{recording_id}/summary"
    recording_chapters_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}/recordings/{recording_id}/chapters"
    recording_transcript_endpoint_template: str = "https://openapi.wps.cn/v7/meetings/{meeting_id}/recordings/{recording_id}/transcript"
    page_size: int = 50
    safe_lookback_days: int = 7
    list_query: MeetingListQueryConfig = field(default_factory=MeetingListQueryConfig)
    list_response: MeetingListResponseConfig = field(default_factory=MeetingListResponseConfig)
    meeting_fields: MeetingFieldsConfig = field(default_factory=MeetingFieldsConfig)
    minutes_response: MeetingListResponseConfig = field(default_factory=lambda: MeetingListResponseConfig(items_path="data.items", next_cursor_path=""))
    minute_fields: MinuteFieldsConfig = field(default_factory=MinuteFieldsConfig)
    ready_status_values: list[str] = field(default_factory=lambda: ["ready", "finished", "success", "done"])
    mentor_user_id: str = ""
    mentor_name: str = "沈惠中"


@dataclass
class AirScriptConfig:
    api_token: str = ""
    upsert_pending_archive_webhook: str = ""
    finalize_pending_archive_webhook: str = ""


@dataclass
class ArchiveConfig:
    default_type: str = "学术讨论"
    exclude_people: list[str] = field(default_factory=lambda: ["沈惠中"])
    topic_people_mapping: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PathsConfig:
    state_file: str = ".wps_archive_state.json"


@dataclass
class AppConfig:
    auth: AuthConfig = field(default_factory=AuthConfig)
    meetings: MeetingsConfig = field(default_factory=MeetingsConfig)
    airscript: AirScriptConfig = field(default_factory=AirScriptConfig)
    archive: ArchiveConfig = field(default_factory=ArchiveConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    config_path: str = ""

    @property
    def state_file_path(self) -> Path:
        path = Path(self.paths.state_file)
        if path.is_absolute():
            return path
        base = Path(self.config_path).resolve().parent if self.config_path else Path.cwd()
        return (base / path).resolve()


def _merge_dataclass(instance: Any, payload: dict[str, Any]) -> Any:
    for key, value in payload.items():
        current = getattr(instance, key)
        if hasattr(current, "__dataclass_fields__") and isinstance(value, dict):
            _merge_dataclass(current, value)
        else:
            setattr(instance, key, value)
    return instance


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    app = AppConfig()
    _merge_dataclass(app, payload)
    app.config_path = str(config_path)
    validate_config(app)
    return app


def validate_config(config: AppConfig) -> None:
    if not config.airscript.api_token:
        raise ValueError("config.airscript.api_token is required")
    if not config.airscript.upsert_pending_archive_webhook:
        raise ValueError("config.airscript.upsert_pending_archive_webhook is required")
    if not config.airscript.finalize_pending_archive_webhook:
        raise ValueError("config.airscript.finalize_pending_archive_webhook is required")
