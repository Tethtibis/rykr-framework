#!/usr/bin/env python3
"""
==============================================================================
RYKR-SCENE: SPATIAL GEOMETRY ASSEMBLER (MODULE 1)
==============================================================================
Converts high-level architectural floor/node definitions into a hardened,
deterministic 3D Cartesian SceneGraph JSON contract.

Input:
  - CLI flags: --floor, --node, --lift, --preset
  - Or JSON stream over stdin.

Output:
  - stdout: Validated SceneGraph JSON contract.
  - Zero terminal formatting, zero ANSI codes, zero Braille logic.
==============================================================================
"""

import sys
import json
import argparse
from typing import Dict, Any, List

VERSION = "1.0.0"


def create_empty_scene() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "canvas": {
            "projection": "isometric",
            "yaw_deg": 30.0,
            "pitch_deg": 35.264
        },
        "bounds": {
            "x_min": 0.0, "y_min": 0.0, "z_min": 0.0,
            "x_max": 0.0, "y_max": 0.0, "z_max": 0.0
        },
        "nodes": [],
        "connectors": []
    }


def update_bounds(scene: Dict[str, Any]):
    """Calculates global 3D extent across all nodes and vectors."""
    xs, ys, zs = [0.0], [0.0], [0.0]
    for n in scene["nodes"]:
        x, y, z, w, d, h = n["box"]
        xs.extend([x, x + w])
        ys.extend([y, y + d])
        zs.extend([z, z + h])

    for c in scene["connectors"]:
        if "from_pos" in c and "to_pos" in c:
            xs.extend([c["from_pos"][0], c["to_pos"][0]])
            ys.extend([c["from_pos"][1], c["to_pos"][1]])
            zs.extend([c["from_pos"][2], c["to_pos"][2]])

    scene["bounds"] = {
        "x_min": min(xs),
        "y_min": min(ys),
        "z_min": min(zs),
        "x_max": max(xs),
        "y_max": max(ys),
        "z_max": max(zs)
    }


def build_preset_scene(preset_name: str) -> Dict[str, Any]:
    """Generates standard pre-configured multi-tier architectures."""
    scene = create_empty_scene()
    p = preset_name.lower().strip()

    if p in ("necrobeast", "sat", "satellite"):
        # 3-Tier Sovereign Satellite Stack
        scene["nodes"] = [
            {
                "id": "hw",
                "label": "Tier 0: GTX 1080 Ti (11GB Pascal)",
                "box": [0.0, 0.0, 0.0, 16.0, 6.0, 1.2],
                "style": "burnt_orange"
            },
            {
                "id": "runtime",
                "label": "Tier 1: Ollama Pascal (rykr-sat:14b)",
                "box": [0.0, 0.0, 4.0, 16.0, 6.0, 1.2],
                "style": "burnt_orange"
            },
            {
                "id": "memory",
                "label": "Tier 2: T0/T1/T2 Sovereign Memory Bus",
                "box": [0.0, 0.0, 8.0, 16.0, 6.0, 1.2],
                "style": "burnt_orange"
            }
        ]
        scene["connectors"] = [
            {
                "from": "hw",
                "to": "runtime",
                "from_pos": [8.0, 3.0, 1.2],
                "to_pos": [8.0, 3.0, 4.0],
                "type": "vertical_lift",
                "label": "CUDA VRAM Bus (~30 t/s)"
            },
            {
                "from": "runtime",
                "to": "memory",
                "from_pos": [8.0, 3.0, 5.2],
                "to_pos": [8.0, 3.0, 8.0],
                "type": "vertical_lift",
                "label": "T1 Working RAM Capper"
            }
        ]

    elif p in ("satisfactory", "factory"):
        # Multi-Floor Satisfactory Factory Schematic
        scene["nodes"] = [
            {
                "id": "floor0",
                "label": "Floor 0: Raw Ingestion & Mining",
                "box": [0.0, 0.0, 0.0, 14.0, 5.0, 1.0],
                "style": "burnt_orange"
            },
            {
                "id": "floor1",
                "label": "Floor 1: Intermediate Assembler",
                "box": [0.0, 0.0, 4.0, 14.0, 5.0, 1.0],
                "style": "burnt_orange"
            },
            {
                "id": "floor2",
                "label": "Floor 2: Packaged Output Station",
                "box": [0.0, 0.0, 8.0, 14.0, 5.0, 1.0],
                "style": "burnt_orange"
            }
        ]
        scene["connectors"] = [
            {
                "from": "floor0",
                "to": "floor1",
                "from_pos": [7.0, 2.5, 1.0],
                "to_pos": [7.0, 2.5, 4.0],
                "type": "vertical_lift",
                "label": "Conveyor Lift Mk.5"
            },
            {
                "from": "floor1",
                "to": "floor2",
                "from_pos": [7.0, 2.5, 5.0],
                "to_pos": [7.0, 2.5, 8.0],
                "type": "vertical_lift",
                "label": "Overhead Gantry Pipeline"
            }
        ]

    else:
        # Default 2-Tier Pipeline
        scene["nodes"] = [
            {
                "id": "src",
                "label": "Input Source",
                "box": [0.0, 0.0, 0.0, 12.0, 4.0, 1.0],
                "style": "burnt_orange"
            },
            {
                "id": "dst",
                "label": "Processed Output",
                "box": [0.0, 0.0, 4.0, 12.0, 4.0, 1.0],
                "style": "burnt_orange"
            }
        ]
        scene["connectors"] = [
            {
                "from": "src",
                "to": "dst",
                "from_pos": [6.0, 2.0, 1.0],
                "to_pos": [6.0, 2.0, 4.0],
                "type": "vertical_lift",
                "label": "Data Flow Pipe"
            }
        ]

    update_bounds(scene)
    return scene


def parse_args():
    parser = argparse.ArgumentParser(description="Rykr-Scene: Spatial Geometry Assembler")
    parser.add_argument("--preset", type=str, help="Load a pre-configured architecture (necrobeast, satisfactory, default)")
    parser.add_argument("--floor", action="append", help="Define a horizontal floor plane: 'Z:Name:Label' (repeatable)")
    parser.add_argument("--lift", action="append", help="Connect two floors vertically: 'FromID->ToID:Label' (repeatable)")
    return parser.parse_args()


def main():
    args = parse_args()

    # 1. Preset Mode
    if args.preset:
        scene = build_preset_scene(args.preset)
        print(json.dumps(scene, indent=2))
        return

    # 2. Dynamic Floor / Lift CLI Mode
    if args.floor:
        scene = create_empty_scene()
        floor_height = 1.0
        floor_width = 16.0
        floor_depth = 6.0
        node_lookup = {}

        for idx, fl_str in enumerate(args.floor):
            parts = fl_str.split(":", 2)
            if len(parts) == 3:
                try:
                    z_pos = float(parts[0])
                except ValueError:
                    z_pos = float(idx * 4.0)
                nid = parts[1].strip()
                label = parts[2].strip()
            elif len(parts) == 2:
                z_pos = float(idx * 4.0)
                nid = parts[0].strip()
                label = parts[1].strip()
            else:
                z_pos = float(idx * 4.0)
                nid = f"floor_{idx}"
                label = parts[0].strip()

            node = {
                "id": nid,
                "label": label,
                "box": [0.0, 0.0, z_pos, floor_width, floor_depth, floor_height],
                "style": "burnt_orange"
            }
            scene["nodes"].append(node)
            node_lookup[nid] = node

        if args.lift:
            for l_str in args.lift:
                if "->" in l_str:
                    endpoints, label = l_str.split(":", 1) if ":" in l_str else (l_str, "Conveyor Bus")
                    src_id, dst_id = endpoints.split("->", 1)
                    src_id, dst_id = src_id.strip(), dst_id.strip()
                    if src_id in node_lookup and dst_id in node_lookup:
                        s_node = node_lookup[src_id]
                        d_node = node_lookup[dst_id]
                        scene["connectors"].append({
                            "from": src_id,
                            "to": dst_id,
                            "from_pos": [floor_width / 2.0, floor_depth / 2.0, s_node["box"][2] + floor_height],
                            "to_pos": [floor_width / 2.0, floor_depth / 2.0, d_node["box"][2]],
                            "type": "vertical_lift",
                            "label": label.strip()
                        })

        update_bounds(scene)
        print(json.dumps(scene, indent=2))
        return

    # 3. Check stdin for piped JSON
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read().strip()
            if raw:
                data = json.loads(raw)
                update_bounds(data)
                print(json.dumps(data, indent=2))
                return
        except Exception as e:
            sys.stderr.write(f"[rykr-scene:ERROR] Failed to parse stdin JSON: {e}\n")
            sys.exit(1)

    # Default fallback to satisfactory preset if invoked bare
    scene = build_preset_scene("satisfactory")
    print(json.dumps(scene, indent=2))


if __name__ == "__main__":
    main()
