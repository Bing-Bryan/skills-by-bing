#!/usr/bin/env python3
"""Validate V1-Sol project and provider registries without exposing their data."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID


TRANSPORTS = {
    "responses-direct",
    "responses-adapter-dedicated",
    "tool-mcp",
}
STATUSES = {"verified-pattern", "conditional", "experimental"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENV_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class RegistryError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RegistryError("invalid_arguments")


def codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    return Path(raw).expanduser().resolve() if raw else (Path.home() / ".codex").resolve()


def load_json_object(path: Path, code: str) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.resolve(strict=True).is_file():
            raise RegistryError(code)
        value = json.loads(path.read_text(encoding="utf-8"))
    except RegistryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(code) from exc
    if not isinstance(value, dict):
        raise RegistryError(code)
    return value


def require_text(value: Any, code: str, maximum: int = 240) -> str:
    if not isinstance(value, str):
        raise RegistryError(code)
    text = value.strip()
    if not text or len(text) > maximum or any(ord(char) < 32 for char in text):
        raise RegistryError(code)
    return text


def validate_projects(path: Path, require_existing_cwds: bool = True) -> dict[str, int]:
    data = load_json_object(path, "projects_registry_unreadable")
    if set(data) != {"version", "projects"} or data.get("version") != 1:
        raise RegistryError("projects_registry_schema_invalid")
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        raise RegistryError("projects_registry_schema_invalid")

    seen_ids: set[str] = set()
    seen_cwds: set[str] = set()
    seen_labels: set[str] = set()
    for item in projects:
        if not isinstance(item, dict) or set(item) != {"projectId", "label", "cwd"}:
            raise RegistryError("projects_registry_schema_invalid")
        project_id = require_text(item.get("projectId"), "project_id_invalid", 64)
        try:
            parsed_id = UUID(project_id)
        except ValueError as exc:
            raise RegistryError("project_id_invalid") from exc
        if str(parsed_id) != project_id:
            raise RegistryError("project_id_invalid")
        label = require_text(item.get("label"), "project_label_invalid", 80)
        cwd_text = require_text(item.get("cwd"), "project_cwd_invalid", 4096)
        cwd = Path(cwd_text).expanduser()
        if not cwd.is_absolute() or cwd == Path(cwd.anchor):
            raise RegistryError("project_cwd_invalid")
        try:
            canonical = cwd.resolve(strict=require_existing_cwds)
        except OSError as exc:
            raise RegistryError("project_cwd_invalid") from exc
        if require_existing_cwds and not canonical.is_dir():
            raise RegistryError("project_cwd_invalid")
        canonical_text = str(canonical)
        if project_id in seen_ids or canonical_text in seen_cwds or label in seen_labels:
            raise RegistryError("projects_registry_duplicate")
        seen_ids.add(project_id)
        seen_cwds.add(canonical_text)
        seen_labels.add(label)
    return {"count": len(projects)}


def validate_base_url(value: Any) -> str:
    url = require_text(value, "provider_base_url_invalid", 2048)
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if (
        scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RegistryError("provider_base_url_invalid")
    try:
        port = parsed.port
    except ValueError as exc:
        raise RegistryError("provider_base_url_invalid") from exc
    if scheme == "http" and hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RegistryError("provider_base_url_invalid")
    host_for_url = f"[{hostname}]" if ":" in hostname else hostname
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host_for_url if port is None or default_port else f"{host_for_url}:{port}"
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def validate_common_provider(item: dict[str, Any]) -> tuple[str, str, str]:
    provider_id = require_text(item.get("providerId"), "provider_id_invalid", 80)
    if ID_PATTERN.fullmatch(provider_id) is None:
        raise RegistryError("provider_id_invalid")
    require_text(item.get("label"), "provider_label_invalid", 120)
    transport = require_text(item.get("transport"), "provider_transport_invalid", 64)
    if transport not in TRANSPORTS:
        raise RegistryError("provider_transport_invalid")
    status = require_text(item.get("status"), "provider_status_invalid", 32)
    if status not in STATUSES:
        raise RegistryError("provider_status_invalid")
    require_text(item.get("notes"), "provider_notes_invalid", 600)
    return provider_id, transport, status


def validate_providers(path: Path) -> dict[str, Any]:
    data = load_json_object(path, "providers_registry_unreadable")
    if set(data) != {"version", "providers"} or data.get("version") != 1:
        raise RegistryError("providers_registry_schema_invalid")
    providers = data.get("providers")
    if not isinstance(providers, list) or not providers:
        raise RegistryError("providers_registry_schema_invalid")

    model_keys = {
        "providerId",
        "label",
        "transport",
        "baseUrl",
        "model",
        "apiKeyEnv",
        "wireApi",
        "status",
        "notes",
    }
    adapter_keys = model_keys | {"immutable"}
    tool_keys = {
        "providerId",
        "label",
        "transport",
        "mcpServer",
        "toolName",
        "readOnly",
        "status",
        "notes",
    }
    seen_ids: set[str] = set()
    seen_model_urls: set[str] = set()
    counts: Counter[str] = Counter()

    for item in providers:
        if not isinstance(item, dict):
            raise RegistryError("providers_registry_schema_invalid")
        provider_id, transport, _ = validate_common_provider(item)
        if provider_id in seen_ids:
            raise RegistryError("providers_registry_duplicate")
        seen_ids.add(provider_id)
        counts[transport] += 1

        if transport in {"responses-direct", "responses-adapter-dedicated"}:
            expected_keys = adapter_keys if transport == "responses-adapter-dedicated" else model_keys
            if set(item) != expected_keys:
                raise RegistryError("providers_registry_schema_invalid")
            base_url = validate_base_url(item.get("baseUrl"))
            if base_url in seen_model_urls:
                raise RegistryError("provider_endpoint_shared")
            seen_model_urls.add(base_url)
            require_text(item.get("model"), "provider_model_invalid", 160)
            api_key_env = require_text(item.get("apiKeyEnv"), "provider_api_key_env_invalid", 160)
            if ENV_PATTERN.fullmatch(api_key_env) is None:
                raise RegistryError("provider_api_key_env_invalid")
            if item.get("wireApi") != "responses":
                raise RegistryError("provider_wire_api_invalid")
            if transport == "responses-adapter-dedicated" and item.get("immutable") is not True:
                raise RegistryError("provider_adapter_not_immutable")
        else:
            if set(item) != tool_keys:
                raise RegistryError("providers_registry_schema_invalid")
            mcp_server = require_text(item.get("mcpServer"), "provider_mcp_name_invalid", 160)
            tool_name = require_text(item.get("toolName"), "provider_tool_name_invalid", 160)
            if NAME_PATTERN.fullmatch(mcp_server) is None or NAME_PATTERN.fullmatch(tool_name) is None:
                raise RegistryError("provider_tool_name_invalid")
            if item.get("readOnly") is not True:
                raise RegistryError("provider_tool_not_read_only")

    return {
        "count": len(providers),
        "transports": {name: counts[name] for name in sorted(TRANSPORTS)},
    }


def parse_args() -> argparse.Namespace:
    home = codex_home()
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects",
        type=Path,
        default=home / "gpt-subagent-external-router" / "projects.json",
    )
    parser.add_argument(
        "--providers",
        type=Path,
        default=home / "gpt-subagent-external-router" / "providers.json",
    )
    parser.add_argument(
        "--allow-missing-cwds",
        action="store_true",
        help="validate an example registry whose project directories do not exist",
    )
    return parser.parse_args()


def run() -> dict[str, Any]:
    args = parse_args()
    projects = validate_projects(args.projects, not args.allow_missing_cwds)
    providers: dict[str, Any] | None = None
    if args.providers.exists():
        providers = validate_providers(args.providers)
    return {"ok": True, "projects": projects, "providers": providers}


def main() -> int:
    try:
        payload = run()
    except RegistryError as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")),
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print('{"ok":false,"error":"interrupted"}', file=sys.stderr)
        return 130
    except Exception:
        print('{"ok":false,"error":"internal_error"}', file=sys.stderr)
        return 1
    print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
