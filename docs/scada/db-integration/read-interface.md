# 팀 공용 DB 조회 인터페이스와 데이터 소스 전환안

2026-11-23 협의 초안. 아래 이름과 타입은 SCADA가 소비하는 논리 계약이다. 팀 공용 DB의 실제 관계와 컬럼은 담당자가 제공하는 정의에 매핑한다. [공정 v2 문서](../../2a-data-design.md#4-db-스키마--battery-db)는 `battery-db`와 PostgreSQL 16을 기록한다. 담당자 회신을 반영한 초기 연결과 실제 매핑은 [별도 PostgreSQL 파일럿](../postgres-pilot/README.md)에 정리했다.

## 조회 계약

요청 기준은 단일 `run_id`와 조회 범위 `[from, to)`다. 시각은 PostgreSQL `timestamptz`로 반환해 발생 시각 기준으로 필터링하고, Grafana가 한국 시각으로 표시한다. `recorded_at`을 별도로 제공하면 수집 지연과 정정을 추적할 수 있다. 식별자와 코드의 조회 표현은 문자열, 셀·Kit 및 시도 수는 부호 있는 정수, V/mΩ 값은 숫자다. 원본 스케일과 유효 자릿수는 제공자와 합의한다. 타임라인은 발생 시각과 안정적인 순서 키로 정렬한다.

| 논리 조회 | 행 기준과 필수 출력 | 사용하는 화면 |
| --- | --- | --- |
| 실행 목록 | 실행당 1행. `run_id`, `started_at`, `ended_at`(진행 중이면 `NULL`), `line_code`, `data_origin`(시뮬레이션·실장비 등 합의된 출처) | 실행 선택, 출처 표시 |
| 생산·검사 누계 | 실행·표시 시각당 1행. `time`, `run_id`, `identified_cells`, `vision_pass_cells`, `vision_fail_cells`, `electrical_final_pass_cells`, `electrical_final_fail_cells`(모두 정수, 셀) | 1, 2 |
| 특성군 Buffer | 실행·시각·특성군당 1행. `time`, `run_id`, `group_code`, `buffer_cells`(정수, 셀), `observed_at` | 3 |
| 검사 관측 | 검사 완료 시도당 1행. `run_id`, `inspection_id`, `cell_id`, `attempt`(정수), `station_code`, `started_at`, `tested_at`, `ocv_v`(V), `ir_mohm`(mΩ), `result`, `reason_code`, `criteria_version`. 측정 불가 필드는 `NULL`. | 4, 5와 검사 상세 |
| Kit 완료 누계 | 실행·표시 시각당 1행. `time`, `run_id`, `completed_kits`(정수, Kit) | 1, 6 |
| 셀·Kit 이력 | 셀 이벤트당 1행. `event_key`, `run_id`, `occurred_at`, `source_sequence` 또는 안정 순서 키, `stage`, `cell_id`, `station_code`, 결과 및 관련 `inspection_id`, `kit_id`, `group_code`, `slot`(1–4). Kit 상세에는 완료 상태·시각과 슬롯별 셀을 함께 조회한다. | 셀·Kit 상세 |
| 데이터 신선도 | 실행·데이터 출처당 최신 상태. `last_received_at` 또는 전달 워터마크, `last_heartbeat_at`, `source_status`. 늦게 도착한 이벤트를 구분하려면 `recorded_at`을 함께 제공한다. | 갱신 상태, 결측 해석 |

검사 시도 행 외에 셀별 **최종 결정에 대한 이력**이 필요하다. 필수 값은 `run_id`, `cell_id`, `decided_at`, `final_result`, 결정 근거가 된 `inspection_id` 또는 판정 근거 코드다. 팀 DB가 최종 결정을 직접 제공하거나, 시도·재검 이력에서 결정 시각을 재구성하는 담당자 승인 규칙을 제공한다. `LOT`, 미판독 건의 임시 투입 키, Kit 인계·편차 등 상세 화면 항목은 [기존 데이터 요청 목록](../db-data-requirements.md)에 있다.

## 패널별 판정과 시각 규칙

- **공정 누계·생산량.** ID 부여 완료 고유 셀을 센다. 외관은 유효한 셀별 판정 기준으로 세고, 미판독·미판정은 별도 상태다. 전기검사 누계는 셀별 최종 PASS/FAIL만 센다. 재검 대기 중인 셀은 최종 FAIL에 아직 포함하지 않는다. 최종 결정의 변경·취소를 어떻게 반영할지는 담당자와 합의한다.
- **기간과 누계.** 기간은 그릴 행을 제한하며, 누계와 현재 Buffer는 실행 시작부터 해당 시각까지의 상태를 사용한다. 기간 시작 전 상태를 기초값으로 포함한다. 선택 종료 시각 직전 상태로 Stat을 계산한다. 직전 구간에 이벤트가 없어도 실행과 상태가 검증되면 마지막 상태를 표시할 수 있다. 미수집·단절·실행 없음은 결측 또는 지연 상태로 표시하고, 관측된 0과 구분한다.
- **Buffer.** 이벤트 방식은 실제 확인된 레인 진입과 포장·폐기·이동·취소 등 출입을 반영한다. 스냅샷 방식은 그룹별 기준 시점과 마지막 유효 측정 시각을 제공한다. 어느 쪽을 기준값으로 삼을지 합의해 같은 출입을 이중 반영하지 않는다. 손실이나 음수 수량은 정합성 상태로 노출한다.
- **OCV·IR.** 1차·재검·FAIL을 포함한 관측 원본을 검사 ID별로 유지한다. 동일 초·밀리초의 병렬 결과를 한 건으로 덮어쓰지 않는다. 점에서 검사 ID를 유지할 수 있으면 상세로 직접 이동한다. 시계열 형식에서 ID가 사라지면 시간 구간과 레인으로 검사 상세 테이블을 열고, 각 행에서 정확한 `inspection_id`로 셀 이력을 연다. 검사 없는 시각과 미계측 필드는 결측이다.
- **완료 Kit.** 완료로 확정된 고유 Kit만 집계한다. 완료 시점의 슬롯 1–4에 서로 다른 셀 4개가 있고 모두 같은 A/B/C 특성군이어야 한다. Kit와 팀 DB의 박스 식별자 대응, 취소·재작업이 누계에 미치는 효과는 협의한다. A/B/C는 전압·저항 유사 특성군이다.

PostgreSQL Grafana 시계열 쿼리는 `time`과 숫자 열을 반환하고 `time` 오름차순으로 정렬한다. 범위를 반개구간으로 유지하려면 `$__timeFrom()` 이상, `$__timeTo()` 미만으로 명시한다. 이력은 Table 형식으로 조회해 키를 열로 보존한다. 초기 파일럿의 화면 갱신은 10초로 시작하고 적재 지연과 쿼리 시간을 계측해 조정한다. [Grafana PostgreSQL 쿼리 편집기](https://grafana.com/docs/grafana/latest/datasources/postgres/query-editor/)

## 설정으로 전환하는 구조 제안

**같은 화면 정의에 데이터 소스별 쿼리 프로필을 적용**한다. 현재 `3300`에는 고정·라이브 모의 대시보드가 계속 제공된다. 후속 구현은 다른 포트와 별도 Grafana 데이터·프로비저닝 경로를 가진 검증 인스턴스에 둔다. 기존 실행 스크립트에서 `-Port`만 바꾸면 로컬 SQLite와 프로비저닝 경로를 공유하므로 검증 환경 격리에는 별도 경로 지정이 필요하다.

| 프로필 설정값 예시 | 데이터 소스 | 쿼리와 이력 링크 |
| --- | --- | --- |
| `SCADA_DASHBOARD_PROFILE=sqlite` | 기존 UID `cellect-scada-simulation`, Graphite → 로컬 SQLite | `cellect.sim.*` 메트릭 경로와 모의 이력 URL. 현재 실행만 노출하는 제약을 표시 |
| `SCADA_DASHBOARD_PROFILE=postgres` | 검증용 별도 UID 예시 `cellect-scada-postgres`, Grafana PostgreSQL 읽기 전용 데이터 소스 | 승인된 읽기 관계를 논리 필드로 변환하는 SQL targets와 검사·셀·Kit 상세 링크 |

프로필 적용기는 공통 패널 정의에 `datasource` 타입·UID, `targets`, 실행·필터 변수, 상세 링크를 함께 넣고 격리된 디렉터리에 Grafana JSON을 생성한다. 같은 화면 정의를 두고 설정값으로 프로필을 고른 뒤 파일을 다시 생성·프로비저닝한다. 패널에 있는 Graphite 목표 경로와 PostgreSQL SQL은 쿼리 모델이 다르므로 데이터 소스 UID만 변경해서는 전환할 수 없다. 접속 설정은 데이터 소스 프로비저닝이나 Grafana 보안 설정에 따로 둔다. 환경변수 치환을 대시보드 JSON 자체에 의존하지 않는다. [Grafana 프로비저닝](https://grafana.com/docs/grafana/latest/administration/provisioning/)

팀 DB 파일럿에서는 승인된 뷰 또는 관계에 한해 조회 권한을 받은 전용 계정을 사용한다. 주소·DB명·TLS 조건과 비밀 주입 경로를 승인된 환경에서 설정한다. 시간 경계, 동시 검사, 재검, 중복, Buffer 반출 및 Kit 재작업 샘플로 [인수 기준](db-handoff.md)을 충족한 뒤 적용한다. 위 프로필 적용기는 설계 단계다. 현재 전환은 `3300`의 SQLite 모의 화면과 `3301`의 PostgreSQL 파일럿을 각각 여는 방식이다.
