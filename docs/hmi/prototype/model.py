"""In-memory fixtures for the main operation screen."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


KST = timezone(timedelta(hours=9))


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


@dataclass(frozen=True)
class Snapshot:
    scenario: str
    quality: Quality
    run_id: str | None
    observed_at: datetime | None
    line_state: State | None
    stations: dict[str, State]
    counts: tuple[int, ...] | None
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
        return str(self.counts[index]) if self.quality is Quality.GOOD and self.counts is not None else "—"

    def control_enabled(self, action):
        # The prototype has no command transport regardless of its visual state.
        if action not in CONTROL_ACTIONS:
            raise ValueError(f"Unknown control action: {action}")
        return False


def sample(key, now=None):
    if key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {key}")
    now = now or datetime.now(KST)
    if key == "missing":
        return Snapshot(key, Quality.MISSING, None, None, None, {}, None)

    idle = dict.fromkeys(STATIONS, State.IDLE)
    if key == "idle":
        return Snapshot(key, Quality.GOOD, "QA-002", now, State.IDLE, idle,
                        (0, 0, 0, 0, 0), "인계 요청 없음")

    running = {**idle, "IN": State.BUSY, "VIS1": State.BUSY, "VIS2": State.BUSY,
               "T1": State.BUSY, "T3": State.BUSY, "T4": State.STARVED,
               "SORT": State.BUSY, "LA": State.BUSY, "LC": State.BLOCKED, "BOX": State.BUSY}
    if key in ("stale", "offline"):
        quality = Quality.STALE if key == "stale" else Quality.OFFLINE
        age = 12 if key == "stale" else 36
        return Snapshot(key, quality, "QA-001", now - timedelta(seconds=age), State.BUSY,
                        running, (24, 2, 1, 3, 0), "마지막 관측: Kit QA-A-003 수신 대기")
    if key == "fault":
        stations = dict.fromkeys(STATIONS, State.STOPPED)
        stations["T3"] = State.FAULT
        return Snapshot(key, Quality.GOOD, "QA-001", now, State.FAULT, stations,
                        (24, 2, 1, 3, 1), "인계 보류", "T3", "E-TEST · 계측 응답 없음")
    return Snapshot(key, Quality.GOOD, "QA-001", now, State.BUSY, running,
                    (24, 2, 1, 3, 0), "Kit QA-A-003 수신 대기")
