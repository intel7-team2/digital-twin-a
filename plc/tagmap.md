# 태그맵 (line_v0 씬)

`factoryio/tools/build_line.py`가 씬과 같이 만드는 파일. 손으로 고치지 말고 스크립트를 고친 뒤 다시 생성.

PLC 디바이스는 제안값. 실물 C의 X/Y와 안 겹치게 내부 릴레이를 씀.

## Factory I/O 센서 -> PLC (비트 입력)

| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |
|---|---|---|---|
| 0 | Cell arrived | M1000 |  |
| 1 | At inspection | M1001 |  |
| 2 | Pusher NG front | M1002 |  |
| 3 | Pusher NG back | M1003 |  |
| 4 | At pusher NG | M1004 |  |
| 5 | Pusher A front | M1005 |  |
| 6 | Pusher A back | M1006 |  |
| 7 | At pusher A | M1007 |  |
| 8 | Pusher B front | M1008 |  |
| 9 | Pusher B back | M1009 |  |
| 10 | At pusher B | M1010 |  |
| 11 | Pusher C front | M1011 |  |
| 12 | Pusher C back | M1012 |  |
| 13 | At pusher C | M1013 |  |
| 14 | Set at exit | M1014 |  |
| 15 | Start | M1015 |  |
| 16 | Stop | M1016 |  |
| 17 | Reset | M1017 |  |
| 18 | Emergency stop | M1018 |  |

## PLC -> Factory I/O 액추에이터 (비트 출력)

| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |
|---|---|---|---|
| 0 | Emit cell | M1100 |  |
| 1 | Entry conveyor | M1101 |  |
| 2 | Main conveyor | M1102 |  |
| 3 | Inspection stop | M1103 |  |
| 4 | Pusher NG | M1104 |  |
| 5 | Pusher A | M1105 |  |
| 6 | Pusher B | M1106 |  |
| 7 | Pusher C | M1107 |  |
| 8 | NG remover | M1108 | 씬에서 항상 ON으로 강제 |
| 9 | Lane A conveyor | M1109 |  |
| 10 | Lane A stop | M1110 |  |
| 11 | Lane B conveyor | M1111 |  |
| 12 | Lane B stop | M1112 |  |
| 13 | Lane C conveyor | M1113 |  |
| 14 | Lane C stop | M1114 |  |
| 15 | Supply conveyor | M1115 |  |
| 16 | Supply remover (to C) | M1116 | 씬에서 항상 ON으로 강제 |
| 17 | Start light | M1117 |  |
| 18 | Stop light | M1118 |  |
| 19 | Reset light | M1119 |  |

## Factory I/O -> PLC (워드 입력)

| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |
|---|---|---|---|
| 0 | LOT vision | D1000 |  |
