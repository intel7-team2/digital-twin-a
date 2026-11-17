"""전공정 라인 씬 생성 (PoC).

입고 -> 검사 위치 -> NG 배출 -> 등급 A/B/C 버퍼 레인 -> 공급 컨베이어 -> C 공급 지점

좌표 단위는 Factory I/O 격자 한 칸(0.125 m). 메인 흐름은 -Z 방향, 레인은 -X 방향.
부품 블록은 기본 예제 씬에서 복사하고 위치와 방향만 바꾼다.

사용: python build_line.py <Factory I/O Scenes 폴더> <껍데기 씬> <출력 씬> <태그맵 md>
"""
import copy
import math
import os
import sys
import uuid
import xml.etree.ElementTree as ET

IO_TAGS = ("BinaryInput", "BinaryOutput", "IntInput", "IntOutput", "FloatInput", "FloatOutput")

# 부품 원본: 이름 -> (예제 씬, 부품, 예제 안 좌표)
LIB = {
    "emitter": ("Separating Station", "Emitter", (276, 9, 173)),
    "belt2": ("Separating Station", "BeltConveyor2M", (276, 3, 169)),      # 흐름 -Z
    "belt6": ("Separating Station", "BeltConveyor6M", (276, 3, 136)),      # 흐름 -Z
    "belt4": ("Production Line", "BeltConveyor4M", (276, 3, 188)),         # 방향은 배치할 때 yaw로 지정
    "pusher": ("Separating Station", "Pusher", (283, 6, 159)),             # -X로 밂
    "cap": ("Separating Station", "CapacitiveSensor", (276, 7, 161)),      # 벨트 위에서 아래를 봄
    "bracket1": ("Separating Station", "MetalCorner", (277, 6, 161)),
    "bracket2": ("Separating Station", "MetalCorner", (278, 6, 161)),
    "bracket3": ("Separating Station", "MetalCorner", (279, 6, 161)),
    "diffuse": ("Separating Station", "DiffusePhotoelectricSensor", (280, 8, 156)),  # +X쪽에서 -X를 봄
    "corner": ("Separating Station", "MetalCorner", (280, 7, 156)),
    "vision": ("Separating Station", "VisionSensor", (276, 11, 163)),
    "pillar_a": ("Separating Station", "PlatformPillar", (278, 11, 164)),
    "pillar_b": ("Separating Station", "PlatformPillar", (283, 5, 164)),
    "blade": ("Buffer Station", "StopBlade", (267, 6, 142)),               # 흐름 +Z (yaw 0)
    "chute": ("Separating Station", "ChuteConveyor", (276, 4, 104)),       # 흐름 -Z (yaw 90)
    "remover": ("Separating Station", "Remover", (276, 1, 90)),
    "column": ("Separating Station", "Column", (281, 8, 128)),
    "board": ("Separating Station", "ElectricSwitchboard", (282, 12, 128)),
    "start": ("Separating Station", "StartPushButton", (284, 12, 127)),
    "stop": ("Separating Station", "StopPushButton", (284, 12, 129)),
    "reset": ("Separating Station", "ResetPushButton", (284, 12, 128)),
    "estop": ("Separating Station", "EmergencyStopButton", (284, 13, 128)),
}

MAIN_X = 276
LANES = [("NG", 150), ("A", 140), ("B", 130), ("C", 120)]   # (이름, Z)
SUPPLY_X = 235

# (부품, 새 좌표, yaw 또는 None(원본 방향 유지), I/O 이름들 또는 None)
PLAN = []


def put(part, pos, yaw=None, names=None, **attrs):
    PLAN.append((part, pos, yaw, names, attrs))


# ---- 입고
put("emitter", (MAIN_X, 9, 173), names=["Emit cell"], forced=False)
put("belt2", (MAIN_X, 3, 169), names=["Entry conveyor"])
put("diffuse", (280, 8, 172), names=["Cell arrived"])
put("corner", (280, 7, 172))
put("vision", (MAIN_X, 11, 163), names=["LOT vision"])
put("pillar_a", (278, 11, 164))
put("pillar_b", (283, 5, 164))

# ---- 메인 컨베이어, 검사 위치
put("belt6", (MAIN_X, 3, 136), names=["Main conveyor"])
put("diffuse", (280, 8, 162), names=["At inspection"])
put("corner", (280, 7, 162))
# Stop blades occupy the joint between belts, as in the Buffer Station example.
put("blade", (MAIN_X, 6, 161), yaw=180, names=["Inspection stop"])

# ---- 푸셔 4개 (NG, A, B, C)와 그 앞 센서
for name, z in LANES:
    put("pusher", (283, 6, z), names=[f"Pusher {name}", f"Pusher {name} front", f"Pusher {name} back"])
    put("cap", (MAIN_X, 7, z + 2), names=[f"At pusher {name}"])
    for i, x in enumerate((277, 278, 279), 1):
        put(f"bracket{i}", (x, 6, z + 2))

# ---- NG 배출
put("chute", (264, 4, 150), yaw=180)
put("remover", (250, 1, 150), names=["NG remover"])

# ---- 등급 버퍼 레인 (흐름 -X)
for name, z in LANES[1:]:
    put("belt4", (256, 3, z), yaw=-90, names=[f"Lane {name} conveyor"])
    put("blade", (240, 6, z), yaw=-90, names=[f"Lane {name} stop"])

# ---- 공급 컨베이어, C 공급 지점
put("belt6", (SUPPLY_X, 3, 124), names=["Supply conveyor"])
put("diffuse", (SUPPLY_X + 4, 8, 104), names=["Set at exit"])
put("corner", (SUPPLY_X + 4, 7, 104))
put("chute", (SUPPLY_X, 4, 92))
put("remover", (SUPPLY_X, 1, 78), names=["Supply remover (to C)"])

# ---- 조작반 (예제 위치에서 Z만 옮김)
DZ = 55
for part in ("column", "board"):
    x, y, z = LIB[part][2]
    put(part, (x, y, z + DZ))
put("start", (284, 12, 127 + DZ), names=["Start", "Start light"])
put("stop", (284, 12, 129 + DZ), names=["Stop", "Stop light"])
put("reset", (284, 12, 128 + DZ), names=["Reset", "Reset light"])
put("estop", (284, 13, 128 + DZ), names=["Emergency stop"])


def fmt(v):
    v = round(v, 7)
    return "0" if v == 0 else repr(v) if v != int(v) else str(int(v))


def set_yaw(proxy, deg):
    t = math.radians(deg)
    s, c = math.sin(t), math.cos(t)
    vals = {
        "Rotation": dict(X=0, Y=math.sin(t / 2), Z=0, W=math.cos(t / 2)),
        "Forward": dict(X=s, Y=0, Z=c),
        "Up": dict(X=0, Y=1, Z=0),
        "Right": dict(X=c, Y=0, Z=-s),
    }
    for tag, d in vals.items():
        e = proxy.find(tag)
        for k, v in d.items():
            e.set(k, fmt(v))


def main(scenes_dir, shell, out, tagmap):
    cache = {}

    def source(part):
        scene, prefab, pos = LIB[part]
        if scene not in cache:
            cache[scene] = ET.parse(os.path.join(scenes_dir, scene + ".factoryio")).getroot().findall("Object")
        for o in cache[scene]:
            p = o.find("Proxy")
            xyz = tuple(int(float(p.find("Position").get(a))) for a in "XYZ")
            if p.get("PrefabName") == prefab and xyz == pos:
                return o
        raise SystemExit(f"예제에서 못 찾음: {part}")

    root = ET.parse(shell).getroot()
    for o in root.findall("Object"):
        root.remove(o)
    for drv in root.find("Drivers"):
        for child in list(drv):
            if child.get("PointIOKey") is not None:
                drv.remove(child)
    root.find("Description").set("Data", "Pre-process line PoC: receiving, inspection, NG reject, grade lanes, 4-cell supply")

    # 카메라: 라인 전체가 보이는 위치 (단위 m = 격자 / 8)
    cam = root.find("Camera")
    for cp in cam.findall("CameraPosition"):
        d = cp.find("Data")
        for k, v in dict(X=39.5, Y=11.0, Z=24.5).items():
            d.find("CameraPosition").set(k, str(v))
        for k, v in dict(X=32.0, Y=0.6, Z=17.0).items():
            d.find("PivotPosition").set(k, str(v))

    counters, rows = {}, []
    idx = 2
    for part, pos, yaw, names, attrs in PLAN:
        o = copy.deepcopy(source(part))
        proxy = o.find("Proxy")
        proxy.set("Key", str(uuid.uuid4()))
        for a, v in zip("XYZ", pos):
            proxy.find("Position").set(a, str(v))
        if yaw is not None:
            set_yaw(proxy, yaw)
        ios = [e for e in o.iter() if e.tag in IO_TAGS]
        if names is not None and len(names) != len(ios):
            raise SystemExit(f"{part}: I/O {len(ios)}개인데 이름 {len(names)}개")
        for i, io in enumerate(ios):
            io.set("Key", str(uuid.uuid4()))
            if names:
                io.set("Name", names[i])
            n = counters.get(io.tag, 0)
            counters[io.tag] = n + 1
            io.set("Address", str(n))
            if "forced" in attrs:
                io.set("UseForcedValue", str(attrs["forced"]))
                io.set("ForcedValue", "False")
            rows.append((io.tag, n, io.get("Name"), io.get("UseForcedValue") == "True"))
        em = o.find("Emitter")
        if em is not None:
            em.set("MinTimeToEmit", "2")
            em.set("MaxTimeToEmit", "2")
            parts = em.find("Parts")
            parts.attrib.clear()
            parts.attrib.update(RawMaterialBlue="True", RawMaterialGreen="True", RawMaterialMetal="True")
        root.insert(idx, o)
        idx += 1

    # Modbus client: sensors -> coils/holding registers; actuators <- discrete inputs.
    # Mapping belongs to the scene, so opening it does not require dragging tags.
    drivers = root.find("Drivers")
    drivers.set("CurrentDriver", "64")
    mb = drivers.find("ModbusTCPClient")
    for child in list(mb):
        mb.remove(child)
    ET.SubElement(mb, "PointIOCount", BitInputCount="22", BitOutputCount="20",
                  FloatInputCount="0", FloatOutputCount="0", IntInputCount="0",
                  IntOutputCount="0", NumericInputCount="1", NumericOutputCount="0")
    ET.SubElement(mb, "PointIOOffset", **{k: "0" for k in (
        "BitInputOffset", "BitOutputOffset", "FloatInputOffset", "FloatOutputOffset",
        "IntInputOffset", "IntOutputOffset", "NumericInputOffset", "NumericOutputOffset")})
    for tag, prefix in (("BinaryInput", "BitInput"), ("BinaryOutput", "BitOutput"),
                        ("IntInput", "NumericInput")):
        for io in root.iter(tag):
            ET.SubElement(mb, prefix + io.get("Address"), PointIOKey=io.get("Key"))
    for n, key in enumerate(("RunInputKey", "PauseInputKey", "ResetInputKey"), 19):
        ET.SubElement(mb, f"BitInput{n}", PointIOKey=drivers.get(key))
    ET.SubElement(mb, "Properties", ReadCoils="False", ReadHoldingRegisters="False", ScaleFactor="1")

    ET.indent(root, space="  ")
    with open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(ET.tostring(root, encoding="unicode") + "\n")

    # ---- 태그맵
    dev = {"BinaryInput": ("M", 1000), "BinaryOutput": ("M", 1100), "IntInput": ("D", 1000)}
    title = {"BinaryInput": "Factory I/O 센서 -> PLC (비트 입력)", "BinaryOutput": "PLC -> Factory I/O 액추에이터 (비트 출력)",
             "IntInput": "Factory I/O -> PLC (워드 입력)"}
    lines = ["# 태그맵 (line_v0 씬)", "",
             "`factoryio/tools/build_line.py`가 씬과 같이 만드는 파일. 손으로 고치지 말고 스크립트를 고친 뒤 다시 생성.", "",
             "PLC 디바이스는 제안값. 실물 C의 X/Y와 안 겹치게 내부 릴레이를 씀.", ""]
    for tag in ("BinaryInput", "BinaryOutput", "IntInput"):
        lines += [f"## {title[tag]}", "", "| Factory I/O 주소 | 이름 | PLC 디바이스 | 비고 |", "|---|---|---|---|"]
        for t, n, name, forced in rows:
            if t == tag:
                p, base = dev[tag]
                note = "씬에서 항상 ON으로 강제" if forced else ""
                lines.append(f"| {n} | {name} | {p}{base + n} | {note} |")
        lines.append("")
    with open(tagmap, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    print(f"부품 {len(PLAN)}개, I/O {len(rows)}점 -> {out}")
    for tag, n in counters.items():
        print(f"  {tag}: {n}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
