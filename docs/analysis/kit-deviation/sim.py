"""세트 안 전압 편차 비교 시뮬레이션 (순서대로 4개 vs A/B/C 구간별 4개).

PLC·Factory I/O 없이 계획서 핵심 지표(세트 편차 50% 감소)를 미리 확인하는 용도.
셀 전압은 실측값이 아니라 가정한 분포에서 뽑는다. 가정은 아래 Scenario에 모아 뒀다.

    python docs/analysis/kit-deviation/sim.py            # 결과 표 출력 + results.md, figure.svg 생성
    python docs/analysis/kit-deviation/sim.py --print    # 파일 안 쓰고 표만

외부 패키지 없이 표준 라이브러리만 쓴다.
"""

from __future__ import annotations

import argparse
import random
import statistics
from collections import deque
from dataclasses import dataclass, field, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT_SIZE = 4


@dataclass(frozen=True)
class Scenario:
    name: str
    cells: int = 100                      # 한 회차 투입 셀 수 (계획서 100셀 시험)
    lot_means: tuple = (3640, 3680, 3720)  # LOT별 평균 OCV [mV] (가정)
    lot_sd: float = 40.0                  # LOT 안 표준편차 [mV] (가정)
    lot_block: int = 10                   # 같은 LOT가 연달아 들어오는 수 (가정)
    defect_rate: float = 0.05             # 규격 이탈 셀 비율 (가정)
    spec: tuple = (3500, 3800)            # 합격 하한·상한, interface.md D2200/D2201
    bounds: tuple = (3650, 3750)          # B 하한, A 하한, interface.md D2204/D2203
    lane_cap: int = 4                     # 레인 버퍼 (factoryio-v1-build-plan Z4)


@dataclass
class Result:
    order_ranges: list = field(default_factory=list)
    bin_ranges: list = field(default_factory=list)
    order_kits: int = 0
    bin_kits: int = 0
    bin_left: int = 0          # 회차 끝에 레인에 남은 합격 셀
    bin_waits: list = field(default_factory=list)  # 셀이 레인에서 기다린 투입 간격 수
    passed: int = 0


def make_cells(sc: Scenario, rng: random.Random) -> list[int]:
    """투입 순서대로 OCV [mV] 목록. LOT는 lot_block개씩 돌아가며 들어온다."""
    cells = []
    for i in range(sc.cells):
        mean = sc.lot_means[(i // sc.lot_block) % len(sc.lot_means)]
        if rng.random() < sc.defect_rate:
            # 규격 밖 셀: 상한 위 또는 하한 아래로 확실히 보냄
            v = rng.choice([rng.uniform(sc.spec[0] - 200, sc.spec[0] - 1),
                            rng.uniform(sc.spec[1] + 1, sc.spec[1] + 100)])
        else:
            v = rng.gauss(mean, sc.lot_sd)
        cells.append(round(v))
    return cells


def grade(v: int, bounds: tuple) -> str:
    b_low, a_low = bounds
    if v >= a_low:
        return "A"
    if v >= b_low:
        return "B"
    return "C"


def kit_range(kit) -> int:
    return max(kit) - min(kit)


def run_once(sc: Scenario, rng: random.Random) -> Result:
    cells = make_cells(sc, rng)
    lo, hi = sc.spec
    passed = [(t, v) for t, v in enumerate(cells) if lo <= v <= hi]
    r = Result(passed=len(passed))

    # 방식 1: 합격 셀을 들어온 순서대로 4개씩
    for i in range(0, len(passed) - KIT_SIZE + 1, KIT_SIZE):
        r.order_ranges.append(kit_range([v for _, v in passed[i:i + KIT_SIZE]]))
    r.order_kits = len(r.order_ranges)

    # 방식 2: 구간별 레인에 쌓다가 4개 차면 세트로 내보냄.
    # 레인 용량이 KIT_SIZE면 4개째가 들어오는 순간 바로 나가므로 막힘은 없다.
    lanes = {g: deque() for g in "ABC"}
    for t, v in passed:
        lane = lanes[grade(v, sc.bounds)]
        lane.append((t, v))
        if len(lane) == KIT_SIZE:
            kit = [lane.popleft() for _ in range(KIT_SIZE)]
            r.bin_ranges.append(kit_range([x for _, x in kit]))
            r.bin_waits.extend(t - tt for tt, _ in kit)
    r.bin_kits = len(r.bin_ranges)
    r.bin_left = sum(len(q) for q in lanes.values())
    return r


def summarize(sc: Scenario, runs: int = 300, seed: int = 1) -> dict:
    rng = random.Random(seed)
    order_means, bin_means, reductions = [], [], []
    order_kits, bin_kits, left, waits, waits_max = [], [], [], [], []
    for _ in range(runs):
        r = run_once(sc, rng)
        if not r.order_ranges or not r.bin_ranges:
            continue
        om = statistics.fmean(r.order_ranges)
        bm = statistics.fmean(r.bin_ranges)
        order_means.append(om)
        bin_means.append(bm)
        reductions.append((om - bm) / om * 100)
        order_kits.append(r.order_kits)
        bin_kits.append(r.bin_kits)
        left.append(r.bin_left)
        waits.append(statistics.fmean(r.bin_waits))
        waits_max.append(max(r.bin_waits))

    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]

    return {
        "scenario": sc,
        "order_mv": statistics.fmean(order_means),
        "bin_mv": statistics.fmean(bin_means),
        "reduction": statistics.fmean(reductions),
        "reduction_p5": pct(reductions, 5),
        "reduction_p95": pct(reductions, 95),
        "order_kits": statistics.fmean(order_kits),
        "bin_kits": statistics.fmean(bin_kits),
        "left": statistics.fmean(left),
        "wait": statistics.fmean(waits),
        "wait_max": statistics.fmean(waits_max),
    }


def equal_count_bounds(sc: Scenario, seed: int = 99, n: int = 20000) -> tuple:
    """합격 셀이 A/B/C에 1/3씩 가도록 경계를 잡는다 (같은 가정 분포에서)."""
    rng = random.Random(seed)
    big = replace(sc, cells=n)
    vs = sorted(v for v in make_cells(big, rng) if sc.spec[0] <= v <= sc.spec[1])
    return (vs[len(vs) // 3], vs[2 * len(vs) // 3])


BASE = Scenario("기준 가정")


def scenarios() -> list[Scenario]:
    eq = equal_count_bounds(BASE)
    return [
        BASE,
        replace(BASE, name="LOT 안 편차 작음 (sd 20)", lot_sd=20.0),
        replace(BASE, name="LOT 안 편차 큼 (sd 60)", lot_sd=60.0),
        replace(BASE, name="LOT 평균 같음 (3680 하나)", lot_means=(3680,)),
        replace(BASE, name="LOT 섞여 들어옴 (block 1)", lot_block=1),
        replace(BASE, name=f"경계 1/3씩 ({eq[0]}/{eq[1]})", bounds=eq),
        replace(BASE, name="경계 좁힘 (3660/3700)", bounds=(3660, 3700)),
        replace(BASE, name="1000셀 (장시간)", cells=1000),
    ]


def table(rows: list[dict]) -> str:
    head = ("| 시나리오 | 순서 평균 편차 | 구간 평균 편차 | 감소율 (5~95%) | 세트 수 순서/구간 "
            "| 남은 셀 | 대기 평균/최대 |\n|---|---:|---:|---:|---:|---:|---:|")
    lines = [head]
    for r in rows:
        lines.append(
            f"| {r['scenario'].name} | {r['order_mv']:.0f} mV | {r['bin_mv']:.0f} mV "
            f"| **{r['reduction']:.0f}%** ({r['reduction_p5']:.0f}~{r['reduction_p95']:.0f}) "
            f"| {r['order_kits']:.1f} / {r['bin_kits']:.1f} | {r['left']:.1f} "
            f"| {r['wait']:.1f} / {r['wait_max']:.0f} |")
    return "\n".join(lines)


def svg(rows: list[dict]) -> str:
    """시나리오별 순서/구간 평균 편차 막대. 보고서 그림용."""
    w, bar_h, gap, left, top = 760, 14, 14, 250, 40
    scale = (w - left - 110) / max(r["order_mv"] for r in rows)
    h = top + len(rows) * (2 * bar_h + gap) + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'font-family="Malgun Gothic, sans-serif" font-size="12">',
           f'<rect width="{w}" height="{h}" fill="#fff"/>',
           '<text x="16" y="22" font-size="14" font-weight="bold">세트 안 전압 편차 (max−min) 평균 (회차 300번)</text>',
           f'<rect x="{w-220}" y="12" width="12" height="12" fill="#9aa5b1"/>'
           f'<text x="{w-202}" y="22">순서대로 4개</text>',
           f'<rect x="{w-120}" y="12" width="12" height="12" fill="#2f6fde"/>'
           f'<text x="{w-102}" y="22">구간별 4개</text>']
    y = top
    for r in rows:
        out.append(f'<text x="{left-8}" y="{y+bar_h+4}" text-anchor="end">{r["scenario"].name}</text>')
        for key, color, dy in (("order_mv", "#9aa5b1", 0), ("bin_mv", "#2f6fde", bar_h)):
            bw = r[key] * scale
            out.append(f'<rect x="{left}" y="{y+dy}" width="{bw:.1f}" height="{bar_h-2}" fill="{color}"/>')
            out.append(f'<text x="{left+bw+4:.1f}" y="{y+dy+bar_h-4}">{r[key]:.0f}</text>')
        out.append(f'<text x="{w-12}" y="{y+bar_h+4}" text-anchor="end" font-weight="bold">'
                   f'−{r["reduction"]:.0f}%</text>')
        y += 2 * bar_h + gap
    out.append(f'<text x="{left}" y="{h-12}" fill="#555">단위 mV. 가정 분포이며 실측값 아님.</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="파일 안 쓰고 표만 출력")
    ap.add_argument("--runs", type=int, default=300)
    args = ap.parse_args()

    rows = [summarize(sc, runs=args.runs) for sc in scenarios()]
    t = table(rows)
    print(t)
    if not args.print:
        (HERE / "results-table.md").write_text(t + "\n", encoding="utf-8")
        (HERE / "figure.svg").write_text(svg(rows), encoding="utf-8")
        print(f"\nwrote {HERE / 'results-table.md'}, {HERE / 'figure.svg'}")


if __name__ == "__main__":
    main()
