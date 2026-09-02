"""Tests for the rule engine."""

from pathlib import Path

from sebaslibs.core.entities import Category, FileEntry
from sebaslibs.org.rule_engine import Rule, RuleEngine


class TestRule:
    def test_match_by_extension(self):
        entry = FileEntry(
            original_name="photo.jpg",
            source_path=Path("/tmp/photo.jpg"),
            size_bytes=100,
        )
        rule = Rule(conditions={"extension": ".jpg"}, actions={"move_to": "/special"})
        assert rule.matches(entry)

    def test_match_by_name(self):
        entry = FileEntry(
            original_name="secret.docx",
            source_path=Path("/tmp/secret.docx"),
            size_bytes=500,
        )
        rule = Rule(conditions={"name": "secret.docx"}, actions={"move_to": "/vault"})
        assert rule.matches(entry)

    def test_match_by_name_contains(self):
        entry = FileEntry(
            original_name="my_invoice_2024.pdf",
            source_path=Path("/tmp/my_invoice_2024.pdf"),
            size_bytes=200,
        )
        rule = Rule(conditions={"name_contains": "invoice"}, actions={"move_to": "/invoices"})
        assert rule.matches(entry)

    def test_match_by_name_regex(self):
        entry = FileEntry(
            original_name="IMG_20240315.jpg",
            source_path=Path("/tmp/IMG_20240315.jpg"),
            size_bytes=300,
        )
        rule = Rule(conditions={"name_regex": r"IMG_\d+\.jpg"}, actions={"move_to_category": "Photos"})
        assert rule.matches(entry)

    def test_match_by_size_gte(self):
        entry = FileEntry(
            original_name="big.zip",
            source_path=Path("/tmp/big.zip"),
            size_bytes=1_000_000,
        )
        rule = Rule(conditions={"size_gte": 500_000}, actions={"move_to": "/large_files"})
        assert rule.matches(entry)

    def test_no_match(self):
        entry = FileEntry(
            original_name="small.txt",
            source_path=Path("/tmp/small.txt"),
            size_bytes=10,
        )
        rule = Rule(conditions={"size_gte": 1000}, actions={"move_to": "/large"})
        assert not rule.matches(entry)

    def test_multiple_conditions_all_must_match(self):
        entry = FileEntry(
            original_name="report.pdf",
            source_path=Path("/tmp/report.pdf"),
            size_bytes=50,
        )
        rule = Rule(
            conditions={"extension": ".pdf", "size_gte": 100},
            actions={"move_to": "/reports"},
        )
        assert not rule.matches(entry)  # size is too small

    def test_apply_move_to(self):
        entry = FileEntry(
            original_name="doc.pdf",
            source_path=Path("/tmp/doc.pdf"),
            size_bytes=100,
        )
        rule = Rule(conditions={"extension": ".pdf"}, actions={"move_to": "/documents"})
        rule.apply(entry)
        assert entry.destination_path == Path("/documents/doc.pdf")

    def test_apply_move_to_category(self):
        entry = FileEntry(
            original_name="song.mp3",
            source_path=Path("/tmp/song.mp3"),
            size_bytes=100,
        )
        rule = Rule(conditions={"extension": ".mp3"}, actions={"move_to_category": "Music"})
        rule.apply(entry)
        assert entry.category == Category.MUSIC

    def test_apply_skip(self):
        entry = FileEntry(
            original_name="keep.txt",
            source_path=Path("/tmp/keep.txt"),
            size_bytes=50,
        )
        rule = Rule(conditions={"name": "keep.txt"}, actions={"skip": True})
        rule.apply(entry)
        assert entry.metadata["action"] == "skip"

    def test_apply_rename_with_regex(self):
        entry = FileEntry(
            original_name="IMG_20240315.jpg",
            source_path=Path("/tmp/IMG_20240315.jpg"),
            size_bytes=100,
        )
        rule = Rule(
            conditions={"name_regex": r"(IMG_\d+)\.jpg"},
            actions={"rename": r"\1_photo.jpg"},
        )
        rule.apply(entry)
        assert entry.original_name == "IMG_20240315_photo.jpg"

    def test_apply_tag(self):
        entry = FileEntry(
            original_name="important.pdf",
            source_path=Path("/tmp/important.pdf"),
            size_bytes=200,
        )
        rule = Rule(conditions={"name_contains": "important"}, actions={"tag": ["priority"]})
        rule.apply(entry)
        assert "priority" in entry.metadata["tags"]

    def test_apply_delete(self):
        entry = FileEntry(
            original_name="junk.tmp",
            source_path=Path("/tmp/junk.tmp"),
            size_bytes=10,
        )
        rule = Rule(conditions={"extension": ".tmp"}, actions={"delete": "trash"})
        rule.apply(entry)
        assert entry.metadata["action"] == "delete"
        assert entry.metadata["delete_dest"] == "trash"


class TestRuleEngine:
    def test_first_match_wins(self):
        engine = RuleEngine()
        engine.rules = [
            Rule(
                conditions={"extension": ".jpg"},
                actions={"move_to": "/photos"},
            ),
            Rule(
                conditions={"name_regex": r"\.jpg$"},
                actions={"move_to": "/other_photos"},
            ),
        ]

        entry = FileEntry(
            original_name="photo.jpg",
            source_path=Path("/tmp/photo.jpg"),
            size_bytes=100,
        )

        assert engine.evaluate(entry) is True
        assert entry.destination_path == Path("/photos/photo.jpg")

    def test_no_match_returns_false(self):
        engine = RuleEngine()
        engine.rules = [
            Rule(conditions={"extension": ".pdf"}, actions={"move_to": "/docs"}),
        ]

        entry = FileEntry(
            original_name="photo.jpg",
            source_path=Path("/tmp/photo.jpg"),
            size_bytes=100,
        )

        assert engine.evaluate(entry) is False

    def test_load_from_yaml(self, tmp_path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(
            """
rules:
  - conditions:
      extension: .pdf
    actions:
      move_to: /documents
  - conditions:
      name_contains: invoice
    actions:
      move_to_category: Documents
"""
        )

        engine = RuleEngine(rules_file)
        assert len(engine.rules) == 2

        entry = FileEntry(
            original_name="report.pdf",
            source_path=Path("/tmp/report.pdf"),
            size_bytes=100,
        )
        assert engine.evaluate(entry) is True
        assert entry.destination_path == Path("/documents/report.pdf")

    def test_empty_rules_file(self, tmp_path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("rules: []")

        engine = RuleEngine(rules_file)
        assert len(engine.rules) == 0

        entry = FileEntry(
            original_name="anything.txt",
            source_path=Path("/tmp/anything.txt"),
            size_bytes=10,
        )
        assert engine.evaluate(entry) is False

    def test_rules_override_default_classification(self):
        """Rules are evaluated before default classifier, so they can override."""
        entry = FileEntry(
            original_name="secret.jpg",
            source_path=Path("/tmp/secret.jpg"),
            size_bytes=100,
        )

        engine = RuleEngine()
        engine.rules = [
            Rule(
                conditions={"name": "secret.jpg"},
                actions={"move_to_category": "Documents", "subfolder": "confidential"},
            ),
        ]
        engine.evaluate(entry)

        assert entry.category == Category.DOCUMENTS
        assert entry.subfolder == "confidential"
