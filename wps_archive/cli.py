from __future__ import annotations

import argparse
import json
from pathlib import Path

from .auth import apply_token_payload, authorize_user, get_access_token
from .config import load_config, save_config
from .meeting_client import WpsOpenApiClient
from .state import load_state, save_state
from .syncer import ArchiveSyncService
from .title_parser import parse_meeting_title
from .utils import utc_now
from .webhook import WebhookClient


def default_config_path() -> str:
    return str((Path.cwd() / "config.json").resolve())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WPS meeting archive sync CLI")
    parser.add_argument("--config", default=default_config_path(), help="Path to config JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_config = subparsers.add_parser("check-config", help="Validate config and print resolved paths")
    check_config.add_argument("--json", action="store_true", help="Print validation result as JSON")

    authorize = subparsers.add_parser("authorize-user", help="Open browser and save user access token into config")
    authorize.add_argument("--no-open", action="store_true", help="Print auth URL only, do not open browser automatically")
    authorize.add_argument("--host", default="127.0.0.1", help="Local callback host")
    authorize.add_argument("--port", type=int, default=8765, help="Local callback port")

    parse_title = subparsers.add_parser("parse-title", help="Parse a meeting title")
    parse_title.add_argument("title", help="Meeting title to parse")

    sync_pending = subparsers.add_parser("sync-pending", help="Sync candidate meetings into pending archive table")
    sync_pending.add_argument("--dry-run", action="store_true", help="Do not call webhook")

    sync_mock = subparsers.add_parser("sync-mock", help="Push one mock meeting into pending archive table")
    sync_mock.add_argument("title", help="Mock meeting title, e.g. 栾天成、褚梦圆_臭氧反演")
    sync_mock.add_argument("--meeting-id", default="", help="Optional mock meeting id")
    sync_mock.add_argument("--link", default="https://meeting.kdocs.cn/meeting/ai/mock-demo", help="Mock meeting link")
    sync_mock.add_argument("--date", default="", help="Meeting date in YYYY/MM/DD")
    sync_mock.add_argument("--created-at", default="", help="Meeting created time in ISO8601")
    sync_mock.add_argument("--minutes-generated-at", default="", help="Minutes generated time in ISO8601")
    sync_mock.add_argument("--type", default="学术讨论", help="Suggested meeting type")
    sync_mock.add_argument("--remark", default="CLI mock sync", help="Remark stored in pending table")
    sync_mock.add_argument("--dry-run", action="store_true", help="Do not call webhook")

    finalize = subparsers.add_parser("finalize-confirmed", help="Finalize confirmed pending archive records")
    finalize.add_argument("--dry-run", action="store_true", help="Do not call webhook")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check-config":
        config = load_config(args.config, validate=False)
        missing = []
        if not config.auth.client_id:
            missing.append("auth.client_id")
        if not config.auth.client_secret:
            missing.append("auth.client_secret")
        if not config.airscript.api_token:
            missing.append("airscript.api_token")
        if not config.airscript.upsert_pending_archive_webhook:
            missing.append("airscript.upsert_pending_archive_webhook")
        if not config.airscript.finalize_pending_archive_webhook:
            missing.append("airscript.finalize_pending_archive_webhook")
        payload = {
            "config_path": config.config_path,
            "state_file_path": str(config.state_file_path),
            "has_access_token": bool(config.auth.access_token),
            "has_refresh_token": bool(config.auth.refresh_token),
            "redirect_uri": config.auth.redirect_uri,
            "scope": config.auth.scope,
            "missing_required_fields": missing,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for key, value in payload.items():
                print(f"{key}: {value}")
        return 0

    if args.command == "parse-title":
        result = parse_meeting_title(args.title, exclude_people=["沈惠中"])
        print(
            json.dumps(
                {
                    "raw_title": result.raw_title,
                    "suggested_people_names": result.suggested_people_names,
                    "suggested_topic": result.suggested_topic,
                    "needs_confirmation": result.needs_confirmation,
                    "has_structured_title": result.has_structured_title,
                    "note": result.note,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "authorize-user":
        config = load_config(args.config, validate=False)
        token_payload = authorize_user(
            config.auth,
            open_browser=not args.no_open,
            host=args.host,
            port=args.port,
        )
        apply_token_payload(config.auth, token_payload)
        save_config(config)
        print(json.dumps(token_payload, ensure_ascii=False, indent=2))
        print(f"config_path={config.config_path}")
        return 0

    config = load_config(args.config)

    webhook_client = WebhookClient(api_token=config.airscript.api_token)

    if args.command == "sync-mock":
        parsed = parse_meeting_title(args.title, exclude_people=config.archive.exclude_people)
        now = utc_now().replace(microsecond=0).isoformat()
        payload = {
            "meetingId": args.meeting_id or f"mock-{utc_now().strftime('%Y%m%d%H%M%S')}",
            "meetingTitle": args.title,
            "meetingDate": args.date or utc_now().astimezone().strftime("%Y/%m/%d"),
            "meetingLink": args.link,
            "suggestedPeopleNames": parsed.suggested_people_names,
            "suggestedTopic": parsed.suggested_topic,
            "suggestedType": args.type,
            "meetingCreatedAt": args.created_at or now,
            "minutesGeneratedAt": args.minutes_generated_at or now,
            "remark": args.remark if not parsed.note else f"{args.remark}; {parsed.note}",
        }
        if not args.dry_run:
            webhook_client.call(config.airscript.upsert_pending_archive_webhook, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    access_token = get_access_token(config)
    api_client = WpsOpenApiClient(config, access_token)
    service = ArchiveSyncService(config, api_client, webhook_client)

    if args.command == "sync-pending":
        state = load_state(config.state_file_path)
        summary = service.sync_pending(state, dry_run=args.dry_run)
        save_state(config.state_file_path, state)
        print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))
        print(f"state_file={config.state_file_path}")
        return 0

    if args.command == "finalize-confirmed":
        summary = service.finalize_confirmed(dry_run=args.dry_run)
        print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")
