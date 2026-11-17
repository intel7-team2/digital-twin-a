"""Rebuild the project plan using the supplied HWP form's section order."""
from pathlib import Path
import html
import re
import zlib
from read_hwp import Compound

BASE=Path(__file__).resolve().parents[1]
ASSETS=BASE/'assets'
ASSETS.mkdir(exist_ok=True)
if not (ASSETS/'institution-logo.png').exists():
    import sys
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
pages=[]
pages.append(page('''<div class="course">[인텔] AI 융합 DX 마스터 클래스<br>프로젝트 실시 계획서</div>
<div class="task">【 과제명 】<br>배터리 셀 입고검사 및 매칭 공급 라인<br>디지털 트윈</div>
<table class="info"><tbody><tr><th>교과목명</th><td style="color:#0666ff;font-weight:700">[인텔] AI 융합 DX 마스터 클래스</td></tr><tr><th>지도교수</th><td>왕 성 식</td></tr><tr><th>팀 구분</th><td>A팀</td></tr><tr><th>팀 장</th><td>최예현</td></tr><tr><th>팀 원</th><td>이순필, 박해준, 정연우, 김동혁</td></tr></tbody></table>
<img class="logo" src="assets/institution-logo.png" alt="대한상공회의소 부산인력개발원">''',1,'cover'))

pages.append(page('''<h1>배터리 셀 입고검사 및 매칭 공급 라인<br>디지털 트윈 프로젝트 계획서</h1>
<h2>1. 프로젝트 개요</h2>
<p class="indent">실물 배터리 팩 라인 C의 앞단에 셀 입고검사, LOT 추적, NG 분리, 등급별 분류 및 4셀 세트 공급 공정을 가상으로 구성하고자 함. Factory I/O에서 설비 배치와 제어 순서를 검증한 후 MELSEC Q PLC 및 실물 C 라인과의 연계를 추진하여 공정 설계와 시스템 상호 운용 능력을 향상하고자 함.</p>
<p class="indent">셀의 전압과 내부저항에 따라 등급을 판정하고, 같은 등급 4개를 한 세트로 공급함. 특정 LOT의 NG가 반복되면 해당 LOT의 공급을 보류하고, 향후 셀 ID와 세트 ID를 실물 C의 팩 이력까지 연결할 계획임.</p>
<h2>2. 프로젝트 목표</h2>
<ol class="goals"><li><strong>공정개발 및 시스템 설계 능력과 I/O 및 Interface 활용 능력 향상</strong><ol><li>Factory I/O의 컨베이어, 센서, 푸셔, 스톱 블레이드를 이용한 전공정 설계</li><li>PLC 래더를 이용한 검사, 등급 판정, 분류 및 버퍼 재고 관리</li><li>비전 판독값을 이용한 LOT 구분과 이상 LOT 공급 보류</li><li>실물 C의 투입 가능 상태에 따른 세트 공급 인터록 및 통신 연계</li></ol></li>
<li><strong>시운전 및 피드백을 통한 공정 수정보완 능력 향상</strong><ol><li>판정 등급과 실제 진입 레인을 대조하여 분류 정확성 확인</li><li>4셀 적재, 블레이드 해제, 공급 컨베이어 이동 및 출구 감지 검증</li><li>정지, 비상정지, 부품 걸림 및 통신 단절에 대한 동작 시험</li></ol></li>
<li><strong>보고서와 포트폴리오 작성 및 프리젠테이션 능력 향상</strong><ol><li>시험 조건, 측정 결과, 오류 원인과 수정 이력 정리</li><li>운전 동영상, 공정 설명 자료 및 최종 보고서 제작</li></ol></li></ol>
<h3>주요 평가 기준안</h3>'''+table(['항목','목표','평가 방법'],[
['전압 편차','기준 대비 50% 이상 감소','동일 셀 데이터의 순서별 4셀 세트와 등급별 세트 비교'],
['분류 및 NG 차단','100셀 분류 오류 0건<br>NG 공급 유출 0건','셀 ID별 판정 결과와 실제 경로 대조'],
['LOT 보류','동일 LOT의 세 번째 NG에서 보류','LOT별 NG 누계와 보류 후 경로 확인'],
['세트 공급','동일 등급 4셀 단위 공급','실제 배출 수량과 출구 감지 및 완료 신호 확인']], [22,29,49],'tight')+'''<p class="small">※ 목표값은 실측과 첫 통합 시험 후 조정함. 현재 시연의 전압·내부저항은 임시 표 값이며, 실측에 근거한 성능 개선 결과가 아님.</p>''',2))

roles=table(['구 분','성 명','역 할'],[
['팀 장','최예현','프로젝트 관리, 세트 구성, LOT 보류, 실물 C 연계'],
['팀 원','이순필','셀 추적, 검사 및 등급 판정, PLC 분류 로직'],
['팀 원','박해준','Factory I/O 씬 제작, 태그 연결, 설비 동작 검증'],
['팀 원','정연우','통신 구성, 수집기, DB 및 이력 조회 화면'],
['팀 원','김동혁','실물 데이터 실측, 시험 기록, 보고서 및 발표 자료']], [17,18,65])
sequence=table(['입 고','검 사','NG 분리','분류 및 버퍼','세트 공급'],[
['① 셀 한 개 투입<br>② LOT 판독<br>③ 검사 도착 시 ID 부여','① 검사 위치 정지<br>② 전압·저항값 연결<br>③ NG 및 등급 판정','① NG 위치 감지<br>② 푸셔 전진·복귀<br>③ LOT별 NG 누계','① A·B·C 레인 분류<br>② 예약·재고 관리<br>③ 4셀 확보까지 대기','① 한 레인씩 배출<br>② 출구 감지 확인<br>③ C 공급 완료 연계']], [20,20,20,20,20])
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>1) 팀원 구성 및 역할 분담</h3>'''+roles+'''<p class="small">※ 역할 분담은 기존 계획서의 배정안을 따르며, 팀 회의에서 최종 확인함.</p>
<h3>2) 공정과정</h3><h4>(1) 공정 시퀀스</h4><div class="flow"><div class="box">입고</div><span class="arrow">→</span><div class="box">검사</div><span class="arrow">→</span><div class="box">NG 분리</div><span class="arrow">→</span><div class="box">등급별 버퍼</div><span class="arrow">→</span><div class="box">4셀 공급</div></div>'''+sequence+'''
<h4>① 셀 입고 및 검사</h4><p>이전 셀의 분류가 끝난 뒤 다음 셀을 투입함. 검사 위치 도착 시 셀 ID와 LOT를 연결하고 전압 및 내부저항 데이터를 읽어 판정함. 목적지 레인에 수용 여유가 있을 때 검사 위치 블레이드를 해제함.</p>
<h4>② NG 분리 및 등급 분류</h4><p>전압 미달, 저항 초과, LOT 미판독 또는 보류 LOT는 NG 경로로 배출함. 합격 셀은 A·B·C 레인으로 분류하고 푸셔 전진 및 복귀 끝 센서로 동작 완료를 확인함. 푸셔가 미는 동안 메인 컨베이어를 정지함.</p>
<h4>③ 버퍼 및 세트 공급</h4><p>각 레인은 예약 수와 분류 완료 재고를 관리함. 같은 등급의 셀 4개가 모이면 한 레인씩 공급 컨베이어로 내보내고, 출구 감지와 공백 시간을 확인하여 완료 처리함. 실제 C 연계 시에는 준비·완료·수신 확인 신호를 추가하여 공급 허가를 구성함.</p>
<h4>④ 이상 정지 및 복구</h4><p>비상정지, 미도착, 검사 위치 미출발, 분류 및 공급 시간 초과를 감시함. 새 시연은 가상 부품과 내부 재고가 일치하도록 Factory I/O를 초기 상태로 되돌린 뒤 시작함.</p>''',3))

io_diagram='''<svg viewBox="0 0 780 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="가상 설비와 제어기 사이의 I/O 연결 구성도"><defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#333"/></marker></defs><g font-family="Malgun Gothic,sans-serif" fill="#000" font-size="16"><rect x="10" y="32" width="220" height="205" fill="#fff" stroke="#333"/><text x="120" y="65" text-anchor="middle" font-weight="bold">Factory I/O 가상 설비</text><text x="30" y="102">검출 센서와 조작반</text><text x="30" y="132">LOT 비전 센서</text><text x="30" y="177">컨베이어와 푸셔</text><text x="30" y="207">블레이드와 표시등</text><rect x="495" y="32" width="275" height="205" fill="#fff" stroke="#333"/><text x="633" y="65" text-anchor="middle" font-weight="bold">현재 소프트 PLC 제어기</text><text x="513" y="102">M1000 ~ M1018</text><text x="513" y="132">D1000</text><text x="513" y="178">M1100 ~ M1119</text><text x="633" y="213" text-anchor="middle" font-size="13">향후 MELSEC Q 연계 검증</text><g stroke="#333" stroke-width="1.6" marker-end="url(#ah)"><path d="M230 98H490"/><path d="M230 130H490"/><path d="M495 180H235"/></g><text x="363" y="89" text-anchor="middle" font-size="12">센서 및 조작반 비트 입력</text><text x="363" y="123" text-anchor="middle" font-size="12">LOT 판독값</text><text x="363" y="170" text-anchor="middle" font-size="12">액추에이터 비트 출력</text><text x="362" y="228" text-anchor="middle" font-size="14">Modbus TCP 127.0.0.1:502</text></g></svg>'''
tags=table(['구 분','Factory I/O 및 통신 주소','제어기 디바이스'],[
['센서 입력 19점','Coils 0 ~ 18','M1000 ~ M1018'],
['액추에이터 출력 20점','Discrete Inputs 0 ~ 19','M1100 ~ M1119'],
['비전 입력 1점','Holding Register 0','D1000'],
['실행·일시정지·씬 리셋','Coils 19 / 20 / 21','소프트 PLC의 시뮬레이션 상태 관리']], [25,41,34])
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>2) 공정과정</h3><h4>(2) I/O 결선도</h4><p>현재 가상 설비는 물리 배선 대신 Modbus TCP로 센서와 액추에이터 신호를 연결함. 아래 구성은 가상 설비의 신호 연결도이며, 실제 PLC 단자 결선도는 통신 장비와 C 라인 태그를 확인한 뒤 별도로 작성함.</p>'''+io_diagram+'''<p class="caption">가상 설비 I/O 연결 구성도</p>'''+tags+'''
<h4>신호 구성</h4><p>비트 입력은 검출 센서 7점, 푸셔 전진·복귀 끝 센서 8점, 조작반 4점으로 구성함. 비트 출력은 컨베이어 6점, 푸셔 4점, 스톱 블레이드 4점, Emitter 1점, Remover 2점, 표시등 3점으로 구성함.</p>
<h4>실물 C 라인과의 연계 계획</h4>'''+table(['방 향','연계 신호','용 도'],[
['C → 전공정','투입 가능, 정지 및 이상 상태','실물 C가 준비된 경우에만 세트 공급'],
['전공정 → C','세트 준비, 세트 ID 및 셀 ID 4개','공급 요청과 팩 구성 이력 연결'],
['C → 전공정','세트 수신 확인','중복 공급 방지 및 다음 세트 허가'],
['전공정 → C','버퍼 고갈, 라인 이상','대기 또는 이상 상태 표시']], [22,39,39],'tight')+'''<p class="small">※ 실물 C와의 신호 교환 및 셀 ID 4개를 보존하는 세트 이력은 개발 예정임. 현재 임시 태그 번호를 실제 공용 PLC에 그대로 적용하지 않고 중복 여부를 확인함.</p>''',4))

equip=table(['구 분','규 격 및 용도','수 량','단 가'],[
['P L C','Mitsubishi MELSEC Q03UDE<br>실물 C와의 연계 제어 목표','공용 사용 예정','보유 장비'],
['가상 설비','Factory I/O Modbus & OPC 에디션','1식','기설치'],
['프로그래밍','GX Works2<br>실제 PLC 래더 변환 및 검증','1식','기설치'],
['소프트 PLC','Python 기반 명령어 목록 실행기<br>현재 가상 라인 시연용','1식','자체 제작'],
['P C','Windows PC<br>가상 설비 및 제어기 실행','1대','보유 장비'],
['검사 데이터','18650 셀 및 C 1차 검사기<br>전압 실측 데이터 확보','확인 후 결정','확인 필요']], [19,49,16,16],'tight')
parts=table(['가상 설비 부품','수 량','구 성'],[
['Belt Conveyor','6','입고 1, 메인 1, 등급 레인 3, 공급 1'],
['Pusher / Stop Blade','4 / 4','NG 및 등급별 분류 / 검사 위치와 레인 끝 정지'],
['검출 센서 / Vision Sensor','7 / 1','위치 및 출구 감지 / LOT 판독'],
['Emitter / Remover / Chute','1 / 2 / 2','셀 투입 / NG 및 공급 경로 회수']], [37,16,47],'tight')
pages.append(page('''<h2>3. 프로젝트 계획</h2><h3>3) 제어설비</h3>'''+equip+'''<p class="small">※ 수량과 단가는 현재 확보 범위에 맞추어 기재함. HMI, OPC 서버, 실물 센서 및 추가 통신 장비는 사양과 사용 여부가 확정된 뒤 반영함.</p>
<h4>(1) PLC 및 프로그래밍</h4><p>최종 제어기는 MELSEC Q03UDE를 목표로 하며 GX Works2에서 프로그램 변환·컴파일 및 실제 통신을 검증할 계획임. 현재 생성된 CSV 및 명령어 목록은 실물 PLC 구동 완료를 의미하지 않음.</p>
<h4>(2) Factory I/O 가상 설비</h4>'''+parts+'''
<h4>(3) 통신 및 소프트 PLC</h4><p>현재는 Factory I/O의 Modbus TCP/IP Client와 Python 소프트 PLC를 연결하여 시연함. 실제 PLC 연계는 OPC 서버 확보 여부와 공용 PLC 환경을 확인한 뒤 확정함.</p>
<h4>(4) 현재 시운전 상태와 보완 사항</h4><p>씬 로드와 신호 연결, NG 및 A·B·C 분류 동작을 관찰하였으며 소프트 PLC 자동 검사 8개를 통과함. 다만 최종 통합 시험에서 4셀 공급 완료가 확인되지 않고 이상 플래그가 발생하여 블레이드 위치, 실제 배출 수량 및 출구 감지를 추가 검증해야 함.</p>
<p class="small">※ 전압 및 내부저항은 현재 임시 표 값임. 셀·세트 이력 수집기, DB와 조회 화면은 후속 개발 범위이며, 별도 HMI 장비 사용 여부는 협의 후 결정함.</p>''',5))

dates=['11/17','18','19','23','24','25','26','27','30','12/1','7','8']
schedule=[('계획서 및 범위 확정',[0,1],1),('통신 경로 및 태그맵',[1,2],2),('실물 전압 실측',[1,2],None),('Factory I/O 씬 보완',[2,3,4,5],5),('검사 및 분류 래더',[3,4,5],None),('세트 공급 및 C 연계',[5,6,7],None),('수집기·DB·화면',[4,5,6,7,8],None),('시험 및 측정',[6,7,8,9],7),('기능 동결 및 보완',[9],9),('보고서 및 발표',[10,11],11)]
gantt='<table class="gantt"><colgroup><col style="width:30%">'+''.join('<col style="width:5.83%">' for _ in dates)+'</colgroup><thead><tr><th>작 업</th>'+''.join(f'<th>{d}</th>' for d in dates)+'</tr></thead><tbody>'
for name,active,gate in schedule:
    gantt+='<tr><td>'+name+'</td>'+''.join(f'<td class="{"gate" if i==gate else "bar" if i in active else ""}">{"◆" if i==gate else "●" if i in active else ""}</td>' for i in range(12))+'</tr>'
gantt+='</tbody></table>'
pages.append(page('''<h2>4. 프로젝트 추진일정</h2><table class="tight"><tbody><tr><th style="width:25%">프로젝트 기간</th><td>2026. 11. 17 ~ 2026. 12. 8 / 수업일 12일</td></tr><tr><th>팀 구분</th><td>A팀 / 배터리 셀 입고검사 및 매칭 공급 라인 디지털 트윈</td></tr></tbody></table>'''+gantt+'''<p class="small">● 수행 기간 / ◆ 주요 완료 시점. 실제 수업 일정과 팀 협의 결과에 따라 세부 배정은 조정함.</p>
<h3>1) 주요 완료 기준</h3>'''+table(['일 정','완료 기준'],[
['11/19','실물 PLC 통신 경로 및 태그 사용 범위 결정'],
['11/25','가상 씬 배치와 센서·블레이드·푸셔 동작 확정'],
['11/27','분류 정확성, NG 유출 및 전압 편차의 첫 측정 결과 확보'],
['12/1','기능 동결 및 통합 시운전 결과 정리'],
['12/7 ~ 12/8','시연 리허설, 최종 보고서와 발표 자료 제출']], [25,75],'tight')+'''
<h3>2) 사전 협의 사항</h3><p>팀원별 역할, 실물 셀 수량과 내부저항 실측 가능 여부, 등급 기준, 공용 PLC 통신 경로, C 및 B팀과의 ID 규칙과 신호 주소를 확정함. 실물 PLC 연결이 지연되면 소프트 PLC 시연과 실제 연계의 구현 범위를 분리하여 보고함.</p>
<h3>3) 최종 산출물</h3><p>Factory I/O 씬, 태그맵, PLC 제어 프로그램, 통신 설정서, 셀·세트 이력 구조, 시험 기록, 운전 동영상, 최종 보고서 및 발표 자료를 제출함. 각 산출물에는 구현 범위와 실제 검증 결과를 함께 기록함.</p>''',6))

document='<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>A팀 프로젝트 실시 계획서</title><style>'+css+'</style></head><body>'+''.join(pages)+'</body></html>'
(BASE/'plan_v0.4.html').write_text(document,encoding='utf-8')
print('Created',BASE/'plan_v0.4.html')
