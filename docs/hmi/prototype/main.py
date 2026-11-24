"""Open the offline Cellect 2A main operation prototype."""

import tkinter as tk
from tkinter import ttk

from model import CONTROL_ACTIONS, CONTROL_REASON, METRICS, SCENARIOS, STATIONS, Quality, State, sample


BG = "#0b1421"
PANEL = "#111e30"
MAP_BG = "#0d1828"
BORDER = "#263955"
TEXT = "#eff5ff"
MUTED = "#a6b7ce"
CYAN = "#66d8ee"
AMBER = "#f7c875"
VIOLET = "#c8adff"
RED = "#ff8c97"
STATE_COLORS = {
    State.IDLE: "#8de0b4", State.BUSY: CYAN, State.BLOCKED: AMBER,
    State.STARVED: AMBER, State.STOPPED: MUTED, State.FAULT: RED,
}
QUALITY_COLORS = {Quality.GOOD: CYAN, Quality.MISSING: MUTED, Quality.STALE: AMBER, Quality.OFFLINE: VIOLET}

NODES = {
    "IN": (57, 128), "VIS1": (176, 128), "VIS2": (294, 128), "RJ1": (294, 257),
    "T1": (420, 49), "T2": (420, 100), "T3": (420, 151), "T4": (420, 202),
    "IDC": (544, 128), "RT": (664, 257), "RJ2": (421, 257), "SORT": (664, 128),
    "LA": (785, 62), "LB": (785, 128), "LC": (785, 194), "BOX": (900, 128), "OUT": (1012, 128),
}
EDGES = ((105, 128, 128, 128), (224, 128, 246, 128), (592, 128, 616, 128), (948, 128, 964, 128))
TESTERS = ("T1", "T2", "T3", "T4")
LANES = ("LA", "LB", "LC")


def label(parent, text="", size=10, color=TEXT, bold=False, **options):
    font = ("Malgun Gothic", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text, fg=color, font=font, bg=parent.cget("bg"),
                    anchor="w", justify="left", **options)


def card(parent):
    return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)


class OperationView:
    def __init__(self, root):
        self.root = root
        self.root.title("Cellect 2A | 메인 운전 시제품")
        self.root.configure(bg=BG)
        self.root.geometry("1440x840")
        self.root.minsize(1040, 710)
        self.snapshot = sample("missing")
        self.selected = "T1"
        self.configure_styles()
        self.build_header()
        self.build_status()
        self.build_operation()
        self.build_metrics()
        self.show_scenario("missing")

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Hmi.TCombobox", font=("Malgun Gothic", 10), padding=(8, 5),
                        fieldbackground=MAP_BG, foreground=TEXT, arrowcolor=TEXT, background=PANEL, bordercolor=BORDER)
        style.map("Hmi.TCombobox", foreground=[("readonly", TEXT)], fieldbackground=[("readonly", MAP_BG)],
                  selectbackground=[("readonly", MAP_BG)], selectforeground=[("readonly", TEXT)])
        style.configure("Locked.TButton", font=("Segoe UI", 10, "bold"), padding=(7, 8), borderwidth=1)
        style.map("Locked.TButton", background=[("disabled", "#182437")], foreground=[("disabled", "#9caec7")],
                  bordercolor=[("disabled", BORDER)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#274562")

    def build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=22, pady=(17, 11))
        title = tk.Frame(header, bg=BG)
        title.pack(side="left")
        label(title, "CELLECT / 2A", size=10, color=CYAN, bold=True).pack(anchor="w")
        label(title, "메인 운전", size=23, bold=True).pack(anchor="w")
        chooser = tk.Frame(header, bg=BG)
        chooser.pack(side="right")
        label(chooser, "테스트 입력 · 외부 연결 없음", color=AMBER, bold=True).pack(anchor="e", pady=(0, 5))
        scenario_row = tk.Frame(chooser, bg=BG)
        scenario_row.pack(anchor="e")
        label(scenario_row, "시나리오", color=MUTED).pack(side="left", padx=(0, 9))
        self.scenario_input = ttk.Combobox(scenario_row, values=tuple(SCENARIOS.values()), state="readonly",
                                           width=22, style="Hmi.TCombobox")
        self.scenario_input.pack(side="left")
        self.scenario_input.bind("<<ComboboxSelected>>", self.on_scenario)

    def build_status(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=22, pady=(0, 12))
        self.status_fields = {}
        for i, (key, title) in enumerate((
            ("line", "라인 상태"), ("quality", "브리지 · PLC 관측"),
            ("run", "선택 회차"), ("observed", "마지막 관측 · KST"),
        )):
            block = card(row)
            block.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            row.columnconfigure(i, weight=1, uniform="status")
            label(block, title, color=MUTED).pack(fill="x", padx=12, pady=(9, 0))
            value = label(block, size=16, bold=True)
            value.pack(fill="x", padx=12, pady=(1, 8))
            self.status_fields[key] = value

    def build_operation(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="both", expand=True, padx=22)
        row.columnconfigure(0, weight=1)
        row.rowconfigure(0, weight=1)
        process = card(row)
        process.grid(row=0, column=0, sticky="nsew", padx=(0, 11))
        label(process, "2A 공정 지도", size=14, bold=True).pack(fill="x", padx=14, pady=(10, 0))
        label(process, "공정 카드를 선택하면 상태를 자세히 볼 수 있습니다.", color=MUTED).pack(fill="x", padx=14, pady=(0, 6))
        self.map = tk.Canvas(process, bg=MAP_BG, highlightthickness=0, height=300)
        self.map.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.map.bind("<Configure>", lambda _: self.draw_map())

        side = card(row)
        side.grid(row=0, column=1, sticky="nsew")
        label(side, "운전 조작", size=14, bold=True).pack(fill="x", padx=14, pady=(10, 4))
        self.control_buttons = {}
        control_row = tk.Frame(side, bg=PANEL)
        control_row.pack(fill="x", padx=12, pady=(0, 8))
        for action in CONTROL_ACTIONS:
            button = ttk.Button(control_row, text=action, width=7, style="Locked.TButton", state="disabled")
            button.pack(side="left", padx=2)
            self.control_buttons[action] = button
        label(side, CONTROL_REASON, size=9, color=AMBER).pack(fill="x", padx=14)
        label(side, "비상정지 관측: 미수집", color=MUTED).pack(fill="x", padx=14, pady=(3, 8))
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(0, 8))
        label(side, "선택 공정", size=12, bold=True).pack(fill="x", padx=14)
        self.station_input = ttk.Combobox(side, values=tuple(f"2A-{code}" for code in STATIONS), state="readonly",
                                          width=19, style="Hmi.TCombobox")
        self.station_input.pack(fill="x", padx=14, pady=(3, 6))
        self.station_input.bind("<<ComboboxSelected>>", self.on_station)
        self.station_state = label(side, size=13, bold=True)
        self.station_state.pack(fill="x", padx=14)
        self.station_detail = label(side, size=9, color=MUTED, wraplength=230)
        self.station_detail.pack(fill="x", padx=14, pady=(4, 9))

    def build_metrics(self):
        metrics = card(self.root)
        metrics.pack(fill="x", padx=22, pady=(12, 16))
        self.metric_fields = []
        for i, (title, unit) in enumerate(METRICS):
            block = tk.Frame(metrics, bg=PANEL)
            block.grid(row=0, column=i, sticky="nsew", padx=12, pady=(8, 6))
            metrics.columnconfigure(i, weight=1, uniform="metrics")
            label(block, f"{title} · {unit}", color=MUTED).pack(fill="x")
            value = label(block, size=16, bold=True)
            value.pack(fill="x")
            self.metric_fields.append(value)
        self.handoff_label = label(metrics, color=MUTED, size=9)
        self.handoff_label.grid(row=1, column=0, columnspan=5, sticky="ew", padx=12, pady=(1, 9))

    def on_scenario(self, _event):
        index = self.scenario_input.current()
        if index >= 0:
            self.show_scenario(tuple(SCENARIOS)[index])

    def on_station(self, _event):
        self.select_station(self.station_input.get().removeprefix("2A-"))

    def show_scenario(self, key):
        self.snapshot = sample(key)
        self.scenario_input.set(SCENARIOS[key])
        view = self.snapshot
        self.status_fields["line"].configure(text=view.display_state(), fg=self.state_color())
        self.status_fields["quality"].configure(text=view.quality.value, fg=QUALITY_COLORS[view.quality])
        run_text = view.run_id or "회차 없음"
        if view.last_state():
            run_text += " · 마지막"
        self.status_fields["run"].configure(text=run_text)
        observed = view.observed_at.strftime("%H:%M:%S") if view.observed_at else "미수집"
        self.status_fields["observed"].configure(text=observed)
        for i, field in enumerate(self.metric_fields):
            value = view.display_count(i)
            field.configure(text=value if value != "—" else "— 미수집", fg=TEXT if value != "—" else MUTED)
        self.handoff_label.configure(text=f"인계 · {view.handoff or '미수집'}    /    이력 DB·API · 미연동")
        self.select_station(view.fault_station or self.selected)

    def state_color(self, station=None):
        if self.snapshot.quality is not Quality.GOOD:
            return QUALITY_COLORS[self.snapshot.quality]
        return STATE_COLORS.get(self.snapshot.state_at(station), MUTED)

    def select_station(self, code):
        if code not in STATIONS:
            return
        self.selected = code
        self.station_input.set(f"2A-{code}")
        view = self.snapshot
        self.station_state.configure(text=view.display_state(code), fg=self.state_color(code))
        detail = [f"{STATIONS[code]} · {view.quality.value}"]
        if view.last_state(code):
            detail.append(f"마지막 관측: {view.last_state(code)}")
        if view.fault_station == code:
            detail.append(view.fault_detail)
        self.station_detail.configure(text="\n".join(detail))
        self.draw_map()

    def draw_map(self):
        canvas = self.map
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 10 or height < 10:
            return
        canvas.delete("all")
        scale = min(width / 1070, height / 323)
        left, top = (width - 1070 * scale) / 2, (height - 323 * scale) / 2

        def scaled(coords):
            return [value * scale + (left if i % 2 == 0 else top) for i, value in enumerate(coords)]

        def arrow(*coords, branch=False):
            canvas.create_line(*scaled(coords), fill="#536480" if branch else "#436783",
                               width=max(1, 2 * scale), arrow="last", dash=(4, 3) if branch else ())

        for edge in EDGES:
            arrow(*edge)
        for code in TESTERS:
            y = NODES[code][1]
            arrow(342, 128, 358, 128, 358, y, 372, y)
            arrow(468, y, 483, y, 483, 128, 496, 128)
        for code in LANES:
            y = NODES[code][1]
            arrow(712, 128, 724, 128, 724, y, 737, y)
            arrow(833, y, 843, y, 843, 128, 852, 128)
        arrow(294, 153, 294, 232, branch=True)
        arrow(664, 153, 664, 232, branch=True)
        arrow(616, 257, 544, 257, 544, 153, branch=True)
        arrow(664, 282, 664, 297, 421, 297, 421, 282, branch=True)
        for x, y, text in ((249, 218, "외관 NG"), (707, 220, "재검 대상"), (528, 311, "최종 NG")):
            canvas.create_text(*scaled((x, y)), text=text, fill=MUTED,
                               font=("Malgun Gothic", max(7, round(10 * scale))))

        for code, (x, y) in NODES.items():
            tag = f"station-{code}"
            accent = self.state_color(code)
            chosen = code == self.selected
            border = CYAN if chosen else BORDER
            fill = "#1a3046" if chosen else "#142237"
            canvas.create_rectangle(*scaled((x - 48, y - 24, x + 48, y + 24)), fill=fill, outline=border,
                                    width=max(1, (2 if chosen else 1) * scale), tags=(tag,))
            canvas.create_oval(*scaled((x - 38, y - 13, x - 32, y - 7)), fill=accent, outline=accent, tags=(tag,))
            canvas.create_text(*scaled((x + 3, y - 11)), text=f"2A-{code}", fill=TEXT,
                               font=("Segoe UI", max(8, round(13 * scale)), "bold"), tags=(tag,))
            canvas.create_text(*scaled((x, y + 9)), text=self.snapshot.display_state(code), fill=accent,
                               font=("Malgun Gothic", max(7, round(10 * scale))), tags=(tag,))
            canvas.tag_bind(tag, "<Button-1>", lambda _, station=code: self.select_station(station))


def main():
    root = tk.Tk()
    OperationView(root)
    root.mainloop()


if __name__ == "__main__":
    main()
