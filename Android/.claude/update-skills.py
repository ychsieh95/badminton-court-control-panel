#!/usr/bin/env python3
"""Check and update the vendored Claude Code skills in ./skills.

Each upstream repository is recorded in skills.lock.json, next to this script:

  layout "root"    the repo root is one skill, installed as skills/<name>/
  layout "plugin"  the repo is a Claude Code plugin; every skill folder under
                   <skills_path> is installed flat as skills/<skill>/, with
                   <plugin_prefix>:<skill> references and
                   ${CLAUDE_PLUGIN_ROOT}/skills/<skill>/ paths rewritten so the
                   skills work as plain project skills

Usage:
  ./update-skills.py check  [NAME...]   report which sources have new commits
                                        (exit code 1 if any are outdated)
  ./update-skills.py update [NAME...]   install the latest upstream version of
        [--force]                       outdated sources (all named sources
        [--dry-run]                     with --force, which also overwrites
                                        local edits)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
SKILLS = BASE / "skills"
LOCK = BASE / "skills.lock.json"
TEXT_SUFFIXES = {".md", ".txt", ".sh", ".ps1", ".py", ".json", ".yml", ".yaml"}


def run(*cmd: str, cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{result.stderr.strip()}")
    return result.stdout


def load_lock() -> dict:
    return json.loads(LOCK.read_text())


def save_lock(lock: dict) -> None:
    LOCK.write_text(json.dumps(lock, indent=2) + "\n")


def select(lock: dict, names: list[str]) -> list[dict]:
    sources = lock["sources"]
    if not names:
        return sources
    known = {s["name"]: s for s in sources}
    unknown = [n for n in names if n not in known]
    if unknown:
        sys.exit(f"Unknown source(s): {', '.join(unknown)}. Known: {', '.join(known)}")
    return [known[n] for n in names]


def remote_commit(source: dict) -> str:
    ref = source.get("ref", "HEAD")
    out = run("git", "ls-remote", source["repo"], ref)
    if not out.strip():
        raise RuntimeError(f"ref {ref!r} not found in {source['repo']}")
    return out.split()[0]


def compare_url(source: dict, old: str, new: str) -> str:
    repo = source["repo"].removesuffix(".git")
    return f"{repo}/compare/{old[:12]}...{new[:12]}" if "github.com" in repo else ""


def check(sources: list[dict]) -> list[tuple[dict, str]]:
    outdated = []
    for source in sources:
        try:
            latest = remote_commit(source)
        except RuntimeError as err:
            print(f"  ERROR     {source['name']}: {err}")
            continue
        if latest == source["commit"]:
            print(f"  current   {source['name']} ({latest[:12]})")
        else:
            print(f"  outdated  {source['name']} {source['commit'][:12]} -> {latest[:12]}")
            url = compare_url(source, source["commit"], latest)
            if url:
                print(f"            {url}")
            outdated.append((source, latest))
    return outdated


def ignore_git(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if n == ".git"]


def rewrite_text(root: Path, rewrites: list[tuple[re.Pattern, str]]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        new = text
        for pattern, repl in rewrites:
            new = pattern.sub(repl, new)
        if new != text:
            path.write_text(new)


def stage(source: dict, checkout: Path, out: Path) -> list[str]:
    """Build the installed skill folders for `source` under `out`; return their names."""
    if source["layout"] == "root":
        if not (checkout / "SKILL.md").is_file():
            raise RuntimeError("no SKILL.md at the repository root")
        name = source["installed"][0] if source.get("installed") else source["name"]
        shutil.copytree(checkout, out / name, ignore=ignore_git)
        return [name]

    if source["layout"] != "plugin":
        raise RuntimeError(f"unknown layout {source['layout']!r}")

    skills_dir = checkout / source["skills_path"]
    names = sorted(p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file())
    if not names:
        raise RuntimeError(f"no skills found under {source['skills_path']}")

    prefix = re.escape(source["plugin_prefix"])
    alternatives = "|".join(re.escape(n) for n in names)
    rewrites = [(re.compile(rf"\b{prefix}:({alternatives})\b"), r"\1")]
    for name in names:
        dest = out / name
        shutil.copytree(skills_dir / name, dest, ignore=ignore_git)
        for extra in source.get("copy_files", []):
            if (checkout / extra).is_file():
                shutil.copy2(checkout / extra, dest / extra)
        plugin_root = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/" + re.escape(name) + "/")
        rewrite_text(dest, rewrites + [(plugin_root, "${CLAUDE_SKILL_DIR}/")])
        for path in dest.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                try:
                    if "CLAUDE_PLUGIN_ROOT" in path.read_text():
                        print(f"  warning: {path.relative_to(out)} still uses ${{CLAUDE_PLUGIN_ROOT}}")
                except UnicodeDecodeError:
                    pass
    return names


def locally_modified(dirs: list[str]) -> list[str]:
    """Tracked files under `dirs` that differ from git HEAD (untracked files are ignored)."""
    try:
        top = Path(run("git", "rev-parse", "--show-toplevel", cwd=BASE).strip())
        paths = [str((SKILLS / d).relative_to(top)) for d in dirs if (SKILLS / d).exists()]
        if not paths:
            return []
        out = run("git", "diff", "--name-only", "HEAD", "--", *paths, cwd=top)
        return out.split()
    except RuntimeError:
        return []  # not a git repo, or no commits yet


def update(lock: dict, sources: list[dict], force: bool, dry_run: bool) -> None:
    if force:
        targets = [(s, remote_commit(s)) for s in sources]
    else:
        print("Checking for updates...")
        targets = check(sources)
    if not targets:
        print("Everything is up to date.")
        return

    owned = {d: s["name"] for s in lock["sources"] for d in s.get("installed", [])}
    with tempfile.TemporaryDirectory(prefix="skills-update-") as tmp:
        tmp_path = Path(tmp)
        planned = []
        for source, latest in targets:
            name = source["name"]
            print(f"\n{name}: fetching {latest[:12]}")
            checkout = tmp_path / "src" / name
            ref = source.get("ref", "HEAD")
            clone = ["git", "clone", "--quiet", "--depth", "1"]
            if ref != "HEAD":
                clone += ["--branch", ref.removeprefix("refs/heads/").removeprefix("refs/tags/")]
            run(*clone, source["repo"], str(checkout))
            got = run("git", "rev-parse", "HEAD", cwd=checkout).strip()

            out = tmp_path / "out" / name
            out.mkdir(parents=True)
            new = stage(source, checkout, out)
            old = source.get("installed", [])

            clashes = [d for d in new if owned.get(d, name) != name or
                       ((SKILLS / d).exists() and d not in owned)]
            if clashes:
                raise RuntimeError(f"{name}: would overwrite folders it does not own: {clashes}")
            edited = locally_modified(old)
            if edited and not force:
                raise RuntimeError(f"{name}: local edits would be lost (use --force):\n  "
                                   + "\n  ".join(edited))

            added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
            if added:
                print(f"  new skills: {', '.join(added)}")
            if removed:
                print(f"  removed upstream: {', '.join(removed)}")
            planned.append((source, got, old, new, out))

        if dry_run:
            print("\nDry run: nothing changed.")
            return

        for source, got, old, new, out in planned:
            for d in old:
                shutil.rmtree(SKILLS / d, ignore_errors=True)
            for d in new:
                shutil.move(str(out / d), SKILLS / d)
            source["commit"], source["installed"] = got, new
            print(f"{source['name']}: updated to {got[:12]}")
        save_lock(lock)
        print("\nDone. Review the changes with: git diff --stat -- " + str(SKILLS))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="report sources with new upstream commits")
    p_check.add_argument("names", nargs="*")
    p_update = sub.add_parser("update", help="install new upstream versions")
    p_update.add_argument("names", nargs="*")
    p_update.add_argument("--force", action="store_true",
                          help="reinstall even if current, and overwrite local edits")
    p_update.add_argument("--dry-run", action="store_true", help="show what would change")
    args = parser.parse_args()

    lock = load_lock()
    sources = select(lock, args.names)
    try:
        if args.command == "check":
            sys.exit(1 if check(sources) else 0)
        update(lock, sources, args.force, args.dry_run)
    except RuntimeError as err:
        sys.exit(f"error: {err}")


if __name__ == "__main__":
    main()
