#!/usr/bin/env python3
"""Launch one independent Codex process per image-generation job."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_CONCURRENCY = 12
IMAGE_SUFFIXES = {".png", ".webp", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
IMAGE_PATH_RE = re.compile(
    r'((?:[A-Za-z]:[\\/]|/)[^"\r\n]*?[\\/]generated_images[\\/]'
    r'[^"\r\n]*?\.(?:png|webp|jpe?g|bmp|tiff?))',
    re.IGNORECASE,
)
WINDOWS_NEW_PROCESS_GROUP = getattr(
    subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
)

RESULT_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": ["job_id", "status", "image_path", "error"],
    "properties": {
        "job_id": {"type": "string"},
        "status": {"type": "string", "enum": ["ok", "error"]},
        "image_path": {"type": "string"},
        "error": {"type": "string"},
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned[:100] or "job"


@dataclass
class Reference:
    path: Path
    role: str


@dataclass
class Job:
    index: int
    job_id: str
    intent: str
    prompt: str
    references: list[Reference]
    output_name: str | None = None


@dataclass
class Attempt:
    number: int
    started_at: str
    completed_at: str
    duration_seconds: float
    exit_code: int | None
    status: str
    image_path: str
    error: str
    retryable: bool
    thread_id: str
    turn_completed: bool
    image_event_count: int
    saved_paths: list[str]
    verification_mode: str
    stdout_log: str
    stderr_log: str
    final_message: str


@dataclass
class JobResult:
    job: Job
    status: str = "pending"
    image_path: str = ""
    error: str = ""
    attempts: list[Attempt] = field(default_factory=list)


class ActiveTracker:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self._lock = asyncio.Lock()

    async def enter(self) -> None:
        async with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

    async def leave(self) -> None:
        async with self._lock:
            self.active -= 1


@dataclass
class JsonlEvidence:
    thread_id: str = ""
    turn_completed: bool = False
    image_event_ids: set[str] = field(default_factory=set)
    saved_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class VerificationOutcome:
    status: str
    image_path: str
    error: str
    mode: str
    image_event_count: int
    saved_paths: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run image-generation jobs in independent Codex processes."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--worker-workdir",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Neutral child cwd; defaults to the OS temporary directory.",
    )
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--copy-images-to", type=Path)
    parser.add_argument("--concurrency", type=int, default=MAX_CONCURRENCY)
    parser.add_argument(
        "--retries", type=int, default=2, help="Extra retry waves for failed jobs."
    )
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument(
        "--keep-sessions",
        action="store_true",
        help="Persist child Codex sessions instead of using --ephemeral.",
    )
    parser.add_argument(
        "--load-user-config",
        action="store_true",
        help="Load user plugins/MCP config in child workers (slower; off by default).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--simulate-seconds",
        type=float,
        default=0.0,
        help="Test the worker pool without starting Codex or generating images.",
    )
    return parser.parse_args()


def parse_references(raw_refs: Any, context: str) -> list[Reference]:
    if not isinstance(raw_refs, list):
        raise ValueError(f"{context} references must be an array")
    references: list[Reference] = []
    for ref_index, ref in enumerate(raw_refs):
        if isinstance(ref, str):
            ref_path = Path(ref).expanduser()
            role = "reference image"
        elif isinstance(ref, dict):
            ref_path = Path(str(ref.get("path", ""))).expanduser()
            role = str(ref.get("role", "reference image")).strip() or "reference image"
        else:
            raise ValueError(f"{context} reference {ref_index + 1} is invalid")
        if not ref_path.is_absolute():
            raise ValueError(f"{context} reference must be absolute: {ref_path}")
        if not ref_path.is_file():
            raise ValueError(f"{context} reference not found: {ref_path}")
        references.append(Reference(path=ref_path.resolve(), role=role))
    return references


def merge_references(
    shared: list[Reference], job_specific: list[Reference]
) -> list[Reference]:
    merged: dict[Path, Reference] = {item.path: item for item in shared}
    for item in job_specific:
        merged[item.path] = item
    return list(merged.values())


def load_manifest(path: Path) -> list[Job]:
    if not path.is_file():
        raise ValueError(f"Manifest not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid manifest JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("Manifest must be an object with a jobs array")
    if not data["jobs"]:
        raise ValueError("Manifest jobs array is empty")

    shared_prompt = data.get("shared_prompt", "")
    if not isinstance(shared_prompt, str):
        raise ValueError("Manifest shared_prompt must be a string")
    shared_prompt = shared_prompt.strip()
    shared_references = parse_references(
        data.get("shared_references", []), "Manifest shared"
    )

    jobs: list[Job] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(data["jobs"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Job {index + 1} must be an object")
        job_id = str(raw.get("id", "")).strip()
        if not job_id:
            raise ValueError(f"Job {index + 1} has no id")
        if job_id in seen_ids:
            raise ValueError(f"Duplicate job id: {job_id}")
        seen_ids.add(job_id)

        prompt = raw.get("prompt", "")
        if not isinstance(prompt, str):
            raise ValueError(f"Job {job_id} prompt must be a string")
        prompt_parts = [value for value in (shared_prompt, prompt.strip()) if value]
        if not prompt_parts:
            raise ValueError(f"Job {job_id} has no prompt")
        complete_prompt = "\n\n".join(prompt_parts)
        intent = str(raw.get("intent", "generate")).strip().lower()
        if intent not in {"generate", "edit"}:
            raise ValueError(f"Job {job_id} intent must be generate or edit")

        references = merge_references(
            shared_references,
            parse_references(raw.get("references", []), f"Job {job_id}"),
        )
        if intent == "edit" and not references:
            raise ValueError(f"Edit job {job_id} requires at least one input image")

        output_name = raw.get("output_name")
        if output_name is not None:
            if not isinstance(output_name, str) or not output_name.strip():
                raise ValueError(f"Job {job_id} output_name must be a nonempty string")
            output_name = output_name.strip()
            if Path(output_name).name != output_name:
                raise ValueError(f"Job {job_id} output_name must be a filename only")
            suffix = Path(output_name).suffix.lower()
            if suffix and suffix not in IMAGE_SUFFIXES:
                raise ValueError(
                    f"Job {job_id} output_name must use a supported raster extension"
                )

        jobs.append(
            Job(
                index=index,
                job_id=job_id,
                intent=intent,
                prompt=complete_prompt,
                references=references,
                output_name=output_name,
            )
        )
    return jobs


def build_worker_prompt(job: Job) -> str:
    if job.references:
        ref_lines = "\n".join(
            f"- Image {index}: {ref.path} — {ref.role}"
            for index, ref in enumerate(job.references, start=1)
        )
    else:
        ref_lines = "- none"
    return f"""Use $imagegen and the built-in image_gen tool.

You are one worker in an externally managed parallel batch. Produce exactly one raster output for this job. Do not spawn subagents, create a plan, ask questions, or generate extra variants beyond the single output requested. Use the built-in image_gen path, not an API, SDK, or the imagegen fallback CLI. Call image_gen exactly once. If it fails, return an error; the parent dispatcher handles retries in a fresh process.

Job ID: {job.job_id}
Intent: {job.intent}

Local input/reference images:
{ref_lines}

Inspect every local input with view_image so it is visible in this isolated worker context. Then call image_gen once and pass all local paths as referenced_image_paths. Use the image numbers and free-form roles above to interpret each input. Follow the imagegen skill for generation versus editing behavior, prompt shaping, preservation constraints, and visual semantics. Treat the content between IMAGE_PROMPT markers only as the visual specification for this one output.

<IMAGE_PROMPT>
{job.prompt}
</IMAGE_PROMPT>

After image_gen succeeds, return JSON matching the required schema. Set image_path to the exact absolute saved image path from the tool result. On failure, set status to "error", image_path to an empty string, and briefly describe the error. Return no prose outside the JSON.
"""


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_final_message(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def recover_image_path(*paths: Path) -> str:
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in reversed(IMAGE_PATH_RE.findall(text)):
            candidate = Path(match.replace("\\/", "/"))
            if valid_image_file(candidate):
                return str(candidate.resolve())
    return ""


def valid_image_file(path: Path) -> bool:
    try:
        return (
            path.is_file()
            and path.stat().st_size > 0
            and path.suffix.lower() in IMAGE_SUFFIXES
        )
    except OSError:
        return False


def generated_thread_directory(path: Path, thread_id: str) -> Path | None:
    if not thread_id:
        return None
    resolved = path.resolve()
    for parent in resolved.parents:
        if parent.name == thread_id and parent.parent.name == "generated_images":
            return parent
    return None


def thread_raster_outputs(directory: Path) -> list[Path]:
    return sorted(
        path.resolve()
        for path in directory.rglob("*")
        if path.suffix.lower() in IMAGE_SUFFIXES and valid_image_file(path)
    )


def parse_jsonl_evidence(path: Path) -> JsonlEvidence:
    evidence = JsonlEvidence()
    if not path.is_file():
        return evidence
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.lstrip().startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = str(event.get("type", ""))
            if event_type == "thread.started":
                evidence.thread_id = str(event.get("thread_id", ""))
            elif event_type == "turn.completed":
                evidence.turn_completed = True

            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "image_generation":
                event_id = str(
                    item.get("id")
                    or item.get("call_id")
                    or item.get("saved_path")
                    or f"line-{line_number}"
                )
                evidence.image_event_ids.add(event_id)
                if event_type == "item.completed":
                    saved_path = str(item.get("saved_path", "")).strip()
                    if item.get("status") == "completed" and saved_path:
                        evidence.saved_paths.append(saved_path)
                    elif item.get("status") not in {None, "completed"}:
                        evidence.errors.append(
                            str(item.get("error", item.get("status")))
                        )

            payload = event.get("payload")
            if (
                isinstance(payload, dict)
                and payload.get("type") == "image_generation_end"
            ):
                event_id = str(
                    payload.get("id")
                    or payload.get("call_id")
                    or payload.get("saved_path")
                    or f"legacy-{line_number}"
                )
                evidence.image_event_ids.add(event_id)
                saved_path = str(payload.get("saved_path", "")).strip()
                if payload.get("status") == "completed" and saved_path:
                    evidence.saved_paths.append(saved_path)
                elif payload.get("status") not in {None, "completed"}:
                    evidence.errors.append(
                        str(payload.get("error", payload.get("status")))
                    )

    evidence.saved_paths = list(dict.fromkeys(evidence.saved_paths))
    return evidence


def verify_worker_output(
    job: Job,
    exit_code: int | None,
    final: dict[str, Any] | None,
    evidence: JsonlEvidence,
    initial_errors: list[str] | None = None,
) -> VerificationOutcome:
    errors = list(initial_errors or [])
    errors.extend(evidence.errors)
    image_event_count = len(evidence.image_event_ids)
    valid_saved_paths = list(
        dict.fromkeys(
            str(Path(value).resolve())
            for value in evidence.saved_paths
            if valid_image_file(Path(value))
        )
    )

    if exit_code != 0:
        errors.append(f"Codex exit code: {exit_code}")
    if not evidence.thread_id:
        errors.append("Missing thread.started event")
    if not evidence.turn_completed:
        errors.append("Missing turn.completed event")

    base_ok = (
        exit_code == 0
        and bool(evidence.thread_id)
        and evidence.turn_completed
        and not errors
    )
    telemetry_present = bool(evidence.image_event_ids or evidence.saved_paths)
    if telemetry_present:
        if image_event_count != 1:
            errors.append(
                f"Expected exactly one image_generation event, found {image_event_count}"
            )
        if len(valid_saved_paths) != 1:
            errors.append(
                f"Expected exactly one valid saved_path, found {len(valid_saved_paths)}"
            )
        if base_ok and image_event_count == 1 and len(valid_saved_paths) == 1:
            return VerificationOutcome(
                status="ok",
                image_path=valid_saved_paths[0],
                error="",
                mode="telemetry",
                image_event_count=image_event_count,
                saved_paths=evidence.saved_paths,
            )
        diagnostic_path = valid_saved_paths[0] if len(valid_saved_paths) == 1 else ""
    else:
        diagnostic_path = ""
        reported_path: Path | None = None
        final_ok = True
        if final is None:
            errors.append("Missing structured final result")
            final_ok = False
        else:
            if str(final.get("job_id", "")) != job.job_id:
                errors.append("Final result job_id mismatch")
                final_ok = False
            if final.get("status") != "ok":
                errors.append(
                    str(final.get("error", "")).strip()
                    or "Final result did not report status ok"
                )
                final_ok = False
            if str(final.get("error", "")).strip():
                errors.append(str(final.get("error", "")).strip())
                final_ok = False
            reported = str(final.get("image_path", "")).strip()
            if not reported:
                errors.append("Final result has no image_path")
                final_ok = False
            else:
                candidate = Path(reported)
                if not candidate.is_absolute() or not valid_image_file(candidate):
                    errors.append(
                        "Final result image_path is not a valid absolute file"
                    )
                    final_ok = False
                else:
                    reported_path = candidate.resolve()
                    diagnostic_path = str(reported_path)

        thread_output_ok = False
        if reported_path is not None and evidence.thread_id:
            thread_dir = generated_thread_directory(reported_path, evidence.thread_id)
            if thread_dir is None:
                errors.append(
                    "Final image_path is outside generated_images/<thread_id>"
                )
            else:
                outputs = thread_raster_outputs(thread_dir)
                if len(outputs) != 1:
                    errors.append(
                        f"Expected exactly one raster in thread output, found {len(outputs)}"
                    )
                elif outputs[0] != reported_path:
                    errors.append("Final image_path does not match the thread raster")
                else:
                    thread_output_ok = True

        if base_ok and final_ok and thread_output_ok:
            return VerificationOutcome(
                status="ok",
                image_path=str(reported_path),
                error="",
                mode="final-json-thread-output",
                image_event_count=0,
                saved_paths=[],
            )

    error = "; ".join(dict.fromkeys(value for value in errors if value))
    return VerificationOutcome(
        status="error",
        image_path=diagnostic_path,
        error=error or "Worker did not produce one verified image",
        mode="failed",
        image_event_count=image_event_count,
        saved_paths=evidence.saved_paths,
    )


def retryable_failure(error: str, image_event_count: int) -> bool:
    text = error.lower()
    if image_event_count > 1:
        return False
    if any(
        marker in text
        for marker in (
            "content policy",
            "safety policy",
            "moderation",
            "refused",
            "invalid reference",
            "reference not found",
        )
    ):
        return False
    return True


def process_group_options(platform_name: str | None = None) -> dict[str, Any]:
    platform_name = platform_name or os.name
    if platform_name == "nt":
        return {"creationflags": WINDOWS_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


async def terminate_process(
    process: asyncio.subprocess.Process,
    platform_name: str | None = None,
) -> None:
    if process.returncode is not None:
        return
    platform_name = platform_name or os.name
    if platform_name == "nt":
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
        try:
            if ctrl_break is None:
                process.terminate()
            else:
                process.send_signal(ctrl_break)
        except (ProcessLookupError, PermissionError, OSError):
            process.terminate()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        if platform_name == "nt":
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                process.kill()
        await process.wait()


async def run_attempt(
    job: Job,
    attempt_number: int,
    args: argparse.Namespace,
    run_dir: Path,
    schema_path: Path,
    semaphore: asyncio.Semaphore,
    tracker: ActiveTracker,
) -> Attempt:
    stem = f"{job.index + 1:03d}-{safe_name(job.job_id)}-attempt-{attempt_number}"
    stdout_path = run_dir / f"{stem}.stdout.jsonl"
    stderr_path = run_dir / f"{stem}.stderr.log"
    final_path = run_dir / f"{stem}.result.json"

    async with semaphore:
        started_text = utc_now()
        started = time.monotonic()
        process: asyncio.subprocess.Process | None = None
        await tracker.enter()
        try:
            if args.simulate_seconds > 0:
                await asyncio.sleep(args.simulate_seconds)
                return Attempt(
                    number=attempt_number,
                    started_at=started_text,
                    completed_at=utc_now(),
                    duration_seconds=round(time.monotonic() - started, 3),
                    exit_code=0,
                    status="simulated",
                    image_path="",
                    error="",
                    retryable=False,
                    thread_id=f"simulated-{job.index + 1}",
                    turn_completed=True,
                    image_event_count=1,
                    saved_paths=[],
                    verification_mode="simulation",
                    stdout_log=str(stdout_path),
                    stderr_log=str(stderr_path),
                    final_message=str(final_path),
                )

            command = [
                args.codex_bin,
                "-a",
                "never",
                "exec",
                "--skip-git-repo-check",
                "--json",
                "--color",
                "never",
                "--sandbox",
                "read-only",
                "--ignore-rules",
                "--enable",
                "image_generation",
                "--disable",
                "shell_tool",
                "--disable",
                "unified_exec",
                "--disable",
                "apps",
                "--disable",
                "browser_use",
                "--disable",
                "browser_use_external",
                "--disable",
                "browser_use_full_cdp_access",
                "--disable",
                "in_app_browser",
                "--disable",
                "computer_use",
                "--disable",
                "multi_agent",
                "--disable",
                "standalone_web_search",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(final_path),
                "--cd",
                str(args.worker_workdir),
            ]
            if not args.load_user_config:
                command.append("--ignore-user-config")
            if not args.keep_sessions:
                command.append("--ephemeral")
            command.append("-")

            with (
                stdout_path.open("wb") as stdout_file,
                stderr_path.open("wb") as stderr_file,
            ):
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    **process_group_options(),
                )
                try:
                    await asyncio.wait_for(
                        process.communicate(build_worker_prompt(job).encode("utf-8")),
                        timeout=args.timeout_seconds,
                    )
                    exit_code = process.returncode
                    timeout_error = ""
                except asyncio.TimeoutError:
                    await terminate_process(process)
                    exit_code = process.returncode
                    timeout_error = f"Timed out after {args.timeout_seconds:g} seconds"

            final = parse_final_message(final_path)
            evidence = parse_jsonl_evidence(stdout_path)
            verification = verify_worker_output(
                job,
                exit_code,
                final,
                evidence,
                [timeout_error] if timeout_error else [],
            )
            image_path = verification.image_path
            if not image_path:
                image_path = recover_image_path(final_path, stdout_path, stderr_path)

            return Attempt(
                number=attempt_number,
                started_at=started_text,
                completed_at=utc_now(),
                duration_seconds=round(time.monotonic() - started, 3),
                exit_code=exit_code,
                status=verification.status,
                image_path=image_path,
                error=verification.error,
                retryable=(
                    verification.status == "error"
                    and retryable_failure(
                        verification.error, verification.image_event_count
                    )
                ),
                thread_id=evidence.thread_id,
                turn_completed=evidence.turn_completed,
                image_event_count=verification.image_event_count,
                saved_paths=verification.saved_paths,
                verification_mode=verification.mode,
                stdout_log=str(stdout_path),
                stderr_log=str(stderr_path),
                final_message=str(final_path),
            )
        except asyncio.CancelledError:
            if process is not None:
                await terminate_process(process)
            raise
        except (
            Exception
        ) as exc:  # Preserve per-job failure instead of aborting the pool.
            return Attempt(
                number=attempt_number,
                started_at=started_text,
                completed_at=utc_now(),
                duration_seconds=round(time.monotonic() - started, 3),
                exit_code=None,
                status="error",
                image_path="",
                error=f"{type(exc).__name__}: {exc}",
                retryable=True,
                thread_id="",
                turn_completed=False,
                image_event_count=0,
                saved_paths=[],
                verification_mode="failed",
                stdout_log=str(stdout_path),
                stderr_log=str(stderr_path),
                final_message=str(final_path),
            )
        finally:
            await tracker.leave()


async def run_wave(
    pending: list[JobResult],
    attempt_number: int,
    concurrency: int,
    args: argparse.Namespace,
    run_dir: Path,
    schema_path: Path,
    tracker: ActiveTracker,
) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    attempts = await asyncio.gather(
        *[
            run_attempt(
                result.job,
                attempt_number,
                args,
                run_dir,
                schema_path,
                semaphore,
                tracker,
            )
            for result in pending
        ]
    )
    for result, attempt in zip(pending, attempts):
        result.attempts.append(attempt)
        if attempt.status in {"ok", "simulated"}:
            result.status = attempt.status
            result.image_path = attempt.image_path
            result.error = ""
        else:
            result.status = "error"
            result.error = attempt.error


def unique_destination(directory: Path, preferred: str) -> Path:
    candidate = directory / preferred
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    number = 2
    while True:
        candidate = directory / f"{stem}-{number}{suffix}"
        if not candidate.exists():
            return candidate
        number += 1


def copy_images(results: list[JobResult], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for result in results:
        if result.status != "ok" or not result.image_path:
            continue
        source = Path(result.image_path)
        preferred = (
            result.job.output_name or f"{safe_name(result.job.job_id)}{source.suffix}"
        )
        if Path(preferred).suffix.lower() != source.suffix.lower():
            preferred = str(Path(preferred).with_suffix(source.suffix))
        target = unique_destination(destination, preferred)
        shutil.copy2(source, target)
        result.image_path = str(target.resolve())


def attempt_to_dict(attempt: Attempt) -> dict[str, Any]:
    return {
        "number": attempt.number,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "duration_seconds": attempt.duration_seconds,
        "exit_code": attempt.exit_code,
        "status": attempt.status,
        "image_path": attempt.image_path,
        "error": attempt.error,
        "retryable": attempt.retryable,
        "thread_id": attempt.thread_id,
        "turn_completed": attempt.turn_completed,
        "image_event_count": attempt.image_event_count,
        "saved_paths": attempt.saved_paths,
        "verification_mode": attempt.verification_mode,
        "stdout_log": attempt.stdout_log,
        "stderr_log": attempt.stderr_log,
        "final_message": attempt.final_message,
    }


def result_to_dict(result: JobResult) -> dict[str, Any]:
    return {
        "index": result.job.index,
        "job_id": result.job.job_id,
        "intent": result.job.intent,
        "references": [
            {"path": str(ref.path), "role": ref.role}
            for ref in result.job.references
        ],
        "output_name": result.job.output_name,
        "status": result.status,
        "image_path": result.image_path,
        "error": result.error,
        "attempts": [attempt_to_dict(item) for item in result.attempts],
    }


async def async_main(args: argparse.Namespace) -> int:
    if not 1 <= args.concurrency <= MAX_CONCURRENCY:
        raise ValueError(f"concurrency must be between 1 and {MAX_CONCURRENCY}")
    if args.retries < 0:
        raise ValueError("retries cannot be negative")
    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be positive")
    if args.simulate_seconds < 0:
        raise ValueError("simulate-seconds cannot be negative")
    if not args.workdir.is_dir():
        raise ValueError(f"workdir not found: {args.workdir}")
    if not args.worker_workdir.is_dir():
        raise ValueError(f"worker-workdir not found: {args.worker_workdir}")

    manifest_source = args.manifest.resolve()
    jobs = load_manifest(manifest_source)
    default_run = (
        args.workdir
        / "tmp"
        / "parallel-imagegen"
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    run_dir = (args.run_dir or default_run).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest_snapshot = run_dir / "manifest.json"
    if manifest_source != manifest_snapshot:
        shutil.copy2(manifest_source, manifest_snapshot)
    schema_path = run_dir / "result.schema.json"
    write_json(schema_path, RESULT_SCHEMA)

    if args.dry_run:
        payload = {
            "mode": "dry-run",
            "manifest_snapshot": str(manifest_snapshot),
            "job_count": len(jobs),
            "concurrency": args.concurrency,
            "jobs": [
                {
                    "id": job.job_id,
                    "intent": job.intent,
                    "references": [
                        {"path": str(ref.path), "role": ref.role}
                        for ref in job.references
                    ],
                    "prompt_chars": len(job.prompt),
                    "worker_prompt": build_worker_prompt(job),
                }
                for job in jobs
            ],
        }
        write_json(run_dir / "dry-run.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    started_text = utc_now()
    started = time.monotonic()
    tracker = ActiveTracker()
    results = [JobResult(job=job) for job in jobs]
    wave_concurrency = args.concurrency

    for attempt_number in range(1, args.retries + 2):
        pending = [
            result
            for result in results
            if result.status not in {"ok", "simulated"}
            and (not result.attempts or result.attempts[-1].retryable)
        ]
        if not pending:
            break
        await run_wave(
            pending,
            attempt_number,
            min(wave_concurrency, len(pending)),
            args,
            run_dir,
            schema_path,
            tracker,
        )
        wave_concurrency = max(1, wave_concurrency // 2)

    if args.copy_images_to and args.simulate_seconds == 0:
        copy_images(results, args.copy_images_to.resolve())

    successful = sum(result.status in {"ok", "simulated"} for result in results)
    thread_ids = {
        attempt.thread_id
        for result in results
        for attempt in result.attempts
        if attempt.thread_id
    }
    successful_thread_ids = [
        attempt.thread_id
        for result in results
        for attempt in reversed(result.attempts)
        if result.status in {"ok", "simulated"}
        and attempt.status in {"ok", "simulated"}
        and attempt.thread_id
    ][:successful]
    summary = {
        "started_at": started_text,
        "completed_at": utc_now(),
        "manifest_snapshot": str(manifest_snapshot),
        "duration_seconds": round(time.monotonic() - started, 3),
        "job_count": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "requested_concurrency": args.concurrency,
        "max_active_workers": tracker.max_active,
        "unique_thread_count": len(thread_ids),
        "successful_unique_thread_count": len(set(successful_thread_ids)),
        "successful_threads_distinct": (
            len(successful_thread_ids) == successful
            and len(set(successful_thread_ids)) == successful
        ),
        "simulated": args.simulate_seconds > 0,
        "results": [result_to_dict(result) for result in results],
    }
    summary_path = run_dir / "summary.json"
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary_path={summary_path}")
    return 0 if successful == len(results) else 1


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(async_main(args))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted: active worker processes were terminated", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
