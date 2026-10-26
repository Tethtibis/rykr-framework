#!/usr/bin/env python3
"""
==============================================================================
RYKR-PUBLISH: PRE-PUBLISH GITHUB SANITIZER, SYNTAX VERIFIER & PAYLOAD REPACKER
==============================================================================
Zero-Pip Python 3 Standard Library Core.
Scans target repositories for hardcoded home paths, private hostnames, keys,
and tokens; purges __pycache__ artifacts; validates Python/POSIX shell syntax;
and synchronizes embedded base64 tarballs inside standalone deployer scripts.
==============================================================================
"""

import argparse
import base64
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
from datetime import datetime, timezone


def build_forbidden_patterns():
    """Builds portable + host-aware forbidden regex patterns for pre-publish scanning."""
    home_dir = os.path.expanduser("~")
    hostname = socket.gethostname()
    patterns = [
        (re.escape(home_dir), f"Hardcoded current operator home path ({home_dir})"),
        (r"BEGIN (OPENSSH|RSA|EC) PRIVATE KEY", "Private cryptographic key material"),
        (r"\b(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b", "GitHub personal access token"),
        (r"\bAIza[0-9A-Za-z\-_]{35}\b", "Google Cloud / Gemini API key leak"),
        (r"\bsk-[0-9A-Za-z]{20,}\b", "OpenAI / LLM provider secret key leak"),
    ]
    if hostname and hostname.lower() not in ("localhost", "ubuntu", "debian"):
        patterns.append((rf"\b{re.escape(hostname)}\b", f"Local host identifier leak ({hostname})"))

    # Load optional custom operator patterns from ~/.config/rykr/publish_patterns.json
    custom_cfg = os.path.join(home_dir, ".config", "rykr", "publish_patterns.json")
    if os.path.isfile(custom_cfg):
        try:
            with open(custom_cfg, "r", encoding="utf-8") as f:
                extra = json.load(f)
                if isinstance(extra, list):
                    for item in extra:
                        if isinstance(item, dict) and "pattern" in item and "reason" in item:
                            patterns.append((item["pattern"], item["reason"]))
        except Exception:
            pass
    return patterns


BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".iso", ".gz", ".tgz", ".deb", ".pyc"}


def emit(action, status, exit_code, data, message="OK", as_json=False):
    envelope = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "origin": socket.gethostname(),
        "module": "rykr-publish",
        "action": action,
        "status": status,
        "exit_code": exit_code,
        "data": data,
        "diagnostics": {"message": message},
    }
    if as_json:
        sys.stdout.write(json.dumps(envelope, indent=2) + "\n")
    else:
        color = "\033[38;2;204;85;0m" if status == "SUCCESS" else "\033[31m"
        sys.stdout.write(f"{color}[RYKR-PUBLISH // {action.upper()} : {status}]\033[0m {message}\n")
        if data.get("violations"):
            for v in data["violations"]:
                sys.stdout.write(f"  \033[31m✗ {v['file']}:{v['line']} -> {v['reason']}\033[0m\n")
        if data.get("syntax_errors"):
            for s in data["syntax_errors"]:
                sys.stdout.write(f"  \033[31m✗ {s['file']} -> {s['error']}\033[0m\n")
    sys.exit(exit_code)


def purge_pycache(repo_dir):
    removed = []
    for root, dirs, files in os.walk(repo_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        for d in list(dirs):
            if d == "__pycache__":
                full_p = os.path.join(root, d)
                shutil.rmtree(full_p, ignore_errors=True)
                removed.append(os.path.relpath(full_p, repo_dir))
                dirs.remove(d)
        for f in files:
            if f.endswith(".pyc"):
                full_f = os.path.join(root, f)
                try:
                    os.remove(full_f)
                    removed.append(os.path.relpath(full_f, repo_dir))
                except OSError:
                    pass
    return removed


def audit_repo(repo_dir, as_json=False):
    repo_dir = os.path.abspath(repo_dir)
    if not os.path.isdir(repo_dir):
        emit("audit", "ERROR", 1, {}, f"Directory not found: {repo_dir}", as_json)

    purged = purge_pycache(repo_dir)
    forbidden_patterns = build_forbidden_patterns()
    violations = []
    syntax_errors = []
    files_scanned = 0

    for root, dirs, files in os.walk(repo_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        for fname in sorted(files):
            ext = os.path.splitext(fname)[1].lower()
            if ext in BINARY_EXTENSIONS:
                continue
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, repo_dir)
            files_scanned += 1

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except OSError:
                continue

            for idx, line in enumerate(lines, start=1):
                for pattern, reason in forbidden_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            "file": relpath,
                            "line": idx,
                            "reason": reason,
                        })

            first_line = lines[0] if lines else ""
            if ext == ".sh" or ("bash" in first_line and first_line.startswith("#!")):
                res = subprocess.run(["bash", "-n", fpath], capture_output=True, text=True)
                if res.returncode != 0:
                    syntax_errors.append({"file": relpath, "error": res.stderr.strip()})
            elif ext == ".py" or ("python" in first_line and first_line.startswith("#!")):
                res = subprocess.run([sys.executable, "-B", "-m", "py_compile", fpath], capture_output=True, text=True)
                if res.returncode != 0:
                    syntax_errors.append({"file": relpath, "error": res.stderr.strip()})

    purged.extend(purge_pycache(repo_dir))

    data = {
        "repo": repo_dir,
        "files_scanned": files_scanned,
        "pycache_purged": purged,
        "violations": violations,
        "syntax_errors": syntax_errors,
    }

    if violations or syntax_errors:
        msg = f"Audit BLOCKED: {len(violations)} leak violation(s), {len(syntax_errors)} syntax error(s)."
        emit("audit", "BLOCKED", 2, data, msg, as_json)
    else:
        msg = f"Clean! Scanned {files_scanned} files (0 leaks, 0 syntax errors, {len(purged)} cache artifacts purged)."
        emit("audit", "SUCCESS", 0, data, msg, as_json)


def repack_embedded(repo_dir, script_name, as_json=False):
    repo_dir = os.path.abspath(repo_dir)
    script_path = os.path.join(repo_dir, script_name)
    if not os.path.isfile(script_path):
        emit("repack", "ERROR", 1, {}, f"Deployer script not found: {script_path}", as_json)

    purge_pycache(repo_dir)

    buf = io.BytesIO()
    subdirs = [d for d in ("bin", "conf", "scripts") if os.path.isdir(os.path.join(repo_dir, d))]
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for d in subdirs:
            tar.add(os.path.join(repo_dir, d), arcname=d)

    raw_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    wrapped_b64 = "\n".join(raw_b64[i:i + 76] for i in range(0, len(raw_b64), 76))

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(base64 -d << 'EOF_EMBEDDED_ASSETS'[^\n]*\n).*?(\nEOF_EMBEDDED_ASSETS)"
    if not re.search(pattern, content, flags=re.DOTALL):
        emit("repack", "ERROR", 1, {}, f"No EOF_EMBEDDED_ASSETS block found in {script_name}", as_json)

    updated = re.sub(pattern, r"\g<1>" + wrapped_b64 + r"\g<2>", content, flags=re.DOTALL)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(updated)

    emit(
        "repack",
        "SUCCESS",
        0,
        {"script": script_path, "subdirs_packed": subdirs, "payload_bytes": len(wrapped_b64)},
        f"Repacked {subdirs} into {script_name} ({len(wrapped_b64)} base64 bytes).",
        as_json,
    )


def main():
    if "--schema" in sys.argv:
        schema = {
            "module": "publish",
            "description": "Pre-publish GitHub leak sanitizer, syntax verifier, and embedded payload repacker",
            "actions": {
                "audit": "Scan repository for private hostnames/IPs/paths, purge __pycache__, and syntax-check scripts",
                "repack": "Synchronize embedded base64 tarball inside a standalone deployer script",
            },
        }
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Rykr Public GitHub Sanitizer & Publisher")
    sub = parser.add_subparsers(dest="action")

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--dir", default=".", help="Target repository directory")
    p_audit.add_argument("--json", action="store_true")

    p_repack = sub.add_parser("repack")
    p_repack.add_argument("--dir", default=".", help="Target repository directory")
    p_repack.add_argument("--script", default="deploy.sh", help="Standalone script with EOF_EMBEDDED_ASSETS")
    p_repack.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.action == "audit":
        audit_repo(args.dir, args.json)
    elif args.action == "repack":
        repack_embedded(args.dir, args.script, args.json)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
