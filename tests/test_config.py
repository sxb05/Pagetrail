import importlib
import os
import sys
import unittest
from unittest.mock import patch

from pydantic import ValidationError


def _load_config_with_env(env: dict[str, str]):
    with patch.dict(os.environ, env, clear=True):
        sys.modules.pop("config", None)
        return importlib.import_module("config")


class SettingsEnvTests(unittest.TestCase):
    def test_database_url_only_is_valid(self):
        config = _load_config_with_env(
            {"DATABASE_URL": "sqlite:///tmp/test.db"}
        )

        settings = config.Settings()

        self.assertEqual(settings.DATABASE_URL, "sqlite:///tmp/test.db")
        self.assertIsNone(settings.DATABASE_HOST)

    def test_legacy_database_settings_are_valid_without_database_url(self):
        config = _load_config_with_env(
            {
                "DATABASE_HOST": "localhost",
                "DATABASE_PORT": "5432",
                "DATABASE_NAME": "postgres",
                "DATABASE_USERNAME": "postgres",
                "DATABASE_PASSWORD": "postgres",
            }
        )

        settings = config.Settings()

        self.assertIsNone(settings.DATABASE_URL)
        self.assertEqual(settings.DATABASE_HOST, "localhost")

    def test_missing_settings_fail_without_database_url(self):
        config = _load_config_with_env({})

        with self.assertRaises(ValidationError) as error_info:
            config.Settings()

        self.assertIn("Set DATABASE_URL or provide all legacy database settings", str(error_info.exception))


if __name__ == "__main__":
    unittest.main()
