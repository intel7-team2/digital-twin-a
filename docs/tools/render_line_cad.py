"""Build and render a deterministic, simplified 3D equipment layout.

Positions and belt lengths follow factoryio/tools/build_line.py. Part profiles,
supports and heights are schematic, not fabrication dimensions. No image model
or existing image is used. Outputs a PNG view and an editable OBJ/MTL mesh.
Requires Pillow only.
"""
from pathlib import Path
import importlib.util
import math
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/assets'
spec = importlib.util.spec_from_file_location('line_layout', ROOT / 'factoryio/tools/build_line.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)

COLORS = {'steel': (192, 203, 212), 'edge': (123, 143, 161),
          'belt': (67, 79, 91), 'blue': (39, 94, 151),
          'cell': (215, 222, 228), 'black': (47, 57, 68)}
vertices, faces = [], []


def mesh(points, polygons, material):
    base = len(vertices)
    vertices.extend(points)
    faces.extend((tuple(base+i for i in polygon), material) for polygon in polygons)


def block(center, size, material='steel', outline=True):
    if not outline:
        COLORS.setdefault(material+'_flat', COLORS[material])
        material += '_flat'
    x, y, z = center
    a, b, c = (v/2 for v in size)
    points = [(x+dx*a, y+dy*b, z+dz*c)
              for dz in (-1, 1) for dy in (-1, 1) for dx in (-1, 1)]
    mesh(points, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
                  (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)], material)


def cylinder(center, radius, length, material='steel', axis='z', sides=20):
    points = []
    for end in (-.5, .5):
        for i in range(sides):
            angle = 2*math.pi*i/sides
            p = [radius*math.cos(angle), radius*math.sin(angle), end*length]
            if axis == 'y': p = [p[0], p[2], p[1]]
            if axis == 'x': p = [p[2], p[0], p[1]]
            points.append(tuple(a+b for a, b in zip(center, p)))
    polygons = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
    polygons += [(i, (i+1) % sides, (i+1) % sides+sides, i+sides) for i in range(sides)]
    mesh(points, polygons, material)


def point(pos):
    # Factory I/O grid: X/Z plane, 0.125 m pitch; Z is height in this mesh.
    x, _, z = pos
    return (173-z)/8, (276-x)/8


def conveyor(x, y, length, axis='x'):
    along_x = axis == 'x'
    size = lambda a, b, c: (a, b, c) if along_x else (b, a, c)
    move = lambda a, b, z: (x+a, y+b, z) if along_x else (x+b, y+a, z)
    # Segment long deck faces so the depth-sorted illustration correctly
    # occludes cells, underside braces and hardware at every belt position.
    segments = math.ceil(length/.2)
    step = length/segments
    for i in range(segments):
        distance = -length/2+(i+.5)*step
        block(move(distance, 0, .79), size(step, .76, .17), outline=False)
        block(move(distance, 0, .895), size(step, .63, .045), 'belt')
        for side in (-1, 1):
            block(move(distance, side*.39, .88), size(step, .055, .16), 'edge', outline=False)
    for distance in (-length/2+.18, length/2-.18):
        cylinder(move(distance, 0, .86), .085, .7, 'steel', 'y' if along_x else 'x')
        for side in (-1, 1):
            block(move(distance, side*.31, .36), (.065, .065, .72), 'edge')
            block(move(distance, side*.31, .035), (.17, .17, .07), 'black')
        block(move(distance, 0, .22), size(.045, .65, .045), 'steel')
    for d in range(int(length/.4)):
        block(move(-length/2+.25+d*.4, 0, .65), size(.025, .68, .025), 'edge')


def cell(x, y):
    block((x, y, .945), (.17, .17, .045), 'blue')
    cylinder((x, y, 1.09), .062, .25, 'cell', sides=24)
    cylinder((x, y, 1.222), .025, .018, 'edge', sides=16)


for part, pos, yaw, names, attrs in layout.PLAN:
    x, y = point(pos)
    if part in ('belt2', 'belt4', 'belt6'):
        conveyor(x, y, int(part[-1]), 'y' if part == 'belt4' else 'x')
    elif part == 'pusher':
        block((x, y, .92), (.48, .28, .18), 'steel')
        cylinder((x, y+.22, .95), .04, .28, 'edge', 'y')
        block((x, y+.38, .98), (.43, .05, .2), 'blue')
    elif part == 'blade':
        side = yaw == -90
        block((x, y, .97), (.62, .045, .17) if side else (.045, .62, .17), 'blue')
    elif part == 'vision':
        for dy in (-.49, .49): block((x, y+dy, 1.28), (.07, .07, 1.05), 'edge')
        block((x, y, 1.83), (.12, 1.08, .12), 'steel')
        block((x, y, 1.69), (.24, .21, .2), 'black')
        cylinder((x, y, 1.53), .07, .12, 'black')
    elif part in ('diffuse', 'cap'):
        block((x, y, 1.12), (.1, .12, .14), 'blue')
        block((x, y, .96), (.035, .035, .22), 'edge')
    elif part == 'chute':
        # A sloped, open chute connects the reject and exit positions.
        along_y = yaw == 180
        a, b = ((x, y-.6), (x, y+.9)) if along_y else ((x-.6, y), (x+.9, y))
        dx, dy = b[0]-a[0], b[1]-a[1]
        perp = (-dy/math.hypot(dx, dy)*.35, dx/math.hypot(dx, dy)*.35)
        pts = [(px+sgn*perp[0], py+sgn*perp[1], h)
               for (px, py), h in [(a, .86), (b, .44)] for sgn in (-1, 1)]
        mesh(pts, [(0, 1, 3, 2)], 'edge')
        for i, j in ((0, 2), (1, 3)):
            p, q = pts[i], pts[j]
            mesh([p, q, (q[0], q[1], q[2]+.12), (p[0], p[1], p[2]+.12)], [(0, 1, 2, 3)], 'steel')

# Four illustrative cells per grade lane; this is a layout view, not live stock.
for grade, grid_z in layout.LANES[1:]:
    x = (173-grid_z)/8
    for y in (1.2, 2.1, 3.0, 3.9): cell(x, y)
for x in (.0, .7, 2.3): cell(x, 0)

# Export the actual geometry used by the renderer for reproducibility.
stem = 'line-cad-v0.10'
obj = ['# Simplified equipment geometry; positions from build_line.py', f'mtllib {stem}.mtl']
obj += [f'v {x:.6f} {y:.6f} {z:.6f}' for x, y, z in vertices]
last = None
for indices, material in faces:
    if material != last: obj.append('usemtl '+material); last = material
    obj.append('f '+' '.join(str(i+1) for i in indices))
(OUT/(stem+'.obj')).write_text('\n'.join(obj)+'\n', encoding='utf-8')
(OUT/(stem+'.mtl')).write_text('\n'.join(f'newmtl {key}\nKd '+ ' '.join(f'{v/255:.4f}' for v in rgb)+'\nKa 0.3 0.3 0.3\nKs 0.1 0.1 0.1\nNs 20\n' for key,rgb in COLORS.items()), encoding='utf-8')

# Orthographic solid rendering with shaded faces, fine edges and antialiasing.
W, H, AA = 2500, 880, 2
right = (.9285, .3714, 0)
down = (.1857, -.4642, -.8660)
depth = (-.3216, .8041, -.5)
dot = lambda a,b: sum(x*y for x,y in zip(a,b))
projected = [(dot(v,right), dot(v,down)) for v in vertices]
x0,x1 = min(p[0] for p in projected),max(p[0] for p in projected)
y0,y1 = min(p[1] for p in projected),max(p[1] for p in projected)
scale = min((W-150)/(x1-x0), (H-120)/(y1-y0))*AA
screen = lambda v: ((dot(v,right)-(x0+x1)/2)*scale+W*AA/2,
                    (dot(v,down)-(y0+y1)/2)*scale+H*AA/2)
image = Image.new('RGB',(W*AA,H*AA),'white')
shadow = Image.new('RGBA', image.size)
sd = ImageDraw.Draw(shadow)
for indices, _ in faces:
    sd.polygon([screen((vertices[i][0],vertices[i][1],0)) for i in indices], fill=(40,55,70,10))
shadow = shadow.filter(ImageFilter.GaussianBlur(8*AA))
image.paste(shadow,(0,0),shadow)
draw = ImageDraw.Draw(image)
for indices, material in sorted(faces,key=lambda f:sum(dot(vertices[i],depth) for i in f[0])/len(f[0]),reverse=True):
    ps=[vertices[i] for i in indices]
    a=[ps[1][i]-ps[0][i] for i in range(3)];b=[ps[2][i]-ps[0][i] for i in range(3)]
    n=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    length=math.sqrt(dot(n,n)) or 1
    light=.65+.35*max(0,dot(tuple(v/length for v in n),(-.3,-.4,.866)))
    color=tuple(int(v*light) for v in COLORS[material])
    xy=[screen(v) for v in ps]
    draw.polygon(xy,fill=color)
    # Exclude internal coplanar seams from the CAD outline pass.
    if material != 'belt' and not material.endswith('_flat'):
        draw.line(xy+[xy[0]],fill=tuple(int(v*.85) for v in color),width=AA)
image.resize((W,H),Image.Resampling.LANCZOS).save(OUT/(stem+'.png'))
print(f'Rendered {len(vertices)} vertices / {len(faces)} faces → {stem}.png + OBJ/MTL')
