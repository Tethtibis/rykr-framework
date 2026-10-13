#!/usr/bin/env python3
"""
==============================================================================
RYKR-NODE: DISTRIBUTED COMPUTE & REMOTE SSH APPLIANCE
==============================================================================
Module 3 of the Rykr Modular Framework.
Standardized remote compute router and headless worker dispatcher over SSH.
Enforces OpenSSH BatchMode, strict signal timeouts, and JSON telemetry emission.
Zero external dependencies (pure Python 3 standard library).
==============================================================================
"""

import sys
import os
import subprocess
import argparse
import json
import re
import time
from pathlib import Path

# Add current dir to import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rykr_bus import (
    make_envelope,
    emit_payload,
    run_command_safe,
    CircuitBreakerTripped,
    handle_appliance_entry
)


def load_config():
    """Loads configuration from ~/.config/rykr/rykr.conf or env/defaults."""
    conf = {
        "WORKER_HOST": os.environ.get("RYKR_WORKER_HOST", "127.0.0.1"),
        "REMOTE_HOST": os.environ.get("RYKR_REMOTE_HOST", "localhost"),
        "SSH_USER": os.environ.get("RYKR_SSH_USER", os.environ.get("USER", "rykr")),
        "SSH_TIMEOUT": int(os.environ.get("RYKR_SSH_TIMEOUT", "5"))
    }
    conf_path = os.path.expanduser("~/.config/rykr/rykr.conf")
    if os.path.isfile(conf_path):
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        conf[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return conf


CONFIG = load_config()


def run_ssh_remote(host, remote_cmd, timeout=None, user=None):
    """
    Executes a remote command over SSH with strict batchmode flags and timeout.
    Returns: (stdout, stderr, exit_code)
    Raises: CircuitBreakerTripped if unreachable or fails.
    """
    ssh_user = user or CONFIG["SSH_USER"]
    timeout_sec = timeout or CONFIG["SSH_TIMEOUT"]
    target = f"{ssh_user}@{host}" if ssh_user else host

    ssh_args = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={timeout_sec}",
        "-o", "StrictHostKeyChecking=accept-new",
        target,
        remote_cmd
    ]

    try:
        proc = subprocess.Popen(
            ssh_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=timeout_sec + 2)
        code = proc.returncode

        if code == 255:
            # OpenSSH error (host down, key rejected, or timeout)
            raise CircuitBreakerTripped(
                breaker_name="SSH_CONNECTION_REFUSED",
                reason=f"Failed to connect to {target}: {stderr.strip()}",
                suggested_action="CHECK_NETWORK_OR_SSH_KEY",
                telemetry={"target": target, "exit_code": code}
            )

        return stdout, stderr, code

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise CircuitBreakerTripped(
            breaker_name="SSH_TIMEOUT",
            reason=f"SSH execution on {target} timed out after {timeout_sec}s.",
            suggested_action="INSPECT_REMOTE_NETWORK_OR_RETRY"
        )


def action_worker(args):
    """Controls the local compute worker node lifecycle."""
    subaction = args.node_action
    host = CONFIG["WORKER_HOST"]

    if subaction == "start":
        stdout, stderr, code = run_ssh_remote(host, "rykr-satellite start", timeout=10)
        return {
            "node": "worker",
            "host": host,
            "action": "start",
            "status": "online"
        }, "Worker service started."

    elif subaction == "stop":
        stdout, stderr, code = run_ssh_remote(host, "rykr-satellite stop", timeout=10)
        return {
            "node": "worker",
            "host": host,
            "action": "stop",
            "vram_evicted": True
        }, "Worker stopped and hardware memory evicted."

    elif subaction == "status":
        stdout, stderr, code = run_ssh_remote(host, "rykr-satellite status", timeout=8)
        return {
            "node": "worker",
            "host": host,
            "action": "status",
            "output": stdout.strip()
        }, stdout.strip()

    raise CircuitBreakerTripped(
        breaker_name="INVALID_ACTION",
        reason=f"Unknown worker action: {subaction}",
        suggested_action="USE_START_STOP_OR_STATUS"
    )


def action_remote(args):
    """Checks WAN SSH connectivity to secondary remote host."""
    subaction = args.node_action
    host = CONFIG["REMOTE_HOST"]
    user = CONFIG["SSH_USER"]

    if subaction in ["ping", "status"]:
        stdout, stderr, code = run_ssh_remote(host, "echo PONG", timeout=5, user=user)
        is_alive = (code == 0 and "PONG" in stdout)
        return {
            "node": "remote",
            "host": host,
            "reachable": is_alive
        }, f"Remote ping {'SUCCESS' if is_alive else 'FAILED'}."

    raise CircuitBreakerTripped(
        breaker_name="INVALID_ACTION",
        reason=f"Unknown remote action: {subaction}",
        suggested_action="USE_PING_OR_STATUS"
    )


def action_dispatch(args):
    """Universal Headless Worker Dispatch to any target host."""
    host = args.host
    cmd = args.cmd
    detach = getattr(args, "detach", False)
    user = getattr(args, "user", None) or CONFIG["SSH_USER"]

    if detach:
        remote_exec = f"nohup sh -c '{cmd}' >/tmp/rykr_worker_{int(time.time())}.log 2>&1 & echo $!"
        stdout, stderr, code = run_ssh_remote(host, remote_exec, timeout=6, user=user)
        remote_pid = stdout.strip()
        return {
            "host": host,
            "dispatched": True,
            "detached": True,
            "remote_pid": remote_pid,
            "command": cmd
        }, f"Worker dispatched to {host} in background (PID: {remote_pid})."
    else:
        stdout, stderr, code = run_ssh_remote(host, cmd, timeout=args.timeout, user=user)
        return {
            "host": host,
            "dispatched": True,
            "exit_code": code,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }, f"Worker completed on {host} with exit code {code}."


def main():
    common_p = argparse.ArgumentParser(add_help=False)
    common_p.add_argument("--json", action="store_true", help="Force machine-readable JSON envelope")

    parser = argparse.ArgumentParser(description="Rykr Remote Node Appliance", parents=[common_p])
    parser.add_argument("--schema", action="store_true", help="Introspect appliance schema")

    subparsers = parser.add_subparsers(dest="subcommand", help="Target node or action")

    # worker
    worker_p = subparsers.add_parser("worker", parents=[common_p], help="Control local compute worker node")
    worker_p.add_argument("node_action", choices=["start", "stop", "status"], help="Action to perform")

    # remote
    remote_p = subparsers.add_parser("remote", parents=[common_p], help="Check remote node connectivity")
    remote_p.add_argument("node_action", choices=["ping", "status"], help="Action to perform")

    # dispatch
    disp_p = subparsers.add_parser("dispatch", parents=[common_p], help="Dispatch remote task over SSH")
    disp_p.add_argument("--host", required=True, help="Remote host IP/hostname")
    disp_p.add_argument("--cmd", required=True, help="Command to execute remotely")
    disp_p.add_argument("--user", default=None, help="Remote SSH user")
    disp_p.add_argument("--detach", action="store_true", help="Run detached in background")
    disp_p.add_argument("--timeout", type=int, default=15, help="Execution timeout in seconds")

    args = parser.parse_args()

    if args.schema:
        schema = {
            "module": "rykr-node",
            "version": "1.0.0",
            "actions": {
                "worker": {"choices": ["start", "stop", "status"]},
                "remote": {"choices": ["ping", "status"]},
                "dispatch": {"flags": ["--host", "--cmd", "--user", "--detach", "--timeout"]}
            },
            "flags": ["--json", "--schema"]
        }
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        sys.exit(0)

    if not args.subcommand:
        parser.print_help()
        sys.exit(2)

    dispatch_map = {
        "worker": action_worker,
        "remote": action_remote,
        "dispatch": action_dispatch
    }

    fn = dispatch_map.get(args.subcommand)
    if fn:
        handle_appliance_entry("rykr-node", fn, args, as_json=args.json)


if __name__ == "__main__":
    main()
