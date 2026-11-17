# digital-twin-a

인텔 과정 B 프로젝트(디지털 트윈) 3조 저장소.
배터리 조립·검사 공정과 연계할 **가상 전공정**을 Factory I/O + MELSEC Q로 만든다.

현재 계획은 [v0.9 계획서 개정안](docs/plan_v0.9.html) 참고. [인쇄용 PDF](docs/plan_v0.9.pdf)도 제공한다. 프로젝트 실시 계획서 양식을 유지하고 전체 시스템 구성도, 검사·분류 흐름도, I/O 및 조별 인계 규격을 보강했다. 팀 구분은 3조, 지도교수는 김유성 교수님이다.

## 이 PC에서 시연하기

1. 루트의 `START_LINE.cmd`를 더블클릭한다. 로컬 소프트 PLC와 Factory I/O가 준비된다.
2. Factory I/O 상단 **▶**를 누른다. 입고 → 검사 → NG/A/B/C 분류를 시연한다. 4셀 공급은 추가 검증이 필요하다.
3. 새로 시작하려면 상단 ▶를 다시 눌러 편집 모드로 돌아간 후 ▶를 누른다.

GX Works2나 실물 Q03UDE가 구동하는 것이 아니다. `plc/softplc.py`가
`plc/line_v0.txt`의 사용 명령을 해석하는 **시연용 소프트 PLC**다.
전압과 내부저항은 임시 표 값이며 실제 계측값이 아니다.

설치된 Modbus & OPC 에디션의 **Modbus TCP/IP Client**를 사용한다.
서버는 이 PC의 `127.0.0.1:502`에만 열며 실제 설비와 연결하지 않는다.
상세 설정과 검증 상태는 [docs/run-line.md](docs/run-line.md)를 참고한다.

## 폴더 구조

```
docs/                 방향·결정 문서, 계획서
  plan_v0.x.*         계획 문서 (가장 높은 번호가 최신. html / docx / hwp)
  archive/            지나간 버전 (참고용)
factoryio/
  scenes/             Factory I/O 씬 파일 (.factoryio)
  tools/              씬 파일을 텍스트로 만드는 스크립트
plc/
  tagmap.md           Factory I/O 주소 <-> PLC 디바이스 (씬과 같이 생성됨)
  line_v0.csv         GX Works2에서 읽어 들이는 래더 (명령어 목록)
  line_v0.txt         같은 래더를 설명과 함께 읽는 용도
  tools/              래더 생성 스크립트
```

아직 안 정해져서 안 만든 폴더 (정해지면 추가):

- `collector/` PLC 값 읽어서 DB에 쌓는 파이썬 수집기
- `web/` 대시보드, 셀 이력 조회 화면
- `db/` 테이블 스키마 (B팀과 공유)

## 규칙

- 문서는 `docs/`에만. 루트에 파일 늘리지 않기.
- 계획은 `plan_v0.x.html`로 번호를 올려 가며 쓰기. 새 번호가 나오면 이전 것은 `docs/archive/`로.
- 태그맵은 `plc/` 한 곳에서만 관리하고 나머지는 그걸 참조.
- 씬, 태그맵, 래더는 스크립트가 만든 파일이라 손으로 고치지 말고 `tools/`의 스크립트를 고쳐서 다시 생성.
