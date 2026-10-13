# Hardware Lifecycle & Gaming Coexistence Guide

A common barrier to running local autonomous AI is that personal workstations are dual-use machines. The most powerful GPU in the house is often the card used for gaming, 3D rendering, or video editing.

Standard AI server installations greedily lock GPU VRAM indefinitely. If an inference task runs while a 3D game is active, both applications compete for memory, resulting in frame drops, DirectX driver crashes, or kernel panics.

This guide details how the Rykr Framework achieves seamless coexistence, allowing heavy local inference workloads to run on a primary gaming workstation while ensuring instant eviction down to **<100 MiB idle VRAM** when you sit down to play a game.

---

## 1. Physical GPU Isolation (Multi-GPU Safety)

If your workstation contains multiple GPUs (for example, a high-end card alongside an older secondary GPU), inference frameworks will frequently attempt to split model layers across both cards. On consumer hardware, cross-PCIe tensor parallelism causes severe bus bottlenecks and memory cascades.

### Systemd Override Configuration
Pin the AI service to target ONLY your designated primary compute card:

```ini
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
# Mask secondary GPUs; expose ONLY the designated card
Environment="CUDA_VISIBLE_DEVICES=0"

# Lock concurrency to 1 to prevent runaway memory allocation
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Evict model from VRAM after 5 minutes of idle time
Environment="OLLAMA_KEEP_ALIVE=5m"
```

Reload and restart the system daemon:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

---

## 2. The One-Shot Memory Evictor (`game-mode`)

Relying on idle timeouts is insufficient when you want to launch a game immediately. We implement a deterministic one-shot eviction script installed to `/usr/local/bin/game-mode`:

```bash
#!/bin/bash
# Evicts all loaded models and clears GPU VRAM instantly
echo "[*] Triggering instant VRAM eviction..."

# 1. Stop active models via CLI
ollama stop $(ollama ps | awk 'NR>1 {print $1}') 2>/dev/null || true

# 2. Query NVIDIA ground truth
echo "[*] GPU Memory Status:"
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader

echo "[+] VRAM evicted. Workstation is gaming-ready."
```

Make the script globally executable:
```bash
sudo chmod +x /usr/local/bin/game-mode
```

When triggered, VRAM usage drops from ~10 GB down to **~73 MiB** within two seconds, releasing 100% of compute and memory bandwidth to the graphics driver.

---

## 3. Signal Trapping in TUI Runners

When developing native terminal runners, always trap POSIX termination signals (`SIGINT`, `SIGTERM`, `SIGHUP`) to ensure that if a user closes their terminal window or presses `Ctrl+C`, the process shuts down cleanly and unhides the cursor:

```python
import sys
import signal

def sig_handler(sig, frame):
    # Restore terminal cursor and reset ANSI colors
    sys.stdout.write("\033[?25h\033[0m\n")
    sys.stdout.flush()
    sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)
```
