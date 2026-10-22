from pathlib import Path
import tempfile
import unittest

from config import ConfigError, load_settings


class ConfigTests(unittest.TestCase):
    def read(self, extra="", prefix="allowed_guild_ids=[1]\nallowed_channel_ids=[2]\n"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.toml"
            path.write_text(prefix + extra, encoding="utf-8")
            return load_settings(path)

    def test_valid_settings(self):
        settings = self.read()
        self.assertEqual(settings.allowed_channel_ids, (2,))

    def test_empty_allowlists_fail_closed(self):
        with self.assertRaises(ConfigError):
            self.read(prefix="")

    def test_invalid_types_and_limits(self):
        for text in ("model=123", "max_output_tokens=99999", "max_response_characters=2001",
                     "history_messages=-1", "provider='unknown'", "typo_key=42",
                     "request_timeout_seconds=true", "personality=[]"):
            with self.assertRaises(ConfigError):
                self.read(text)

    def test_ids_are_numbers(self):
        for prefix in ("allowed_guild_ids=['1']\nallowed_channel_ids=[2]\n",
                       "allowed_guild_ids=[true]\nallowed_channel_ids=[2]\n"):
            with self.assertRaises(ConfigError):
                self.read(prefix=prefix)

    def test_endpoint_transport_security(self):
        for url in ("http://example.com", "https://user:password@example.com", "https://example.com?key=secret"):
            with self.assertRaises(ConfigError):
                self.read(f"base_url='{url}'")
        self.assertEqual(self.read("provider='ollama'\nbase_url='http://127.0.0.1:11434'").provider, "ollama")
