"""Rule engine: declarative YAML rules evaluated before the default classifier.

First match wins.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..core.entities import Category, FileEntry


class Rule:
    def __init__(self, conditions: dict[str, Any], actions: dict[str, Any]) -> None:
        self.conditions = conditions
        self.actions = actions

    def matches(self, entry: FileEntry) -> bool:
        for key, value in self.conditions.items():
            if not self._check_condition(key, value, entry):
                return False
        return True

    def _check_condition(self, key: str, value: Any, entry: FileEntry) -> bool:
        if key == "name":
            return entry.original_name == value
        if key == "name_regex":
            return bool(re.search(value, entry.original_name))
        if key == "name_contains":
            return value.lower() in entry.original_name.lower()
        if key == "extension":
            return entry.extension == value.lower()
        if key == "base_category":
            return entry.category and entry.category.value == value
        if key == "size_gte":
            return entry.size_bytes >= value
        if key == "size_lte":
            return entry.size_bytes <= value
        if key == "year":
            dt = entry.date_taken or entry.modified or entry.created
            return dt is not None and dt.year == value
        if key == "month":
            dt = entry.date_taken or entry.modified or entry.created
            return dt is not None and dt.month == value
        if key == "date_gte":
            dt = entry.date_taken or entry.modified or entry.created
            return dt is not None and dt >= datetime.fromisoformat(value)
        if key == "date_lte":
            dt = entry.date_taken or entry.modified or entry.created
            return dt is not None and dt <= datetime.fromisoformat(value)
        if key == "is_archive":
            return entry.is_archive == bool(value)
        if key == "has_password":
            return entry.has_password == bool(value)
        return True

    def apply(self, entry: FileEntry) -> None:
        for action, value in self.actions.items():
            if action == "move_to":
                entry.destination_path = Path(value) / entry.original_name
            elif action == "move_to_category":
                entry.category = Category(value)
            elif action == "subfolder":
                entry.subfolder = value
            elif action == "delete":
                entry.status = entry.status  # handled by executor
                entry.metadata["action"] = "delete"
                entry.metadata["delete_dest"] = value
            elif action == "rename":
                # Support capture groups: e.g. "(.*)\.png" -> "\1_final.png"
                new_name = re.sub(self.conditions.get("name_regex", ""), value, entry.original_name)
                entry.original_name = new_name
            elif action == "skip":
                entry.status = entry.status
                entry.metadata["action"] = "skip"
            elif action == "extract":
                entry.metadata["action"] = "extract"
                entry.metadata["extract_dest"] = value
            elif action == "tag":
                entry.metadata["tags"] = value if isinstance(value, list) else [value]


class RuleEngine:
    def __init__(self, rules_path: Path | None = None) -> None:
        self.rules: list[Rule] = []
        if rules_path and rules_path.exists():
            self.load(rules_path)

    def load(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for rule_data in data.get("rules", []):
            rule = Rule(rule_data.get("conditions", {}), rule_data.get("actions", {}))
            self.rules.append(rule)

    def evaluate(self, entry: FileEntry) -> bool:
        """Returns True if a rule matched and was applied."""
        for rule in self.rules:
            if rule.matches(entry):
                rule.apply(entry)
                return True
        return False
