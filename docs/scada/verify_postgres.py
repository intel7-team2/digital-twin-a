"""Run read-only schema, inventory, and SCADA query checks through Grafana."""

import argparse
import getpass
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


SOURCE = {"uid": "bg551q8i4v6rkb", "type": "grafana-postgresql-datasource"}
BASE_RELATIONS = (
    "alarm", "cell", "cell_box", "cell_inspection", "equipment_state", "event_log", "lot", "sim_run",
    "station", "supply_handoff", "v_alarm_open", "v_box_spread", "v_cell_electrical_latest",
    "v_equipment_time", "v_lot_status", "v_run_yield", "v_set_spread_compare", "v_tester_stats",
)
API_RELATIONS = ("api_access_log", "v_api_usage")
DASHBOARDS = ("cellect-2a-production-db", "cellect-2a-scada-overview-v2")
OPENER = build_opener(ProxyHandler({}))
DETAIL_COUNTS_SQL = """
WITH selected_run AS (
    SELECT run_id FROM sim_run
    WHERE line = '2A'
      AND (btrim(${run_id:sqlstring}) = '' OR run_id::text = btrim(${run_id:sqlstring}))
    ORDER BY started_at DESC, run_id DESC LIMIT 1
)
SELECT r.run_id, i.electrical_total, i.electrical_in_window, k.kits_total, k.kits_in_window
FROM selected_run r
CROSS JOIN LATERAL (
    SELECT count(*) AS electrical_total,
           count(*) FILTER (WHERE i.measured_at >= $__timeFrom()
                             AND i.measured_at < $__timeTo()) AS electrical_in_window
    FROM cell c JOIN cell_inspection i ON i.cell_id = c.cell_id
    WHERE c.run_id = r.run_id AND i.kind = 'electrical'
      AND (btrim(${cell_id:sqlstring}) = '' OR c.cell_id = btrim(${cell_id:sqlstring}))
) i
CROSS JOIN LATERAL (
    SELECT count(*) AS kits_total,
           count(*) FILTER (WHERE COALESCE(b.packed_at, b.opened_at) >= $__timeFrom()
                             AND COALESCE(b.packed_at, b.opened_at) < $__timeTo()) AS kits_in_window
    FROM cell_box b WHERE b.run_id = r.run_id
) k
"""


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def render_variables(sql, values):
    return re.sub(r"\$\{(run_id|cell_id|kit_id):sqlstring\}", lambda m: literal(values[m[1]]), sql)


def catalog_sql():
    relations = ", ".join(map(literal, BASE_RELATIONS + API_RELATIONS))
    return f"""
    SELECT c.relname AS relation, c.relkind::text AS kind,
           a.attname AS column_name, format_type(a.atttypid, a.atttypmod) AS data_type,
           a.attnotnull AS not_null,
           CASE WHEN c.relkind = 'v' THEN pg_get_viewdef(c.oid) END AS view_definition
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
    WHERE n.nspname = 'public' AND c.relkind IN ('r','v') AND c.relname IN ({relations})
    ORDER BY c.relname, a.attnum
    """


def catalog_manifest(rows):
    manifest = {}
    for row in rows:
        relation = manifest.setdefault(row["relation"], {
            "kind": row["kind"], "columns": {}, "view_definition": row["view_definition"],
        })
        relation["columns"][row["column_name"]] = [row["data_type"], row["not_null"]]
    return manifest


def compare_catalog(actual, reference):
    return sorted(name for name in actual.keys() | reference.keys() if actual.get(name) != reference.get(name))


def frame_rows(result):
    rows = []
    for frame in result.get("frames", []):
        names = [field["name"] for field in frame["schema"]["fields"]]
        rows.extend(dict(zip(names, row)) for row in zip(*frame.get("data", {}).get("values", [])))
    return rows


def query(sql, window, auth=None, port=3300):
    if not re.match(r"\s*(?:SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ValueError("Only Grafana SELECT queries are supported")
    start, end = (str(int(point.timestamp() * 1000)) for point in window)
    target = {"refId": "A", "datasource": SOURCE, "format": "table", "rawQuery": True, "rawSql": sql}
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth
    req = Request(f"http://127.0.0.1:{port}/api/ds/query", headers=headers,
                  data=json.dumps({"queries": [target], "from": start, "to": end}).encode())
    with OPENER.open(req, timeout=15) as response:
        result = json.load(response)["results"]["A"]
    if result.get("error") or result.get("status", 200) >= 400:
        raise RuntimeError("Grafana reported a data-source query error; inspect the panel or connection locally.")
    return frame_rows(result)


def dashboard_queries():
    root = Path(__file__).resolve().parent / "dashboards"
    for name in DASHBOARDS:
        dashboard = json.loads((root / f"{name}.json").read_text(encoding="utf-8-sig"))
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                if "rawSql" in target:
                    if target.get("datasource", {}).get("uid") != SOURCE["uid"]:
                        raise ValueError(f"Unexpected data source in {name} panel {panel['id']}")
                    yield name, panel["id"], target["rawSql"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-token", action="store_true", help="Read an existing Grafana API token without echo")
    parser.add_argument("--reference", type=Path, help="Catalog manifest from a trusted local reference database")
    parser.add_argument("--run-id", default="", help="Default: latest 2A run")
    parser.add_argument("--cell-id", default="")
    parser.add_argument("--kit-id", default="")
    parser.add_argument("--hours", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.hours <= 168:
        parser.error("--hours must be between 1 and 168")
    if args.prompt_token and not sys.stdin.isatty():
        parser.error("Token input requires an interactive terminal")
    token = getpass.getpass("Existing Grafana API token: ") if args.prompt_token else ""
    auth = f"Bearer {token}" if token else None
    end = datetime.now(timezone.utc)
    window = end - timedelta(hours=args.hours), end
    values = {name: getattr(args, name) for name in ("run_id", "cell_id", "kit_id")}
    try:
        stations = query("SELECT station_code, name FROM station ORDER BY sort_order", window, auth)
        [inventory] = query("""
            SELECT current_setting('transaction_read_only') AS read_only,
                   (SELECT count(*) FROM sim_run WHERE line = '2A') AS runs_2a,
                   (SELECT count(*) FROM cell c JOIN sim_run r USING (run_id) WHERE r.line = '2A') AS cells_2a,
                   (SELECT count(*) FROM event_log WHERE source = '2A') AS events_2a
            """, window, auth)
        if inventory["read_only"] != "on":
            raise RuntimeError("The configured data source did not report a read-only transaction.")
        actual = catalog_manifest(query(catalog_sql(), window, auth))
        missing = sorted(set(BASE_RELATIONS) - actual.keys())
        api_columns = [name for name in ("event_log", "sim_run")
                       if "api_client" in actual.get(name, {}).get("columns", {})]
        print(f"Station SELECT: {len(stations)} rows; 2A inventory: {inventory}")
        print(f"API migration: api_client on {api_columns}; objects {sorted(actual.keys() & set(API_RELATIONS))}")
        print(f"Missing SCADA catalog objects: {missing}")
        if args.reference:
            reference = json.loads(args.reference.read_text(encoding="utf-8"))
            differences = compare_catalog(actual, reference)
            print(f"Catalog differences against reference: {differences}")
        else:
            differences = []
        detail = query(render_variables(DETAIL_COUNTS_SQL, values), window, auth)
        if detail:
            [counts] = detail
            print(f"Selected run {counts['run_id']} detail rows (window / all): "
                  f"electrical {counts['electrical_in_window']}/{counts['electrical_total']}, "
                  f"Kit records {counts['kits_in_window']}/{counts['kits_total']}")
        else:
            print("No matching 2A run for the detail queries.")
        if not (values["cell_id"].strip() or values["kit_id"].strip()):
            print("Trace panels return no rows without a Cell ID or Kit ID.")
        for dashboard, panel, sql in dashboard_queries():
            rows = query(render_variables(sql, values), window, auth)
            print(f"{dashboard} / panel {panel}: SELECT OK · {len(rows)} rows")
        return 1 if missing or differences else 0
    except HTTPError as error:
        print(f"Grafana API HTTP {error.code}; live queries were not fully verified.")
    except (URLError, OSError, ValueError, RuntimeError, KeyError) as error:
        if isinstance(error, RuntimeError):
            print(error)
        else:
            print("Cannot complete Grafana verification. Check the local server, token and reference file.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
