from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - pyproject requires 3.11+
    tomllib = None  # type: ignore[assignment]

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from cheap_opinion.prompts import ASK_SYSTEM_PROMPT, ASK_TEMPLATES, REVIEW_SYSTEM_PROMPT
else:
    from .prompts import ASK_SYSTEM_PROMPT, ASK_TEMPLATES, REVIEW_SYSTEM_PROMPT

APP_STATE_DIRNAME = ".second-opinion-poc"


def default_models_file() -> Path:
    script_path = Path(__file__).resolve()
    candidates = [
        script_path.parents[2] / "models.toml",
        script_path.parent / "models.toml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


DEFAULT_MODELS_FILE = default_models_file()


@dataclass(frozen=True)
class ModelConfig:
    alias: str
    provider: str
    model: str
    base_url: str
    temperature: float
    max_tokens: int
    timeout_seconds: int


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def load_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("Python 3.11+ is required for tomllib support.")
    with path.open("rb") as f:
        return tomllib.load(f)


def load_models(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"models file not found: {path}")
    data = load_toml(path)
    if "models" not in data:
        raise SystemExit(f"models file has no [models.*] entries: {path}")
    return data


def resolve_model(alias: str | None, models_file: Path) -> ModelConfig:
    data = load_models(models_file)
    defaults = data.get("defaults", {})
    models = data.get("models", {})
    selected_alias = alias or defaults.get("model")
    if not selected_alias:
        raise SystemExit("No model alias was supplied and [defaults].model is missing.")
    if selected_alias not in models:
        known = ", ".join(sorted(models))
        raise SystemExit(f"Unknown model alias '{selected_alias}'. Known aliases: {known}")
    entry = models[selected_alias]
    provider = str(entry.get("provider", "openrouter"))
    if provider != "openrouter":
        raise SystemExit(f"Only provider='openrouter' is supported in this PoC: {selected_alias}")
    return ModelConfig(
        alias=selected_alias,
        provider=provider,
        model=str(entry["model"]),
        base_url=str(entry.get("base_url", defaults.get("base_url", "https://openrouter.ai/api/v1"))),
        temperature=float(entry.get("temperature", defaults.get("temperature", 0.1))),
        max_tokens=int(entry.get("max_tokens", defaults.get("max_tokens", 3000))),
        timeout_seconds=int(entry.get("timeout_seconds", defaults.get("timeout_seconds", 120))),
    )


def state_dir_from_arg(value: str) -> Path:
    return Path(value).expanduser().resolve()


def default_state_dir(args: argparse.Namespace) -> Path:
    repo_value = getattr(args, "repo", None)
    if repo_value:
        return git_root(Path(repo_value).expanduser().resolve()) / APP_STATE_DIRNAME
    return git_root(Path.cwd()) / APP_STATE_DIRNAME


def finalize_state_dir(args: argparse.Namespace) -> None:
    if args.state_dir is None:
        args.state_dir = default_state_dir(args).resolve()


def state_file(state_dir: Path) -> Path:
    return state_dir / "state.toml"


def read_logging_enabled(state_dir: Path) -> bool:
    path = state_file(state_dir)
    if not path.exists():
        return False
    try:
        data = load_toml(path)
    except Exception:
        return False
    return bool(data.get("logging_enabled", False))


def write_logging_enabled(state_dir: Path, enabled: bool) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    value = "true" if enabled else "false"
    state_file(state_dir).write_text(f"logging_enabled = {value}\n", encoding="utf-8")


def write_log(state_dir: Path, record: dict[str, Any]) -> Path | None:
    if not read_logging_enabled(state_dir):
        return None
    logs_dir = state_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.localtime())
    path = logs_dir / f"{stamp}-{record.get('command', 'run')}-{record.get('model_alias', 'model')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_git_diff(repo: Path, staged: bool) -> str:
    inside = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        text=True,
        capture_output=True,
        check=False,
    )
    if inside.returncode != 0:
        raise SystemExit(f"not a git repository: {repo}. Use --repo or --diff-file.")
    cmd = ["git", "-C", str(repo), "diff", "--no-ext-diff", "--unified=80"]
    if staged:
        cmd.insert(4, "--cached")
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "git diff failed")
    return proc.stdout


def git_root(repo: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return Path(proc.stdout.strip()).resolve()
    return repo.resolve()


def read_text_file(path: Path, max_chars: int) -> str:
    data = path.read_text(encoding="utf-8", errors="replace")
    if len(data) > max_chars:
        raise SystemExit(f"file is too large for this request: {path} ({len(data)} chars)")
    return data


def enforce_limit(label: str, text: str, max_chars: int) -> None:
    if len(text) > max_chars:
        raise SystemExit(
            f"{label} is too large ({len(text)} chars > {max_chars}). "
            "Narrow the scope or raise --max-input-chars."
        )


def openrouter_chat(model: ModelConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set.")

    url = model.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model.model,
        "messages": messages,
        "temperature": model.temperature,
        "max_tokens": model.max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/openai/codex",
            "X-Title": "cheap-opinion-poc",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=model.timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenRouter HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"OpenRouter request failed: {exc}") from exc


def response_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def render_review_markdown(review: dict[str, Any]) -> str:
    findings = review.get("findings") or []
    lines: list[str] = []
    if not findings:
        lines.append("Findings: none")
    else:
        lines.append("Findings:")
        for item in findings:
            title = item.get("title", "(untitled)")
            location = item.get("code_location") or {}
            line_range = location.get("line_range") or {}
            path = location.get("absolute_file_path", "(unknown path)")
            start = line_range.get("start", "?")
            lines.append(f"- {title} ({path}:{start})")
            body = item.get("body")
            if body:
                lines.append(f"  {body}")
    correctness = review.get("overall_correctness")
    explanation = review.get("overall_explanation")
    if correctness or explanation:
        lines.append("")
        lines.append(f"Overall: {correctness or 'unknown'}")
        if explanation:
            lines.append(str(explanation))
    return "\n".join(lines)


def print_models(models_file: Path) -> int:
    data = load_models(models_file)
    defaults = data.get("defaults", {})
    default_alias = defaults.get("model")
    for alias, entry in sorted(data.get("models", {}).items()):
        marker = " (default)" if alias == default_alias else ""
        description = entry.get("description", "")
        print(f"{alias}{marker}: {entry.get('model')} [{entry.get('provider', 'openrouter')}]")
        if description:
            print(f"  {description}")
    return 0


def split_model_aliases(value: str) -> list[str]:
    aliases = [item.strip() for item in value.split(",") if item.strip()]
    if not aliases:
        raise SystemExit("--models requires at least one model alias.")
    seen: set[str] = set()
    unique: list[str] = []
    for alias in aliases:
        if alias not in seen:
            seen.add(alias)
            unique.append(alias)
    return unique


def resolve_many_models(value: str, models_file: Path) -> list[ModelConfig]:
    return [resolve_model(alias, models_file) for alias in split_model_aliases(value)]


def get_review_context(args: argparse.Namespace) -> tuple[Path, str]:
    repo = Path(args.repo).expanduser().resolve()
    root = git_root(repo)
    if args.diff_file:
        diff = read_text_file(Path(args.diff_file).expanduser().resolve(), args.max_input_chars)
    else:
        diff = run_git_diff(repo, staged=args.staged)
    if not diff.strip():
        raise SystemExit("No diff found. Nothing to review.")
    enforce_limit("diff", diff, args.max_input_chars)
    return root, diff


def build_review_messages_from_context(
    root: Path,
    diff: str,
    max_findings: int,
    model: ModelConfig,
) -> list[dict[str, str]]:
    user = (
        f"Repository root: {root}\n"
        f"Reviewer model alias: {model.alias}\n"
        f"Maximum findings: {max_findings}\n\n"
        f"Review this diff:\n\n"
        f"```diff\n{diff}\n```"
    )
    return [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_review_messages(args: argparse.Namespace, model: ModelConfig) -> list[dict[str, str]]:
    root, diff = get_review_context(args)
    return build_review_messages_from_context(root, diff, args.max_findings, model)


def build_ask_messages(args: argparse.Namespace) -> list[dict[str, str]]:
    question = " ".join(args.question).strip()
    if not question:
        raise SystemExit("ask requires a question.")

    chunks: list[str] = []
    template = ASK_TEMPLATES.get(args.template)
    if template:
        chunks.append(f"Template intent: {template}")
    chunks.append(f"Question: {question}")

    for file_name in args.file:
        path = Path(file_name).expanduser().resolve()
        content = read_text_file(path, args.max_file_chars)
        chunks.append(f"\nFile: {path}\n```text\n{content}\n```")

    if args.stdin:
        stdin_text = sys.stdin.read()
        enforce_limit("stdin", stdin_text, args.max_input_chars)
        chunks.append(f"\nAdditional stdin context:\n```text\n{stdin_text}\n```")

    user = "\n".join(chunks)
    enforce_limit("ask prompt", user, args.max_input_chars)
    return [
        {"role": "system", "content": ASK_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def run_one_model(
    command: str,
    model: ModelConfig,
    messages: list[dict[str, str]],
    parse_json: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    run: dict[str, Any] = {
        "alias": model.alias,
        "model": model.model,
        "status": "ok",
        "elapsed_seconds": 0.0,
    }
    try:
        response = openrouter_chat(model, messages)
        text = response_text(response)
        run["raw_text"] = text
        run["response"] = response
        if parse_json:
            parsed = parse_json_object(text)
            run["parsed"] = parsed is not None
            if parsed is not None:
                run["result"] = parsed
        else:
            run["result"] = text
    except SystemExit as exc:
        run["status"] = "failed"
        run["error"] = str(exc)
    except Exception as exc:  # pragma: no cover - defensive around network clients
        run["status"] = "failed"
        run["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        run["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return run


def run_many_models(
    command: str,
    model_configs: list[ModelConfig],
    messages_by_alias: dict[str, list[dict[str, str]]],
    parse_json: bool,
    concurrency: int,
) -> list[dict[str, Any]]:
    max_workers = max(1, min(concurrency, len(model_configs)))
    runs_by_alias: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_alias = {
            executor.submit(
                run_one_model,
                command,
                model,
                messages_by_alias[model.alias],
                parse_json,
            ): model.alias
            for model in model_configs
        }
        for future in concurrent.futures.as_completed(future_to_alias):
            alias = future_to_alias[future]
            runs_by_alias[alias] = future.result()
    return [runs_by_alias[model.alias] for model in model_configs]


def summarize_runs(command: str, runs: list[dict[str, Any]], started: float) -> dict[str, Any]:
    succeeded = [run["alias"] for run in runs if run.get("status") == "ok"]
    failed = [run["alias"] for run in runs if run.get("status") != "ok"]
    parse_failures = [
        run["alias"]
        for run in runs
        if run.get("status") == "ok" and run.get("parsed") is False
    ]
    total_findings = 0
    if command == "review":
        for run in runs:
            result = run.get("result")
            if isinstance(result, dict):
                total_findings += len(result.get("findings") or [])
    return {
        "models": [run["alias"] for run in runs],
        "succeeded": succeeded,
        "failed": failed,
        "parse_failures": parse_failures,
        "total_findings": total_findings if command == "review" else None,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def render_multi_review_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "Multi Review Summary",
        f"- models: {', '.join(summary['models'])}",
        f"- succeeded: {', '.join(summary['succeeded']) or 'none'}",
        f"- failed: {', '.join(summary['failed']) or 'none'}",
        f"- parse failures: {', '.join(summary['parse_failures']) or 'none'}",
        f"- total findings: {summary['total_findings']}",
        "",
    ]
    for run in result["runs"]:
        lines.append(f"## {run['alias']} ({run['status']})")
        if run.get("status") != "ok":
            lines.append(run.get("error", "unknown error"))
        elif run.get("parsed") is False:
            lines.append("Response was not parseable JSON.")
            lines.append(run.get("raw_text", ""))
        else:
            lines.append(render_review_markdown(run.get("result") or {}))
        lines.append("")
    return "\n".join(lines).rstrip()


def render_multi_ask_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "Multi Ask Summary",
        f"- models: {', '.join(summary['models'])}",
        f"- succeeded: {', '.join(summary['succeeded']) or 'none'}",
        f"- failed: {', '.join(summary['failed']) or 'none'}",
        "",
    ]
    for run in result["runs"]:
        lines.append(f"## {run['alias']} ({run['status']})")
        if run.get("status") != "ok":
            lines.append(run.get("error", "unknown error"))
        else:
            lines.append(str(run.get("result", "")))
        lines.append("")
    return "\n".join(lines).rstrip()


def render_multi_raw(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for run in result["runs"]:
        lines.append(f"===== {run['alias']} ({run['status']}) =====")
        if run.get("status") != "ok":
            lines.append(run.get("error", "unknown error"))
        else:
            lines.append(run.get("raw_text", str(run.get("result", ""))))
        lines.append("")
    return "\n".join(lines).rstrip()


def command_review(args: argparse.Namespace) -> int:
    model = resolve_model(args.model, args.models_file)
    messages = build_review_messages(args, model)
    if args.dry_run:
        print(json.dumps({"model": model.model, "messages": messages}, ensure_ascii=False, indent=2))
        return 0

    response = openrouter_chat(model, messages)
    text = response_text(response)
    parsed = parse_json_object(text)

    record = {
        "timestamp": time.time(),
        "command": "review",
        "cwd": str(Path.cwd()),
        "model_alias": model.alias,
        "model": model.model,
        "messages": messages,
        "response": response,
    }
    log_path = write_log(args.state_dir, record)

    if args.format == "raw":
        print(text)
    elif parsed is None:
        eprint("warning: model did not return parseable JSON; printing raw response")
        print(text)
        return 2
    elif args.format == "markdown":
        print(render_review_markdown(parsed))
    else:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))

    if log_path:
        eprint(f"log written: {log_path}")
    return 0


def command_multi_review(args: argparse.Namespace) -> int:
    model_configs = resolve_many_models(args.models, args.models_file)
    root, diff = get_review_context(args)
    messages_by_alias = {
        model.alias: build_review_messages_from_context(root, diff, args.max_findings, model)
        for model in model_configs
    }
    if args.dry_run:
        payload = {
            "mode": "multi",
            "command": "review",
            "models": [model.model for model in model_configs],
            "requests": [
                {"alias": model.alias, "model": model.model, "messages": messages_by_alias[model.alias]}
                for model in model_configs
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    started = time.monotonic()
    runs = run_many_models("review", model_configs, messages_by_alias, True, args.concurrency)
    result = {
        "mode": "multi",
        "command": "review",
        "summary": summarize_runs("review", runs, started),
        "runs": runs,
    }
    log_path = write_log(
        args.state_dir,
        {
            "timestamp": time.time(),
            "command": "multi-review",
            "cwd": str(Path.cwd()),
            "messages_by_alias": messages_by_alias,
            "result": result,
        },
    )

    if args.format == "raw":
        print(render_multi_raw(result))
    elif args.format == "markdown":
        print(render_multi_review_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if log_path:
        eprint(f"log written: {log_path}")
    return 1 if not result["summary"]["succeeded"] else 0


def command_ask(args: argparse.Namespace) -> int:
    model = resolve_model(args.model, args.models_file)
    messages = build_ask_messages(args)
    if args.dry_run:
        print(json.dumps({"model": model.model, "messages": messages}, ensure_ascii=False, indent=2))
        return 0

    response = openrouter_chat(model, messages)
    text = response_text(response)
    record = {
        "timestamp": time.time(),
        "command": "ask",
        "cwd": str(Path.cwd()),
        "model_alias": model.alias,
        "model": model.model,
        "messages": messages,
        "response": response,
    }
    log_path = write_log(args.state_dir, record)
    print(text)
    if log_path:
        eprint(f"log written: {log_path}")
    return 0


def command_multi_ask(args: argparse.Namespace) -> int:
    model_configs = resolve_many_models(args.models, args.models_file)
    messages = build_ask_messages(args)
    messages_by_alias = {model.alias: messages for model in model_configs}
    if args.dry_run:
        payload = {
            "mode": "multi",
            "command": "ask",
            "models": [model.model for model in model_configs],
            "requests": [
                {"alias": model.alias, "model": model.model, "messages": messages_by_alias[model.alias]}
                for model in model_configs
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    started = time.monotonic()
    runs = run_many_models("ask", model_configs, messages_by_alias, False, args.concurrency)
    result = {
        "mode": "multi",
        "command": "ask",
        "summary": summarize_runs("ask", runs, started),
        "runs": runs,
    }
    log_path = write_log(
        args.state_dir,
        {
            "timestamp": time.time(),
            "command": "multi-ask",
            "cwd": str(Path.cwd()),
            "messages": messages,
            "result": result,
        },
    )

    if args.format == "raw":
        print(render_multi_raw(result))
    elif args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_multi_ask_markdown(result))
    if log_path:
        eprint(f"log written: {log_path}")
    return 1 if not result["summary"]["succeeded"] else 0


def command_logging(args: argparse.Namespace) -> int:
    if args.action == "enable":
        write_logging_enabled(args.state_dir, True)
    elif args.action == "disable":
        write_logging_enabled(args.state_dir, False)
    enabled = read_logging_enabled(args.state_dir)
    print(f"logging: {'enabled' if enabled else 'disabled'}")
    print(f"state_dir: {args.state_dir}")
    if enabled:
        print(f"logs_dir: {args.state_dir / 'logs'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cheap-opinion")
    parser.add_argument(
        "--models-file",
        type=Path,
        default=Path(os.environ.get("CHEAP_OPINION_MODELS_TOML", DEFAULT_MODELS_FILE)),
        help="Path to models.toml.",
    )
    parser.add_argument(
        "--state-dir",
        type=state_dir_from_arg,
        default=None,
        help=(
            "Directory for opt-in state/logs. Default: target git root's "
            ".second-opinion-poc directory."
        ),
    )

    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review the current git diff.")
    review.add_argument("--model", help="Model alias from models.toml.")
    review.add_argument("--repo", default=".", help="Repository path for git diff.")
    review.add_argument("--staged", action="store_true", help="Review staged changes via git diff --cached.")
    review.add_argument("--diff-file", help="Read a diff from a file instead of running git diff.")
    review.add_argument("--max-findings", type=int, default=5)
    review.add_argument("--max-input-chars", type=int, default=120_000)
    review.add_argument("--format", choices=["json", "markdown", "raw"], default="json")
    review.add_argument("--dry-run", action="store_true", help="Print the API request payload without calling OpenRouter.")
    review.set_defaults(func=command_review)

    ask = sub.add_parser("ask", help="Ask for an open-ended second opinion.")
    ask.add_argument("--model", help="Model alias from models.toml.")
    ask.add_argument("--file", action="append", default=[], help="Include a file as context. Repeatable.")
    ask.add_argument("--stdin", action="store_true", help="Include stdin as additional context.")
    ask.add_argument("--template", choices=sorted(ASK_TEMPLATES), default="general")
    ask.add_argument("--max-input-chars", type=int, default=100_000)
    ask.add_argument("--max-file-chars", type=int, default=60_000)
    ask.add_argument("--dry-run", action="store_true", help="Print the API request payload without calling OpenRouter.")
    ask.add_argument("question", nargs="*")
    ask.set_defaults(func=command_ask)

    multi = sub.add_parser("multi", help="Run the same review or ask request against multiple models.")
    multi_sub = multi.add_subparsers(dest="multi_command", required=True)

    multi_review = multi_sub.add_parser("review", help="Review the current git diff with multiple models.")
    multi_review.add_argument("--models", required=True, help="Comma-separated model aliases from models.toml.")
    multi_review.add_argument("--repo", default=".", help="Repository path for git diff.")
    multi_review.add_argument("--staged", action="store_true", help="Review staged changes via git diff --cached.")
    multi_review.add_argument("--diff-file", help="Read a diff from a file instead of running git diff.")
    multi_review.add_argument("--max-findings", type=int, default=5)
    multi_review.add_argument("--max-input-chars", type=int, default=120_000)
    multi_review.add_argument("--concurrency", type=int, default=3)
    multi_review.add_argument("--format", choices=["json", "markdown", "raw"], default="json")
    multi_review.add_argument("--dry-run", action="store_true", help="Print the API request payloads without calling OpenRouter.")
    multi_review.set_defaults(func=command_multi_review)

    multi_ask = multi_sub.add_parser("ask", help="Ask multiple models for a targeted second opinion.")
    multi_ask.add_argument("--models", required=True, help="Comma-separated model aliases from models.toml.")
    multi_ask.add_argument("--file", action="append", default=[], help="Include a file as context. Repeatable.")
    multi_ask.add_argument("--stdin", action="store_true", help="Include stdin as additional context.")
    multi_ask.add_argument("--template", choices=sorted(ASK_TEMPLATES), default="general")
    multi_ask.add_argument("--max-input-chars", type=int, default=100_000)
    multi_ask.add_argument("--max-file-chars", type=int, default=60_000)
    multi_ask.add_argument("--concurrency", type=int, default=3)
    multi_ask.add_argument("--format", choices=["markdown", "json", "raw"], default="markdown")
    multi_ask.add_argument("--dry-run", action="store_true", help="Print the API request payloads without calling OpenRouter.")
    multi_ask.add_argument("question", nargs="*")
    multi_ask.set_defaults(func=command_multi_ask)

    logging_parser = sub.add_parser("logging", help="Toggle opt-in run logging.")
    logging_parser.add_argument("--repo", default=".", help="Repository path that owns the default log state.")
    logging_parser.add_argument("action", choices=["status", "enable", "disable"])
    logging_parser.set_defaults(func=command_logging)

    models_parser = sub.add_parser("models", help="List configured model aliases.")
    models_parser.set_defaults(func=lambda args: print_models(args.models_file))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    finalize_state_dir(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
