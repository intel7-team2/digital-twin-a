# Cellect 2A 실데이터 연동 검증

## 기존 화면과 실행

| 화면 | 조회와 용도 |
| --- | --- |
| [고정 모의](http://127.0.0.1:3300/d/cellect-scada-demo) | Grafana TestData의 고정 CSV |
| [라이브 모의](http://127.0.0.1:3300/d/cellect-scada-live) | `8766` Graphite 어댑터가 로컬 SQLite 이벤트를 조회. 별도 모의 서버 실행. |
| [Production SCADA](http://127.0.0.1:3300/d/cellect-2a-production-db) | PostgreSQL `bg551q8i4v6rkb`. 회차, 검사, Kit와 추적 상세. |
| [Overview v2](http://127.0.0.1:3300/d/cellect-2a-scada-overview-v2) | 같은 PostgreSQL UID. 다섯 SELECT를 패널 사이에서 공유. 10초 갱신. |

Grafana는 `docs/scada/Start-Grafana.ps1`로 시작하고 DB 터널은 별도 PowerShell에서 유지한다. 모의 서버는 `python -B .\docs\scada\simulation\server.py`로 시작한다. 기본 `3300` 프로비저닝은 `docs/scada/dashboards/`를 읽는다. 자세한 실행과 재시작은 [SCADA README](../README.md)를 참조한다.

## 스키마와 SQL 확인

`battery-db` `main`의 검증 스냅샷은 `9c0c146048554107cef2d9463bbd3276bae72a00`이다. `b728829` 대비 기존 테이블·뷰 정의와 시드는 동일하다. `schema/05_api.sql`에서 `event_log.api_client`, `sim_run.api_client`, `api_access_log`, `v_api_usage`를 추가했다. SCADA 패널 SQL은 기존 공정 스키마를 조회한다. [테이블](https://github.com/intel7-team2/battery-db/blob/9c0c146048554107cef2d9463bbd3276bae72a00/schema/01_tables.sql) · [뷰](https://github.com/intel7-team2/battery-db/blob/9c0c146048554107cef2d9463bbd3276bae72a00/schema/02_views.sql) · [API 변경](https://github.com/intel7-team2/battery-db/blob/9c0c146048554107cef2d9463bbd3276bae72a00/schema/05_api.sql)

현재 PC에 독립 PostgreSQL 16.15와 Grafana OSS 13.3.1로 QA 인스턴스를 구성했다. 최신 정의와 시드로 기준 카탈로그를 만들고, Grafana의 PostgreSQL 조회 API를 통해 스테이션 23행, 읽기 전용 모드 및 두 운영 대시보드의 SQL 10개를 빈 회차와 샘플 회차에서 실행했다. 기준 카탈로그는 Git에서 제외되는 `.local/integration-qa/catalog-reference.json`에 있다.

| 검증 | 독립 QA 결과 |
| --- | --- |
| 빈 DB | 회차 없음, KPI `NULL`, 개별 검사기 `미수집`, 조회 오류 없이 목록 0행 |
| 데이터 있는 DB | 최신 2A 선택, 명시 회차/존재하지 않는 회차, 2A 외 회차 제외, 과거 시간 범위에서 회차 간 혼합 방지 |
| 생산·품질 | 재검 이력 추가에도 투입은 6셀, 외관 PASS 5·NG 1, 최종 전기 PASS 4·NG 0, 재검 대기 1. 두 attempt의 원본 검사와 OCV(V)·IR(mΩ) 확인. |
| 포장·추적 | 상태만 완료인 불완전 Kit 제외. 완료 Kit 1개, 구성 4셀과 인계 확인. |
| 설비와 수신 | `idle`, 종료된 `busy`, 미수집, 수신 지연, 열린 `COMM_LOST`, 종료된 회차와 실패한 SQL을 구분 |

운영 `3300`에서 2026-11-24 사용자가 읽기 전용 검증 도구를 실행했다. 스테이션 23행, 2A 회차 1건, 셀 100건, 공정 이벤트 305건을 확인했다. API 마이그레이션 객체가 있었고 SCADA·API 감사 카탈로그는 로컬 기준과 일치했다. 두 대시보드의 SELECT 10개가 모두 성공했다. 기본 시간 범위에서 검사·Kit은 0행, ID 미입력 상태에서 추적도 0행이었다. 이 검사로 브라우저 렌더링까지 확인되지는 않았다.

운영 조회 권한이 있는 기존 Grafana API 토큰을 아래 도구에 숨김 입력해 검증을 반복할 수 있다. 로컬 기준 파일이 없으면 `--reference`를 생략해 운영 스키마의 주요 객체와 API 마이그레이션 존재 여부를 확인한다.

```powershell
python -X utf8 -B .\docs\scada\verify_postgres.py --prompt-token --reference .\docs\scada\.local\integration-qa\catalog-reference.json
```

비교 범위는 SCADA·API 감사 관련 객체의 컬럼 타입·NULL 가능 여부와 뷰 정의다. 도구는 팀 DB에 SELECT만 발행하며, 인증 정보는 파일과 로그에 기록하지 않는다. `SELECT OK · 0 rows`는 조회 성공이며, HTTP·데이터 소스 오류는 실패로 출력한다. 선택 회차의 전기검사·Kit 기록은 `시간 범위 안 / 회차 전체` 건수를 함께 표시한다. 회차 전체에 기록이 있으면 시간 범위를 늘려 확인한다. 두 ID가 비어 있으면 추적 패널은 0행이다. `--run-id`, `--cell-id`, `--kit-id`, `--hours`로 필터 케이스를 재현할 수 있다.

## Factory I/O 통합 인수 순서

1. 승인된 테스트 회차와 시작 시각을 DB·PLC 담당자와 확정한다. 브리지는 `run_id`를 생성하거나 인계받아 Cell, 검사, 이벤트, 설비, Kit에 같은 회차 키를 유지한다. 운영 공용 DB에 수동 샘플을 넣는 대신 승인된 스테이징 또는 별도 로컬 DB에서 수행한다.
2. Factory I/O 정상 4셀과 외관 NG, 전기 NG 후 재검 대기·회복을 차례로 흘린다. Overview v2 회차 필터를 지정하고 투입·판정·재검 집계와 검사 ID를 대조한다. 판정과 계측은 다른 레인 또는 시도에서 발생하더라도 실제 Cell ID로 연결한다.
3. 동일 특성군 Kit의 네 슬롯과 포장 완료 시각을 확인한 후 인계 요청, 출구 통과, 수신 확인을 순서대로 추적한다. 불완전 Kit가 완료 KPI에 들어가지 않는지 확인하고 명시 이전 회차에서 새 데이터의 혼입 여부를 확인한다.
4. 브리지를 중단해 이벤트 유입 지연을 확인한 뒤 재연결·재전송을 검사한다. 단순 유입 지연은 장애로 단정하지 않는다. 수집기가 열린 `COMM_LOST`를 기록하면 장애로 표시된다. Grafana 접속 또는 조회 실패는 패널 오류로 구분한다.

## 담당자 확인 사항

- **PLC·브리지**는 [이벤트 봉투](collector-interface.md)의 생산자·세션·순번·ACK 규칙, 발생 시각의 출처, 레인 재고 근거, 하트비트 및 `COMM_LOST` 생성·해제를 확정한다. 센서와 Buffer 점유량은 현재 `미수집`이다. 진행 중 회차 수신 후 30초는 발표용 지연 참고값이다. 유휴 구간과 설비 통신 장애의 구분에는 하트비트가 필요하다.
- **DB**는 실물 Cell의 `run_id` 연결, 재전송 키와 배치 확정, 4슬롯·Kit 완료의 트랜잭션 경계, 취소·재작업·인계 상태 규칙을 확정한다. 이벤트 양이 늘면 `event_log`의 회차·발생/수신 시각 조회 계획과 `equipment_state` 이력 조회 비용을 담당자와 확인한다.
- **수집기**의 로컬 SQLite 대기열은 구현됐다. PLC ACK, 공용 DB 쓰기 전송기와 배포는 규칙 확정 후 연결한다. 현재 대시보드는 커밋된 실제 PostgreSQL 값을 10초마다 조회한다.
