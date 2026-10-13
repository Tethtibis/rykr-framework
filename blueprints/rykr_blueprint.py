#!/usr/bin/env python3
"""
==============================================================================
RYKR-BLUEPRINT: BLUEPRINT LIBRARY CLI & DEPLOYMENT APPLIANCE
==============================================================================
Manages the installation, inspection, and verification of pure Satisfactory-style
Python standard library modules. Prevents FUSE execution lockups by copying
modules locally before execution.
==============================================================================
"""

import sys
import os
import shutil
import argparse
import json
from pathlib import Path

# ANSI colors
ORANGE = "\033[38;2;204;85;0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
GRAY = "\033[90m"
RESET = "\033[0m"

MODULE_CATALOG = {
    "rykr_bus": {
        "filename": "rykr_bus.py",
        "description": "Standardized I/O Envelope, Circuit Breaker & Telemetry Substrate",
        "io_contract": "Python API & CLI | stdin/args -> JSON Envelope stdout",
        "version": "1.0.0"
    },
    "rykr_node": {
        "filename": "rykr_node.py",
        "description": "Distributed Compute & Remote SSH Execution Appliance",
        "io_contract": "CLI flags (--host, --cmd) -> JSON Telemetry stdout",
        "version": "1.0.0"
    },
    "rykr_session": {
        "filename": "rykr_session.py",
        "description": "Tmux Daemon Lifecycle Governor & Detached Session Controller",
        "io_contract": "CLI commands (attach, detach, status, kill) -> JSON Telemetry",
        "version": "1.0.0"
    },
    "rykr_memory": {
        "filename": "rykr_memory.py",
        "description": "Atomic REF Ledger Committer & Archive Integrity Verifier",
        "io_contract": "CLI flags (--commit, --audit) -> Atomic File Update",
        "version": "1.0.0"
    },
    "rykr_compress": {
        "filename": "rykr_compress.py",
        "description": "RRS Token & Context Compressor (70-75% JSON Schema Reduction)",
        "io_contract": "UNIX pipe | stdin (JSON/Text) -> stdout (RRS Compressed) + stderr (Telemetry)",
        "version": "1.0.0"
    },
    "rykr_scene": {
        "filename": "rykr_scene.py",
        "description": "3D Cartesian Spatial Geometry Assembler",
        "io_contract": "CLI flags / stdin -> SceneGraph JSON contract stdout",
        "version": "1.0.0"
    },
    "rykr_blit": {
        "filename": "rykr_blit.py",
        "description": "Mathematical 30° Axonometric Braille Rasterizer (2x4 sub-pixel)",
        "io_contract": "stdin (SceneGraph JSON) -> stdout (Braille Framebuffer)",
        "version": "1.0.0"
    },
    "rykr_demo": {
        "filename": "rykr_demo.py",
        "description": "Real-time 3D Wireframe Rotation Engine (30 FPS)",
        "io_contract": "CLI (--snapshot / interactive) -> stdout (Animated Braille)",
        "version": "1.0.0"
    }
}


def get_library_paths():
    """Locates library root and modules directory."""
    # Priority: Env var -> Script parent -> Google Drive vault
    env_path = os.environ.get("RYKR_BLUEPRINT_DIR")
    if env_path and os.path.isdir(env_path):
        base = Path(env_path)
    else:
        base = Path(__file__).resolve().parent

    modules = base / "modules"
    if not modules.is_dir():
        # Fallback to current directory if files are alongside
        modules = base
    return base, modules


def list_modules():
    base, modules_dir = get_library_paths()
    manifest_path = base / "manifest.json"
    manifest = {}
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception:
            pass

    print(f"\n{ORANGE}{BOLD}=== RYKR PRIME BLUEPRINT LIBRARY ==={RESET}")
    print(f"{GRAY}Library Path: {modules_dir}{RESET}\n")

    for key, info in sorted(MODULE_CATALOG.items()):
        fn = info["filename"]
        target = modules_dir / fn
        exists = target.is_file()
        sha = manifest.get(fn, {}).get("sha256", "unverified")[:12] if exists else "missing"
        status_badge = f"{GREEN}[READY]{RESET}" if exists else f"{RED}[NOT FOUND]{RESET}"

        print(f" {status_badge} {BOLD}{key}{RESET} (v{info['version']}) -- {sha}...")
        print(f"         {info['description']}")
        print(f"         {GRAY}Contract: {info['io_contract']}{RESET}\n")


def pull_module(name, dest_dir):
    base, modules_dir = get_library_paths()
    clean_name = name.replace(".py", "")
    if clean_name not in MODULE_CATALOG:
        print(f"{RED}Error: Module '{name}' not found in catalog.{RESET}")
        print(f"Available: {', '.join(sorted(MODULE_CATALOG.keys()))}")
        sys.exit(1)

    info = MODULE_CATALOG[clean_name]
    src_file = modules_dir / info["filename"]
    if not src_file.is_file():
        print(f"{RED}Error: Source file {src_file} does not exist.{RESET}")
        sys.exit(1)

    dest_path = Path(dest_dir).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    out_file = dest_path / info["filename"]

    # Also copy dependency rykr_bus if module requires it and not present
    dependencies = []
    if clean_name in ("rykr_node", "rykr_session", "rykr_memory"):
        bus_file = dest_path / "rykr_bus.py"
        if not bus_file.is_file():
            shutil.copy2(modules_dir / "rykr_bus.py", bus_file)
            os.chmod(bus_file, 0o755)
            dependencies.append("rykr_bus.py")

    shutil.copy2(src_file, out_file)
    os.chmod(out_file, 0o755)

    print(f"{GREEN}{BOLD}✓ Installed:{RESET} {out_file}")
    if dependencies:
        print(f"{GRAY}  Linked dependencies: {', '.join(dependencies)}{RESET}")
    print(f"{GRAY}  Execution syntax: python3 {out_file.name} [args]{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Rykr Prime Blueprint Library Appliance")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List available golden blueprint modules")

    pull_parser = subparsers.add_parser("pull", help="Pull/install a blueprint into a local project")
    pull_parser.add_argument("module", help="Name of module (e.g. rykr_compress, rykr_bus)")
    pull_parser.add_argument("--dest", default=".", help="Target directory (default: current directory)")

    subparsers.add_parser("verify", help="Run AST stdlib and cryptographic audit")

    args = parser.parse_args()

    if args.command == "list" or not args.command:
        list_modules()
    elif args.command == "pull":
        pull_module(args.module, args.dest)
    elif args.command == "verify":
        base, _ = get_library_paths()
        verifier = base / "verify_library.py"
        if verifier.is_file():
            import subprocess
            res = subprocess.run([sys.executable, str(verifier)], cwd=str(base))
            sys.exit(res.returncode)
        else:
            print(f"{RED}Error: verify_library.py not found at {verifier}{RESET}")
            sys.exit(1)


if __name__ == "__main__":
    main()
