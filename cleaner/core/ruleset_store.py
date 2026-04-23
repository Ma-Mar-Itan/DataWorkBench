"""
Rule-set storage.

Reusable cleaning recipes are persisted to a directory as individual JSON
files. One file per rule set keeps the blast radius of a corrupt save
minimal — a broken set doesn't take the rest down with it.

File naming
-----------
``{slug}.json`` where slug is a filesystem-safe transform of the set name.
The in-memory ``RuleSet.name`` is authoritative — the slug is cosmetic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from models.schemas import RuleSet


DEFAULT_RULESET_DIR = Path("rulesets")


# --------------------------------------------------------------------------- #

def _slugify(name: str) -> str:
    """Turn a human name into a safe filename stem."""
    s = re.sub(r"[^\w\-. ]+", "", name, flags=re.UNICODE).strip()
    s = re.sub(r"\s+", "_", s)
    return (s or "ruleset").lower()


# --------------------------------------------------------------------------- #

class RuleSetStore:
    """Directory-backed store. One file per rule set."""

    def __init__(self, directory: Path = DEFAULT_RULESET_DIR) -> None:
        self.directory = Path(directory)

    # ------------------------------------------------------------------ #

    def list_names(self) -> List[str]:
        """Return the names of all stored rule sets, alphabetically sorted.

        Reads each file to recover the canonical ``name`` — we don't rely on
        the slug because names are mutable but slugs are committed filenames.
        """
        if not self.directory.exists():
            return []
        names: List[str] = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(set(names))

    # ------------------------------------------------------------------ #

    def _path_for_name(self, name: str) -> Path:
        """Return the filepath associated with a rule-set name.

        We scan the directory to honour any existing file whose *content*
        has this name, even if the filename was hand-edited. Falls back to
        the slug-based path for new writes.
        """
        if self.directory.exists():
            for path in self.directory.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("name") == name:
                        return path
                except (OSError, json.JSONDecodeError):
                    continue
        return self.directory / f"{_slugify(name)}.json"

    # ------------------------------------------------------------------ #

    def load(self, name: str) -> RuleSet:
        """Load and deserialize a named rule set. Raises on missing/malformed."""
        path = self._path_for_name(name)
        if not path.exists():
            raise FileNotFoundError(f"Rule set {name!r} not found at {path}.")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return RuleSet.from_dict(data)

    # ------------------------------------------------------------------ #

    def save(self, ruleset: RuleSet) -> Path:
        """Persist a rule set. Returns the file path written."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path_for_name(ruleset.name)
        with path.open("w", encoding="utf-8") as f:
            json.dump(ruleset.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    # ------------------------------------------------------------------ #

    def delete(self, name: str) -> bool:
        """Remove a stored rule set. Returns True if something was deleted."""
        path = self._path_for_name(name)
        if path.exists():
            path.unlink()
            return True
        return False
