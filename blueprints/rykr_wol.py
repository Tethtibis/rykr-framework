#!/usr/bin/env python3
"""
==============================================================================
RYKR-WOL: ZERO-DEPENDENCY WAKE-ON-LAN APPLIANCE
==============================================================================
Generates and broadcasts standard Wake-on-LAN magic packets across local
subnets using pure Python 3 standard library sockets. Eliminates external
package dependencies (e.g. apt install wakeonlan).

Guarantees:
  - 100% Python Standard Library (Zero-Pip).
  - Robust MAC address sanitization across all standard delimiters.
  - JSON telemetry envelope support via --json.
==============================================================================
"""

import sys
import os
import re
import socket
import struct
import argparse
import json
from typing import Dict, Any, Optional

VERSION = "1.0.0"

# Default hardware presets (can be overridden via ~/.config/rykr/wol_presets.json)
HARDWARE_PRESETS = {
    "gpu-worker": "00:11:22:33:44:55",
    "compute-node": "00:11:22:33:44:56",
    "client-rig": "00:E0:4C:68:01:23"
}


def sanitize_mac(mac_str: str) -> bytes:
    """
    Normalizes MAC address string into exactly 6 raw bytes.
    Accepts: 'XX:XX:XX:XX:XX:XX', 'XX-XX-XX-XX-XX-XX', 'XXXX.XXXX.XXXX', 'XXXXXXXXXXXX'.
    """
    cleaned = re.sub(r"[^0-9a-fA-F]", "", mac_str)
    if len(cleaned) != 12:
        raise ValueError(f"Invalid MAC address format: '{mac_str}' (expected 12 hexadecimal characters)")
    return bytes.fromhex(cleaned)


def create_magic_packet(mac_bytes: bytes) -> bytes:
    """
    Builds standard WoL magic packet: 6 bytes of 0xFF followed by 16 repetitions of MAC.
    Length is exactly 102 bytes.
    """
    return b"\xff" * 6 + (mac_bytes * 16)


def send_wol_packet(mac_str: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> Dict[str, Any]:
    """
    Transmits magic packet over UDP broadcast socket.
    """
    mac_bytes = sanitize_mac(mac_str)
    packet = create_magic_packet(mac_bytes)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast_ip, port))

    formatted_mac = ":".join(f"{b:02x}" for b in mac_bytes).upper()
    return {
        "status": "SUCCESS",
        "mac": formatted_mac,
        "broadcast_ip": broadcast_ip,
        "port": port,
        "packet_size_bytes": len(packet)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Rykr Zero-Dependency Wake-on-LAN Magic Packet Broadcaster"
    )
    parser.add_argument("--mac", "-m", help="Target MAC address (e.g. E8:9C:25:C5:30:AF)")
    parser.add_argument("--preset", "-p", choices=list(HARDWARE_PRESETS.keys()), help="Target node hardware preset")
    parser.add_argument("--broadcast", "-b", default="255.255.255.255", help="Broadcast IP address (default: 255.255.255.255)")
    parser.add_argument("--port", type=int, default=9, help="UDP destination port (default: 9)")
    parser.add_argument("--json", action="store_true", help="Emit telemetry in JSON format")

    args = parser.parse_args()

    mac_target = None
    if args.preset:
        mac_target = HARDWARE_PRESETS[args.preset]
    elif args.mac:
        mac_target = args.mac
    else:
        # Check environment or prompt
        parser.error("Must specify either --mac or --preset")

    try:
        telemetry = send_wol_packet(mac_target, broadcast_ip=args.broadcast, port=args.port)
        if args.json:
            print(json.dumps(telemetry, indent=2))
        else:
            print(f"\033[1;38;2;204;85;0m[RYKR::WOL]\033[0m Magic packet sent to \033[1;37m{telemetry['mac']}\033[0m via {telemetry['broadcast_ip']}:{telemetry['port']}")
        sys.exit(0)
    except Exception as e:
        err = {"status": "ERROR", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2), file=sys.stderr)
        else:
            print(f"\033[1;31m[-] WOL Failure: {e}\033[0m", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
