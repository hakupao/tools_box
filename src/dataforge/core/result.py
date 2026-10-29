"""Processing result container."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileIssue:
    path: str
    message: str


@dataclass(frozen=True)
class EncodingQuestion:
    path: str
    previews: dict[str, str]


@dataclass
class Result:
    outputs: list[Path] = field(default_factory=list)
    warnings: list[FileIssue] = field(default_factory=list)
    errors: list[FileIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    encoding_questions: list[EncodingQuestion] = field(default_factory=list)
    data: Any = None  # structured payload of the task; not merged by extend()

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_output(self, path: Path) -> None:
        self.outputs.append(path)

    def warn(self, path: str | Path, message: str) -> None:
        self.warnings.append(FileIssue(str(path), message))

    def fail(self, path: str | Path, message: str) -> None:
        self.errors.append(FileIssue(str(path), message))

    def count(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n

    def ask_encoding(self, path: str | Path, previews: dict[str, str]) -> None:
        self.encoding_questions.append(EncodingQuestion(str(path), previews))

    def extend(self, other: Result) -> None:
        self.outputs.extend(other.outputs)
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)
        self.encoding_questions.extend(other.encoding_questions)
        for key, n in other.stats.items():
            self.count(key, n)
