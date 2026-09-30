#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цветные рендеры модели v3.1 rev.3 (matplotlib, без OpenGL) — для PDF-документа."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from cadquery.occ_impl.shapes import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build_v31_modular.py")

src = open(BUILD, encoding="utf-8").read().split("# ============================== ЭКСПОРТ")[0]
ns = {"__file__": BUILD}
exec(compile(src, "build_v31", "exec"), ns)
parts = ns["parts"]
W, H = ns["W"], ns["H"]
LEAF1_X0 = ns["LEAF1_X0"]


def rot(shape, x, y, z, dx, dy, dz, ang):
    return shape.rotate(Vector(x, y, z), Vector(x + dx, y + dy, z + dz), ang)


def mv(shape, dx, dy, dz):
    return shape.translate(Vector(dx, dy, dz))


def open_transform(nm, sh):
    """Ход механизмов: двери распахиваются, ящики выезжают (см. docs/kompas_motion.md)."""
    if nm.startswith(("10_Дверь_C2", "57_", "58_")):
        return rot(sh, W, 0, 0, 0, 0, 1, 100)
    if nm.startswith(("10_Дверь_C1", "55_", "56_")):
        return rot(sh, LEAF1_X0, 0, 0, 0, 0, 1, -100)
    if nm.startswith(("10_Дверь_B", "53_", "54_", "60_", "61_")):
        return rot(sh, 0, 0, 0, 0, 0, 1, -100)
    if nm.startswith(("15_Фасад_A", "64_", "65_")):
        return rot(sh, 0, 0, H, 1, 0, 0, -70)
    if nm.startswith(("11_Фасад_ящика_бака", "29_Ящик_бака",
                      "12_Фасад_ящика_сервиса", "30_Ящик_сервисный")):
        return mv(sh, 0, -450, 0)
    if nm.startswith("13_Фасад_секрет"):
        return mv(sh, 0, -350, 0)
    return sh


def draw(out_name, view, hide=(), title="", opened=False):
    fig = plt.figure(figsize=(15, 11), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    all_polys, all_colors, all_edges = [], [], []
    n = 0
    for p in parts:
        nm, shape = p["name"], p["shape"]
        if any(nm.startswith(h) for h in hide):
            continue
        if opened:
            shape = open_transform(nm, shape)
        verts, tris = shape.tessellate(0.35)
        vs = [(v.x, v.y, v.z) for v in verts]
        for t in tris:
            all_polys.append([vs[i] for i in t])
            all_colors.append(tuple(p["color"]) + (1.0,))
            all_edges.append((0.08, 0.08, 0.08, 0.30))
        n += 1

    pc = Poly3DCollection(all_polys, facecolors=all_colors, edgecolors=all_edges,
                          linewidths=0.12)
    pc.set_zsort("average")
    ax.add_collection3d(pc)
    ax.set_xlim(-80, 1420)
    ax.set_ylim(-480, 780)
    ax.set_zlim(-90, 2060)
    ax.set_box_aspect((1500, 1260, 2150))
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=11)
    plt.savefig(os.path.join(HERE, "renders", out_name), bbox_inches="tight", facecolor="white")
    plt.close()
    print(out_name, "— деталей:", n, "полигонов:", len(all_polys))


DOORS = ("10_Дверь", "53_", "54_", "55_", "56_", "57_", "58_", "15_Фасад_A", "64_", "65_")
draw("render_v31_iso.png", (22, -58), title="Гроубокс v3.1 rev.3 — общий вид (3/4)")
draw("render_v31_front.png", (8, -90), title="Гроубокс v3.1 rev.3 — вид спереди (3 двери)")
draw("render_v31_open.png", (18, -62), opened=True,
     title="Гроубокс v3.1 rev.3 — двери распахнуты, ящики выдвинуты")
draw("render_v31_cut.png", (20, -58), hide=DOORS + ("02_Боковина", "44_Крышка_A"),
     title="Гроубокс v3.1 rev.3 — сняты двери, боковина и крышка (внутренняя компоновка)")
