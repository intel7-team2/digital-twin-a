# Writes prj01_signals.md: every Factory I/O tag in prj01 with its Modbus slot and what ON means.
# Usage: python gen_signal_list.py [scene] [out.md]
import re, sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]   # repository root
scene = sys.argv[1] if len(sys.argv) > 1 else root / "factoryio" / "scenes" / "prj01.factoryio"
out = sys.argv[2] if len(sys.argv) > 2 else root / "docs" / "prj01-signals.md"
t = open(scene, encoding="utf-8-sig").read()
key_name = {k: n for n, k in re.findall(r'<(?:Binary|Int|Analogue)\w+ Name="([^"]+)" Address="\d+" Key="([^"]+)"', t)}
drv = re.search(r"<ModbusTCPClient>(.*?)</ModbusTCPClient>", t, re.S).group(1)
slot = {}
for kind, n, key in re.findall(r'<(BitInput|BitOutput|NumericInput|NumericOutput)(\d+) PointIOKey="([^"]+)"', drv):
    if key in key_name:
        slot[key_name[key]] = (kind, int(n))
forced = set(re.findall(r'Name="([^"]+)" Address="\d+" Key="[^"]+" OpenCircuit="False" ShortCircuit="False" UseForcedValue="True"', t))

ZONE = {"Z1": "Z1 투입", "Z2": "Z2 분배", "Z3": "Z3 스테이션·합류", "Z4": "Z4 재판독·분류", "Z5": "Z5 팔레트 적재", "PB": "조작반",
        "SE": "조작반", "LA": "조작반", "EN": "Z4 재판독·분류"}

def meaning(n):
    rules = [
        (r"_BELT(_\d)?$|_ROLLER$", "컨베이어", "ON = 벨트 구동"),
        (r"^Z1_EMITTER$", "셀 생성기", "ON 동안 2~3초마다 셀 1개. 투입 대기 3개 미만일 때만 ON"),
        (r"^Z1_IN_SENS$", "투입 센서", "ON = 투입 벨트에 셀 있음"),
        (r"^Z1_LOT_VISION$", "투입 QR(비전)", "읽은 값 = 셀 색(LOT). 0 = 없음"),
        (r"^Z2_GATE$", "분배 게이트 스톱", "ON = 날 올림(셀 정지), OFF = 날 내림(통과)"),
        (r"^Z2_AT_GATE$", "게이트 센서", "ON = 게이트 앞에 셀 대기"),
        (r"^Z2_AT_PUSH_(\d)$", "분배 푸셔 앞 센서", "ON = 셀이 푸셔 0.625 m 앞을 지나는 중"),
        (r"^Z2_PUSH_(\d)$", "분배 푸셔", "ON = 밀기(앞으로). OFF = 복귀"),
        (r"_FWD$", "푸셔 앞 끝", "ON = 끝까지 밀었음"),
        (r"_BWD$", "푸셔 뒤 끝", "ON = 원위치"),
        (r"^Z3_ST\d_IN$", "스테이션 입구 센서", "ON = 기계 입구에 셀 대기"),
        (r"^Z3_ST\d_OUT$", "스테이션 출구 센서", "ON = 가공 끝난 셀이 출구 끝에 있음"),
        (r"^Z3_ST\d_START$", "기계 시작", "0.5초 펄스. 입구에 셀이 있고 기계가 쉬고 있을 때"),
        (r"^Z3_ST\d_STOP$", "기계 정지", "ON = 정지"),
        (r"^Z3_ST\d_RESET$", "기계 리셋", "ON = 리셋"),
        (r"^Z3_ST\d_LIDS$", "뚜껑/베이스 선택", "OFF 강제 = 베이스 생산"),
        (r"^Z3_ST\d_BUSY$", "기계 가공 중", "ON = 가공 중(사용 중)"),
        (r"^Z3_ST\d_ERROR$", "기계 이상", "ON = 입구에 잘못된 물건"),
        (r"^Z3_ST\d_OPEN$", "기계 문", "ON = 문 열림"),
        (r"^Z3_ST\d_PROGRESS$", "가공 진행률", "0~100"),
        (r"^Z3_MERGE_(\d)$", "합류 감시 센서", "ON = 수집 벨트 합류 지점 바로 앞에 셀 → 옆 레인 대기"),
        (r"^Z4_QR_RESCAN$", "재판독 QR(비전)", "읽은 값 = 셀 색. 0 = 없음"),
        (r"^Z4_AT_PUSH_(\w+)$", "분류 푸셔 앞 센서", "ON = 셀이 푸셔 0.625 m 앞을 지나는 중"),
        (r"^Z4_PUSH_(\w+)$", "분류 푸셔", "ON = 밀기. OFF = 복귀"),
        (r"^Z4_NG_CONFIRM$", "NG 확인 센서", "ON = NG 벨트에 셀 있음"),
        (r"^Z4_NG_REMOVER$", "NG 제거", "항상 ON (강제)"),
        (r"^END_REMOVER$", "분류 안 된 셀 제거", "항상 ON (강제)"),
        (r"^Z4_LANE_\w_FULL$", "레인 입구 센서", "ON = 레인이 입구까지 참"),
        (r"^Z4_LANE_\w_HEAD$", "레인 끝 센서", "ON = 레인 맨 앞에 셀 대기"),
        (r"^Z4_LANE_\w_STOP$", "레인 끝 스톱", "ON = 막음. 4개 묶음을 보낼 때만 OFF"),
        (r"^Z4_LANE_\w$", "레인 컨베이어", "ON = 구동"),
        (r"^Z5_CELL_COUNT$", "패키징 투입 센서", "ON = 셀 통과"),
        (r"^Z5_AT_PICK$", "집는 위치 센서", "ON = 셀이 Pick & Place 아래 도착"),
        (r"^Z5_PNP_SP_(\w)$", "Pick & Place 목표 위치", "0~10 V (Modbus 값 = V × 100)"),
        (r"^Z5_PNP_(X|Y|Z)$", "Pick & Place 현재 위치", "0~10 V (Modbus 값 = V × 100)"),
        (r"^Z5_PNP_DETECTED$", "그리퍼 아래 물체", "ON = 집을 물체 감지"),
        (r"^Z5_PNP_GRAB$", "그리퍼", "ON = 잡기"),
        (r"^Z5_PNP_C_LIMIT$", "그리퍼 회전 끝", "ON = 회전 끝"),
        (r"^Z5_PNP_C_TURN$", "그리퍼 회전", "ON = 회전 (사용 안 함)"),
        (r"^Z5_PALLET_EMIT$", "팔레트 생성", "0.15초 펄스 = 빈 팔레트 1장"),
        (r"^Z5_PALLET_AT_PLACE$", "팔레트 위치 센서", "ON = 팔레트가 적재 위치에 있음"),
        (r"^Z5_TO_2B$", "2B 인계(제거)", "항상 ON (강제). 팔레트+셀 4개를 지움 = 다음 공정으로 넘어감"),
        (r"^PB_(\w+)_LAMP$", "버튼 램프", "ON = 점등"),
        (r"^PB_ESTOP$", "비상정지 버튼", "OFF = 눌림 (NC)"),
        (r"^PB_(\w+)$", "조작반 버튼", "ON = 누르는 중"),
        (r"^SEL_ASSY_READY$", "선택 스위치", "ON = 후공정 준비"),
        (r"^LAMP_(\w+)$", "경광등", "ON = 점등"),
    ]
    for pat, what, on in rules:
        if re.search(pat, n):
            return what, on
    return "", ""

KIND = {"BitInput": ("센서 → PLC", "Coil"), "BitOutput": ("PLC → 장치", "Discrete Input"),
        "NumericInput": ("값 → PLC", "Holding Register"), "NumericOutput": ("PLC → 값", "Input Register")}
rows = {k: [] for k in KIND}
for n, (kind, idx) in slot.items():
    what, on = meaning(n)
    if n in forced:
        on += " (장면에서 강제)" if "강제" not in on else ""
    rows[kind].append((idx, n, ZONE.get(n[:2], ""), what, on))

lines = ["# prj01 신호표", "",
         "`factoryio/tools/gen_signal_list.py`가 장면(factoryio/scenes/prj01.factoryio)에서 만든 표. 장면을 다시 만들면 이것도 다시 만든다.", "",
         "- 번호 = Factory I/O Modbus 슬롯 번호. 팀 규칙대로 옮기면 센서 n → M2000+n, 출력 n → M2100+n, 값 n → D2000+n.",
         f"- 센서 다음 슬롯 {len(rows['BitInput'])}~{len(rows['BitInput']) + 2}은 Factory I/O 실행/일시정지/리셋 상태.",
         "- 숫자 값은 ScaleFactor 100: 레지스터 값 = 실제 값 × 100.", ""]
for kind, (title, reg) in KIND.items():
    lines += [f"## {title} ({reg})", "", "| 번호 | 태그 | 구역 | 무엇 | 켜짐(ON)의 뜻 |", "|---|---|---|---|---|"]
    lines += [f"| {i} | `{n}` | {z} | {w} | {o} |" for i, n, z, w, o in sorted(rows[kind])]
    lines.append("")
open(out, "w", encoding="utf-8").write("\n".join(lines))
print(out, {k: len(v) for k, v in rows.items()})
