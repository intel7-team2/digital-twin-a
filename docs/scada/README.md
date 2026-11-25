# Cellect 2A Grafana SCADA 개발 환경

Grafana OSS 13.3.1 / Windows에서 시작용 대시보드를 실행한다. SCADA는 검사·분류·포장 상태와 이력을 읽기 전용으로 조회한다. 운전·정지, 판정 기준 변경, 알람 확인은 별도 HMI와 PLC의 역할이다.

시간에 따라 진행되는 공정과 개별 셀 이력을 확인하려면 [라이브 시뮬레이션 실행 안내](simulation/README.md)를 참고한다. 아래의 고정 TestData 화면도 같은 개발 인스턴스에서 열 수 있다.

## 업무별 SCADA

Grafana 3300의 [01 메인 · 회차 총괄](http://127.0.0.1:3300/d/cellect-2a-main)에서 시작한다. 상단 메뉴를 사용하면 선택 회차·기간과 입력한 조회 필터가 이어진다. 팀 LAN에서 접속할 때는 로컬 주소 대신 Grafana가 열려 있는 개발 PC의 LAN 주소를 사용한다.

| 화면 | 용도 |
| --- | --- |
| [01 메인 · 회차 총괄](http://127.0.0.1:3300/d/cellect-2a-main) | 회차·출처·수신 상태, 생산 KPI 4개, 비교 표본과 편차 감소율, 최근 열린 알람 |
| [02 공정 관제](http://127.0.0.1:3300/d/cellect-2a-process) | 컨베이어 평면도, T1~T4·RT, 기록 기반 Cell 단계 추적과 열린 알람 |
| [03 생산·인계](http://127.0.0.1:3300/d/cellect-2a-production-flow) | 회차 누계, 선택 기간 분당 생산량, 특성군별 셀·Kit 수와 인계 현황 |
| [04 품질·설비 분석](http://127.0.0.1:3300/d/cellect-2a-quality-equipment) | 외관·전기 NG율, 재검 회복률, OCV·IR, 편차 비교와 관측된 장애 지속시간 |
| [05 DB 이력·추적](http://127.0.0.1:3300/d/cellect-2a-trace) | Cell ID·Kit ID·LOT 검색, 검사 원본과 구성 슬롯, 공정·설비 이벤트 |

메인·공정·생산은 10초 자동 갱신한다. 품질·DB 이력은 범위를 바꿀 때와 수동 새로고침 시 조회한다. 합격률과 최종 전기 NG율은 최종 판정이 확정된 셀 기준이다. 외관 NG율은 최신 외관 판정이 확정된 셀, 재검 회복률은 재검을 받은 고유 셀 기준이다. 공정 관제는 DB 기록을 표시하며, Factory I/O·Buffer 실시간 수집과 수리 완료 기반 MTTR은 미연동이다.

업무별 JSON은 현재 발표용 JSON의 검증된 패널에서 생성한다. 공유 패널 정의나 업무별 배치를 변경한 뒤 아래 명령을 실행한다.

```powershell
python -X utf8 -B .\docs\scada\build_role_dashboards.py
```

## 기존 검증·발표 화면과 연동 자료

- [운영 SCADA Overview v2](http://127.0.0.1:3300/d/cellect-2a-scada-overview-v2?theme=dark&kiosk)
- [SCADA 관제 · 발표용](http://127.0.0.1:3300/d/cellect-2a-scada-presentation?theme=dark&kiosk)
- [실데이터 연동 검증 결과와 Factory I/O 통합 절차](db-integration/integration-test.md)
- [팀 PostgreSQL 읽기 전용 파일럿 실행과 확인 항목](postgres-pilot/README.md)
- [현재 이벤트 구조와 패널 필드·단위·갱신 주기](db-integration/current-data-flow.md)
- [DB 조회 인터페이스와 SQLite/PostgreSQL 전환 설계](db-integration/read-interface.md)
- [Factory I/O·PLC 이벤트 수집 인터페이스](db-integration/collector-interface.md)
- [02 공정 관제 셀 위치 연동 뼈대와 로컬 테스트](db-integration/cell-position-adapter.md)
- [DB 담당자에게 전달할 협의사항과 인수 기준](db-integration/db-handoff.md)

발표용 화면은 기존 Overview v2와 같은 PostgreSQL 데이터 소스를 사용한다. 상단에 회차와 마지막 DB 수신을, 중앙에 컨베이어 평면도와 검사기·알람을 배치했다. 평면도에는 T1~T4 병렬 검사, RT 재검 복귀, 외관·최종 NG 배출, A/B/C 레인과 4셀 트레이가 표시된다. 트레이 숫자는 슬롯 번호이고 실시간 셀 위치와 Buffer 점유량은 미수집으로 표시한다.

- **편차 비교**는 선택 회차에서 완료 상태, 동일 특성군 4슬롯, 유효한 최종 OCV 4개를 확인한 Kit를 대상으로 한다. 두 방식에 동일한 셀을 사용한다. 2 Kit 미만은 표본 부족으로, 기준 편차가 0이면 감소율을 비교 불가로 표시한다. 50%는 [설계 메모의 잠정 목표](../design-notes.md#편차-비교-방법)다.
- **인계**는 출구와 수신 기록이 없는 요청 접수, 출구 통과, 수신 확인을 해당 기록이 있는 고유 Kit로 집계한다. 출구 통과와 수신 확인 집계에는 같은 Kit가 포함될 수 있다.
- **셀 이력**은 Cell ID와 단계 번호를 선택하면 공정 평면도에 해당 기록 지점을 표시한다. 단계 번호를 비우면 마지막 기록을 표시한다. 단계 표는 기록 시각 순이며, 포장 시각이 전기검사 시각보다 이르면 포장 기록에 확인 메시지를 표시한다. 추이 그래프나 Kit 상세를 시연할 때는 검사·포장 시각이 포함되는 시간 범위를 선택한다.

## 저장소 분석과 작업 순서

| 위치 | 현재 역할 |
| --- | --- |
| [`docs/`](../) | 팀 계획서와 공정·데이터·인터페이스 문서. [공정 v2 및 공용 DB 현황](../2a-data-design.md)을 SCADA 설계 기준으로 사용한다. |
| [`factoryio/`](../../factoryio/) | Factory I/O 시연 씬과 생성 도구 |
| [`plc/`](../../plc/) | PLC 래더, 태그맵, 소프트 PLC와 시험 도구 |
| [`START_LINE.cmd`](../../START_LINE.cmd) | 기존 Factory I/O·소프트 PLC 시연 진입점 |

1. `docs/scada/`에서 Grafana 설정, 대시보드 JSON, SCADA 문서를 관리한다.
2. [전체 화면 설계](dashboard-design.md)에 따라 모의 데이터로 셀 이력과 Kit 추적을 먼저 검증한다.
3. [데이터 요청 목록](db-data-requirements.md)을 공용 DB 담당자와 확인한 뒤 읽기 전용 데이터 소스를 연결한다.

## Windows에서 실행

Grafana OSS 13.3.1이 설치된 PC에서 저장소 루트를 열고 실행한다. 기본 설치 경로는 `C:\Program Files\GrafanaLabs\grafana`다. 다른 위치에 설치했다면 `-GrafanaHome 'D:\Grafana'`를, 개발 포트가 사용 중이면 `-Port 3301`을 명령 끝에 붙인다. [Grafana OSS 13.3.1 Windows 다운로드](https://grafana.com/grafana/download/13.3.1?edition=oss&platform=windows)

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\docs\scada\Start-Grafana.ps1
```

다른 PowerShell에서 `python -X utf8 -B .\docs\scada\check_environment.py`를 실행하면 `3300`의 응답, Overview v2 등록과 갱신 설정, PostgreSQL 데이터 소스 UID, 로컬 `5433` 연결, 선택 사항인 모의 서버 `8766`을 확인한다. 기본 개발 인스턴스의 로컬 등록 메타데이터만 읽는다. `5433` TCP 연결 성공은 실제 PostgreSQL 로그인·SELECT 및 화면 표시 결과와 별개다.

발표 전 검증은 다음 순서로 진행한다.

1. **화면 검증.** 팀 DB 터널과 `3300`을 연 뒤, PostgreSQL 조회와 Overview v2의 KPI·Canvas·검사 상태·차트·추적을 1920×1080에서 확인한다. 근거 데이터가 없을 때 `미수집`이 표시되는지 확인하고, 조회 오류와 구분한다.
2. **수집 경로 검증.** [수집 인터페이스](db-integration/collector-interface.md)의 키·순번·ACK 규칙을 DB·PLC 담당자와 합의한다. 승인된 스테이징 회차에서 검사·포장 이벤트와 화면 집계를 대조한다.
3. **발표 리허설.** 회차 선택 → OCV·IR 확인 → Cell ID·Kit ID 추적 순으로 시연한다. 연결이 끊기면 [라이브 모의 대시보드](http://127.0.0.1:3300/d/cellect-scada-live)를 별도 모의 화면으로 시연한다.

1. 콘솔에서 `HTTP Server Listen` 로그를 확인한 뒤 [Cellect SCADA 모의 대시보드](http://127.0.0.1:3300/d/cellect-scada-demo)를 연다. 새 개발 인스턴스의 초기 로그인은 `admin` / `admin`이며 첫 로그인에서 비밀번호를 변경한다.
2. `Cellect SCADA` 폴더와 `Cellect SCADA TestData` 데이터 소스는 자동 등록된다. 패널 수정은 [`dashboards/cellect-scada-demo.json`](dashboards/cellect-scada-demo.json)에 반영한다. 실행 중인 인스턴스가 약 30초 간격으로 변경 사항을 읽는다.
3. 종료하려면 실행 콘솔에서 `Ctrl+C`를 누른다. Grafana 설정·로그인 상태를 담는 로컬 SQLite와 로그는 Git에서 제외한 `.local/`에 저장된다. 개발 인스턴스는 루프백 주소를 사용한다.

## DB 없이 검증

첫 단계는 Grafana 내장 TestData의 **CSV Content**에 저장한 `DEMO-RUN-01` 고정 스냅샷이다. 외부 DB, Factory I/O, PLC를 켜지 않고 실행할 수 있다. 수치는 패널 JSON에 포함된 고정값이며 시간 필터와 조회 SQL은 공용 DB 연결 단계에서 검증한다. Grafana Explore에서 Random Walk 또는 Predictable Pulse를 사용하면 시간 차트와 갱신 동작을 별도로 연습할 수 있다. [Grafana TestData 시나리오](https://grafana.com/docs/grafana/latest/datasources/testdata/query-editor/)

| 확인 위치 | 기대 결과 |
| --- | --- |
| 공정 요약 | ID 부여 16셀, 외관 PASS 15셀, 최종 전기검사 PASS 13셀, A/B/C 분류 13셀, 완료 Kit 3개 |
| 특성군별 현황 | A/B/C 분류 5/4/4셀, 각 4셀 포장, A 1셀 대기 |
| 완료 Kit | 각 Kit는 동일 특성군의 고유 셀 4개, 슬롯 1~4, 예시 OCV 편차 0.006 V, IR 편차 1.5 mΩ |
| 셀 목록 | `DEMO-C008` 재검 PASS, `DEMO-C013` 외관 FAIL, `DEMO-C014` 재검 후 FAIL, `DEMO-C015` 검사 결과 대기, `DEMO-C016` 포장 대기 |

시간 범위, 재검 시도별 이력, 계보 조인을 시험할 때는 공용 DB 담당자가 제공한 스테이징 데이터나 익명 샘플을 사용한다. 스테이징을 기다리는 동안에는 TestData의 고정 CSV로 상태 표시와 레이아웃을 확인한다.
