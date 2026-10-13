#!/usr/bin/env python3
"""
RYKR-MEMORY: Deterministic Archival & Context Bus Appliance
Module 4 of RYKR-MODULAR-CONSOLE.
Uses rykr_bus for standardized I/O envelope and circuit breaking.
Zero external dependencies (pure Python 3 standard library).
"""

import sys
import os
import re
import json
import argparse
import tempfile
from datetime import datetime, timezone

# Add current dir to import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rykr_bus import (
    make_envelope,
    emit_payload,
    CircuitBreakerTripped,
    handle_appliance_entry
)

BASE_DIR = os.environ.get("RYKR_WORKSPACE") or os.path.expanduser("~/agy-projects")
ARCHIVE_INDEX_PATH = os.path.join(BASE_DIR, "rykr_archive_index.md")
SKILLS_PATH = os.path.join(BASE_DIR, "rykr_skills.md")


def get_current_date_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def find_highest_ref(archive_content):
    """Scans archive content and returns highest integer REF ID."""
    matches = re.findall(r"\[REF-(\d+)\]", archive_content)
    if not matches:
        return 0
    return max(int(m) for m in matches)


def atomic_write(filepath, new_content):
    """Safely writes content via tempfile and atomic rename."""
    dirname = os.path.dirname(filepath)
    prefix = ".tmp_" + os.path.basename(filepath)
    with tempfile.NamedTemporaryFile("w", dir=dirname, prefix=prefix, delete=False) as tf:
        tf.write(new_content)
        tf.flush()
        os.fsync(tf.fileno())
        temp_name = tf.name
    os.replace(temp_name, filepath)


def action_commit(args):
    """
    Appends a structured summary to rykr_archive_index.md atomically.
    Increments REF counter sequentially.
    """
    summary = args.summary.strip()
    if not summary:
        raise CircuitBreakerTripped(
            breaker_name="EMPTY_SUMMARY",
            reason="Cannot commit an empty memory summary.",
            suggested_action="PROVIDE_SUMMARY_TEXT"
        )

    if not os.path.isfile(ARCHIVE_INDEX_PATH):
        raise CircuitBreakerTripped(
            breaker_name="ARCHIVE_NOT_FOUND",
            reason=f"Archive file not found at {ARCHIVE_INDEX_PATH}",
            suggested_action="CHECK_ARCHIVE_PATH"
        )

    with open(ARCHIVE_INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    highest = find_highest_ref(content)
    next_ref_num = highest + 1
    next_ref_str = f"REF-{next_ref_num:03d}"
    today = get_current_date_str()

    new_entry = f"\n* [{next_ref_str}] | LU: {today} | DATA: {summary}\n"
    updated_content = content.rstrip() + new_entry

    atomic_write(ARCHIVE_INDEX_PATH, updated_content)

    skills_updated = []
    if getattr(args, "skills", None):
        for sk in args.skills.split(","):
            sk = sk.strip()
            if sk:
                update_skill_weight(sk)
                skills_updated.append(sk)

    return {
        "ref": next_ref_str,
        "archive_path": ARCHIVE_INDEX_PATH,
        "date": today,
        "summary": summary,
        "skills_updated": skills_updated
    }, f"Committed memory entry [{next_ref_str}]."


def update_skill_weight(skill_name):
    """Increments W and updates LU for a given skill in rykr_skills.md."""
    if not os.path.isfile(SKILLS_PATH):
        return False

    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"(\[SKILL:\s*{re.escape(skill_name)}\]\s*\|\s*W:)(\d+)(\s*\|\s*LU:)([\d-]+)",
        re.IGNORECASE
    )

    def repl(m):
        prefix = m.group(1)
        w = int(m.group(2)) + 1
        mid = m.group(3)
        today = get_current_date_str()
        return f"{prefix}{w}{mid}{today}"

    updated, count = pattern.subn(repl, content)
    if count > 0:
        atomic_write(SKILLS_PATH, updated)
        return True
    return False


def action_skill_use(args):
    """Updates weight and last-used date for a specific skill."""
    name = args.name.strip()
    success = update_skill_weight(name)
    if not success:
        raise CircuitBreakerTripped(
            breaker_name="SKILL_NOT_FOUND",
            reason=f"Skill '{name}' not found in {SKILLS_PATH}",
            suggested_action="CHECK_SKILL_NAME_SPELLING"
        )
    return {
        "skill": name,
        "skills_file": SKILLS_PATH,
        "updated": True
    }, f"Incremented weight and updated LU for skill '{name}'."


def action_audit(args):
    """Scans core markdown files and checks local file:// links."""
    core_files = [
        os.path.join(BASE_DIR, ".agents/AGENTS.md"),
        os.path.join(BASE_DIR, "rykr_operator.md"),
        os.path.join(BASE_DIR, "rykr_macros.md"),
        ARCHIVE_INDEX_PATH
    ]
    
    total_links = 0
    broken_links = []

    link_pattern = re.compile(r"\[([^\]]+)\]\(file://([^\)#\s]+)")

    for fpath in core_files:
        if not os.path.isfile(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()
        for m in link_pattern.finditer(text):
            total_links += 1
            target_path = m.group(2)
            if not os.path.exists(target_path):
                broken_links.append({"source": fpath, "target": target_path})

    return {
        "total_links_checked": total_links,
        "broken_links_count": len(broken_links),
        "broken_links": broken_links
    }, f"Audit complete: {total_links} links checked, {len(broken_links)} broken."


def main():
    common_p = argparse.ArgumentParser(add_help=False)
    common_p.add_argument("--json", action="store_true", help="Force machine-readable JSON envelope")

    parser = argparse.ArgumentParser(description="Rykr Memory & Archival Appliance", parents=[common_p])
    parser.add_argument("--schema", action="store_true", help="Introspect appliance schema")

    subparsers = parser.add_subparsers(dest="subcommand", help="Memory action")

    # commit
    commit_p = subparsers.add_parser("commit", parents=[common_p], help="Append sequential memory record")
    commit_p.add_argument("--summary", required=True, help="Dense factual summary text")
    commit_p.add_argument("--skills", default=None, help="Comma-separated skill names to update")

    # skill-use
    skill_p = subparsers.add_parser("skill-use", parents=[common_p], help="Increment skill weight")
    skill_p.add_argument("--name", required=True, help="Skill name in rykr_skills.md")

    # audit
    subparsers.add_parser("audit", parents=[common_p], help="Audit link integrity")

    args = parser.parse_args()

    if args.schema:
        schema = {
            "module": "rykr-memory",
            "version": "1.0.0",
            "actions": {
                "commit": {"args": ["--summary", "--skills"]},
                "skill-use": {"args": ["--name"]},
                "audit": {"args": []}
            },
            "flags": ["--json", "--schema"]
        }
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        sys.exit(0)

    if not args.subcommand:
        parser.print_help()
        sys.exit(2)

    dispatch_map = {
        "commit": action_commit,
        "skill-use": action_skill_use,
        "audit": action_audit
    }

    fn = dispatch_map.get(args.subcommand)
    handle_appliance_entry(
        module_name="memory",
        action_name=args.subcommand,
        action_fn=lambda _: fn(args),
        argv=sys.argv[1:]
    )


if __name__ == "__main__":
    main()
