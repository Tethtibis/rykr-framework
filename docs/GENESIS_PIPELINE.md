# The Genesis Pipeline: Developer Guide

The Genesis Pipeline is a mandatory 3-stage state machine that governs all software construction inside the Rykr Framework. It was engineered to mathematically prevent "prompt thrashing"—the cycle where an AI generates unvetted code, encounters runtime errors, pastes patches on top of patches, and collapses the active context window.

---

## The Three Phases

### Phase 1: Skeleton & Map (`~plan`)
* **Objective:** Establish the macro blueprint before writing a single line of logic.
* **The Absolute Rule:** ZERO code generation is allowed.
* **Required Output:**
  1. Module names and single-responsibility descriptions.
  2. Exact input formats (CLI flags, stdin schemas, environment variables).
  3. Exact output formats (JSON contracts, stdout streams, stderr telemetry).
  4. Failure modes and circuit breaker behaviors.
* **State Lock:** The AI is locked from writing implementation code until the human operator validates the skeleton.

### Phase 2: Adversarial Audit (`~redteam`)
* **Objective:** Stress-test the theoretical framework before expending implementation bandwidth.
* **Persona:** The AI adopts an adversarial "Devil's Advocate" stance against its own Phase 1 blueprint.
* **Audit Checklist:**
  * Hunt for hidden state or tight coupling.
  * Check for external dependency creep (violating the Zero-Pip standard).
  * Hunt for hardcoded user paths or environment assumptions.
  * Evaluate storage latency traps (e.g. running across network FUSE mounts).
  * Check for edge-case failure loops and memory leaks.
* **State Lock:** All identified flaws must have concrete, agreed-upon countermeasures before entering Phase 3.

### Phase 3: Modular Execution (`~execute`)
* **Objective:** Build the system using strict UNIX pipe philosophy (`|`).
* **The Rule of Single-Threaded Construction:** Build ONE isolated module at a time.
* **Failsafes:**
  * **Anti-Creep Failsafe:** All lateral ideas or "nice-to-have" features introduced during construction are rejected and appended to `backlog.md`.
  * **Local Test Mandate:** The active module must compile, run, and pass automated unit tests before the next module begins.
  * **Cognitive Failsafe:** If unexpected errors clutter the context buffer, trigger a `[MEM_COMMIT]` to clear conversational debris and reload only the pristine module blueprint.
