# Rykr Framework: Technical Architecture

This document details the systems engineering schematics, mathematical projections, and state machines underlying the Rykr Framework.

---

## 1. The 4-Tier Memory Bus

Standard AI implementations attempt to maintain persistent context either by stuffing hundreds of historical turns into the active prompt (causing attention dispersion and KV-cache explosion) or by querying vector databases (introducing semantic drift and retrieval latency).

Rykr partitions memory into four distinct architectural tiers with strict bandwidth firewalls:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TIER 0: THE KERNEL (ROM)                        │
│  • Pinned immutable system prompt (Persona, Core Laws, State Machine)  │
│  • Zero runtime mutation | Bandwidth: ~1,500 tokens                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       TIER 1: THE WORKING BUFFER                       │
│  • Ephemeral context for the active module only                        │
│  • Hard token cap (<4,000 tokens) | Prevents VRAM KV-cache bloat       │
│  • Wiped clean upon task completion or [MEM_COMMIT] trigger            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    TIER 2: THE DISK ARCHIVE (LEDGER)                   │
│  • Append-only plain-text Markdown file (rykr_archive_index.md)        │
│  • Sequential atomic reference commits ([REF-001] to [REF-184])        │
│  • Human-readable, git-tracked, zero-database durability               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                   TIER 3: THE OPERATOR PROFILE (NVRAM)                 │
│  • Host network topology (Hostnames, IPs, SSH user mappings)           │
│  • Operator behavioral accommodations and communication protocols      │
│  • Decouples the engine from the physical deployment environment       │
└────────────────────────────────────────────────────────────────────────┘
```

### The Atomic Commit Appliance (`rykr_memory.py`)
To prevent corruption from sudden disconnections or kernel crashes, Tier 2 commits are executed through atomic POSIX replacement:
1. Load existing archive into memory.
2. Scan for the highest reference integer (`[REF-XXX]`).
3. Write the new reference block alongside historical data to a temporary file in the same filesystem.
4. Call `os.replace(temp_file, archive_path)` for atomic substitution.

---

## 2. The Genesis Pipeline State Machine

To enforce modularity and eliminate hallucinated "prompt thrashing," all software development inside Rykr must advance through a three-stage deterministic state machine:

```
                      [ NEW OBJECTIVE INGESTED ]
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │     PHASE 1: SKELETON     │
                    │         (~plan)           │
                    └─────────────┬─────────────┘
                                  │
                       [ ZERO CODE ALLOWED ]
                       Map data flow & contracts
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    PHASE 2: ADVERSARIAL   │
                    │      AUDIT (~redteam)     │
                    └─────────────┬─────────────┘
                                  │
                       [ STRESS TEST FRAMEWORK ]
                       Hunt for edge cases & leaks
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    PHASE 3: MODULAR       │
                    │   EXECUTION (~execute)    │
                    └─────────────┬─────────────┘
                                  │
                       [ UNIX PIPE PHILOSOPHY ]
                       Build ONE isolated module
                       Automated deterministic tests
                                  │
                                  ▼
                    [ LOCAL VALIDATION PASSES ]
                                  │
                                  ▼
                    [ COMMIT TO T2 ARCHIVE & SYNC ]
```

### Anti-Creep & Cognitive Failsafes
* **Anti-Creep Failsafe:** Any secondary ideas or feature enhancements suggested during Phase 3 are immediately rejected and pushed to `backlog.md` until the current active module passes local tests.
* **Cognitive Failsafe:** If a module requires excessive troubleshooting that clutters the Tier 1 buffer, an autonomous `[MEM_COMMIT]` is triggered to clear conversational debris and reload only the pristine module blueprint.

---

## 3. Hardware Lifecycle Matrix & Gaming Coexistence

The computing topology separates the primary controller from stateful hardware crunching across a local network:

```
[ HOST CONTROLLER (Node Alpha) ]
  • Linux Workstation (Native Residency)
  • Hosts Rykr Core, Memory Bus, and Git origin
  • Low CPU/RAM footprint; manages orchestration
            │
            │  OpenSSH BatchMode (BatchMode=yes, ConnectTimeout=5s)
            ▼
[ COMPUTE WORKER (Node Beta) ]
  • Dedicated Heavy Compute Node
  • NVIDIA GeForce GTX 1080 Ti (11GB Pascal Silicon)
  • Dual-workload: Autonomous LLM Inference & High-End PC Gaming
```

### The VRAM Eviction Governor
To prevent video game crashes, Ollama and the local inference engine are governed by deterministic lifecycle scripts:

```
                     [ INFERENCE ACTIVE ]
                   VRAM Usage: ~10,160 MiB
                              │
               User launches game / runs 'game-mode'
                              │
                              ▼
                   [ SIGINT / SIGTERM TRAP ]
              Kills inference process immediately
                              │
                              ▼
                   [ OLLAMA FORCE EVICTION ]
               Calls: ollama stop rykr-model
                              │
                              ▼
                      [ VRAM CLEARED ]
             VRAM Usage drops to: 73 MiB Idle (<2 sec)
            Zero GPU contention with video game engines
```

---

## 4. The 3D Braille Rasterizer Mathematics

To render smooth 3D spatial geometry in standard terminal windows without line-wrapping, `rykr_scene` and `rykr_blit` decouple geometry assembly from terminal blitting.

### 1. Axonometric Isometric Projection
Cartesian coordinates $(X, Y, Z)$ are projected onto a 2D virtual canvas $(X', Y')$ using standard $30^\circ$ axonometric transformation:

$$X' = (X - Y) \cdot \cos(30^\circ) = (X - Y) \cdot 0.8660$$

$$Y' = (X + Y) \cdot \sin(30^\circ) - Z = (X + Y) \cdot 0.5000 - Z$$

To correct for the vertical aspect ratio distortion inherent to monospace fonts (where characters are approximately twice as tall as they are wide), an aspect factor $AR = 0.92$ is applied to $Y'$:

$$Y'_{\text{corrected}} = Y' \cdot AR$$

### 2. The $2\times4$ Braille Sub-Pixel Virtual Framebuffer
Standard terminal characters are mapped to Unicode Braille patterns (`U+2800` through `U+28FF`). Each character represents a $2\times4$ sub-pixel matrix:

```
Dot Mapping:
[ Dot 1 (0x01) ]  [ Dot 4 (0x08) ]
[ Dot 2 (0x02) ]  [ Dot 5 (0x10) ]
[ Dot 3 (0x04) ]  [ Dot 6 (0x20) ]
[ Dot 7 (0x40) ]  [ Dot 8 (0x80) ]
```

Line segments are drawn across the sub-pixel grid using an integer-only Bresenham algorithm. The final Unicode character is synthesized by summing the active dot bitmasks:

$$\text{Braille Codepoint} = 0\text{x}2800 + \sum_{k=1}^{8} \text{Bitmask}_k$$

### 3. Non-Clobbering Label Masks
When labels are placed on a 3D diagram, a bounding box cutout is registered in character space. The rasterizer bypasses sub-pixel dot generation inside the label box, ensuring text characters are never clobbered or obscured by crossing vector lines.
