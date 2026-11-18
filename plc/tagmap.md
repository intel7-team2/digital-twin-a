# 태그맵 (line_v0 씬)

`factoryio/tools/build_line.py`가 씬과 같이 만드는 파일. 손으로 고치지 말고 스크립트를 고친 뒤 다시 생성.

PLC 디바이스는 2A 대역(2000~2999) 안. 실물 C의 X/Y와 안 겹치게 내부 릴레이를 씀. 전체 배정은 docs/interface.md.

## Factory I/O 센서 -> PLC (비트 입력)

| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |
|---|---|---|---|
| 0 | Cell arrived | M2000 |  |
| 1 | At inspection | M2001 |  |
| 2 | Pusher NG front | M2002 |  |
| 3 | Pusher NG back | M2003 |  |
| 4 | At pusher NG | M2004 |  |
| 5 | Pusher A front | M2005 |  |
| 6 | Pusher A back | M2006 |  |
| 7 | At pusher A | M2007 |  |
| 8 | Pusher B front | M2008 |  |
| 9 | Pusher B back | M2009 |  |
| 10 | At pusher B | M2010 |  |
| 11 | Pusher C front | M2011 |  |
| 12 | Pusher C back | M2012 |  |
| 13 | At pusher C | M2013 |  |
| 14 | Set at exit | M2014 |  |
| 15 | Start | M2015 |  |
| 16 | Stop | M2016 |  |
| 17 | Reset | M2017 |  |
| 18 | Emergency stop | M2018 |  |

## PLC -> Factory I/O 액추에이터 (비트 출력)

| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |
|---|---|---|---|
| 0 | Emit cell | M2100 |  |
| 1 | Entry conveyor | M2101 |  |
| 2 | Main conveyor | M2102 |  |
| 3 | Inspection stop | M2103 |  |
| 4 | Pusher NG | M2104 |  |
| 5 | Pusher A | M2105 |  |
| 6 | Pusher B | M2106 |  |
| 7 | Pusher C | M2107 |  |
| 8 | NG remover | M2108 | 씬에서 항상 ON으로 강제 |
| 9 | Lane A conveyor | M2109 |  |
| 10 | Lane A stop | M2110 |  |
| 11 | Lane B conveyor | M2111 |  |
| 12 | Lane B stop | M2112 |  |
| 13 | Lane C conveyor | M2113 |  |
| 14 | Lane C stop | M2114 |  |
| 15 | Supply conveyor | M2115 |  |
| 16 | Supply remover (to C) | M2116 | 씬에서 항상 ON으로 강제 |
| 17 | Start light | M2117 |  |
| 18 | Stop light | M2118 |  |
| 19 | Reset light | M2119 |  |

## Factory I/O -> PLC (워드 입력)

| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |
|---|---|---|---|
| 0 | LOT vision | D2000 |  |
