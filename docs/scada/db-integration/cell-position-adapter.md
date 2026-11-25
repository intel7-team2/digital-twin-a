# 02 공정 관제 셀 위치 연동 준비

## 현재 연결점

기존 브리지가 확인한 이동 이벤트를 [수집 이벤트 봉투](collector-interface.md#논리-이벤트-봉투)로 변환한다. 기존 SQLite 대기열에 저장한 이벤트는 [위치 계산기](../collector/cell_positions.py)가 읽어, 선택 회차·출처·세션의 Cell ID별 마지막 확인 위치를 JSON으로 반환한다. 명령과 표시 경로는 기존 PLC 단일 쓰기 담당 규칙을 따른다.

```text
담당 조 이벤트 → 입력 매핑 → SQLite 대기열 → 셀 위치 스냅샷 → 02 공정 관제
```

입력 매핑과 Grafana 전송 경로는 연동 시 적용한다. 현재 JSON 출력은 독립 로컬 검증용이며 기존 02 화면은 PostgreSQL 이력 조회를 계속 사용한다.

## 로컬 초안의 이동 신호

| 종류 | 필요한 데이터 | 화면에 전달할 상태 |
| --- | --- | --- |
| `ID_READ` | `2A-VIS1`, `cell_id`, 성공을 뜻하는 `payload.result="PASS"` | 처음 식별된 셀을 VIS1에 표시 |
| `CELL_ENTERED` | 센서로 확인된 `station_code`, 확인된 `cell_id` | 해당 스테이션으로 이동 |
| `CELL_EXITED` | 이탈 확인 스테이션과 Cell ID | 마지막 위치에 이동 중·도착 미확인 표시 |
| `HEARTBEAT` | 동일한 출처·세션의 주기 신호와 실제 수신 시각 | 최근 신호 수신, 신호 지연 또는 미수집 구분 |

종류와 값은 로컬 매핑의 초안이다. 실제 장비 코드와 주소는 담당 조와 합의한 뒤 입력 매핑에 적용한다. Cell ID가 확인되지 않은 위치 이벤트와 상충하는 이탈 이벤트는 거부 건수에 기록한다. 검사 완료·특성군 판정만으로 다음 위치를 추정하지 않는다.

스냅샷의 `cells[]`는 `cell_id`, `last_station_code`, `movement`, `observed_at`, `received_at`, 최신 `event_key`와 순번을 제공한다. `source_status`가 `heartbeat_late` 또는 `unobserved`이면 관측된 셀에 마지막 확인 위치임을 표시한다. 최근 하트비트 수신은 셀별 위치 재관측과 별개다. 새 세션에는 이전 세션 위치를 복사하지 않는다.

생산자 한 곳의 회차·세션별 순번을 기준으로 읽는다. 순번 누락을 해석하려면 해당 스트림의 모든 이벤트를 받는다는 보장이 필요하다. 세션을 자동 선택하거나 재시작 뒤 기존 재공품을 대사하는 규칙은 담당 조와 정한다.

## 재현

저장소 루트 PowerShell에서 실행한다. 다음 명령의 시간과 하트비트 10초는 테스트 입력에만 적용한다.

```powershell
$positionDb = '.\docs\scada\.local\cell-position-qa.sqlite3'
python -X utf8 -B .\docs\scada\collector\spool.py --db $positionDb enqueue .\docs\scada\collector\fixtures\cell_positions.jsonl
python -X utf8 -B .\docs\scada\collector\cell_positions.py --db $positionDb --run-id QA-POSITION --source-id qa-bridge --session-id boot-1 --as-of 2026-11-25T09:00:06+09:00 --heartbeat-timeout 10
```

`09:00:03`에는 QA-001이 VIS1에서 이탈했고 QA-002는 VIS1에 있다. `09:00:06`에는 QA-001이 T2, QA-002가 T4에 있다. `09:00:11`에는 하트비트 지연으로 표시하고 각 셀의 마지막 위치를 유지한다. 이탈 이후 다음 진입을 기록하기 전까지 도착 설비는 확인되지 않은 상태다.

## 담당 조가 데이터를 제공하면

1. 두 레인의 이벤트 샘플을 받아 VIS1 발급 키가 진입·이탈까지 동일한지 확인한다. PLC 투입 번호만 제공하면 승인된 회차·번호 매핑을 사용해서야 `cell_id`를 채울 수 있다.
2. 회차·생산자·세션·순번, 현장 시각과 수신 시각, 하트비트 주기 및 새 세션의 재공품 확인 방법을 확정한다. 실제 포장·배출에서 화면의 셀 표시를 제거할 완료 이벤트도 이때 합의한다.
3. 확인된 입력을 위치 계산기에 연결하고, 읽기 전용 전송 방식과 02 화면 갱신 주기를 정한다. 먼저 VIS1→T2 단일 셀과 T2/T4 병렬 두 셀을 검증한 뒤 RT와 Kit로 확장한다.
