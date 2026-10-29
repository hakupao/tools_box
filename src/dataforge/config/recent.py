"""Recent-use history stored in the shared config."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .store import ConfigStore


@dataclass(frozen=True)
class RecentEntry:
    tool_id: str
    summary: str
    state: dict[str, Any]
    timestamp: str


class RecentStore:
    SECTION = "recent"

    def __init__(self, store: ConfigStore, limit: int = 10) -> None:
        self._store = store
        self._limit = limit

    def entries(self) -> list[RecentEntry]:
        raw = self._store.section(self.SECTION).get("entries", [])
        result: list[RecentEntry] = []
        if not isinstance(raw, list):
            return result
        for item in raw:
            if not isinstance(item, dict):
                continue
            tool_id, summary = item.get("tool_id"), item.get("summary")
            state, ts = item.get("state"), item.get("timestamp")
            if not (
                isinstance(tool_id, str)
                and isinstance(summary, str)
                and isinstance(state, dict)
                and isinstance(ts, str)
            ):
                continue
            result.append(RecentEntry(tool_id, summary, state, ts))
        return result

    def add(self, tool_id: str, summary: str, state: dict[str, Any]) -> RecentEntry:
        entry = RecentEntry(
            tool_id, summary, state, datetime.now().isoformat(timespec="seconds")
        )
        kept = [e for e in self.entries() if not (e.tool_id == tool_id and e.state == state)]
        self._save([entry, *kept][: self._limit])
        return entry

    def clear(self) -> None:
        self._save([])

    def _save(self, entries: list[RecentEntry]) -> None:
        data = {
            "entries": [
                {"tool_id": e.tool_id, "summary": e.summary, "state": e.state,
                 "timestamp": e.timestamp}
                for e in entries
            ]
        }
        self._store.update_section(self.SECTION, data)
