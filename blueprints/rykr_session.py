#!/usr/bin/env python3
"""
RYKR-SESSION: Deterministic Lifecycle & Attachment Appliance
Module 2 of RYKR-MODULAR-CONSOLE.
Uses rykr_bus for standardized I/O envelope and circuit breaking.
"""

import sys
import os
import subprocess
import argparse
import json
import time

# Add current dir to import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rykr_bus import (
    make_envelope,
    emit_payload,
    run_command_safe,
    CircuitBreakerTripped,
    handle_appliance_entry
)

DEFAULT_SESSION = "rykr"


def get_session_telemetry(session_name=DEFAULT_SESSION):
    """Inspects tmux ground truth for the target session."""
    has_res = subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True)
    if has_res.returncode != 0:
        return {
            "session_exists": False,
            "session_name": session_name,
            "attached_clients": 0,
            "windows": 0,
            "pane_pid": None
        }

    # Query pane PID and window count
    cmd = ["tmux", "list-panes", "-t", session_name, "-F", "#{pane_pid} #{pane_current_command}"]
    panes_res = subprocess.run(cmd, capture_output=True, text=True)
    panes = panes_res.stdout.strip().split("\n") if panes_res.stdout.strip() else []

    # Query attached client count
    clients_res = subprocess.run(["tmux", "list-clients", "-t", session_name], capture_output=True, text=True)
    clients = clients_res.stdout.strip().split("\n") if clients_res.stdout.strip() else []

    pane_pid = None
    if panes:
        try:
            pane_pid = int(panes[0].split()[0])
        except (IndexError, ValueError):
            pass

    return {
        "session_exists": True,
        "session_name": session_name,
        "attached_clients": len(clients),
        "windows": len(panes),
        "pane_pid": pane_pid
    }


def action_status(args):
    """Inspects and returns ground-truth session telemetry."""
    session = getattr(args, "session", DEFAULT_SESSION)
    telemetry = get_session_telemetry(session)
    msg = f"Session '{session}' active with {telemetry['attached_clients']} client(s)." if telemetry["session_exists"] else f"Session '{session}' does not exist."
    return telemetry, msg


def action_close(args):
    """
    Schedules clean delayed self-termination of the tmux session.
    Guarantees no SIGHUP truncation via double-fork / nohup / disown.
    """
    session = getattr(args, "session", DEFAULT_SESSION)
    delay = getattr(args, "delay", 3)

    telemetry = get_session_telemetry(session)
    if not telemetry["session_exists"]:
        return telemetry, f"Session '{session}' is already closed."

    # Non-blocking detached delayed suicide command
    # Uses sh with nohup to detach completely from the active controlling terminal
    kill_cmd = f"nohup sh -c 'sleep {delay} && tmux kill-session -t {session}' >/dev/null 2>&1 &"
    subprocess.Popen(kill_cmd, shell=True, preexec_fn=os.setpgrp)

    telemetry["countdown_seconds"] = delay
    telemetry["termination_scheduled"] = True
    return telemetry, f"Termination sequence armed for session '{session}' ({delay}s delay)."


def action_snap(args):
    """
    Interactive snap-to command for user terminals.
    In JSON/script mode, returns status and action intent.
    In TTY mode outside tmux, attaches or creates session.
    """
    session = getattr(args, "session", DEFAULT_SESSION)
    telemetry = get_session_telemetry(session)

    # If running interactively from an outside shell, execute actual tmux attach
    if sys.stdout.isatty() and not getattr(args, "json", False):
        if os.environ.get("TMUX"):
            print("[*] Already inside an active tmux session. Running directly.")
            os.execvp("agy", ["agy"])

        if telemetry["session_exists"]:
            print(f"[*] Snapping to active Rykr session '{session}' (detaching stale clients)...")
            os.execvp("tmux", ["tmux", "attach-session", "-d", "-t", session])
        else:
            print(f"[*] Booting fresh Rykr session '{session}'...")
            os.execvp("tmux", ["tmux", "new-session", "-s", session, "agy"])

    return telemetry, f"Snap target '{session}' inspected."


def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="Force machine-readable JSON envelope")
    common_parser.add_argument("--session", default=DEFAULT_SESSION, help="Target tmux session name")

    parser = argparse.ArgumentParser(description="Rykr Session Lifecycle Appliance", parents=[common_parser])
    parser.add_argument("--schema", action="store_true", help="Introspect appliance schema")

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")
    
    # status / audit
    subparsers.add_parser("status", parents=[common_parser], help="Get session telemetry")
    subparsers.add_parser("audit", parents=[common_parser], help="Audit active session state")

    # close
    close_p = subparsers.add_parser("close", parents=[common_parser], help="Clean delayed session termination")
    close_p.add_argument("--delay", type=int, default=3, help="Seconds before session kill")

    # snap
    subparsers.add_parser("snap", parents=[common_parser], help="Snap to session or inspect attachment")

    args = parser.parse_args()

    if args.schema:
        schema = {
            "module": "rykr-session",
            "version": "1.0.0",
            "actions": {
                "status": {"args": ["--session"]},
                "audit": {"args": ["--session"]},
                "close": {"args": ["--session", "--delay"]},
                "snap": {"args": ["--session"]}
            },
            "flags": ["--json", "--schema"]
        }
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        sys.exit(0)

    action = args.subcommand or "status"

    action_map = {
        "status": action_status,
        "audit": action_status,
        "close": action_close,
        "snap": action_snap
    }

    fn = action_map.get(action)
    if not fn:
        sys.stderr.write(f"Unknown subcommand: {action}\n")
        sys.exit(2)

    handle_appliance_entry(
        module_name="session",
        action_name=action,
        action_fn=lambda _: fn(args),
        argv=sys.argv[1:]
    )


if __name__ == "__main__":
    main()
