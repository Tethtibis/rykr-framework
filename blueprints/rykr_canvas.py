#!/usr/bin/env python3
"""
==============================================================================
RYKR-CANVAS: PUSH-OPEN HTML5 + MATHEMATICAL SVG VISUAL & CLIPBOARD APPLIANCE
==============================================================================
Zero-Pip Python 3 Standard Library Core.
Generates resolution-independent Burnt Orange (#CC5500) HTML5 + Vector SVG
canvases with 1-click clipboard copy cards (supporting file:// fallback) and
automatically pushes them open on the Operator's active SSH client display.
==============================================================================
"""

import argparse
import html
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone

CANVAS_CSS = """
:root {
  --bg: #050505;
  --panel: #0d0d0d;
  --panel-alt: #141414;
  --orange: #CC5500;
  --amber: #FF8C00;
  --text: #E8E2D5;
  --muted: #8C8275;
  --green: #2ECC71;
  --border: #2A1808;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 28px 36px 60px 36px;
  background: var(--bg);
  color: var(--text);
  font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
  line-height: 1.55;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid var(--orange);
  padding-bottom: 14px;
  margin-bottom: 24px;
}
.title-block h1 {
  margin: 0;
  font-size: 1.45rem;
  color: var(--orange);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.title-block .subtitle {
  color: var(--muted);
  font-size: 0.85rem;
  margin-top: 4px;
}
.badge {
  background: #1A0D00;
  border: 1px solid var(--orange);
  color: var(--amber);
  padding: 6px 12px;
  font-size: 0.78rem;
  border-radius: 4px;
  letter-spacing: 0.05em;
}
.svg-container {
  background: var(--panel);
  border: 1px solid var(--orange);
  border-radius: 6px;
  padding: 20px;
  margin-bottom: 26px;
  overflow-x: auto;
  box-shadow: 0 0 24px rgba(204, 85, 0, 0.12);
}
.svg-container svg {
  width: 100%;
  height: auto;
  max-height: 620px;
  display: block;
  margin: 0 auto;
}
.cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-left: 4px solid var(--orange);
  border-radius: 6px;
  overflow: hidden;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--panel-alt);
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}
.card-title {
  color: var(--amber);
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.03em;
}
.copy-btn {
  background: var(--orange);
  color: #000000;
  border: none;
  padding: 6px 14px;
  font-family: inherit;
  font-weight: 700;
  font-size: 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  letter-spacing: 0.04em;
  transition: all 0.15s ease;
}
.copy-btn:hover {
  background: var(--amber);
}
.copy-btn.copied {
  background: var(--green);
  color: #000000;
}
.card-note {
  padding: 10px 16px 0 16px;
  color: var(--muted);
  font-size: 0.85rem;
}
.card-pre {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  font-size: 0.88rem;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}
"""

CANVAS_JS = """
function copyBlock(btn, id) {
  const el = document.getElementById(id);
  if (!el) return;
  const text = el.textContent;
  const markCopied = () => {
    const orig = btn.getAttribute('data-label') || 'COPY';
    btn.textContent = '✓ COPIED TO CLIPBOARD';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = orig;
      btn.classList.remove('copied');
    }, 1800);
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(markCopied).catch(() => fallbackCopy(text, markCopied));
  } else {
    fallbackCopy(text, markCopied);
  }
}
function fallbackCopy(text, callback) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
    callback();
  } catch (e) {}
  document.body.removeChild(ta);
}
"""


def detect_active_ssh_client():
    """Detects the most recent LAN/WireGuard SSH client IP from `who`."""
    try:
        res = subprocess.run(["who"], capture_output=True, text=True, timeout=3)
        candidates = []
        for line in res.stdout.splitlines():
            m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
            if m:
                ip = m.group(1)
                if ip.startswith("192.168.") or ip.startswith("10."):
                    candidates.append(ip)
        if candidates:
            return candidates[-1]
    except Exception:
        pass
    return None


def build_html(title, subtitle, svg_content, cards):
    ts = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    svg_section = ""
    if svg_content:
        svg_section = f'<div class="svg-container">\n{svg_content}\n</div>'

    cards_html = []
    for idx, c in enumerate(cards):
        cid = f"copy_target_{idx}"
        ctitle = html.escape(c.get("title", f"Block {idx + 1}"))
        cnote = html.escape(c.get("note", ""))
        ccontent = html.escape(c.get("content", ""))
        btn_label = html.escape(c.get("button", "COPY BLOCK"))
        note_div = f'<div class="card-note">{cnote}</div>' if cnote else ""
        cards_html.append(f"""
        <div class="card">
          <div class="card-header">
            <span class="card-title">{ctitle}</span>
            <button class="copy-btn" data-label="{btn_label}" onclick="copyBlock(this, '{cid}')">{btn_label}</button>
          </div>
          {note_div}
          <pre class="card-pre" id="{cid}">{ccontent}</pre>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CANVAS_CSS}</style>
</head>
<body>
  <div class="header">
    <div class="title-block">
      <h1>{html.escape(title)}</h1>
      <div class="subtitle">{html.escape(subtitle)}</div>
    </div>
    <div class="badge">RYKR-CANVAS // {ts}</div>
  </div>
  {svg_section}
  <div class="cards-grid">
    {''.join(cards_html)}
  </div>
<script>{CANVAS_JS}</script>
</body>
</html>
"""


def push_open_canvas(local_path, target_host=None):
    """Pushes the HTML canvas to the active client desktop and launches it on DISPLAY=:0."""
    host = target_host or detect_active_ssh_client()
    fname = os.path.basename(local_path)
    telemetry = {
        "local_path": os.path.abspath(local_path),
        "target_host": host or "local",
        "launched": False,
    }

    if host and host not in ("local", "127.0.0.1", "localhost"):
        remote_path = f"~/Desktop/{fname}"
        scp_res = subprocess.run(
            ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", local_path, f"{host}:{remote_path}"],
            capture_output=True,
            text=True,
        )
        if scp_res.returncode == 0:
            telemetry["remote_path"] = remote_path
            open_cmd = (
                f"export DISPLAY=:0; "
                f"nohup xdg-open ~/Desktop/{fname} >/dev/null 2>&1 & "
                f"sleep 0.2"
            )
            ssh_res = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", host, open_cmd],
                capture_output=True,
                text=True,
            )
            telemetry["launched"] = (ssh_res.returncode == 0)
            return telemetry

    # Local fallback
    try:
        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")
        subprocess.Popen(
            ["xdg-open", os.path.abspath(local_path)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        telemetry["launched"] = True
    except Exception:
        pass
    return telemetry


def main():
    if "--schema" in sys.argv:
        schema = {
            "module": "canvas",
            "description": "Generate Burnt Orange HTML5 + Mathematical SVG visual & copy-paste canvases and push open on active client display",
            "actions": {
                "render": "Build an HTML5/SVG canvas from JSON spec and optionally push-open on active client",
                "open": "Push an existing HTML/SVG file to the active client display and open it",
            },
        }
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Rykr Push-Open HTML5/SVG Canvas Appliance")
    sub = parser.add_subparsers(dest="action")

    p_render = sub.add_parser("render")
    p_render.add_argument("--spec", required=True, help="Path to JSON specification file")
    p_render.add_argument("--out", required=True, help="Output HTML file path")
    p_render.add_argument("--host", default=None, help="Override target client IP/hostname")
    p_render.add_argument("--no-open", action="store_true", help="Generate file without launching browser")
    p_render.add_argument("--json", action="store_true")

    p_open = sub.add_parser("open")
    p_open.add_argument("--file", required=True, help="Existing HTML/SVG file to push open")
    p_open.add_argument("--host", default=None, help="Override target client IP/hostname")
    p_open.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.action == "render":
        with open(args.spec, "r", encoding="utf-8") as f:
            spec = json.load(f)
        html_doc = build_html(
            title=spec.get("title", "RYKR VISUAL CANVAS"),
            subtitle=spec.get("subtitle", ""),
            svg_content=spec.get("svg", ""),
            cards=spec.get("cards", []),
        )
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(html_doc)
        tel = {"local_path": os.path.abspath(args.out), "launched": False}
        if not args.no_open:
            tel = push_open_canvas(args.out, args.host)
        if args.json:
            sys.stdout.write(json.dumps({"status": "SUCCESS", "telemetry": tel}, indent=2) + "\n")
        else:
            sys.stdout.write(
                f"\033[38;2;204;85;0m[RYKR-CANVAS // RENDER]\033[0m Saved to {tel['local_path']} "
                f"(Target: {tel.get('target_host', 'local')}, Launched: {tel['launched']})\n"
            )
    elif args.action == "open":
        tel = push_open_canvas(args.file, args.host)
        if args.json:
            sys.stdout.write(json.dumps({"status": "SUCCESS", "telemetry": tel}, indent=2) + "\n")
        else:
            sys.stdout.write(
                f"\033[38;2;204;85;0m[RYKR-CANVAS // OPEN]\033[0m Pushed {args.file} -> "
                f"{tel.get('target_host', 'local')} (Launched: {tel['launched']})\n"
            )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
