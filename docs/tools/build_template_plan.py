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
# v0.6: submission content; no changes to the Factory I/O or PLC prototype.
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
pages=[]

def cards(items):
    return '<div class="cards">'+''.join(f'<div class="card"><b>{title}</b>{text}</div>' for title,text in items)+'</div>'

def svg_start(height, label):
    return f'''<div class="diagram"><svg viewBox="0 0 720 {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}"><defs><marker id="arrow{height}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto-start-reverse"><path d="M0 0L7 3.5L0 7" fill="#525252"/></marker></defs>'''

def box(x,y,w,h,title,lines=(),owned=False):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{chr(35)}f5f8fc" stroke="#0b63b6" stroke-width="2"/>' if owned else f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="white" stroke="#777"/>') + f'<text x="{x+w/2}" y="{y+25}" text-anchor="middle" font-size="16" font-weight="700">{title}</text>'+''.join(f'<text x="{x+w/2}" y="{y+48+i*20}" text-anchor="middle" font-size="14">{s}</text>' for i,s in enumerate(lines))

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
overview+=label(360,23,'배터리 공정을 중심으로 연결하는 전체 구성안')
overview+=label(235,180,'공급 상태·ID')+label(485,180,'검사 결과·제품 ID')
overview+=label(360,218,'점선: 조별 시스템 간 데이터·인터록 연계 계획 (실물 반송 경로와 구분)')+'</svg></div>'
pages.append(page('''<p class="draft">v0.6 · 내용 검토용 초안</p><h1>배터리 셀 입고검사 및 매칭 공급 라인<br>디지털 트윈 프로젝트 계획서</h1>
<h2>1. 프로젝트 개요</h2><h3>1) 배터리 공정과 연계하는 가상 전공정</h3>
<p>PLC·로봇·비전을 활용하는 배터리 조립·검사 공정과 연계하여, 조립 전 셀을 검사하고 같은 등급끼리 공급하는 가상 전공정을 설계함. 합격 여부를 판정하는 검사에 더해 셀 특성에 따른 세트 구성을 비교하고, 설비를 추가하기 전에 분류 순서와 공급 조건을 검증하는 것이 목적임.</p>'''+overview+'''
<h3>2) 3조가 설계할 핵심 기능</h3>'''+cards([
('검사와 분류','셀 ID·LOT에 검사값을 연결하고 NG와 A·B·C 등급으로 분류'),
('공급 조건 검증','동일 등급 4셀 구성, 재고 확인, 설비 준비 상태에 따른 공급 허가'),
('이력과 품질 추적','LOT별 NG 누적 보류, 셀 ID와 세트 ID 연결, 판정·공급 이력 조회')])+'''
<h3>3) 실물 데이터와 가상 검증의 연결</h3>'''+cards([
('① 측정값 확보','실물 셀 전압 수집 → 가상 셀 데이터 연결'),
('② 가상 비교 시험','순서별·등급별 구성 비교 → 분류·공급 조건 검증'),
('③ 연계 조건 반영','검증한 조건 적용 → 준비·공급·수신 확인 신호 교환')])+'''
<p class="small">실측값은 사전 입력 또는 통신 수신으로 연결함. 실시간 자동 연동 범위는 통신 구성 확정 시 명시함. 내부저항은 측정 가능 여부를 확인하며, 전압만 확보하면 평가를 전압 편차 비교로 한정함.</p>''',2))

# 3. Performance definitions with a visual comparison, no invented results.
comparison=svg_start(145,'같은 입력 셀 데이터를 순서별 세트와 등급별 세트로 비교하는 평가 방법')
comparison+=box(10,35,170,85,'동일 합격 셀 데이터',['ID · 전압 · 입력 순서'])
comparison+=box(260,5,190,60,'순서별 4셀 구성')+box(260,80,190,60,'등급별 4셀 구성',owned=True)
comparison+=box(535,35,175,85,'세트 편차 비교',['최대-최소 전압의 평균'])
comparison+=arrow('M180 77H220V35H260',145)+arrow('M220 77V110H260',145)
comparison+=arrow('M450 35H490V77H535',145)+arrow('M450 110H490V77',145)+'</svg></div>'
pages.append(page('''<h2>2. 프로젝트 목표</h2><h3>1) 공정 성과와 완료 기준</h3>'''+table(['평가 항목','계획 목표','확인 방법'],[
['세트 내 전압 편차','순서별 구성 대비<br>50% 이상 감소 (잠정)','동일 입력 데이터로 두 방식의 세트별 전압 편차 평균을 비교'],
['분류 정확성','100셀 중 오류 0건','셀 ID별 판정 등급과 실제 진입 레인 대조'],
['NG 공급 차단','NG 공급 유출 0건','NG 및 보류 LOT 셀의 공급 경로 진입 여부 기록'],
['LOT 보류','동일 LOT의 세 번째 NG에서 보류','보류 전환 시점과 이후 해당 LOT의 NG 분리 확인'],
['4셀 공급·이력','동일 등급 4셀 공급<br>구성 셀 ID 연결','배출 수량·출구 감지·수신 확인 및 세트별 셀 ID 대조']], [23,30,47],'tight')+'''
<h3>2) 전압 편차 비교 설계</h3>'''+comparison+'''
<p class="formula">세트 편차(mV) = 세트 내 최대 전압 - 최소 전압<br>감소율(%) = (순서별 평균 편차 - 등급별 평균 편차) ÷ 순서별 평균 편차 × 100</p>
<p class="compact">입력 순서·등급 구간·비교 세트 수와 잔여 셀 수를 함께 기록함. 순서별 평균 편차가 0이면 감소율 대신 편차값을 제시함. 50%는 잠정 목표이며 실측 분포와 첫 비교 시험 후 검토함. 팩 수명이나 실제 불량률 개선을 입증한 것으로 해석하지 않음.</p>
<h3>3) 교육 및 수행 역량 목표</h3>'''+cards([
('설계·인터페이스','설비 배치, 태그 연결, PLC 순차 제어와 공급 인터록 설계'),
('시운전·피드백','정지·비상정지·걸림·통신 단절 시험 및 원인별 수정 기록'),
('문서화·발표','시험 조건과 결과 정리, 운전 동영상·최종 보고서 제작')])+'''
<p class="small">성공 여부는 실제 레인 진입과 배출 수량으로 확인함. 제어 신호 발생만으로 분류·공급 성공을 판정하지 않음.</p>''',3))

# 4. Branching process diagram replaces duplicate flow tables and long prose.
process=svg_start(365,'입고와 검사 후 NG를 분리하고 A B C 레인에서 동일 등급 4셀을 공급하는 분기 공정')
process+=box(10,115,115,80,'입고·LOT',['셀 ID 부여'])+box(175,115,125,80,'검사·판정',['전압 · 저항값'])
for y,grade in [(10,'A'),(115,'B'),(220,'C')]:
 process+=box(365,y,130,75,f'{grade}등급 버퍼',['예약 수 · 실제 재고'],True)
 process+=arrow(f'M300 150H330V{y+37}H365',365)+arrow(f'M495 {y+37}H530V150H570',365)
process+=box(570,115,140,80,'4셀 세트 공급',['설비 준비 확인'],True)+box(175,280,160,70,'NG 격리',['LOT별 NG 누계'])
process+=arrow('M125 150H175',365)+arrow('M235 195V280',365)
process+=label(520,320,'동일 LOT의 NG 누계 도달')+label(520,342,'→ 해당 LOT 공급 보류')+'</svg></div>'
roles=table(['구분','성명','담당 범위'],[
['팀장','최예현','일정·범위 관리, 세트 구성, LOT 보류, 실물 설비 연계'],
['팀원','이순필','셀 추적, 검사·등급 판정, PLC 분류 로직'],
['팀원','박해준','Factory I/O 배치, 태그 연결, 설비 동작 검증'],
['팀원','정연우','통신·수집기, DB 및 이력 조회 화면'],
['팀원','김동혁','실측, 시험 기록, 보고서·발표 자료']], [15,17,68],'tight')
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>1) 팀원 구성 및 역할 분담</h3>'''+roles+'''<p class="small">역할은 기존 배정안이며 팀 회의에서 최종 확인함.</p>
<h3>2) 공정과정</h3><h4>(1) 검사·분류·공급 시퀀스</h4>'''+process+cards([
('검사 위치 해제','검사 완료 + 목적지 여유 + 분류 구간 비어 있음'),
('세트 공급 허가','동일 등급 4셀 확보 + 실물 설비 준비 + 진행 세트 없음'),
('공급 완료 확인','실제 4셀 배출 + 출구 감지 + 수신 확인 + 이력 저장')])+'''
<p class="compact">NG 판정에는 전압 미달, 적용 시 저항 초과, LOT 미판독·보류를 포함함. 등급 구간과 적용 검사값은 실측 후 확정함. 이상 해제 후에는 부품 위치와 내부 재고를 대조하여 중복 투입을 방지함.</p>''',4))

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
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정과정</h3><h4>(2) 전체 시스템 및 I/O 연결 구성</h4>'''+architecture+'''
<p class="legend">파란 테두리: 3조 설계 범위 / 회색: 연계 대상 / 점선: 통신·인터록 협의 대상</p>'''+table(['구성','오가는 정보','설계 시 확인할 항목'],[
['가상 설비 ↔ PLC','센서·LOT 판독값 / 컨베이어·푸셔·블레이드 명령','신호 방향, 태그 중복, 통신 단절 시 동작'],
['실물 설비 ↔ PLC','검사 결과·준비 상태 / 공급 요청·수신 확인','실물 공정 담당 범위와 공급 허가 조건'],
['PLC ↔ 수집기 → DB·화면','셀 ID·세트 ID·등급·재고·이상·공급 이벤트','값의 갱신 주기, 이벤트 누락·중복, 조회 항목']], [25,40,35],'tight')+'''
<p class="small">전체 시스템 설계안이며 전기 단자 결선도를 의미하지 않음. 실물 통신 경로와 로봇·비전의 실제 접속 방식은 기존 설비 구성 확인 후 확정함. 가상 부품의 이동은 실물 배터리의 자동 반송과 구분함.</p>''',5))

# 6. Field-level interfaces and explicit boundary with the supplied 4조 plan.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정과정</h3><h4>(3) I/O 신호 및 인계 데이터</h4>
<p>설비 신호, 공급 승인, 이력 데이터를 나누어 관리함. 아래 가상 I/O 주소는 시연용 기준이며 공용 PLC 적용 전 기존 태그와 대조함.</p>'''+table(['신호 구분','현재 가상 설비 연결','내용'],[
['비트 입력 19점','Coils 0~18 → M1000~M1018','위치 검출 7점, 푸셔 끝 센서 8점, 조작반 4점'],
['비트 출력 20점','M1100~M1119 → Discrete Inputs 0~19','컨베이어·푸셔·블레이드·투입·회수·표시등'],
['LOT 판독 1점','Holding Register 0 → D1000','가상 비전 판독값을 LOT 구분에 사용'],
['시뮬레이션 상태','Coils 19 / 20 / 21','실행 / 일시정지 / 씬 초기화']], [25,38,37],'tight')+'''
<h4>공급 승인과 완료 확인</h4>'''+cards([
('① 준비 확인','설비 → 전공정<br>투입 가능·정지·이상 상태 확인'),
('② 세트 공급 요청','전공정 → 설비<br>세트 ID·구성 셀 ID·등급 전달'),
('③ 수신 확인','설비 → 전공정<br>수신 ID 대조 후 다음 세트 허가')])+'''
<h4>조별 이력을 연결할 데이터 항목</h4>'''+table(['담당 구간','관리 단위·필드','연결 목적'],[
['3조 · 전공정','셀 ID, LOT, 전압, 적용 시 내부저항, 판정 등급','셀별 검사·분류 결과 추적'],
['3조 → 실물 설비','세트 ID, 구성 셀 ID 4개, 공급 상태','4셀 구성과 수신 확인 대조'],
['실물 설비 → 4조','제품 ID, LOT, 초기 전압, 검사 결과','4조 에이징·특성검사의 기준 데이터'],
['4조 · 후공정','제품 ID, 재검 횟수, 박스 ID','재검 이력 및 포장 단위 추적']], [25,43,32],'tight')+'''
<div class="keyline"><strong>조별 협의: 셀·세트·제품 단위를 먼저 맞춤</strong><br>3조는 4셀 세트 공급안, 4조 참고 계획서는 1셀 카트리지 인계안을 전제로 함. 셀 수, 실물 조립 단위, 세트 ID와 제품 ID의 대응 관계를 공동 확정한 뒤 최종 인계 규격을 작성함.</div>
<p class="small">4조 계획서는 후공정의 범위와 데이터 구성 참고로 사용함. 후공정의 수치 목표·계측 기준·디바이스 번호는 3조의 확정값으로 사용하지 않음. 실물 전압의 단위와 사전 입력·통신 수신 방식도 공동 규격에 명시함.</p>''',6))

# 7. Equipment and verification chain, with status consolidated here.
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>3) 제어설비 및 검증 계획</h3>'''+table(['구분','규격·용도','확보·적용 계획'],[
['PLC','Mitsubishi MELSEC Q03UDE / 순차 제어·연계','공용 장비 사용 예정'],
['가상 설비','Factory I/O Modbus & OPC 에디션','기설치 / 전공정 배치'],
['제어 프로그램','GX Works2 / 실제 PLC 프로그램 검증','기설치 / 변환·컴파일'],
['수집·이력','Python, DB, 웹 조회 화면','직접 구성 / 상세 기술 확정'],
['검사 데이터','18650 셀 전압 및 적용 시 내부저항','실측 가능 항목·수량 확인'],
['PC','Windows / 가상 설비·수집·화면 실행','보유 장비 1대']], [21,48,31],'tight')+'''
<p class="small">추가 장비 수량·단가는 사양 확인 후 산정함. OPC 서버 확보와 공용 PLC 환경에 따라 통신 경로를 결정함.</p>
<h4>가상 설비 구성</h4>'''+table(['구성 요소','수량','역할'],[
['컨베이어','6','입고 1, 메인 1, 등급 레인 3, 공급 1'],
['푸셔 / 스톱 블레이드','4 / 4','NG·등급 분류 / 검사 위치·레인 끝 정지'],
['검출 센서 / 가상 비전','7 / 1','위치·출구 감지 / LOT 판독'],
['투입기 / 회수기 / 슈트','1 / 2 / 2','가상 셀 입고 / NG·공급 경로 회수']], [40,15,45],'tight')+'''
<h4>현재 상태</h4><p class="compact">2026년 11월 17일 기록 기준, 임시 검사값을 사용하는 소프트 PLC 시연에서 씬 로드·통신·분류 동작을 관찰함. 4셀 공급 통합 시험, 실물 PLC 연계, 수집기·DB·조회 화면은 보완·개발 예정임.</p>
<h4>통합 시험에서 남길 증거</h4>'''+table(['시험 구간','기대 동작','기록 자료'],[
['검사 → 분류','판정 등급과 실제 레인 일치','셀 ID·입력값·판정·진입 레인 대조표'],
['버퍼 → 공급','4셀 확보 후 허가 조건에서만 배출','실제 수량·출구 감지·수신 ID·시간'],
['LOT·이상 처리','보류 LOT 격리, 이상 시 정지','NG 누계·보류 시점·복구 전후 상태'],
['수집 → 조회','셀·세트 이력 연결, 누락·중복 확인','DB 저장값·조회 결과·수정 기록']], [25,35,40],'tight')+'''
<p class="small">실측 데이터 비교 결과와 임시값 기반 제어 시험 결과를 구분함. 시험마다 입력 조건, 기대 동작, 실제 결과와 수정 내용을 함께 남김.</p>''',7,'equipment'))

# 8. Course schedule preserved, deliverables linked to review evidence.
dates=['11/17','18','19','23','24','25','26','27','30','12/1','7','8']
schedule=[('범위·역할·인계 단위',[0,1],1),('통신 경로·태그맵',[1,2],2),('실물 전압 실측',[1,2],None),('가상 전공정 배치',[2,3,4,5],5),('검사·분류 제어',[3,4,5],None),('세트 공급·설비 연계',[5,6,7],None),('수집기·DB·조회 화면',[4,5,6,7,8],None),('시험·비교 측정',[6,7,8,9],7),('기능 동결·보완',[9],9),('보고서·발표',[10,11],11)]
gantt='<table class="gantt"><colgroup><col style="width:30%">'+''.join('<col style="width:5.83%">' for _ in dates)+'</colgroup><thead><tr><th>작업</th>'+''.join(f'<th>{d}</th>' for d in dates)+'</tr></thead><tbody>'
for name,active,gate in schedule:
 gantt+='<tr><td>'+name+'</td>'+''.join(f'<td class="{"gate" if i==gate else "bar" if i in active else ""}">{"◆" if i==gate else "●" if i in active else ""}</td>' for i in range(12))+'</tr>'
gantt+='</tbody></table>'
pages.append(page('''<h2>4. 프로젝트 추진일정</h2><p>2026. 11. 17 ~ 2026. 12. 8 / 수업일 12일 / 3조</p>'''+gantt+'''<p class="small">● 수행 기간 / ◆ 주요 완료 시점. 세부 배정은 실제 수업 일정과 팀 협의 결과에 따라 조정함.</p>
<h3>1) 주요 완료 기준</h3>'''+table(['시점','확인할 결과'],[
['11/19','실물 통신 경로, 조별 담당 범위·인계 단위·ID 대응 규칙 결정'],
['11/25','가상 배치 및 센서·블레이드·푸셔 동작 확정'],
['11/27','분류 정확성·NG 유출·세트 내 전압 편차의 첫 측정 결과'],
['12/1','기능 동결, 4셀 공급·수신 확인·이력 조회의 통합 시험 결과'],
['12/7~12/8','시연 리허설, 최종 보고서·발표 자료 제출']], [22,78],'tight')+'''
<h3>2) 최종 산출물</h3>'''+cards([
('공정·제어 자료','Factory I/O 씬, 태그맵, PLC 프로그램, 통신·인계 규격'),
('이력·시험 자료','셀·세트 이력 구조와 조회 화면, 분류·공급 대조표, 편차 비교표'),
('시연·제출 자료','운전 동영상, 시험·수정 기록, 최종 보고서, 발표 자료')])+'''
<h3>3) 협의와 범위 조정</h3><p class="compact">실물 셀 수량, 내부저항 실측 가능 여부, 등급 구간, 공용 PLC 주소, 4조와의 제품 단위·ID 규칙을 확정함. 실물 통신 확보가 늦어지면 가상 제어 시험과 실물 연계의 평가 범위를 나누어 일정과 산출물에 반영함.</p>''',8))

assert len(pages)==8
assert not any(term in ''.join(pages) for term in ['C 라인','실물 C','C →','→ C','왕 성 식','A팀','B팀'])
document='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>3조 프로젝트 실시 계획서 v0.6</title><style>'+css+'</style></head><body class="p-brief">'+''.join(pages)+'</body></html>'
(BASE/'plan_v0.6.html').write_text(document,encoding='utf-8')
print('Created',BASE/'plan_v0.6.html')
