# 2A HMI 메인 운전 시제품

Python 3.10 이상과 표준 Tkinter가 포함된 Windows Python에서 실행한다. 저장소 루트의 PowerShell에서 다음 명령을 실행한다.

```powershell
python -B .\docs\hmi\prototype\main.py
```

**시나리오**를 바꿔 미수집, 새 회차 정상 대기, 운전 중, 관측 지연, 통신 단절, T3 설비 이상을 비교한다. 공정 카드를 누르거나 **선택 공정** 목록으로 스테이션을 선택한다. 정상 대기의 `0`은 테스트 입력에서 확인된 집계다. 미수집·지연·단절에서는 현재 집계를 숨기고, 마지막 관측이 있으면 관측 시각과 해당 상태를 따로 표시한다.

데이터는 메모리의 고정 시나리오다. START·STOP·RESET과 비상정지 관측은 미연동으로 표시된다. 제어 버튼은 비활성화됐으며, 프로그램에는 네트워크 처리나 제어 전송 경로가 없다. 창을 닫으면 종료한다.

[v0.2 설계](../README.md)의 메인 운전 화면만 구현했다. 검사·분류, 설정·알람 화면과 실제 스냅샷 어댑터는 후속 범위다.

```powershell
python -B -m unittest discover -s docs/hmi/prototype -v
```
