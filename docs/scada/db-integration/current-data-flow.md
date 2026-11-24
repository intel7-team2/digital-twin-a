# 현재 SQLite 이벤트와 Grafana 패널 분석

2026-11-23 기준. 라이브 화면은 [`cellect-scada-live.json`](../dashboards/cellect-scada-live.json), 이벤트 생성은 [`process.py`](../simulation/process.py), 집계와 이력 조회는 [`server.py`](../simulation/server.py)에 있다.

## 현재 이벤트 원장

시뮬레이터의 `.local/simulation.sqlite3`는 `events`를 추가 기록한다. 인덱스는 `(run_id, stamp, event_id)`, `(cell_id, event_id)`, `(kit_id, event_id)`다. 기본 2초 틱마다 새 Cell ID 하나와 앞선 셀의 단계 이벤트를 한 트랜잭션으로 저장한다. `PACKED` 4건과 `KIT_CREATED` 1건도 같은 커밋에 속한다. 재시작하면 새 `run_id`로 집계하고, 이전 실행의 셀과 Kit는 정확한 ID로 조회할 수 있다.

| SQLite 필드 | 타입 | 의미와 단위 |
| --- | --- | --- |
| `event_id` | `INTEGER PRIMARY KEY` | 로컬 증가 키. 동일 초 안에서 이벤트 순서를 정함 |
| `run_id` | `TEXT NOT NULL` | 시뮬레이션 실행 ID |
| `stamp` | `INTEGER NOT NULL` | 발생 시각. Unix UTC 초. 여러 이벤트가 같은 틱을 공유 |
| `kind` | `TEXT NOT NULL` | `ID_ASSIGNED`, `VISION`, `ELECTRICAL`, `SORTED`, `PACKED`, `KIT_CREATED` |
| `cell_id` | `TEXT` | 내부 셀 식별자. `KIT_CREATED`에서 비어 있음 |
| `result` | `TEXT` | `VISION`과 `ELECTRICAL`의 `PASS` 또는 `FAIL` |
| `ocv_v`, `ir_mohm` | `REAL` | `ELECTRICAL`에서 OCV는 V, IR은 mΩ. FAIL 검사도 측정값을 기록 |
| `group_code` | `TEXT` | 분류, 포장, Kit 이벤트의 전압·저항 유사 특성군 `A`, `B`, `C` |
| `kit_id`, `slot` | `TEXT`, `INTEGER` | 포장·Kit 완료를 묶는 ID. 슬롯 1–4는 `PACKED`에만 기록 |

이벤트 종류에 해당하지 않는 필드는 `NULL`이다. 외관 FAIL 뒤 전기검사, 전기검사 FAIL 뒤 분류 이벤트는 발생하지 않는다. 현재 원장에는 LOT, 레인, 검사 시도 ID, 재검, 기록 시각, 버퍼 보정 이벤트가 없다. 시뮬레이터는 한 틱에 전기검사 결과를 최대 1건 기록한다.

## 라이브 화면의 조회 경로

`3300`의 Grafana가 `cellect-scada-simulation` Graphite 데이터 소스를 통해 `127.0.0.1:8766/render`에 목표 메트릭과 `from`·`until`을 Unix 초로 전달한다. 어댑터는 현재 `run_id`를 선택한다. 범위 시작 전 이벤트로 누계·Buffer의 기초값을 계산하고, 범위 안의 커밋된 틱마다 `[값, Unix 초]`를 반환한다. 범위 안에 틱이 없으면 빈 시계열을 반환한다. 기본 조회는 최근 5분, 화면 시간대는 `Asia/Seoul`이다.

아래 메트릭은 모두 `cellect.sim.` 접두사를 사용한다. 공통 입력은 현재 실행 ID와 조회 구간이고, 시계열 출력의 시간 필드는 모의 어댑터에서 Unix 초, Grafana에서는 시간 필드다. 표의 갱신 주기는 현재 동작과 팀 DB 검증 시작값을 함께 표시한다. DB 값의 실제 갱신은 수집기 커밋에 따르며 Grafana 갱신과 별개다.

| ID·패널 | 현재 목표 메트릭과 계산 | 원본에 필요한 필드 | 값 타입·단위 | 화면 갱신 현재 / DB 파일럿 제안 |
| --- | --- | --- | --- | --- |
| 1 공정 누계 | `production.cells`, `vision.pass`, `vision.fail`, `electrical.pass`, `electrical.fail`, `kits.total`의 `lastNotNull` | `run_id`, `stamp`, `kind`, `result`, 셀·Kit 식별자 | 정수, 셀 / 완료 Kit | 5초 / 10초 |
| 2 생산량과 검사 분기 | 위 메트릭 중 `kits.total`을 제외한 5개 시계열. `ID_ASSIGNED`와 판정 이벤트별 누계 | `run_id`, `stamp`, `kind`, `cell_id`, `result` | 정수, 셀 | 5초 / 10초 |
| 3 특성군별 Buffer | `buffer.A`, `.B`, `.C`. 그룹별 `SORTED` 누계 − `PACKED` 누계 | `run_id`, `stamp`, `kind`, `cell_id`, `group_code` | 정수, 셀 | 5초 / 10초 |
| 4 OCV 검사값 | `electrical.ocv_v`. 검사 행 값, 검사 없는 틱은 `null` | `run_id`, `stamp`, `kind`, `cell_id`, `ocv_v` | 실수, V. 결측 허용 | 5초 / 10초 |
| 5 IR 검사값 | `electrical.ir_mohm`. 검사 행 값, 검사 없는 틱은 `null` | `run_id`, `stamp`, `kind`, `cell_id`, `ir_mohm` | 실수, mΩ. 결측 허용 | 5초 / 10초 |
| 6 완료 Kit | `kits.total`. `KIT_CREATED` 이벤트 누계 | `run_id`, `stamp`, `kind`, `kit_id` | 정수, 완료 Kit | 5초 / 10초 |

현재 누계는 이벤트 행을 센다. 모의 공정에서 ID 부여와 각 검사는 셀당 최대 1회다. 팀 DB에서는 중복 전달과 재검을 고려해 표준 조회의 셀 단위 최종 결과와 검사 시도 데이터를 구분한다. Buffer의 차감식도 분류와 포장만 존재하는 모의 공정에 해당한다.

**이력 조회**는 Grafana 패널 밖의 `/trace`와 `/api/history`에서 이뤄진다. 정확한 ID로 조회하면 전체 이력을 이벤트 ID 순으로 반환한다. 기본 화면은 현 실행의 최근 이벤트 40건이다. OCV·IR 화면의 링크는 Grafana가 전달한 Unix 밀리초를 초로 환산해 현재 실행의 해당 검사 이벤트에서 Cell ID를 찾는다. 팀 DB에서는 병렬 검사 때문에 같은 시각의 결과가 여럿일 수 있다. [조회 명세](read-interface.md)는 `inspection_id`를 경유하도록 제안한다.

## 기존 고정 화면

[`cellect-scada-demo.json`](../dashboards/cellect-scada-demo.json)은 패널 JSON에 포함된 TestData `CSV Content`를 읽는다. 자동 갱신은 꺼져 있고 선택 시간은 수치에 영향을 주지 않는다.

| ID·패널 | 현재 출력 필드·타입·단위 |
| --- | --- |
| 1 공정 요약 | ID 부여, 외관 PASS, 전기검사 PASS, 그룹 분류는 정수(셀). 완료 Kit는 정수(Kit) |
| 2 특성군별 분류 및 포장 | 특성군은 문자열. 분류·포장·포장 대기는 정수(셀) |
| 3 완료 Kit | Kit ID, 특성군, 상태는 문자열. 셀 수는 정수, OCV·IR 편차는 실수(V, mΩ) |
| 4 셀별 추적 | Cell ID, LOT, 외관·최종 전기검사 결과, 검사 위치, 특성군, Kit ID, 상태는 문자열. 최종 시도·슬롯은 정수, OCV·IR은 실수(V, mΩ). 미검사·미포장 필드는 빈 값 |
