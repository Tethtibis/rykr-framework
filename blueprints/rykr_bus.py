#!/usr/bin/env python3
"""
RYKR-BUS: Standardized I/O Envelope, Circuit Breaker & Telemetry Substrate
Zero-dependency Python 3 standard library core.
Part of RYKR-MODULAR-CONSOLE (Satisfactory Blueprint).
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime, timezone

# Burnt orange ANSI aesthetic for TUI output
COLOR_ORANGE = "\033[38;2;204;85;0m"
COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"
COLOR_BOLD = "\033[1m"


class CircuitBreakerTripped(Exception):
    def __init__(self, breaker_name, reason, suggested_action=None, telemetry=None):
        super().__init__(reason)
        self.breaker_name = breaker_name
        self.reason = reason
        self.suggested_action = suggested_action or "INSPECT_LOGS"
        self.telemetry = telemetry or {}


def get_origin_node():
    """Detect local hostname or default to rykr-prime."""
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "rykr-prime"


def format_iso_timestamp():
    return datetime.now(timezone.utc).isoformat()


def make_envelope(module, action, status="SUCCESS", exit_code=0, telemetry=None, diagnostics=None, breaker=None):
    """
    Constructs the canonical Rykr JSON envelope.
    status: SUCCESS | TRIPPED | CRITICAL
    """
    payload = {
        "timestamp": format_iso_timestamp(),
        "origin": get_origin_node(),
        "module": module,
        "action": action,
        "status": status,
        "exit_code": exit_code,
        "telemetry": telemetry or {},
        "diagnostics": diagnostics or {"error_code": None, "message": "OK"}
    }
    if breaker:
        payload["circuit_breaker"] = breaker
    return payload


def emit_payload(envelope, force_json=False):
    """
    Dual-Track Emission:
    - If force_json is True or stdout is not a TTY: writes rigid machine-readable JSON to stdout.
    - If interactive TTY and not force_json: writes burnt-orange clean TUI output.
    """
    is_tty = sys.stdout.isatty()
    as_json = force_json or (not is_tty)

    if as_json:
        # Guarantee stdout gets ONLY pure valid JSON
        sys.stdout.write(json.dumps(envelope, indent=2) + "\n")
        sys.stdout.flush()
    else:
        # High-contrast TUI output for Operator
        status = envelope.get("status", "UNKNOWN")
        mod = envelope.get("module", "appliance")
        act = envelope.get("action", "")

        status_color = COLOR_GREEN if status == "SUCCESS" else (COLOR_YELLOW if status == "TRIPPED" else COLOR_RED)
        sys.stdout.write(f"\n{COLOR_BOLD}{COLOR_ORANGE}[RYKR::{mod.upper()}]{COLOR_RESET} -> {act}\n")
        sys.stdout.write(f"Status: {status_color}{status}{COLOR_RESET} (Exit Code: {envelope.get('exit_code')})\n")

        if envelope.get("circuit_breaker"):
            cb = envelope["circuit_breaker"]
            sys.stdout.write(f"{COLOR_YELLOW}[!] CIRCUIT BREAKER TRIPPED:{COLOR_RESET} {cb.get('name')}\n")
            sys.stdout.write(f"    Reason: {cb.get('reason')}\n")
            sys.stdout.write(f"    Action: {cb.get('suggested_action')}\n")

        telemetry = envelope.get("telemetry", {})
        if telemetry:
            sys.stdout.write(f"{COLOR_ORANGE}Telemetry:{COLOR_RESET}\n")
            for k, v in telemetry.items():
                sys.stdout.write(f"  • {k}: {v}\n")

        diag = envelope.get("diagnostics", {})
        if diag and diag.get("message") and diag.get("message") != "OK":
            sys.stdout.write(f"Diagnostics: {diag.get('message')}\n")
        sys.stdout.write("\n")
        sys.stdout.flush()


def run_command_safe(cmd, timeout_seconds=10, check_breaker=None, env=None, cwd=None):
    """
    Deterministic sub-process execution protected by a strict local timeout.
    Returns: (stdout, stderr, exit_code)
    Raises: CircuitBreakerTripped on timeout or custom rule violation.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=isinstance(cmd, str),
            env=env or os.environ.copy(),
            cwd=cwd
        )
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        exit_code = proc.returncode

        if check_breaker:
            check_breaker(exit_code, stdout, stderr)

        return stdout, stderr, exit_code

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise CircuitBreakerTripped(
            breaker_name="EXEC_TIMEOUT",
            reason=f"Command timed out after {timeout_seconds} seconds.",
            suggested_action="CHECK_NETWORK_OR_PROCESS"
        )
    except Exception as e:
        raise CircuitBreakerTripped(
            breaker_name="EXEC_EXCEPTION",
            reason=str(e),
            suggested_action="INSPECT_LOCAL_SUBSYSTEM"
        )


def handle_appliance_entry(module_name, action_name, action_fn, argv=None):
    """
    Universal dispatcher wrapper for all appliances.
    Captures unhandled exceptions, evaluates circuit breakers, and enforces envelope delivery.
    """
    if argv is None:
        argv = sys.argv[1:]

    force_json = "--json" in argv
    clean_argv = [a for a in argv if a != "--json"]

    try:
        telemetry, diag_msg = action_fn(clean_argv)
        envelope = make_envelope(
            module=module_name,
            action=action_name,
            status="SUCCESS",
            exit_code=0,
            telemetry=telemetry,
            diagnostics={"error_code": None, "message": diag_msg or "OK"}
        )
        emit_payload(envelope, force_json=force_json)
        sys.exit(0)

    except CircuitBreakerTripped as cbt:
        envelope = make_envelope(
            module=module_name,
            action=action_name,
            status="TRIPPED",
            exit_code=1,
            telemetry=cbt.telemetry,
            diagnostics={"error_code": cbt.breaker_name, "message": cbt.reason},
            breaker={
                "name": cbt.breaker_name,
                "reason": cbt.reason,
                "suggested_action": cbt.suggested_action
            }
        )
        emit_payload(envelope, force_json=force_json)
        sys.exit(1)

    except Exception as e:
        envelope = make_envelope(
            module=module_name,
            action=action_name,
            status="CRITICAL",
            exit_code=2,
            telemetry={},
            diagnostics={"error_code": "UNCAUGHT_FATAL", "message": str(e)}
        )
        emit_payload(envelope, force_json=force_json)
        sys.exit(2)


if __name__ == "__main__":
    # Self-test / Introspection
    if len(sys.argv) > 1 and sys.argv[1] == "--schema":
        schema = {
            "module": "rykr-bus",
            "version": "1.0.0",
            "description": "Standardized I/O Envelope & Circuit Breaker Engine",
            "envelope_keys": ["timestamp", "origin", "module", "action", "status", "exit_code", "telemetry", "diagnostics", "circuit_breaker"],
            "flags": ["--json", "--schema"]
        }
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        sys.exit(0)

    # Test execution
    test_env = make_envelope(
        module="bus-test",
        action="self-test",
        status="SUCCESS",
        telemetry={"latency_ms": 1.2, "status": "nominal"}
    )
    emit_payload(test_env, force_json="--json" in sys.argv)
