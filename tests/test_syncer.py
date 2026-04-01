import unittest

from wps_archive.config import AppConfig
from wps_archive.state import SyncState
from wps_archive.syncer import ArchiveSyncService


class FakeApiClient:
    def __init__(self, meetings, details, participants, recordings, minutes, users=None, summaries=None, chapters=None, transcripts=None):
        self._meetings = meetings
        self._details = details
        self._participants = participants
        self._recordings = recordings
        self._minutes = minutes
        self._users = users or {}
        self._summaries = summaries or {}
        self._chapters = chapters or {}
        self._transcripts = transcripts or {}

    def list_meetings(self, since):
        self.since = since
        return self._meetings

    def get_meeting_detail(self, meeting_id):
        return self._details[meeting_id]

    def list_participants(self, meeting_id):
        return self._participants[meeting_id]

    def list_recordings(self, meeting_id):
        return self._recordings[meeting_id]

    def list_minutes(self, meeting_id):
        return self._minutes[meeting_id]

    def get_user_detail(self, user_id):
        value = self._users[user_id]
        if isinstance(value, Exception):
            raise value
        return value

    def get_recording_summary(self, meeting_id, recording_id):
        return self._summaries.get((meeting_id, recording_id), "")

    def get_recording_chapters(self, meeting_id, recording_id):
        return self._chapters.get((meeting_id, recording_id), [])

    def get_recording_transcript(self, meeting_id, recording_id):
        return self._transcripts.get((meeting_id, recording_id), "")


class FakeWebhookClient:
    def __init__(self):
        self.calls = []

    def call(self, webhook_url, argv=None):
        self.calls.append((webhook_url, argv or {}))
        return {"status": "finished"}


class SyncerTests(unittest.TestCase):
    def test_sync_pending_builds_candidate(self):
        config = AppConfig()
        config.airscript.api_token = "token"
        config.airscript.upsert_pending_archive_webhook = "https://example.com/upsert"
        config.airscript.finalize_pending_archive_webhook = "https://example.com/finalize"
        config.meetings.mentor_user_id = "teacher-1"

        meeting = {"id": "m1", "subject": "栾天成、褚梦圆_臭氧反演"}
        detail = {
            "id": "m1",
            "subject": "栾天成、褚梦圆_臭氧反演",
            "start_time": "2026-03-29T11:00:00+08:00",
            "create_time": "2026-03-29T10:00:00+08:00",
            "host_user": {"user_id": "teacher-1"},
        }
        recording = {
            "id": "rec-1",
            "view_url": "https://meeting.kdocs.cn/meeting/ai/abc",
            "create_time": "2026-03-29T12:00:00+08:00",
        }
        participants = [
            {"user_id": "teacher-1", "is_host": True},
            {"user_id": "student-1", "is_host": False},
        ]
        api_client = FakeApiClient(
            [meeting],
            {"m1": detail},
            {"m1": participants},
            {"m1": [recording]},
            {"m1": []},
            {
                "teacher-1": {"user_name": "沈惠中"},
                "student-1": {"user_name": "栾天成"},
            },
        )
        webhook_client = FakeWebhookClient()
        service = ArchiveSyncService(config, api_client, webhook_client)

        summary = service.sync_pending(SyncState(last_sync_at="2026-03-29T00:00:00+08:00"))

        self.assertEqual(summary.seen, 1)
        self.assertEqual(summary.upserted, 1)
        self.assertEqual(len(webhook_client.calls), 1)
        _, payload = webhook_client.calls[0]
        self.assertEqual(payload["meetingId"], "m1")
        self.assertEqual(payload["meetingDate"], "2026/03/29")
        self.assertEqual(payload["suggestedPeopleNames"], ["栾天成", "褚梦圆"])
        self.assertEqual(payload["suggestedTopic"], "臭氧反演")
        self.assertEqual(payload["suggestedTags"], ["数据分析"])

    def test_sync_pending_uses_participant_names_when_api_title_is_not_structured(self):
        config = AppConfig()
        config.airscript.api_token = "token"
        config.airscript.upsert_pending_archive_webhook = "https://example.com/upsert"
        config.airscript.finalize_pending_archive_webhook = "https://example.com/finalize"
        config.archive.exclude_people = ["沈惠中"]

        meeting = {"id": "m1", "subject": "栾天成的会议"}
        detail = {
            "id": "m1",
            "subject": "栾天成的会议",
            "start_time": "2026-03-30T10:00:00+08:00",
            "create_time": "2026-03-30T09:00:00+08:00",
            "host_user": {"user_id": "teacher-1"},
        }
        recording = {
            "id": "rec-1",
            "view_url": "https://meeting.kdocs.cn/meeting/ai/abc",
            "create_time": "2026-03-30T11:00:00+08:00",
        }
        participants = [
            {"user_id": "teacher-1", "is_host": True},
            {"user_id": "student-1", "is_host": False},
            {"user_id": "student-2", "is_host": False},
        ]
        api_client = FakeApiClient(
            [meeting],
            {"m1": detail},
            {"m1": participants},
            {"m1": [recording]},
            {"m1": []},
            {
                "teacher-1": {"user_name": "沈惠中"},
                "student-1": {"user_name": "栾天成"},
                "student-2": {"user_name": "许俊鹏"},
            },
        )
        webhook_client = FakeWebhookClient()
        service = ArchiveSyncService(config, api_client, webhook_client)

        summary = service.sync_pending(SyncState(last_sync_at="2026-03-30T00:00:00+08:00"))

        self.assertEqual(summary.seen, 1)
        self.assertEqual(summary.skipped, 0)
        self.assertEqual(summary.upserted, 1)
        _, payload = webhook_client.calls[0]
        self.assertEqual(payload["suggestedPeopleNames"], ["栾天成", "许俊鹏"])
        self.assertEqual(payload["suggestedTopic"], "")
        self.assertEqual(payload["suggestedTags"], ["方案设计"])
        self.assertEqual(payload["remark"], "")

    def test_sync_pending_infers_people_from_topic_mapping(self):
        config = AppConfig()
        config.airscript.api_token = "token"
        config.airscript.upsert_pending_archive_webhook = "https://example.com/upsert"
        config.airscript.finalize_pending_archive_webhook = "https://example.com/finalize"
        config.archive.exclude_people = ["沈惠中"]
        config.archive.topic_people_mapping = [
            {"name": "韩宇潇", "priority": 10, "include_keywords": ["航空排放健康", "航空排放"]},
        ]

        meeting = {"id": "m1", "subject": "沈惠中的会议"}
        detail = {
            "id": "m1",
            "subject": "沈惠中的会议",
            "start_time": "2026-03-30T10:00:00+08:00",
            "create_time": "2026-03-30T09:00:00+08:00",
            "host_user": {"user_id": "teacher-1"},
        }
        recording = {
            "id": "rec-1",
            "view_url": "https://meeting.kdocs.cn/meeting/ai/abc",
            "create_time": "2026-03-30T11:00:00+08:00",
        }
        participants = [{"user_id": "teacher-1", "is_host": True}]
        api_client = FakeApiClient(
            [meeting],
            {"m1": detail},
            {"m1": participants},
            {"m1": [recording]},
            {"m1": []},
            {"teacher-1": {"user_name": "沈惠中"}},
            summaries={("m1", "rec-1"): "## 关于航空排放健康影响与论文修改的讨论会议"},
        )
        webhook_client = FakeWebhookClient()
        service = ArchiveSyncService(config, api_client, webhook_client)

        summary = service.sync_pending(SyncState(last_sync_at="2026-03-30T00:00:00+08:00"))

        self.assertEqual(summary.upserted, 1)
        _, payload = webhook_client.calls[0]
        self.assertEqual(payload["suggestedTopic"], "航空排放健康影响")
        self.assertEqual(payload["suggestedPeopleNames"], ["韩宇潇"])

    def test_sync_pending_prefers_priority_rule_for_conflicting_topic(self):
        config = AppConfig()
        config.airscript.api_token = "token"
        config.airscript.upsert_pending_archive_webhook = "https://example.com/upsert"
        config.airscript.finalize_pending_archive_webhook = "https://example.com/finalize"
        config.archive.exclude_people = ["沈惠中"]
        config.archive.topic_people_mapping = [
            {
                "name": "麦泽霖",
                "priority": 10,
                "include_keywords": ["伴随模型", "优化函数"],
                "exclude_keywords": ["AI辅助55版本", "55版本", "化学机制开发"],
            },
            {
                "name": "何金玲",
                "priority": 20,
                "include_keywords": ["AI辅助55版本", "55版本", "化学机制开发"],
            },
        ]

        meeting = {"id": "m1", "subject": "沈惠中的会议"}
        detail = {
            "id": "m1",
            "subject": "沈惠中的会议",
            "start_time": "2026-03-30T10:00:00+08:00",
            "create_time": "2026-03-30T09:00:00+08:00",
            "host_user": {"user_id": "teacher-1"},
        }
        recording = {
            "id": "rec-1",
            "view_url": "https://meeting.kdocs.cn/meeting/ai/abc",
            "create_time": "2026-03-30T11:00:00+08:00",
        }
        participants = [{"user_id": "teacher-1", "is_host": True}]
        api_client = FakeApiClient(
            [meeting],
            {"m1": detail},
            {"m1": participants},
            {"m1": [recording]},
            {"m1": []},
            {"teacher-1": {"user_name": "沈惠中"}},
            summaries={("m1", "rec-1"): "## AI辅助55版本伴随模型开发进展"},
        )
        webhook_client = FakeWebhookClient()
        service = ArchiveSyncService(config, api_client, webhook_client)

        summary = service.sync_pending(SyncState(last_sync_at="2026-03-30T00:00:00+08:00"))

        self.assertEqual(summary.upserted, 1)
        _, payload = webhook_client.calls[0]
        self.assertIn("AI辅助55版本", payload["suggestedTopic"])
        self.assertEqual(payload["suggestedPeopleNames"], ["何金玲"])

    def test_sync_pending_skips_unreadable_user_details(self):
        config = AppConfig()
        config.airscript.api_token = "token"
        config.airscript.upsert_pending_archive_webhook = "https://example.com/upsert"
        config.airscript.finalize_pending_archive_webhook = "https://example.com/finalize"
        config.archive.exclude_people = ["沈惠中"]

        meeting = {"id": "m1", "subject": "沈惠中的会议"}
        detail = {
            "id": "m1",
            "subject": "沈惠中的会议",
            "start_time": "2026-03-30T10:00:00+08:00",
            "create_time": "2026-03-30T09:00:00+08:00",
            "host_user": {"user_id": "teacher-1"},
        }
        recording = {
            "id": "rec-1",
            "view_url": "https://meeting.kdocs.cn/meeting/ai/abc",
            "create_time": "2026-03-30T11:00:00+08:00",
        }
        participants = [
            {"user_id": "teacher-1", "is_host": True},
            {"user_id": "student-1", "is_host": False},
            {"user_id": "student-2", "is_host": False},
        ]
        api_client = FakeApiClient(
            [meeting],
            {"m1": detail},
            {"m1": participants},
            {"m1": [recording]},
            {"m1": []},
            {
                "teacher-1": {"user_name": "沈惠中"},
                "student-1": PermissionError("forbidden"),
                "student-2": {"user_name": "许俊鹏"},
            },
        )
        webhook_client = FakeWebhookClient()
        service = ArchiveSyncService(config, api_client, webhook_client)

        summary = service.sync_pending(SyncState(last_sync_at="2026-03-30T00:00:00+08:00"))

        self.assertEqual(summary.upserted, 1)
        _, payload = webhook_client.calls[0]
        self.assertEqual(payload["suggestedPeopleNames"], ["许俊鹏"])

    def test_sync_pending_infers_topic_from_recording_chapters(self):
        config = AppConfig()
        config.airscript.api_token = "token"
        config.airscript.upsert_pending_archive_webhook = "https://example.com/upsert"
        config.airscript.finalize_pending_archive_webhook = "https://example.com/finalize"
        config.archive.exclude_people = ["沈惠中"]

        meeting = {"id": "m1", "subject": "沈惠中的会议"}
        detail = {
            "id": "m1",
            "subject": "沈惠中的会议",
            "start_time": "2026-03-30T10:00:00+08:00",
            "create_time": "2026-03-30T09:00:00+08:00",
            "host_user": {"user_id": "teacher-1"},
        }
        recording = {
            "id": "rec-1",
            "view_url": "https://meeting.kdocs.cn/meeting/ai/abc",
            "create_time": "2026-03-30T11:00:00+08:00",
        }
        participants = [{"user_id": "teacher-1", "is_host": True}]
        api_client = FakeApiClient(
            [meeting],
            {"m1": detail},
            {"m1": participants},
            {"m1": [recording]},
            {"m1": []},
            {"teacher-1": {"user_name": "沈惠中"}},
            chapters={("m1", "rec-1"): [{"title": "优化函数参数设置问题讨论"}]},
        )
        webhook_client = FakeWebhookClient()
        service = ArchiveSyncService(config, api_client, webhook_client)

        summary = service.sync_pending(SyncState(last_sync_at="2026-03-30T00:00:00+08:00"))

        self.assertEqual(summary.upserted, 1)
        _, payload = webhook_client.calls[0]
        self.assertEqual(payload["suggestedTopic"], "优化函数参数设置问题")
        self.assertEqual(payload["suggestedTags"], ["模式模拟"])


if __name__ == "__main__":
    unittest.main()
