"""Build the read-only role dashboards from the verified presentation panels."""

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "dashboards"
PG = {"type": "grafana-postgresql-datasource", "uid": "bg551q8i4v6rkb"}
SHARED = {"type": "dashboard", "uid": "-- Dashboard --"}
ROLES = (
    ("main", "01 메인 · 회차 총괄", ("run_id",), "10s"),
    ("process", "02 공정 관제", ("run_id", "cell_id", "trace_step"), "10s"),
    ("production-flow", "03 생산·인계", ("run_id",), "10s"),
    ("quality-equipment", "04 품질·설비 분석", ("run_id", "cell_id"), ""),
    ("trace", "05 DB 이력·추적", ("run_id", "cell_id", "kit_id", "lot_code"), ""),
)

RUN = """
WITH selected_run AS (
  SELECT run_id, ended_at FROM sim_run WHERE line = '2A'
    AND (NULLIF(btrim(${run_id:sqlstring}), '') IS NULL OR run_id::text = btrim(${run_id:sqlstring}))
  ORDER BY started_at DESC, run_id DESC LIMIT 1
)
"""

COMPLETE = RUN.rstrip() + """, complete AS (
  SELECT b.box_id, b.packed_at
  FROM selected_run r JOIN cell_box b USING (run_id) JOIN cell c USING (box_id)
  WHERE b.status IN ('full','handed_over','consumed') AND b.packed_at IS NOT NULL
  GROUP BY b.box_id, b.packed_at
  HAVING count(*) = 4 AND count(DISTINCT c.box_slot) = 4
    AND bool_and(c.grade IS NOT DISTINCT FROM b.grade AND c.run_id IS NOT DISTINCT FROM b.run_id)
)
"""

PRODUCTION = COMPLETE.rstrip() + """, production_events AS (
  SELECT c.created_at AS stamp, 1 AS cells, 0 AS kits FROM selected_run r JOIN cell c USING (run_id)
  WHERE c.created_at >= $__timeFrom() AND c.created_at < $__timeTo()
  UNION ALL
  SELECT packed_at, 0, 1 FROM complete WHERE packed_at >= $__timeFrom() AND packed_at < $__timeTo()
)
SELECT date_trunc('minute', stamp) AS time, sum(cells) AS "투입 셀", sum(kits) AS "완료 Kit"
FROM production_events GROUP BY 1 ORDER BY 1
"""

DISPATCH = COMPLETE.rstrip() + """, handoff AS (
  SELECT b.box_id, b.packed_at, count(h.request_id) AS requests, min(h.requested_at) AS requested_at,
         min(h.released_at) AS released_at, min(h.confirmed_at) AS confirmed_at
  FROM complete b LEFT JOIN supply_handoff h USING (box_id)
  GROUP BY b.box_id, b.packed_at
)
SELECT box_id AS "Kit ID",
       CASE WHEN confirmed_at IS NOT NULL THEN '수신 확인'
            WHEN released_at IS NOT NULL THEN '출구 통과 · 확인 기록 없음'
            WHEN requested_at IS NOT NULL THEN '요청 접수 · 출구 기록 없음'
            ELSE '요청 기록 없음' END AS "인계 상태",
       packed_at AS "포장", requested_at AS "요청", released_at AS "출구", confirmed_at AS "수신 확인",
       requests AS "요청 기록 수"
FROM handoff ORDER BY confirmed_at NULLS FIRST, released_at NULLS LAST, packed_at DESC, box_id LIMIT 200
"""

FAULTS = RUN.rstrip() + """, observed AS (
  SELECT e.station_code, e.state, e.ended_at,
         GREATEST(e.started_at, $__timeFrom()) AS started_in_range,
         LEAST(COALESCE(e.ended_at, r.ended_at, CURRENT_TIMESTAMP), $__timeTo(), CURRENT_TIMESTAMP) AS ended_in_range
  FROM selected_run r JOIN equipment_state e USING (run_id)
  WHERE e.started_at < $__timeTo() AND COALESCE(e.ended_at, r.ended_at, CURRENT_TIMESTAMP) > $__timeFrom()
)
SELECT s.station_code AS "설비",
       NULLIF(count(o.station_code), 0) AS "상태 관측 구간",
       CASE WHEN count(o.station_code) > 0 THEN count(*) FILTER (WHERE o.state = 'fault') END AS "장애 구간",
       CASE WHEN count(o.station_code) > 0 THEN
         round(COALESCE(sum(extract(epoch FROM o.ended_in_range - o.started_in_range))
               FILTER (WHERE o.state = 'fault'), 0) / 60, 1) END AS "장애 지속시간 (분)",
       CASE WHEN count(o.station_code) > 0 THEN
         count(*) FILTER (WHERE o.state = 'fault' AND o.ended_at IS NULL) END AS "장애 종료 기록 없음"
FROM station s LEFT JOIN observed o ON o.station_code = s.station_code AND o.ended_in_range > o.started_in_range
WHERE s.station_code IN ('2A-T1','2A-T2','2A-T3','2A-T4','2A-RT')
GROUP BY s.station_code, s.sort_order ORDER BY s.sort_order
"""

LOT_SEARCH = RUN + """
SELECT c.lot_code AS "LOT", c.cell_id AS "Cell ID", c.status AS "셀 상태",
       c.grade AS "특성군", c.box_id AS "Kit ID", c.box_slot AS "슬롯", c.created_at AS "등록 시각"
FROM selected_run r JOIN cell c USING (run_id)
WHERE c.lot_code = NULLIF(btrim(${lot_code:sqlstring}), '')
ORDER BY c.created_at DESC, c.cell_id LIMIT 200
"""

RATE_ROWS = """
  UNION ALL
  SELECT 'role_rate', metrics.label, metrics.rate, '%', NULL, NULL, NULL, NULL, NULL, NULL
  FROM (
    SELECT count(*) FILTER (WHERE result_code = 9) AS ng,
           count(*) FILTER (WHERE result_code IN (0,9)) AS decided
    FROM (
      SELECT DISTINCT ON (c.cell_id) ci.result_code
      FROM selected_run r JOIN cell c USING (run_id) JOIN cell_inspection ci USING (cell_id)
      WHERE ci.kind = 'appearance'
      ORDER BY c.cell_id, ci.measured_at DESC, ci.id DESC
    ) latest
  ) appearance
  CROSS JOIN (
    SELECT count(*) FILTER (WHERE c.status <> 'retest' AND latest.result_code IN (1,2,3)) AS recovered,
           count(*) AS retested
    FROM selected_run r JOIN cell c USING (run_id)
    LEFT JOIN v_cell_electrical_latest latest USING (cell_id)
    WHERE EXISTS (SELECT 1 FROM cell_inspection i WHERE i.cell_id = c.cell_id
                  AND i.kind = 'electrical' AND i.attempt > 1)
  ) retest
  CROSS JOIN (
    SELECT max("수량") FILTER (WHERE "항목" = '최종 전기 PASS') AS pass,
           max("수량") FILTER (WHERE "항목" = '최종 전기 NG') AS fail
    FROM core WHERE "영역" = 'production'
  ) electrical
  CROSS JOIN LATERAL (VALUES
    ('외관 NG율', 100.0 * appearance.ng / NULLIF(appearance.decided, 0)),
    ('최종 전기 합격률', 100.0 * electrical.pass / NULLIF(electrical.pass + electrical.fail, 0)),
    ('최종 전기 NG율', 100.0 * electrical.fail / NULLIF(electrical.pass + electrical.fail, 0)),
    ('재검 회복률', 100.0 * retest.recovered / NULLIF(retest.retested, 0))
  ) metrics(label, rate)
"""


def grid(panel, x, y, width, height):
    panel["gridPos"] = dict(zip(("x", "y", "w", "h"), (x, y, width, height)))
    return panel


def postgres(panel, sql, output="table"):
    panel["datasource"] = PG
    panel["targets"] = [{
        "refId": "A", "datasource": PG, "editorMode": "code",
        "format": output, "rawQuery": True, "rawSql": sql.strip(),
    }]
    return panel


def use_peer(panel, source_id):
    panel["datasource"] = SHARED
    panel["targets"] = [{"refId": "A", "datasource": SHARED, "panelId": source_id, "withTransforms": False}]


def subset(*filters, fields):
    return [
        {"id": "filterByValue", "options": {"type": "include", "match": "all", "filters": [
            {"fieldName": field, "config": {"id": "equal", "options": {"value": value}}}
            for field, value in filters
        ]}},
        {"id": "filterFieldsByName", "options": {"include": {"names": fields}}},
    ]


def metric(source, pid, title, description):
    panel = deepcopy(source)
    panel.update(id=pid, title=title, description=description)
    panel["transformations"] = subset(("영역", "role_rate"), ("항목", title), fields=["수량"])
    panel["fieldConfig"]["defaults"].update(unit="percent", decimals=1)
    return panel


def adopt_source(panels, source, substitute):
    target = panels[substitute]
    target["datasource"] = deepcopy(source["datasource"])
    target["targets"] = deepcopy(source["targets"])
    for panel in panels.values():
        if panel["id"] != substitute and any(t.get("panelId") == source["id"] for t in panel.get("targets", [])):
            use_peer(panel, substitute)


def layout(base, placements):
    return {pid: grid(deepcopy(base[pid]), *rect) for pid, rect in placements.items()}


def table(pid, title, description, sql):
    return postgres({"id": pid, "title": title, "description": description, "type": "table",
                     "fieldConfig": {"defaults": {"noValue": "미수집"}, "overrides": []},
                     "options": {"showHeader": True, "cellHeight": "sm"}}, sql)


def trace_link(panel, field, variable):
    url = ("/d/cellect-2a-trace?${run_id:queryparam}&from=${__from}&to=${__to}"
           f"&var-{variable}=" + "${__value.raw}")
    panel["fieldConfig"]["overrides"].append({
        "matcher": {"id": "byName", "options": field},
        "properties": [{"id": "links", "value": [
            {"title": "DB 이력 조회", "url": url, "oneClick": True},
        ]}],
    })


def variables(source, visible):
    result = deepcopy(source)
    result.append({"name": "lot_code", "label": "LOT", "type": "textbox", "query": "",
                   "current": {"text": "", "value": ""}, "options": [], "skipUrlSync": False})
    for variable in result:
        variable["hide"] = 0 if variable["name"] in visible else 2
    return result


def make_roles(base):
    default = base[40]
    rate_scope = "최종 전기 판정이 확정된 고유 셀 기준입니다. 재검 대기는 분모에서 제외합니다."
    enriched = deepcopy(base[3])
    sql = enriched["targets"][0]["rawSql"]
    marker = '\n)\nSELECT area AS "영역"'
    assert sql.count(marker) == 1, "Check the shared query before generating role dashboards"
    enriched["targets"][0]["rawSql"] = sql.replace(marker, RATE_ROWS.rstrip() + marker, 1)

    overview = layout(base, {
        1: (0, 0, 4, 3), 48: (9, 0, 8, 3), 49: (17, 0, 7, 3),
        40: (0, 3, 6, 4), 46: (12, 3, 6, 4), 57: (18, 3, 6, 4),
        52: (0, 7, 8, 4), 53: (8, 7, 6, 4), 47: (14, 7, 5, 4), 45: (19, 7, 5, 4),
        28: (0, 11, 24, 5),
    })
    overview[61] = grid(metric(default, 61, "최종 전기 합격률", rate_scope), 6, 3, 6, 4)
    identity = deepcopy(base[48])
    identity.update(id=60, title="데이터 종류", description="공용 DB의 회차 목적을 표시합니다.")
    identity["transformations"] = subset(("영역", "overview"), ("항목", "선택 실행"), fields=["상세"])
    identity["fieldConfig"]["overrides"] = []
    identity["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {
        value: {"text": label, "color": "#F7C875"}
        for value, label in (("fake", "시연 데이터"), ("demo", "시연용 회차"),
                             ("test", "시험 회차"), ("fault-test", "장애 시험 회차"))
    }}]
    overview[60] = grid(identity, 4, 0, 5, 3)
    overview[28]["title"] = "열린 알람 · 최근 3건"
    overview[28]["transformations"] += [
        {"id": "sortBy", "options": {"sort": [{"field": "발생", "desc": True}]}},
        {"id": "limit", "options": {"limitField": 3}},
    ]
    adopt_source(overview, enriched, 40)

    process = layout(base, {
        1: (0, 0, 5, 3), 48: (5, 0, 10, 3), 49: (15, 0, 9, 3),
        20: (0, 3, 24, 9), 3: (0, 12, 14, 7), 28: (14, 12, 10, 7),
        58: (0, 19, 24, 8),
    })
    process[20]["title"] = "2A 공정 평면도 · 기록 기반"
    for override in process[58]["fieldConfig"]["overrides"]:
        for prop in override["properties"]:
            if prop["id"] == "links":
                for link in prop["value"]:
                    link["url"] = link["url"].replace("cellect-2a-scada-presentation", "cellect-2a-process")

    production = layout(base, {
        40: (0, 0, 4, 4), 46: (4, 0, 5, 4), 55: (9, 0, 5, 4),
        56: (14, 0, 5, 4), 57: (19, 0, 5, 4), 24: (16, 4, 8, 8),
    })
    for panel in production.values():
        if panel["type"] == "stat":
            panel["title"] = "회차 · " + panel["title"]
    trend = deepcopy(base[7])
    trend.update(id=63, title="선택 기간 · 분당 투입 셀과 완료 Kit",
                 description="투입과 포장 발생 시각을 분 단위로 집계합니다. 관측이 없는 분은 빈 구간입니다.")
    trend.pop("transformations", None)
    trend["fieldConfig"] = {"defaults": {"min": 0, "decimals": 0, "unit": "short",
                                          "custom": {"drawStyle": "bars", "spanNulls": False}}, "overrides": []}
    trend["options"]["legend"] = {"showLegend": True, "displayMode": "list", "placement": "bottom"}
    production[63] = grid(postgres(trend, PRODUCTION, "time_series"), 0, 4, 16, 8)
    production[64] = grid(table(64, "완료 Kit · 인계 현황",
        "회차 전체의 완료 Kit 기준입니다. 요청 없음과 출구 통과 후 확인 기록 없음을 구분합니다. 최대 200개.",
        DISPATCH), 0, 12, 24, 10)
    trace_link(production[64], "Kit ID", "kit_id")
    adopt_source(production, base[3], 40)

    quality = layout(base, {
        52: (18, 0, 6, 4), 7: (0, 4, 8, 8), 23: (8, 4, 8, 8), 25: (16, 4, 8, 8),
        3: (0, 12, 13, 7), 26: (13, 12, 11, 7), 21: (0, 19, 12, 7),
        27: (12, 19, 12, 7),
    })
    for pid, title, x, explanation in (
        (61, "외관 NG율", 0, "최신 외관 판정이 확정된 고유 셀 중 NG 비율입니다."),
        (62, "최종 전기 NG율", 6, rate_scope),
        (65, "재검 회복률", 12, "재검 기록이 있는 고유 셀 중 현재 최종 전기 합격을 확인한 비율입니다."),
    ):
        quality[pid] = grid(metric(default, pid, title, explanation), x, 0, 6, 4)
    quality[3]["targets"] = deepcopy(enriched["targets"])
    quality[66] = grid(table(66, "선택 기간 · 설비 장애 지속시간",
        "선택 기간에 관측된 상태만 집계합니다. 0은 관측된 구간에 fault 기록이 없는 경우입니다. MTTR은 미연동입니다.",
        FAULTS), 0, 26, 24, 7)

    trace = layout(base, {
        12: (0, 0, 24, 10), 9: (0, 16, 24, 9), 22: (0, 25, 24, 9),
        29: (0, 34, 12, 10), 30: (12, 34, 12, 10), 11: (0, 44, 24, 7),
    })
    trace[67] = grid(table(67, "LOT 검색 · 구성 셀",
        "LOT 코드를 입력하면 선택 회차에 속한 Cell ID와 Kit ID를 보여줍니다. 최대 200개.",
        LOT_SEARCH), 0, 10, 24, 6)
    trace_link(trace[67], "Cell ID", "cell_id")
    trace_link(trace[67], "Kit ID", "kit_id")
    adopt_source(trace, base[1], 29)
    adopt_source(trace, base[7], 22)

    return overview, process, production, quality, trace


def main():
    source = json.loads((ROOT / "cellect-2a-scada-presentation.json").read_text(encoding="utf-8-sig"))
    base = {panel["id"]: panel for panel in source["panels"]}
    for (role, title, shown, refresh), panels in zip(ROLES, make_roles(base)):
        dashboard = {key: deepcopy(value) for key, value in source.items()
                     if key not in {"id", "title", "uid", "description", "tags", "templating", "panels", "links"}}
        uid = f"cellect-2a-{role}"
        dashboard.update(id=None, uid=uid, title=f"Cellect 2A · {title}",
                         description=f"{title} · 팀 공용 PostgreSQL 읽기 전용",
                         tags=["cellect", "2a", "scada", "업무별 관제"], refresh=refresh,
                         templating={"list": variables(source["templating"]["list"], shown)},
                         panels=sorted(panels.values(), key=lambda p: (p["gridPos"]["y"], p["gridPos"]["x"])))
        dashboard["links"] = [
            {"type": "link", "title": name, "url": f"/d/cellect-2a-{target}", "keepTime": True,
             "includeVars": True, "targetBlank": False}
            for target, name, _, _ in ROLES if target != role
        ]
        (ROOT / f"{uid}.json").write_text(
            json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
        )


if __name__ == "__main__":
    main()
