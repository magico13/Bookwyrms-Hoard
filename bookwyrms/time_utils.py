"""Datetime helpers for consistent ISO formatting."""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from typing import Optional


def _local_timezone() -> tzinfo:
    tzinfo = datetime.now().astimezone().tzinfo
    return tzinfo or timezone.utc


def ensure_aware(dt: datetime) -> datetime:
    """Ensure datetime has tzinfo, defaulting to local system timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_local_timezone())
    return dt


def to_utc_iso(dt: datetime) -> str:
    """Return ISO-8601 string in UTC with explicit offset."""
    return ensure_aware(dt).astimezone(timezone.utc).isoformat()


def normalize_datetime_string(value: Optional[str]) -> Optional[str]:
    """Normalize stored datetime strings to UTC ISO format."""
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text

    return to_utc_iso(parsed)
