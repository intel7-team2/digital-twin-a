import argparse
import fnmatch
import json
import time
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import groupby
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlsplit

from process import CENTERS, Simulation, connect


PREFIX = "cellect.sim."
COUNTS = (
    "production.cells", "vision.pass", "vision.fail", "electrical.pass", "electrical.fail",
    *(f"buffer.{group}" for group in CENTERS), "kits.total",
)
MEASUREMENTS = ("electrical.ocv_v", "electrical.ir_mohm")
METRICS = (*COUNTS, *MEASUREMENTS)


def count_event(counts, kind, result, group, amount=1):
    if kind == "ID_ASSIGNED":
        counts["production.cells"] += amount
    elif kind in ("VISION", "ELECTRICAL"):
        counts[f"{kind.lower()}.{result.lower()}"] += amount
    elif kind in ("SORTED", "PACKED"):
        counts[f"buffer.{group}"] += amount if kind == "SORTED" else -amount
    elif kind == "KIT_CREATED":
        counts["kits.total"] += amount


def render(path, run_id, targets, start, end):
    series = {target: [] for target in targets}
    counts = dict.fromkeys(COUNTS, 0)
    with connect(path) as db:
        db.execute("BEGIN")
        opening = db.execute("""
            SELECT kind, result, group_code, count(*) FROM events
            WHERE run_id = ? AND stamp < ? GROUP BY kind, result, group_code
        """, (run_id, start))
        for kind, result, group, amount in opening:
            count_event(counts, kind, result, group, amount)
        events = db.execute("""
            SELECT stamp, kind, result, group_code, ocv_v, ir_mohm FROM events
            WHERE run_id = ? AND stamp BETWEEN ? AND ? ORDER BY stamp, event_id
        """, (run_id, start, end))
        for stamp, batch in groupby(events, key=lambda event: event["stamp"]):
            measurements = {}
            for event in batch:
                count_event(counts, event["kind"], event["result"], event["group_code"])
                if event["kind"] == "ELECTRICAL":
                    measurements["electrical.ocv_v"] = event["ocv_v"]
                    measurements["electrical.ir_mohm"] = event["ir_mohm"]
            for target, points in series.items():
                metric = target.removeprefix(PREFIX)
                value = counts.get(metric, measurements.get(metric))
                points.append([value, stamp])

    return [{"target": target, "datapoints": points} for target, points in series.items()]


def find_metrics(pattern):
    depth = len(pattern.split("."))
    matches = {}
    for metric in METRICS:
        full_path = f"{PREFIX}{metric}"
        node = ".".join(full_path.split(".")[:depth])
        if fnmatch.fnmatchcase(node, pattern):
            leaf = int(full_path == node)
            matches[node] = {"id": node, "text": node.rsplit(".", 1)[-1],
                             "leaf": leaf, "expandable": 1 - leaf, "allowChildren": 1 - leaf}
    return list(matches.values())


def read_history(path, run_id, cell_id, kit_id, test_stamp=None):
    with connect(path) as db:
        if test_stamp is not None:
            rows = db.execute("""
                SELECT * FROM events WHERE cell_id = (
                    SELECT cell_id FROM events WHERE run_id = ? AND stamp = ? AND kind = 'ELECTRICAL'
                ) ORDER BY event_id
            """, (run_id, test_stamp))
        elif cell_id:
            rows = db.execute("SELECT * FROM events WHERE cell_id = ? ORDER BY event_id", (cell_id,))
        elif kit_id:
            rows = db.execute("SELECT * FROM events WHERE kit_id = ? ORDER BY event_id", (kit_id,))
        else:
            rows = db.execute("""
                SELECT * FROM events WHERE run_id = ? ORDER BY event_id DESC LIMIT 40
            """, (run_id,))
        return [dict(row) for row in rows]


def trace_page(run_id, rows, cell_id, kit_id, test_stamp):
    def link(field, label):
        if label is None:
            return ""
        href = escape("/trace?" + urlencode({field: label}), quote=True)
        return f'<a href="{href}">{escape(label)}</a>'

    def display(value):
        return "" if value is None else escape(str(value))

    body = []
    for row in rows:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(row["stamp"]))
        fields = [stamp, row["event_id"], row["kind"], row["result"], row["ocv_v"],
                  row["ir_mohm"], row["group_code"], row["slot"]]
        columns = [*(display(field) for field in fields), link("cell_id", row["cell_id"]),
                   link("kit_id", row["kit_id"])]
        body.append("<tr>" + "".join(f"<td>{column}</td>" for column in columns) + "</tr>")

    heading = cell_id or kit_id or (f"검사 시각 {test_stamp}" if test_stamp else f"{run_id} · 최근 이벤트 40건")
    message = escape(heading)
    if not rows:
        message += " · 조회 결과 없음"
    return f"""<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Cellect SCADA 모의 공정 이력</title>
<style>
body {{ font: 1rem system-ui, sans-serif; margin: 2rem; color: #183040; }}
form {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-block: 1rem; }}
input {{ width: min(28rem, 72vw); }} .scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; white-space: nowrap; }}
td, th {{ padding: .5rem; border-bottom: 1px solid #c5d2d8; text-align: left; }}
</style>
<h1>Cellect SCADA 모의 공정 이력</h1><a href="/trace">현재 실행의 최근 이벤트</a>
<form action="/trace"><label>Cell ID <input name="cell_id" value="{escape(cell_id)}"></label>
<button>셀 조회</button></form>
<form action="/trace"><label>Kit ID <input name="kit_id" value="{escape(kit_id)}"></label>
<button>Kit 조회</button></form>
<p>{message}</p><div class="scroll"><table>
<thead><tr><th>발생 시각 (UTC)</th><th>이벤트 ID</th><th>공정</th><th>결과</th><th>OCV (V)</th>
<th>IR (mΩ)</th><th>특성군</th><th>슬롯</th><th>Cell ID</th><th>Kit ID</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></div></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        self.respond(url.path.rstrip("/"), parse_qs(url.query))

    def do_POST(self):
        url = urlsplit(self.path)
        length_header = self.headers.get("Content-Length", "0")
        if not (length_header.isascii() and length_header.isdecimal() and len(length_header) <= 5):
            self.send_error(400)
            return
        length = int(length_header)
        if url.path.rstrip("/") != "/render" or not 0 <= length <= 16384:
            self.send_error(400)
            return
        params = parse_qs(url.query)
        params.update(parse_qs(self.rfile.read(length).decode("utf-8")))
        self.respond("/render", params)

    def respond(self, route, params):
        def param(key, default=""):
            return params.get(key, [default])[0]

        simulation = self.server.simulation
        if route == "/render":
            targets = params.get("target", [])
            if any(not target.startswith(PREFIX) or target.removeprefix(PREFIX) not in METRICS
                   for target in targets):
                self.send_error(400, "Use an exact cellect.sim metric path")
                return
            now = int(time.time())
            try:
                start = int(param("from", now - 600))
                end = int(param("until", now))
                if not 0 <= start <= end <= 2**53:
                    raise ValueError
            except ValueError:
                self.send_error(400, "Expected a valid range in UNIX seconds")
                return
            self.json_response(render(simulation.path, simulation.run_id, targets, start, end))
        elif route == "/metrics/find":
            self.json_response(find_metrics(param("query", "*")))
        elif route == "/health":
            self.json_response({"run_id": simulation.run_id})
        elif route in ("", "/trace", "/api/history"):
            cell_id, kit_id = param("cell_id"), param("kit_id")
            test_ms = param("test_at")
            if test_ms and not (test_ms.isascii() and test_ms.isdecimal() and len(test_ms) <= 15):
                self.send_error(400, "Expected a test timestamp in UNIX milliseconds")
                return
            test_stamp = int(test_ms) // 1000 if test_ms else None
            rows = read_history(simulation.path, simulation.run_id, cell_id, kit_id, test_stamp)
            if route == "/api/history":
                self.json_response({"current_run_id": simulation.run_id, "events": rows})
            else:
                if test_stamp is not None and rows:
                    cell_id = rows[0]["cell_id"]
                self.send_body(trace_page(simulation.run_id, rows, cell_id, kit_id, test_stamp), "text/html")
        else:
            self.send_error(404)

    def json_response(self, payload):
        self.send_body(json.dumps(payload), "application/json")

    def send_body(self, content, content_type):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_request(self, code="-", size="-"):
        if str(code).startswith(("4", "5")):
            super().log_request(code, size)


def main():
    parser = argparse.ArgumentParser(description="Run the local Cellect SCADA simulation")
    parser.add_argument("--interval", type=int, default=2, help="seconds per tick, at least 1")
    parser.add_argument("--seed", type=int, default=42, help="seed for repeatable measurements")
    args = parser.parse_args()
    if args.interval < 1:
        parser.error("--interval must be at least 1 second")

    data_dir = Path(__file__).resolve().parents[1] / ".local"
    data_dir.mkdir(exist_ok=True)
    with ThreadingHTTPServer(("127.0.0.1", 8766), Handler) as server:
        server.simulation = Simulation(data_dir / "simulation.sqlite3", args.seed)
        server.simulation.tick(int(time.time()))
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        print(f"{server.simulation.run_id} | http://127.0.0.1:8766/trace", flush=True)
        try:
            while True:
                time.sleep(args.interval)
                server.simulation.tick(int(time.time()))
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
