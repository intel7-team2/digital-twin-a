"""Figures for the mid-progress report (docs/report): system structure, process v2 flow, Factory I/O scene screenshot.

Usage: python make_report_figures.py <out dir> <scene screenshot (webp/png)>  (needs Pillow, Windows Malgun Gothic)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
SCENE = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
F = "C:/Windows/Fonts/malgun.ttf"
FB = "C:/Windows/Fonts/malgunbd.ttf"
NAVY, GREEN, INK, MUTED, LINE, PAPER, AMBER = "#1B2A41", "#22B573", "#2E3A4D", "#56627A", "#AEB8C4", "#FFFFFF", "#B45A0C"
GREEN_BG, GREY_BG = "#E8F6EF", "#F2F4F6"


def font(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def box(d, x, y, w, h, title, sub="", fill=PAPER, edge=LINE, tcol=NAVY):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill, outline=edge, width=3)
    ft, fs = font(30, True), font(22)
    tw = d.textlength(title, font=ft)
    n = len(sub.split("\n")) if sub else 0
    block = 34 + (8 + 28 * n if n else 0)
    ty = y + (h - block) / 2 - 4
    d.text((x + (w - tw) / 2, ty), title, font=ft, fill=tcol)
    if sub:
        for i, line in enumerate(sub.split("\n")):
            sw = d.textlength(line, font=fs)
            d.text((x + (w - sw) / 2, ty + 42 + i * 28), line, font=fs, fill=MUTED)


def arrow(d, x1, y1, x2, y2, col=MUTED, both=False):
    d.line([x1, y1, x2, y2], fill=col, width=4)

    def head(xa, ya, xb, yb):
        import math
        ang = math.atan2(yb - ya, xb - xa)
        L = 16
        pts = [(xb, yb), (xb - L * math.cos(ang - 0.45), yb - L * math.sin(ang - 0.45)),
               (xb - L * math.cos(ang + 0.45), yb - L * math.sin(ang + 0.45))]
        d.polygon(pts, fill=col)
    head(x1, y1, x2, y2)
    if both:
        head(x2, y2, x1, y1)


def label(d, x, y, text, size=22, col=MUTED, bold=False):
    d.text((x, y), text, font=font(size, bold), fill=col)


def system():
    W, H = 1800, 900
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    label(d, 60, 40, "제어 (PLC 쪽)", 26, NAVY, True)
    box(d, 60, 90, 360, 130, "Factory I/O", "가상 전공정 씬")
    box(d, 620, 90, 420, 130, "브리지 (Python)", "Modbus TCP · MX Component\nPLC에 쓰는 프로그램은 하나")
    box(d, 1240, 90, 500, 130, "PLC 래더", "MELSEC Q03UDE · GX Works2\nGX Simulator2")
    arrow(d, 420, 155, 620, 155, both=True)
    arrow(d, 1040, 155, 1240, 155, both=True)
    box(d, 620, 300, 420, 110, "2A HMI", "운전·정지·기준값·알람 확인")
    arrow(d, 830, 300, 830, 220, both=True)
    label(d, 60, 480, "기록 (DB 쪽)", 26, GREEN, True)
    box(d, 60, 520, 360, 150, "수집기", "PLC 메일박스 읽기\n로컬 저장 후 전송", GREEN_BG, GREEN)
    box(d, 500, 520, 330, 150, "API", "FastAPI · HTTPS\nAPI 키", GREEN_BG, GREEN)
    box(d, 910, 520, 400, 150, "PostgreSQL 16", "Oracle Cloud VM\n2A · 팩 라인 공용", GREEN_BG, GREEN)
    box(d, 1390, 520, 350, 150, "Grafana SCADA", "읽기 전용 조회")
    arrow(d, 420, 595, 500, 595, GREEN)
    arrow(d, 830, 595, 910, 595, GREEN)
    arrow(d, 1390, 595, 1310, 595, MUTED)
    d.line([1490, 220, 1490, 460], fill=GREEN, width=4)
    d.line([1490, 460, 240, 460], fill=GREEN, width=4)
    arrow(d, 240, 460, 240, 520, GREEN)
    label(d, 1080, 425, "이벤트 메일박스 (D2700~, 제안)", 22, GREEN)
    box(d, 910, 740, 400, 100, "팩 라인 (2B)", "같은 DB에 쓰고 읽음", GREY_BG)
    arrow(d, 1110, 740, 1110, 670, MUTED, both=True)
    label(d, 60, 760, "DB가 멈춰도 라인은 HMI로 조작 (DB를 거치지 않음)", 24, MUTED)
    im.save(OUT / "system.png")


def process():
    W, H = 2000, 760
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    y, h = 260, 140
    xs = [(40, 200, "투입", "2A-IN"), (290, 220, "1차 비전", "ID 부여"), (560, 220, "2차 비전", "외관 판정"),
          (870, 300, "검사기 ×4", "T1~T4 병렬\n전압·저항"), (1260, 230, "ID 재확인", "2A-IDC"),
          (1580, 200, "분류", "A·B·C")]
    for x, w, t, s in xs:
        box(d, x, y, w, h, t, s, GREEN_BG if t.startswith("검사기") else PAPER, GREEN if t.startswith("검사기") else LINE)
    for (x1, w1, *_), (x2, *_r) in zip(xs, xs[1:]):
        arrow(d, x1 + w1, y + h / 2, x2, y + h / 2)
    # NG branches
    box(d, 560, 520, 220, 100, "외관 NG 배출", "2A-RJ1", GREY_BG)
    arrow(d, 670, y + h, 670, 520, AMBER)
    box(d, 1420, 40, 230, 110, "재검", "2A-RT (1회)", GREY_BG)
    arrow(d, 1680, y, 1620, 150, AMBER)          # 미분류 → 재검
    arrow(d, 1460, 150, 1400, y, MUTED)          # 재검 통과 → ID 재확인
    box(d, 1730, 40, 250, 110, "최종 NG 배출", "2A-RJ2", GREY_BG)
    arrow(d, 1650, 95, 1730, 95, AMBER)          # 재검 NG → 배출
    # lanes and box
    box(d, 1820, 230, 160, 230, "레인", "A · B · C\n→ 박스 4셀\n→ 2B 인계")
    arrow(d, 1780, y + h / 2, 1820, y + h / 2)
    label(d, 40, 660, "주황 화살표 = 불합격·재검 경로.  11/23 미팅 기준 (docs/2a-data-design.md)", 24, MUTED)
    im.save(OUT / "process.png")


def scene():
    im = Image.open(SCENE).convert("RGB")
    im.save(OUT / "scene.png")


system()
process()
scene()
print("ok", sorted(p.name for p in OUT.iterdir()))
