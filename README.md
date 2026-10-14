# The Rykr Framework
> **Sovereign Cognitive Architecture & Modular Systems Engineering on Consumer Silicon**

[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies: Zero](https://img.shields.io/badge/Dependencies-0%20(Pure%20Stdlib)-brightgreen.svg)](#the-zero-pip-guarantee)
[![Architecture: Satisfactory](https://img.shields.io/badge/Architecture-Satisfactory%20UNIX%20Pipes-orange.svg)](#philosophy)

The Rykr Framework is an open-source, dependency-free systems architecture designed to make local autonomous AI reliable, deterministic, and hardware-conscious on standard consumer PCs.

Instead of chasing parameter scale or wrapping local models in fragile multi-package bloat, Rykr treats the language model as an isolated engine block inside a strict, modular factory floor.

---

## Read the Whitepaper
The complete systems engineering thesis, historical evolution, and architectural rationale is documented in our master paper:
* **[WHITEPAPER.md](WHITEPAPER.md)** — *The Rykr Framework: A Systems Engineering Architecture for Sovereign Local AI on Consumer Silicon*

Additional documentation:
* **[ARCHITECTURE.md](ARCHITECTURE.md)** — The 4-Tier Memory Bus, Genesis Pipeline state machines, and hardware lifecycle governors.
* **[PHILOSOPHY.md](PHILOSOPHY.md)** — The Laws of Rykr, neurodivergent cognitive conservation, and radical anti-sycophancy.

---

## Core Breakthroughs

1. **The Satisfactory Modular Blueprint:** Code structured like an industrial factory floor. Every module does one job, bounded by strict input/output contracts and isolated UNIX pipes (`|`).
2. **The Zero-Pip Guarantee:** 100% Python standard library. Zero external packages, zero virtual environments, and zero dependency rot. Built to run out-of-the-box on clean Linux installs.
3. **The 4-Tier Memory Bus:** Eliminates model amnesia and VRAM runaway without expensive vector database sprawl.
   * **T0 (Kernel):** Pinned, invariant laws and persona.
   * **T1 (RAM):** Active blueprint cache with hard-capped context token budgets.
   * **T2 (Disk):** Plain-text, human-auditable atomic milestone ledger.
   * **T3 (Profile):** Dynamic host topology and operator accommodations.
4. **Hardware Coexistence (73 MiB Idle VRAM):** Designed for developers whose primary GPU lives in their gaming rig. Instant signal-trapped eviction drops VRAM from 10 GB down to **73 MiB** within two seconds when you launch a game.
5. **Decoupled 3D Braille Rasterizer:** High-definition 3D wireframe spatial visualization rendered directly in standard terminal windows using $2\times4$ Unicode Braille sub-pixels (`U+2800`–`U+28FF`) with zero line-wrapping.

---

## The Prime Blueprint Library

All modules live in [`blueprints/`](blueprints/) and can be run or pulled directly into your own projects:

| Module | Purpose | I/O Contract |
| :--- | :--- | :--- |
| **`rykr_bus.py`** | Standardized JSON Envelope & Circuit Breaker | Python API / CLI $\to$ JSON Envelope |
| **`rykr_node.py`** | Remote SSH Compute & Headless Dispatcher | CLI flags $\to$ Remote JSON Telemetry |
| **`rykr_session.py`** | Tmux Daemon Lifecycle & Attached Controller | CLI commands $\to$ Session Telemetry |
| **`rykr_memory.py`** | Atomic REF Ledger Committer & Archive Auditor | CLI flags $\to$ Atomic POSIX Rename |
| **`rykr_compress.py`**| RRS Token Compressor (72.8% Schema Reduction) | `stdin` $\to$ `stdout` (Compressed) + `stderr` |
| **`rykr_scene.py`** | 3D Spatial Cartesian Geometry Assembler | CLI flags $\to$ SceneGraph JSON Contract |
| **`rykr_blit.py`** | 30° Axonometric Braille Virtual Framebuffer | `stdin` (JSON) $\to$ `stdout` (Braille Buffer) |
| **`rykr_demo.py`** | Real-Time 3D Rotating Wireframe Engine (30 FPS) | CLI $\to$ Real-Time Terminal Animation |
| **`rykr_wol.py`** | Zero-Dependency Wake-on-LAN Magic Packet Broadcaster | CLI flags $\to$ UDP Broadcast / JSON Telemetry |
| **`rykr_dial.py`** | Interactive Curses TUI Speed-Dial & SSH Dispatcher | JSON ledger $\to$ Full-Screen Curses TUI |


---

## Quick Start

### 1. Test the 3D Braille Rasterizer
Clone the repository and run the real-time wireframe demo (pure standard library, zero installs):
```bash
python3 blueprints/rykr_demo.py
# Press Ctrl+C to exit cleanly
```
Or generate a single static frame:
```bash
python3 blueprints/rykr_demo.py --snapshot
```

### 2. Verify Standard Library Purity
Audit all modules against Python's standard library using AST parsing:
```bash
python3 blueprints/verify_library.py
```

### 3. Pull a Blueprint into Your Project
Use the built-in blueprint manager to copy pristine modules locally:
```bash
python3 blueprints/rykr_blueprint.py list
python3 blueprints/rykr_blueprint.py pull rykr_compress --dest ~/my_project/
```

### 4. Test RRS Token Compression
Pipe any JSON tool definition into the compressor to verify 70%+ token savings:
```bash
echo '[{"name": "fetch_data", "parameters": {"properties": {"query": {"type": "string"}}}}]' | \
python3 blueprints/rykr_compress.py --tools
```

---

## License
MIT License. Free to use, adapt, and build upon.
