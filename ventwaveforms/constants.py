"""Shared labels and colors for waveform rendering."""

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
PHASE_LABELS = {0: "Expiration", 1: "Inspiration", 2: "Error"}
PHASE_COLORS = {
    0: ("#e8f3ff", "#1d5fa7"),
    1: ("#e8f7e8", "#1c6b2a"),
    2: ("#fdeaea", "#9b1c1c"),
}
BREATH_COLORS = ["#1259a7", "#c8551a", "#18794e", "#8b2f8f", "#8a6d1d", "#006d77"]
DEFAULT_SELECTED_BREATH = 1
