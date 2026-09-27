#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цветные рендеры модели growbox_v3 на matplotlib (софтверные, без OpenGL).
Все полигоны всех деталей собираются в один набор — корректная сортировка граней."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))

src = open(os.path.join(HERE, "build_growbox_v3.py"), encoding="utf-8").read()
src = src.split("# ================= СБОРКА")[0]
ns = {"__file__": os.path.join(HERE, "build_growbox_v3.py")}
exec(compile(src, "build_part", "exec"), ns)
parts = ns["parts"]

HIDE_FOR_CUT = ("Дверь", "Фасад", "Ручка", "Боковина_правая", "Крышка", "Решётка", "Оргалит")


def draw(out_name, view, hide=(), title=""):
    fig = plt.figure(figsize=(15, 11), dpi=110)
    ax = fig.add_subplot(111, projection="3d")

    all_polys, all_colors, all_edges = [], [], []
    n = 0
    for name, shape, color, cut, qty, mat in parts:
        if any(name.startswith(p) for p in hide):
            continue
        verts, tris = shape.tessellate(0.35)
        vs = [(v.x, v.y, v.z) for v in verts]
        for t in tris:
            all_polys.append([vs[i] for i in t])
            all_colors.append(color + (1.0,))
            all_edges.append((0.08, 0.08, 0.08, 0.30))
        n += 1

    pc = Poly3DCollection(all_polys, facecolors=all_colors, edgecolors=all_edges,
                          linewidths=0.12)
    pc.set_zsort("average")
    ax.add_collection3d(pc)

    ax.set_xlim(0, 1280)
    ax.set_ylim(-60, 760)
    ax.set_zlim(-80, 2050)
    ax.set_box_aspect((1280, 820, 2130))
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=11)
    plt.savefig(os.path.join(HERE, out_name), bbox_inches="tight", facecolor="white")
    plt.close()
    print(out_name, "— деталей:", n, "полигонов:", len(all_polys))


draw("render_iso.png", (22, -58), title="Гроубокс v3.0 — общий вид (3/4)")
draw("render_front.png", (8, -90), title="Гроубокс v3.0 — вид спереди")
draw("render_side.png", (8, 2), title="Гроубокс v3.0 — вид справа")
draw("render_cut.png", (20, -58), hide=HIDE_FOR_CUT, title="Гроубокс v3.0 — сняты фасады/крышка")
draw("render_top.png", (86, -90), hide=HIDE_FOR_CUT, title="Гроубокс v3.0 — вид сверху (без крышки)")
