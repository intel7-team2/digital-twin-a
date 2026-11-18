"""Read-only live trace: python plc/observe.py --seconds 60 --out trace.json."""
import argparse
import json
from pathlib import Path
import time
from urllib.request import urlopen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    events, last, prev_exit, exits = [], None, False, 0
    start = time.monotonic()
    while time.monotonic() - start < args.seconds:
        with urlopen('http://127.0.0.1:8765/', timeout=2) as response:
            state = json.load(response)
        at_exit = state['sensors'][14]
        if at_exit and not prev_exit:
            exits += 1
        prev_exit = at_exit
        mem = state['memory']
        reduced = {k: mem.get(k, 0) for k in
                   ('D2400', 'D2423', 'D2451', 'D2452', 'D2453', 'D2460', 'M2390', 'M2341', 'M2342', 'M2343')}
        reduced.update(exit=at_exit, exits=exits, outputs=state['outputs'])
        if reduced != last:
            events.append({'elapsed': round(time.monotonic()-start, 3), **reduced})
            args.out.write_text(json.dumps(events, indent=2), encoding='utf-8')
            last = reduced
        time.sleep(.04)
    print(json.dumps({'observed_exit_edges': exits, 'last': last}))


if __name__ == '__main__':
    main()
