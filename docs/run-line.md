# line_v0 실행 안내

## 시작

`D:\se4nchoi\digital-twin-a\START_LINE.cmd` 더블클릭 → Factory I/O **▶**.

이 PC에는 Python 3.15와 Factory I/O가 이미 설치되어 있다. 추가 Python 패키지는 필요 없다.
시작 파일은 소프트 PLC가 이미 떠 있으면 재사용한다. Factory I/O가 닫혀 있으면 실행한다.
열려 있던 다른 씬은 자동으로 바꾸지 않으므로, 그 경우 My Scenes에서 `line_v0`를 연다.
시뮬레이션을 실행하면 첫 스캔에서 자동 시작 요청을 한 번 넣는다.

조작반 Stop/E-stop은 운전 자기유지를 해제한다. 재개는 조작반 Start로 한다.
상단 일시정지는 물리 시뮬레이션과 소프트 PLC 타이머를 함께 멈춘다.
새 시연은 상단 ▶를 눌러 편집 모드로 돌아갔다가 다시 ▶로 시작한다.
조작반 Reset만으로는 이미 배치된 부품이 없어지지 않으므로 새 시연은 이 방법을 사용한다.

## 통신

Factory I/O는 Modbus TCP/IP Client, 소프트 PLC는 로컬 서버이다.

| 항목 | 값 |
|---|---|
| Host / Port / Slave ID | 127.0.0.1 / 502 / 1 |
| Read Digital | Inputs |
| Read Register | Input Registers |
| Scale | 1 |
| Digital Inputs / Outputs | 22 / 20 |
| Register Inputs / Outputs | 1 / 0 |
| 모든 Offset | 0 |

Coils 0~18은 센서(`M1000~M1018`), 19/20/21은 실행/일시정지/씬 리셋이다.
Holding Register 0은 비전(`D1000`), Discrete Inputs 0~19는 액추에이터(`M1100~M1119`)이다.
씬에 태그 매핑이 저장되어 있다. 연결 성공은 우측 아래 초록 표시로 확인한다.

`factoryio/auto.cfg`를 이 PC의 `Documents\Factory IO\auto.cfg`에 반영했다.
Factory I/O를 켤 때 저장소 씬 로드, 자동 통신 연결, 실행 전 대기 상태를 지정한다.
다른 프로젝트로 기본 시작 설정을 돌릴 때는 이 설정 파일의 라인 관련 설정을 해제한다.

상태 확인: `http://127.0.0.1:8765/` (읽기 전용 JSON).
시작 실패 기록: `plc/softplc.log`.
통신이 1초 이상 끊기면 컨트롤러의 출력을 지우고 진행 상태를 초기화한다.
연결을 복구한 뒤 상단 ▶로 씬을 새로 시작한다.

## 범위

GX Works2와 연결하지 않는다. GX Works2 CSV 가져오기·컴파일은 아직 별도 검증이 필요하다.
이 실행기는 전체 MELSEC 명령어/PLC의 동작을 재현하는 제품이 아니다.
이 씬에서 사용하는 명령, 100ms 타이머, 인덱스 지정만 구현했다.
지원하지 않는 명령은 실행 전에 오류로 처리한다.

판정값은 PLC 내부 임시 표이다. LOT 보류가 누적되면 해당 LOT가 계속 NG로 분류되는 것이 설계 동작이다.
부품 색은 LOT이고 등급은 임시 계측값에 따라 결정하므로 색과 레인이 고정 대응하지 않는다.

## 생성 및 검사

저장소 루트에서 실행한다.

```powershell
python factoryio/tools/build_line.py D:/programs/factoryIO/Scenes factoryio/scenes/poc_v0.factoryio factoryio/scenes/line_v0.factoryio plc/tagmap.md
python plc/tools/gen_ladder.py plc
python -m unittest discover -s plc -v
```

변경은 생성 스크립트에 반영한다. 생성한 씬/래더를 수동 수정하지 않는다.
원래 씬은 `factoryio/scenes/line_v0.before-modbus.factoryio`에 백업했다.

## 2026년 11월 17일 검증 상태

씬 로드, Modbus 통신, 센서 입출력 및 NG/A/B/C 분류 동작을 확인했다.
소프트 PLC 자동 검사 8개가 통과했다.
최종 통합 시험에서는 4셀 공급 완료가 확인되지 않고 이상 플래그가 발생했다.
블레이드 동작, 실제 배출 수량과 출구 감지의 통합 검증이 남아 있다.
GX Works2 가져오기·컴파일, 실제 PLC 연계 및 이력 화면은 미검증 또는 개발 예정이다.
