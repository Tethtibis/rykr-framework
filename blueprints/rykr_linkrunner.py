#!/usr/bin/env python3
"""
==============================================================================
RYKR-LINKRUNNER: PHYSICAL SWITCHPORT & LINK DIAGNOSTIC APPLIANCE
==============================================================================
Sniffs physical Ethernet switchport link states and LLDP/CDP neighbor
advertisements. Extracts remote switch chassis name, model, port ID,
VLAN memberships (PVID / Voice), management IPs, and local carrier states.

Guarantees:
  - 100% Python Standard Library (Zero-Pip).
  - Portability: Reads sysfs directly and parses LLDP/CDP JSON payloads.
  - Telemetry: Supports clean TUI output and structured --json envelope.
==============================================================================
"""

import os
import sys
import json
import time
import argparse
import subprocess
from typing import Dict, Any, List, Optional

VERSION = "1.0.0"

# ANSI Burnt Orange Palette
ORANGE = "\033[38;2;204;85;0m"
AMBER = "\033[1;38;2;255;140;0m"
GREEN = "\033[1;32m"
RED = "\033[1;31m"
CYAN = "\033[1;36m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_ethernet_interfaces() -> List[str]:
    """Scans sysfs for physical Ethernet interfaces, filtering out wireless/virtual."""
    ifaces = []
    net_path = "/sys/class/net"
    if not os.path.exists(net_path):
        return ifaces

    for name in sorted(os.listdir(net_path)):
        if name.startswith(("en", "eth", "eno", "ens", "enp")):
            dev_dir = os.path.join(net_path, name)
            if not os.path.exists(os.path.join(dev_dir, "wireless")) and not os.path.exists(os.path.join(dev_dir, "phy80211")):
                ifaces.append(name)
    return ifaces


def get_carrier_status(iface: str) -> bool:
    try:
        with open(f"/sys/class/net/{iface}/carrier", "r", encoding="utf-8") as f:
            return f.read().strip() == "1"
    except OSError:
        return False


def get_mac_address(iface: str) -> str:
    try:
        with open(f"/sys/class/net/{iface}/address", "r", encoding="utf-8") as f:
            return f.read().strip().upper()
    except OSError:
        return "UNKNOWN"


def get_interface_ip(iface: str) -> str:
    try:
        res = subprocess.run(["ip", "-4", "addr", "show", iface], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1]
    except Exception:
        pass
    return "None"


def extract_vlans(interface_data: Dict[str, Any]) -> List[str]:
    vlans = []
    vlan_data = interface_data.get("vlan", [])
    if isinstance(vlan_data, dict):
        vlan_data = [vlan_data]
    if isinstance(vlan_data, list):
        for v in vlan_data:
            if isinstance(v, dict):
                v_id = v.get("vlan-id") or v.get("id")
                v_name = v.get("name", "")
                is_pvid = v.get("pvid", "")
                suffix = " (PVID)" if is_pvid in [True, "yes", "true"] else ""
                if v_id is not None:
                    name_str = f" - {v_name}" if v_name else ""
                    vlans.append(f"VLAN {v_id}{name_str}{suffix}")

    for med_key in ["lldp-med", "med"]:
        med_data = interface_data.get(med_key, {})
        if isinstance(med_data, dict):
            for policy_key in ["policy", "med-policy", "policies"]:
                policies = med_data.get(policy_key, [])
                if isinstance(policies, dict):
                    policies = [policies]
                if isinstance(policies, list):
                    for p in policies:
                        if isinstance(p, dict):
                            app_type = str(p.get("apptype") or p.get("application") or p.get("type") or "").lower()
                            if app_type == "voice":
                                vlan_info = p.get("vlan", {})
                                v_id = vlan_info.get("vid") or vlan_info.get("vlan-id") if isinstance(vlan_info, dict) else vlan_info
                                if v_id is not None:
                                    vlans.append(f"VLAN {v_id} (Voice)")
    return vlans


def extract_mgmt_ips(chassis_data: Dict[str, Any]) -> List[str]:
    ips = []
    for key in ["management-address", "mgmt-ip"]:
        addr_data = chassis_data.get(key, [])
        if isinstance(addr_data, dict):
            addr_data = [addr_data]
        if isinstance(addr_data, list):
            for entry in addr_data:
                if isinstance(entry, dict) and "value" in entry:
                    ips.append(entry["value"])
                elif isinstance(entry, str):
                    ips.append(entry)
    return sorted(list(set(ips)))


def query_lldp_neighbors(timeout_seconds: int = 5) -> Dict[str, Any]:
    """Queries lldpctl for active neighbors."""
    cmd = ["lldpctl", "-f", "json"]
    if os.geteuid() != 0 and subprocess.run(["which", "sudo"], capture_output=True).returncode == 0:
        cmd = ["sudo", "-n", "lldpctl", "-f", "json"]

    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                parsed = json.loads(res.stdout)
                return parsed.get("lldp", {}).get("interface", {})
        except Exception:
            pass
        time.sleep(1)
    return {}


def analyze_link() -> Dict[str, Any]:
    report = {
        "version": VERSION,
        "interfaces": {}
    }

    ifaces = get_ethernet_interfaces()
    lldp_interfaces = query_lldp_neighbors(timeout_seconds=3)

    for iface in ifaces:
        carrier = get_carrier_status(iface)
        mac = get_mac_address(iface)
        ip = get_interface_ip(iface)

        iface_report: Dict[str, Any] = {
            "carrier_detected": carrier,
            "mac_address": mac,
            "ip_address": ip,
            "switch_neighbor": None
        }

        # Check for neighbor data
        neighbor = None
        if isinstance(lldp_interfaces, list):
            for obj in lldp_interfaces:
                if iface in obj:
                    neighbor = obj[iface]
                    break
        elif isinstance(lldp_interfaces, dict):
            neighbor = lldp_interfaces.get(iface)

        if neighbor and "chassis" in neighbor:
            chassis = neighbor["chassis"]
            port = neighbor.get("port", {})

            switch_name = chassis.get("name", "Unknown")
            if isinstance(switch_name, dict):
                switch_name = switch_name.get("value", "Unknown")

            port_id = port.get("id", {})
            port_val = port_id.get("value") if isinstance(port_id, dict) else port_id

            iface_report["switch_neighbor"] = {
                "switch_name": switch_name,
                "switch_port": port_val,
                "port_description": port.get("descr", ""),
                "vlans": extract_vlans(neighbor),
                "management_ips": extract_mgmt_ips(chassis),
                "chassis_description": chassis.get("descr", "").replace("\n", " ").strip()
            }

        report["interfaces"][iface] = iface_report
    return report


def main():
    parser = argparse.ArgumentParser(description="Rykr LinkRunner: Physical Switchport Link & LLDP/CDP Inspector")
    parser.add_argument("--json", action="store_true", help="Emit raw telemetry as JSON")
    args = parser.parse_args()

    results = analyze_link()

    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0)

    print(f"\n{AMBER}⚡ RYKR-LINKRUNNER // PHYSICAL SWITCHPORT INSPECTOR{RESET}")
    print(f"{ORANGE}{'─' * 60}{RESET}")

    if not results["interfaces"]:
        print(f"{RED}[-] No physical Ethernet interfaces detected.{RESET}\n")
        sys.exit(0)

    for iface, data in results["interfaces"].items():
        carrier_str = f"{GREEN}CONNECTED (Carrier UP){RESET}" if data["carrier_detected"] else f"{RED}DISCONNECTED (No Carrier){RESET}"
        print(f"[*] Interface: {CYAN}{iface}{RESET} ({carrier_str})")
        print(f"    • MAC Address : {data['mac_address']}")
        print(f"    • IP Address  : {data['ip_address']}")

        sw = data["switch_neighbor"]
        if sw:
            print(f"    {GREEN}► Switch Neighbor (LLDP/CDP Detected):{RESET}")
            print(f"      • Switch Name : {BOLD}{sw['switch_name']}{RESET}")
            print(f"      • Remote Port : {BOLD}{sw['switch_port']}{RESET}")
            if sw.get("port_description"):
                print(f"      • Port Descr  : {sw['port_description']}")
            if sw.get("vlans"):
                print(f"      • VLANs       : {', '.join(sw['vlans'])}")
            if sw.get("management_ips"):
                print(f"      • Mgmt IP(s)  : {', '.join(sw['management_ips'])}")
            if sw.get("chassis_description"):
                print(f"      • Hardware    : {sw['chassis_description'][:50]}...")
        else:
            if data["carrier_detected"]:
                print(f"    {GRAY}• Switch neighbor: No LLDP/CDP advertisements received (unmanaged switch or protocol disabled){RESET}")
            else:
                print(f"    {GRAY}• Ethernet cable unplugged.{RESET}")
        print()
    print(f"{ORANGE}{'─' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
