"""SVG and WebGL view builders for waveform loops and trajectories."""

from __future__ import annotations

import html
import json
import math

from .constants import BREATH_COLORS, DEFAULT_SELECTED_BREATH

def map_range(value: float, src_min: float, src_max: float, dst_min: float, dst_max: float) -> float:
    src_span = src_max - src_min
    if src_span == 0:
        return (dst_min + dst_max) / 2.0
    ratio = (value - src_min) / src_span
    return dst_min + ratio * (dst_max - dst_min)


def build_loop_view(
    svg_id: str,
    breath_slices: list[dict[str, int | float | None]],
    x_values: list[float],
    y_values: list[float],
    x_label: str,
    y_label: str,
    baseline_axis: str,
    title: str,
    selected_breath: int | None = DEFAULT_SELECTED_BREATH,
    width: int = 640,
    height: int = 440,
) -> str:
    left_pad = 72
    right_pad = 24
    top_pad = 44
    bottom_pad = 54
    plot_width = width - left_pad - right_pad
    plot_height = height - top_pad - bottom_pad
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    x_zero_ref = min(max(0.0, x_min), x_max)
    y_zero_ref = min(max(0.0, y_min), y_max)

    dataset = {
        "svg_id": svg_id,
        "width": width,
        "height": height,
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "baseline_axis": baseline_axis,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "x_zero_ref": x_zero_ref,
        "y_zero_ref": y_zero_ref,
        "breaths": [],
    }
    for idx, breath in enumerate(breath_slices):
        start_idx = int(breath["start_idx"])
        next_start_idx = int(breath["next_start_idx"])
        breath_x = x_values[start_idx:next_start_idx]
        breath_y = y_values[start_idx:next_start_idx]
        if len(breath_x) < 2:
            continue
        dataset["breaths"].append(
            {
                "breath": int(breath["breath"]),
                "color": BREATH_COLORS[idx % len(BREATH_COLORS)],
                "points": list(zip(breath_x, breath_y)),
            }
        )

    markup = build_loop_svg_markup(dataset, selected_breath=selected_breath)
    return (
        f'<svg id="{svg_id}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">{markup}</svg>',
        dataset,
    )


def build_loop_svg_markup(dataset: dict[str, object], selected_breath: int | None) -> str:
    width = int(dataset["width"])
    height = int(dataset["height"])
    left_pad = 72
    right_pad = 24
    top_pad = 44
    bottom_pad = 54
    plot_width = width - left_pad - right_pad
    plot_height = height - top_pad - bottom_pad
    x_min = float(dataset["x_min"])
    x_max = float(dataset["x_max"])
    y_min = float(dataset["y_min"])
    y_max = float(dataset["y_max"])
    zero_x = map_range(float(dataset["x_zero_ref"]), x_min, x_max, left_pad, left_pad + plot_width)
    zero_y = map_range(float(dataset["y_zero_ref"]), y_min, y_max, top_pad + plot_height, top_pad)

    parts = [
        f'<text x="{left_pad}" y="24" class="title-small">{html.escape(str(dataset["title"]))}</text>',
        f'<rect x="{left_pad}" y="{top_pad}" width="{plot_width}" height="{plot_height}" fill="#fffdf8" stroke="#1a1a1a" stroke-width="1"></rect>',
        f'<line x1="{zero_x:.2f}" y1="{top_pad}" x2="{zero_x:.2f}" y2="{top_pad + plot_height}" stroke="#444" stroke-opacity="0.2"></line>',
        f'<line x1="{left_pad}" y1="{zero_y:.2f}" x2="{left_pad + plot_width}" y2="{zero_y:.2f}" stroke="#444" stroke-opacity="0.2"></line>',
    ]

    for breath in dataset["breaths"]:
        breath_no = int(breath["breath"])
        if selected_breath is not None and breath_no != selected_breath:
            continue
        breath_points = breath["points"]
        points = []
        for x_value, y_value in breath_points:
            sx = map_range(float(x_value), x_min, x_max, left_pad, left_pad + plot_width)
            sy = map_range(float(y_value), y_min, y_max, top_pad + plot_height, top_pad)
            points.append(f"{sx:.2f},{sy:.2f}")
        if str(dataset["baseline_axis"]) == "y":
            fill_points = [
                points[0],
                *points,
                f"{map_range(float(breath_points[-1][0]), x_min, x_max, left_pad, left_pad + plot_width):.2f},{zero_y:.2f}",
                f"{map_range(float(breath_points[0][0]), x_min, x_max, left_pad, left_pad + plot_width):.2f},{zero_y:.2f}",
            ]
        else:
            fill_points = [
                points[0],
                *points,
                f"{zero_x:.2f},{map_range(float(breath_points[-1][1]), y_min, y_max, top_pad + plot_height, top_pad):.2f}",
                f"{zero_x:.2f},{map_range(float(breath_points[0][1]), y_min, y_max, top_pad + plot_height, top_pad):.2f}",
            ]
        color = str(breath["color"])
        parts.append(f'<polygon points="{" ".join(fill_points)}" fill="{color}" fill-opacity="0.10"></polygon>')
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"></polyline>')
        parts.append(f'<circle cx="{points[0].split(",")[0]}" cy="{points[0].split(",")[1]}" r="3" fill="{color}"></circle>')

    parts.append(f'<text x="{width / 2:.2f}" y="{height - 14}" text-anchor="middle" class="axis-label">{html.escape(str(dataset["x_label"]))}</text>')
    parts.append(f'<text x="20" y="{height / 2:.2f}" transform="rotate(-90 20 {height / 2:.2f})" text-anchor="middle" class="axis-label">{html.escape(str(dataset["y_label"]))}</text>')
    return "".join(parts)


def build_3d_view(
    times: list[float],
    signals: dict[str, list[float]],
    phases: list[int],
    breath_slices: list[dict[str, int | float | None]],
    selected_breath: int | None = None,
    width: int = 940,
    height: int = 560,
) -> tuple[str, dict[str, object]]:
    flow = signals["data 1"]
    pressure = signals["data 2"]
    volume = signals["data 3"]
    flow_min, flow_max = min(flow), max(flow)
    time_min, time_max = min(times), max(times)
    pressure_min, pressure_max = min(pressure), max(pressure)
    volume_min, volume_max = min(volume), max(volume)

    dataset = {
        "width": width,
        "height": height,
        "mins": {"flow": flow_min, "time": time_min, "volume": volume_min, "pressure": pressure_min},
        "maxs": {"flow": flow_max, "time": time_max, "volume": volume_max, "pressure": pressure_max},
        "breaths": [],
        "errors": [],
    }

    for idx, breath in enumerate(breath_slices):
        start_idx = int(breath["start_idx"])
        next_start_idx = int(breath["next_start_idx"])
        breath_number = int(breath["breath"])
        dataset["breaths"].append(
            {
                "breath": breath_number,
                "color": BREATH_COLORS[idx % len(BREATH_COLORS)],
                "points": [
                    [flow[i], times[i], volume[i], pressure[i], phases[i]]
                    for i in range(start_idx, next_start_idx)
                ],
            }
        )
        for index in range(start_idx, next_start_idx):
            if phases[index] == 2:
                dataset["errors"].append(
                    {
                        "breath": breath_number,
                        "point": [flow[index], times[index], volume[index], pressure[index]],
                    }
                )

    widget = f"""
<div class="trajectory-widget">
  <div class="trajectory-stage">
    <canvas id="trajectory-3d-gl" aria-label="Interactive WebGL ventilator waveform trajectory"></canvas>
    <canvas id="trajectory-3d-labels" aria-hidden="true"></canvas>
    <div class="gl-settings">
      <button id="gl-settings-button" class="gl-settings-button" type="button" aria-expanded="false" aria-controls="gl-settings-panel">Settings</button>
      <div id="gl-settings-panel" class="gl-settings-panel" hidden>
        <label>X axis
          <select id="x-axis-control">
            <option value="flow" selected>Flow</option>
            <option value="time">Time</option>
            <option value="volume">Volume</option>
            <option value="pressure">Pressure</option>
          </select>
        </label>
        <label>Y axis
          <select id="y-axis-control">
            <option value="flow">Flow</option>
            <option value="time">Time</option>
            <option value="volume" selected>Volume</option>
            <option value="pressure">Pressure</option>
          </select>
        </label>
        <label>Z axis
          <select id="z-axis-control">
            <option value="flow">Flow</option>
            <option value="time" selected>Time</option>
            <option value="volume">Volume</option>
            <option value="pressure">Pressure</option>
          </select>
        </label>
        <label>Thickness
          <select id="thickness-control">
            <option value="pressure" selected>Pressure</option>
            <option value="flow">Flow</option>
            <option value="time">Time</option>
            <option value="volume">Volume</option>
          </select>
        </label>
        <label>Min thickness
          <input id="thickness-min-control" type="number" min="0.5" max="120" step="0.25" value="5">
        </label>
        <label>Max thickness
          <input id="thickness-max-control" type="number" min="0.5" max="120" step="0.25" value="80">
        </label>
        <label>Rotation mode
          <button id="camera-mode-toggle" type="button" aria-pressed="true">Quaternion</button>
        </label>
        <label>Trace playback
          <button id="trace-animation-toggle" type="button" aria-pressed="false">Animate Time</button>
        </label>
        <label>Replay speed
          <button id="time-domain-toggle" type="button" aria-pressed="false">Real time</button>
        </label>
        <label>Grid scale
          <button id="data-scale-toggle" type="button" aria-pressed="false">Raw values</button>
        </label>
        <label>Volume fill
          <select id="volume-fill-pattern-control">
            <option value="phase" selected>Phase colors</option>
            <option value="breath">Breath colors</option>
            <option value="amber">Amber fade</option>
            <option value="teal">Teal fade</option>
            <option value="violet">Violet fade</option>
          </select>
        </label>
        <div class="ring-control-settings">
          <div class="settings-subtitle">Ring control</div>
          <button id="ring-connect-toggle" type="button" aria-pressed="false">Connect R02_DA00</button>
          <button id="ring-control-toggle" type="button" aria-pressed="false" disabled>Ring Off</button>
          <div class="ring-pose-row">
            <button type="button" data-ring-pose="side1">Side 1</button>
            <button type="button" data-ring-pose="side2">Side 2</button>
            <button type="button" data-ring-pose="north">North</button>
          </div>
          <button id="ring-zero-button" type="button" disabled>Zero Current Pose</button>
          <div id="ring-control-status" class="ring-control-status">Ring disconnected</div>
        </div>
        <div id="trace-animation-status" class="trace-animation-status">Full trace shown</div>
        <button id="reset-camera-3d" type="button">Reset Camera</button>
        <p>Use Quaternion mode for continuous rotation without pole locking.</p>
      </div>
    </div>
    <div class="camera-orb" aria-label="Camera view orb">
      <div class="camera-orb-ring" aria-hidden="true"></div>
      <button class="orb-node orb-top" type="button" data-camera-step="top">Top</button>
      <button class="orb-node orb-front" type="button" data-camera-step="front">Front</button>
      <button class="orb-node orb-right" type="button" data-camera-step="right">Right</button>
      <button class="orb-node orb-left" type="button" data-camera-step="left">Left</button>
      <button class="orb-node orb-back" type="button" data-camera-step="back">Back</button>
      <button class="orb-node orb-bottom" type="button" data-camera-step="bottom">Bottom</button>
      <button class="orb-node orb-center" type="button" data-camera-step="iso">Iso</button>
    </div>
    <div class="trajectory-help">Drag to rotate. Right-drag to pan. Wheel to zoom. Axes and thickness can be swapped live.</div>
  </div>
  <script id="trajectory-3d-data" type="application/json">{json.dumps(dataset)}</script>
</div>
"""
    return widget, dataset


def build_3d_svg_markup(
    dataset: dict[str, object],
    yaw_deg: float,
    pitch_deg: float,
    roll_deg: float,
    thickness_variable: str,
    selected_breath: int | None,
) -> str:
    width = int(dataset["width"])
    height = int(dataset["height"])
    mins = dataset["mins"]
    maxs = dataset["maxs"]
    breaths = dataset["breaths"]
    errors = dataset["errors"]
    center_x = width * 0.5
    center_y = height * 0.58
    scale = min(width, height) * 0.34

    def normalize(point: list[float]) -> tuple[float, float, float]:
        flow, time_value, volume, _pressure = point
        x = ((flow - mins["flow"]) / ((maxs["flow"] - mins["flow"]) or 1.0)) * 2.0 - 1.0
        y = ((time_value - mins["time"]) / ((maxs["time"] - mins["time"]) or 1.0)) * 2.0 - 1.0
        z = ((volume - mins["volume"]) / ((maxs["volume"] - mins["volume"]) or 1.0)) * 2.0 - 1.0
        return x, y, z

    def project(point: list[float], z_override: float | None = None) -> tuple[float, float, float]:
        x, y, z = normalize(point)
        if z_override is not None:
            z = z_override
        yaw = yaw_deg * 3.141592653589793 / 180.0
        pitch = pitch_deg * 3.141592653589793 / 180.0
        roll = roll_deg * 3.141592653589793 / 180.0
        cos_y = math.cos(yaw)
        sin_y = math.sin(yaw)
        cos_p = math.cos(pitch)
        sin_p = math.sin(pitch)
        cos_r = math.cos(roll)
        sin_r = math.sin(roll)
        x1 = x * cos_y - y * sin_y
        y1 = x * sin_y + y * cos_y
        z1 = z
        y2 = y1 * cos_p - z1 * sin_p
        z2 = y1 * sin_p + z1 * cos_p
        x3 = x1 * cos_r + z2 * sin_r
        z3 = -x1 * sin_r + z2 * cos_r
        return center_x + x3 * scale, center_y - y2 * scale, z3

    def variable_stroke_width(point: list[float], variable: str) -> float:
        point_index = {"flow": 0, "time": 1, "volume": 2, "pressure": 3}[variable]
        variable_span = (maxs[variable] - mins[variable]) or 1.0
        normalized = (point[point_index] - mins[variable]) / variable_span
        return 1.25 + normalized * 4.75

    origin = project([mins["flow"], mins["time"], mins["volume"], mins["pressure"]], z_override=-1.0)
    flow_axis = project([maxs["flow"], mins["time"], mins["volume"], mins["pressure"]], z_override=-1.0)
    time_axis = project([mins["flow"], maxs["time"], mins["volume"], mins["pressure"]], z_override=-1.0)
    volume_axis = project([mins["flow"], mins["time"], maxs["volume"], mins["pressure"]])

    parts = [
        '<text x="60" y="28" class="title-small">Flow-Time-Volume 3D Trajectory</text>',
        f'<line x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{flow_axis[0]:.2f}" y2="{flow_axis[1]:.2f}" stroke="#1259a7" stroke-width="2"></line>',
        f'<line x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{time_axis[0]:.2f}" y2="{time_axis[1]:.2f}" stroke="#8b2f8f" stroke-width="2"></line>',
        f'<line x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{volume_axis[0]:.2f}" y2="{volume_axis[1]:.2f}" stroke="#b05300" stroke-width="2"></line>',
        f'<text x="{flow_axis[0] + 10:.2f}" y="{flow_axis[1] + 4:.2f}" class="range-label">Flow</text>',
        f'<text x="{time_axis[0] - 34:.2f}" y="{time_axis[1] + 4:.2f}" class="range-label">Time</text>',
        f'<text x="{volume_axis[0] + 10:.2f}" y="{volume_axis[1]:.2f}" class="range-label">Volume</text>',
    ]

    for breath in breaths:
        if selected_breath is not None and int(breath["breath"]) != selected_breath:
            continue
        top_points = [project(point) for point in breath["points"]]
        base_points = [project(point, z_override=-1.0) for point in breath["points"]]
        if len(top_points) < 2:
            continue
        shadow = " ".join(
            f"{p[0]:.2f},{p[1]:.2f}" for p in top_points + list(reversed(base_points))
        )
        parts.append(f'<polygon points="{shadow}" fill="#cfe6d0" fill-opacity="0.12"></polygon>')
        for index in range(len(top_points) - 1):
            start = top_points[index]
            end = top_points[index + 1]
            start_width = variable_stroke_width(breath["points"][index], thickness_variable)
            end_width = variable_stroke_width(breath["points"][index + 1], thickness_variable)
            stroke_width = (start_width + end_width) / 2.0
            parts.append(
                f'<line x1="{start[0]:.2f}" y1="{start[1]:.2f}" '
                f'x2="{end[0]:.2f}" y2="{end[1]:.2f}" '
                f'stroke="{breath["color"]}" stroke-width="{stroke_width:.2f}" '
                'stroke-linecap="round"></line>'
            )

    for error in errors:
        if selected_breath is not None and int(error["breath"]) != selected_breath:
            continue
        px, py, _ = project(error["point"])
        parts.append(f'<circle cx="{px:.2f}" cy="{py - 6:.2f}" r="3.6" fill="#cf2020" stroke="#ffffff" stroke-width="1"></circle>')

    return "".join(parts)


def build_polyline(
    times: list[float],
    values: list[float],
    x_min: float,
    x_max: float,
    y_top: float,
    plot_height: float,
    width: float,
    left_pad: float,
) -> str:
    v_min = min(values)
    v_max = max(values)
    span = v_max - v_min or 1.0
    x_span = x_max - x_min or 1.0
    points = []

    for t_value, v_value in zip(times, values):
        x = left_pad + ((t_value - x_min) / x_span) * width
        normalized = (v_value - v_min) / span
        y = y_top + plot_height - (normalized * plot_height)
        points.append(f"{x:.2f},{y:.2f}")

    return " ".join(points)
