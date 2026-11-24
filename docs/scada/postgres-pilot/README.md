# 팀 PostgreSQL 읽기 전용 파일럿

팀 DB 담당자의 회신과 `battery-db` 커밋 `b728829`를 기준으로 구성했다. [파일럿 대시보드](http://127.0.0.1:3301/d/cellect-scada-postgres)는 Windows Grafana OSS 13.3.1에서 실행한다. [3300 라이브 모의 대시보드](http://127.0.0.1:3300/d/cellect-scada-live)는 기존 Graphite/SQLite 경로를 사용한다.

## 실행

1. PowerShell에서 팀원이 전달한 SSH 호스트를 입력하고 터널을 실행한다. SSH 개인 키를 별도로 지정해야 하면 대상 인수 앞에 `-i <키 파일 경로>`를 추가한다. 터널 콘솔은 켜 둔다.

   ```powershell
   $dbSshHost = Read-Host 'Team DB SSH host'
   ssh -N -L 127.0.0.1:5433:localhost:5432 -o ExitOnForwardFailure=yes ("tunnel@" + $dbSshHost)
   ```

2. 다른 PowerShell에서 저장소 루트를 열고 아래 명령을 실행한다. 숨김 입력창에는 팀원이 전달한 **DB `grafana` 계정**의 비밀번호를 넣는다. Grafana 웹 로그인은 파일럿 인스턴스의 별도 계정이다. 처음 실행하면 Grafana 기본 관리자 계정으로 로그인해 비밀번호를 변경한다.

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\docs\scada\postgres-pilot\Start-PostgresPilot.ps1
   ```

3. 파일럿에서 **팀 DB 스테이션**이 23행인지 확인한다. 수집기 실행 전에는 최근 실행·검사·Kit이 비어 있을 수 있다. 검사와 Kit는 시간 선택기의 범위를 적용하고, 최근 실행 수율은 해당 실행 전체를 조회한다. 두 콘솔은 각각 `Ctrl+C`로 종료한다.

데이터 소스는 루프백 `127.0.0.1:5433`, DB `battery`, 읽기 전용 사용자 `grafana`, PostgreSQL 16을 사용한다. DB TLS는 SSH 터널 내부에서 `disable`이다. Grafana 풀은 최대 3연결이며 서버 측 역할 설정은 최대 5연결과 쿼리 10초 제한이다. 파일럿 SQLite와 Grafana 보안 설정은 저장소 밖 시스템 임시 폴더의 `Cellect-2A-Grafana-Postgres`에 저장한다. 파일럿은 별도 로그인 쿠키를 쓴다. SSH 호스트와 데이터베이스 비밀번호는 실행 시에만 입력한다. [Grafana PostgreSQL 설정](https://grafana.com/docs/grafana/latest/datasources/postgres/configure/)

## 확정 매핑과 파일럿 범위

| 대상 | 조회 기준 |
| --- | --- |
| 연결 확인 | `station.station_code`, `station.name`, `station.sort_order` |
| 2A 실행·수율 | `sim_run.line = '2A'`의 최신 실행과 `v_run_yield`. `cells_in`, `appearance_ng`, `first_pass_ok`, `retested`, `retest_recovered`, `removed`, `boxed` 사용 |
| 이벤트·검사 키 | `run_id`는 전역 식별자, `plc_no`는 실행 안에서 유일, `cell_id`·`cell_inspection.id`·`cell_box.box_id`는 전역 식별자. 파일럿의 실행별 조회에는 `cell.run_id`가 필요하므로 실물 셀의 실행 연결 방법은 수집기 담당자와 확인 |
| 전기검사 | `cell_inspection.kind = 'electrical'`. `measured_at`과 `id`로 정렬하고 검사 ID는 텍스트로 표시. OCV는 `ocv_mv / 1000.0`으로 V 변환, IR은 `ir_mohm` 그대로 mΩ. 미계측은 `NULL` 유지 |
| 판정 | 외관 코드는 0=G, 5=미판독, 9=NG. 전기검사는 1/2/3=PASS(A/B/C 특성군), 5=대기, 9=NG. 이력 표는 검사 시도 결과를 표시. `v_cell_electrical_latest`는 가장 큰 시도 번호의 현재 결과이며 검사 ID가 없어 이력 표는 원본 관계에서 읽음 |
| 완료 Kit | 파일럿은 `box_id`를 Kit ID로 표시. `packed_at`, 완료 이후 상태(`full`, `handed_over`, `consumed`), 4셀, 그룹·실행 일치를 확인. `v_box_spread.spread_mv`는 OCV 편차이며 V로 변환 |
| 갱신·운영 | 각 패널은 SELECT만 사용. 10초마다 조회하고 화면은 `Asia/Seoul`로 표시. 실제 신선도는 수집기 기록 시점에 따름 |

전기검사 시도와 최종 판정은 구분한다. `cell.status='retest'`의 NG는 재검 대기이고, `rejected`는 최종 실패 상태다. `v_cell_electrical_latest`와 현재 셀 상태만으로 과거 각 시점의 최종 판정을 재구성하는 규칙은 수집기 연동 때 확정한다. 팀 뷰의 최종 검사 ID 제공이 필요한 경우 담당자와 별도로 협의할 수 있다. [팀 DB 테이블 정의](https://github.com/intel7-team2/battery-db/blob/b728829/schema/01_tables.sql) · [팀 DB 조회 뷰](https://github.com/intel7-team2/battery-db/blob/b728829/schema/02_views.sql)

2026-11-23에 실제 팀 DB에서 스테이션 23행, 2A 실행·셀 0건, Grafana 역할의 읽기 전용 모드와 쿼리 제한을 확인했다. 동시 검사, 재검, 단위 환산, 미계측 및 Kit 제외 조건은 읽기 전용 `SELECT`에 샘플 값을 넣어 확인했다.

## 후속 협의

- **Buffer**는 DB에 레인별 현재 재고가 없으므로 브리지 값을 검토한다. 누계에 필요한 실제 출입, 폐기·재작업 감소 규칙은 PLC 담당자와 합의한다.
- **Kit**의 `box_id` 사용은 파일럿 매핑이다. 취소·재작업 상태와 팩 팀 경계가 정해지면 조회 기준을 추가한다.
- **수집기**의 `writer_2a`, 팀 이벤트 UUIDv5 규칙, 메일박스 범위·ACK·현장 시각 출처와 외관 결함 코드표는 [수집 인터페이스](../db-integration/collector-interface.md) 기준으로 담당자와 협의한다. `occurred_at`/`measured_at`은 현장 시각, `received_at`은 DB 기록 시각이다.
- **샘플**의 기대 누계는 투입 24, 외관 NG 1, 재검 2, 재검 합격 1, 제거 2다. 팀 스모크 SQL은 적재 후 롤백하는 DB 쓰기 테스트다. 파일럿은 읽기 전용이므로 이 스크립트 실행을 포함하지 않는다. [팀 스모크 샘플](https://github.com/intel7-team2/battery-db/blob/b728829/schema/test/smoke.sql)
