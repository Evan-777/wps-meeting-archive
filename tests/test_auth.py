from __future__ import annotations

import unittest
from unittest.mock import patch

from wps_archive.auth import apply_token_payload, get_access_token
from wps_archive.config import AppConfig


class AuthTests(unittest.TestCase):
    def test_get_access_token_prefers_valid_existing_token(self) -> None:
        config = AppConfig()
        apply_token_payload(config.auth, {"access_token": "cached", "expires_in": 7200})

        with patch("wps_archive.auth.refresh_user_access_token") as refresh_mock:
            token = get_access_token(config)

        self.assertEqual(token, "cached")
        refresh_mock.assert_not_called()

    def test_get_access_token_refreshes_and_persists_when_refresh_token_exists(self) -> None:
        config = AppConfig()
        config.config_path = "/tmp/config.json"
        config.auth.client_id = "cid"
        config.auth.client_secret = "secret"
        config.auth.access_token = "expired"
        config.auth.access_token_expires_at = "2000-01-01T00:00:00+00:00"
        config.auth.refresh_token = "refresh-1"

        with (
            patch(
                "wps_archive.auth.refresh_user_access_token",
                return_value={
                    "access_token": "fresh",
                    "expires_in": 7200,
                    "refresh_token": "refresh-2",
                    "refresh_expires_in": 86400,
                },
            ) as refresh_mock,
            patch("wps_archive.auth.save_config") as save_mock,
        ):
            token = get_access_token(config)

        self.assertEqual(token, "fresh")
        self.assertEqual(config.auth.refresh_token, "refresh-2")
        refresh_mock.assert_called_once()
        save_mock.assert_called_once_with(config)

    def test_get_access_token_raises_clear_error_when_refresh_fails(self) -> None:
        config = AppConfig()
        config.auth.refresh_token = "bad-refresh"

        with patch("wps_archive.auth.refresh_user_access_token", side_effect=ValueError("boom")):
            with self.assertRaisesRegex(ValueError, "refresh_token 已失效或刷新失败"):
                get_access_token(config)

    def test_get_access_token_uses_client_credentials_when_user_authorization_not_configured(self) -> None:
        config = AppConfig()
        config.auth.client_id = "cid"
        config.auth.client_secret = "secret"

        with patch(
            "wps_archive.auth._request_token",
            return_value={"access_token": "app-token", "expires_in": 7200},
        ) as request_mock:
            token = get_access_token(config)

        self.assertEqual(token, "app-token")
        request_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
