"""line_v0 씬용 래더 생성 (PoC).

명령어 목록을 만들어 두 파일로 저장한다.
  - line_v0.csv : GX Works2 [편집] -> [CSV 파일에서 읽기]용 (심플 프로젝트, 라벨 없음)
                  형식은 설명서 6.16절 기준: UTF-16 LE + BOM, 탭 구분, 큰따옴표, CR+LF, 앞 3줄은 머리말
  - line_v0.txt : 사람이 읽는 용도. 렁마다 설명이 붙어 있음

동작 개요 (단순화한 PoC)
  - 분류가 끝난 뒤 다음 셀을 투입 (동시에 이동하는 셀은 1개)
  - 검사값은 PLC 안의 표(D2600~, D2620~)에서 꺼냄. 지금 값은 임시
  - 등급 레인은 4개가 차면 스톱 블레이드를 내려 한 세트를 내보냄

사용: python gen_ladder.py <출력 폴더>
"""
import os
import sys

rungs = []          # (설명, [(명령, 피연산자...), ...])


def rung(comment, *ins):
    rungs.append((comment, [tuple(i.split()) for i in ins]))


# 디바이스 대역: 2A는 2000~2999 (11/18 협의). 상세 배정은 docs/interface.md
IN, OUT = 2000, 2100
PUSH = ["NG", "A", "B", "C"]

# ---------------------------------------------------------------- 초기값
rung("첫 스캔: 판정 기준. D2200 전압 하한, D2201 전압 상한(mV), D2202 내부저항 상한(mΩ), D2203 A등급 하한, D2204 B등급 하한, D2205 LOT 보류 NG 횟수",
     "LD SM402", "MOV K3500 D2200", "MOV K3800 D2201", "MOV K60 D2202", "MOV K3750 D2203", "MOV K3650 D2204", "MOV K3 D2205")
VOLT = [3780, 3690, 3620, 3760, 3400, 3660, 3710, 3790]
IR = [35, 38, 42, 36, 40, 75, 37, 39]
rung("첫 스캔: 셀 전압 표 D2600~D2607 (임시값. 실측값으로 바꿀 자리)",
     "LD SM402", *[f"MOV K{v} D{2600 + i}" for i, v in enumerate(VOLT)])
rung("첫 스캔: 셀 내부저항 표 D2620~D2627 (임시값)",
     "LD SM402", *[f"MOV K{v} D{2620 + i}" for i, v in enumerate(IR)])

# ---------------------------------------------------------------- 운전
rung("운전 자기유지 M2300. 정지와 비상정지 버튼은 B접점이라 안 눌렸을 때 ON",
     "LD M2015", "OR M2300", "AND M2016", "AND M2018", "ANI M2390", "OUT M2300")
rung("리셋: 이상, 진행 상태, LOT 보류와 집계를 지움",
     "LD M2017", "RST M2390", "RST M2310", "RST M2311", "RST M2312", "RST M2313", "RST M2330", "RST M2331",
     *[f"RST M{2360 + k}" for k in range(4)], *[f"RST M{2370 + k}" for k in range(4)],
     *[f"RST M{2340 + k}" for k in (1, 2, 3)],
     "FMOV K0 D2440 K4", "FMOV K0 D2450 K4", "FMOV K0 D2500 K10", "BKRST M2500 K10")
rung("표시등: 시작등 = 운전 중", "LD M2300", f"OUT M{OUT + 17}")
rung("표시등: 정지등 = 정지 또는 이상", "LDI M2300", "OR M2390", f"OUT M{OUT + 18}")
rung("표시등: 리셋등 = 이상 발생", "LD M2390", f"OUT M{OUT + 19}")

rung("푸셔가 미는 중이면 M2320 (메인 컨베이어 일시 정지용)",
     "LD M2360", "AND T10", "LD M2361", "AND T11", "ORB", "LD M2362", "AND T12", "ORB", "LD M2363", "AND T13", "ORB", "OUT M2320")
rung("컨베이어: 진입", "LD M2300", f"OUT M{OUT + 1}")
rung("컨베이어: 메인. 푸셔가 밀 때는 멈춤", "LD M2300", "ANI M2320", f"OUT M{OUT + 2}")
rung("컨베이어: 레인 A/B/C, 공급", "LD M2300", f"OUT M{OUT + 9}", f"OUT M{OUT + 11}", f"OUT M{OUT + 13}", f"OUT M{OUT + 15}")

# ---------------------------------------------------------------- 입고
rung("입고 요청 M2310: 진입 구간과 검사 위치가 비어 있으면 셀 하나 투입",
     "LD M2300", "ANI M2310", "ANI M2311", "ANI M2312", "ANI M2313", "ANI M2001", "ANI M2390", "SET M2310")
rung("Emitter를 0.1초 켬: 활성화 때 한 개 생성. 도착까지 M2310 유지",
     "LD M2310", "OUT T0 K1")
rung("", "LD M2310", "ANI T0", "AND M2300", f"OUT M{OUT + 0}")
rung("비전 센서 값이 0이 아니면 D2410에 기억 (지나가는 셀의 LOT. 1=파랑, 4=초록, 7=금속으로 가정)",
     "LD<> D2000 K0", "MOV D2000 D2410")

# ---------------------------------------------------------------- 검사
rung("검사 위치 도착(상승 에지): 셀 ID(D2400) 부여, 표에서 전압(D2420)과 내부저항(D2421)을 꺼내고 LOT(D2412)를 붙임",
     "LDP M2001", "SET M2311", "RST M2310", "INC D2400", "/ D2400 K8 D2402", "MOV D2403 Z1",
     "MOV D2600Z1 D2420", "MOV D2620Z1 D2421", "MOV D2410 D2412", "MOV D2412 Z0", "MOV K0 D2410")
rung("검사 시간 1초", "LD M2311", "OUT T1 K10")
rung("NG 판정 M2350: 전압 미달·초과, 내부저항 초과, LOT 못 읽음(이력 없음), 보류 중인 LOT",
     "LD< D2420 D2200", "OR> D2420 D2201", "OR> D2421 D2202", "OR= D2412 K0", "OR M2500Z0", "OUT M2350")
rung("목적지 D2422: 0=NG, 1=A, 2=B, 3=C", "LD M2350", "MOV K0 D2422")
rung("", "LDI M2350", "AND>= D2420 D2203", "MOV K1 D2422")
rung("", "LDI M2350", "AND< D2420 D2203", "AND>= D2420 D2204", "MOV K2 D2422")
rung("", "LDI M2350", "AND< D2420 D2204", "MOV K3 D2422")
rung("", "LD SM400", "MOV D2422 Z2")
rung("목적지 수용 가능 M2351: NG는 항상 가능, 레인은 예약 4개 미만이고 배출 중이 아닐 때",
     "LD= D2422 K0", "LD< D2440Z2 K4", "ANI M2340Z2", "ORB", "OUT M2351")
rung("검사 위치 출발 허가(1스캔 펄스 M2314): 검사 끝, 수용 가능, 분류 구간 비어 있음",
     "LD M2311", "AND T1", "AND M2351", "ANI M2312", "ANI M2313", "OUT M2314")
rung("출발: 목적지를 분류 구간용 D2423으로 넘기고 스톱 블레이드를 내림(M2313)",
     "LD M2314", "MOV D2422 D2423", "SET M2313")
rung("출발: 레인행이면 그 레인 예약 수 +1", "LD M2314", "AND<> D2422 K0", "INC D2440Z2")
rung("출발: NG면 그 LOT의 NG 횟수 +1, 기준 이상이면 LOT 보류", "LD M2314", "AND M2350", "INC D2500Z0")
rung("", "LD>= D2500Z0 D2205", "AND<> D2412 K0", "AND M2311", "SET M2500Z0")
rung("셀이 검사 센서를 벗어나고 0.3초 뒤 블레이드를 다시 올리고 분류 구간 사용 중(M2312)으로",
     "LD M2313", "ANI M2001", "OUT T2 K3")
rung("", "LD T2", "RST M2313", "RST M2311", "SET M2312")
rung("검사 위치 스톱 블레이드: 평소에는 올림, 출발 때만 내림", "LD M2300", "ANI M2313", f"OUT M{OUT + 3}")

# ---------------------------------------------------------------- 분류 (푸셔 4개)
for k, name in enumerate(PUSH):
    sen, front, back = IN + 4 + 3 * k, IN + 2 + 3 * k, IN + 3 + 3 * k
    rung(f"푸셔 {name}: 자기 앞 센서에 셀이 오고 목적지가 {k}이면 밀기 요청",
         f"LD M{sen}", f"AND= D2423 K{k}", "AND M2312", f"SET M{2360 + k}")
    rung(f"푸셔 {name}: 센서에서 푸셔 중심까지 가는 시간 (조정 필요)", f"LD M{2360 + k}", f"OUT T{10 + k} K3")
    rung("", f"LD M{2360 + k}", f"AND T{10 + k}", f"ANI M{2370 + k}", "AND M2300", f"OUT M{OUT + 4 + k}")
    rung(f"푸셔 {name}: 전진 끝에 닿으면 복귀", f"LD M{2360 + k}", f"AND M{front}", f"SET M{2370 + k}")
    rung(f"푸셔 {name}: 복귀 끝에 닿으면 완료(M{2380 + k}, 1스캔)", f"LD M{2370 + k}", f"AND M{back}", f"OUT M{2380 + k}")
    done = [f"LD M{2380 + k}", f"RST M{2360 + k}", f"RST M{2370 + k}", "RST M2312"]
    if k:
        done.append(f"INC D{2450 + k}")
    rung(f"푸셔 {name}: 완료 처리. 분류 구간 비움" + ("" if not k else f", 레인 {name} 재고 +1"), *done)
rung("운전 중 분류 구간에 20초 넘게 머물면 이상(M2390)", "LD M2312", "AND M2300", "OUT T40 K200")
rung("", "LD T40", "SET M2390")
rung("입고 후 검사 위치 미도착 또는 블레이드 해제 후 미출발 감시",
     "LD M2310", "AND M2300", "OUT T41 K200")
rung("", "LD M2313", "AND M2300", "OUT T42 K50")
rung("", "LD T41", "OR T42", "SET M2390")

# ---------------------------------------------------------------- 레인 배출 (4셀 세트)
for k, name in enumerate(PUSH):
    if not k:
        continue
    rung(f"레인 {name}: 재고 4개, 이동 중인 세트 없음, C 투입 가능(M2332가 OFF)이면 배출 시작",
         f"LD>= D{2450 + k} K4", "ANI M2330", "ANI M2332", f"ANI M{2340 + k}", "AND M2300", f"SET M{2340 + k}", "SET M2330")
    rung(f"레인 {name}: 마지막 셀 이동을 포함해 12초 동안 블레이드를 내려 4개 배출", f"LD M{2340 + k}", f"OUT T{20 + k} K120")
    rung("", f"LD T{20 + k}", f"RST M{2340 + k}", f"MOV K0 D{2450 + k}", f"MOV K0 D{2440 + k}")
    rung(f"레인 {name} 스톱 블레이드", "LD M2300", f"ANI M{2340 + k}", f"OUT M{OUT + 8 + 2 * k}")
rung("세트의 실제 출구 감지를 기억 (타이머만으로 성공 처리하지 않음)",
     "LD M2330", "AND M2014", "SET M2331")
rung("출구 감지 후 배출이 끝나고 출구가 8초 비었을 때만 완료",
     "LD M2330", "AND M2331", "ANI M2341", "ANI M2342", "ANI M2343", "ANI M2014", "OUT T30 K80")
rung("", "LD T30", "RST M2330", "RST M2331", "INC D2460")
rung("공급 배출이 40초 내 완료되지 않으면 이상 정지",
     "LD M2330", "AND M2300", "OUT T31 K400")
rung("", "LD T31", "SET M2390")
rung("끝", "END")


def write(outdir):
    rows = [["line_v0"], ["PLC Information:", "QCPU (Q mode) Q03UDE"],
            ["Step No.", "Line Statement", "Instruction", "I/O (Device)", "Blank", "PI Statement", "Note"]]
    txt = []
    n = 0
    for comment, ins in rungs:
        if comment:
            txt.append("")
            txt.append("; " + comment)
        for op, *args in ins:
            txt.append(("    " + " ".join([op.ljust(6)] + args)).rstrip())
            rows.append(["", "", op, args[0] if args else "", "", "", ""])
            for a in args[1:]:
                rows.append(["", "", "", a, "", "", ""])
            n += 1
    csv = "\r\n".join("\t".join('"' + c.replace('"', '""') + '"' for c in r) for r in rows) + "\r\n"
    with open(os.path.join(outdir, "line_v0.csv"), "wb") as f:
        f.write(b"\xff\xfe" + csv.encode("utf-16-le"))
    with open(os.path.join(outdir, "line_v0.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("; line_v0 래더 (명령어 목록). gen_ladder.py가 만든 파일\n" + "\n".join(txt) + "\n")
    print(f"렁 {len(rungs)}개, 명령 {n}개 -> {outdir}")


if __name__ == "__main__":
    write(sys.argv[1])
