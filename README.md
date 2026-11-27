# digital-twin-a

<img src="docs/assets/cellect-wordmark.svg" alt="Cellect" height="56">

인텔 과정 B 프로젝트(디지털 트윈) 2A **Cellect**(Cell + Select) 저장소.
배터리 조립·검사 공정과 연계할 **가상 전공정**을 Factory I/O + MELSEC Q로 만든다.

현재 계획서는 [v0.18 (hwp)](docs/plan_v0.18.hwp)다. 교수님 피드백(계획서는 hwp로 통일, 보고서처럼 너무 자세하지 않게)에 맞춰 과정 양식과 1조a 계획서 구성을 섞어 다시 썼다. 계획서에서 뺀 상세 규칙은 [설계 메모](docs/design-notes.md)에 있다. 팀 구분은 2A(후공정은 2B), 지도교수는 김유성 교수님이다. [검토·인계 노트](docs/handoff/HANDOFF_2026-11-17.md)에 문제 정의와 미확정 항목을 정리했다.

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
  plan_v0.x.hwp       계획서 (가장 높은 번호가 최신, v0.17부터 hwp만)
  design-notes.md     계획서에서 뺀 상세 규칙 (구현 참고용)
  interface.md        PLC 디바이스 배정, Python 브리지 신호 규약 (초안)
  open-decisions.md   사람이 정해 줘야 하는 것 + 제안, 일정 제안
  abnormal-cases.md   비정상 상황 시험 8건 (재현·기대 동작·복구)
  analysis/           PLC 없이 돌리는 분석 (세트 편차 비교 시뮬 등)
  assets/cellect-*    팀 로고 (워드마크, 흰색 워드마크, 프사용 512px)
  assets/hwp/         계획서 그림 (html 원본과 png)
  tools/hwp/          계획서 hwp 생성 도구
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
- 계획서는 `plan_v0.x.hwp`로 번호를 올려 가며 쓰기. 새 번호가 나오면 이전 것은 `docs/archive/`로.
- v0.17 hwp는 `docs/tools/hwp/BuildPlan.java`로 만들었다. 틀로 쓴 1조a 계획서와 hwplib(1.1.11) jar는 저장소에 넣지 않았다. 이후 수정은 한글에서 직접 해도 된다.
- 태그맵은 `plc/` 한 곳에서만 관리하고 나머지는 그걸 참조.
- 씬, 태그맵, 래더는 스크립트가 만든 파일이라 손으로 고치지 말고 `tools/`의 스크립트를 고쳐서 다시 생성.
