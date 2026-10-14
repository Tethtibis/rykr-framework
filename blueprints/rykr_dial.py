#!/usr/bin/env python3
"""
==============================================================================
RYKR-DIAL: TERMINAL TUI SPEED-DIAL & SSH DISPATCHER
==============================================================================
Interactive retro phosphor curses speed-dialer for multi-node SSH infrastructure.
Decouples node configurations into a portable JSON ledger. Establishes single-pane
connections in-place and returns cleanly on disconnect.

Guarantees:
  - 100% Python Standard Library (Zero-Pip).
  - Portability: Dynamic path resolution via Path.home().
  - Zero tmux nesting or quad-pane complexity.
==============================================================================
"""

import os
import sys
import json
import curses
import argparse
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

VERSION = "1.0.0"

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "rykr" / "hosts.json"
FALLBACK_CONFIG_PATH = Path.home() / ".config" / "ssh_station" / "hosts.json"

DEFAULT_SCHEMA = {
    "version": VERSION,
    "hosts": [
        {
            "name": "Localhost",
            "host": "127.0.0.1",
            "user": "rykr",
            "port": 22,
            "auth_type": "key",
            "key_path": "~/.ssh/id_ed25519",
            "password": ""
        }
    ]
}


def resolve_config_file(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        return Path(custom_path).expanduser().resolve()
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    if FALLBACK_CONFIG_PATH.exists():
        return FALLBACK_CONFIG_PATH
    return DEFAULT_CONFIG_PATH


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        save_config(config_path, DEFAULT_SCHEMA)
        return DEFAULT_SCHEMA
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "hosts" not in data or not isinstance(data["hosts"], list):
                data["hosts"] = []
            return data
    except Exception:
        return DEFAULT_SCHEMA


def save_config(config_path: Path, data: Dict[str, Any]):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass


def build_ssh_command(target: Dict[str, Any]) -> str:
    user = target.get("user", "").strip()
    host = target.get("host", "").strip()
    port = target.get("port", 22)
    auth_type = target.get("auth_type", "key")
    key_path = str(Path(target.get("key_path", "")).expanduser()) if target.get("key_path") else ""
    password = target.get("password", "")

    ssh_args = f"-p {port} -o StrictHostKeyChecking=accept-new "
    if auth_type == "key" and key_path and os.path.exists(key_path):
        ssh_args += f"-i '{key_path}' "

    dest = f"{user}@{host}" if user else host
    base_cmd = f"ssh {ssh_args}{dest}"

    if auth_type == "password" and password:
        return f"sshpass -p '{password}' {base_cmd}"
    return base_cmd


def prompt_input(stdscr, y: int, x: int, prompt_text: str, default_val: str = "") -> str:
    stdscr.addstr(y, x, prompt_text + ": ", curses.color_pair(2) | curses.A_BOLD)
    input_win = curses.newwin(1, 40, y, x + len(prompt_text) + 2)
    input_win.bkgd(" ", curses.color_pair(3))
    input_win.addstr(0, 0, default_val[:38])
    input_win.refresh()
    curses.echo()
    curses.curs_set(1)
    try:
        val = input_win.getstr(0, 0, 38).decode("utf-8").strip()
    except Exception:
        val = default_val
    curses.noecho()
    curses.curs_set(0)
    return val if val else default_val


def edit_host_dialog(stdscr, host_dict: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    h = dict(host_dict) if host_dict else {
        "name": "New Server",
        "host": "192.168.0.",
        "user": "user",
        "port": 22,
        "auth_type": "key",
        "key_path": "~/.ssh/id_ed25519",
        "password": ""
    }

    max_y, max_x = stdscr.getmaxyx()
    win_h, win_w = 12, min(65, max_x - 4)
    start_y, start_x = max(1, (max_y - win_h) // 2), max(1, (max_x - win_w) // 2)

    dlg = curses.newwin(win_h, win_w, start_y, start_x)
    dlg.box()
    dlg.bkgd(" ", curses.color_pair(1))
    title = " [ EDIT SERVER CONFIG ] " if host_dict else " [ ADD NEW SERVER ] "
    dlg.addstr(0, 2, title, curses.color_pair(2) | curses.A_BOLD)
    dlg.refresh()

    h["name"] = prompt_input(dlg, 2, 2, "Label Name ", h.get("name", ""))
    h["host"] = prompt_input(dlg, 3, 2, "Host / IP  ", h.get("host", ""))
    h["user"] = prompt_input(dlg, 4, 2, "User Name  ", h.get("user", ""))
    port_str = prompt_input(dlg, 5, 2, "Port Number", str(h.get("port", 22)))
    try:
        h["port"] = int(port_str)
    except ValueError:
        h["port"] = 22

    auth_choice = prompt_input(dlg, 6, 2, "Auth (key/pwd)", h.get("auth_type", "key"))
    h["auth_type"] = "password" if auth_choice.lower().startswith("p") else "key"

    if h["auth_type"] == "key":
        h["key_path"] = prompt_input(dlg, 7, 2, "Key File   ", h.get("key_path", "~/.ssh/id_ed25519"))
    else:
        h["password"] = prompt_input(dlg, 7, 2, "Password   ", h.get("password", ""))

    dlg.addstr(9, 2, "[S] Save Entry   [ESC] Discard", curses.color_pair(2) | curses.A_BOLD)
    dlg.refresh()
    ch = dlg.getch()
    if ch in [ord('s'), ord('S'), 10, 13]:
        return h
    return None


def curses_speed_dial(stdscr, config_path: Path):
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(4, curses.COLOR_RED, -1)

    selected_idx = 0

    while True:
        cfg = load_config(config_path)
        hosts = cfg.get("hosts", [])
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        header_text = " ⚡ RYKR-DIAL // INFRASTRUCTURE SPEED-DIAL "
        stdscr.addstr(0, max(0, (max_x - len(header_text)) // 2), header_text, curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(1, 1, "─" * (max_x - 2), curses.color_pair(1))

        sub_text = "[Enter] Connect   [a] Add   [e] Edit   [d] Delete   [q] Exit"
        stdscr.addstr(2, max(1, (max_x - len(sub_text)) // 2), sub_text, curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(3, 1, "─" * (max_x - 2), curses.color_pair(1))

        if not hosts:
            stdscr.addstr(6, 4, "[-] No servers configured. Press [a] to add a connection.", curses.color_pair(4))
        else:
            list_start_y = 5
            max_visible = max(1, max_y - list_start_y - 2)
            if selected_idx >= len(hosts):
                selected_idx = max(0, len(hosts) - 1)

            for i, target in enumerate(hosts[:max_visible]):
                y = list_start_y + i
                is_selected = (i == selected_idx)
                prefix = " ► " if is_selected else "   "
                name = target.get("name", "Unnamed")[:24].ljust(25)
                endpoint = f"{target.get('user', '')}@{target.get('host', '')}:{target.get('port', 22)}"[:28].ljust(29)
                auth = f"[{target.get('auth_type', 'key').upper()}]"

                line_str = f"{prefix}{name} │ {endpoint} │ {auth}"
                line_str = line_str[:max_x - 2]
                attr = curses.color_pair(3) | curses.A_BOLD if is_selected else curses.color_pair(1)
                stdscr.addstr(y, 1, line_str, attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key in [curses.KEY_UP, ord('k')]:
            selected_idx = max(0, selected_idx - 1)
        elif key in [curses.KEY_DOWN, ord('j')]:
            if hosts:
                selected_idx = min(len(hosts) - 1, selected_idx + 1)
        elif key in [10, 13]:
            if hosts and selected_idx < len(hosts):
                target = hosts[selected_idx]
                cmd = build_ssh_command(target)
                curses.endwin()
                os.system("clear")
                print(f"\033[1;38;2;204;85;0m[⚡ CONNECTING TO {target.get('name')}...]\033[0m")
                print(f"\033[90m$ {cmd}\033[0m\n")
                subprocess.run(cmd, shell=True)
                print("\n\033[1;38;2;204;85;0m[Session Closed. Returning to Speed-Dial...]\033[0m")
                time.sleep(1)
                stdscr = curses.initscr()
                curses.cbreak()
                curses.noecho()
                stdscr.keypad(True)
        elif key in [ord('a'), ord('A')]:
            new_h = edit_host_dialog(stdscr)
            if new_h:
                hosts.append(new_h)
                save_config(config_path, cfg)
                selected_idx = len(hosts) - 1
        elif key in [ord('e'), ord('E')]:
            if hosts and selected_idx < len(hosts):
                edited = edit_host_dialog(stdscr, hosts[selected_idx])
                if edited:
                    hosts[selected_idx] = edited
                    save_config(config_path, cfg)
        elif key in [ord('d'), ord('D')]:
            if hosts and selected_idx < len(hosts):
                del hosts[selected_idx]
                save_config(config_path, cfg)
                selected_idx = max(0, min(selected_idx, len(hosts) - 1))


def main():
    parser = argparse.ArgumentParser(description="Rykr Terminal TUI Speed-Dial & SSH Dispatcher")
    parser.add_argument("--config", "-c", help="Path to custom JSON host file")
    parser.add_argument("--list", "-l", action="store_true", help="Print configured hosts as JSON and exit")
    args = parser.parse_args()

    cfg_path = resolve_config_file(args.config)

    if args.list:
        cfg = load_config(cfg_path)
        print(json.dumps(cfg, indent=2))
        sys.exit(0)

    curses.wrapper(lambda scr: curses_speed_dial(scr, cfg_path))


if __name__ == "__main__":
    main()
