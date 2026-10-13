#!/usr/bin/env python3
"""
==============================================================================
RYKR-DEMO: REAL-TIME 3D BRAILLE WIREFRAME DEMO
==============================================================================
Demonstrates sub-pixel 2x4 dot-matrix rendering with a rotating 3D wireframe
cube styled in Burnt Orange (#CC5500).
==============================================================================
"""

import sys
import os
import math
import time
import signal

# ANSI Escape Sequences
ORANGE = "\033[38;2;204;85;0m"
BOLD_ORANGE = "\033[1;38;2;204;85;0m"
WHITE = "\033[1;37m"
GRAY = "\033[90m"
RESET = "\033[0m"
CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"
CLEAR_SCREEN = "\033[2J\033[H"
HOME_CURSOR = "\033[H"


def sig_handler(sig, frame):
    sys.stdout.write(CURSOR_SHOW + "\n" + RESET)
    sys.exit(0)


signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def rotate_3d(x, y, z, ax, ay, az):
    """Rotates a 3D point around X, Y, and Z axes."""
    # Rotate around X
    rad_x = math.radians(ax)
    y1 = y * math.cos(rad_x) - z * math.sin(rad_x)
    z1 = y * math.sin(rad_x) + z * math.cos(rad_x)

    # Rotate around Y
    rad_y = math.radians(ay)
    x2 = x * math.cos(rad_y) + z1 * math.sin(rad_y)
    z2 = -x * math.sin(rad_y) + z1 * math.cos(rad_y)

    # Rotate around Z
    rad_z = math.radians(az)
    x3 = x2 * math.cos(rad_z) - y1 * math.sin(rad_z)
    y3 = x2 * math.sin(rad_z) + y1 * math.cos(rad_z)

    return x3, y3, z2


def render_frame(cols, rows, angle_x, angle_y, angle_z):
    sub_w = cols * 2
    sub_h = rows * 4
    pixels = [[False] * sub_w for _ in range(sub_h)]

    # 8 vertices of a cube
    raw_verts = [
        (-1.0, -1.0, -1.0),
        ( 1.0, -1.0, -1.0),
        ( 1.0,  1.0, -1.0),
        (-1.0,  1.0, -1.0),
        (-1.0, -1.0,  1.0),
        ( 1.0, -1.0,  1.0),
        ( 1.0,  1.0,  1.0),
        (-1.0,  1.0,  1.0),
    ]

    # 12 edges connecting the vertices
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # back
        (4, 5), (5, 6), (6, 7), (7, 4),  # front
        (0, 4), (1, 5), (2, 6), (3, 7)   # connectors
    ]

    # Rotate and project vertices
    proj = []
    scale = min(sub_w, sub_h) * 0.35
    cx_sub = sub_w / 2.0
    cy_sub = sub_h / 2.0

    for vx, vy, vz in raw_verts:
        rx, ry, rz = rotate_3d(vx, vy, vz, angle_x, angle_y, angle_z)
        # Perspective projection
        fov = 3.2
        persp = fov / (fov + rz)
        px = int(round(rx * scale * persp + cx_sub))
        py = int(round(ry * scale * persp * 0.9 + cy_sub))  # Aspect correction
        proj.append((px, py))

    # Draw lines
    def draw_line(x0, y0, x1, y1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            if 0 <= x0 < sub_w and 0 <= y0 < sub_h:
                pixels[y0][x0] = True
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    for e0, e1 in edges:
        draw_line(proj[e0][0], proj[e0][1], proj[e1][0], proj[e1][1])

    # Convert virtual framebuffer to Braille text
    out_lines = []
    center_char_x = cols // 2
    center_char_y = rows // 2
    label = "RYKR-3D"

    for cy in range(rows):
        line = []
        py_base = cy * 4
        is_label_row = (cy == center_char_y)
        label_start_x = center_char_x - (len(label) // 2)

        for cx in range(cols):
            # Embed centered label
            if is_label_row and label_start_x <= cx < label_start_x + len(label):
                idx = cx - label_start_x
                line.append(f"{WHITE}{label[idx]}{RESET}")
                continue

            px_base = cx * 2
            mask = 0
            if pixels[py_base + 0][px_base + 0]: mask |= 0x01
            if pixels[py_base + 1][px_base + 0]: mask |= 0x02
            if pixels[py_base + 2][px_base + 0]: mask |= 0x04
            if pixels[py_base + 0][px_base + 1]: mask |= 0x08
            if pixels[py_base + 1][px_base + 1]: mask |= 0x10
            if pixels[py_base + 2][px_base + 1]: mask |= 0x20
            if pixels[py_base + 3][px_base + 0]: mask |= 0x40
            if pixels[py_base + 3][px_base + 1]: mask |= 0x80

            if mask == 0:
                line.append(" ")
            else:
                line.append(f"{ORANGE}{chr(0x2800 + mask)}{RESET}")

        out_lines.append("".join(line).rstrip())

    return "\n".join(out_lines)


def main():
    try:
        size = os.get_terminal_size()
        cols = min(size.columns - 4, 72)
        rows = min(size.lines - 4, 22)
    except Exception:
        cols, rows = 64, 18

    # Check for single-frame mode (e.g. for non-interactive output)
    if "--snapshot" in sys.argv:
        print(render_frame(cols, rows, 30.0, 45.0, 15.0))
        return

    # Check for limited duration / frame count
    max_frames = 150 if "--short" in sys.argv else 1000000

    sys.stdout.write(CURSOR_HIDE + CLEAR_SCREEN)
    ax, ay, az = 0.0, 0.0, 0.0
    frame_count = 0

    try:
        while frame_count < max_frames:
            rendered = render_frame(cols, rows, ax, ay, az)
            sys.stdout.write(HOME_CURSOR)
            sys.stdout.write(f"{BOLD_ORANGE}--- RYKR MATRIX: REAL-TIME 3D BRAILLE RASTERIZER ---{RESET}\n")
            sys.stdout.write(f"{GRAY}Sub-pixel 2x4 dot-matrix projection | Exit: Ctrl+C{RESET}\n")
            sys.stdout.write(rendered + "\n")
            sys.stdout.flush()

            ax = (ax + 3.0) % 360
            ay = (ay + 4.5) % 360
            az = (az + 1.5) % 360
            frame_count += 1
            time.sleep(0.033)  # ~30 FPS
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sys.stdout.write(CURSOR_SHOW + "\n" + RESET)


if __name__ == "__main__":
    main()
