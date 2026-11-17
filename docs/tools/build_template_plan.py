"""Rebuild the project plan using the supplied HWP form's section order."""
from pathlib import Path
import zlib

BASE=Path(__file__).resolve().parents[1]
ASSETS=BASE/'assets'
ASSETS.mkdir(exist_ok=True)
if not (ASSETS/'institution-logo.png').exists():
    import sys
    from read_hwp import Compound
    if len(sys.argv)<2:
        raise SystemExit('Pass the reference HWP path when institution-logo.png is missing.')
    reference=Compound(sys.argv[1])
    logo=reference.read(next(e for e in reference.entries if e['name']=='BIN0001.png'))
    try:
        logo=zlib.decompress(logo,-15)
    except zlib.error:
        pass
    (ASSETS/'institution-logo.png').write_bytes(logo)

def table(headers, rows, widths=None, cls=''):
    cols='<colgroup>'+''.join(f'<col style="width:{x}%">' for x in widths)+'</colgroup>' if widths else ''
    return f'<table class="{cls}">{cols}<thead><tr>'+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table>'

def page(content,n,cls=''):
    return f'<section class="page {cls}">{content}<footer>- {n} -</footer></section>'

css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e8eaed;color:#000;font-family:"Malgun Gothic",sans-serif;font-size:10.5pt;line-height:1.7;word-break:keep-all}.page{width:210mm;height:297mm;padding:20mm 22mm;background:#fff;margin:18px auto;position:relative;overflow:hidden;break-after:page}.page:last-child{break-after:auto}h1,h2,h3,h4{font-family:"Malgun Gothic",sans-serif;line-height:1.5;color:#000;break-after:avoid}h1{font-size:17pt;text-align:center;margin:0 0 10mm}h2{font-size:14pt;margin:6mm 0 3mm}h3{font-size:11.5pt;margin:4mm 0 2mm}h4{font-size:10.5pt;margin:3mm 0 1mm}p{margin:0 0 3mm}table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:9.2pt;line-height:1.6;margin:3mm 0 5mm}th,td{border:1px solid #444;padding:2mm 2.2mm;vertical-align:middle;overflow-wrap:anywhere}th{background:#f0f0f0;font-weight:700;text-align:center}td:first-child{text-align:center}table.tight td,table.tight th{padding:1.6mm 2mm}.small{font-size:8.8pt;line-height:1.65;color:#333}.indent{margin-left:5mm}.goals{padding-left:7mm;margin:2mm 0 4mm}.goals>li{margin:2mm 0}.goals ol{padding-left:6mm;margin:1mm 0}.goals ol li{margin:1mm 0}footer{position:absolute;left:0;right:0;bottom:10mm;text-align:center;font-family:"Batang",serif;font-size:9pt}.cover .course{font-weight:700;color:#0666ff;font-size:19pt;text-align:center;line-height:1.55;border-top:2px solid #454094;border-bottom:2px solid #454094;padding:2mm 0;margin-top:10mm}.cover .task{font-size:16pt;text-align:center;font-weight:700;line-height:1.8;margin:46mm 0 28mm}.cover .info{width:140mm;margin:auto;font-size:11pt}.cover .info th{width:27%;background:white}.cover .info td{text-align:center}.cover .info td,.cover .info th{padding:2.6mm;border-style:dotted}.cover .info{border:1px solid #000}.cover .logo{display:block;width:82mm;height:auto;margin:20mm auto 0}.flow{display:flex;gap:2mm;align-items:center;margin:3mm 0}.flow .box{flex:1;text-align:center;padding:3mm 1mm;border:1px solid #444;background:#f6f6f6;font-size:9pt;line-height:1.6}.flow .arrow{flex:none;font-size:13pt}svg{display:block;width:100%;height:auto}.caption{font-size:8.5pt;text-align:center;margin:1mm 0 4mm;color:#333}code{font-family:Consolas,monospace;font-size:.95em}.gantt{font-size:8pt;line-height:1.4}.gantt td,.gantt th{text-align:center;padding:2mm 1mm}.gantt td:first-child{text-align:left}.gantt .bar{background:#dbe7f9}.gantt .gate{background:#e9d9bc;font-weight:700}@media print{body{background:#fff}.page{margin:0}}'''

css+='body{font-size:10pt;line-height:1.6}.page:not(.cover){padding-top:17mm}h2{margin-top:5mm}h3{margin-top:3.5mm}table{font-size:9pt;line-height:1.5;margin:2.5mm 0 4mm}td,th{padding:1.8mm 2.2mm}.small{font-size:8.6pt;line-height:1.55}.goals>li{margin:1.6mm 0}.goals ol li{margin:.8mm 0}'
css+='.gantt th{white-space:nowrap;font-size:7.3pt;padding:2mm .5mm}'
css+='''
:root{--accent:#0b63b6;--ink:#171717;--muted:#525252;--line:#d4d4d4;color-scheme:light}
body{color:var(--ink)}.cover .course{color:var(--accent);border-color:var(--accent)}
.system{border:1px solid #444;padding:4mm;margin:4mm 0}
.system .box{background:white}.system .owned{border:2px solid var(--accent)}
.system p{font-size:9pt;margin:2mm 0 0}.formula{padding:2mm 3mm;border-left:2px solid var(--accent);background:#f5f7fa;font-size:9pt}
.draft{text-align:right;font-size:8pt;color:var(--muted);margin:0 0 2mm}
.equipment p{font-size:9.5pt;line-height:1.55}.equipment table{margin-bottom:3mm}
@media screen and (max-width:820px){
 body{font-size:16px}.page,.page:not(.cover){width:100%;height:auto;min-height:0;margin:0 0 16px;padding:24px 18px;overflow:visible;break-after:auto}
 h1{font-size:22px}h2{font-size:21px}h3{font-size:18px}h4{font-size:16px}
 p,.small,.formula,.system p,.equipment p{font-size:16px}table{font-size:14px}footer{position:static;margin-top:24px}
 .cover .course{font-size:22px;margin-top:8px}.cover .task{font-size:22px;margin:48px 0 28px}
 .cover .info{width:100%;font-size:16px}.cover .logo{width:75%;margin:32px auto 0}
 .flow{flex-direction:column}.flow .box{width:100%;font-size:16px}.flow .arrow{transform:rotate(90deg)}
 .sequence{display:block;overflow-x:auto}.sequence table{min-width:600px}
 .gantt{display:block;overflow-x:auto}.gantt td,.gantt th{min-width:32px}.gantt td:first-child,.gantt th:first-child{min-width:120px}
 .diagram{overflow-x:auto}.diagram svg{min-width:720px}.draft{font-size:13px}.indent{margin-left:0}
}
'''
# v0.12: submission content; no changes to the Factory I/O or PLC prototype.
# Reference: user-supplied "디지털 트윈 2B 계획서.hwpx" (4조), 2026-11-17.
# Its process/data/interface structure is referenced; numerical claims are not adopted.
css+='''
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm;margin:3mm 0 4mm}
.card{border:1px solid #aaa;padding:3mm;background:#fafafa;font-size:9pt;line-height:1.6}
.card b{display:block;color:var(--accent);margin-bottom:1mm;font-size:10pt}
.diagram{margin:3mm 0}.diagram svg{font-family:"Malgun Gothic",sans-serif}
.keyline{border-left:3px solid var(--accent);padding:2mm 3mm;background:#f5f7fa;margin:3mm 0}
.compact{font-size:9pt}.legend{font-size:8.5pt;color:#444;margin:1mm 0 3mm}
@media screen and (max-width:820px){.cards{grid-template-columns:1fr}.card,.card b,.compact,.legend{font-size:16px}}
'''
# Title and heading styles read from the supplied 4조 HWPX charPr 13/10/15/21.
# 휴먼명조 is unavailable locally; Batang is the HWPX-declared substitution.
css+='''
@font-face{font-family:PlanHeadline;src:url("assets/plan_v0.12-headline.ttf") format("truetype");font-weight:400;font-style:normal}
h1{font-family:PlanHeadline,"HY헤드라인M","HYHeadLine-Medium";font-size:20pt;font-weight:400;color:#000;text-align:center;line-height:1.6;letter-spacing:0}
h2{font-family:PlanHeadline,"HY헤드라인M","HYHeadLine-Medium";font-size:15pt;font-weight:400;color:#3a3c84;text-align:left;line-height:1.6;letter-spacing:0}
h3,h4{font-family:"휴먼명조","Batang","바탕",serif;font-size:13pt;font-weight:700;color:#000;text-align:left;line-height:1.6;letter-spacing:0}
.cover .course{font-family:"HY견고딕","HYGothic-Extra";font-size:20pt;font-weight:700;color:#0066ff;line-height:1.6;border-color:#3a3c84}
.cover .task{font-family:PlanHeadline,"HY헤드라인M","HYHeadLine-Medium";font-size:20pt;font-weight:400;color:#000;line-height:1.6}
'''
css+='''
.equipment-figure{margin:3mm 0 2mm}.equipment-figure img{width:100%;height:56mm;object-fit:contain;display:block}
.equipment-figure figcaption{font-size:8pt;color:#525252;text-align:center;margin-top:1mm}
.equipment-stages{display:grid;grid-template-columns:repeat(4,1fr);gap:2mm;margin:1mm 0 2mm;color:#23456b;font-size:9pt;text-align:center}.equipment-stages span{border-bottom:2px solid #a7bbd3;padding-bottom:1mm}
.scope-strip{display:flex;justify-content:space-between;align-items:center;gap:2mm;border-top:1px solid #ccd5e0;border-bottom:1px solid #ccd5e0;padding:2mm 0;font-size:9pt}
.scope-strip i{font-style:normal;color:#0b63b6}.scope-strip b{color:#0b63b6}
.card{border:1px solid #d0d8e2;background:#f8fafc;border-top:2px solid #0b63b6}.card b{color:#23456b}
.diagram svg{background:#fbfcfe;border:1px solid #e2e7ee;border-radius:5px}
@media screen and (max-width:820px){.equipment-figure{overflow-x:auto}.equipment-figure img{height:auto;min-width:720px}.equipment-figure figcaption{font-size:13px}.scope-strip{flex-wrap:wrap;font-size:14px}}
'''
pages=[]

def cards(items):
    return '<div class="cards">'+''.join(f'<div class="card"><b>{title}</b>{text}</div>' for title,text in items)+'</div>'

def svg_start(height, label):
    return f'''<div class="diagram"><svg viewBox="0 0 720 {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}"><defs><marker id="arrow{height}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto-start-reverse"><path d="M0 0L7 3.5L0 7" fill="#525252"/></marker></defs>'''

def box(x,y,w,h,title,lines=(),owned=False):
    shapes = {
        '검사·비전': '<rect x="1" y="5" width="20" height="14" rx="2"/><circle cx="11" cy="12" r="4"/><path d="M6 5V2H15V5"/>',
        'MELSEC Q PLC': '<rect x="1" y="2" width="21" height="20" rx="1"/><path d="M7 3V21M14 3V21M3 7H5M9 7H12M16 7H20M16 11H20M16 15H20"/>',
        '로봇·실물 설비': '<path d="M2 22H22M7 22V18L15 12L9 6L13 2M15 12L20 7L23 9"/><circle cx="9" cy="6" r="3"/><circle cx="15" cy="12" r="3"/>',
        'Factory I/O · 가상 전공정': '<rect x="1" y="9" width="22" height="8" rx="4"/><circle cx="6" cy="13" r="2"/><circle cx="18" cy="13" r="2"/><path d="M5 17V22M19 17V22M8 9V3H16V9"/>',
        'Python · 수집 및 통신': '<rect x="2" y="1" width="20" height="22" rx="2"/><path d="M3 8H21M3 15H21M6 5H8M6 12H8M6 19H8M11 5H18M11 12H18M11 19H18"/>',
        'DB': '<ellipse cx="12" cy="4" rx="10" ry="3"/><path d="M2 4V20C2 24 22 24 22 20V4M2 12C2 16 22 16 22 12"/>',
        '조회 화면': '<rect x="1" y="2" width="22" height="16" rx="1"/><path d="M8 23H17M12 18V23M4 7H10M4 11H8M13 7H20M13 11H20"/>',
    }
    icon = f'<g transform="translate({x+8} {y+8}) scale(.72)" fill="none" stroke="#315e8e" stroke-width="1.6">{shapes[title]}</g>' if title in shapes else ''
    border = '#7b9bbf' if owned else '#a8b4c1'
    fill = '#f0f5fb' if owned else '#ffffff'
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}" stroke="{border}" stroke-width="1.5"/>'+icon+f'<text x="{x+w/2}" y="{y+25}" text-anchor="middle" font-size="16" font-weight="700" fill="#183b60">{title}</text>'+''.join(f'<text x="{x+w/2}" y="{y+48+i*20}" text-anchor="middle" font-size="14" fill="#384a5b">{s}</text>' for i,s in enumerate(lines))

def arrow(d,height,dashed=False,both=False):
    return f'<path d="{d}" fill="none" stroke="#525252" stroke-width="1.5" marker-end="url(#arrow{height})"'+(f' marker-start="url(#arrow{height})"' if both else '')+(' stroke-dasharray="5 4"' if dashed else '')+'/>'

def label(x,y,text):
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-size="13" fill="#444">{text}</text>'

# 1. Keep the institution's cover and confirmed group/instructor information.
pages.append(page('''<div class="course">[인텔] AI 융합 DX 마스터 클래스<br>프로젝트 실시 계획서</div>
<div class="task">【 과제명 】<br>배터리 셀 입고검사 및 매칭 공급 라인<br>디지털 트윈</div>
<table class="info"><tbody><tr><th>교과목명</th><td style="color:#0b63b6;font-weight:700">[인텔] AI 융합 DX 마스터 클래스</td></tr><tr><th>지도교수</th><td>김 유 성</td></tr><tr><th>팀 구분</th><td>3조</td></tr><tr><th>팀 장</th><td>최예현</td></tr><tr><th>팀 원</th><td>이순필, 박해준, 정연우, 김동혁</td></tr></tbody></table>
<img class="logo" src="assets/institution-logo.png" alt="대한상공회의소 부산인력개발원">''',1,'cover'))

# 2. Project context and boundaries, using descriptive names rather than "C".
overview=svg_start(235,'배터리 공정의 전공정, 실물 조립·검사, 후공정과 조별 담당 경계')
overview+=box(10,45,200,110,'3조 · 가상 전공정',['입고검사 · LOT 추적','등급 분류 · 4셀 세트'],True)
overview+=box(260,45,200,110,'실물 조립·검사 설비',['PLC · 로봇 · 비전','기존 설비와 연계'])
overview+=box(510,45,200,110,'4조 · 가상 후공정',['에이징 · 특성검사','포장 · 출하'])
overview+=arrow('M210 90H260',235,True,True)+arrow('M460 90H510',235,True,True)
overview+=label(360,23,'배터리 전공정·조립 및 검사·후공정 통합 구성안')
overview+=label(235,180,'공급 상태·ID')+label(485,180,'검사 결과·제품 ID')
overview+=label(360,218,'점선: 조별 시스템 간 데이터·인터록 연계 계획 (실물 반송 경로와 구분)')+'</svg></div>'
pages.append(page('''<p class="draft">v0.12 · 계획서 개정안</p><h1>배터리 셀 입고검사 및 매칭 공급 라인<br>디지털 트윈 프로젝트 계획서</h1>
<h2>1. 프로젝트 개요</h2><h3>1) 추진 목적 및 적용 범위</h3>
<p>본 프로젝트는 PLC·로봇·비전 기반 배터리 조립·검사 공정과 연계하여 셀 입고검사, 등급별 분류 및 매칭 공급을 수행하는 가상 전공정을 구축하는 것을 목적으로 한다. 셀의 합격 여부와 특성에 따른 세트 구성을 구분하여 관리하며, 가상 설비에서 분류 시퀀스와 공급 인터록을 검증한 후 실물 설비 연계 조건을 수립한다.</p><figure class="equipment-figure"><img src="assets/line-top-v0.12.svg" alt="입고·검사 위치, NG 분리 경로, 세 개의 등급별 버퍼와 공급 컨베이어를 표현한 가상 전공정 설계 개념도"><figcaption>개략 배치도</figcaption></figure><div class="scope-strip"><span><b>3조</b> 가상 전공정</span><i>↔</i><span>실물 조립·검사 설비</span><i>↔</i><span><b>4조</b> 가상 후공정</span></div>
<h3>2) 주요 개발 범위 및 기능</h3>'''+cards([
('입고검사 및 등급 분류','셀 ID·LOT에 유효 검사값을 연결하고 합격 셀을 A·B·C 전압 구간으로 분류'),
('공급 조건 검증','동일 전압 구간 4셀 구성, 보류·재고·세트 편차 확인 후 공급 허가'),
('품질 이력 및 추적성 관리','개별 셀 판정과 LOT 보류 상태 분리, 셀·세트별 판정 및 공급 이력 조회')])+'''
<h3>3) 실측 데이터 기반 가상 검증 및 공정 연계</h3>'''+cards([
('① 실측 데이터 취득','실물 셀 전압 수집 → 가상 셀 데이터 연결'),
('② 가상 비교 시험','순서별·등급별 구성 비교 → 분류·공급 조건 검증'),
('③ 제어 조건 및 인터록 반영','검증한 조건 적용 → 준비·공급·수신 확인 신호 교환')])+'''
<p class="small">실측 데이터는 사전 입력 또는 통신 수신 방식으로 연계하며, 실시간 자동 연동 범위는 통신 구성 확정 시 명시한다. 내부저항은 실측 가능 여부에 따라 적용하며, 전압만 확보되는 경우 평가 범위를 세트 내 전압 편차 비교로 한정한다.</p>''',2))

# 3. Performance definitions with a visual comparison, no invented results.
comparison=svg_start(145,'같은 입력 셀 데이터를 순서별 세트와 등급별 세트로 비교하는 평가 방법')
comparison+=box(10,35,170,85,'동일 합격 셀 데이터',['ID · 전압 · 입력 순서'])
comparison+=box(260,5,190,60,'순서별 4셀 구성')+box(260,80,190,60,'등급별 4셀 구성',owned=True)
comparison+=box(535,35,175,85,'세트 편차 비교',['최대-최소 전압의 평균'])
comparison+=arrow('M180 77H220V35H260',145)+arrow('M220 77V110H260',145)
comparison+=arrow('M450 35H490V77H535',145)+arrow('M450 110H490V77',145)+'</svg></div>'
pages.append(page('''<h2>2. 프로젝트 목표</h2><h3>1) 핵심 관리 지표 및 검증 기준</h3>'''+table(['핵심 관리 지표','목표치','검증 방법 및 판정 기준'],[
['세트 내 전압 편차','순서별 구성 대비<br>50% 이상 감소 (잠정)','동일 입력·관찰 시간에서 편차·완성 세트 수·잔여 재고를 함께 비교'],
['분류 정확성','100셀 중 오류 0건','셀 ID별 판정 등급과 실제 진입 레인 대조'],
['NG 공급 차단','NG 공급 유출 0건','부적합·보류 확정 후 신규 공급 차단 확인. 이전 인계분은 추적·통보 기록'],
['LOT 보류','확정 NG 누적 3건 시 보류<br>(교육용 정책값)','측정 오류는 NG 누계에서 제외. 해당 LOT의 대기 재고·미공급 세트 차단 확인'],
['4셀 공급·이력','동일 구간 4셀 공급<br>구성 셀 ID 연결','배출 수량·출구 감지·요청 ID별 수신 확인 대조. 이력 저장 상태는 별도 관리'],
['공급 성과','공급률·대기시간 병행 평가','완성 세트 수, 공급 셀 수/합격 입력 셀 수, 잔여·보류 수량과 대기시간 기록']], [23,30,47],'tight')+'''
<h3>2) 세트 내 전압 편차 평가 방법</h3>'''+comparison+'''
<p class="formula">세트 편차(mV) = 세트 내 최대 전압 - 최소 전압<br>감소율(%) = (순서별 평균 편차 - 등급별 평균 편차) ÷ 순서별 평균 편차 × 100</p>
<p class="compact">두 방식에 동일한 합격 셀·입력 순서·관찰 시간·시뮬레이션 배속을 적용한다. 구간 기준은 평가 전 고정하며, 가능하면 기준 설정 데이터와 평가 데이터를 분리한다. 완성 세트 편차와 함께 공급률·잔여 재고·대기시간을 제시한다. 비교 대상 셀이 다르면 공통 셀 집합으로 두 방식을 재구성하여 편차를 별도로 비교한다. 기준 편차가 0이면 감소율 대신 편차값을 보고하며, 50%는 첫 시험 후 적정성을 검토한다.</p>
<h3>3) 교육 및 수행 역량 목표</h3>'''+cards([
('설계·인터페이스','설비 배치, 태그 연결, PLC 순차 제어와 공급 인터록 설계'),
('시운전·피드백','정지·비상정지·걸림·통신 단절 시험 및 원인별 수정 기록'),
('문서화·발표','시험 조건과 결과 정리, 운전 동영상·최종 보고서 제작')])+'''
<p class="small">전압 비교는 팩 수명·불량률 개선의 입증 자료로 사용하지 않는다. 분류·공급 성공은 시험 조건과 표본 수를 명시하며, 관측 오류 0건을 전체 공정의 무결함 보장으로 해석하지 않는다.</p>''',3))

# 4. Branching process diagram replaces duplicate flow tables and long prose.
process=svg_start(365,'입고와 검사 후 NG를 분리하고 A B C 레인에서 동일 등급 4셀을 공급하는 분기 공정')
process+=box(10,115,115,80,'입고·LOT',['셀 ID 부여'])+box(175,115,125,80,'검사·판정',['전압 · 저항값'])
for y,grade in [(10,'A'),(115,'B'),(220,'C')]:
 process+=box(365,y,130,75,f'{grade}구간 버퍼',['예약 수 · 실제 재고'],True)
 process+=arrow(f'M300 150H330V{y+37}H365',365)+arrow(f'M495 {y+37}H530V150H570',365)
process+=box(570,115,140,80,'4셀 세트 공급',['설비 준비 확인'],True)+box(175,280,160,70,'부적합 셀 격리',['확정 NG만 누계'])
process+=arrow('M125 150H175',365)+arrow('M235 195V280',365)
process+=label(520,320,'동일 LOT의 NG 누계 도달')+label(520,342,'→ 해당 LOT 재고·세트 보류')+'</svg></div>'
roles=table(['구분','성명','담당 범위'],[
['팀장','최예현','일정·범위 관리, 세트 구성, LOT 보류, 실물 설비 연계'],
['팀원','이순필','셀 추적, 검사·등급 판정, PLC 분류 로직'],
['팀원','박해준','Factory I/O 배치, 태그 연결, 설비 동작 검증'],
['팀원','정연우','통신·수집기, DB 및 이력 조회 화면'],
['팀원','김동혁','실측, 시험 기록, 보고서·발표 자료']], [15,17,68],'tight')
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>1) 팀원 구성 및 역할 분담</h3>'''+roles+'''<p class="small">상기 역할 분담은 기존 배정안을 기준으로 하며, 팀 회의를 거쳐 최종 확정한다.</p>
<h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(1) 검사·분류·공급 시퀀스</h4>'''+process+cards([
('검사 위치 해제','다음 조건을 모두 만족할 때 해제<br>① 검사 완료<br>② 목적지 수용 가능<br>③ 분류 구간 비점유'),
('세트 공급 허가','다음 조건을 모두 만족할 때 공급<br>① 유효·비보류 4셀 및 세트 편차 적합<br>② 수신측 준비 완료<br>③ 다른 세트 공급 없음'),
('공급 완료 확인','물리적 인계 완료 기준<br>① 실제 배출 수량 4셀<br>② 출구 감지·요청 ID별 수신 확인<br>③ 이력 저장 상태는 별도 관리')])+'''
<p class="compact">측정 유효성 확인 후 셀 사양에 따른 상·하한을 적용한다. 측정 실패·LOT 미확인·LOT 보류는 부적합 확정과 구분하여 공급을 차단한다. 공급 직전 LOT 상태와 세트 편차를 재확인하고, 복구 시 실물 수량·요청 ID·내부 재고를 대조한다.</p>''',4))

# Inspection scope: voltage bins, validity checks and measurement protocol.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(2) 검사 기준 및 측정 조건</h4>
<div class="keyline"><strong>A·B·C는 합격 셀의 전압 구간이다.</strong><br>구간명은 품질의 우열을 의미하지 않는다. 본 계획의 매칭은 전압 구간별 세트 구성 및 공급 제어 검증으로 한정한다. 용량·수명·종합 성능 매칭은 평가 범위에 포함하지 않는다.</div>
<h4>측정 및 판정 조건 확정표</h4>'''+table(['확정 항목','시험 전 정의할 조건','남길 기록'],[
['셀 및 검사 규격','동일 비교군의 모델·화학계·제조 LOT 확인. 제조사 사양과 입고 조건에 따라 전압 상·하한 설정','셀 모델, 사양서, 적용 기준 및 개정 번호'],
['측정 조건','충방전 이후 휴지 조건·온도 조건을 통일. 측정 시각과 조건 이탈 여부 확인','온도, 휴지 조건, 측정 시각, 셀 ID'],
['장비 및 접촉','전압계 분해능·오차와 접촉 방식을 기록. 내부저항은 측정 방식·조건을 명시하여 적용','장비 모델, 유효 범위, 확인·교정 이력'],
['내부저항 미확보','해당 항목을 미측정으로 표시하고 판정에서 제외. 임시값 시험과 실측 평가 분리','미측정 여부, 임시/실측 데이터 구분'],
['구간 및 세트 허용차','A·B·C 경계를 사전 고정하고 공급 직전 4셀 최대-최소 전압을 별도 확인','구간 경계, 세트 허용 편차, 기준 버전']], [24,51,25],'tight')+'''
<h4>판정 순서와 예외 처리</h4>'''+cards([
('① 측정 유효성','셀 ID·모델·측정 시각·장비 상태 확인. 누락·기한 초과·접촉 실패는 재측정 대기'),
('② 합격 여부 판정','유효 검사값에 사양 기반 상·하한 적용. 기준 이탈은 부적합 확정 및 사유 기록'),
('③ 구간·공급 판정','합격 셀에 전압 구간 부여. 비보류 재고로 세트를 구성하고 세트 허용 편차 재확인')])+'''
<p class="compact">측정 실패는 셀 불량으로 단정하지 않는다. 재측정 가능 횟수와 데이터 유효기간은 장비 확인 후 시험 전에 정한다. 미판독 LOT·모델 불일치는 식별 확인 전까지 보류한다. 구체적인 전압·저항 수치는 사용 셀과 장비의 사양 확인 후 확정한다.</p>
<p class="small">기술 참고: <a href="https://www.ti.com/lit/an/slua340c/slua340c.pdf">TI, Cell Balancing Using the bq20zxx</a> / <a href="https://www.hioki.com/global/industries-solutions/manufacturing/liion-ocv-test.html">HIOKI, OCV Testing</a> / <a href="https://www.hioki.com/us-en/learning/usage/resistance-meters_2.html">HIOKI, Internal Resistance Testing</a></p>''',5))

pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(3) 셀 판정·LOT 보류 및 재고 관리</h4>
<p>개별 셀의 검사 결과와 LOT의 공급 가능 상태를 별도로 관리한다. 부적합 확정 셀은 격리하고, 측정·식별 미확인 및 LOT 보류 셀은 검토 대기 상태로 관리한다.</p>'''+table(['상태','설정 조건','공급 및 재고 처리'],[
['합격','검사 유효·규격 적합','LOT 정상·세트 허용 편차 충족 시 공급 가능'],
['부적합 확정','유효 측정값의 규격 이탈','공급 금지, 격리 및 사유 기록. LOT의 확정 NG 누계에 반영'],
['재측정·식별 대기','접촉 실패·데이터 누락·기한 초과·LOT 미확인','판정 전까지 공급 금지. 확정 NG 누계에는 반영하지 않음'],
['LOT 보류','해당 LOT의 확정 NG 누계가 설정값에 도달','해당 LOT의 신규 셀·대기 재고·미공급 세트에 공급 차단 적용']], [23,35,42],'tight')+'''
<h4>보류 발생 시 처리 순서</h4>'''+cards([
('① 대상 재고 잠금','LOT를 보류로 전환하고 가용 재고에서 제외. 혼합 세트도 해당 셀이 포함되면 공급 차단'),
('② 진행·인계분 확인','세트 예약 취소 또는 재검토. 이동 중·인계 완료분은 수신측에 대상 ID를 통보하고 상태 대조'),
('③ 검토 후 해제','원인·재검 결과·검토자·시각 기록 후 해제 또는 부적합 확정. 단순 리셋으로 보류 이력 삭제 금지')])+'''
<h4>시험용 보류 정책</h4><p>동일 LOT의 확정 NG 누적 3건을 교육용 초기 설정값으로 사용한다. 산업 공통 기준으로 해석하지 않으며, LOT별 검사 총수·확정 NG 수·검사 기간과 함께 기록한다. 보류 및 해제 조건은 시험 전에 고정하여 판정 재현성을 확보한다.</p>
<h4>가용 재고 및 세트 구성 규칙</h4>'''+table(['관리 항목','설계 규칙'],[
['가용 재고','합격·식별 완료·측정 유효·LOT 정상인 미예약 셀만 집계'],
['세트 예약','구성 셀 ID 4개를 잠그고 구간·편차·보류 상태를 공급 직전 재확인'],
['이상 복구','실제 위치·배출 수량·예약·수신 ID 대조 후 재개. 인계 상태 불명 시 자동 재공급 금지']], [25,75],'tight')+'''
<p class="small">인계 완료 후 LOT 보류가 발생한 경우 이미 공급된 사실은 유지하고 품질 상태를 별도로 갱신한다. 후속 공정에서의 사용 보류 및 처리 범위는 대상 ID와 함께 공동 확인한다.</p>''',6))

# 5. Full architecture: equipment, control, bridge, storage, and operator view.
architecture=svg_start(500,'검사·비전, PLC, 로봇, Factory I/O, Python 수집기, 데이터베이스와 조회 화면을 연결하는 전체 시스템 설계')
architecture+=label(360,20,'실물 조립·검사 설비와 가상 전공정의 제어·데이터 연결 계획')
architecture+=box(10,50,190,90,'검사·비전',['검사값 · 판독 결과','실물 공정 데이터'])
architecture+=box(265,50,190,90,'MELSEC Q PLC',['순차 제어 · 분류·공급','준비 · 이상 · 수신 확인'],True)
architecture+=box(520,50,190,90,'로봇·실물 설비',['조립 · 검사 · 투입','기존 공정 제어 범위'])
architecture+=arrow('M200 95H265',500,True)+arrow('M455 95H520',500,True,True)
architecture+=box(10,245,305,110,'Factory I/O · 가상 전공정',['센서 · 컨베이어 · 푸셔 · 블레이드','입고 → 검사 → 분류 → 4셀 공급'],True)
architecture+=box(395,245,315,110,'Python · 수집 및 통신',['PLC 값 수집 · 셀/세트 ID 연결','이벤트 · 이상 · 검사 결과 저장'],True)
architecture+=arrow('M360 140V185H160V245',500,True,True)+label(165,207,'센서값 ↑ / 구동 명령 ↓')
architecture+=arrow('M400 140V210H550V245',500,True,True)+label(558,233,'상태·판정·공급 이력')
architecture+=box(395,425,145,65,'DB',['셀 · 세트 · 시험'],True)+box(565,425,145,65,'조회 화면',['상태 · 알람 · 이력'],True)
architecture+=arrow('M475 355V425',500)+arrow('M635 355V425',500)+arrow('M540 458H565',500)
architecture+=box(10,415,305,75,'4조 · 후공정 연계',['제품 ID · LOT · 검사 결과 인계'])
architecture+=arrow('M315 453H395',500,True,True)+'</svg></div>'
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(4) 전체 시스템 및 I/O 연결 구성</h4>'''+architecture+'''
<p class="legend">파란 테두리: 3조 설계 범위 / 회색: 연계 대상 / 점선: 통신·인터록 협의 대상</p>'''+table(['시스템 구성','교환 데이터 및 제어 신호','인터페이스 검증 항목'],[
['가상 설비 ↔ PLC','센서·LOT 판독값 / 컨베이어·푸셔·블레이드 명령','신호 방향, 태그 중복, 통신 단절 시 동작'],
['실물 설비 ↔ PLC','검사 결과·준비 상태 / 공급 요청·수신 확인','실물 공정 담당 범위와 공급 허가 조건'],
['PLC ↔ 수집기 → DB·화면','셀 ID·세트 ID·등급·재고·이상·공급 이벤트','값의 갱신 주기, 이벤트 누락·중복, 조회 항목']], [25,40,35],'tight')+'''
<p class="small">상기 도식은 전체 시스템의 기능 및 신호 연결을 정의하는 설계안이다. 전기 단자 결선도, 실물 통신 경로 및 로봇·비전 접속 방식은 기존 설비 구성 확인 후 확정한다. 가상 부품의 이동과 실물 배터리의 자동 반송은 구분하여 관리한다.</p>''',7))

# Synchronization scope and fault-tolerant transfer are planned requirements.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(5) 실물·가상 동기화 및 공급 거래 관리</h4>
<p>가상 전공정은 신규 설계안이며 실물 전공정의 복제 완료를 의미하지 않는다. 실물과 대응시키는 범위는 셀 검사 데이터, 설비 준비·이상 상태 및 공급 요청·수신 확인이다. 가상 부품 이동과 실물 배터리 반송은 별도로 검증한다.</p>'''+table(['운영 모드','동기화 범위','검증 및 보고 기준'],[
['사전 데이터 시험','실측 셀 ID·측정값을 가상 개체에 연결','입력 데이터 고정 및 재현 시험. 실시간 자동 연동으로 보고하지 않음'],
['온라인 연계 목표','셀 ID·측정 시각·상태와 준비·요청·수신 확인 교환','갱신 주기·허용 지연을 시험 전 확정. ID·상태·수량·시각 대조'],
['모델 검증','분류 결과·재고·공급 수량을 기준 기록과 비교','불일치 건수·지연·누락 기록. 미연계 항목은 모사 범위로 명시']], [24,39,37],'tight')+'''
<h4>공급 상태와 이력 저장 상태의 분리</h4>'''+cards([
('① 요청 기록','요청 ID·세트 ID·셀 ID·수량을 지속 보관 가능한 로컬 기록에 저장한 뒤 공급 요청'),
('② 물리적 인계','배출 수량·출구 감지·동일 요청 ID의 수신 확인을 대조하여 물리적 인계 완료 확정'),
('③ 이력 반영','이벤트 ID로 DB 저장·중복 제거. DB 저장 대기는 물리적 인계 완료 상태와 별도 표시')])+'''
<h4>지연·중단 및 재전송 처리</h4>'''+table(['상황','처리 및 재개 조건'],[
['준비 해제·부분 배출','새 공급을 차단하고 배출·수신 수량을 기록. 실제 위치와 인계 상태 대조 후 복구'],
['수신 확인 시간 초과','미확정 상태 유지 및 자동 재배출 금지. 동일 요청 ID로 상태 조회·확인 메시지만 재전송'],
['중복 요청·통신 복구','이미 처리한 요청 ID는 다시 배출하지 않음. 수신측 처리 ID와 송신측 기록 대조'],
['DB 저장 실패','로컬 이력 보관 후 동일 이벤트 ID로 저장 재시도. 로컬 기록도 불가능하면 새 공급 차단'],
['재시작·정전 복구','요청·완료 ID와 실제 수량을 복원·대조. 상태 보존 범위 확인 전 자동 운전 재개 금지']], [28,72],'tight')+'''
<p class="small">상기 내용은 구현·검증할 요구사항이다. 타임아웃·갱신 주기·보존 장치는 실물 통신 구성 확인 후 확정한다. 기술 참고: <a href="https://www.nist.gov/programs-projects/digital-twins-advanced-manufacturing">NIST, Digital Twins for Advanced Manufacturing</a>.</p>''',8))

# 6. Field-level interfaces and explicit boundary with the supplied 4조 plan.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(6) I/O 신호 및 인계 데이터</h4>
<p>인터페이스는 설비 I/O, 공급 승인 인터록 및 이력 데이터로 구분한다. 아래 I/O 주소는 가상 설비 시연 기준이며, 공용 PLC 적용 전 기존 태그와의 중복 여부를 검증한다.</p>'''+table(['신호 구분','현재 가상 설비 연결','내용'],[
['비트 입력 19점','Coils 0~18 → M1000~M1018','위치 검출 7점, 푸셔 끝 센서 8점, 조작반 4점'],
['비트 출력 20점','M1100~M1119 → Discrete Inputs 0~19','컨베이어·푸셔·블레이드·투입·회수·표시등'],
['LOT 판독 1점','Holding Register 0 → D1000','가상 비전 판독값을 LOT 구분에 사용'],
['시뮬레이션 상태','Coils 19 / 20 / 21','실행 / 일시정지 / 씬 초기화']], [25,38,37],'tight')+'''
<h4>공급 승인 및 수신 확인 인터록</h4>'''+cards([
('① 준비 확인','설비 → 전공정<br>투입 가능·정지·이상 상태 확인'),
('② 세트 공급 요청','전공정 → 설비<br>세트 ID·구성 셀 ID·등급 전달'),
('③ 수신 확인','설비 → 전공정<br>요청 ID·수량 대조 후 물리적 인계 확정')])+'''
<h4>공정 간 인계 데이터 및 추적성 관리 항목</h4>'''+table(['담당 구간','관리 단위·필드','연결 목적'],[
['3조 · 전공정','셀 ID, LOT, 전압, 적용 시 내부저항, 판정 등급','셀별 검사·분류 결과 추적'],
['3조 → 실물 설비','요청 ID, 세트 ID, 구성 셀 ID 4개, 공급 상태','4셀 구성과 수신 확인 대조'],
['실물 설비 → 4조','제품 ID, LOT, 초기 전압, 검사 결과','4조 에이징·특성검사의 기준 데이터'],
['4조 · 후공정','제품 ID, 재검 횟수, 박스 ID','재검 이력 및 포장 단위 추적']], [25,43,32],'tight')+'''
<div class="keyline"><strong>공정 간 인계 단위 및 ID 대응 규격 협의</strong><br>3조는 4셀 세트 공급을, 4조 참고 계획서는 1셀 카트리지 인계를 전제로 한다. 인계 셀 수, 실물 조립 단위 및 세트 ID와 제품 ID의 대응 관계를 공동으로 확정한 후 최종 인계 규격을 수립한다.</div>
<p class="small">후공정 범위 및 데이터 구성은 4조 계획서를 참고하되, 해당 문서의 수치 목표·계측 기준·디바이스 번호는 3조의 확정 규격에 포함하지 않는다. 전압 단위와 데이터 입력·수신 방식은 공동 인계 규격에 명시한다.</p>''',9))

# Address review: 4조 supplied plan versus current generated PoC ladder.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정 구성 및 제어 시퀀스</h3><h4>(7) PLC 디바이스 영역 분리 및 공용 태그 관리</h4>
<p>4조 계획서의 명시 주소와 3조 PoC의 생성 래더를 대조한 결과, 내부 릴레이 및 데이터 레지스터 일부가 중복된다. 별도 제어기에서는 독립적으로 사용할 수 있으나, 동일 PLC에 통합할 경우 주소 재배정이 필요하다.</p>'''+table(['중복 주소','3조 현재 PoC 용도','4조 계획서 용도'],[
['M0','운전 자기유지','비상정지'],['M10','입고 요청','반입·바코드 스캔'],['M200','LOT 보류 영역의 시작 주소','자동창고 운전'],['D200','임시 전압 표의 시작 주소','자동창고 랙 번호']], [18,41,41],'tight')+'''
<h4>3조 전용 영역 배정 제안</h4>'''+table(['구분','현재 PoC 예시','통합 적용 제안'],[
['순차 제어·LOT 관리','M0 / M10 / M200','M3000 / M3010 / M3200'],['가상 센서·액추에이터','M1000~M1018 / M1100~M1119','M4000~M4018 / M4100~M4119'],['판정·검사 데이터','D200 / D1000','D3200 / D4000'],['3조 내부 디바이스 예약안','현재 PoC는 저주소 영역 포함','M3000~M4999 / D3000~D4999']], [30,35,35],'tight')+'''
<p class="small">상기 주소는 통합 설계를 위한 제안이며 현재 PoC에는 적용하지 않았다. 4조 계획서에 명시된 주소와 분리한 안으로, 실제 PLC의 지원 범위와 기존 설비·타 조 전체 태그맵을 확인한 후 확정한다. 타이머·카운터·인덱스 영역도 별도로 대조한다.</p>
<h4>실물 I/O 및 공용 인터록 확정 절차</h4>'''+cards([
('① X/Y 결선 확인','3조 가상 PoC는 X/Y 미사용. 4조 자료에도 X/Y 할당표가 없어 실물 단자·모듈 구성 확인 필요'),
('② 소유 영역 분리','각 조가 갱신할 주소와 읽기·쓰기 권한을 지정하고 준비·요청·수신 확인 태그를 공동 정의'),
('③ 통합 전 대조','간접 주소·일괄 초기화 범위까지 대조한 뒤 주소표 확정 및 통합 시험 수행')])+'''
<div class="keyline"><strong>검토 결론</strong><br>현재 PoC는 M0·M10·M200·D200이 중복된다. X/Y 비중복은 미확정이며, 통합 주소 재배정과 공용 태그 승인 후 동일 PLC에 적용한다.</div>''',10))

# 7. Equipment and verification chain, with status consolidated here.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>3) 제어설비 및 검증 계획</h3>'''+table(['구분','규격·용도','확보·적용 계획'],[
['PLC','Mitsubishi MELSEC Q03UDE / 순차 제어·연계','공용 장비 사용 예정'],
['가상 설비','Factory I/O Modbus & OPC 에디션','기설치 / 전공정 배치'],
['제어 프로그램','GX Works2 / 실제 PLC 프로그램 검증','기설치 / 변환·컴파일'],
['수집·이력','Python, DB, 웹 조회 화면','직접 구성 / 상세 기술 확정'],
['검사 데이터','18650 셀 전압 및 적용 시 내부저항','실측 가능 항목·수량 확인'],
['PC','Windows / 가상 설비·수집·화면 실행','보유 장비 1대']], [21,48,31],'tight')+'''
<p class="small">추가 장비의 수량 및 단가는 사양 확인 후 산정한다. 통신 경로는 OPC 서버 확보 여부와 공용 PLC의 운영 환경을 기준으로 결정한다.</p>
<h4>가상 설비 구성</h4>'''+table(['구성 요소','수량','역할'],[
['컨베이어','6','입고 1, 메인 1, 등급 레인 3, 공급 1'],
['푸셔 / 스톱 블레이드','4 / 4','NG·등급 분류 / 검사 위치·레인 끝 정지'],
['검출 센서 / 가상 비전','7 / 1','위치·출구 감지 / LOT 판독'],
['투입기 / 회수기 / 슈트','1 / 2 / 2','가상 셀 입고 / NG·공급 경로 회수']], [40,15,45],'tight')+'''
<h4>개발 현황 및 후속 검증 범위</h4><p class="compact">2026년 11월 17일 작업 기록을 기준으로, 임시 검사값을 적용한 소프트 PLC 시연에서 씬 로드, 통신 및 분류 동작을 관찰하였다. 4셀 공급 통합 시험과 실물 PLC 연계는 후속 검증 범위이며, 수집기·DB·조회 화면은 개발 예정이다.</p>
<h4>통합 검증 시나리오 및 시험 기록</h4>'''+table(['시험 구간','기대 동작','기록 자료'],[
['검사 → 분류','판정 등급과 실제 레인 일치','셀 ID·입력값·판정·진입 레인 대조표'],
['버퍼 → 공급','4셀 확보 후 허가 조건에서만 배출','실제 수량·출구 감지·수신 ID·시간'],
['LOT·이상 처리','대기 재고·세트 공급 차단, 이상 시 정지','확정NG 누계·대상 재고·보류/해제 이력'],
['수집 → 조회','DB 지연·통신 복구 시 중복 공급 방지','요청/이벤트 ID·로컬 기록·재전송 결과']], [25,35,40],'tight')+'''
<p class="small">실측 데이터 비교 결과와 임시값 기반 제어 시험 결과는 구분하여 관리한다. 각 시험에는 입력 조건, 기대 동작, 실제 결과 및 수정 이력을 기록한다.</p>''',11,'equipment'))

# 8. Course schedule preserved, deliverables linked to review evidence.
phase_plan=table(['계획 기간','단계 및 주요 활동','선행 조건·조정 기준'],[
['11/17~11/19','범위·역할·인계 규격 설계 / 실측·통신 경로 확인','수업 시간표와 장비 사용 가능 시간 확인'],
['11/23~11/25','가상 전공정 배치 / 검사·분류 제어 구현','실습 가능 시간에 따라 배치·제어 작업 분담'],
['11/26~12/1','세트 공급·이력 연계 / 비교 측정·통합 검증','조별 인터페이스 확정 및 장비 사용 시간 확보'],
['12/7~12/8','미완료 검증 보완 / 시연·보고서·발표','수업·제출 일정에 맞춰 검증 범위 확정']], [23,44,33],'tight')
pages.append(page('''<h2>4. 프로젝트 추진일정</h2><p>추진 기간: 2026. 11. 17 ~ 2026. 12. 8 / 3조</p><div class="keyline"><strong>정규 수업과 프로젝트를 병행하는 추진 계획</strong><br>기간 내 모든 수업일을 프로젝트 전일 작업일로 산정하지 않는다. 과제와 실습 가능 시간, 장비 사용 시간을 확인하여 주별 작업량과 담당을 조정한다.</div>'''+phase_plan+'''<p class="small">기간별 작업 범위와 아래 완료 시점은 잠정 목표이다. 전일 작업량이나 프로젝트 전용 시수의 배정을 의미하지 않는다.</p>
<h3>1) 단계별 잠정 완료 목표</h3>'''+table(['추진 일정','단계별 완료 및 검증 기준'],[
['11/19','실물 통신 경로, 조별 담당 범위·인계 단위·ID 대응 규칙 결정'],
['11/25','가상 배치 및 센서·블레이드·푸셔 동작 확정'],
['11/27','분류·공급 차단·전압 편차·공급률·잔여 재고의 첫 측정 결과'],
['12/1','기능 동결, 보류·부분 공급·통신/DB 복구·이력 조회의 통합 시험 결과'],
['12/7~12/8','시연 리허설, 최종 보고서·발표 자료 제출']], [22,78],'tight')+'''
<h3>2) 최종 산출물</h3>'''+cards([
('공정·제어 자료','Factory I/O 씬, 태그맵, PLC 프로그램, 통신·인계 규격'),
('이력·시험 자료','셀·세트 이력 구조와 조회 화면, 분류·공급 대조표, 편차 비교표'),
('시연·제출 자료','운전 동영상, 시험·수정 기록, 최종 보고서, 발표 자료')])+'''
<h3>3) 사전 협의 및 범위 조정 기준</h3><p class="compact">실물 셀 수량, 검사 항목, 공용 PLC 주소 및 조별 인계 규격을 사전 확정한다. 수업 진행과 장비 사용 가능 시간에 따라 주별 가용 시간을 산정하고 검증 필수 항목을 우선 배정한다. 통신 확보 또는 수업 일정에 변동이 발생하면 완료 목표와 평가 범위를 조정하여 최종 산출물에 반영한다.</p>''',12))

assert len(pages)==12
assert not any(term in ''.join(pages) for term in ['C 라인','실물 C','C →','→ C','왕 성 식','A팀','B팀'])
document='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>3조 프로젝트 실시 계획서 v0.12</title><style>'+css+'</style></head><body class="p-brief">'+''.join(pages)+'</body></html>'
(BASE/'plan_v0.12.html').write_text(document,encoding='utf-8')
print('Created',BASE/'plan_v0.12.html')
