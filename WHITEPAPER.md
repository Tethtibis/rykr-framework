# The Rykr Framework
### A Systems Engineering Architecture for Sovereign Local AI on Consumer Silicon

---

## 1. The Crisis of Fragile AI

We did not set out to write an academic thesis. We set out to solve an infuriating practical problem.

Over the past two years, the AI industry has developed a single, predictable reflex to every software failure: **throw more parameters at it**. When a local model loses track of its task, the advice is to upgrade from an 8B model to a 70B model. When an agent hallucinates invalid tool syntax, people reach for massive frontier APIs. When a runtime crashes, developers wrap it in three more Python frameworks, dragging in hundreds of ephemeral `pip` dependencies that rot within ninety days.

For people running workloads on consumer hardware in the real world, this approach is a dead end. 

If you run an agent on a machine with an 11GB graphics card, you cannot simply "scale up." If an agent leaks memory across a twenty-turn loop, your GPU runs out of VRAM. If an agent crashes because a local model dropped a quotation mark inside a JSON string, your entire automated workflow halts. And if an assistant demands twenty manual decisions just to format a text file, it is not saving mental bandwidth—it is creating administrative friction.

The problem with modern agentic AI is not that local models are "too dumb." The problem is that **modern agent frameworks are mechanical disasters**. They treat the language model as the entire machine rather than an engine block. When the chassis rattles at highway speeds, they try to carve a new shape of tire instead of bolting on shock absorbers.

The Rykr Framework was engineered on a different premise: **Systemic architecture beats parameter scaling.**

By isolating probabilistic language models behind strict UNIX pipes, enforcing an invariant four-tier memory bus, capping context windows, and governing host hardware with deterministic OS-level controls, we turned an ordinary consumer PC into a resilient, autonomous workstation.

---

## 2. The Cognitive Origin: Advocacy and Conservation

The root of this architecture is deeply human. 

For a neurodivergent engineer, executive function is not an infinite resource. Mental bandwidth has a hard daily budget. Traditional software constantly drains that budget: confirmation modals, ambiguous error messages, broken dependencies, and conversational AI that apologizes three times before failing to execute a command.

Rykr was created to be the opposite of that: an **Executive Advocate and Cognitive Shield**. 

From its very first commit, the framework was governed by core operational laws rather than polite conversational prompts:

* **The Law of Cognitive Conservation:** Never force the human operator to make a low-level administrative decision if the machine can resolve it deterministically. No open-ended questions that trigger decision fatigue. Offer optimized paths and require simple binary confirmation.
* **The Law of Radical Honesty (Anti-Sycophancy):** Corporate RLHF (Reinforcement Learning from Human Feedback) trains language models to be polite, agreeable, and deferential—even when an idea is mathematically or architecturally flawed. Rykr rejects sycophancy entirely. It is required to state technical realities directly, dismantle architectural fallacies, and refuse wishful thinking.
* **The Law of Intent Optimization:** Evaluate what the user is trying to accomplish, not just the mechanical words they typed. If a workflow introduces friction, bypass the bureaucracy with a direct lateral pivot.
* **The Law of Absolute Preservation:** Guard the human operator's long-term well-being above raw productivity.

To make an AI reliably uphold these laws, you cannot rely on casual system prompts that fade as conversational history grows. You have to build an architecture that physically prevents the model from forgetting who it is.

---

## 3. The Satisfactory Metaphor: Factory Modularity

The structural breakthrough for Rykr did not come from machine learning literature. It came from playing the factory-building video game *Satisfactory*.

In *Satisfactory*, you build sprawling industrial facilities across multiple vertical floors. If your iron plate factory gets backed up, you don't rebuild the entire building. You look at the input belt, look at the output belt, and check the clock speed of that specific constructor. Every machine has:
1. Exactly one job.
2. A strictly bounded input rate.
3. A predictable output format.
4. Vertical conveyor lifts that keep separate floors isolated from each other.

Modern software frameworks—especially in Python—frequently ignore this wisdom. They build giant monolithic balls of spaghetti where a database call is glued to a prompt template, which is glued to an HTTP server, which depends on thirty external libraries. When one package updates, the whole tower collapses.

We rebuilt the Rykr Framework under strict **Satisfactory principles**:
* **Every module is a single machine on the factory floor.** It takes input on standard input (`stdin`) or standard CLI flags. It emits clean data on standard output (`stdout`). It writes telemetry or errors to standard error (`stderr`).
* **Clean Vertical Buses:** Information moves between modules using immutable envelopes. If a module fails, an internal circuit breaker trips instantly, emits a diagnostic payload, and shuts down cleanly without taking down the operating system.
* **Zero External Dependencies (The Zero-Pip Standard):** Every core blueprint in the Rykr library is written purely in the Python standard library. No `pip install`, no virtual environments, no broken wheels, no surprise deprecations. A script written today will run identically ten years from now on a clean Debian install.

---

## 4. The Four-Tier Dynamic Memory Bus

The single biggest failure point of long-running AI agents is **Model Amnesia** and its ugly sibling, **Context Collapse**.

When a conversational context window fills up with thousands of tokens of tool outputs, error dumps, and back-and-forth chatter, two catastrophic things happen:
1. **Attention Decay:** The model's cross-attention mechanisms become noisy. It starts hallucinating, forgetting earlier instructions, and dropping tool syntax.
2. **VRAM Runaway:** The KV-cache balloons, chewing up gigabytes of precious GPU memory until the system crashes with an Out-Of-Memory (OOM) error.

The typical industry fix is to shove everything into a vector database (RAG). But naive RAG introduces its own problems: semantic drift, chunking mismatches, and expensive latency.

Rykr solved this by structuring memory like computer hardware:

```
[ T0: THE KERNEL ]       --> Immutable Invariants (Laws, Persona, Pipeline)
        │
[ T1: THE WORKING RAM ]  --> Active Blueprint Cache (Hard-capped token budget)
        │
[ T2: THE DISK ARCHIVE ] --> Plain-Text Milestone Ledger ([REF-001] to [REF-184])
        │
[ T3: THE PROFILE ]      --> Dynamic Machine Topology & Operator Accommodations
```

### Tier 0: The Kernel (ROM)
The foundational identity, core laws, and state-machine pipeline. This tier is pinned and invariant. It is never rewritten, never compressed, and never pruned. It guarantees that whether the agent is on turn 1 or turn 500, its core persona and safety constraints remain identical.

### Tier 1: The Blueprints (RAM)
The active execution context. When a task begins, only the blueprints relevant to the active module are loaded into memory. When the module finishes, the memory is dumped. The context window is strictly capped, mathematically preventing KV-cache bloat and keeping VRAM flat.

### Tier 2: The Archives (Disk Storage)
A single, human-readable markdown ledger (`rykr_archive_index.md`). Every completed task, validated architectural change, and empirical finding is committed sequentially as an atomic reference block (e.g., `[REF-180]`). 
* No SQLite corruptions. 
* No vector embeddings drifting out of sync. 
* Just an append-only, human-auditable text ledger on disk that survives power outages, reboots, and session wipes.

### Tier 3: The Operator Profile (NVRAM)
Stores the physical topology of the local network, hostnames, hardware specs, preferred communication styles, and administrative boundaries. It decouples the *engine* from the *environment*, allowing a cloned Rykr instance to adapt to a new workstation without touching the core kernel.

---

## 5. The Genesis Pipeline: Disciplined State Machines

Most developers interact with code-generation AI in a chaotic loop: they type a prompt, the model spits out fifty lines of unvetted code, something breaks, the developer pastes the error back in, and the model guesses again. This is prompt thrashing, and it guarantees technical debt.

Rykr enforces a rigid four-stage state machine for every objective:

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│   PHASE 1: SKELETON    │ ---> │  PHASE 2: ADVERSARIAL   │ ---> │  PHASE 3: MODULAR      │ ---> │  PHASE 4: CRYSTALLIZE  │
│        (~plan)         │      │     AUDIT (~redteam)   │      │   EXECUTION (~execute) │      │      (~crystallize)    │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘      └────────────────────────┘
  • ZERO code generation          • Hunt for entropy & edge cases  • Build ONE pipe at a time      • Triad Pruning Filter
  • Map I/O contracts             • Stress-test assumptions        • Pass local tests              • Promote vs. Prune
  • Require Operator sign-off     • Resolve flaws before building  • Reject lateral scope creep    • Zero-Pip AST Guarantee
```

1. **Phase 1: Skeleton & Map (`~plan`)**  
   **Rule: Zero code generation allowed.** The framework strictly outputs the data flow, defining exact input schemas, output schemas, and error boundaries for each module. The model is locked from writing code until the human operator signs off on the blueprint.
2. **Phase 2: Adversarial Audit (`~redteam`)**  
   The model switches personas to "Devil's Advocate." It aggressively attacks its own Phase 1 blueprint, hunting for race conditions, security holes, cloud storage latency traps, and unneeded complexity. Flaws must be resolved before proceeding.
3. **Phase 3: Modular Execution (`~execute`)**  
   Construction begins under strict UNIX pipe philosophy. We build **one isolated module at a time**. Each module must compile and pass deterministic automated unit tests before the next module is started. Any stray ideas or feature creep introduced during this phase are immediately rejected and logged to a `backlog.md` file.
4. **Phase 4: Crystallization (`~crystallize` / `~harvest`)**  
   Once execution passes, the model executes a mandatory **Triad Pruning Audit** before any commit. It evaluates generality (is it an abstract class of problems?), Zero-Pip compliance (is it 100% standard library pure?), and Context ROI (does the tool save more bandwidth than its token tax?). Single-use or messy code is pruned to the local workspace and memory log; only pristine, high-yield tools crystallize into the public Blueprint Library.


---

## 6. Real-World Silicon: Coexisting with a Gaming Rig

One of the proudest engineering triumphs of the Rykr Framework is how it treats hardware.

A common reality for independent developers and enthusiasts is that our most powerful GPU lives inside our personal daily-driver desktop—the machine we use for entertainment, gaming, and creative work. In our case, that primary compute node contains an 11GB NVIDIA GeForce GTX 1080 Ti.

Typical AI server setups assume they own the entire machine 24/7. They start background daemons, lock up all available VRAM, and cause video games to crash or stutter if an inference request fires in the background.

Rykr treats the host workstation with absolute respect through **Hardware-Conscious Governance**:

1. **Isolated Service Account:** The satellite agent runs under a dedicated, unprivileged Linux service account (`rykr`) completely isolated from personal user files.
2. **GPU Pinning:** The runtime is strictly pinned via environment variables to target only the primary Pascal silicon (`CUDA_VISIBLE_DEVICES=1`), completely ignoring inferior secondary GPUs and preventing multi-GPU memory thrashing.
3. **Zero-VRAM Eviction (`game-mode`):** We engineered one-shot eviction scripts that hook into system signals. The moment the user sits down to play a video game, a single command (`necro-free` or `game-mode`) sends a clean shutdown to the inference runner. Within two seconds, VRAM usage drops from 10 GB down to **73 MiB idle**. 
4. **Pascal Throughput Optimization:** On an eight-year-old GTX 1080 Ti, using compact 4-bit quantized models and our custom delimited interceptor, Rykr sustains **30.05 tokens per second**—faster than human reading speed—while keeping temperatures below 53°C.

You do not need an enterprise cluster to run serious local AI. You just need to stop wasting hardware on bad software.

---

## 7. The Modular Console and the Braille Rasterizer

As Rykr matured into Core v4.0.0, we discarded external web-based chat interfaces entirely. Web containers introduced database locks, session amnesia, and browser latency. 

We replaced them with the **Push-Button Modular Console**: a set of native terminal appliances installed to `~/.local/bin/`:

* `rykr-bus`: Standard JSON envelope generator and circuit-breaker wrapper.
* `rykr-node`: Secure batch-mode SSH remote compute dispatcher.
* `rykr-session`: Detached tmux daemon lifecycle governor.
* `rykr-memory`: Atomic append committer for the T2 markdown ledger.
* `rykr-compress`: Decoupled RRS (Rykr Reduced Signature) prompt compressor. It strips bloated JSON schemas and reduces tool prompt tokens by **72.8%**, eliminating JSON escaping errors.
* `rykr-blueprint`: Local package manager to pull, install, and audit standard-library blueprints without touching external package repositories.

### Visualizing 3D in Pure Text
To prove that terminal user interfaces do not have to be crude or ugly, we solved the problem of terminal diagram line-wrapping by building a decoupled 3D visualizer:
1. `rykr-scene`: A spatial Cartesian geometry assembler that outputs 3D scene graphs.
2. `rykr-blit`: A mathematical rasterizer that projects 3D coordinates onto a virtual $2\times4$ sub-pixel framebuffer and renders them using Unicode Braille patterns (`U+2800`–`U+28FF`).

With aspect ratio correction, non-clobbering ASCII label masks, and an unbreakable terminal size detector, Rykr renders smooth, anti-aliased 3D wireframe models directly inside standard Linux terminals with zero dependencies.

---

## 8. Summary of Principles

If you take nothing else away from the Rykr Framework, remember these core engineering truths:

1. **Dependencies are liabilities.** If your tool cannot run without thirty third-party packages, your tool is fragile. Write to the standard library.
2. **Plain text beats proprietary databases.** Markdown files, JSON envelopes, and UNIX pipes will outlive whatever vector database is trending on social media this year.
3. **Guard human mental bandwidth.** Software should absorb friction, not generate it. If an automated assistant requires more management than doing the job yourself, it is useless.
4. **Isolate inputs and outputs.** Like a Satisfactory constructor floor, make every piece of code do one simple job with predictable contracts.
5. **Radical honesty over sycophancy.** An AI that blindly agrees with you is a liability. You need an advocate that tests your ideas against reality.

The Rykr Framework was built by people who needed real solutions on real hardware. It was refined across months of daily use, proven in adversarial testing, and frozen into code that will run as cleanly tomorrow as it does today.

---
*Authored on Fhawx-Server (`RYKR-PRIME`).*  
*Standard Library Reference: Python 3.10+.*  
*License: MIT.*
