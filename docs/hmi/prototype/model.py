"""Projection from offline bridge fixtures and an isolated operator practice model."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


KST = timezone(timedelta(hours=9))
SAMPLE_MAX_AGE = timedelta(seconds=10)


class Quality(Enum):
    GOOD = "정상 관측"
    MISSING = "미수집"
    STALE = "관측 지연"
    OFFLINE = "통신 단절"


class State(Enum):
    IDLE = "정상 대기"
    BUSY = "운전 중"
    BLOCKED = "후단 대기"
    STARVED = "공급 대기"
    STOPPED = "정지"
    FAULT = "설비 이상"


STATIONS = {
    "IN": "셀 투입", "VIS1": "ID 부여", "VIS2": "외관 검사", "RJ1": "외관 배출",
    "T1": "검사 레인 1", "T2": "검사 레인 2", "T3": "검사 레인 3", "T4": "검사 레인 4",
    "IDC": "ID 재확인", "RT": "재검", "RJ2": "최종 배출", "SORT": "특성군 분류",
    "LA": "특성군 A", "LB": "특성군 B", "LC": "특성군 C", "BOX": "동일군 4셀", "OUT": "Kit 인계",
}
METRICS = (("총 투입", "셀"), ("외관 NG", "셀"), ("재검 대기", "셀"), ("완료 Kit", "개"), ("열린 알람", "건"))
SCENARIOS = {
    "missing": "미수집", "idle": "정상 대기 · 새 회차", "running": "운전 중",
    "stale": "관측 지연", "offline": "PLC 통신 단절", "fault": "설비 이상 · T3",
}
CONTROL_ACTIONS = ("START", "STOP", "RESET")
CONTROL_REASON = "브리지 명령 미연동 · 테스트 입력 전용"
PRACTICE_SCENARIOS = {
    "practice": "조작 연습 · 정상 대기",
    "practice_hold": "조작 연습 · LOT 보류 및 T3 이상",
}


@dataclass(frozen=True)
class Snapshot:
    scenario: str
    quality: Quality
    run_id: str | None
    observed_at: datetime | None
    line_state: State | None
    stations: dict[str, State]
    counts: tuple[int | None, ...] | None
    handoff: str | None = None
    fault_station: str | None = None
    fault_detail: str | None = None

    def state_at(self, station=None):
        return self.line_state if station is None else self.stations.get(station)

    def display_state(self, station=None):
        state = self.state_at(station)
        if self.quality is not Quality.GOOD:
            return "확인 불가" if state else "미수집"
        return state.value if state else "미수집"

    def last_state(self, station=None):
        state = self.state_at(station)
        return state.value if self.quality is not Quality.GOOD and state else None

    def display_count(self, index):
        if self.quality is Quality.GOOD and self.counts is not None and self.counts[index] is not None:
            return str(self.counts[index])
        return "—"

    def control_enabled(self, action):
        # The prototype has no command transport regardless of its visual state.
        if action not in CONTROL_ACTIONS:
            raise ValueError(f"Unknown control action: {action}")
        return False


@dataclass(frozen=True)
class BridgeObservation:
    """Logical sample input for local testing. The live bridge format is pending."""

    plc_connected: bool | None = None
    observed_at: datetime | None = None
    run_id: str | None = None
    line_state: State | None = None
    stations: dict[str, State] | None = None
    counts: tuple[int | None, ...] | None = None
    handoff: str | None = None
    fault_station: str | None = None
    fault_detail: str | None = None


def project_observation(key, observation, now):
    if observation.plc_connected is False:
        quality = Quality.OFFLINE
    elif observation.plc_connected is None or observation.observed_at is None:
        quality = Quality.MISSING
    elif now - observation.observed_at > SAMPLE_MAX_AGE:
        quality = Quality.STALE
    else:
        quality = Quality.GOOD

    current = quality is Quality.GOOD
    run_id = observation.run_id
    return Snapshot(
        key, quality, run_id, observation.observed_at, observation.line_state,
        dict(observation.stations or {}), observation.counts if run_id else None,
        observation.handoff if current and run_id else None,
        observation.fault_station if current else None,
        observation.fault_detail if current else None,
    )


def sample_observation(key, now):
    if key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {key}")
    if key == "missing":
        return BridgeObservation()

    idle = dict.fromkeys(STATIONS, State.IDLE)
    if key == "idle":
        return BridgeObservation(True, now, "QA-002", State.IDLE, idle, (0, 0, 0, 0, 0), "인계 요청 없음")

    running = {**idle, "IN": State.BUSY, "VIS1": State.BUSY, "VIS2": State.BUSY,
               "T1": State.BUSY, "T3": State.BUSY, "T4": State.STARVED,
               "SORT": State.BUSY, "LA": State.BUSY, "LC": State.BLOCKED, "BOX": State.BUSY}
    if key == "fault":
        stations = dict.fromkeys(STATIONS, State.STOPPED)
        stations["T3"] = State.FAULT
        return BridgeObservation(True, now, "QA-001", State.FAULT, stations, (24, 2, 1, 3, 1),
                                 "인계 보류", "T3", "E-TEST · 계측 응답 없음")
    age = {"stale": 12, "offline": 36}.get(key, 0)
    return BridgeObservation(key != "offline", now - timedelta(seconds=age), "QA-001", State.BUSY,
                             running, (24, 2, 1, 3, 0), "Kit QA-A-003 수신 대기")


def sample(key, now=None):
    now = now or datetime.now(KST)
    return project_observation(key, sample_observation(key, now), now)


@dataclass(frozen=True)
class PracticeResult:
    action: str
    applied: bool
    reason: str


class OperationPractice:
    """In-memory command loop for touch practice. No transport or live addresses."""

    def __init__(self, scenario):
        if scenario not in PRACTICE_SCENARIOS:
            raise ValueError(f"Unknown practice scenario: {scenario}")
        self.scenario = scenario
        self.lot_hold = scenario == "practice_hold"
        self.fault = self.lot_hold
        self.running = False
        self.engaged = False
        self.result = None

    def command(self, action):
        if action not in CONTROL_ACTIONS:
            raise ValueError(f"Unknown control action: {action}")
        if action == "START" and (self.lot_hold or self.fault):
            result = PracticeResult(action, False, "LOT 보류" if self.lot_hold else "T3 설비 이상")
        elif action == "START":
            result = PracticeResult(action, True, "이미 운전 중" if self.running else "운전 시작 확인")
            self.running = self.engaged = True
        elif action == "STOP":
            result = PracticeResult(action, True, "정지 확인")
            self.running = False
            self.engaged = True
        elif self.running:
            result = PracticeResult(action, False, "운전 중 · 먼저 정지하세요")
        else:
            self.fault = False
            self.engaged = True
            result = PracticeResult(action, True, "설비 이상 리셋 · LOT 보류 유지" if self.lot_hold else "리셋 확인")
        self.result = result
        return result

    def snapshot(self, now=None):
        now = now or datetime.now(KST)
        if self.running:
            state = State.BUSY
            stations = sample_observation("running", now).stations
        else:
            station_state = State.STOPPED if self.engaged or self.fault else State.IDLE
            stations = dict.fromkeys(STATIONS, station_state)
            state = State.FAULT if self.fault else station_state
            if self.fault:
                stations["T3"] = State.FAULT
        # Practice changes operation state only. No cells or kits are generated.
        observation = BridgeObservation(
            True, now, "TRAINING-2A", state, stations, (0, 0, 0, 0, int(self.fault)), "인계 요청 없음",
            "T3" if self.fault else None, "연습용 계측 이상" if self.fault else None,
        )
        return project_observation(self.scenario, observation, now)
