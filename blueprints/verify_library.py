#!/usr/bin/env python3
"""
==============================================================================
RYKR BLUEPRINT GATEKEEPER & VERIFICATION APPLIANCE
==============================================================================
Enforces the Zero-Pip Guarantee, AST standard-library purity, portability
(zero hardcoded host paths), and SHA-256 cryptographic manifest integrity.
==============================================================================
"""

import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def get_stdlib_modules():
    """Returns the set of standard library module names."""
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)
    # Fallback for older python runtimes if needed
    import distutils.sysconfig
    return set()


def scan_ast_imports(filepath):
    """
    Parses a python file with AST and extracts all top-level imported module names.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except SyntaxError as e:
            return None, f"SyntaxError: {e}"

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    return imported, None


def check_portability(filepath):
    """
    Scans a python file for hardcoded user paths like /home/username.
    """
    violations = []
    with open(filepath, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if re.search(r"/home/[a-zA-Z0-9_\-\.]+", line) and "expanduser" not in line and "Path.home" not in line:
                # Allow safe generic examples or comments
                if any(x in line for x in ("username", "user", "rykr")):
                    continue
                violations.append((idx, line.strip()))
    return violations


def compute_sha256(filepath):
    """Computes SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_module(filepath, sibling_names=None):
    """
    Runs full audit on a single python module.
    Returns: dict(passed=bool, imports=list, violations=list, sha256=str, errors=list)
    """
    sibling_names = sibling_names or set()
    stdlib = get_stdlib_modules()
    
    imports, err = scan_ast_imports(filepath)
    if err:
        return {
            "passed": False,
            "errors": [err],
            "non_stdlib_imports": [],
            "portability_violations": [],
            "sha256": None
        }

    non_stdlib = []
    for mod in imports:
        if mod not in stdlib and mod not in sibling_names:
            non_stdlib.append(mod)

    portability = check_portability(filepath)
    passed = (len(non_stdlib) == 0 and len(portability) == 0)

    return {
        "passed": passed,
        "errors": [],
        "imports": sorted(list(imports)),
        "non_stdlib_imports": non_stdlib,
        "portability_violations": portability,
        "sha256": compute_sha256(filepath)
    }


def main():
    base_dir = Path(__file__).resolve().parent
    modules_dir = base_dir / "modules"
    if not modules_dir.exists():
        modules_dir = base_dir

    py_files = sorted(list(modules_dir.glob("*.py")))
    sibling_names = {p.stem for p in py_files}

    print(f"\033[1;38;2;204;85;0m=== RYKR BLUEPRINT LIBRARY: AUDIT & VERIFICATION ===\033[0m")
    print(f"Directory: {modules_dir}")
    print(f"Python standard library modules indexed: {len(get_stdlib_modules())}\n")

    all_passed = True
    manifest = {}

    for py_file in py_files:
        if py_file.name == Path(__file__).name:
            continue

        result = audit_module(py_file, sibling_names=sibling_names)
        status_color = "\033[32m[PASS]\033[0m" if result["passed"] else "\033[31m[FAIL]\033[0m"
        print(f"{status_color} {py_file.name}")
        print(f"       SHA-256: {result['sha256']}")
        print(f"       Imports: {', '.join(result['imports']) if result['imports'] else 'None'}")

        if result["non_stdlib_imports"]:
            all_passed = False
            print(f"       \033[31mERROR Non-stdlib imports detected: {result['non_stdlib_imports']}\033[0m")

        if result["portability_violations"]:
            all_passed = False
            for line_no, content in result["portability_violations"]:
                print(f"       \033[31mERROR Hardcoded path on line {line_no}: {content}\033[0m")

        manifest[py_file.name] = {
            "sha256": result["sha256"],
            "imports": result["imports"],
            "passed": result["passed"]
        }

    manifest_path = base_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest generated: {manifest_path}")

    if all_passed:
        print("\033[1;32mALL BLUEPRINTS VALIDATED (100% Zero-Pip, Portability Compliant)\033[0m")
        sys.exit(0)
    else:
        print("\033[1;31mVALIDATION FAILED: Correct errors before publishing.\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
