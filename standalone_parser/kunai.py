"""Standalone parser helpers for Kunai JSON-lines event logs.

The module is intentionally independent from Plaso so it can be tested on the
development system and reused by the Plaso integration files.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import gzip
import json
import re
from typing import Any, BinaryIO, Iterable, Iterator


KUNAI_LOG_PATH_RE = re.compile(
    r"(^|.*/)?var/log/kunai/events\.log(?:\.\d+)?(?:\.gz)?$"
)


class KunaiParseError(ValueError):
    """Raised when a Kunai record cannot be parsed."""


@dataclass(frozen=True)
class KunaiEvent:
    """Normalized Kunai event extracted from one JSON-lines record."""

    line_number: int
    timestamp: datetime
    timestamp_epoch_microseconds: int
    timestamp_nanoseconds: int
    original_timestamp: str
    event_name: str
    event_id: int | None
    event_uuid: str | None
    event_batch: int | None
    source: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KunaiRecordError:
    """Recoverable parse error for a single Kunai log line."""

    line_number: int
    message: str
    line: str


@dataclass(frozen=True)
class KunaiParseResult:
    """Result of parsing a Kunai JSON-lines stream."""

    events: list[KunaiEvent]
    errors: list[KunaiRecordError]


def is_default_kunai_log_path(path: str) -> bool:
    """Return True if a path matches the default Kunai log naming pattern."""

    normalized_path = path.replace("\\", "/").lstrip("/")
    return bool(KUNAI_LOG_PATH_RE.match(normalized_path))


def looks_like_kunai_record(record: dict[str, Any]) -> bool:
    """Return True if a decoded JSON object has Kunai event structure."""

    info = _get_mapping(record, "info")
    event = _get_mapping(info, "event")
    return event.get("source") == "kunai" and isinstance(info.get("utc_time"), str)


def parse_timestamp(value: str) -> tuple[datetime, int]:
    """Parse Kunai UTC timestamp and return datetime plus nanosecond fraction."""

    match = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2})T"
        r"(?P<time>\d{2}:\d{2}:\d{2})"
        r"(?:\.(?P<fraction>\d{1,9}))?Z",
        value,
    )
    if not match:
        raise KunaiParseError(f"unsupported utc_time value: {value!r}")

    fraction = (match.group("fraction") or "0").ljust(9, "0")
    nanoseconds = int(fraction)
    timestamp = datetime.strptime(
        f"{match.group('date')}T{match.group('time')}", "%Y-%m-%dT%H:%M:%S"
    )
    timestamp = timestamp.replace(
        microsecond=nanoseconds // 1000, tzinfo=timezone.utc
    )
    return timestamp, nanoseconds


def parse_line(line: str, line_number: int) -> KunaiEvent:
    """Parse one Kunai JSON-lines record."""

    stripped_line = line.strip()
    if not stripped_line:
        raise KunaiParseError("empty line")

    try:
        record = json.loads(stripped_line)
    except json.JSONDecodeError as exception:
        raise KunaiParseError(f"invalid JSON: {exception.msg}") from exception

    if not isinstance(record, dict):
        raise KunaiParseError("JSON line is not an object")
    return parse_record(record, line_number)


def parse_record(record: dict[str, Any], line_number: int = 0) -> KunaiEvent:
    """Parse one decoded Kunai JSON record."""

    if not looks_like_kunai_record(record):
        raise KunaiParseError("JSON object is not a Kunai event")

    info = _get_mapping(record, "info")
    event = _get_mapping(info, "event")
    timestamp_value = info.get("utc_time")
    timestamp, nanoseconds = parse_timestamp(str(timestamp_value))

    fields = _flatten_record(record)
    return KunaiEvent(
        line_number=line_number,
        timestamp=timestamp,
        timestamp_epoch_microseconds=_datetime_to_epoch_microseconds(timestamp),
        timestamp_nanoseconds=nanoseconds,
        original_timestamp=str(timestamp_value),
        event_name=str(event.get("name") or "unknown"),
        event_id=_optional_int(event.get("id")),
        event_uuid=_optional_str(event.get("uuid")),
        event_batch=_optional_int(event.get("batch")),
        source=str(event.get("source") or "kunai"),
        fields=fields,
    )


def parse_lines(lines: Iterable[str]) -> KunaiParseResult:
    """Parse Kunai JSON-lines content, keeping recoverable record errors."""

    events: list[KunaiEvent] = []
    errors: list[KunaiRecordError] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            events.append(parse_line(line, line_number))
        except KunaiParseError as exception:
            errors.append(KunaiRecordError(line_number, str(exception), line.rstrip()))
    return KunaiParseResult(events=events, errors=errors)


def iter_text_lines(file_object: BinaryIO, compressed: bool = False) -> Iterator[str]:
    """Yield UTF-8 text lines from a regular or gzip-compressed binary stream."""

    stream: Any
    if compressed:
        stream = gzip.GzipFile(fileobj=file_object)
    else:
        stream = file_object

    pending = ""
    while True:
        data = stream.read(1024 * 1024)
        if not data:
            break
        text = data.decode("utf-8", errors="replace")
        lines = (pending + text).splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            pending = lines.pop()
        else:
            pending = ""
        yield from lines

    if pending:
        yield pending


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten stable Kunai fields into event-data friendly attributes."""

    info = _get_mapping(record, "info")
    data = _get_mapping(record, "data")
    event = _get_mapping(info, "event")
    host = _get_mapping(info, "host")
    container = _get_mapping(host, "container")
    task = _get_mapping(info, "task")
    parent_task = _get_mapping(info, "parent_task")
    exe = _get_mapping(data, "exe")
    target = _get_mapping(data, "target")
    target_task = _get_mapping(target, "task")
    target_exe = _get_mapping(target, "exe")
    socket = _get_mapping(data, "socket")
    src = _get_mapping(data, "src")
    dst = _get_mapping(data, "dst")

    fields: dict[str, Any] = {
        "event_name": event.get("name"),
        "event_id": event.get("id"),
        "event_uuid": event.get("uuid"),
        "event_batch": event.get("batch"),
        "event_source": event.get("source"),
        "host_name": host.get("name"),
        "host_uuid": host.get("uuid"),
        "container_name": container.get("name"),
        "container_type": container.get("type"),
        "process_name": task.get("name"),
        "pid": task.get("pid"),
        "tgid": task.get("tgid"),
        "process_guid": task.get("guuid"),
        "uid": task.get("uid"),
        "user": task.get("user"),
        "gid": task.get("gid"),
        "group": task.get("group"),
        "process_flags": task.get("flags"),
        "process_zombie": task.get("zombie"),
        "parent_process_name": parent_task.get("name"),
        "parent_pid": parent_task.get("pid"),
        "parent_tgid": parent_task.get("tgid"),
        "parent_process_guid": parent_task.get("guuid"),
        "parent_user": parent_task.get("user"),
        "parent_group": parent_task.get("group"),
        "ancestors": data.get("ancestors"),
        "command_line": data.get("command_line"),
        "executable_path": exe.get("path"),
        "path": data.get("path"),
        "success": data.get("success"),
        "signal": data.get("signal"),
        "target_command_line": target.get("command_line"),
        "target_executable_path": target_exe.get("path"),
        "target_process_name": target_task.get("name"),
        "target_pid": target_task.get("pid"),
        "target_tgid": target_task.get("tgid"),
        "socket_domain": socket.get("domain"),
        "socket_type": socket.get("type"),
        "socket_protocol": socket.get("proto"),
        "source_ip": src.get("ip"),
        "source_port": src.get("port"),
        "destination_hostname": dst.get("hostname"),
        "destination_ip": dst.get("ip"),
        "destination_port": dst.get("port"),
        "destination_public": dst.get("public"),
        "destination_is_v6": dst.get("is_v6"),
        "community_id": data.get("community_id"),
        "data_entropy": data.get("data_entropy"),
        "data_size": data.get("data_size"),
    }
    return {key: value for key, value in fields.items() if value is not None}


def _get_mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a nested mapping, or an empty mapping when absent."""

    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def _optional_int(value: Any) -> int | None:
    """Return an integer value when possible."""

    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    """Return a string value when present."""

    if value is None:
        return None
    return str(value)


def _datetime_to_epoch_microseconds(value: datetime) -> int:
    """Return POSIX timestamp microseconds for an aware UTC datetime."""

    return calendar.timegm(value.utctimetuple()) * 1_000_000 + value.microsecond
