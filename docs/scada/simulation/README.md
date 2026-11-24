# Cellect 2A 라이브 시뮬레이션

## 실행

Windows에서 Python 3.10 이상과 기존 Grafana OSS 13.3.1 설치를 사용한다. 저장소 루트에서 PowerShell 두 개를 열고 각각 아래 명령을 실행한다. `3300` 개발 인스턴스가 이미 떠 있었다면 새 데이터 소스를 등록하도록 그 개발 인스턴스만 재시작한다.

```powershell
python -B .\docs\scada\simulation\server.py
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\docs\scada\Start-Grafana.ps1
```

- [라이브 대시보드](http://127.0.0.1:3300/d/cellect-scada-live)에서 5초마다 갱신되는 생산·검사 누계, 그룹별 Buffer, OCV·IR 검사값, 완료 Kit 수를 확인한다.
- 대시보드 상단의 **Cell / Kit 이력 조회** 또는 [이력 화면](http://127.0.0.1:8766/trace)에서 ID를 클릭하거나 검색한다. OCV·IR 그래프의 점에서 **검사 셀 이력**을 열면 해당 검사값을 남긴 셀의 이력을 조회한다. 그래프는 한국 시각, 이력 표는 UTC로 표시한다.
- 기본 간격은 2초며 첫 Kit는 기본 실행에서 약 30초 후 생성된다. 빠른 검증에는 시뮬레이터 명령 뒤에 `--interval 1`을 붙인다. `--seed`는 측정값 편차를 재현할 때 사용한다.
- 각 콘솔에서 `Ctrl+C`로 종료한다. 시뮬레이터를 다시 시작하면 새 실행 ID로 공정이 시작된다. 이전 셀·Kit ID를 검색하면 `.local/simulation.sqlite3`에 남은 이력을 조회할 수 있다. 실행 종료 시점에 진행 중이던 셀은 그 상태까지 기록된다.

## 공정과 수치의 관계

각 셀은 ID 부여 → Vision 외관 → OCV·IR → 특성군 분류 → 포장을 순서대로 진행한다. 단계는 셀마다 틱을 달리해 기록하고 셀 여러 개가 서로 다른 단계에서 진행된다. 외관 FAIL은 전기검사를 건너뛰고 종료된다. 전기검사 FAIL은 OCV·IR 측정값과 결과를 남긴 뒤 종료된다.

전기검사 PASS 셀은 OCV와 IR 두 값의 정규화 거리로 가장 가까운 A/B/C 특성군에 배정한다. 데모 임계값과 특성군 중심값은 시뮬레이터 코드에 두며, 실제 공정 기준은 담당자와 별도 협의한다. 한 그룹에 4셀이 모이면 다음 틱에 먼저 들어온 4셀을 슬롯 1~4로 포장한다. 슬롯 이벤트 4건과 Kit 완료 이벤트 1건은 한 트랜잭션에서 저장한다.

| 대시보드 항목 | SQLite 이벤트에서 집계하는 기준 |
| --- | --- |
| 생산량 | `ID_ASSIGNED` 고유 셀 누계 |
| PASS/FAIL | `VISION`, `ELECTRICAL`의 결과별 누계 |
| OCV 및 IR | 해당 시각의 `ELECTRICAL` 이벤트 값. 검사 이벤트가 없는 시각은 결측으로 표시 |
| Buffer | 특성군별 `SORTED` 누계에서 `PACKED` 셀 누계를 뺀 값 |
| Kit | `KIT_CREATED` 이벤트 누계 |

시간 선택기는 현재 실행에서 그래프에 그릴 시점을 정한다. 누계와 Buffer는 실행 시작부터 해당 시점까지의 기록을 반영한다. 초기에는 단계별 진행 차이와 포장 대기 때문에 공정별 셀 수가 다르다.

## 데이터 소스

| 용도 | 연결 |
| --- | --- |
| 고정 화면 | 기존 `cellect-scada-testdata` / Grafana TestData |
| 라이브 모의 공정 | `cellect-scada-simulation` / Grafana 내장 Graphite → `127.0.0.1:8766`의 읽기 전용 로컬 어댑터 → 모의 SQLite 이벤트 |
| 실제 DB | 향후 별도 PostgreSQL 데이터 소스 UID와 읽기 전용 접속으로 설정. 조회 정의는 [DB 요청 문서](../db-data-requirements.md) 기준으로 협의 |

Graphite 어댑터는 대시보드에 필요한 정확한 메트릭 경로, 시간 범위와 JSON 응답을 제공한다. 별도 Graphite 서버 설치는 필요 없다. 이력은 `GET /api/history?cell_id=...` 또는 `GET /api/history?kit_id=...`로도 읽을 수 있다. [Grafana Graphite 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/graphite/) · [Graphite Render API](https://graphite.readthedocs.io/en/latest/render_api.html)

## 검증 명령

```powershell
python -B -m unittest discover -s docs/scada/simulation -v
```

60셀 실행에서 단계 순서와 두 FAIL 분기, 특성군 배정, Kit 구성·슬롯·셀 중복, 매 틱의 원장 대조, 재시작 후 이력 조회, 검사 시각으로 셀 찾기를 확인한다.
