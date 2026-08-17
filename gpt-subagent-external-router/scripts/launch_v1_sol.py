#!/usr/bin/env python3
"""Create one persistent Codex Desktop task: Luna/V1 handshake -> Sol Ultra.

The launcher verifies the approved project allowlist and canonical cwd. Desktop
task binding still requires a follow-up lookup by the host application.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from typing import Any
from uuid import UUID


LUNA_MODEL = "gpt-5.6-luna"
SOL_MODEL = "gpt-5.6-sol"
DEFAULT_TIMEOUT_SECONDS = 180
MAX_TIMEOUT_SECONDS = 180


class LauncherError(RuntimeError):
    def __init__(self, code: str, thread_id: str | None = None):
        super().__init__(code)
        self.code = code
        self.thread_id = thread_id


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise LauncherError("invalid_arguments")


def codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    return Path(raw).expanduser().resolve() if raw else (Path.home() / ".codex").resolve()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_projects_registry(home: Path) -> list[dict[str, str]]:
    runtime_dir = home / "gpt-subagent-external-router"
    registry_path = runtime_dir / "projects.json"
    try:
        if runtime_dir.resolve(strict=True) != runtime_dir or registry_path.is_symlink():
            raise LauncherError("projects_registry_invalid")
        if registry_path.resolve(strict=True).parent != runtime_dir:
            raise LauncherError("projects_registry_invalid")
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except LauncherError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LauncherError("projects_registry_unreadable") from exc
    if not isinstance(data, dict) or set(data) != {"version", "projects"} or data.get("version") != 1:
        raise LauncherError("projects_registry_invalid")
    raw_projects = data.get("projects")
    if not isinstance(raw_projects, list) or not raw_projects:
        raise LauncherError("projects_registry_invalid")

    projects: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_cwds: set[str] = set()
    seen_labels: set[str] = set()
    for item in raw_projects:
        if not isinstance(item, dict) or set(item) != {"projectId", "label", "cwd"}:
            raise LauncherError("projects_registry_invalid")
        project_id = item.get("projectId")
        label = item.get("label")
        cwd_text = item.get("cwd")
        if not all(isinstance(value, str) and value.strip() for value in (project_id, label, cwd_text)):
            raise LauncherError("projects_registry_invalid")
        if len(label) > 80 or any(ord(char) < 32 for char in label):
            raise LauncherError("projects_registry_invalid")
        try:
            parsed_id = UUID(project_id)
        except ValueError as exc:
            raise LauncherError("projects_registry_invalid") from exc
        if str(parsed_id) != project_id:
            raise LauncherError("projects_registry_invalid")
        configured_cwd = Path(cwd_text).expanduser()
        if not configured_cwd.is_absolute() or configured_cwd == Path(configured_cwd.anchor):
            raise LauncherError("projects_registry_invalid")
        try:
            resolved_cwd = configured_cwd.resolve(strict=True)
        except OSError as exc:
            raise LauncherError("projects_registry_invalid") from exc
        if not resolved_cwd.is_dir():
            raise LauncherError("projects_registry_invalid")
        canonical = str(resolved_cwd)
        if project_id in seen_ids or canonical in seen_cwds or label in seen_labels:
            raise LauncherError("projects_registry_invalid")
        seen_ids.add(project_id)
        seen_cwds.add(canonical)
        seen_labels.add(label)
        projects.append({"projectId": project_id, "label": label, "cwd": canonical})
    return projects


def resolve_approved_project(
    projects: list[dict[str, str]], project_id: str, cwd: str
) -> tuple[str, Path]:
    matches = [item for item in projects if item["projectId"] == project_id]
    if len(matches) != 1:
        raise LauncherError("project_scope_rejected")
    requested = Path(cwd).expanduser()
    if not requested.is_absolute():
        raise LauncherError("invalid_cwd")
    try:
        canonical = requested.resolve(strict=True)
    except OSError as exc:
        raise LauncherError("invalid_cwd") from exc
    if not canonical.is_dir():
        raise LauncherError("invalid_cwd")
    project = matches[0]
    if str(canonical) != project["cwd"]:
        raise LauncherError("project_binding_mismatch")
    return project["label"], canonical


def fallback_parse_config(text: str) -> tuple[dict[str, str], dict[str, bool]]:
    section = ""
    defaults: dict[str, str] = {}
    features: dict[str, bool] = {}
    string_pattern = re.compile(r"^(model|model_reasoning_effort)\s*=\s*(['\"])(.*?)\2\s*$")
    bool_pattern = re.compile(r"^(multi_agent|multi_agent_v2)\s*=\s*(true|false)\s*$")
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section == "":
            match = string_pattern.fullmatch(line)
            if match:
                defaults[match.group(1)] = match.group(3)
        elif section == "features":
            match = bool_pattern.fullmatch(line)
            if match:
                features[match.group(1)] = match.group(2) == "true"
    return defaults, features


def require_global_defaults(home: Path) -> None:
    config_path = home / "config.toml"
    try:
        config_text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LauncherError("global_config_unreadable") from exc

    try:
        import tomllib

        parsed = tomllib.loads(config_text)
        defaults = {
            "model": parsed.get("model"),
            "model_reasoning_effort": parsed.get("model_reasoning_effort"),
        }
        raw_features = parsed.get("features")
        features = raw_features if isinstance(raw_features, dict) else {}
    except ModuleNotFoundError:
        defaults, features = fallback_parse_config(config_text)
    except Exception as exc:
        raise LauncherError("global_config_invalid") from exc

    if defaults.get("model") != SOL_MODEL or defaults.get("model_reasoning_effort") != "ultra":
        raise LauncherError("global_defaults_required")
    if features.get("multi_agent") is not True or features.get("multi_agent_v2") is not False:
        raise LauncherError("global_v1_required")


def require_codex_state_outside_project(home: Path, project_cwd: Path) -> None:
    paths = [
        home,
        home / "config.toml",
        home / "gpt-subagent-external-router",
        home / "sessions",
        home / "archived_sessions",
    ]
    for path in paths:
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if is_within(resolved, project_cwd):
            raise LauncherError("codex_state_inside_project")


def executable_candidate(raw: str) -> Path | None:
    expanded = Path(raw).expanduser()
    if expanded.is_file() and os.access(expanded, os.X_OK):
        return expanded.resolve()
    found = shutil.which(raw)
    if found:
        candidate = Path(found)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def locate_codex_app_cli() -> Path:
    override = os.environ.get("CODEX_APP_CLI")
    if override:
        candidate = executable_candidate(override.strip())
        if candidate is None:
            raise LauncherError("codex_app_cli_invalid")
        return candidate

    candidates = (
        Path("/Applications/Codex.app/Contents/Resources/codex"),
        Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
        Path.home() / "Applications/Codex.app/Contents/Resources/codex",
        Path.home() / "Applications/ChatGPT.app/Contents/Resources/codex",
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise LauncherError("desktop_codex_missing")


def codex_cli_version(binary: Path) -> str:
    try:
        completed = subprocess.run(
            [str(binary), "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LauncherError("app_server_version_unavailable") from exc
    version = completed.stdout.strip()
    if not version.startswith("codex-cli "):
        raise LauncherError("app_server_version_unavailable")
    return version.removeprefix("codex-cli ")


class ExclusiveLock:
    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None
        self.identity: tuple[int, int] | None = None

    def __enter__(self) -> "ExclusiveLock":
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as exc:
            raise LauncherError("lock_unavailable") from exc
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        try:
            self.fd = os.open(self.path, flags, 0o600)
        except FileExistsError as exc:
            raise LauncherError("already_running") from exc
        except OSError as exc:
            raise LauncherError("lock_unavailable") from exc
        try:
            current = os.fstat(self.fd)
            self.identity = (current.st_dev, current.st_ino)
            os.write(self.fd, b'{"state":"running"}\n')
        except OSError as exc:
            try:
                os.close(self.fd)
            finally:
                self.fd = None
                try:
                    path_state = self.path.lstat()
                except OSError:
                    path_state = None
                if (
                    path_state is not None
                    and self.identity is not None
                    and not stat.S_ISLNK(path_state.st_mode)
                    and (path_state.st_dev, path_state.st_ino) == self.identity
                ):
                    try:
                        self.path.unlink()
                    except OSError:
                        pass
            raise LauncherError("lock_unavailable") from exc
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        try:
            current = self.path.lstat()
        except OSError:
            return
        if (
            self.identity is not None
            and not stat.S_ISLNK(current.st_mode)
            and (current.st_dev, current.st_ino) == self.identity
        ):
            try:
                self.path.unlink()
            except OSError:
                pass


class AppServer:
    def __init__(self, binary: Path, deadline: float, runtime_dir: Path):
        self.binary = binary
        self.deadline = deadline
        self.runtime_dir = runtime_dir
        self.proc: subprocess.Popen[str] | None = None
        self.messages: queue.Queue[str | None] = queue.Queue()
        self.next_id = 1

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [str(self.binary), "app-server", "--stdio"],
            cwd=str(self.runtime_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "gpt-subagent-external-router",
                    "title": "GPT Subagent External Router",
                    "version": "1.0.0",
                }
            },
        )
        self.notify("initialized", {})

    def _read_stdout(self) -> None:
        proc = self.proc
        if proc is None or proc.stdout is None:
            self.messages.put(None)
            return
        try:
            for line in proc.stdout:
                self.messages.put(line)
        finally:
            self.messages.put(None)

    def close(self) -> None:
        proc = self.proc
        if proc is None:
            return
        if proc.stdin is not None and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except OSError:
                pass
        try:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
        except (OSError, subprocess.SubprocessError):
            pass

    def _write(self, payload: dict[str, Any]) -> None:
        proc = self.proc
        if proc is None or proc.stdin is None or proc.poll() is not None:
            raise LauncherError("app_server_unavailable")
        try:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
            proc.stdin.flush()
        except OSError as exc:
            raise LauncherError("app_server_unavailable") from exc

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            message = self._read_message()
            if message.get("id") == request_id:
                if "error" in message:
                    raise LauncherError("app_server_request_failed")
                result = message.get("result")
                if not isinstance(result, dict):
                    raise LauncherError("app_server_response_invalid")
                return result
            if "method" in message and "id" in message:
                raise LauncherError("unexpected_server_request")

    def _read_message(self) -> dict[str, Any]:
        while time.monotonic() < self.deadline:
            proc = self.proc
            if proc is None:
                raise LauncherError("app_server_unavailable")
            remaining = max(0.0, self.deadline - time.monotonic())
            try:
                line = self.messages.get(timeout=min(1.0, remaining))
            except queue.Empty:
                if proc.poll() is not None:
                    raise LauncherError("app_server_exited")
                continue
            if line is None:
                raise LauncherError("app_server_exited")
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise LauncherError("timeout")


def find_rollout(home: Path, thread_id: str, deadline: float) -> Path:
    while time.monotonic() < deadline:
        matches: list[Path] = []
        for folder in (home / "sessions", home / "archived_sessions"):
            if folder.is_dir():
                matches.extend(folder.rglob(f"*{thread_id}.jsonl"))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            exact = [path for path in matches if path.name.endswith(f"-{thread_id}.jsonl")]
            if len(exact) == 1:
                return exact[0]
            raise LauncherError("ambiguous_rollout", thread_id)
        time.sleep(0.1)
    raise LauncherError("rollout_missing", thread_id)


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    records.append(value)
    except (OSError, UnicodeError) as exc:
        raise LauncherError("rollout_unreadable") from exc
    return records


def verify_turn_context(
    rollout: Path,
    thread_id: str,
    turn_id: str,
    expected_model: str,
    expected_effort: str,
    expected_cwd: str,
    expected_reply: str,
    deadline: float,
) -> None:
    while time.monotonic() < deadline:
        records = read_json_lines(rollout)
        session_ok = any(
            record.get("type") == "session_meta"
            and isinstance(record.get("payload"), dict)
            and record["payload"].get("id") == thread_id
            and record["payload"].get("cwd") == expected_cwd
            for record in records
        )
        context: dict[str, Any] | None = None
        context_index = -1
        for index, record in enumerate(records):
            payload = record.get("payload")
            if (
                record.get("type") == "turn_context"
                and isinstance(payload, dict)
                and payload.get("turn_id") == turn_id
            ):
                context = payload
                context_index = index
                break
        if session_ok and context is not None:
            completed = False
            tool_call_seen = False
            final_reply: str | None = None
            for record in records[context_index + 1 :]:
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue
                if record.get("type") == "event_msg" and payload.get("type") == "task_complete":
                    if payload.get("turn_id") == turn_id:
                        completed = True
                        reply = payload.get("last_agent_message")
                        final_reply = reply if isinstance(reply, str) else None
                        break
                if record.get("type") == "response_item" and payload.get("type") not in {
                    "message",
                    "reasoning",
                }:
                    tool_call_seen = True
                    break
            if not completed:
                time.sleep(0.1)
                continue
            workspace_roots = context.get("workspace_roots")
            valid = (
                context.get("model") == expected_model
                and context.get("effort") == expected_effort
                and context.get("multi_agent_version") == "v1"
                and context.get("cwd") == expected_cwd
                and isinstance(workspace_roots, list)
                and expected_cwd in workspace_roots
                and not tool_call_seen
                and final_reply == expected_reply
            )
            if not valid:
                raise LauncherError("v1_override_failed", thread_id)
            return
        time.sleep(0.1)
    raise LauncherError("metadata_timeout", thread_id)


def start_turn(
    server: AppServer,
    thread_id: str,
    prompt: str,
    model: str,
    effort: str,
    sandbox_policy: dict[str, Any],
    approval_policy: Any,
) -> str:
    result = server.request(
        "turn/start",
        {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt}],
            "model": model,
            "effort": effort,
            "sandboxPolicy": sandbox_policy,
            "approvalPolicy": approval_policy,
        },
    )
    turn = result.get("turn")
    turn_id = turn.get("id") if isinstance(turn, dict) else None
    if not isinstance(turn_id, str) or not turn_id:
        raise LauncherError("turn_id_missing", thread_id)
    return turn_id


def parse_args() -> argparse.Namespace:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        choices=range(30, MAX_TIMEOUT_SECONDS + 1),
        metavar="30..180",
    )
    return parser.parse_args()


def run() -> dict[str, Any]:
    args = parse_args()
    home = codex_home()
    projects = load_projects_registry(home)
    project_label, project_cwd = resolve_approved_project(projects, args.project_id, args.cwd)
    require_codex_state_outside_project(home, project_cwd)
    require_global_defaults(home)
    binary = locate_codex_app_cli()
    if is_within(binary, project_cwd):
        raise LauncherError("codex_app_cli_inside_project")
    cli_version = codex_cli_version(binary)

    runtime_dir = home / "gpt-subagent-external-router"
    lock_path = runtime_dir / "launch.lock"
    with ExclusiveLock(lock_path):
        deadline = time.monotonic() + args.timeout_seconds
        server = AppServer(binary, deadline, runtime_dir)
        thread_id: str | None = None
        try:
            server.start()
            started = server.request(
                "thread/start",
                {
                    "cwd": str(project_cwd),
                    "model": LUNA_MODEL,
                    "config": {
                        "features": {"multi_agent": True, "multi_agent_v2": False},
                        "project_doc_max_bytes": 0,
                        "project_doc_fallback_filenames": [],
                    },
                    "ephemeral": False,
                },
            )
            thread = started.get("thread")
            thread = thread if isinstance(thread, dict) else {}
            thread_id = thread.get("id")
            if not isinstance(thread_id, str):
                raise LauncherError("thread_id_missing")
            try:
                UUID(thread_id)
            except ValueError as exc:
                raise LauncherError("thread_id_invalid", thread_id) from exc

            started_cwd = started.get("cwd", thread.get("cwd"))
            started_model = started.get("model", thread.get("model"))
            if started_cwd != str(project_cwd) or started_model != LUNA_MODEL:
                raise LauncherError("thread_start_override_failed", thread_id)
            original_sandbox = started.get("sandbox", thread.get("sandbox"))
            original_approval = started.get("approvalPolicy", thread.get("approvalPolicy"))
            if not isinstance(original_sandbox, dict) or original_approval is None:
                raise LauncherError("thread_defaults_missing", thread_id)

            luna_turn_id = start_turn(
                server,
                thread_id,
                "Protocol bootstrap only. Do not read or modify files and do not call tools. Reply exactly READY_V1.",
                LUNA_MODEL,
                "low",
                {"type": "readOnly", "networkAccess": False},
                "never",
            )
            rollout = find_rollout(home, thread_id, deadline)
            verify_turn_context(
                rollout,
                thread_id,
                luna_turn_id,
                LUNA_MODEL,
                "low",
                str(project_cwd),
                "READY_V1",
                deadline,
            )

            sol_turn_id = start_turn(
                server,
                thread_id,
                "Protocol handoff only. Do not read or modify files and do not call tools. Reply exactly READY_SOL_ULTRA.",
                SOL_MODEL,
                "ultra",
                original_sandbox,
                original_approval,
            )
            verify_turn_context(
                rollout,
                thread_id,
                sol_turn_id,
                SOL_MODEL,
                "ultra",
                str(project_cwd),
                "READY_SOL_ULTRA",
                deadline,
            )
        except LauncherError as exc:
            if exc.thread_id is None and thread_id is not None:
                exc.thread_id = thread_id
            raise
        except Exception as exc:
            raise LauncherError("launcher_internal_error", thread_id) from exc
        finally:
            server.close()

    return {
        "ok": True,
        "threadId": thread_id,
        "requestedProjectId": args.project_id,
        "projectLabel": project_label,
        "cwd": str(project_cwd),
        "projectBinding": "desktop_required",
        "model": SOL_MODEL,
        "effort": "ultra",
        "multiAgentVersion": "v1",
        "globalMultiAgentV2": False,
        "codexCliVersion": cli_version,
    }


def main() -> int:
    try:
        payload = run()
    except LauncherError as exc:
        error: dict[str, Any] = {"ok": False, "error": exc.code}
        if exc.thread_id is not None:
            error["threadId"] = exc.thread_id
        print(json.dumps(error, separators=(",", ":")), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('{"ok":false,"error":"interrupted"}', file=sys.stderr)
        return 130
    except Exception:
        print('{"ok":false,"error":"internal_error"}', file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
