"""Figures for the hwp plan (v0.17~): process flow, system diagram, schedule.

Writes one HTML page per figure into docs/assets/hwp/; render_figures.cjs turns them into PNG.
The Factory I/O screenshot is cropped from a capture passed as the first argument (optional).
"""
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[2]          # docs/
OUT = BASE / 'assets' / 'hwp'
OUT.mkdir(parents=True, exist_ok=True)


def svg_start(w, h, label):
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}">'
            f'<defs><marker id="a" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto-start-reverse">'
            f'<path d="M0 0L7 3.5L0 7" fill="#525252"/></marker></defs><rect width="{w}" height="{h}" fill="white"/>')


def box(x, y, w, h, title, lines=(), owned=False):
    border = '#4a78a8' if owned else '#9aa6b2'
    fill = '#eef4fb' if owned else '#ffffff'
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}" stroke="{border}" stroke-width="1.6"/>'
    top = y + h / 2 - (len(lines) * 20) / 2 + 6
    s += f'<text x="{x + w / 2}" y="{top}" text-anchor="middle" font-size="17" font-weight="700" fill="#183b60">{title}</text>'
    for i, line in enumerate(lines):
        s += f'<text x="{x + w / 2}" y="{top + 22 + i * 20}" text-anchor="middle" font-size="14" fill="#384a5b">{line}</text>'
    return s


def arrow(d, dashed=False, both=False, color='#525252'):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" marker-end="url(#a)"'
            + (' marker-start="url(#a)"' if both else '') + (' stroke-dasharray="5 4"' if dashed else '') + '/>')


def label(x, y, text, size=13, color='#444'):
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" fill="{color}">{text}</text>'


def page(name, body, width):
    html = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>'
            'body{margin:0;background:white;font-family:"Malgun Gothic",sans-serif}'
            f'#fig{{display:inline-block;width:{width}px}}svg{{display:block;font-family:"Malgun Gothic",sans-serif}}'
            'table{border-collapse:collapse;font-size:14px}th,td{border:1px solid #8a96a3;padding:7px 4px;text-align:center}'
            'th{background:#eef1f5;font-weight:700}td.task{text-align:left;padding-left:10px;white-space:nowrap}'
            'td.on{background:#cfe0f5}td.gate{background:#f3d9b8;font-weight:700;color:#7a4a12}'
            '.legend{font-size:13px;color:#444;margin-top:8px}'
            f'</style></head><body><div id="fig">{body}</div></body></html>')
    (OUT / f'{name}.html').write_text(html, encoding='utf-8')


# 1. Process flow: one centerline (y=155) so every branch meets cleanly.
p = svg_start(720, 370, '입고, 검사, NG 격리, A B C 구간 버퍼와 4셀 세트 공급으로 이어지는 공정 흐름')
p += box(10, 115, 115, 80, 'Z1 입고', ['셀 ID · LOT'])
p += box(175, 115, 125, 80, 'Z2 검사', ['전압 · 저항 판정'])
for y, g in [(10, 'A'), (115, 'B'), (220, 'C')]:
    p += box(365, y, 130, 80, f'{g}구간 버퍼', ['Z4 · 레인 재고'], True)
    c = y + 40
    p += arrow(f'M300 155H330V{c}H365' if c != 155 else 'M300 155H365')
    p += arrow(f'M495 {c}H530V155H570' if c != 155 else 'M495 155H570')
p += box(570, 115, 140, 80, 'Z5 세트 공급', ['같은 구간 4셀'], True)
p += box(175, 280, 160, 70, 'Z3 NG 격리', ['NG · 보류 LOT'])
p += arrow('M125 155H175') + arrow('M237 195V280')
p += label(530, 318, 'LOT별 NG 3건 → 그 LOT 공급 보류') + label(530, 340, '조립 설비 준비 · 수신 확인 후 다음 세트')
page('fig-process', p + '</svg>', 720)

# 2. System diagram: SCADA is the box title, Python is its sub-heading.
a = svg_start(720, 492, '실물 설비, PLC, Factory I/O, SCADA, DB, 조회 화면과 2B 연계를 보여 주는 시스템 구성도')
a += box(10, 20, 190, 90, '검사 · 비전', ['실측 전압 · 판독 결과'])
a += box(265, 20, 190, 90, 'MELSEC Q PLC', ['래더 · 인터록', '셀 추적 · 세트 공급'], True)
a += box(520, 20, 190, 90, '조립 · 검사 설비', ['로봇 · 실물 라인'])
a += arrow('M200 65H265', True) + arrow('M455 65H520', True, True)
a += label(488, 128, '준비 · 요청 · 수신 확인')
a += box(10, 215, 305, 100, 'Factory I/O · 가상 전공정', ['센서 · 컨베이어 · 푸셔 · 블레이드', '입고 → 검사 → 분류 → 4셀 공급'], True)
a += box(395, 215, 315, 100, 'SCADA', ['Python · 수집 및 통신', '셀 · 세트 상태 · 알람 · 이력'], True)
a += arrow('M330 110V160H160V215', True, True) + label(250, 180, '센서값 ↑ / 구동 명령 ↓')
a += arrow('M390 110V170H550V215', True, True) + label(640, 195, '상태 · 판정 · 공급 이벤트')
a += box(395, 385, 145, 70, 'DB', ['셀 · 세트 · 시험'], True) + box(565, 385, 145, 70, '조회 화면', ['상태 · 알람 · 이력'], True)
a += arrow('M467 315V385') + arrow('M637 315V385') + arrow('M540 420H565')
a += box(10, 385, 305, 70, '2B · 후공정 연계', ['세트 ID · 셀 ID · LOT · 검사 결과'])
a += arrow('M315 420H395', True, True)
a += label(360, 482, '파란 상자: 2A 범위 · 점선: 통신 · 인터록', 12, '#555')
page('fig-system', a + '</svg>', 720)

# 3. Schedule (gantt). 1 = work, G = gate.
days = ['11/17', '18', '19', '23', '24', '25', '26', '27', '30', '12/1']
rows = [
    ('계획 확정 · I/O 리스트 (G1)', '11G.......'),
    ('실물 셀 전압 실측', '.11.......'),
    ('Factory I/O 씬 배치 (G2)', '..111G....'),
    ('입고 · 검사 · NG 래더', '...111....'),
    ('분류 · 버퍼 · 세트 공급 래더', '....111...'),
    ('브리지 · 수집기 · DB · 화면', '...11111..'),
    ('통합 연결 · 첫 측정 (G3)', '......1G..'),
    ('비정상 상황 시험 · 기능 동결', '........G.'),
    ('시연 · 발표', '.........G'),
]
cells = {'1': '<td class="on"></td>', 'G': '<td class="gate">◆</td>', '.': '<td></td>'}
g = '<table><tr><th style="width:230px">작업</th>' + ''.join(f'<th style="width:46px">{d}</th>' for d in days) + '</tr>'
g += ''.join(f'<tr><td class="task">{t}</td>' + ''.join(cells[c] for c in bar) + '</tr>' for t, bar in rows) + '</table>'
g += '<div class="legend">■ 수행 기간 · ◆ 관문 (G1 설계 확정 · G2 구역 단독 동작 · G3 전체 연결)</div>'
page('fig-schedule', g, 700)

# 4. Zoned top-view layout (drawn by docs/tools/draw_line_top.py).
page('fig-layout', (BASE / 'assets' / 'line-top-v0.14.svg').read_text(encoding='utf-8'), 1100)

# 5. Factory I/O screenshot: crop the 3D view out of a full-window capture.
if len(sys.argv) > 1:
    from PIL import Image
    im = Image.open(sys.argv[1]).convert('RGB')
    w, h = im.size
    im.crop((int(w * 0.07), int(h * 0.37), int(w * 0.78), int(h * 0.89))).save(OUT / 'fig-factoryio.png', optimize=True)

print('figures ->', OUT)
