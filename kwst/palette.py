"""Palety kolorów rysunku i statusów (niezależne od Qt — używane przez GUI, PDF i DXF)."""

CANVAS = {
    "light": {
        "background": "#f6f7f9", "grid": "#e3e6ea",
        "concrete_fill": "#d8dce2", "concrete_edge": "#28313b", "column_fill": "#c7ccd4",
        "plate_fill": "#7b8592", "plate_edge": "#2c3036",
        "strut": "#d62728", "strut_fill": "#e8584f", "tie": "#1f5fbf", "tie_fill": "#4a86e8",
        "node": "#1b1b1b", "node_fill": "#ffffff", "load": "#198a3a", "reaction": "#7e3fa6",
        "dim": "#4d5560", "axis": "#8a929c", "cover": "#2a8a66", "rebar": "#7a3e0e", "rebar_col": "#8c6d50",
        "link": "#5c7a1e", "angle": "#d97706", "handle": "#ff9800", "handle_stm": "#9c27b0",
        "critical": "#e600e6", "eta_low": "#2e7d32", "eta_mid": "#f9a825", "eta_high": "#ef6c00",
        "eta_fail": "#c62828", "text": "#111111", "line": "#333333", "select": "#00b7ff", "measure": "#008b8b",
    },
    "dark": {
        "background": "#1d2025", "grid": "#2a2e35",
        "concrete_fill": "#3a4049", "concrete_edge": "#cfd4da", "column_fill": "#30353d",
        "plate_fill": "#9aa3ae", "plate_edge": "#e0e0e0",
        "strut": "#ff5f57", "strut_fill": "#ff7b72", "tie": "#58a6ff", "tie_fill": "#79b8ff",
        "node": "#eeeeee", "node_fill": "#1d2025", "load": "#3fb950", "reaction": "#c297ff",
        "dim": "#aab2bd", "axis": "#6e7681", "cover": "#3fbf8f", "rebar": "#f0a050", "rebar_col": "#c09a70",
        "link": "#a5d6a7", "angle": "#f0b429", "handle": "#ffb74d", "handle_stm": "#ce93d8",
        "critical": "#ff4dff", "eta_low": "#56d364", "eta_mid": "#e3b341", "eta_high": "#f0883e",
        "eta_fail": "#ff6b6b", "text": "#f0f0f0", "line": "#d0d0d0", "select": "#33ccff", "measure": "#40e0d0",
    },
}

STATUS_COLORS = {
    "light": {"SPEŁNIONO": "#1e7e34", "NIE SPEŁNIONO": "#c62828", "WYMAGA OSOBNEJ WERYFIKACJI": "#b26a00",
              "NIE DOTYCZY": "#6c757d"},
    "dark": {"SPEŁNIONO": "#56d364", "NIE SPEŁNIONO": "#ff6b6b", "WYMAGA OSOBNEJ WERYFIKACJI": "#e3b341",
             "NIE DOTYCZY": "#9aa0a6"},
}

VERDICT_COLORS = {
    "PASS_SCOPE": ("#1e7e34", "#ffffff"), "CONDITIONAL": ("#b26a00", "#ffffff"),
    "FAIL": ("#c62828", "#ffffff"), "BLOCKED": ("#5a0d0d", "#ffffff"), "OUT_OF_SCOPE": ("#6a1b9a", "#ffffff"),
    "STALE": ("#546e7a", "#ffffff"),
}
