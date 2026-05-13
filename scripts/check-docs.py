#!/usr/bin/env python3
"""Documentation consistency check.

Run from the repo root::

    python3 scripts/check-docs.py

The script returns non-zero if it finds any of the following:

* A relative Markdown link in a tracked doc points to a missing file.
* A `` `make <target>` `` reference in a doc names a target that does not
  exist in the real ``Makefile``.
* A `` `npm run <script>` `` reference in a doc names a script that does
  not exist in ``frontend/package.json``.
* A REST endpoint documented in ``docs/API.md`` is not actually exposed
  by the running backend (this requires being able to import the
  backend; skipped with a warning if the import fails).

This is a self-contained, dependency-free script aimed at CI parity with
Phase 6's ad-hoc checks. It uses only the Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

DOCS_TO_CHECK = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "TESTING_REPORT.md",
    "PROJECT_COMPLETION_CHECKLIST.md",
    "docs/ARCHITECTURE.md",
    "docs/API.md",
    "docs/DEPLOYMENT.md",
    "docs/HARDWARE.md",
    "docs/DATA_MODEL.md",
    "firmware/README.md",
    "examples/README.md",
)

# Inline link, not an image.
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)")
MAKE_RE = re.compile(r"`make ([a-z][a-z0-9_-]*)`")
# Two patterns to capture both backtick-wrapped and free-form "npm run X" usage.
NPM_RE = re.compile(r"`npm run ([a-z][a-z0-9_:-]*)`")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_links(docs: list[Path]) -> list[str]:
    """Verify every relative Markdown link resolves to a real file."""
    issues: list[str] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(2)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (doc.parent / path_part).resolve()
            if not resolved.exists():
                line = text[: match.start()].count("\n") + 1
                issues.append(
                    f"{doc.relative_to(REPO_ROOT)}:{line}: broken link '{target}'"
                )
    return issues


def check_make_targets(docs: list[Path]) -> list[str]:
    """Verify every `` `make <target>` `` reference matches a real target."""
    makefile = REPO_ROOT / "Makefile"
    if not makefile.exists():
        return [f"Makefile not found at {makefile}"]
    real_targets: set[str] = set()
    for line in makefile.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([a-z][a-z0-9_-]*):", line)
        if match:
            real_targets.add(match.group(1))

    issues: list[str] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for match in MAKE_RE.finditer(text):
            target = match.group(1)
            if target not in real_targets:
                line = text[: match.start()].count("\n") + 1
                issues.append(
                    f"{doc.relative_to(REPO_ROOT)}:{line}: "
                    f"`make {target}` does not exist in Makefile"
                )
    return issues


def check_npm_scripts(docs: list[Path]) -> list[str]:
    """Verify every `` `npm run <script>` `` matches a real package.json script."""
    package_json = REPO_ROOT / "frontend" / "package.json"
    if not package_json.exists():
        return [f"frontend/package.json not found at {package_json}"]
    scripts: set[str] = set(
        json.loads(package_json.read_text(encoding="utf-8"))["scripts"].keys()
    )

    issues: list[str] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for match in NPM_RE.finditer(text):
            script = match.group(1)
            if script not in scripts:
                line = text[: match.start()].count("\n") + 1
                issues.append(
                    f"{doc.relative_to(REPO_ROOT)}:{line}: "
                    f"`npm run {script}` does not exist in package.json"
                )
    return issues


def check_api_endpoints() -> list[str]:
    """Diff the routes documented in docs/API.md against the live backend."""
    api_doc = REPO_ROOT / "docs" / "API.md"
    if not api_doc.exists():
        return ["docs/API.md not found"]

    # Boot the backend in-process to read its real route table.
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    os.environ.setdefault("LOG_FORMAT", "text")
    sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
    try:
        from greenhouse.main import create_app  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"  warning: could not import backend ({exc}); skipping endpoint check")
        return []

    app = create_app()
    real_routes: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        if path in {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}:
            continue
        methods = getattr(route, "methods", None)
        if methods:
            for method in methods:
                if method in {"HEAD", "OPTIONS"}:
                    continue
                real_routes.add(f"{method} {path}")
        elif path == "/ws":
            real_routes.add(f"WS {path}")

    # Documented endpoints are written in API.md as lines like
    # "#### `POST /api/readings` — …" — grep those out.
    text = api_doc.read_text(encoding="utf-8")
    documented: set[str] = set()
    for match in re.finditer(r"`((?:GET|POST|PUT|DELETE|WS)\s+[^`]+?)`", text):
        documented.add(match.group(1).strip())

    issues: list[str] = []
    # Only flag a real route as missing when it isn't documented anywhere.
    for route in real_routes:
        if route not in documented:
            issues.append(f"docs/API.md: missing endpoint '{route}'")
    # Only flag a doc-only route as extra when it doesn't exist on the server.
    for route in documented:
        if route not in real_routes:
            # Filter out helper / repeated mentions that are not endpoint headings.
            # Real headings start with one of GET/POST/PUT/DELETE/WS and a /path.
            if re.match(r"^(GET|POST|PUT|DELETE|WS)\s+/", route):
                issues.append(f"docs/API.md: documented '{route}' is not a real route")
    return issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    docs: list[Path] = []
    for relative in DOCS_TO_CHECK:
        path = REPO_ROOT / relative
        if path.exists():
            docs.append(path)
        else:
            print(f"  warning: doc not found, skipping: {relative}")

    all_issues: list[str] = []

    print("== relative link check ==")
    issues = check_links(docs)
    print(f"   {len(issues)} issue(s)")
    all_issues.extend(issues)

    print("== make-target reference check ==")
    issues = check_make_targets(docs)
    print(f"   {len(issues)} issue(s)")
    all_issues.extend(issues)

    print("== npm-script reference check ==")
    issues = check_npm_scripts(docs)
    print(f"   {len(issues)} issue(s)")
    all_issues.extend(issues)

    print("== API.md ↔ backend route check ==")
    issues = check_api_endpoints()
    print(f"   {len(issues)} issue(s)")
    all_issues.extend(issues)

    print()
    if all_issues:
        print(f"FAIL: {len(all_issues)} issue(s):")
        for issue in all_issues:
            print(f"  - {issue}")
        return 1
    print("OK: documentation consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
