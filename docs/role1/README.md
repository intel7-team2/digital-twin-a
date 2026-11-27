# 역할① 투입 · 분배 · 측정기 4대 (박해준)

2026-11-27 기준. 팀 main의 소프트 PLC(Modbus) 방식과 달리, 이 폴더는
**GX Works2 + GX Simulator2 + MX OPC Server 6.10 + Factory I/O (OPC Client DA/UA)** 방식이다.

## 파일
| 파일 | 내용 |
|---|---|
| `plc/role1/pivot_arm_sorter.gxw` | 래더 (Q03UDE, GX Works2) |
| `plc/role1/role1_mxopc_tags.csv` | MX OPC 태그 68개 (MX Configurator에서 Import) |
| `plc/role1/역할1_디바이스코멘트.txt` | 디바이스 코멘트 목록 |
| `factoryio/scenes/role1_pivot_arm_sorter.factoryio` | Factory I/O 씬 (Pivot Arm Sorter 4개, 머시닝 센터 4대) |
| `docs/role1/역할1_IO표.html` | I/O 표 (브라우저로 열기, 검색 가능) |
| `docs/role1/역할1_IO표.txt` | I/O 표 텍스트판 |
| `docs/role1/측정값_생성_정리.md` | 전압·저항 값 만들기와 등급 판정 정리 |

## 실행 순서
1. GX Works2에서 `pivot_arm_sorter.gxw` 열기 → 시뮬레이션 시작 (GX Simulator2, Simulator A)
2. MX OPC Configurator에서 태그 CSV Import (처음 한 번) → 런타임 ▶
3. Factory I/O 씬 열기 → 드라이버 OPC Client DA/UA, 서버 `Mitsubishi.MXOPC.6` → DISCONNECT → CONNECT
4. Factory I/O ▶ → 화면의 Start 버튼

시뮬레이터를 다시 켜면 Factory I/O를 DISCONNECT → CONNECT 해야 Stop(NC) 같은 값이 다시 들어온다.

## 오늘까지 된 것
- 운전: Start / Stop(NC) / 비상정지(NC) / Reset, 운전 중 M2000
- Emitter: 측정기 4대가 모두 사용 중이면 멈춤
- 분배: Pivot Arm 4개, 빈 측정기로만 보냄 (M2101~, T201~T204)
- 측정기 4대: Start/Stop 인터록, Is Busy ↓에서 사용 중 해제
- 측정값: 전압 349~381(÷100 V), 저항 15~61 mΩ, V×R, 등급 코드 1 A / 2 B / 3 C / 5 재측정 / 9 NG
- 재측정 대상은 팔 돌 때 정하고 Produce Lids로 뚜껑을 만들어 표시

## 다른 담당이 읽는 칸
- 측정기 n 기록: D2400 + 10×(n−1) → +2 전압, +3 저항, +4 V×R, +5 등급 코드
- 다음 셀이 같은 측정기로 들어가면 덮어써짐. ②와 넘기는 방식(M2900~)은 협의 중

## 아직 남은 것
- NG 비율 조정 (불량 스톱워치 방식 검토)
- 셀 ID (비전 X1001, FIFO)
- 출구 벨트와 ② 인계, 측정 완료 비트(M24n2)
- 판정 기준 K 숫자 → D2200번대 (HMI 연동)
- T, C 대역 팀 확정 후 일괄 치환
