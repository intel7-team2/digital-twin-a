# SCADA 조회 요청 회신 (DB 담당, 11/23)

기준: battery-db `9604290` (`schema/01_tables.sql`, `02_views.sql`, `04_roles.sql`), PostgreSQL 16.15.
지금 DB에는 스키마와 기준 데이터(스테이션 23개, 판정 기준 1세트)만 있다. 셀 데이터는 수집기가 붙은 뒤 쌓인다.

> **11/23 추가 (battery-db `9c0c146`)**
> - **API:** DB 계정 대신 API 키로 조회할 수 있다. 키는 본인이 `ssh tunnel@<서버 IP> new`로 받고 (GitHub 키 등록된 팀원), 문서는 `https://<API 도메인>/docs` (주소는 따로 전달). 엔드포인트와 추적 방식은 battery-db [`api/README.md`](https://github.com/intel7-team2/battery-db/blob/main/api/README.md).
> - **Grafana:** 지금처럼 SQL 직결, 계정 `grafana` (조회만, 쿼리 10초 제한, 연결 5개). 아래 표의 접속 정보 그대로.
> - **화면 개발용 가짜 데이터:** `sim_run.run_id = 4` (`purpose = 'fake'`, 셀 100개, 45분 운전). 재검, LOT 보류, 2A-T2 NG 편향, 2A-T3 검사 시간 편향, 설비 고장·막힘, 알람이 들어 있다. 실제 데이터가 들어오면 `fake_cleanup.sql`로 지우므로 쿼리는 `purpose <> 'fake'` 또는 run 선택 변수로 거를 것.

## 1. 먼저 받을 자료

| 항목 | 제공 데이터 또는 규칙 | 담당 | 미정 사항 |
|---|---|---|---|
| 조회 대상 | 뷰 9개: `v_cell_electrical_latest`, `v_box_spread`, `v_set_spread_compare`, `v_run_yield`, `v_tester_stats`, `v_equipment_time`, `v_lot_status`, `v_pack_trace`, `v_alarm_open`. 원본 테이블 21개 전부 SELECT 가능 (필드는 `01_tables.sql` 주석 참고). 정의 버전은 battery-db 커밋 해시로 맞춘다 | DB | SCADA 화면별로 더 필요한 뷰가 있으면 요청 |
| 읽기 전용 역할 | `reader`: public 스키마 전체 SELECT만, INSERT/UPDATE 없음 (확인함) | DB | 새 뷰를 만들면 `04_roles.sql`을 다시 실행해야 권한이 붙음 |
| 접속 정보 | DB `battery`, 포트 5432는 VM 안에서만 열림. 접속은 SSH 터널만: 터널을 연 PC에서 `localhost:5433`. 서버 주소는 저장소에 적지 않고 따로 전달 | DB | Grafana를 어디서 돌릴지 (개인 PC + 터널 / VM 안) |
| 네트워크·TLS | 인터넷에 DB 포트를 열지 않음. 암호화는 SSH 터널이 담당 (서버 ssl=on이지만 터널 안이라 필요 없음). 인증은 scram-sha-256 | DB | — |
| 계정 발급·비밀 전달 | SSH: GitHub `01xooyeon` 키를 `tunnel` 계정에 등록함 (DB 포트 포워딩만 가능, 쉘 없음). 터널: `ssh -N -L 5433:localhost:5432 tunnel@<서버 IP>`. DB: Grafana는 `grafana` 계정 (조회만, 쿼리 10초 제한, 연결 5개), 사람이 볼 때는 `reader`. 서버 주소·비밀번호는 관리자가 채팅·저장소가 아닌 별도 경로로 전달 | DB | — |
| 키·유일 범위 | `sim_run.run_id` 전역 유일 (시험 1회). `line` = '2A'/'PACK'/'2B'. `lot.lot_code` 전역 유일. `cell.plc_no`(PLC 투입 번호)는 **run 안에서만** 유일 → 키는 `(run_id, plc_no)`. `cell.cell_id` 전역 유일, 형식 `R<run 4자리>-<plc 6자리>`. 검사 ID = `cell_inspection.id` 전역 유일. 박스 ID = `cell_box.box_id` 전역 유일 | DB | 실물 셀·박스 ID 형식은 팩 팀과 확정 전 |
| 조인 규칙 | 셀→LOT `cell.lot_code`, 셀→박스 `cell.box_id`(+`box_slot` 1~4), 검사→셀 `cell_inspection.cell_id`, 검사→기준 `criteria_set_id`, 모두→스테이션 `station_code`, 모두→시험 `run_id`. 박스→팩 `pack_slot.source_box_id`, 셀→팩 `pack_slot.cell_id` | DB | — |
| 시각 | 모두 `timestamptz`, 서버 시간대 UTC로 저장 → Grafana에서 Asia/Seoul로 표시. `occurred_at`/`measured_at` = 현장(PLC 이벤트) 시각, `received_at` = DB 기록 시각. 검사 시간 = `measured_at - started_at` | DB | 현장 시각을 PLC가 줄지, 브리지 수신 시각으로 찍을지 (PLC 담당과) |
| 정렬 키 | 검사: `(measured_at, id)`. 이벤트: `(occurred_at, event_id)`. 같은 시각 병렬 결과(검사기 4레인)도 `id`로 구분됨 | DB | — |
| 외관 판정 | `cell_inspection.kind='appearance'`, `result_code` 0 = G(PASS), 9 = NG(FAIL), 5 = 미판독. NG면 `reason_code`에 결함 코드 | DB | 외관 결함 코드표 (비전 담당) |
| 전압 판정 | `kind='electrical'`, `result_code` 1 A, 2 B, 3 C (= PASS), 5 대기, 9 NG (= FAIL). `reason_code` 0 없음, 1 OCV 미달, 2 OCV 초과, 3 내부저항 초과, 4 QR 미판독, 5 측정 실패, 6 LOT 보류 (interface.md D2303) | DB | — |
| 미계측 | 내부저항을 못 재면 `ir_mohm` = null, `read_status` 0 정상 / 1 QR 미판독 / 2 측정 실패 | DB | — |
| 단위 | `ocv_mv`, `v1_mv`, `v2_mv` = mV 정수 → V는 `/1000.0`. `i1_ma`, `i2_ma` = mA. `ir_mohm` = mΩ 정수 (변환 없음) | DB | — |
| 시도·최종 | 검사 1회 = 1행. `attempt` 1 = 1차, 2 = 재검. 최종 = 가장 큰 attempt (`v_cell_electrical_latest`) | DB | 재검 허용 횟수 (기준 1회, `criteria_set.retest_limit`) |
| A/B/C 레인 | 등급 = `cell.grade`, 레인 스테이션 `2A-LA/LB/LC`. 박스 적재는 `cell.box_id` 채워질 때 | DB + PLC | 레인 투입 "확인 이벤트"를 PLC가 따로 줄지 (아래 2번) |
| 검증 샘플 | battery-db `schema/test/smoke.sql`: 가상 셀 24개, 끝에 ROLLBACK이라 DB에 안 남음. 기대 누계: 투입 24, 외관 NG 1, 재검 2, 재검 합격 1, 제거 2, 검사기 레인 4개 | DB | 남아 있는 샘플 run이 필요하면 `purpose='test'`로 VM에 넣을 수 있음 |
| 갱신 주기·지연 | 한국→서버 왕복 약 43 ms, 조회 부하는 문제 없음. 실제 신선도는 수집기 쓰기 주기에 달림 | DB + 수집기 | 수집기 쓰기 주기 |
| 샘플 운전 시각 | `sim_run.started_at`/`ended_at`로 조회 | — | 첫 실제 운전 일정 |

## 2. 같이 정할 사항

| 항목 | 제공 데이터 또는 규칙 | 담당 | 미정 사항 |
|---|---|---|---|
| 1. 재검과 최종 수율 | 재검 대기 = `cell.status='retest'` (1차 NG, 재검 전). 최종 FAIL = `status='rejected'`. 최종 결정 시각·검사 ID = `v_cell_electrical_latest`의 `measured_at` + 원본 `cell_inspection.id`. 수율은 `v_run_yield` (1차 합격, 재검, 재검 합격, 제거) | DB | `v_cell_electrical_latest`에 `id` 컬럼 추가 (SCADA가 쓰면 바로 추가) |
| 2. Buffer 기준값 | DB는 이벤트만 저장. 레인별 현재 개수 스냅샷은 DB에 없음 → 실시간 개수는 브리지 라이브 값, 누계·이력은 DB 이벤트로 | DB + PLC | 레인 출입 이벤트 정의, 폐기·이동·재작업 시 감소 규칙, 통신 단절 표시 (`alarm` COMM_LOST) |
| 3. Kit 완료와 취소 | Kit = `cell_box` (4셀)로 보면 Kit ID = `box_id`. 슬롯 유일 `(box_id, box_slot)`, 한 셀은 한 팩에만 (`pack_slot.cell_id` UNIQUE). 상태: `filling` → `full`(완료, `packed_at`) → `handed_over`(인계, `supply_handoff.confirmed_at`) → `consumed` | DB + 팩 | Kit ID를 box_id로 쓸지. 취소·재작업 시 박스 상태 값 추가 여부 |
| 4. 수집기 쓰기 | 쓰기 계정 `writer_2a`는 Grafana `reader`와 분리됨. 메일박스 제안 D2700~D2799 (헤더 4워드 + 12워드×8건). 중복 방지: `event_id` = uuid v5(`run:<run_id>/seq:<순번>`), 같은 이벤트 재전송은 무시. run이 바뀌면 순번 초기화해도 키가 겹치지 않음. 커밋 후 ACK | DB + PLC | 메일박스 범위, 순번 폭, ACK 방식, 정정 이벤트 형식 (PLC 담당과). 완료 Kit 가시성 = 트랜잭션 커밋 시점 |
| 5. DB 파일럿 | 조회 단위 `run_id` + 시간 범위, 계정 `grafana`, 10초 갱신 시작값 OK | DB + SCADA | 첫 운전 데이터가 생긴 뒤 지연·부하 측정 |

## 담당 회신 순서

1. 지금 가능: 조회 정의(위 뷰), 키·시간·단위 규칙, smoke 샘플.
2. 계정: SSH 등록 + `reader` 비밀번호 전달.
3. PLC 담당과 합의 후: 메일박스·레인 이벤트·ACK.
