import json
import socket
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parent
GRAFANA_URL = "http://127.0.0.1:3300"
SIMULATOR_URL = "http://127.0.0.1:8766"
DASHBOARD_UID = "cellect-2a-scada-overview-v2"
POSTGRES_UID = "bg551q8i4v6rkb"
TIMEOUT_SECONDS = 2
HTTP = build_opener(ProxyHandler({}))


def get_health(url):
    with HTTP.open(url, timeout=TIMEOUT_SECONDS) as response:
        health = json.load(response)
    if not isinstance(health, dict):
        raise ValueError("Expected a health object")
    return health


def local_provisioning():
    path = (ROOT / ".local" / "grafana.db").as_uri()
    with closing(sqlite3.connect(f"{path}?mode=ro", uri=True, timeout=TIMEOUT_SECONDS)) as db:
        dashboard = db.execute(
            """
            SELECT json_extract(value, '$.spec.title'), json_extract(value, '$.spec.refresh')
            FROM resource
            WHERE resource = 'dashboards' AND namespace = 'default' AND name = ?
            """,
            (DASHBOARD_UID,),
        ).fetchone()
        source = db.execute(
            "SELECT 1 FROM data_source WHERE uid = ? AND org_id = 1", (POSTGRES_UID,)
        ).fetchone()
    return dashboard, source is not None


def report(status, check, details):
    print(f"[{status}] {check} - {details}")


def main():
    ready = True
    try:
        health = get_health(f"{GRAFANA_URL}/api/health")
        if health.get("database") != "ok":
            raise ValueError("Grafana store is not ready")
        report("OK", "Grafana", f"{GRAFANA_URL} · {health['version']}")
    except (URLError, OSError, ValueError, KeyError):
        report("BLOCKED", "Grafana", "3300 응답 없음 또는 Grafana 내부 저장소 준비 중")
        report("SKIP", "등록 확인", "Grafana가 응답한 후 확인")
        ready = False
    else:
        try:
            dashboard, source_exists = local_provisioning()
        except sqlite3.Error:
            report("BLOCKED", "등록 확인", "기본 개발 인스턴스의 로컬 등록 정보를 읽을 수 없음")
            ready = False
        else:
            dashboard_ok = dashboard == ("Cellect 2A - SCADA Overview v2", "10s")
            report("OK" if dashboard_ok else "BLOCKED", "Overview v2", f"{GRAFANA_URL}/d/{DASHBOARD_UID}")
            report("OK" if source_exists else "BLOCKED", "PostgreSQL UID", POSTGRES_UID)
            ready = ready and dashboard_ok and source_exists

    try:
        with socket.create_connection(("127.0.0.1", 5433), timeout=TIMEOUT_SECONDS):
            pass
    except OSError:
        report("BLOCKED", "DB 터널", "로컬 5433에 연결할 수 없음")
        ready = False
    else:
        report("OK", "DB 터널", "로컬 5433 TCP 연결 성공")
    report("PENDING", "DB 조회·화면", "Grafana의 PostgreSQL SELECT와 패널 렌더링은 별도 검증")

    try:
        simulation = get_health(f"{SIMULATOR_URL}/health")
        report("OK", "모의 서버 (선택)", simulation["run_id"])
    except (URLError, OSError, ValueError, KeyError):
        report("INFO", "모의 서버 (선택)", "8766 응답 없음. 운영 DB 화면에는 영향 없음")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
