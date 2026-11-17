"""Draw a sectioned top-view equipment concept, without fabrication dimensions."""
from pathlib import Path

out = Path(__file__).resolve().parents[1] / 'assets/line-top-v0.13.svg'
s = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="380" viewBox="0 0 1100 380" role="img" aria-label="입고, 검사, NG 분리 및 구간별 버퍼, 공급 구역으로 나눈 평면 배치 개념도">
<defs><marker id="flow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#315e8e"/></marker><pattern id="reject" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M-2 2L2 -2M0 8L8 0M6 10L10 6" stroke="#c2cad3" stroke-width="1"/></pattern></defs>
<rect width="1100" height="380" fill="white"/>
<g font-family="Malgun Gothic,sans-serif" fill="#233b54">''']

def rect(x,y,w,h,fill,stroke='#bac8d7',r=3):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')

def text(x,y,value,size=18,weight=400,anchor='middle',color='#233b54'):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{value}</text>')

def arrow(path):
    s.append(f'<path d="{path}" fill="none" stroke="#315e8e" stroke-width="2.5" marker-end="url(#flow)"/>')

for x,w,title in [(10,175,'01  입고'),(195,190,'02  검사'),(395,465,'03  분류·버퍼'),(870,220,'04  공급')]:
    rect(x,10,w,355,'#f5f8fc' if x in (195,870) else '#fafbfc','#d1dbe6',5)
    text(x+14,42,title,22,700,'start')

# Main line and top-view equipment symbols.
rect(35,105,805,54,'#e0e7ed','#7c91a5')
for x in range(43,830,16):
    s.append(f'<path d="M{x} 109V155" stroke="#c4ced8"/>')
rect(42,113,35,38,'#6885a4','#486888')
text(110,84,'셀 투입·ID',18)
for x in (105,148,225):
    s.append(f'<circle cx="{x}" cy="132" r="9" fill="white" stroke="#6d8399" stroke-width="2"/>')
rect(257,91,66,80,'none','#315e8e')
rect(276,111,29,42,'#c1d3e7','#315e8e')
text(290,80,'LOT·검사값',18)
text(290,201,'판정 후 이동',18)
arrow('M166 132H205')
arrow('M330 132H370')

# Reject branch, distinct from the three grade storage lanes.
rect(417,159,38,88,'#e4e9ef','#8b9baa')
rect(408,250,56,49,'url(#reject)','#8b9baa')
rect(420,82,34,16,'#91aac5','#315e8e')
arrow('M436 168V231')
text(436,325,'NG 격리',17,700)

# Three independent lanes and a shared output collector.
for x,grade in [(535,'A'),(665,'B'),(795,'C')]:
    rect(x-17,82,34,16,'#91aac5','#315e8e')
    rect(x-24,159,48,125,'#e0e7ed','#7c91a5')
    text(x,76,f'{grade} 구간',18,700)
    for y in (182,207,232,257):
        s.append(f'<circle cx="{x}" cy="{y}" r="7" fill="white" stroke="#6d8399" stroke-width="1.7"/>')
    rect(x-26,279,52,7,'#315e8e','#315e8e',0)
    arrow(f'M{x} 164V173')
    arrow(f'M{x} 288V306')
rect(497,309,548,36,'#dce6f0','#7c91a5')
for x in (570,700,830,988): arrow(f'M{x} 327h40')
text(665,366,'한 레인씩 배출',17)
text(980,200,'동일 구간',19,700)
text(980,228,'4셀 단위',19,700)
text(980,273,'수신 확인',18)
text(980,297,'후 다음 세트',18)

s.append('</g></svg>')
out.write_text(''.join(s),encoding='utf-8')
print('Created',out.name)
