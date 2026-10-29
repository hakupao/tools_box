"""Masking profile: settings model with v2 config coercion rules."""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dataforge.config.legacy import load_section_with_legacy
from dataforge.config.store import ConfigStore

CONFIG_SECTION = "data_masking_pattern1"
LEGACY_FILE_NAME = "data_masking_pattern1_config.json"
REMOVED_KEYS = frozenset({"subject_sort", "date_output_format", "partial_date_policy"})

_STR_KEYS = (
    "studyid_value",
    "sequential_prefix",
    "doctor_value",
    "site_field",
    "site_value",
    "age_field",
)
_INT_KEYS = (
    "subject_limit",
    "sequential_width",
    "sequential_start",
    "date_shift_years",
    "age_shift_years",
    "date_detect_sample_size",
    "date_detect_min_non_empty",
)
_BOOL_KEYS = ("include_subjid", "doctor_replace_enabled", "site_replace_enabled")
_USUBJID_MODES = ("sequential", "rule_chain")


@dataclass
class RuleStep:
    op: str
    value: Any


def _default_steps() -> list[RuleStep]:
    return [
        RuleStep("remove_prefix", 4),
        RuleStep("remove_suffix", 0),
        RuleStep("prepend", "SKLT"),
        RuleStep("append", ""),
    ]


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
        return default
    return bool(value)


@dataclass
class MaskingProfile:
    studyid_value: str = "[UAT]CIRCULATE"
    subject_limit: int = 100
    usubjid_mode: str = "sequential"  # sequential | rule_chain
    rule_chain_steps: list[RuleStep] = field(default_factory=_default_steps)
    sequential_prefix: str = "TEST"
    sequential_width: int = 4
    sequential_start: int = 1
    date_shift_years: int = -2
    age_shift_years: int = -2
    date_detect_sample_size: int = 200
    date_detect_min_non_empty: int = 20
    date_detect_success_ratio: float = 0.8
    doctor_fields: list[str] = field(default_factory=lambda: ["INVNAM"])
    doctor_value: str = "テスト医師"
    doctor_replace_enabled: bool = True
    site_field: str = "SITEID"
    site_value: str = "テスト施設"
    site_replace_enabled: bool = True
    age_field: str = "AGE"
    include_subjid: bool = True

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> MaskingProfile:
        profile = cls()

        for key in _STR_KEYS:
            if raw.get(key) is not None:
                setattr(profile, key, str(raw[key]))

        if raw.get("usubjid_mode") is not None:
            mode = str(raw["usubjid_mode"])
            profile.usubjid_mode = mode if mode in _USUBJID_MODES else "sequential"

        for key in _INT_KEYS:
            if raw.get(key) is not None:
                try:
                    setattr(profile, key, int(raw[key]))
                except (TypeError, ValueError):
                    pass

        if raw.get("date_detect_success_ratio") is not None:
            try:
                profile.date_detect_success_ratio = float(raw["date_detect_success_ratio"])
            except (TypeError, ValueError):
                pass

        if isinstance(raw.get("doctor_fields"), list):
            profile.doctor_fields = [str(x).strip() for x in raw["doctor_fields"] if str(x).strip()]

        for key in _BOOL_KEYS:
            if key in raw:
                setattr(profile, key, _coerce_bool(raw[key], getattr(profile, key)))

        if isinstance(raw.get("rule_chain_steps"), list):
            steps = [
                RuleStep(op=str(s.get("op", "")).strip(), value=s.get("value", ""))
                for s in raw["rule_chain_steps"]
                if isinstance(s, dict)
            ]
            if steps:
                profile.rule_chain_steps = steps

        return profile

    def to_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data["rule_chain_steps"] = [{"op": s.op, "value": s.value} for s in self.rule_chain_steps]
        return data


LEGACY_KEYS: frozenset[str] = (
    frozenset(f.name for f in dataclasses.fields(MaskingProfile)) | REMOVED_KEYS
)


def load_profile(store: ConfigStore, legacy_files: Sequence[Path] = ()) -> MaskingProfile:
    raw = load_section_with_legacy(store, CONFIG_SECTION, LEGACY_KEYS, legacy_files)
    return MaskingProfile.from_dict(raw)


def save_profile(store: ConfigStore, profile: MaskingProfile) -> bool:
    return store.update_section(CONFIG_SECTION, profile.to_dict())
