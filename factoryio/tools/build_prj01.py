# prj01 v4: v3 layout turned 90 deg so the line runs along X (the long side of the floor).
# Floor measured from floor_probe.factoryio: X 0..474, Z 0..284. Layout is written in v3 coordinates
# (flow -Z) and part() maps it: new X = 236 - z, new Z = 142 + (x - 270), theta - 90. Flow is +X.
# Flow: Z1 entry + QR -> Z2 dispatch gate + 3 pushers -> Z3 stations 1..3 -> collector (merge)
#       -> Z4 QR rescan + sort NG/A/B/C -> Z5 pallet loading (4 same-grade cells per pallet) -> 2B.
# Grid: 1 cell = 0.125 m. Belt length in cells = 8*m + 1. Belts flow along Forward; pushers/sensors act along Right.
# Machining Center geometry is copied from the "Production Line" sample (theta 0, forward +Z):
#   centre (cx, 9, cz); its conveyor line is at +11 along Right; inlet 2M belt centre at -30 along Forward,
#   exit 2M belt centre at +31; entry sensor at -23, exit sensor at +23. Neighbouring centres there are 64 apart.
# Usage: python build_prj01.py <in.factoryio> <out.factoryio>   (keeps header, camera, drivers; replaces all parts)
import math, re, sys, uuid, collections

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8-sig").read()

def rot(theta):
    t = math.radians(theta)
    return (math.sin(t / 2), math.cos(t / 2),
            (round(math.sin(t)), round(math.cos(t))), (round(math.cos(t)), round(-math.sin(t))))

idx = collections.Counter()
addr = collections.Counter()
objs = []

def io(kind, name, forced=None):
    a = addr[kind]; addr[kind] += 1
    uf = "True" if forced is not None else "False"
    fv = forced if forced is not None else ("0" if kind.startswith(("Int", "Analogue")) else "False")
    return (f'<{kind} Name="{name}" Address="{a}" Key="{uuid.uuid4()}" OpenCircuit="False" '
            f'ShortCircuit="False" UseForcedValue="{uf}" ForcedValue="{fv}" />')

FINAL = [False]   # True: coordinates are already in the final (X-axis) frame
def part(prefab, x, y, z, theta, body=None, mode=0, color=None):
    if not FINAL[0]:
        x, z, theta = 236 - z, 142 + (x - 270), (theta - 90) % 360
    qy, qw, f, r = rot(theta)
    if body is None:
        ci = -1
    else:
        idx[prefab] += 1; ci = idx[prefab]
    col = f' Color="{color}"' if color is not None else ""
    objs.append(f'''  <Object Locked="False" GroupKey="00000000-0000-0000-0000-000000000000">
    <Proxy PrefabName="{prefab}" Key="{uuid.uuid4()}">
      <Position X="{x}" Y="{y}" Z="{z}" />
      <Rotation X="0" Y="{qy:.7g}" Z="0" W="{qw:.7g}" />
      <FineRotation>0</FineRotation>
      <FinePosition>0</FinePosition>
      <Forward X="{f[0]}" Y="0" Z="{f[1]}" />
      <Up X="0" Y="1" Z="0" />
      <Right X="{r[0]}" Y="0" Z="{r[1]}" />
    </Proxy>
    <ComponentIO Index="{ci}" CurrentOperatingMode="{mode}"{col} />
{body or ""}  </Object>''')

def om(desc, *groups):
    s = f'    <OperatingMode Description="{desc}">\n'
    for g, lines in groups:
        s += f'      <GroupIO Description="{g}">\n' + "".join(f"        {l}\n" for l in lines) + "      </GroupIO>\n"
    return s + "    </OperatingMode>\n"

def belt(L, x, z, theta, name):
    part(f"BeltConveyor{L}M", x, 3, z, theta,
         om("$C_BeltConveyor_OM_SingleBinary_NAME", ("Default", [io("BinaryOutput", name)])) + '    <Encoder Enabled="False" />\n')

def diffuse(x, z, theta, name):
    part("DiffusePhotoelectricSensor", x, 8, z, theta,
         om("$C_DefaultSensor_OM_Binary_NAME", ("Default", [io("BinaryInput", name)])) + '    <Sensor Range="1" />\n')

def capacitive(x, z, theta, name, rng=0.2):
    part("CapacitiveSensor", x, 7, z, theta,
         om("$C_DefaultSensor_OM_Binary_NAME", ("Default", [io("BinaryInput", name)])) + f'    <Sensor Range="{rng}" />\n')

# pusher trigger: diffuse sensor at the belt edge, 5 cells (0.625 m) before the pusher centre.
# (A capacitive sensor over the belt centre as in line_v0 never switched on in the 11/19 run.)
# The controller waits for the cell to travel those 0.625 m before it stops the belt and pushes.

def vision(x, z, name):
    part("VisionSensor", x, 16, z, 0,
         om("$C_VisionSensor_OM_DetectsAllNumerical_NAME", ("Default", [io("IntInput", name)])) + '    <Sensor Range="1" />\n', mode=10)

def stopblade(x, z, theta, name, y=6):
    part("StopBlade", x, y, z, theta, om("$C_OM_Default_NAME", ("Default", [io("BinaryOutput", name)])))

def pusher(x, z, theta, name):
    part("Pusher", x, 6, z, theta, om("$C_Pusher_OM_Monostable_NAME",
         ("Default", [io("BinaryOutput", name)]),
         ("Front", [io("BinaryInput", name + "_FWD")]),
         ("Back", [io("BinaryInput", name + "_BWD")])))

def chute(x, z, theta):
    part("ChuteConveyor", x, 4, z, theta)

ALL = ('BoxS="True" BoxM="True" BoxL="True" PalletizingBox="True" RawMaterialBlue="True" RawMaterialGreen="True" '
       'RawMaterialMetal="True" ProductBaseBlue="True" ProductBaseGreen="True" ProductBaseMetal="True" '
       'ProductLidBlue="True" ProductLidGreen="True" ProductLidMetal="True" StackableBox="True"')
# after a station the cell is a Product Base, so the packaging remover takes raw material and bases
CELLS = ALL.replace('="True"', '="False"')
for k in ("RawMaterialBlue", "RawMaterialGreen", "RawMaterialMetal", "ProductBaseBlue", "ProductBaseGreen", "ProductBaseMetal"):
    CELLS = CELLS.replace(f'{k}="False"', f'{k}="True"')

def remover(x, y, z, name, parts=ALL, forced=True):
    bases = 'Pallet="True" SquarePallet="True" StackableBox="True"' if parts == ALL else 'Pallet="False" SquarePallet="False" StackableBox="False"'
    part("Remover", x, y, z, 0,
         om("$C_Remover_OM_Default_NAME", ("Default", [io("BinaryOutput", name, "True" if forced else None)])) +
         f"    <Remover>\n      <Bases {bases} />\n      <Parts {parts} />\n    </Remover>\n")

def machining_center(cx, cz, theta, n):
    p = f"Z3_ST{n}"
    part("MachiningCenter", cx, 9, cz, theta, om("$C_OM_Default_NAME",
         ("produceLids", [io("BinaryOutput", p + "_LIDS", "False")]),   # forced False = produces bases
         ("start", [io("BinaryOutput", p + "_START")]),
         ("stop", [io("BinaryOutput", p + "_STOP")]),
         ("reset", [io("BinaryOutput", p + "_RESET")]),
         ("isBusy", [io("BinaryInput", p + "_BUSY")]),
         ("hasError", [io("BinaryInput", p + "_ERROR")]),
         ("door", [io("BinaryInput", p + "_OPEN")]),
         ("progress", [io("IntInput", p + "_PROGRESS")])))

MX = 270                  # whole line axis, flow -Z
DOWN, LEFT, RIGHT = 180, 270, 90
# Station lanes run parallel to the main line: lane 2 = main axis, lane 1 = +X side, lane 3 = -X side.
# Lane spacing 56 (7 m): cross belts are exactly 4M+2M long. Machining Center sits +11 X beside its lane.
# Station + fence footprint measured on the 11/19 top-view screenshot: about lane-24 .. lane+20 cells (estimate),
# so 56 leaves ~12 cells (1.5 m) between neighbouring fences. (Was 72 = 9 m; the user found the gap too wide.)
LX1, LX2, LX3 = MX + 56, MX, MX - 56

# ---------- Z1 entry + QR (unchanged) ----------
belt(4, MX, 200, DOWN, "Z1_BELT")                                  # Z 183.5..216.5
part("Emitter", MX, 9, 212, 0,
     om("$C_Emitter_OM_Default_NAME", ("Default", [io("BinaryOutput", "Z1_EMITTER")])) +
     """    <Emitter MinTimeToEmit="2" MaxTimeToEmit="3" UpTo="0" RandomPartPosition="False" RandomPartOrientation="False">
      <Bases />
      <Parts RawMaterialBlue="True" RawMaterialGreen="True" RawMaterialMetal="True" />
    </Emitter>
""")
diffuse(MX + 4, 205, 180, "Z1_IN_SENS")
vision(MX, 194, "Z1_LOT_VISION")

# ---------- Z2 dispatch: gate, then push to lane 1 (+X) or lane 3 (-X); lane 2 = go straight ----------
stopblade(MX, 184, DOWN, "Z2_GATE")
diffuse(MX + 4, 186, 180, "Z2_AT_GATE")
belt(4, MX, 167, DOWN, "Z2_BELT")                                  # Z 150.5..183.5
P1, P3 = 176, 158
diffuse(MX + 4, P1 + 5, 180, "Z2_AT_PUSH_1")
pusher(MX - 7, P1, 0, "Z2_PUSH_1")                                 # pushes +X
belt(4, MX + 20, P1, RIGHT, "Z2_TO_ST1_BELT_1")                    # X 273.5..306.5
belt(2, MX + 45, P1, RIGHT, "Z2_TO_ST1_BELT_2")                    # X 306.5..323.5 (2.5 before lane 1)
diffuse(MX - 4, P3 + 5, 0, "Z2_AT_PUSH_3")
pusher(MX + 7, P3, DOWN, "Z2_PUSH_3")                              # pushes -X
belt(4, MX - 20, P3, LEFT, "Z2_TO_ST3_BELT_1")                     # X 233.5..266.5
belt(2, MX - 45, P3, LEFT, "Z2_TO_ST3_BELT_2")                     # X 216.5..233.5 (2.5 before lane 3)

# ---------- Z3 stations (flow -Z). theta 180: Right = -X, so MC centre X = lane + 11 ----------
def station(n, lx, cz, feeder_z=None, ext=None):
    if feeder_z is not None:
        belt(2, lx, feeder_z, DOWN, f"Z3_ST{n}_FEED_BELT")
    belt(2, lx, cz + 30, DOWN, f"Z3_ST{n}_IN_BELT")
    diffuse(lx - 4, cz + 23, 0, f"Z3_ST{n}_IN")                     # cell waiting at the station entry
    machining_center(lx + 11, cz, DOWN, n)
    belt(2, lx, cz - 31, DOWN, f"Z3_ST{n}_OUT_BELT")                # cz-39.5 .. cz-22.5
    end = cz - 39.5   # x.5; positions below are whole cells
    if ext:
        belt(4, lx, int(end - 16.5), DOWN, f"Z3_ST{n}_EXT_BELT")
        end -= 33
    diffuse(lx - 4, int(end + 4.5), 0, f"Z3_ST{n}_OUT")                  # finished cell at the end of the station
    return end

station(1, LX1, 130, feeder_z=177, ext=True)                       # feed 168.5..185.5, MC z 130, end 57.5
station(2, LX2, 112)                                               # straight on from Z2_BELT, end 72.5
station(3, LX3, 112, feeder_z=159, ext=True)                       # feed 150.5..167.5, MC z 112, end 39.5
# ST1 / ST3 cells arrive off-centre after the side transfer and catch on the entry-bay frame (11/19 run).
# Guide pair as in the Pick & Place sample (Aligner2, 3 cells either side of the belt centre), final coordinates.
FINAL[0] = True
for zc in (142 + 56, 142 - 56):                                    # ST1 / ST3 entry belt lines (final Z)
    part("Aligner2", 74, 8, zc - 3, 90, color=7)
    part("Aligner2", 74, 8, zc + 3, 90, color=7)
# Wheel Aligner at the 90-degree corner (side belt -> feed belt), placed like the Production Line sample:
# 2.5 cells before the side belt's end, 4~5 cells to the side the item turns to, facing the side belt's flow.
# (11/19 17:0x run: cells came onto the feed belt twisted and did not fit the entry bay.)
part("WheelAligner", 65, 8, 193, 0, color=7)      # ST1: side belt X 60 ends at Z 195.5, flows +Z, turns to +X
part("WheelAligner", 82, 8, 91, 180, color=7)     # ST3: side belt X 78 ends at Z 88.5, flows -Z, turns to +X
FINAL[0] = False

# merge: lane 2 runs straight into the collector, lanes 1 and 3 come in from the sides 18 apart
belt(6, MX, 48, DOWN, "Z3_COLLECT_BELT")                           # Z 23.5..72.5
M1, M3 = 55, 37                                                    # 2.5 below the lane 1 / 3 belt ends
belt(6, MX + 44, M1, LEFT, "Z3_FROM_ST1_BELT_1")                   # X 289.5..338.5
belt(2, MX + 11, M1, LEFT, "Z3_FROM_ST1_BELT_2")                   # X 272.5..289.5
diffuse(MX - 4, M1 + 7, 0, "Z3_MERGE_1")                           # collector occupied just upstream of merge 1
belt(6, MX - 44, M3, RIGHT, "Z3_FROM_ST3_BELT_1")                  # X 201.5..250.5
belt(2, MX - 11, M3, RIGHT, "Z3_FROM_ST3_BELT_2")                  # X 250.5..267.5
diffuse(MX + 4, M3 + 7, 180, "Z3_MERGE_3")                         # collector occupied just upstream of merge 3

# ---------- Z4 QR rescan + sort NG / A / B / C (v2 pattern, on the main axis, 13 lower) ----------
SX, O = MX, -13
belt(6, SX, 12 + O, DOWN, "Z4_BELT_1")                             # Z -25.5..23.5
vision(SX, 20 + O, "Z4_QR_RESCAN")
diffuse(SX - 4, 5 + O, 0, "Z4_AT_PUSH_NG")
pusher(SX + 7, 0 + O, DOWN, "Z4_PUSH_NG")
belt(2, SX - 12, 0 + O, LEFT, "Z4_NG_BELT")
capacitive(SX - 8, 0 + O, 0, "Z4_NG_CONFIRM")
chute(SX - 28, 0 + O, 180)
remover(SX - 42, 1, 0 + O, "Z4_NG_REMOVER")

belt(6, SX, -37 + O, DOWN, "Z4_BELT_2")
LX = SX - 20
for name, z in (("A", -19), ("B", -35), ("C", -51)):
    z += O
    diffuse(SX - 4, z + 5, 0, f"Z4_AT_PUSH_{name}")
    pusher(SX + 7, z, DOWN, f"Z4_PUSH_{name}")
    belt(4, LX, z, LEFT, f"Z4_LANE_{name}")
    diffuse(SX - 8, z + 4, 90, f"Z4_LANE_{name}_FULL")
    diffuse(LX - 14, z + 4, 90, f"Z4_LANE_{name}_HEAD")
    stopblade(LX - 16, z, LEFT, f"Z4_LANE_{name}_STOP")
chute(SX, -69 + O, 90)
remover(SX, 1, -83 + O, "END_REMOVER")

# ---------- Z5 pallet loading -> 2B ----------
# A batch of 4 same-grade cells comes from one A/B/C lane. A Pick & Place (XYZ gantry) puts the 4 Product Bases
# on one pallet; the loaded pallet rolls on and the last remover takes pallet + cells together (= handed to 2B).
# Station geometry is the "Pick & Place XYZ" sample moved by (+69, -38) cells; written in final coordinates.
X5 = LX - 20
belt(6, X5, -37 + O, DOWN, "Z5_COLLECT_BELT")                      # final X 261.5..310.5, Z 102, flow +X
diffuse(X5 - 4, -63 + O, 0, "Z5_CELL_COUNT")                       # final (312, 98)

FINAL[0] = True
def retro(x, y, z, theta, name, rng, mx, mz):
    part("RetroreflectivePhotoelectricSensor", x, y, z, theta,
         om("$C_DefaultSensor_OM_Binary_NAME", ("Default", [io("BinaryInput", name)])) + f'    <Sensor Range="{rng}" />\n')
    part("RetroreflectiveMirror", mx, y, mz, theta)

def roller(L, x, z, theta, name):
    part(f"RollerConveyor{L}M", x, 2, z, theta,
         om("$C_RollerConveyor_OM_SingleBinary_NAME", ("Default", [io("BinaryOutput", name)])) + '    <Encoder Enabled="False" />\n')

belt(4, 327, 102, 90, "Z5_FEED_BELT")                              # X 310.5..343.5 -> pick point at the end
part("Aligner2", 333, 8, 99, 90, color=7)
part("Aligner2", 333, 8, 105, 90, color=7)
retro(341, 8, 98, 270, "Z5_AT_PICK", 1.0, 341, 106)                 # cell at the pick point
part("PickNPlace", 345, 11, 102, 180, om("$C_PickNPlace_OM_Analogue_NAME",
     ("beamVoltage", [io("AnalogueOutput", "Z5_PNP_SP_Y")]),
     ("pickerVoltage", [io("AnalogueOutput", "Z5_PNP_SP_Z")]),
     ("headVoltage", [io("AnalogueOutput", "Z5_PNP_SP_X")]),
     ("beamDistance", [io("AnalogueInput", "Z5_PNP_Y")]),
     ("pickerDistance", [io("AnalogueInput", "Z5_PNP_Z")]),
     ("headDistance", [io("AnalogueInput", "Z5_PNP_X")]),
     ("boxDetected", [io("BinaryInput", "Z5_PNP_DETECTED")]),
     ("gripperLimit", [io("BinaryInput", "Z5_PNP_C_LIMIT")]),
     ("turnGripper", [io("BinaryOutput", "Z5_PNP_C_TURN")]),
     ("grab", [io("BinaryOutput", "Z5_PNP_GRAB")])), mode=1)
part("Emitter", 348, 6, 80, 0,
     om("$C_Emitter_OM_Default_NAME", ("Default", [io("BinaryOutput", "Z5_PALLET_EMIT")])) +
     """    <Emitter MinTimeToEmit="0.1" MaxTimeToEmit="0.1" UpTo="0" RandomPartPosition="False" RandomPartOrientation="False">
      <Bases Pallet="True" />
      <Parts />
    </Emitter>
""")
roller(6, 348, 99, 0, "Z5_PALLET_ROLLER")                          # Z 74.5..123.5, flow +Z
retro(344, 5, 106, 0, "Z5_PALLET_AT_PLACE", 1.184086, 352, 106)     # pallet in the loading position
roller(4, 348, 140, 0, "Z5_EXIT_ROLLER")                           # Z 123.5..156.5
remover(348, 6, 151, "Z5_TO_2B")                                   # pallet + 4 cells vanish here = handed to 2B
FINAL[0] = False

# ---------- operator panel (unchanged) ----------
part("ElectricSwitchboard", 288, 12, 200, 0)
def button(prefab, x, y, z, name, lamp=True):
    lines = [io("BinaryInput", name)] + ([io("BinaryOutput", name + "_LAMP")] if lamp else [])
    desc = "$C_OM_Default_NAME" if prefab == "EmergencyStopButton" else "$C_PushButton_OM_MomentaryAction_NAME"
    part(prefab, x, y, z, 0, om(desc, ("Default", lines)), color=None if prefab == "EmergencyStopButton" else 0)
button("EmergencyStopButton", 290, 13, 199, "PB_ESTOP", lamp=False)
button("StartPushButton", 290, 12, 199, "PB_START")
button("StopPushButton", 290, 12, 200, "PB_STOP")
button("ResetPushButton", 290, 12, 201, "PB_RESET")
part("Selector", 290, 13, 201, 0, om("$C_Selector_Type1_NAME", ("Default", [io("BinaryInput", "SEL_ASSY_READY")])))
for name, y, z, c in (("LAMP_GREEN_RUN", 11, 199, 2), ("LAMP_YELLOW_HOLD", 11, 200, 1), ("LAMP_RED_ALARM", 11, 201, 0)):
    part("LightIndicator", 290, y, z, 0, om("$C_OM_Default_NAME", ("Default", [io("BinaryOutput", name)])), color=c)

# ---------- write ----------
text = re.sub(r"\n  <Object .*?\n  </Object>", "", text, flags=re.S)
i = text.index("</Camera>") + len("</Camera>")
text = text[:i] + "\n" + "\n".join(objs) + text[i:]
# ---------- Modbus TCP Client mapping (same scheme as the team's line_v0 / softplc.py) ----------
# bit inputs (sensors) -> coils n, then Run/Pause/Reset; bit outputs -> discrete inputs n;
# numeric inputs (vision ints, then Pick & Place X/Y/Z positions) -> holding registers n;
# numeric outputs (Pick & Place X/Y/Z set points) -> input registers n. ScaleFactor 100: register = value x 100.
tags = re.findall(r'<(BinaryInput|BinaryOutput|IntInput|AnalogueInput|AnalogueOutput) Name="[^"]+" Address="(\d+)" Key="([^"]+)"', text)
cnt = collections.Counter(k for k, _, _ in tags)
nin, nout, nint = cnt["BinaryInput"], cnt["BinaryOutput"], cnt["IntInput"]
drv = re.search(r'<Drivers [^>]*>', text).group(0)
keys = dict(re.findall(r'(RunInputKey|PauseInputKey|ResetInputKey)="([^"]+)"', drv))
lines = [f'      <PointIOCount BitInputCount="{nin + 3}" BitOutputCount="{nout}" FloatInputCount="0" FloatOutputCount="0" '
         f'IntInputCount="0" IntOutputCount="0" NumericInputCount="{nint + cnt["AnalogueInput"]}" '
         f'NumericOutputCount="{cnt["AnalogueOutput"]}" />',
         '      <PointIOOffset BitInputOffset="0" BitOutputOffset="0" FloatInputOffset="0" FloatOutputOffset="0" '
         'IntInputOffset="0" IntOutputOffset="0" NumericInputOffset="0" NumericOutputOffset="0" />']
slot = {"BinaryInput": ("BitInput", 0), "BinaryOutput": ("BitOutput", 0), "IntInput": ("NumericInput", 0),
        "AnalogueInput": ("NumericInput", nint), "AnalogueOutput": ("NumericOutput", 0)}
lines += [f'      <{slot[k][0]}{int(a) + slot[k][1]} PointIOKey="{key}" />' for k, a, key in tags]
lines += [f'      <BitInput{nin + j} PointIOKey="{keys[k]}" />' for j, k in enumerate(("RunInputKey", "PauseInputKey", "ResetInputKey"))]
lines.append('      <Properties ReadCoils="False" ReadHoldingRegisters="False" ScaleFactor="100" />')
text = re.sub(r"<ModbusTCPClient>.*?</ModbusTCPClient>",
              lambda m: "<ModbusTCPClient>\n" + "\n".join(lines) + "\n    </ModbusTCPClient>", text, count=1, flags=re.S)
text = text.replace(drv, re.sub(r'CurrentDriver="\d+"', 'CurrentDriver="64"', drv))
text = text.replace("\r\n", "\n").replace("\n", "\r\n")
open(dst, "w", encoding="utf-8-sig", newline="").write(text)
print("objects:", len(objs), dict(idx))
print("addresses:", dict(addr))
