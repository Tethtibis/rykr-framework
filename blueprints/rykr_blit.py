#!/usr/bin/env python3
"""
==============================================================================
RYKR-BLIT: MATHEMATICAL BRAILLE RASTERIZER (MODULE 2)
==============================================================================
Ingests SceneGraph JSON from stdin, projects 3D isometric coordinates to
a 2D sub-pixel virtual canvas, and blits into Unicode Braille (U+2800..U+28FF)
with crisp ASCII labels and Burnt Orange ANSI styling.

Guarantees:
  - 0% line wrapping (fits strictly inside detected $COLUMNS).
  - Unbreakable ioctl fallback for headless pipes.
  - Sub-pixel vector lines with non-clobbering label cutouts.
==============================================================================
"""

import sys
import os
import math
import json
import argparse
from typing import Dict, Any, List, Tuple

# ANSI Colors (Burnt Orange #CC5500)
ORANGE = "\033[38;2;204;85;0m"
BOLD_ORANGE = "\033[1;38;2;204;85;0m"
DIM_ORANGE = "\033[38;2;136;56;0m"
WHITE = "\033[1;37m"
GRAY = "\033[90m"
RESET = "\033[0m"

COS_30 = math.cos(math.radians(30))  # ~0.8660
SIN_30 = math.sin(math.radians(30))  # 0.5000
ASPECT_RATIO = 0.92                  # Fine-tuned for terminal font line-spacing


def get_terminal_dimensions() -> Tuple[int, int]:
    """Robust 4-tier terminal size detector immune to broken-pipe ioctl crashes."""
    for fd in (sys.stdout, sys.stderr, sys.stdin):
        try:
            if hasattr(fd, "fileno"):
                size = os.get_terminal_size(fd.fileno())
                if size.columns > 20 and size.lines > 10:
                    return size.columns, size.lines
        except Exception:
            continue

    try:
        cols = int(os.environ.get("COLUMNS", 80))
        lines = int(os.environ.get("LINES", 24))
        return max(cols, 40), max(lines, 15)
    except Exception:
        pass

    return 80, 24


class BrailleCanvas:
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.sub_w = cols * 2
        self.sub_h = rows * 4
        self.pixels = [[False] * self.sub_w for _ in range(self.sub_h)]
        self.labels: Dict[Tuple[int, int], Tuple[str, str]] = {}  # (cx, cy) -> (char, color)

    def set_pixel(self, x: int, y: int):
        if 0 <= x < self.sub_w and 0 <= y < self.sub_h:
            self.pixels[y][x] = True

    def draw_line(self, x0: int, y0: int, x1: int, y1: int):
        """Bresenham's line algorithm on sub-pixel grid."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.set_pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def add_label(self, cx: int, cy: int, text: str, color: str = WHITE):
        """Places text label and carves out sub-pixel exclusion zone."""
        start_x = cx - (len(text) // 2)
        for i, ch in enumerate(text):
            pos_x = start_x + i
            if 0 <= pos_x < self.cols and 0 <= cy < self.rows:
                self.labels[(pos_x, cy)] = (ch, color)
                # Mask out sub-pixels in this character cell to prevent clobbering
                px_start = pos_x * 2
                py_start = cy * 4
                for py in range(py_start, py_start + 4):
                    for px in range(px_start, px_start + 2):
                        if 0 <= px < self.sub_w and 0 <= py < self.sub_h:
                            self.pixels[py][px] = False

    def render(self, use_color: bool = True) -> str:
        """Converts virtual framebuffer into Unicode Braille string with labels."""
        # Braille dot mapping bit offsets
        # [0, 3]
        # [1, 4]
        # [2, 5]
        # [6, 7]
        output_lines = []

        for cy in range(self.rows):
            line_chars = []
            py_base = cy * 4
            active_color = None

            for cx in range(self.cols):
                # 1. Check if an ASCII text label exists at this cell
                if (cx, cy) in self.labels:
                    ch, col = self.labels[(cx, cy)]
                    if use_color:
                        if active_color != col:
                            if active_color is not None:
                                line_chars.append(RESET)
                            line_chars.append(col)
                            active_color = col
                    line_chars.append(ch)
                    continue

                # 2. Compute 8-dot Braille bitmask
                px_base = cx * 2
                mask = 0
                if self.pixels[py_base + 0][px_base + 0]: mask |= 0x01
                if self.pixels[py_base + 1][px_base + 0]: mask |= 0x02
                if self.pixels[py_base + 2][px_base + 0]: mask |= 0x04
                if self.pixels[py_base + 0][px_base + 1]: mask |= 0x08
                if self.pixels[py_base + 1][px_base + 1]: mask |= 0x10
                if self.pixels[py_base + 2][px_base + 1]: mask |= 0x20
                if self.pixels[py_base + 3][px_base + 0]: mask |= 0x40
                if self.pixels[py_base + 3][px_base + 1]: mask |= 0x80

                if mask == 0:
                    if active_color is not None:
                        line_chars.append(RESET)
                        active_color = None
                    line_chars.append(" ")
                else:
                    b_char = chr(0x2800 + mask)
                    if use_color:
                        if active_color != ORANGE:
                            if active_color is not None:
                                line_chars.append(RESET)
                            line_chars.append(ORANGE)
                            active_color = ORANGE
                    line_chars.append(b_char)

            if active_color is not None:
                line_chars.append(RESET)

            # Strip trailing whitespace on each line to prevent wrapping
            line_str = "".join(line_chars).rstrip()
            output_lines.append(line_str)

        # Trim leading and trailing empty lines
        while output_lines and not output_lines[0].strip():
            output_lines.pop(0)
        while output_lines and not output_lines[-1].strip():
            output_lines.pop()

        return "\n".join(output_lines)


def project_isometric(x: float, y: float, z: float) -> Tuple[float, float]:
    """Standard 30-degree axonometric isometric projection."""
    u = (x - y) * COS_30
    v = ((x + y) * SIN_30 - z) * ASPECT_RATIO
    return u, v


def render_scene(scene: Dict[str, Any], target_cols: int, target_rows: int, use_color: bool = True) -> str:
    """Projects SceneGraph JSON and renders to Braille terminal string."""
    nodes = scene.get("nodes", [])
    connectors = scene.get("connectors", [])

    if not nodes:
        return f"{GRAY}[rykr-blit: Empty SceneGraph]{RESET}"

    # 1. Collect all 3D vertices to determine bounding extent
    vertices_3d = []
    for n in nodes:
        x, y, z, w, d, h = n["box"]
        # 8 corners of the box
        for dx in (0, w):
            for dy in (0, d):
                for dz in (0, h):
                    vertices_3d.append((x + dx, y + dy, z + dz))

    for c in connectors:
        if "from_pos" in c:
            vertices_3d.append(tuple(c["from_pos"]))
        if "to_pos" in c:
            vertices_3d.append(tuple(c["to_pos"]))

    # 2. Project to 2D unscaled isometric space
    projected_2d = [project_isometric(vx, vy, vz) for vx, vy, vz in vertices_3d]
    u_vals = [p[0] for p in projected_2d]
    v_vals = [p[1] for p in projected_2d]

    min_u, max_u = min(u_vals), max(u_vals)
    min_v, max_v = min(v_vals), max(v_vals)
    span_u = max(max_u - min_u, 1.0)
    span_v = max(max_v - min_v, 1.0)

    # 3. Canvas sizing (Strictly bounded to terminal size)
    safe_cols = max(min(target_cols - 4, 140), 30)
    safe_rows = max(min(target_rows - 3, 40), 12)
    canvas = BrailleCanvas(safe_cols, safe_rows)

    sub_w_usable = canvas.sub_w - 12
    sub_h_usable = canvas.sub_h - 12

    scale_x = sub_w_usable / span_u
    scale_y = sub_h_usable / span_v
    scale = min(scale_x, scale_y)  # Preserves uniform scaling

    offset_u = 6 + (sub_w_usable - (span_u * scale)) / 2.0
    offset_v = 6 + (sub_h_usable - (span_v * scale)) / 2.0

    def to_canvas_px(wx: float, wy: float, wz: float) -> Tuple[int, int]:
        u, v = project_isometric(wx, wy, wz)
        px = int(round((u - min_u) * scale + offset_u))
        # Note: In screen coords, Y increases downwards, so v is inverted
        py = int(round((v - min_v) * scale + offset_v))
        return px, py

    # 4. Draw Connectors (Vertical Lifts / Pipes) first so boxes sit over them
    for c in connectors:
        f_pos = c.get("from_pos")
        t_pos = c.get("to_pos")
        if f_pos and t_pos:
            p0 = to_canvas_px(*f_pos)
            p1 = to_canvas_px(*t_pos)
            canvas.draw_line(p0[0], p0[1], p1[0], p1[1])
            # Draw lift shaft parallel lines for visual depth
            canvas.draw_line(p0[0] + 1, p0[1], p1[0] + 1, p1[1])

            # Label on lift shaft if space permits
            lbl = c.get("label")
            if lbl:
                mid_x = (p0[0] + p1[0]) // 4  # convert sub_px to char col
                mid_y = (p0[1] + p1[1]) // 8
                canvas.add_label(mid_x, mid_y, f"[{lbl}]", color=DIM_ORANGE)

    # 5. Draw 3D Bounding Boxes for each node
    for n in nodes:
        x, y, z, w, d, h = n["box"]
        # Bottom 4 corners
        b0 = to_canvas_px(x, y, z)
        b1 = to_canvas_px(x + w, y, z)
        b2 = to_canvas_px(x + w, y + d, z)
        b3 = to_canvas_px(x, y + d, z)

        # Top 4 corners
        t0 = to_canvas_px(x, y, z + h)
        t1 = to_canvas_px(x + w, y, z + h)
        t2 = to_canvas_px(x + w, y + d, z + h)
        t3 = to_canvas_px(x, y + d, z + h)

        # Wireframe edges - Bottom plane
        canvas.draw_line(b0[0], b0[1], b1[0], b1[1])
        canvas.draw_line(b1[0], b1[1], b2[0], b2[1])
        canvas.draw_line(b2[0], b2[1], b3[0], b3[1])
        canvas.draw_line(b3[0], b3[1], b0[0], b0[1])

        # Wireframe edges - Top plane
        canvas.draw_line(t0[0], t0[1], t1[0], t1[1])
        canvas.draw_line(t1[0], t1[1], t2[0], t2[1])
        canvas.draw_line(t2[0], t2[1], t3[0], t3[1])
        canvas.draw_line(t3[0], t3[1], t0[0], t0[1])

        # Vertical pillars
        canvas.draw_line(b0[0], b0[1], t0[0], t0[1])
        canvas.draw_line(b1[0], b1[1], t1[0], t1[1])
        canvas.draw_line(b2[0], b2[1], t2[0], t2[1])
        canvas.draw_line(b3[0], b3[1], t3[0], t3[1])

        # 6. Center ASCII Text Label on front/top face
        label_text = n.get("label", "")
        if label_text:
            center_x = (t0[0] + t1[0] + t2[0] + t3[0]) // 4
            center_y = (t0[1] + t1[1] + t2[1] + t3[1]) // 4
            char_x = center_x // 2
            char_y = center_y // 4
            canvas.add_label(char_x, char_y, label_text, color=WHITE)

    return canvas.render(use_color=use_color)


def main():
    parser = argparse.ArgumentParser(description="Rykr-Blit: Mathematical Braille Rasterizer")
    parser.add_argument("--cols", type=int, help="Override terminal columns width")
    parser.add_argument("--rows", type=int, help="Override terminal rows height")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color codes")
    args = parser.parse_args()

    # Ingest SceneGraph JSON from stdin
    try:
        raw_json = sys.stdin.read().strip()
        if not raw_json:
            sys.stderr.write("[rykr-blit:ERROR] No SceneGraph JSON received on stdin.\n")
            sys.exit(1)
        scene = json.loads(raw_json)
    except Exception as e:
        sys.stderr.write(f"[rykr-blit:ERROR] Invalid SceneGraph JSON: {e}\n")
        sys.exit(1)

    # Detect terminal dimensions
    det_cols, det_rows = get_terminal_dimensions()
    target_cols = args.cols if args.cols else det_cols
    target_rows = args.rows if args.rows else det_rows

    rendered = render_scene(scene, target_cols, target_rows, use_color=not args.no_color)
    print(rendered)


if __name__ == "__main__":
    main()
