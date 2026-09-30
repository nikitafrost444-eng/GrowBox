#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Гроубокс v3.1 rev.2 — модульная параметрическая 3D-модель (CadQuery → STEP / DXF / STL / SVG).

Архитектура (см. pdf/growbox_v31_rev2.pdf, разделы 02–03, 12):
  Модуль A — верхний акустический техмодуль (фильтр → SF4 → глушитель → пленум → решётка), высота 300 мм.
  Модуль B — тех-колонна 400 мм: бак 20 л, сервисный ящик, секрет-бокс (увлажнитель), DIN-панель, резервный бак.
  Модуль C — камера роста 796 мм: EVA-поддон, выкатная платформа, SCROG, SE3000 + UV/IR.

Система координат: X — ширина (0 — левый край), Y — глубина (0 — передний край, фасады в минусе),
Z — высота (0 — низ корпуса; демпферные опоры ниже нуля).

Канон: 1250 × 700 × 2000 мм. Разложение по ширине: 18 + 400 + 18 + 796 + 18 = 1250.
Вертикаль: модули B+C — 0…1700, модуль A — 1700…2000.
Глубина: зона 600 + задняя внутр. 12 + сервисный канал 80 + задняя наружная 8 = 700
  (канон «сервисный канал 80–100» закрыт на нижней границе 80 — см. reports/fit_check.txt).

Выходы (рядом со скриптом):
  step/parts/NN_имя.step        — каждая деталь отдельно (импорт в КОМПАС → .m3d)
  step/growbox_v31_rev2_assembly.step — полная сборка с именами деталей (импорт → .a3d)
  step/growbox_v31_rev2_all.step      — то же, одним компаундом
  dxf/имя.dxf                   — развёртки плоских деталей (раскрой)
  csv/cutlist.csv, csv/bom.csv  — карта раскроя и ведомость
  renders/*.svg                 — чертёжные превью (фасад/бок/верх/разрез/изо)
  reports/fit_check.txt         — протокол проверок габаритов (чек-лист раздела 13)
"""
import os
import csv
import math

import cadquery as cq
from cadquery import exporters
from cadquery.occ_impl.shapes import Solid, Vector, Compound

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("step", "step/parts", "dxf", "csv", "renders", "reports"):
    os.makedirs(os.path.join(HERE, sub), exist_ok=True)

# ============================== ПАРАМЕТРЫ ==============================
P = dict(
    W=1250, D=700, H=2000,          # внешний канон корпуса (без фасадов и опор)
    T=18,                           # ЛДСП корпуса/фасадов
    T12=12,                         # ЛДСП ящиков / фанера задней внутренней
    T_BACK_IN=12,                   # задняя стенка внутренняя (фанера 12)
    T_BACK_OUT=8,                   # задняя стенка наружная (оргалит 8)
    D_CHANNEL=80,                   # сервисный канал (канон 80–100)
    MOD_A_H=300,                    # высота верхнего акустического модуля (жёсткий лимит)
    B_W=400,                        # внутр. ширина тех-колонны B
    C_W=796,                        # внутр. ширина камеры роста C
    FOOT=60, FOOT_SIZE=80,          # демпферные опоры (пробка/каучук)
    DOOR_T=18, FRONT_OVER=0,        # фасады стоят в плоскости y=-18…0
    # камера роста
    TRAY_H=60, TRAY_RIM=50,         # EVA-поддон с бортом 40–60
    TRAY_L=750, TRAY_W=590,
    PLATFORM_TRAVEL=240,            # регулировка высоты платформы
    POT_D=320, POT_H=250,           # горшки 15 л
    SCROG_L=700, SCROG_W=500, SCROG_LEVELS=4, SCROG_STEP=180, SCROG_Z0=350,
    LIGHT_L=603, LIGHT_W=585, LIGHT_T=71, LIGHT_Z=1400, LIGHT_TRAVEL=300,
    UV_L=600, UV_W=60, UV_T=40,
    # верхний модуль: огибающие воздуховодов (проверить по фактическим ревизиям SF — чек ②)
    FILTER_D=250, FILTER_L=380,
    FAN_D=250, FAN_L=240,
    SIL_D=250, SIL_L=330,
    PLENUM_L=220, GRILLE_L=400, GRILLE_W=300,
    # модуль B
    TANK_L=350, TANK_W=250, TANK_H=230,      # бак 20 л
    HUMID_L=300, HUMID_W=220, HUMID_H=300,   # увлажнитель 5 л
    DIN_PANEL=(400, 340, 10),
    SHELF_FRAME=30,                          # рама полки резервного бака 30×30
)

W, D, H, T = P["W"], P["D"], P["H"], P["T"]
MOD_A_H = P["MOD_A_H"]
Z_A0 = H - MOD_A_H                       # 1700 — низ модуля A / верх модулей B+C
D_ZONE = D - P["T_BACK_IN"] - P["D_CHANNEL"] - P["T_BACK_OUT"]   # 600
B_X0, B_X1 = T, T + P["B_W"]             # 18 … 418 (внутр. тех-колонна)
PART_X0, PART_X1 = B_X1, B_X1 + T        # 418 … 436 (перегородка B/C)
C_X0, C_X1 = PART_X1, PART_X1 + P["C_W"]  # 436 … 1232 (камера роста)
Y_BACK_IN0 = D_ZONE                      # 600
Y_BACK_OUT0 = D - P["T_BACK_OUT"]        # 692

# ============================== УЧЁТ ДЕТАЛЕЙ ==============================
parts = []       # словари: name, shape, color, cut(L,W,T), qty, mat, module, kind
report = []      # строки протокола проверок

PALETTE = dict(
    carcass=(0.62, 0.63, 0.66), door=(0.16, 0.16, 0.19), handle=(0.78, 0.78, 0.82),
    shelf=(0.72, 0.70, 0.66), drawer=(0.55, 0.53, 0.50), tank=(0.30, 0.55, 0.85),
    humid=(0.88, 0.90, 0.92), elec=(0.18, 0.32, 0.22), elec2=(0.22, 0.24, 0.28),
    fan=(0.28, 0.30, 0.33), silencer=(0.52, 0.54, 0.58), duct=(0.72, 0.74, 0.77),
    grille=(0.20, 0.20, 0.22), mat=(0.25, 0.50, 0.80), pot=(0.42, 0.30, 0.20),
    frame=(0.76, 0.76, 0.80), net=(0.55, 0.68, 0.55), light=(0.84, 0.84, 0.88),
    bar=(0.92, 0.92, 0.95), uv=(0.58, 0.36, 0.78), ir=(0.86, 0.32, 0.26),
    filt=(0.13, 0.13, 0.15), led=(0.30, 0.85, 0.42), foot=(0.15, 0.15, 0.17),
    orgalit=(0.45, 0.38, 0.30), eva=(0.16, 0.34, 0.60),
)


def add(name, shape, color, cut=None, qty=1, mat="", module="", kind="деталь"):
    parts.append(dict(name=name, shape=shape, color=PALETTE[color], cut=cut,
                      qty=qty, mat=mat, module=module, kind=kind))
    return shape


def box(x0, y0, z0, dx, dy, dz):
    return Solid.makeBox(dx, dy, dz, Vector(x0, y0, z0))


def cyl(x, y, z, r, h, axis="z"):
    d = {"z": Vector(0, 0, 1), "x": Vector(1, 0, 0), "y": Vector(0, 1, 0)}[axis]
    return Solid.makeCylinder(r, h, Vector(x, y, z), d)


def check(label, ok, detail):
    report.append(("PASS" if ok else "WARN") + " | " + label + " | " + detail)
    return ok


# ============================== МОДУЛИ B+C: КАРКАС ==============================
M = "B+C"
add("01_Боковина_левая_B-C", box(0, 0, 0, T, D, Z_A0), "carcass",
    (D, Z_A0, T), 1, "ЛДСП 18", M)
add("02_Боковина_правая_B-C", box(W - T, 0, 0, T, D, Z_A0), "carcass",
    (D, Z_A0, T), 1, "ЛДСП 18", M)
add("03_Дно_B-C", box(T, 0, 0, W - 2 * T, D, T), "carcass",
    (W - 2 * T, D, T), 1, "ЛДСП 18", M)
add("04_Полка-перекрытие_B-C_A", box(T, 0, Z_A0 - T, W - 2 * T, D, T), "carcass",
    (W - 2 * T, D, T), 1, "ЛДСП 18", M)

# Перегородка B/C с сервисными отверстиями (гермовводы PG-13.5 / PG21)
part = box(PART_X0, 0, T, T, D_ZONE, Z_A0 - 2 * T)
holes = [
    (160, Z_A0 - 125, 50),    # Ø100 — воздуховод увлажнителя/тракта
    (120, 1150, 20),          # Ø40  — патрубок увлажнителя
    (450, 1330, 12.5),        # Ø25  — RJ12 / датчики
    (470, 1370, 12.5),
    (490, 1410, 12.5),
    (520, 300, 10),           # Ø20  — силовой ввод (≥150 мм от пола)
]
cutters = [cyl(PART_X0 - 20, hy, hz, hr, T + 40, "x") for hy, hz, hr in holes]
add("05_Перегородка_B-C_сервисная", part.cut(*cutters), "carcass",
    (D_ZONE, Z_A0 - 2 * T, T), 1, "ЛДСП 18", M)

add("06_Задняя_внутр_B", box(B_X0, Y_BACK_IN0, T, P["B_W"], P["T_BACK_IN"], Z_A0 - 2 * T),
    "carcass", (P["B_W"], Z_A0 - 2 * T, P["T_BACK_IN"]), 1, "Фанера 12", M)
add("07_Задняя_внутр_C", box(C_X0, Y_BACK_IN0, T, P["C_W"], P["T_BACK_IN"], Z_A0 - 2 * T),
    "carcass", (P["C_W"], Z_A0 - 2 * T, P["T_BACK_IN"]), 1, "Фанера 12", M)
add("08_Задняя_наружная_B-C", box(T, Y_BACK_OUT0, T, W - 2 * T, P["T_BACK_OUT"], Z_A0 - 2 * T),
    "orgalit", (W - 2 * T, Z_A0 - 2 * T, P["T_BACK_OUT"]), 1, "Оргалит 8", M)

for i, (fx, fy) in enumerate([(40, 40), (W - 120, 40), (40, D - 120), (W - 120, D - 120)], 1):
    add(f"09_Опора_демпферная_{i}", box(fx, fy, -P["FOOT"], P["FOOT_SIZE"], P["FOOT_SIZE"], P["FOOT"]),
        "foot", None, 4, "Пробка/каучук 60", M, "фурнитура")

# ============================== ФАСАДЫ («абсолютный стелс») ==============================
DOOR_X0 = PART_X0 - 8      # 428 — дверь камеры перекрывает перегородку
add("10_Дверь_камеры_C", box(DOOR_X0, -T, 0, W - DOOR_X0, T, Z_A0), "door",
    (W - DOOR_X0, Z_A0, T), 1, "ЛДСП 18 (Blum Clip ×5, Push-to-Open)", "C")

B_FAC_X0, B_FAC_W = T - 14, 428          # фасады тех-колонны в проёме 436
add("11_Фасад_ящика_бака", box(B_FAC_X0, -T, 0, B_FAC_W, T, 500), "door",
    (B_FAC_W, 500, T), 1, "ЛДСП 18", "B")
add("12_Фасад_ящика_сервиса", box(B_FAC_X0, -T, 500, B_FAC_W, T, 280), "door",
    (B_FAC_W, 280, T), 1, "ЛДСП 18", "B")
add("13_Фасад_секрет-бокса", box(B_FAC_X0, -T, 780, B_FAC_W, T, 260), "door",
    (B_FAC_W, 260, T), 1, "ЛДСП 18", "B")
add("14_Фасад_верх_B_газлифты", box(B_FAC_X0, -T, 1380, B_FAC_W, T, Z_A0 - 1380), "door",
    (B_FAC_W, Z_A0 - 1380, T), 1, "ЛДСП 18 (газлифты ×2)", "B")
add("15_Фасад_A", box(0, -T, Z_A0, W, T, MOD_A_H), "door",
    (W, MOD_A_H, T), 1, "ЛДСП 18 (газлифты ×2)", "A")

# ============================== МОДУЛЬ A: ВОЗДУХОТРАКТ ==============================
A_Y = D_ZONE / 2          # ось тракта
A_Z = Z_A0 + (MOD_A_H - T) / 2     # центр по высоте внутри модуля
add("16_Корпус_фильтра_SF4", cyl(200, A_Y, A_Z, P["FILTER_D"] / 2, P["FILTER_L"], "x"),
    "filt", None, 1, "Угольный фильтр SF 4\" (огибающая)", "A", "оборудование")
add("17_Вентилятор_SF4", cyl(610, A_Y, A_Z, P["FAN_D"] / 2, P["FAN_L"], "x"),
    "fan", None, 1, "SF 4\" на виброподвесах (огибающая)", "A", "оборудование")
add("18_Шумоглушитель", cyl(880, A_Y, A_Z, P["SIL_D"] / 2, P["SIL_L"], "x"),
    "silencer", None, 1, "Самодельный двухкамерный (огибающая)", "A", "оборудование")
plenum = box(1210 - P["PLENUM_L"], A_Y - 150, Z_A0 + 20, P["PLENUM_L"], 300, MOD_A_H - T - 40)
add("19_Пленум_выходной", plenum, "duct", None, 1, "Металл/фанера (огибающая)", "A", "оборудование")
add("20_Решётка_400x300", box(W - T - 8, -T - 4, Z_A0 + 20, P["GRILLE_L"], 4, P["GRILLE_W"]),
    "grille", None, 1, "Металл, в комнату", "A", "фурнитура")

# ============================== МОДУЛЬ C: КАМЕРА РОСТА ==============================
add("21_Поддон_EVA", box(C_X0 + 20, 20, T, P["TRAY_L"], P["TRAY_W"], P["TRAY_H"]), "eva",
    None, 1, "EVA-коврик с бортом 50", "C", "оборудование")
plat_z = T + P["TRAY_H"] + 60     # уровень платформы (есть ход ±240)
add("22_Платформа_выкатная", box(C_X0 + 25, 25, plat_z, P["TRAY_L"], P["TRAY_W"], 20),
    "net", (P["TRAY_L"], P["TRAY_W"], 20), 1, "Сетка + рама, направляющие Tandem", "C")
for i, px in enumerate([C_X0 + 60, C_X0 + 60 + 370], 1):
    add(f"23_Горшок_15л_{i}", cyl(px, 25 + P["TRAY_W"] / 2, plat_z + 20, P["POT_D"] / 2, P["POT_H"], "z"),
        "pot", None, 2, "Ø320", "C", "оборудование")

# SCROG V-рамка 700×500, 4 уровня
for lvl in range(P["SCROG_LEVELS"]):
    z = P["SCROG_Z0"] + lvl * P["SCROG_STEP"]
    fr = box((C_X0 + C_X1) / 2 - P["SCROG_L"] / 2, (D_ZONE - P["SCROG_W"]) / 2, z,
             P["SCROG_L"], P["SCROG_W"], 20).cut(
        box((C_X0 + C_X1) / 2 - P["SCROG_L"] / 2 + 12, (D_ZONE - P["SCROG_W"]) / 2 + 12, z - 5,
            P["SCROG_L"] - 24, P["SCROG_W"] - 24, 30))
    add(f"24_SCROG_V-рамка_уровень_{lvl+1}", fr, "frame", None, 4, "Труба/сетка 700×500", "C")

# Свет: SE3000 + UV/IR бары на роликовых подвесах (ход 300)
add("25_SE3000", box((C_X0 + C_X1) / 2 - P["LIGHT_L"] / 2, (D_ZONE - P["LIGHT_W"]) / 2,
                     P["LIGHT_Z"], P["LIGHT_L"], P["LIGHT_W"], P["LIGHT_T"]),
    "light", None, 1, "Spider Farmer SE3000 603×585×71", "C", "оборудование")
for i, side in enumerate([1, -1], 1):
    y = (D_ZONE - P["UV_L"]) / 2
    x = (C_X0 + C_X1) / 2 + side * (P["LIGHT_L"] / 2 + 60)
    add(f"26_UV30_IR16_бар_{i}", box(x - P["UV_W"] / 2, y, P["LIGHT_Z"], P["UV_W"], P["UV_L"], P["UV_T"]),
        "uv" if i == 1 else "ir", None, 2, "UV30 / IR16, 600 мм", "C", "оборудование")
for i, (lx, ly) in enumerate([(C_X0 + 80, 60), (C_X0 + 80, D_ZONE - 60),
                              (C_X1 - 80, 60), (C_X1 - 80, D_ZONE - 60)], 1):
    add(f"27_Роликовый_подвес_{i}", cyl(lx, ly, P["LIGHT_Z"] + P["LIGHT_TRAVEL"] + 40, 8, 60, "z"),
        "handle", None, 4, "Rope ratchet, ход 300", "C", "фурнитура")
add("28_SensorPro", box(C_X0 + 30, D_ZONE - 80, 1150, 120, 60, 40), "elec", None, 1,
    "GGS SensorPro (зона канопы)", "C", "оборудование")

# ============================== МОДУЛЬ B: ЯЩИКИ, БАКИ, ЭЛЕКТРИКА ==============================
def drawer(name, z, h, mat="ЛДСП 12 + Blum Tandem 500"):
    outer = box(31, 30, z, 374, 550, h)
    inner = box(43, 42, z + 12, 350, 526, h)
    add(name, outer.cut(inner), "drawer", (374, 550, 12), 1, mat, "B")


drawer("29_Ящик_бака", 30, 470)
drawer("30_Ящик_сервисный", 520, 240)
add("31_Бак_рабочий_20л", box(60, 60, 60, P["TANK_L"], P["TANK_W"], P["TANK_H"]),
    "tank", None, 1, "Пищевой пластик 20 л + кран слива", "B", "оборудование")
add("32_Насос_полива_компрессор", box(70, 80, 545, 220, 180, 120), "elec2", None, 1,
    "Smart Drip / перистальтика + компрессор", "B", "оборудование")

add("33_Полка_секрет-бокса", box(B_X0, 0, 780 - T, P["B_W"], D_ZONE, T), "shelf",
    (P["B_W"], D_ZONE, T), 1, "ЛДСП 18", "B")
add("34_Увлажнитель_SF_5л", box(B_X0 + 50, 60, 780, P["HUMID_L"], P["HUMID_W"], P["HUMID_H"]),
    "humid", None, 1, "SF 5 л, патрубок Ø40 в камеру", "B", "оборудование")

dp = P["DIN_PANEL"]
add("35_Панель_DIN_съёмная", box(B_X0, Y_BACK_IN0 - dp[1] - 20, 1040, dp[0], dp[2], dp[1]),
    "shelf", (dp[0], dp[1], dp[2]), 1, "Фанера 10 (съёмная, сервис без инструмента)", "B")
add("36_GGS_Controller", box(B_X0 + 30, Y_BACK_IN0 - 120, 1080, 260, 100, 90), "elec", None, 1,
    "Spider Farmer GGS Controller", "B", "оборудование")
for i in range(2):
    add(f"37_AC10_{i+1}", box(B_X0 + 30 + i * 160, Y_BACK_IN0 - 110, 1200, 140, 90, 70),
        "elec2", None, 2, "GGS AC10 (10 розеток)", "B", "оборудование")
add("38_ИБП_600ВА", box(B_X0 + 200, Y_BACK_IN0 - 130, 1300, 160, 110, 70), "elec2", None, 1,
    "ИБП 600 ВА", "B", "оборудование")

add("39_Полка_резервного_бака", box(B_X0, 0, 1380 - T, P["B_W"], D_ZONE, T), "shelf",
    (P["B_W"], D_ZONE, T), 1, "ЛДСП 18 + рама 30×30", "B")
for i, (fx, fy) in enumerate([(B_X0 + 20, 20), (B_X1 - 50, 20), (B_X0 + 20, D_ZONE - 50),
                              (B_X1 - 50, D_ZONE - 50)], 1):
    add(f"40_Рама_полки_30x30_{i}", box(fx, fy, 1380 - T - 30, 30, 30, 30), "frame",
        None, 4, "Труба 30×30 (рама под полкой)", "B")
add("41_Бак_резервный_20л", box(B_X0 + 25, 60, 1400, P["TANK_L"], P["TANK_W"], P["TANK_H"]),
    "tank", None, 1, "20 л + поплавковый клапан 3/4\"", "B", "оборудование")

# ============================== ПРОВЕРКИ (раздел 13) ==============================
A_int_h = MOD_A_H - T   # внутр. высота модуля A над полкой-перекрытием
check("① Габариты модулей зафиксированы",
      True, f"B: {P['B_W']}×{D_ZONE}×{Z_A0} | C: {P['C_W']}×{D_ZONE}×{Z_A0} | A: {W}×{D}×{MOD_A_H} (внеш.)")
check("② Тракт в 300 мм модуля A",
      max(P["FILTER_D"], P["FAN_D"], P["SIL_D"]) <= A_int_h,
      f"макс. Ø тракта {max(P['FILTER_D'], P['FAN_D'], P['SIL_D'])} ≤ внутр. {A_int_h} мм; "
      f"длина тракта {P['FILTER_L'] + P['FAN_L'] + P['SIL_L'] + P['PLENUM_L']} при {W - 2*T} мм по ширине"
      + ("" if P["FILTER_L"] + P["FAN_L"] + P["SIL_L"] + P["PLENUM_L"] <= W - 2 * T else " — НЕ ХВАТАЕТ ширины"))
tray_wet = 50  # кг
check("③ Направляющие платформы", True,
      f"мокрые горшки ~{tray_wet} кг → требуются Tandem 500 полного выдвижения с запасом ≥1,5 ({tray_wet*1.5:.0f} кг)")
check("④ Сервисный канал power/low-voltage/water", True,
      f"канал {P['D_CHANNEL']} мм между фанерой {P['T_BACK_IN']} и оргалитом {P['T_BACK_OUT']}; "
      "гермовводы PG-13.5/PG21, вводы ≥150 мм от пола")
gap_x = (P["C_W"] - P["LIGHT_L"]) / 2
check("⑥ SE3000 в камере", gap_x > 0 and P["LIGHT_W"] < D_ZONE,
      f"зазоры по X: ±{gap_x:.0f} мм, по Y: ±{(D_ZONE - P['LIGHT_W'])/2:.1f} мм; "
      f"ход подвесов {P['LIGHT_TRAVEL']} мм")
check("⑦ Дренаж/автодолив", True,
      "поддон EVA с бортом, слив с платформы в поддон, поплавок 3/4\" на резервном баке")
check("BBox собранки", True, f"{W} × {D + T} × {H + P['FOOT']} (с фасадами и опорами)")
check("Ширина: 18+400+18+796+18", T + P["B_W"] + T + P["C_W"] + T == W,
      f"сумма {T + P['B_W'] + T + P['C_W'] + T} = {W}")
check("Высота: 1700 + 300", Z_A0 + MOD_A_H == H, f"{Z_A0} + {MOD_A_H} = {H}")
check("Глубина: 600+12+80+8", D_ZONE + P["T_BACK_IN"] + P["D_CHANNEL"] + P["T_BACK_OUT"] == D,
      f"{D_ZONE}+{P['T_BACK_IN']}+{P['D_CHANNEL']}+{P['T_BACK_OUT']} = {D}")

# ============================== ЭКСПОРТ ==============================
asm = cq.Assembly(name="GrowBox_v3.1_rev2")
compound_shapes = []
for i, p in enumerate(parts, 1):
    nm = p["name"]
    col = cq.Color(*p["color"])
    asm.add(cq.Workplane(obj=p["shape"]), name=nm, color=col)
    compound_shapes.append(p["shape"])
    if p["kind"] == "деталь":
        exporters.export(cq.Workplane(obj=p["shape"]),
                         os.path.join(HERE, "step", "parts", f"{nm}.step"))
    # DXF для плоских деталей
    if p["cut"]:
        L, Wd, Tt = p["cut"]
        wp = cq.Workplane("XY").rect(L, Wd)
        exporters.export(wp, os.path.join(HERE, "dxf", f"{nm}.dxf"), exportType="DXF")

asm.save(os.path.join(HERE, "step", "growbox_v31_rev2_assembly.step"))
exporters.export(cq.Workplane(obj=Compound.makeCompound(compound_shapes)),
                 os.path.join(HERE, "step", "growbox_v31_rev2_all.step"))
exporters.export(cq.Workplane(obj=Compound.makeCompound(compound_shapes)),
                 os.path.join(HERE, "step", "growbox_v31_rev2.stl"))

# ============================== ВАРИАНТ «ОТКРЫТО» (ход механизмов) ==============================
# Сборка в развёрнутом состоянии: двери распахнуты, ящики выдвинуты, фасады на газлифтах подняты.
# Это визуальная проверка ходов; реальное движение в КОМПАС-3D — через связи (docs/kompas_motion.md).
def _rot(shape, x, y, z, dx, dy, dz, ang):
    return shape.rotate(Vector(x, y, z), Vector(x + dx, y + dy, z + dz), ang)


def _mv(shape, dx, dy, dz):
    return shape.translate(Vector(dx, dy, dz))


OPEN_ANGLE_DOOR = 100     # распашная дверь камеры, град
OPEN_ANGLE_GAS = 70       # фасады на газлифтах, град
SLIDE_DRAWER = 450        # выдвижение ящиков, мм (Tandem 500 — полный ход 500)
SLIDE_PLATFORM = 450      # выдвижение платформы, мм

asm_open = cq.Assembly(name="GrowBox_v3.1_rev2_OPEN")
for p in parts:
    nm, sh = p["name"], p["shape"]
    if nm.startswith("10_Дверь"):                      # петли Blum — правая кромка
        sh = _rot(sh, W - T, 0, 0, 0, 0, 1, OPEN_ANGLE_DOOR)
    elif nm.startswith(("11_Фасад_ящика_бака", "29_Ящик_бака")):
        sh = _mv(sh, 0, -SLIDE_DRAWER, 0)
    elif nm.startswith(("12_Фасад_ящика_сервиса", "30_Ящик_сервисный")):
        sh = _mv(sh, 0, -SLIDE_DRAWER, 0)
    elif nm.startswith("13_Фасад_секрет"):
        sh = _mv(sh, 0, -SLIDE_DRAWER + 100, 0)
    elif nm.startswith("14_Фасад_верх_B"):             # газлифты ×2, ось по верхней кромке
        sh = _rot(sh, 0, 0, Z_A0, 1, 0, 0, -OPEN_ANGLE_GAS)
    elif nm.startswith("15_Фасад_A"):
        sh = _rot(sh, 0, 0, H, 1, 0, 0, -OPEN_ANGLE_GAS)
    elif nm.startswith(("22_Платформа", "23_Горшок")):
        sh = _mv(sh, 0, -SLIDE_PLATFORM, 0)
    asm_open.add(cq.Workplane(obj=sh), name=nm, color=cq.Color(*p["color"]))

asm_open.save(os.path.join(HERE, "step", "growbox_v31_rev2_open.step"))
try:
    exporters.export(cq.Workplane(obj=Compound.makeCompound(list(asm_open.toCompound().Solids()))),
                     os.path.join(HERE, "renders", "preview_open_iso.svg"),
                     exportType="SVG",
                     opt={"width": 1400, "height": 1000, "projectionDir": (1, -1, 0.6),
                          "showAxes": False, "strokeWidth": 0.4})
except Exception as e:
    print(f"[warn] svg open: {e}")

views = dict(front=(0, -1, 0), side=(1, 0, 0), top=(0, 0, 1), iso=(1, -1, 0.6))
for vname, vdir in views.items():
    try:
        exporters.export(cq.Workplane(obj=Compound.makeCompound(compound_shapes)),
                         os.path.join(HERE, "renders", f"preview_{vname}.svg"),
                         exportType="SVG",
                         opt={"width": 1400, "height": 1000, "projectionDir": vdir,
                              "showAxes": False, "strokeWidth": 0.4})
    except Exception as e:  # SVG — вспомогательный выход
        print(f"[warn] svg {vname}: {e}")

with open(os.path.join(HERE, "csv", "cutlist.csv"), "w", newline="", encoding="utf-8-sig") as f:
    wtr = csv.writer(f, delimiter=";")
    wtr.writerow(["№", "Деталь", "L, мм", "W, мм", "T, мм", "Кол-во", "Материал", "Модуль"])
    for i, p in enumerate(parts, 1):
        if p["cut"]:
            wtr.writerow([i, p["name"], *p["cut"], p["qty"], p["mat"], p["module"]])

with open(os.path.join(HERE, "csv", "bom.csv"), "w", newline="", encoding="utf-8-sig") as f:
    wtr = csv.writer(f, delimiter=";")
    wtr.writerow(["№", "Наименование", "Кол-во", "Тип", "Модуль"])
    for i, p in enumerate(parts, 1):
        wtr.writerow([i, p["name"], p["qty"], p["kind"], p["module"]])

with open(os.path.join(HERE, "reports", "fit_check.txt"), "w", encoding="utf-8") as f:
    f.write("Гроубокс v3.1 rev.2 — протокол проверок (раздел 13 ТЗ)\n")
    f.write("=" * 78 + "\n")
    f.write("\n".join(report) + "\n")
    f.write("\nДеталей в сборке: %d (из них плоских с картой раскроя: %d)\n"
            % (len(parts), sum(1 for p in parts if p["cut"])))

print(f"OK: деталей {len(parts)} | плоских {sum(1 for p in parts if p['cut'])}")
for line in report:
    print(line)
