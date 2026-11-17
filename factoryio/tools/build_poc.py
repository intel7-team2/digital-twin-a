"""씬 파일 생성 PoC.

Factory I/O 씬(.factoryio)은 XML이라서 손으로 배치하지 않고 파일로 만들 수 있는지 확인하는 스크립트.

- 부품 블록은 기본 예제 'Separating Station'에서 검증된 좌표째로 가져옴
- 껍데기(헤더, 드라이버 설정, 썸네일)는 Factory I/O가 직접 저장한 씬에서 가져옴
- 마지막에 센서 하나를 직접 계산한 좌표에 추가해서, 예제에 없는 위치에도 놓을 수 있는지 봄

사용: python build_poc.py <예제 씬> <껍데기 씬> <출력 파일>
"""
import copy
import sys
import uuid
import xml.etree.ElementTree as ET

IO_TAGS = ("BinaryInput", "BinaryOutput", "IntInput", "IntOutput", "FloatInput", "FloatOutput")

# (부품, 예제 안 좌표) -> I/O 이름 바꾸기. None이면 I/O 없는 부품.
PICK = [
    ("Emitter", (276, 9, 173), {"Emitter 1": "Emitter"}),
    ("BeltConveyor2M", (276, 3, 169), {"Entry conveyor 1": "Entry conveyor"}),
    ("BeltConveyor6M", (276, 3, 136), {"Conveyor 1": "Main conveyor"}),
    ("BeltConveyor6M", (269, 3, 136), {"Conveyor 2": "NG conveyor"}),
    ("Pusher", (283, 6, 159), {"Pusher 1": "NG pusher", "Pusher 1 front": "NG pusher front", "Pusher 1 back": "NG pusher back"}),
    ("VisionSensor", (276, 11, 163), {"Vision sensor 1": "Vision sensor (LOT)"}),
    ("PlatformPillar", (278, 11, 164), None),
    ("PlatformPillar", (283, 5, 164), None),
    ("CapacitiveSensor", (276, 7, 161), {"Sensor 1": "At NG pusher"}),
    ("MetalCorner", (277, 6, 161), None),
    ("MetalCorner", (278, 6, 161), None),
    ("MetalCorner", (279, 6, 161), None),
    ("DiffusePhotoelectricSensor", (280, 8, 156), {"At pusher 1 exit": "Pusher exit"}),
    ("MetalCorner", (280, 7, 156), None),
    ("ChuteConveyor", (276, 4, 104), None),
    ("ChuteConveyor", (269, 4, 104), None),
    ("Remover", (276, 1, 90), {"Remover 1": "OK remover"}),
    ("Remover", (269, 1, 90), {"Remover 2": "NG remover"}),
    ("Column", (281, 8, 128), None),
    ("ElectricSwitchboard", (282, 12, 128), None),
    ("StartPushButton", (284, 12, 127), {}),
    ("StopPushButton", (284, 12, 129), {}),
    ("ResetPushButton", (284, 12, 128), {}),
    ("EmergencyStopButton", (284, 13, 128), {}),
]

# 직접 계산한 좌표에 추가하는 부품: (복사할 부품, 원래 좌표, 새 좌표, I/O 이름)
ADDED = [
    ("DiffusePhotoelectricSensor", (280, 8, 156), (280, 8, 124), {"At pusher 1 exit": "Main exit (added)"}),
    ("MetalCorner", (280, 7, 156), (280, 7, 124), None),
]


def pos_of(obj):
    p = obj.find("Proxy/Position")
    return tuple(int(float(p.get(a))) for a in "XYZ")


def find(objs, prefab, pos):
    for o in objs:
        if o.find("Proxy").get("PrefabName") == prefab and pos_of(o) == pos:
            return o
    raise SystemExit(f"예제에서 못 찾음: {prefab} {pos}")


def main(example, shell, out):
    src = ET.parse(example).getroot().findall("Object")
    root = ET.parse(shell).getroot()

    # 껍데기에서 기존 부품과 드라이버의 I/O 연결 줄을 걷어냄
    for o in root.findall("Object"):
        root.remove(o)
    for drv in root.find("Drivers"):
        for child in list(drv):
            if child.get("PointIOKey") is not None:
                drv.remove(child)
    root.find("Description").set("Data", "PoC: generated from text by build_poc.py")

    # 카메라는 예제의 현재 시점을 씀
    cam_src = ET.parse(example).getroot().find("Camera")
    cam = root.find("Camera")
    root.remove(cam)
    root.insert(1, copy.deepcopy(cam_src))

    counters = {}
    insert_at = 2
    report = []

    def add(prefab, pos, new_pos, names):
        nonlocal insert_at
        o = copy.deepcopy(find(src, prefab, pos))
        proxy = o.find("Proxy")
        proxy.set("Key", str(uuid.uuid4()))
        if new_pos:
            for a, v in zip("XYZ", new_pos):
                proxy.find("Position").set(a, str(v))
        for io in o.iter():
            if io.tag in IO_TAGS:
                io.set("Key", str(uuid.uuid4()))
                if names and io.get("Name") in names:
                    io.set("Name", names[io.get("Name")])
                n = counters.get(io.tag, 0)
                io.set("Address", str(n))
                counters[io.tag] = n + 1
                report.append((io.tag, n, io.get("Name")))
        root.insert(insert_at, o)
        insert_at += 1

    for prefab, pos, names in PICK:
        add(prefab, pos, None, names)
    for prefab, pos, new_pos, names in ADDED:
        add(prefab, pos, new_pos, names)

    ET.indent(root, space="  ")
    xml = ET.tostring(root, encoding="unicode")
    with open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(xml + "\n")

    print(f"부품 {len(PICK) + len(ADDED)}개 -> {out}")
    for tag, n, name in sorted(report):
        print(f"  {tag:13s} {n:2d}  {name}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
