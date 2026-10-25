"""Guard against capture-token and distinct-ID leakage in feed-order warnings."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = ROOT / "nodejs" / "src" / "ingestion" / "api" / "feed-order-sentinel.ts"


class FeedOrderPrivacyWave86(unittest.TestCase):
    def test_routing_identity_cannot_alias_across_slash_separators(self):
        source = SENTINEL.read_text(encoding="utf-8")
        self.assertIn("JSON.stringify([message.topic, message.partition, message.key])", source)
        self.assertNotIn("`${message.topic}/${message.partition}/${message.key}`", source)

    def test_ordering_warning_never_serializes_raw_kafka_key(self):
        source = SENTINEL.read_text(encoding="utf-8")
        match = re.search(
            r"logger\.warn\('⚠️', 'Out-of-order message fed to ingestion pipeline',\s*\{(?P<fields>.*?)\}\)",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        fields = match.group("fields")
        for field in ("topic:", "partition:", "offset:", "lastSeenOffset:", "consumerId,"):
            self.assertIn(field, fields)
        self.assertNotRegex(fields, r"\bkey\s*[,:]")
        self.assertNotIn("message.key", fields)


if __name__ == "__main__":
    unittest.main()
