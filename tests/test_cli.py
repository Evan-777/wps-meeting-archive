from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from wps_archive.cli import default_config_path, main


class CliTests(unittest.TestCase):
    def test_default_config_path_uses_current_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path.cwd()
            try:
                Path(tmpdir).mkdir(parents=True, exist_ok=True)
                import os

                os.chdir(tmpdir)
                self.assertEqual(default_config_path(), str((Path(tmpdir) / "config.json").resolve()))
            finally:
                os.chdir(cwd)

    def test_check_config_reports_missing_fields_without_failing_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "auth": {
                            "client_id": "cid",
                            "client_secret": "",
                            "scope": "kso.meeting.read",
                            "redirect_uri": "http://127.0.0.1:8765/callback",
                        },
                        "airscript": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["--config", str(config_path), "check-config", "--json"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(buffer.getvalue())
            self.assertIn("airscript.api_token", payload["missing_required_fields"])
            self.assertIn("airscript.upsert_pending_archive_webhook", payload["missing_required_fields"])


if __name__ == "__main__":
    unittest.main()
