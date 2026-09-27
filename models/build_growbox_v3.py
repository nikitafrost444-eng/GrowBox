#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Гроубокс v3.0 — параметрическая 3D-модель (CadQuery → STEP / STL / SVG).
Все размеры в миллиметрах.
Система координат: X — ширина (0 слева), Y — глубина (0 — передний край корпуса, фасады в минусе),
Z — высота (0 — низ корпуса, опоры ниже нуля).

Внешние габариты корпуса: 1250 x 700 x 2000 (с фасадами глубина 718).
Тех-колонна внутр.: 400 x 620 x 1964. Зона растений внутр.: 796 x 620 x 1964.
Задний кабельный колодец: 58 мм (оргалит 4 мм на тыльной кромке).
"""
import os
import cadquery as cq
from cadquery import exporters, Shape, Vector, Solid

# ================= ПАРАМЕТРЫ =================
T = 18                       # ЛДСП
W, D, H = 1250, 700, 2000    # корпус (без фасадов)
TECH_W = 400                 # внутр. ширина тех-колонны
DOOR_T = 18
BACK_T = 18
ORG_T = 4

TECH_X0, TECH_X1 = T, T + TECH_W                  # 18 .. 418
GROW_X0, GROW_X1 = TECH_X1 + T, W - T             # 436 .. 1232
ZONE_D = D - BACK_T - 58                          # 620 (полезная глубина зон)
Z0, Z1 = T, H - T                                 # 18 .. 1982 (внутр. по высоте)

OUT = os.path.dirname(os.path.abspath(__file__))

# ================= ЦВЕТА =================
C = dict(
    carcass=(0.62, 0.63, 0.66), door=(0.16, 0.16, 0.19), handle=(0.78, 0.78, 0.82),
    shelf=(0.72, 0.70, 0.66), drawer=(0.55, 0.53, 0.50), tank=(0.30, 0.55, 0.85),
    humid=(0.88, 0.90, 0.92), elec=(0.18, 0.32, 0.22), elec2=(0.22, 0.24, 0.28),
    fan=(0.28, 0.30, 0.33), silencer=(0.52, 0.54, 0.58), duct=(0.72, 0.74, 0.77),
    grille=(0.20, 0.20, 0.22), mat=(0.25, 0.50, 0.80), pot=(0.42, 0.30, 0.20),
    frame=(0.76, 0.76, 0.80), net=(0.55, 0.68, 0.55), light=(0.84, 0.84, 0.88),
    bar=(0.92, 0.92, 0.95), uv=(0.58, 0.36, 0.78), ir=(0.86, 0.32, 0.26),
    act=(0.66, 0.67, 0.70), filt=(0.13, 0.13, 0.15), led=(0.30, 0.85, 0.42),
    foot=(0.15, 0.15, 0.17), orgalit=(0.45, 0.38, 0.30),
)

parts = []   # (name, shape, color_key, (L,W,T) для карты раскроя или None, кол-во, материал)


def add(name, shape, color, cut=None, qty=1, mat=""):
    parts.append((name, shape, C[color], cut, qty, mat))
    return shape


def box(x0, y0, z0, dx, dy, dz):
    return Solid.makeBox(dx, dy, dz, Vector(x0, y0, z0))


def cyl(x, y, z, r, h, axis="z"):
    d = {"z": Vector(0, 0, 1), "x": Vector(1, 0, 0), "y": Vector(0, 1, 0)}[axis]
    return Solid.makeCylinder(r, h, Vector(x, y, z), d)


# ================= КОРПУС =================
add("Боковина_левая", box(0, 0, 0, T, D, H), "carcass", (D, H, T), 1, "ЛДСП 18")
add("Боковина_правая", box(W - T, 0, 0, T, D, H), "carcass", (D, H, T), 1, "ЛДСП 18")
add("Крышка", box(T, 0, H - T, W - 2 * T, D, T), "carcass", (W - 2 * T, D, T), 1, "ЛДСП 18")
add("Дно", box(T, 0, 0, W - 2 * T, D, T), "carcass", (W - 2 * T, D, T), 1, "ЛДСП 18")

# Перегородка между зонами — с сервисными отверстиями
part_shape = box(TECH_X1, 0, Z0, T, ZONE_D, Z1 - Z0)
holes = [
    cyl(TECH_X1 - 20, 160, 1875, 50, T + 40, "x"),    # Ø100 тракт вентиляции
    cyl(TECH_X1 - 20, 120, 1150, 20, T + 40, "x"),    # Ø40 патрубок увлажнителя
    cyl(TECH_X1 - 20, 450, 1330, 12.5, T + 40, "x"),  # Ø25 x3 (RJ12 / датчики)
    cyl(TECH_X1 - 20, 470, 1370, 12.5, T + 40, "x"),
    cyl(TECH_X1 - 20, 490, 1410, 12.5, T + 40, "x"),
    cyl(TECH_X1 - 20, 520, 900, 10, T + 40, "x"),     # Ø20 силовой ввод
]
part_shape = part_shape.cut(*holes)
add("Перегородка_сервисная", part_shape, "carcass", (ZONE_D, Z1 - Z0, T), 1, "ЛДСП 18")

add("Задняя_стенка_техзоны", box(TECH_X0, ZONE_D, Z0, TECH_W + T, BACK_T, Z1 - Z0),
    "carcass", (TECH_W + T, Z1 - Z0, BACK_T), 1, "Фанера 18")
add("Задняя_стенка_зоны_роста", box(GROW_X0, ZONE_D, Z0, GROW_X1 - GROW_X0, BACK_T, Z1 - Z0),
    "carcass", (GROW_X1 - GROW_X0, Z1 - Z0, BACK_T), 1, "Фанера 18")
add("Оргалит_колодца", box(TECH_X0, D - ORG_T, Z0, W - 2 * TECH_X0 + T, ORG_T, Z1 - Z0),
    "orgalit", (W - 2 * TECH_X0 + T, Z1 - Z0, ORG_T), 1, "Оргалит 4")

for i, (fx, fy) in enumerate([(40, 40), (1130, 40), (40, 580), (1130, 580)], 1):
    add(f"Опора_{i}", box(fx, fy, -60, 80, 80, 60), "foot", None, 4, "Каучук/пробка")

# ================= ФАСАДЫ =================
add("Дверь_зоны_роста", box(GROW_X0 - 8, -DOOR_T, 0, 822, DOOR_T, H), "door", (822, H, DOOR_T), 1, "ЛДСП 18")
add("Фасад_техзоны_верх", box(0, -DOOR_T, 820, GROW_X0 - 8, DOOR_T, H - 820), "door",
    (GROW_X0 - 8, H - 820, DOOR_T), 1, "ЛДСП 18")
add("Фасад_ящика_помпа", box(0, -DOOR_T, 520, GROW_X0 - 8, DOOR_T, 300), "door",
    (GROW_X0 - 8, 300, DOOR_T), 1, "ЛДСП 18")
add("Фасад_ящика_бак", box(0, -DOOR_T, 0, GROW_X0 - 8, DOOR_T, 520), "door",
    (GROW_X0 - 8, 520, DOOR_T), 1, "ЛДСП 18")
add("Ручка_двери", box(1206, -DOOR_T - 12, 700, 24, 12, 600), "handle")
add("Ручка_техзоны", box(372, -DOOR_T - 12, 1200, 24, 12, 300), "handle")
add("Решётка_выхода_в_комнату", box(48, -DOOR_T - 4, 1690, 340, 4, 280), "grille")

# ================= ЯЩИКИ ТЕХ-КОЛОННЫ =================
def drawer(name, z, h):
    outer = box(31, 30, z, 374, 550, h)
    inner = box(31 + 12, 30 + 12, z + 12, 374 - 24, 550 - 24, h)
    add(name, outer.cut(inner), "drawer", None, 1, "ЛДСП 12 + Blum Tandem 500")


drawer("Ящик_бака", 30, 470)
drawer("Ящик_насосов", 550, 240)

# ================= ПОЛКИ / ПАНЕЛИ ТЕХ-КОЛОННЫ =================
add("Полка_секретбокс", box(TECH_X0, 0, 820, TECH_W, ZONE_D, T), "shelf",
    (TECH_W, ZONE_D, T), 1, "ЛДСП 18")
add("Панель_электроники", box(TECH_X0, ZONE_D - BACK_T - 18, 1080, TECH_W, T, 340), "shelf",
    (TECH_W, 340, T), 1, "Фанера 10 (съёмная)")
add("Полка_бака_резервного", box(TECH_X0, 0, 1420, TECH_W, ZONE_D, T), "shelf",
    (TECH_W, ZONE_D, T), 1, "ЛДСП 18 + рама 30x30")

# ================= ОБОРУДОВАНИЕ ТЕХ-КОЛОННЫ =================
add("Бак_рабочий_20л", box(75, 80, 60, 280, 280, 340), "tank")
add("Бак_резервный_20л", box(75, 80, 1438, 280, 280, 340), "tank")
add("Поплавковый_клапан", box(300, 300, 1438, 60, 60, 60), "elec2")
add("Увлажнитель_SF_5л", box(60, 80, 838, 240, 240, 320), "humid")
add("Камера_WiFi", box(315, 520, 1000, 80, 80, 70), "elec2")
add("ИБП_600ВА", box(60, 80, 560, 250, 200, 140), "elec2")
add("Дозатор_удобрений", box(320, 90, 838, 90, 200, 190), "elec")
add("pH_модуль", box(320, 310, 838, 90, 120, 120), "elec")
add("AC10_№1", box(40, 505, 1100, 340, 80, 110), "elec2")
add("AC10_№2", box(40, 505, 1230, 340, 80, 110), "elec2")
add("GGS_Controller", box(60, 505, 1355, 160, 80, 60), "elec2")
add("БП_12В", box(250, 505, 1355, 130, 80, 60), "elec2")

# ================= ВЕНТ-МОДУЛЬ (верх тех-колонны) =================
add("Вентилятор_SF_4", cyl(180, 160, 1875, 65, 250, "x"), "fan")
add("Шумоглушитель", cyl(135, 120, 1875, 75, 400, "y"), "silencer")
add("Воздуховод_Ø100", cyl(TECH_X1 - 20, 160, 1875, 50, 230, "x"), "duct")
add("Виброподвесы_вентилятора", box(190, 130, 1940, 60, 60, 30), "foot")

# ================= ЗОНА РОСТА =================
mat_outer = box(GROW_X0, 0, Z0, GROW_X1 - GROW_X0, ZONE_D, 50)
mat_inner = box(GROW_X0 + 10, 10, Z0 + 10, GROW_X1 - GROW_X0 - 20, ZONE_D - 20, 50)
add("Коврик_EVA_с_бортами", mat_outer.cut(mat_inner), "mat")

add("Горшок_1_15л", cyl(700, 180, 68, 160, 320), "pot")
add("Горшок_2_15л", cyl(970, 440, 68, 160, 320), "pot")

# Направляющие SCROG — вплотную к боковинам зоны
add("Направляющая_SCROG_L", box(GROW_X0, 300, 400, 20, 20, 1000), "frame")
add("Направляющая_SCROG_R", box(GROW_X1 - 20, 300, 400, 20, 20, 1000), "frame")

# SCROG V-рама (рамка 700x500 + борта под 18°)
add("SCROG_рама_перед", box(484, 65, 850, 700, 20, 20), "frame")
add("SCROG_рама_зад", box(484, 545, 850, 700, 20, 20), "frame")
add("SCROG_рама_лево", box(484, 85, 850, 20, 460, 20), "frame")
add("SCROG_рама_право", box(1164, 85, 850, 20, 460, 20), "frame")

axis_a, axis_b = Vector(484, 310, 878), Vector(1184, 310, 878)
flap_f = box(484, 65, 878, 700, 245, 6).rotate(axis_a, axis_b, -18)
add("SCROG_борт_передний", flap_f, "net")
flap_b = box(484, 310, 878, 700, 245, 6).rotate(axis_a, axis_b, 18)
add("SCROG_борт_задний", flap_b, "net")
add("SCROG_сетка", box(484, 65, 872, 700, 490, 2), "net")

# Кронштейны: рамка SCROG опирается на направляющие
add("Кронштейн_SCROG_1", box(GROW_X0 + 20, 65, 850, 28, 20, 20), "frame")
add("Кронштейн_SCROG_2", box(GROW_X0 + 20, 545, 850, 28, 20, 20), "frame")
add("Кронштейн_SCROG_3", box(GROW_X1 - 48, 65, 850, 28, 20, 20), "frame")
add("Кронштейн_SCROG_4", box(GROW_X1 - 48, 545, 850, 28, 20, 20), "frame")

# Свет SE3000 (603 x 585 x 71) + UV/IR бары
add("SE3000_каркас", box(532, 17, 1396, 603, 585, 25), "light")
for i, by in enumerate([25, 183, 341, 499], 1):
    add(f"SE3000_бара_{i}", box(549, by, 1351, 570, 62, 45), "bar")
add("UV30_бар", box(446, 10, 1385, 60, 600, 25), "uv")
add("IR16_бар", box(1162, 10, 1385, 60, 600, 25), "ir")

# Моторизованный подъём
add("Траверса_актуатора", box(534, 288, 1902, 600, 44, 40), "frame")
add("Актуатор_12В", cyl(834, 310, 1710, 30, 192), "act")
add("Шток_актуатора", cyl(834, 310, 1421, 10, 289), "act")

# Фильтр, обдув, датчики, подсветка
add("Фильтр_SF_4_угольный", cyl(620, 160, 1875, 100, 450, "x"), "filt")
add("Хомут_фильтра_1", box(700, 145, 1775, 20, 30, 207), "frame")
add("Хомут_фильтра_2", box(1000, 145, 1775, 20, 30, 207), "frame")
add("Обдув_1", box(GROW_X0, 60, 700, 34, 120, 120), "fan")
add("Обдув_2", box(GROW_X1 - 34, 440, 1150, 34, 120, 120), "fan")
add("SensorPro", box(1172, 200, 980, 60, 60, 30), "elec2")
add("Soil_Sensor_1", cyl(700, 180, 250, 8, 150), "elec2")
add("Soil_Sensor_2", cyl(970, 440, 250, 8, 150), "elec2")
add("LED_зелёная_520нм", box(480, 614, 1520, 700, 6, 20), "led")
add("Патрубок_увлажнителя", cyl(400, 120, 1150, 20, 120, "x"), "duct")

# ================= СБОРКА И ЭКСПОРТ =================
asm = cq.Assembly(name="Гроубокс_v3")
solids = []
for name, shape, color, cut, qty, mat in parts:
    asm.add(shape, name=name, color=cq.Color(*color, 1.0))
    solids.append(shape)

compound = Compound = cq.Compound.makeCompound(solids)

step_path = os.path.join(OUT, "growbox_v3.step")
asm.save(step_path)

# ISO-10303-21: не-ASCII символы в именах записываем стандартными эскейпами \X2\...\X0\,
# чтобы КОМПАС/любой CAD гарантированно показал кириллицу в дереве сборки.
def fix_step_unicode(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    # OCC записал кириллицу двойным UTF-8 (latin-1 mojibake) — восстанавливаем
    try:
        text2 = text.encode("latin-1").decode("utf-8")
        text = text2
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        else:
            out.append("\\X2\\%04X\\X0\\" % ord(ch))
    with open(path, "w", encoding="ascii") as f:
        f.write("".join(out))

fix_step_unicode(step_path)
print("STEP:", step_path, os.path.getsize(step_path), "bytes")

stl_path = os.path.join(OUT, "growbox_v3.stl")
try:
    asm.save(stl_path)
except Exception:
    exporters.export(compound, stl_path, tolerance=0.5, angularTolerance=0.3)
print("STL:", stl_path, os.path.getsize(stl_path), "bytes")

# Цветная модель для просмотра/рендера (GLB)
glb_path = os.path.join(OUT, "growbox_v3.glb")
try:
    asm.save(glb_path)
    print("GLB:", glb_path, os.path.getsize(glb_path), "bytes")
except Exception as e:
    print("GLB export failed:", e)

views = {
    "preview_iso.svg": (1.3, -1.6, 1.1),
    "preview_front.svg": (0.05, -1.0, 0.15),
    "preview_side.svg": (1.0, -0.15, 0.12),
    "preview_top.svg": (0.02, -0.02, 1.0),
}
for fn, direction in views.items():
    opt = {
        "width": 1500, "height": 1100, "marginLeft": 30, "marginTop": 30,
        "showAxes": False, "projectionDir": direction,
        "strokeWidth": 0.12, "strokeColor": (30, 30, 30),
        "hiddenColor": (170, 170, 170), "showHidden": False,
    }
    exporters.export(compound, os.path.join(OUT, fn), opt=opt)
    print("SVG:", fn)

# Габаритная проверка
bb = compound.BoundingBox()
print(f"\nBBox: X {bb.xmin:.0f}..{bb.xmax:.0f}  Y {bb.ymin:.0f}..{bb.ymax:.0f}  Z {bb.zmin:.0f}..{bb.zmax:.0f}")

print("\nДеталей в сборке:", len(parts))
for name, *_ in parts:
    print(" -", name)
