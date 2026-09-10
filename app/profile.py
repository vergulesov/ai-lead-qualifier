from pathlib import Path
import json
from typing import Any


class ProfileError(ValueError):
    pass


class Profile:
    def __init__(self, name: str, data: dict[str, Any]):
        self.name = name
        self.data = data
        self.version = str(data.get("version", "1.0"))
        self.fields = data.get("fields", {})
        self.score_rules = data.get("score_rules", [])
        self.intent_bonus = data.get("intent_bonus", {})
        self.quality = data.get(
            "quality",
            {"high": 70, "medium": 40, "low": 0},
        )
        self.required_fields = data.get("required_fields", [])
        self.object_priority_bonus = data.get("object_priority_bonus", {})

    def validate(self):
        if not self.fields:
            raise ProfileError("Profile contains no fields")
        for rule in self.score_rules:
            if "id" not in rule or "points" not in rule or "condition" not in rule:
                raise ProfileError(f"Invalid score rule: {rule}")
        return self


def load_profile(profiles_dir: Path, name: str) -> Profile:
    path = profiles_dir / name / "profile.json"
    if not path.exists():
        raise ProfileError(f"Profile not found: {name}")
    return Profile(name, json.loads(path.read_text(encoding="utf-8"))).validate()


def list_profiles(profiles_dir: Path) -> list[str]:
    if not profiles_dir.exists():
        return []
    return sorted(
        p.name for p in profiles_dir.iterdir()
        if p.is_dir() and (p / "profile.json").exists()
    )
