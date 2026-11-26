# Cellect 2A GP-Pro EX 가져오기용 화면

[작화 설계](../gp-pro-ex-screen-plan.md)의 Base Screen 8개를 **임시 800×480 PNG**로 그렸다. 각 PNG는 GP-Pro EX에 가져오기 위한 배경 원본이다. 운전 값과 메뉴 글자는 이미지에 표시된 자리이며, 버튼 동작과 표시기 데이터는 프로젝트 안에서 연결한다. 사진 속 글자가 프로젝트에서 편집 가능한 문자 객체로 변환되지는 않는다.

| 화면 번호 | PNG |
| --- | --- |
| 100 메인 운전 | [B100.png](B100.png) |
| 200 설비 관제 | [B200.png](B200.png) |
| 210 검사기 상세 | [B210.png](B210.png) |
| 220 보조 설비 | [B220.png](B220.png) |
| 300 검사·분류 | [B300.png](B300.png) |
| 400 포장·인계 | [B400.png](B400.png) |
| 500 알람 | [B500.png](B500.png) |
| 510 판정 기준 조회 | [B510.png](B510.png) |

## 작화에 가져오기

1. GP-Pro EX에서 대상 표시기 모델과 해상도를 확인한다. Base Screen 번호는 위 표에 맞춰 만든다.
2. 각 Base Screen에서 **Draw → Image Placement**로 PNG를 배치한다. 하단 메뉴 5개 위에 화면 전환 스위치를 배치한다. 800×480 원본 기준 메뉴 영역은 x=18, 172, 326, 480, 634에서 시작하며, y=433, 폭 148, 높이 34다.
3. B200의 T1~T4·RT 카드에는 B210 상세 이동을 연결한다. B500의 판정 기준에는 B510 이동을 연결한다. 값 영역 위에 승인된 태그를 사용하는 표시기를 추가한다. START·STOP·RESET은 이번 오프라인 작화에서 작동을 배정하지 않는다.
4. 화면 전환과 터치 위치는 GP-Pro EX 자체 시뮬레이션에서 확인한다.

[Pro-face 이미지 배치 매뉴얼](https://www.pro-face.com/otasuke/files/manual/gpproex/refer/data/Draw.pdf)

## 크기 변경

Windows PowerShell 7에서 아래 명령으로 PNG를 다시 생성한다. 원본의 화면 비율을 유지하며 남는 공간에는 같은 배경색을 채운다. 실제 장치가 800×480과 다른 비율이라면 출력과 터치 영역을 검수한다.

```powershell
pwsh -NoProfile -File .\docs\hmi\gp-pro-ex\Render-BaseScreens.ps1 -Width 800 -Height 480
```

## 실물 HMI 없이 PC에서 검수하기

[`Cellect-2A-PCAT.prxe`](Cellect-2A-PCAT.prxe)는 GP-Pro EX 4.09.600에서 저장한 800×480 PC/AT 프로젝트다. 메인 운전 `B100.png`를 시작 화면 Base 1에, 검사기 상세 `B210.png`를 Base 2에 배치했다. **Simulation**(`F12`)에서 메인의 **T1–T4** 카드를 눌러 상세로 이동하고, 상세 하단의 **메인**을 눌러 복귀하는 것을 확인했다. 다른 메뉴와 검사기 개별 선택, START·STOP·RESET은 이 프로젝트에서 연결 전이다. 운전 명령과 LOT 보류는 [오프라인 시제품](../prototype/README.md)에서 연습할 수 있다. `Cellect-2A-PCAT.bake`는 편집기가 자동 생성한 이전 저장본이다.

GP-Pro EX 4.09.600 Limited Edition에서 `IPC Series (PC/AT)` → `PC/AT` → `800×480 (WVGA)`를 선택하면 이 폴더의 PNG를 원본 해상도로 쓸 수 있다. PLC 주소는 실제 연결이 승인되기 전까지 연결하지 않고, 화면 배치와 터치 전환은 편집기 상단의 **Simulation**에서 검수한다. [GP-Pro EX 시뮬레이션 설정](https://www.proface.com/data/manual/gpproex/v4_0/refer/mergedProjects/simulation/simulation_sg_simulation.htm)

WinGP는 별도 Windows 런타임으로, 4.09.600 **Disc 2**에서 설치한다. 설치 후 매뉴얼에 따라 PC를 재시작한다. 이 PC에서 WinGP 실행과 Trial 시작 화면의 **3시간 제한**을 확인했다. 상시 구동에는 PC/AT용 WinGP 라이선스가 필요하다. 같은 PC에서 배포를 검증할 경우 Transfer Tool에서 대상 주소 `127.0.0.1`을 직접 지정하고, 편집기의 에디션에서 WinGP로 전송할 수 있는지 확인한다. [WinGP 설치](https://www.proface.com/data/manual/gpproex/v4_0/refer/mergedProjects/wingp/wingp_pr_install.htm) · [동일 PC 전송](https://www.proface.com/data/manual/gpproex/v4_0/refer/mergedProjects/wingp/wingp_mm_pcssame.htm)

## I/O 할당표 인수

[io-map.csv](io-map.csv)의 `symbol`은 화면에서 사용할 이름이다. 새 화면 부품을 만들 때 이 이름을 기준으로 연결한다. `screen`은 설계상 배치 위치이며 현재 프로젝트에서 B100과 B210은 각각 Base 1과 Base 2다. 주소가 확인되기 전에는 `pending`으로 유지한다. 기능 사용 여부는 실제 관측 값과 품질을 확인한 뒤 판단한다. [표시 데이터 및 명령 계약](../interfaces.md) · [PoC와 v2 주소 대응](../plc-tag-map.md)

| 항목 | I/O 할당표를 받은 뒤 적용할 내용 |
| --- | --- |
| `bit`, `word` | 브리지가 HMI에 게시하는 읽기 전용 포인트. 확인한 `device`, 해당 GP 드라이버가 받는 `gp_address`, 조원과 확인한 I/O 표 버전을 `reference`에 기록하고 `approved`로 바꾼다. 워드는 단일 워드다. |
| `bridge` | Cell/Kit ID, 측정 묶음, 시각, 여러 슬롯처럼 데이터 폭·유효 조건·갱신 순서가 필요한 항목. 브리지 계약 참조를 기록한다. 화면용 주소를 게시할 수 있는지 확인한 후 표현을 정한다. |
| START·STOP·RESET | 화면은 브리지 요청을 보낸다. `command_id`로 접수와 결과를 묶고, 실제 운전 상태는 관측 포인트로 표시한다. 명령 경로의 승인 및 응답 검증 전에는 실제 동작을 연결하지 않는다. PLC 쓰기는 브리지가 담당한다. |

저장소 루트에서 실행하면 주소표 형식과 승인 상태를 확인할 수 있다.

```powershell
python -B .\docs\hmi\gp-pro-ex\prepare_io.py
```

승인된 비트·단일 워드가 생기면 저장한 I/O 할당표 사본에서 대상 디바이스의 가져오기 파일을 생성한다. `device`에는 GP-Pro EX에 구성한 브리지 디바이스 이름을 동일하게 입력한다.

```powershell
python -B .\docs\hmi\gp-pro-ex\prepare_io.py --map .\docs\hmi\gp-pro-ex\io-map.csv --device '<브리지 디바이스 이름>' --output .\gp-read-symbols.csv
```

GP-Pro EX에서 **Common Settings → Symbol Variable → Utility → Import → Other Formats**를 사용한다. 대상 디바이스를 확인하고 데이터 시작 행 `2`, 열 `Name / Type / Address`, 비트 `BIT`, 워드 `WORD`를 선택한다. 이름이 같은 심볼은 가져오기 시 덮어쓰므로 기존 정의와 대조한 후 프로젝트 사본에서 먼저 검수한다. [Pro-face 심볼 가져오기 안내](https://www.proface.com/data/manual/gpproex/v4_0/refer/mergedProjects/draw/draw_sg_symbolother.htm)

현재 프로젝트의 PNG 배경과 GP 네이티브 표시기·명령 부품은 연결 전이다. 주소표 검사기는 통신을 열지 않으며, 실제 주소의 드라이버 문법과 비트/워드 범위는 승인된 할당표와 GP-Pro EX 가져오기 결과로 검증한다.
