"""Standalone HTML renderer for captured ventilator waveform reviews."""

from __future__ import annotations

import html
import json
import statistics

from .analysis import analyze_breaths, build_breath_rows, build_breath_slices, build_phase_segments
from .constants import DEFAULT_SELECTED_BREATH, PHASE_COLORS, PHASE_LABELS
from .views import build_3d_view, build_loop_view, build_polyline

def render_html(
    headers: list[str],
    times: list[float],
    phases: list[int],
    signals: dict[str, list[float]],
) -> str:
    left_pad = 88
    right_pad = 24
    top_pad = 48
    bottom_pad = 72
    section_gap = 28
    section_height = 210
    width = 1400
    height = top_pad + bottom_pad + section_height * 3 + section_gap * 2
    plot_width = width - left_pad - right_pad
    x_min = times[0]
    x_max = times[-1]
    x_span = x_max - x_min or 1.0

    wave_defs = [
        ("data 1", "#1259a7"),
        ("data 2", "#8b2f8f"),
        ("data 3", "#b05300"),
    ]

    phase_segments = build_phase_segments(times, phases)
    error_times = [time_value for time_value, phase in zip(times, phases) if phase == 2]
    section_specs = []
    for idx, (name, color) in enumerate(wave_defs):
        y_top = top_pad + idx * (section_height + section_gap)
        section_specs.append(
            {
                "name": name,
                "color": color,
                "y_top": y_top,
                "y_bottom": y_top + section_height,
                "min": min(signals[name]),
                "max": max(signals[name]),
                "polyline": build_polyline(
                    times,
                    signals[name],
                    x_min,
                    x_max,
                    y_top,
                    section_height,
                    plot_width,
                    left_pad,
                ),
            }
        )

    dt_values = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    dt_counts = {}
    for dt in dt_values:
        dt_key = round(dt, 6)
        dt_counts[dt_key] = dt_counts.get(dt_key, 0) + 1

    breath_analysis = analyze_breaths(times, phases)
    breath_rows = build_breath_rows(times, phases, signals)
    breath_slices = build_breath_slices(phases, times)
    pressure_volume_svg, pressure_volume_data = build_loop_view(
        "pressure-volume-loop",
        breath_slices,
        signals["data 3"],
        signals["data 2"],
        "Volume (raw)",
        "Pressure (raw)",
        "y",
        "Pressure-Volume Loops",
    )
    flow_volume_svg, flow_volume_data = build_loop_view(
        "flow-volume-loop",
        breath_slices,
        signals["data 3"],
        signals["data 1"],
        "Volume (raw)",
        "Flow (raw)",
        "y",
        "Flow-Volume Loops",
    )
    pressure_flow_svg, pressure_flow_data = build_loop_view(
        "pressure-flow-loop",
        breath_slices,
        signals["data 1"],
        signals["data 2"],
        "Flow (raw)",
        "Pressure (raw)",
        "y",
        "Pressure-Flow Loops",
    )
    trajectory_3d_svg, trajectory_3d_data = build_3d_view(times, signals, phases, breath_slices)

    summary = {
        "rows": len(times),
        "duration_s": round(times[-1] - times[0], 6),
        "start_s": times[0],
        "end_s": times[-1],
        "median_dt_s": statistics.median(dt_values) if dt_values else 0.0,
        "mean_hz": (len(dt_values) / sum(dt_values)) if dt_values else 0.0,
        "dt_distribution": dt_counts,
        "headers": headers,
        "breath_analysis": breath_analysis,
        "per_breath_rows": breath_rows,
        "trajectory_3d_points": sum(len(item["points"]) for item in trajectory_3d_data["breaths"]),
    }
    breath_options = "".join(
        (
            f'<option value="{int(row["breath"])}"'
            f'{" selected" if int(row["breath"]) == DEFAULT_SELECTED_BREATH else ""}'
            f'>Breath {int(row["breath"])}</option>'
        )
        for row in breath_rows
    )

    metric_rows = [
        ("Breath count (1->0)", breath_analysis["breath_count_1_to_0"]),
        (
            "Respiratory rate",
            f'{breath_analysis["respiratory_rate_bpm_from_cycle_mean"]:.2f} bpm'
            if breath_analysis["respiratory_rate_bpm_from_cycle_mean"] is not None
            else "n/a",
        ),
        (
            "Inspiratory time",
            f'{breath_analysis["inspiratory_time_s_mean"]:.3f} s mean'
            if breath_analysis["inspiratory_time_s_mean"] is not None
            else "n/a",
        ),
        (
            "Expiratory time",
            f'{breath_analysis["expiratory_time_s_mean"]:.3f} s mean'
            if breath_analysis["expiratory_time_s_mean"] is not None
            else "n/a",
        ),
        (
            "Estimated I:E",
            f'1:{breath_analysis["e_to_i_ratio_mean"]:.2f}'
            if breath_analysis["e_to_i_ratio_mean"] is not None
            else "n/a",
        ),
        ("Error segments", breath_analysis["error_segment_count"]),
    ]
    metric_cards = "".join(
        f'<div class="metric"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'
        for label, value in metric_rows
    )

    phase_legend = "".join(
        (
            f'<div class="legend-item"><span class="swatch" style="background:{PHASE_COLORS[key][0]};'
            f'border-color:{PHASE_COLORS[key][1]};"></span>{html.escape(PHASE_LABELS[key])} ({key})</div>'
        )
        for key in [0, 1, 2]
    )

    table_rows = []
    for row in breath_rows:
        cells = [
            f"<td>{int(row['breath'])}</td>",
            f"<td>{row['t_start']:.3f}</td>",
            f"<td>{row['ti']:.3f}</td>",
            f"<td>{row['te']:.3f}</td>" if row["te"] is not None else "<td>n/a</td>",
            f"<td>{row['t_total']:.3f}</td>" if row["t_total"] is not None else "<td>n/a</td>",
            f"<td>1:{(1 / row['i_to_e']):.2f}</td>" if row["i_to_e"] not in (None, 0) else "<td>n/a</td>",
            f"<td>{row['peak_flow_insp']:.0f}</td>" if row["peak_flow_insp"] is not None else "<td>n/a</td>",
            f"<td>{row['peak_flow_exp']:.0f}</td>" if row["peak_flow_exp"] is not None else "<td>n/a</td>",
            f"<td>{row['pip']:.0f}</td>" if row["pip"] is not None else "<td>n/a</td>",
            f"<td>{row['peep_est']:.0f}</td>" if row["peep_est"] is not None else "<td>n/a</td>",
            f"<td>{row['tidal_volume_est']:.0f}</td>" if row["tidal_volume_est"] is not None else "<td>n/a</td>",
        ]
        table_rows.append(
            f'<tr data-breath="{int(row["breath"])}">' + "".join(cells) + "</tr>"
        )
    breath_table = "".join(table_rows)

    section_svgs = []
    for section in section_specs:
        parts = []
        for segment in phase_segments:
            phase = int(segment["phase"])
            fill, stroke = PHASE_COLORS.get(phase, ("#f0f0f0", "#555555"))
            x = left_pad + ((float(segment["start"]) - x_min) / x_span) * plot_width
            rect_width = ((float(segment["end"]) - float(segment["start"])) / x_span) * plot_width
            parts.append(
                f'<rect x="{x:.2f}" y="{section["y_top"]:.2f}" width="{rect_width:.2f}" '
                f'height="{section_height:.2f}" fill="{fill}" opacity="0.8"></rect>'
            )

        parts.append(
            f'<rect x="{left_pad}" y="{section["y_top"]}" width="{plot_width}" height="{section_height}" '
            'fill="none" stroke="#1a1a1a" stroke-width="1"></rect>'
        )

        for step in range(5):
            y = section["y_top"] + (step / 4.0) * section_height
            parts.append(
                f'<line x1="{left_pad}" y1="{y:.2f}" x2="{left_pad + plot_width}" y2="{y:.2f}" '
                'stroke="#666" stroke-opacity="0.15" stroke-width="1"></line>'
            )

        parts.append(
            f'<polyline fill="none" stroke="{section["color"]}" stroke-width="1.5" '
            f'points="{section["polyline"]}"></polyline>'
        )
        parts.append(
            f'<text x="20" y="{section["y_top"] + 18:.2f}" class="axis-label">{html.escape(section["name"])}</text>'
        )
        parts.append(
            f'<text x="20" y="{section["y_top"] + 38:.2f}" class="range-label">{section["min"]:.0f} to {section["max"]:.0f}</text>'
        )
        section_svgs.append("\n".join(parts))

    x_ticks = []
    for step in range(11):
        frac = step / 10.0
        x = left_pad + frac * plot_width
        t = x_min + frac * x_span
        x_ticks.append(
            f'<line x1="{x:.2f}" y1="{top_pad}" x2="{x:.2f}" y2="{height - bottom_pad}" '
            'stroke="#666" stroke-opacity="0.15" stroke-width="1"></line>'
        )
        x_ticks.append(
            f'<text x="{x:.2f}" y="{height - bottom_pad + 26:.2f}" text-anchor="middle" class="tick-label">{t:.2f}s</text>'
        )

    error_markers = []
    marker_y = top_pad - 12
    for time_value in error_times:
        x = left_pad + ((time_value - x_min) / x_span) * plot_width
        error_markers.append(
            f'<circle cx="{x:.2f}" cy="{marker_y:.2f}" r="4" fill="#cf2020" stroke="#ffffff" stroke-width="1.2"></circle>'
        )

    svg = f"""
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Ventilator waveforms">
  <text x="{left_pad}" y="26" class="title">Ventilator Waveforms with Phase Overlay</text>
  {''.join(x_ticks)}
  {''.join(error_markers)}
  {' '.join(section_svgs)}
  <text x="{width / 2:.2f}" y="{height - 18:.2f}" text-anchor="middle" class="axis-label">Program Time [s]</text>
</svg>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VentWaveforms WebGL Explorer v1.5 Ring Control</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f4ec;
      --panel: #fffdf8;
      --ink: #1a1a1a;
      --muted: #5b5448;
      --border: #d8cfbf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, #fff6db 0, transparent 28%),
        linear-gradient(180deg, #f3efe5 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1480px;
      margin: 0 auto;
      padding: 28px;
    }}
    .card {{
      background: color-mix(in srgb, var(--panel) 92%, white);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 12px 36px rgba(44, 33, 14, 0.08);
      overflow: hidden;
    }}
    .header {{
      padding: 22px 24px 14px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.1;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      padding: 14px 24px 0;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--muted);
    }}
    .swatch {{
      width: 14px;
      height: 14px;
      border-radius: 999px;
      border: 2px solid transparent;
      display: inline-block;
    }}
    .plot-wrap {{
      padding: 14px 10px 10px;
      overflow-x: auto;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      padding: 18px 24px 0;
    }}
    .metric {{
      background: #f3eee3;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 16px;
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .metric-value {{
      font-size: 22px;
      font-weight: 700;
      line-height: 1.1;
    }}
    .table-wrap {{
      padding: 8px 24px 0;
      overflow-x: auto;
    }}
    .views-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      padding: 20px 24px 0;
      align-items: start;
    }}
    .view-card {{
      border: 1px solid var(--border);
      border-radius: 16px;
      background: #fffdf8;
      overflow: hidden;
    }}
    .view-card.wide {{
      grid-column: 1 / -1;
    }}
    .view-card svg {{
      min-width: 0;
    }}
    .trajectory-widget {{
      padding: 14px;
    }}
    .trajectory-stage {{
      position: relative;
      height: min(68vh, 680px);
      min-height: 520px;
      background: #f8fbff;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      touch-action: none;
    }}
    #trajectory-3d-gl,
    #trajectory-3d-labels {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      display: block;
    }}
    #trajectory-3d-labels {{
      pointer-events: none;
    }}
    .trajectory-help {{
      position: absolute;
      left: 12px;
      bottom: 10px;
      padding: 6px 8px;
      border-radius: 6px;
      background: rgba(255, 253, 248, 0.86);
      border: 1px solid rgba(107, 118, 130, 0.3);
      color: var(--muted);
      font-size: 13px;
      pointer-events: none;
    }}
    .gl-settings {{
      position: absolute;
      right: 12px;
      bottom: 12px;
      z-index: 3;
      color: var(--ink);
      font-size: 13px;
      display: flex;
      flex-direction: column-reverse;
      align-items: flex-end;
    }}
    .gl-settings-button,
    .gl-settings-panel button,
    .gl-settings-panel select {{
      font: inherit;
      padding: 7px 10px;
      border-radius: 8px;
      border: 1px solid rgba(66, 82, 98, 0.4);
      background: rgba(255, 253, 248, 0.94);
      color: var(--ink);
    }}
    .gl-settings-button,
    .gl-settings-panel button {{
      cursor: pointer;
      box-shadow: 0 4px 10px rgba(31, 41, 51, 0.12);
    }}
    .gl-settings-button {{
      border-radius: 999px 999px 999px 8px;
      padding: 9px 12px;
    }}
    .gl-settings-panel {{
      position: relative;
      margin-bottom: 12px;
      width: min(320px, calc(100vw - 64px));
      max-height: min(70vh, 520px);
      padding: 14px;
      overflow-y: auto;
      overscroll-behavior: contain;
      scrollbar-gutter: stable;
      border-radius: 8px;
      border: 1px solid rgba(66, 82, 98, 0.34);
      background: rgba(255, 253, 248, 0.94);
      box-shadow: 0 12px 28px rgba(31, 41, 51, 0.18);
      backdrop-filter: blur(4px);
    }}
    .gl-settings-panel::after {{
      content: "";
      position: absolute;
      right: 14px;
      bottom: -10px;
      width: 22px;
      height: 22px;
      border-right: 1px solid rgba(66, 82, 98, 0.34);
      border-bottom: 1px solid rgba(66, 82, 98, 0.34);
      background: rgba(255, 253, 248, 0.94);
      transform: rotate(45deg);
      border-radius: 0 0 7px 0;
    }}
    .gl-settings-panel label {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .gl-settings-panel select,
    .gl-settings-panel button {{
      min-width: 132px;
    }}
    .settings-subtitle {{
      margin: 12px 0 8px;
      color: var(--ink);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .ring-control-settings {{
      margin: 12px 0;
      padding: 10px;
      border: 1px solid rgba(66, 82, 98, 0.22);
      border-radius: 8px;
      background: rgba(238, 244, 249, 0.66);
    }}
    .ring-control-settings button {{
      width: 100%;
      margin-bottom: 8px;
    }}
    .ring-control-settings button[disabled] {{
      cursor: not-allowed;
      opacity: 0.56;
    }}
    .ring-pose-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 6px;
      margin-bottom: 8px;
    }}
    .ring-pose-row button {{
      min-width: 0;
      margin: 0;
      padding: 6px 4px;
    }}
    .ring-control-status {{
      margin-top: 2px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}
    #reset-camera-3d {{
      width: 100%;
      margin-top: 2px;
    }}
    .trace-animation-status {{
      margin: 0 0 10px;
      padding: 6px 8px;
      border-radius: 8px;
      background: rgba(238, 244, 249, 0.78);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.3;
    }}
    .gl-settings-panel p {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.35;
    }}
    .camera-orb {{
      position: absolute;
      right: 12px;
      top: 12px;
      width: 166px;
      height: 166px;
      z-index: 2;
      border-radius: 50%;
      background:
        radial-gradient(circle at 35% 28%, rgba(255, 255, 255, 0.98), rgba(232, 239, 246, 0.82) 48%, rgba(153, 171, 188, 0.42) 100%);
      border: 1px solid rgba(80, 96, 112, 0.34);
      box-shadow: 0 10px 28px rgba(31, 41, 51, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(4px);
    }}
    .camera-orb-ring {{
      position: absolute;
      inset: 18px;
      border: 1px solid rgba(70, 84, 100, 0.32);
      border-radius: 50%;
      box-shadow: inset 0 0 18px rgba(60, 79, 98, 0.14);
    }}
    .camera-orb::before,
    .camera-orb::after {{
      content: "";
      position: absolute;
      background: rgba(70, 84, 100, 0.26);
      transform-origin: center;
    }}
    .camera-orb::before {{
      left: 30px;
      right: 30px;
      top: 50%;
      height: 1px;
    }}
    .camera-orb::after {{
      top: 30px;
      bottom: 30px;
      left: 50%;
      width: 1px;
    }}
    .orb-node {{
      position: absolute;
      min-width: 42px;
      height: 30px;
      transform: translate(-50%, -50%);
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      padding: 0 8px;
      border-radius: 8px;
      border: 1px solid rgba(66, 82, 98, 0.4);
      background: rgba(255, 253, 248, 0.94);
      color: var(--ink);
      cursor: pointer;
      box-shadow: 0 4px 10px rgba(31, 41, 51, 0.16);
    }}
    .orb-node:hover,
    .orb-node:focus-visible {{
      background: #f3eee3;
      outline: 2px solid rgba(18, 89, 167, 0.32);
    }}
    .orb-top {{ left: 50%; top: 17%; color: #8b2f8f; }}
    .orb-front {{ left: 50%; top: 83%; color: #8b2f8f; }}
    .orb-right {{ left: 83%; top: 50%; color: #1259a7; }}
    .orb-left {{ left: 17%; top: 50%; color: #1259a7; }}
    .orb-back {{ left: 70%; top: 30%; color: #b05300; }}
    .orb-bottom {{ left: 30%; top: 70%; color: #b05300; }}
    .orb-center {{
      left: 50%;
      top: 50%;
      min-width: 46px;
      height: 34px;
      color: #0d6039;
      background: rgba(255, 255, 255, 0.98);
    }}
    .global-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
      padding: 18px 24px 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .global-controls label {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .global-controls select,
    .global-controls button {{
      font: inherit;
      padding: 8px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #fffdf8;
      color: var(--ink);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
      font-size: 14px;
      background: #fffdf8;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      text-align: right;
      white-space: nowrap;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #f3eee3;
      color: var(--ink);
      font-weight: 700;
    }}
    th:first-child, td:first-child {{
      text-align: left;
    }}
    svg {{
      width: 100%;
      min-width: 1080px;
      height: auto;
      display: block;
    }}
    .title {{
      font-size: 24px;
      font-weight: 700;
    }}
    .title-small {{
      font-size: 18px;
      font-weight: 700;
    }}
    .axis-label {{
      font-size: 16px;
      font-weight: 600;
    }}
    .range-label, .tick-label {{
      font-size: 13px;
      fill: #5b5448;
    }}
    .stats {{
      padding: 0 24px 24px;
      color: var(--muted);
      font-size: 14px;
    }}
    pre {{
      margin: 14px 0 0;
      padding: 14px 16px;
      background: #f3eee3;
      border-radius: 12px;
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <main>
    <section class="card">
      <div class="header">
        <h1>VentWaveforms WebGL Explorer v1.4 High Thickness</h1>
        <p>Three waveform channels are plotted against program time. Background shading uses the phase trace from <code>data 0</code>: expiration, inspiration, and error.</p>
      </div>
      <div class="global-controls">
        <label>Breath
          <select id="breath-filter">
            <option value="all">All breaths</option>
            {breath_options}
          </select>
        </label>
        <button id="clear-breath-filter" type="button">Show All</button>
      </div>
      <div class="legend">{phase_legend}</div>
      <div class="metrics">{metric_cards}</div>
      <div class="plot-wrap">
        {svg}
      </div>
      <div class="views-grid">
        <div class="view-card">{pressure_volume_svg}</div>
        <div class="view-card">{flow_volume_svg}</div>
        <div class="view-card">{pressure_flow_svg}</div>
        <div class="view-card wide">{trajectory_3d_svg}</div>
        <script id="pressure-volume-loop-data" type="application/json">{json.dumps(pressure_volume_data)}</script>
        <script id="flow-volume-loop-data" type="application/json">{json.dumps(flow_volume_data)}</script>
        <script id="pressure-flow-loop-data" type="application/json">{json.dumps(pressure_flow_data)}</script>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Breath</th>
              <th>Start (s)</th>
              <th>Ti (s)</th>
              <th>Te (s)</th>
              <th>Ttot (s)</th>
              <th>I:E</th>
              <th>Peak Insp Flow</th>
              <th>Peak Exp Flow</th>
              <th>PIP</th>
              <th>PEEP est</th>
              <th>Vt est</th>
            </tr>
          </thead>
          <tbody>{breath_table}</tbody>
        </table>
      </div>
      <div class="stats">
        <pre>{html.escape(json.dumps(summary, indent=2))}</pre>
      </div>
    </section>
  </main>
  <script>
    (() => {{
      const glCanvas = document.getElementById('trajectory-3d-gl');
      const labelCanvas = document.getElementById('trajectory-3d-labels');
      const dataEl = document.getElementById('trajectory-3d-data');
      const xAxisInput = document.getElementById('x-axis-control');
      const yAxisInput = document.getElementById('y-axis-control');
      const zAxisInput = document.getElementById('z-axis-control');
      const thicknessInput = document.getElementById('thickness-control');
      const thicknessMinInput = document.getElementById('thickness-min-control');
      const thicknessMaxInput = document.getElementById('thickness-max-control');
      const resetCameraButton = document.getElementById('reset-camera-3d');
      const settingsButton = document.getElementById('gl-settings-button');
      const settingsPanel = document.getElementById('gl-settings-panel');
      const cameraModeToggle = document.getElementById('camera-mode-toggle');
      const traceAnimationToggle = document.getElementById('trace-animation-toggle');
      const timeDomainToggle = document.getElementById('time-domain-toggle');
      const dataScaleToggle = document.getElementById('data-scale-toggle');
      const volumeFillPatternInput = document.getElementById('volume-fill-pattern-control');
      const ringConnectToggle = document.getElementById('ring-connect-toggle');
      const ringControlToggle = document.getElementById('ring-control-toggle');
      const ringZeroButton = document.getElementById('ring-zero-button');
      const ringControlStatus = document.getElementById('ring-control-status');
      const traceAnimationStatus = document.getElementById('trace-animation-status');
      const breathFilter = document.getElementById('breath-filter');
      const clearFilterButton = document.getElementById('clear-breath-filter');
      const pvDataEl = document.getElementById('pressure-volume-loop-data');
      const fvDataEl = document.getElementById('flow-volume-loop-data');
      const pfDataEl = document.getElementById('pressure-flow-loop-data');
      const pvSvg = document.getElementById('pressure-volume-loop');
      const fvSvg = document.getElementById('flow-volume-loop');
      const pfSvg = document.getElementById('pressure-flow-loop');
      if (!glCanvas || !labelCanvas || !dataEl || !xAxisInput || !yAxisInput || !zAxisInput || !thicknessInput || !thicknessMinInput || !thicknessMaxInput || !resetCameraButton || !settingsButton || !settingsPanel || !cameraModeToggle || !traceAnimationToggle || !timeDomainToggle || !dataScaleToggle || !volumeFillPatternInput || !ringConnectToggle || !ringControlToggle || !ringZeroButton || !ringControlStatus || !traceAnimationStatus || !breathFilter || !clearFilterButton) return;

      const data = JSON.parse(dataEl.textContent);
      const pvData = JSON.parse(pvDataEl.textContent);
      const fvData = JSON.parse(fvDataEl.textContent);
      const pfData = JSON.parse(pfDataEl.textContent);
      const variableLabels = {{ flow: 'Flow', time: 'Time', volume: 'Volume', pressure: 'Pressure' }};
      const variablePointIndex = {{ flow: 0, time: 1, volume: 2, pressure: 3 }};
      const variableColors = {{ flow: [0.07, 0.35, 0.65], time: [0.55, 0.18, 0.56], volume: [0.69, 0.33, 0.0], pressure: [0.08, 0.48, 0.2] }};
      const volumeFillGradientPresets = {{
        amber: {{ top: [0.82, 0.38, 0.00, 0.34], base: [1.00, 0.74, 0.22, 0.05] }},
        teal: {{ top: [0.00, 0.47, 0.45, 0.30], base: [0.62, 0.90, 0.86, 0.05] }},
        violet: {{ top: [0.48, 0.25, 0.63, 0.28], base: [0.82, 0.70, 0.94, 0.05] }},
      }};
      const volumeFillPhasePresets = {{
        0: {{ top: [0.61, 0.11, 0.11, 0.32], base: [0.99, 0.86, 0.86, 0.05] }},
        1: {{ top: [0.11, 0.42, 0.16, 0.30], base: [0.91, 0.97, 0.91, 0.05] }},
        2: {{ top: [0.11, 0.37, 0.65, 0.34], base: [0.91, 0.95, 1.00, 0.05] }},
      }};
      let volumeFillPattern = volumeFillPatternInput.value;
      const gl = glCanvas.getContext('webgl', {{ antialias: true, alpha: false }});
      if (!gl) {{
        labelCanvas.getContext('2d').fillText('WebGL is not available in this browser session.', 20, 32);
        return;
      }}
      let xAxisVariable = xAxisInput.value;
      let yAxisVariable = yAxisInput.value;
      let zAxisVariable = zAxisInput.value;
      let thicknessVariable = thicknessInput.value;
      let renderedThicknessVariable = thicknessVariable;
      let thicknessBlend = 1;
      let thicknessMin = Number(thicknessMinInput.value);
      let thicknessMax = Number(thicknessMaxInput.value);
      let thicknessAnimationToken = 0;
      let cameraAnimationToken = 0;
      let dataScale = 'raw';
      const traceAnimation = {{
        active: false,
        frameToken: 0,
        startWallTime: 0,
        startDataTime: data.mins.time,
        endDataTime: data.maxs.time,
        currentDataTime: data.maxs.time,
        currentNormalizedTime: 1,
        timeDomain: 'raw',
      }};
      const camera = {{ yaw: -0.72, pitch: 0.52, orientation: null, mode: 'quaternion', distance: 4.2, target: [0, 0, 0] }};
      const pointer = {{ active: false, button: 0, lastX: 0, lastY: 0 }};
      const ringControl = {{
        serviceUuid: '6e40fff0-b5a3-f393-e0a9-e50e24dcca9e',
        writeUuid: '6e400002-b5a3-f393-e0a9-e50e24dcca9e',
        notifyUuid: '6e400003-b5a3-f393-e0a9-e50e24dcca9e',
        rawOnHex: 'A10404',
        rawOffHex: 'A102',
        connected: false,
        active: false,
        device: null,
        writeCharacteristic: null,
        lastMotion: {{ rotX: 19, rotY: 64, rotZ: 23, ax: 0, ay: 0, az: 1 }},
        zeroPose: {{ rotX: 19, rotY: 64, rotZ: 23 }},
        poses: {{
          side1: {{ rotX: 63, rotY: 124, rotZ: 60 }},
          side2: {{ rotX: 59, rotY: 3, rotZ: 62 }},
          north: {{ rotX: 19, rotY: 64, rotZ: 23 }},
        }},
      }};
      const cameraSteps = {{
        right: {{ yaw: Math.PI / 12, pitch: 0 }},
        left: {{ yaw: -Math.PI / 12, pitch: 0 }},
        top: {{ yaw: 0, pitch: Math.PI / 12 }},
        bottom: {{ yaw: 0, pitch: -Math.PI / 12 }},
        front: {{ yaw: Math.PI / 4, pitch: 0 }},
        back: {{ yaw: -Math.PI / 4, pitch: 0 }},
      }};
      const quatNormalize = (q) => {{
        const len = Math.hypot(q[0], q[1], q[2], q[3]) || 1;
        return [q[0] / len, q[1] / len, q[2] / len, q[3] / len];
      }};
      const quatFromAxisAngle = (axis, angle) => {{
        const normalizedAxis = normalize3(axis);
        const half = angle * 0.5;
        const s = Math.sin(half);
        return quatNormalize([normalizedAxis[0] * s, normalizedAxis[1] * s, normalizedAxis[2] * s, Math.cos(half)]);
      }};
      const quatMultiply = (a, b) => quatNormalize([
        a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
        a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
        a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
        a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
      ]);
      const quatSlerp = (a, b, t) => {{
        let end = b;
        let cosHalfTheta = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
        if (cosHalfTheta < 0) {{
          end = [-b[0], -b[1], -b[2], -b[3]];
          cosHalfTheta = -cosHalfTheta;
        }}
        if (cosHalfTheta > 0.9995) {{
          return quatNormalize([
            a[0] + (end[0] - a[0]) * t,
            a[1] + (end[1] - a[1]) * t,
            a[2] + (end[2] - a[2]) * t,
            a[3] + (end[3] - a[3]) * t,
          ]);
        }}
        const halfTheta = Math.acos(cosHalfTheta);
        const sinHalfTheta = Math.sqrt(1 - cosHalfTheta * cosHalfTheta);
        const ratioA = Math.sin((1 - t) * halfTheta) / sinHalfTheta;
        const ratioB = Math.sin(t * halfTheta) / sinHalfTheta;
        return quatNormalize([
          a[0] * ratioA + end[0] * ratioB,
          a[1] * ratioA + end[1] * ratioB,
          a[2] * ratioA + end[2] * ratioB,
          a[3] * ratioA + end[3] * ratioB,
        ]);
      }};
      const quatRotate = (q, v) => {{
        const u = [q[0], q[1], q[2]];
        const uv = cross(u, v);
        const uuv = cross(u, uv);
        return [
          v[0] + (uv[0] * q[3] + uuv[0]) * 2,
          v[1] + (uv[1] * q[3] + uuv[1]) * 2,
          v[2] + (uv[2] * q[3] + uuv[2]) * 2,
        ];
      }};
      const quatFromEulerCamera = () => quatMultiply(
        quatFromAxisAngle([0, 1, 0], camera.yaw),
        quatFromAxisAngle([1, 0, 0], -camera.pitch)
      );
      const syncEulerFromQuaternion = () => {{
        const offset = quatRotate(camera.orientation, [0, 0, 1]);
        camera.pitch = Math.asin(Math.max(-1, Math.min(1, offset[1])));
        camera.yaw = Math.atan2(offset[0], offset[2]);
      }};
      const normalizeCameraAngles = () => {{
        const halfTurn = Math.PI / 2;
        while (camera.pitch > halfTurn) {{
          camera.pitch = Math.PI - camera.pitch;
          camera.yaw += Math.PI;
        }}
        while (camera.pitch < -halfTurn) {{
          camera.pitch = -Math.PI - camera.pitch;
          camera.yaw += Math.PI;
        }}
        if (camera.yaw > Math.PI || camera.yaw < -Math.PI) {{
          camera.yaw = ((camera.yaw + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
        }}
      }};

      const mapRange = (value, srcMin, srcMax, dstMin, dstMax) => {{
        const srcSpan = srcMax - srcMin;
        if (srcSpan === 0) return (dstMin + dstMax) / 2;
        return dstMin + ((value - srcMin) / srcSpan) * (dstMax - dstMin);
      }};
      const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
      const ringRotToDegrees = (value) => ((clamp(Number(value) || 0, 0, 127) - 63.5) / 63.5) * 180;
      const shortestDegreeDelta = (current, origin) => {{
        let delta = current - origin;
        while (delta > 180) delta -= 360;
        while (delta < -180) delta += 360;
        return delta;
      }};
      const ringPoseOnly = (sample) => ({{
        rotX: clamp(Math.round(sample.rotX), 0, 127),
        rotY: clamp(Math.round(sample.rotY), 0, 127),
        rotZ: clamp(Math.round(sample.rotZ), 0, 127),
      }});
      const ringDeltaDegrees = (axis) => shortestDegreeDelta(
        ringRotToDegrees(ringControl.lastMotion[axis]),
        ringRotToDegrees(ringControl.zeroPose[axis])
      );
      const setRingStatus = (message) => {{
        ringControlStatus.textContent = message;
      }};
      const setRingActive = (active) => {{
        ringControl.active = active && ringControl.connected;
        ringControlToggle.textContent = ringControl.active ? 'Ring On' : 'Ring Off';
        ringControlToggle.setAttribute('aria-pressed', String(ringControl.active));
        if (ringControl.active) {{
          camera.mode = 'quaternion';
          cameraModeToggle.textContent = 'Quaternion';
          cameraModeToggle.setAttribute('aria-pressed', 'true');
        }}
      }};
      const updateRingUi = () => {{
        ringConnectToggle.textContent = ringControl.connected ? 'Disconnect Ring' : 'Connect R02_DA00';
        ringConnectToggle.setAttribute('aria-pressed', String(ringControl.connected));
        ringControlToggle.disabled = !ringControl.connected;
        ringZeroButton.disabled = !ringControl.connected;
        document.querySelectorAll('[data-ring-pose]').forEach((button) => {{
          button.disabled = !ringControl.connected;
        }});
        if (!ringControl.connected) setRingActive(false);
      }};
      const int12 = (u12) => u12 > 2047 ? u12 - 4096 : u12;
      const raw12FromBytes = (hi, lo) => int12(((hi << 4) | (lo & 0x0f)) & 0x0fff);
      const convertRawToG = (raw, rangeG = 4) => (raw / 2048) * rangeG;
      const decodeType3Motion = (bytes) => {{
        if (bytes.length < 8) return null;
        if ((bytes[1] & 0xff) !== 3) return null;
        const rawY = raw12FromBytes(bytes[2] & 0xff, bytes[3] & 0xff);
        const rawZ = raw12FromBytes(bytes[4] & 0xff, bytes[5] & 0xff);
        const rawX = raw12FromBytes(bytes[6] & 0xff, bytes[7] & 0xff);
        const ax = convertRawToG(rawX);
        const ay = convertRawToG(rawY);
        const az = convertRawToG(rawZ);
        const ratio = 127 / Math.PI;
        return {{
          rotX: Math.trunc((Math.atan2(ax, Math.sqrt((ay * ay) + (az * az))) + (Math.PI / 2)) * ratio),
          rotY: Math.trunc((Math.atan2(ay, Math.sqrt((ax * ax) + (az * az))) + (Math.PI / 2)) * ratio),
          rotZ: Math.trunc((Math.atan2(az, Math.sqrt((ax * ax) + (ay * ay))) + (Math.PI / 2)) * ratio),
          ax,
          ay,
          az,
        }};
      }};
      const hexToBytes = (hex) => {{
        const clean = hex.replace(/[^a-fA-F0-9]/g, '');
        if (clean.length % 2 !== 0) return null;
        const bytes = [];
        for (let index = 0; index < clean.length; index += 2) bytes.push(Number.parseInt(clean.slice(index, index + 2), 16));
        return bytes;
      }};
      const frameRingCommand = (hex) => {{
        const bytes = hexToBytes(hex);
        if (!bytes || bytes.length === 0 || bytes.length > 15) return null;
        const frame = new Uint8Array(16);
        bytes.forEach((value, index) => {{ frame[index] = value; }});
        let checksum = 0;
        for (let index = 0; index < 15; index += 1) checksum = (checksum + frame[index]) & 0xff;
        frame[15] = checksum;
        return frame;
      }};
      const sendRingCommand = async (hex) => {{
        if (!ringControl.writeCharacteristic) return;
        const frame = frameRingCommand(hex);
        if (!frame) return;
        await ringControl.writeCharacteristic.writeValue(frame);
      }};
      const applyRingCamera = () => {{
        if (!ringControl.active) return;
        const yaw = ringDeltaDegrees('rotY') * Math.PI / 180;
        const pitch = -ringDeltaDegrees('rotX') * Math.PI / 180;
        const roll = ringDeltaDegrees('rotZ') * Math.PI / 180;
        camera.orientation = quatMultiply(
          quatFromAxisAngle([0, 1, 0], yaw),
          quatMultiply(
            quatFromAxisAngle([1, 0, 0], pitch),
            quatFromAxisAngle([0, 0, 1], roll)
          )
        );
        camera.mode = 'quaternion';
        draw();
      }};
      const handleRingNotification = (event) => {{
        const value = event.target.value;
        const bytes = new Uint8Array(value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength));
        const motion = decodeType3Motion(bytes);
        if (!motion) return;
        ringControl.lastMotion = motion;
        setRingStatus(`Ring motion ${{motion.rotX}}, ${{motion.rotY}}, ${{motion.rotZ}} | zero ${{ringControl.zeroPose.rotX}}, ${{ringControl.zeroPose.rotY}}, ${{ringControl.zeroPose.rotZ}}`);
        applyRingCamera();
      }};
      const disconnectRing = async () => {{
        try {{
          await sendRingCommand(ringControl.rawOffHex);
        }} catch (_error) {{}}
        if (ringControl.device?.gatt?.connected) ringControl.device.gatt.disconnect();
        ringControl.connected = false;
        ringControl.device = null;
        ringControl.writeCharacteristic = null;
        setRingStatus('Ring disconnected');
        updateRingUi();
      }};
      const connectRing = async () => {{
        if (!navigator.bluetooth) {{
          setRingStatus('Web Bluetooth is not available in this browser.');
          return;
        }}
        const device = await navigator.bluetooth.requestDevice({{
          filters: [{{ name: 'R02_DA00' }}, {{ namePrefix: 'R02' }}, {{ namePrefix: 'COLMI' }}, {{ namePrefix: 'QRING' }}],
          optionalServices: [ringControl.serviceUuid],
        }});
        ringControl.device = device;
        device.addEventListener('gattserverdisconnected', () => {{
          ringControl.connected = false;
          ringControl.writeCharacteristic = null;
          setRingStatus('Ring disconnected');
          updateRingUi();
        }});
        setRingStatus(`Connecting ${{device.name || 'ring'}}...`);
        const server = await device.gatt.connect();
        const service = await server.getPrimaryService(ringControl.serviceUuid);
        ringControl.writeCharacteristic = await service.getCharacteristic(ringControl.writeUuid);
        const notifyCharacteristic = await service.getCharacteristic(ringControl.notifyUuid);
        notifyCharacteristic.addEventListener('characteristicvaluechanged', handleRingNotification);
        await notifyCharacteristic.startNotifications();
        ringControl.connected = true;
        updateRingUi();
        await sendRingCommand(ringControl.rawOnHex);
        setRingStatus(`Ring connected: ${{device.name || 'R02_DA00'}}`);
      }};

      const pointValue = (point, variable) => point[variablePointIndex[variable]];
      const timeSpan = () => (data.maxs.time - data.mins.time) || 1;
      const rawTimeToNormalized = (timeValue) => (timeValue - data.mins.time) / timeSpan();
      const normalizedTimeToRaw = (normalizedTime) => data.mins.time + normalizedTime * timeSpan();
      const gridTickLabel = (variable, unit) => {{
        if (dataScale === 'normalized') return unit.toFixed(2);
        return (data.mins[variable] + unit * (data.maxs[variable] - data.mins[variable])).toFixed(2);
      }};
      const normalizeVariable = (value, variable) => {{
        const span = (data.maxs[variable] - data.mins[variable]) || 1;
        return ((value - data.mins[variable]) / span) * 2 - 1;
      }};
      const normalizedPoint = (point) => [
        normalizeVariable(pointValue(point, xAxisVariable), xAxisVariable),
        normalizeVariable(pointValue(point, yAxisVariable), yAxisVariable),
        normalizeVariable(pointValue(point, zAxisVariable), zAxisVariable),
      ];
      const displayedAxisVariables = () => [xAxisVariable, yAxisVariable, zAxisVariable];
      const volumeAxisIndex = () => displayedAxisVariables().indexOf('volume');
      const volumeBaselineCoordinate = () => {{
        const rawBaseline = Math.max(data.mins.volume, 0);
        return normalizeVariable(Math.min(rawBaseline, data.maxs.volume), 'volume');
      }};
      const volumeBaselinePoint = (point, baselineCoordinate) => {{
        const axisIndex = volumeAxisIndex();
        if (axisIndex < 0) return null;
        const base = normalizedPoint(point);
        base[axisIndex] = baselineCoordinate;
        return base;
      }};
      const interpolatePoint = (startPoint, endPoint, blend) => startPoint.map((value, index) => value + (endPoint[index] - value) * blend);
      const thicknessRange = () => {{
        const a = Math.max(0.5, Math.min(120, Number.isFinite(thicknessMin) ? thicknessMin : 5));
        const b = Math.max(0.5, Math.min(120, Number.isFinite(thicknessMax) ? thicknessMax : 80));
        return [Math.min(a, b), Math.max(a, b)];
      }};
      const thicknessForPoint = (point, variable) => {{
        const span = (data.maxs[variable] - data.mins[variable]) || 1;
        const normalized = (pointValue(point, variable) - data.mins[variable]) / span;
        const [minThickness, maxThickness] = thicknessRange();
        return minThickness + Math.max(0, Math.min(1, normalized)) * (maxThickness - minThickness);
      }};
      const blendedThickness = (startPoint, endPoint) => {{
        const fromWidth = (thicknessForPoint(startPoint, renderedThicknessVariable) + thicknessForPoint(endPoint, renderedThicknessVariable)) / 2;
        const toWidth = (thicknessForPoint(startPoint, thicknessVariable) + thicknessForPoint(endPoint, thicknessVariable)) / 2;
        return fromWidth + (toWidth - fromWidth) * thicknessBlend;
      }};

      const renderLoop = (targetSvg, dataset, selectedBreath) => {{
        if (!targetSvg || !dataset) return;
        const width = dataset.width;
        const height = dataset.height;
        const leftPad = 72;
        const rightPad = 24;
        const topPad = 44;
        const bottomPad = 54;
        const plotWidth = width - leftPad - rightPad;
        const plotHeight = height - topPad - bottomPad;
        const zeroX = mapRange(dataset.x_zero_ref, dataset.x_min, dataset.x_max, leftPad, leftPad + plotWidth);
        const zeroY = mapRange(dataset.y_zero_ref, dataset.y_min, dataset.y_max, topPad + plotHeight, topPad);
        const items = [
          `<text x="${{leftPad}}" y="24" class="title-small">${{dataset.title}}</text>`,
          `<rect x="${{leftPad}}" y="${{topPad}}" width="${{plotWidth}}" height="${{plotHeight}}" fill="#fffdf8" stroke="#1a1a1a" stroke-width="1"></rect>`,
          `<line x1="${{zeroX.toFixed(2)}}" y1="${{topPad}}" x2="${{zeroX.toFixed(2)}}" y2="${{(topPad + plotHeight).toFixed(2)}}" stroke="#444" stroke-opacity="0.2"></line>`,
          `<line x1="${{leftPad}}" y1="${{zeroY.toFixed(2)}}" x2="${{(leftPad + plotWidth).toFixed(2)}}" y2="${{zeroY.toFixed(2)}}" stroke="#444" stroke-opacity="0.2"></line>`,
        ];
        for (const breath of dataset.breaths) {{
          if (selectedBreath !== null && breath.breath !== selectedBreath) continue;
          const points = breath.points.map(([xValue, yValue]) => {{
            const sx = mapRange(xValue, dataset.x_min, dataset.x_max, leftPad, leftPad + plotWidth);
            const sy = mapRange(yValue, dataset.y_min, dataset.y_max, topPad + plotHeight, topPad);
            return [sx, sy];
          }});
          if (points.length < 2) continue;
          const polyline = points.map((p) => `${{p[0].toFixed(2)}},${{p[1].toFixed(2)}}`).join(' ');
          let fillPoints;
          if (dataset.baseline_axis === 'y') {{
            fillPoints = [
              `${{points[0][0].toFixed(2)}},${{points[0][1].toFixed(2)}}`,
              ...points.map((p) => `${{p[0].toFixed(2)}},${{p[1].toFixed(2)}}`),
              `${{points[points.length - 1][0].toFixed(2)}},${{zeroY.toFixed(2)}}`,
              `${{points[0][0].toFixed(2)}},${{zeroY.toFixed(2)}}`
            ].join(' ');
          }} else {{
            fillPoints = [
              `${{points[0][0].toFixed(2)}},${{points[0][1].toFixed(2)}}`,
              ...points.map((p) => `${{p[0].toFixed(2)}},${{p[1].toFixed(2)}}`),
              `${{zeroX.toFixed(2)}},${{points[points.length - 1][1].toFixed(2)}}`,
              `${{zeroX.toFixed(2)}},${{points[0][1].toFixed(2)}}`
            ].join(' ');
          }}
          items.push(`<polygon points="${{fillPoints}}" fill="${{breath.color}}" fill-opacity="0.10"></polygon>`);
          items.push(`<polyline points="${{polyline}}" fill="none" stroke="${{breath.color}}" stroke-width="2"></polyline>`);
          items.push(`<circle cx="${{points[0][0].toFixed(2)}}" cy="${{points[0][1].toFixed(2)}}" r="3" fill="${{breath.color}}"></circle>`);
        }}
        items.push(`<text x="${{(width / 2).toFixed(2)}}" y="${{height - 14}}" text-anchor="middle" class="axis-label">${{dataset.x_label}}</text>`);
        items.push(`<text x="20" y="${{(height / 2).toFixed(2)}}" transform="rotate(-90 20 ${{(height / 2).toFixed(2)}})" text-anchor="middle" class="axis-label">${{dataset.y_label}}</text>`);
        targetSvg.innerHTML = items.join('');
      }};

      const compileShader = (type, source) => {{
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
        return shader;
      }};
      const program = gl.createProgram();
      gl.attachShader(program, compileShader(gl.VERTEX_SHADER, `
        attribute vec3 a_position;
        attribute vec4 a_color;
        varying vec4 v_color;
        void main() {{
          gl_Position = vec4(a_position, 1.0);
          v_color = a_color;
        }}
      `));
      gl.attachShader(program, compileShader(gl.FRAGMENT_SHADER, `
        precision mediump float;
        varying vec4 v_color;
        void main() {{
          gl_FragColor = v_color;
        }}
      `));
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
      const vertexBuffer = gl.createBuffer();
      const positionLocation = gl.getAttribLocation(program, 'a_position');
      const colorLocation = gl.getAttribLocation(program, 'a_color');

      const resizeCanvases = () => {{
        const rect = glCanvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const pixelWidth = Math.max(1, Math.floor(rect.width * dpr));
        const pixelHeight = Math.max(1, Math.floor(rect.height * dpr));
        if (glCanvas.width !== pixelWidth || glCanvas.height !== pixelHeight) {{
          glCanvas.width = pixelWidth;
          glCanvas.height = pixelHeight;
          labelCanvas.width = pixelWidth;
          labelCanvas.height = pixelHeight;
          gl.viewport(0, 0, pixelWidth, pixelHeight);
        }}
        return {{ width: pixelWidth, height: pixelHeight, dpr }};
      }};

      const mat4Multiply = (a, b) => {{
        const out = new Array(16).fill(0);
        for (let col = 0; col < 4; col += 1) {{
          for (let row = 0; row < 4; row += 1) {{
            out[col * 4 + row] =
              a[0 * 4 + row] * b[col * 4 + 0] +
              a[1 * 4 + row] * b[col * 4 + 1] +
              a[2 * 4 + row] * b[col * 4 + 2] +
              a[3 * 4 + row] * b[col * 4 + 3];
          }}
        }}
        return out;
      }};
      const perspective = (fovy, aspect, near, far) => {{
        const f = 1 / Math.tan(fovy / 2);
        const nf = 1 / (near - far);
        return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, (2 * far * near) * nf, 0];
      }};
      const normalize3 = (v) => {{
        const len = Math.hypot(v[0], v[1], v[2]) || 1;
        return [v[0] / len, v[1] / len, v[2] / len];
      }};
      camera.orientation = quatFromEulerCamera();
      const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
      const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
      const lookAt = (eye, center, up) => {{
        const z = normalize3([eye[0] - center[0], eye[1] - center[1], eye[2] - center[2]]);
        const x = normalize3(cross(up, z));
        const y = cross(z, x);
        return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, eye), -dot(y, eye), -dot(z, eye), 1];
      }};
      const transformPoint = (matrix, point) => {{
        const [x, y, z] = point;
        return [
          matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
          matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
          matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
          matrix[3] * x + matrix[7] * y + matrix[11] * z + matrix[15],
        ];
      }};
      const cameraMatrix = (width, height) => {{
        let offset;
        let up;
        if (camera.mode === 'quaternion') {{
          camera.orientation = camera.orientation || quatFromEulerCamera();
          offset = quatRotate(camera.orientation, [0, 0, camera.distance]);
          up = quatRotate(camera.orientation, [0, 1, 0]);
        }} else {{
          const cp = Math.cos(camera.pitch);
          offset = [
            Math.sin(camera.yaw) * cp * camera.distance,
            Math.sin(camera.pitch) * camera.distance,
            Math.cos(camera.yaw) * cp * camera.distance,
          ];
          up = [0, 1, 0];
        }}
        const eye = [
          camera.target[0] + offset[0],
          camera.target[1] + offset[1],
          camera.target[2] + offset[2],
        ];
        return mat4Multiply(perspective(Math.PI / 4, width / height, 0.05, 80), lookAt(eye, camera.target, up));
      }};
      const project = (matrix, point, width, height) => {{
        const clip = transformPoint(matrix, point);
        const w = clip[3] || 1;
        const ndc = [clip[0] / w, clip[1] / w, clip[2] / w];
        return {{ ndc, screen: [(ndc[0] * 0.5 + 0.5) * width, (-ndc[1] * 0.5 + 0.5) * height] }};
      }};
      const hexToRgb = (hex) => {{
        const clean = hex.replace('#', '');
        return [parseInt(clean.slice(0, 2), 16) / 255, parseInt(clean.slice(2, 4), 16) / 255, parseInt(clean.slice(4, 6), 16) / 255];
      }};
      const volumeFillColorsForSegment = (breath, startPoint, endPoint, segmentIndex) => {{
        if (volumeFillPattern === 'phase') {{
          return volumeFillPhasePresets[Math.round(startPoint[4])] || volumeFillPhasePresets[2];
        }}
        if (volumeFillPattern === 'breath') {{
          const rgb = hexToRgb(breath.color);
          return {{ top: [rgb[0], rgb[1], rgb[2], 0.30], base: [rgb[0], rgb[1], rgb[2], 0.04] }};
        }}
        return volumeFillGradientPresets[volumeFillPattern] || volumeFillGradientPresets.amber;
      }};
      const pushVertex = (vertices, position, color) => vertices.push(position[0], position[1], position[2], color[0], color[1], color[2], color[3]);
      const drawVertices = (mode, vertices) => {{
        if (!vertices.length) return;
        gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.DYNAMIC_DRAW);
        gl.useProgram(program);
        gl.enableVertexAttribArray(positionLocation);
        gl.enableVertexAttribArray(colorLocation);
        gl.vertexAttribPointer(positionLocation, 3, gl.FLOAT, false, 28, 0);
        gl.vertexAttribPointer(colorLocation, 4, gl.FLOAT, false, 28, 12);
        gl.drawArrays(mode, 0, vertices.length / 7);
      }};
      const addLine = (vertices, matrix, start, end, color) => {{
        const a = project(matrix, start, glCanvas.width, glCanvas.height).ndc;
        const b = project(matrix, end, glCanvas.width, glCanvas.height).ndc;
        pushVertex(vertices, a, color);
        pushVertex(vertices, b, color);
      }};
      const addRibbon = (vertices, matrix, start, end, widthPx, color) => {{
        const a = project(matrix, start, glCanvas.width, glCanvas.height);
        const b = project(matrix, end, glCanvas.width, glCanvas.height);
        const dx = b.screen[0] - a.screen[0];
        const dy = b.screen[1] - a.screen[1];
        const len = Math.hypot(dx, dy);
        if (len < 0.01) return;
        const halfX = (-dy / len) * widthPx * 0.5 / glCanvas.width * 2;
        const halfY = (-dx / len) * widthPx * 0.5 / glCanvas.height * 2;
        const z = (a.ndc[2] + b.ndc[2]) * 0.5;
        const p0 = [a.ndc[0] - halfX, a.ndc[1] - halfY, z];
        const p1 = [a.ndc[0] + halfX, a.ndc[1] + halfY, z];
        const p2 = [b.ndc[0] - halfX, b.ndc[1] - halfY, z];
        const p3 = [b.ndc[0] + halfX, b.ndc[1] + halfY, z];
        pushVertex(vertices, p0, color);
        pushVertex(vertices, p1, color);
        pushVertex(vertices, p2, color);
        pushVertex(vertices, p2, color);
        pushVertex(vertices, p1, color);
        pushVertex(vertices, p3, color);
      }};
      const addVolumeFill = (vertices, matrix, startPoint, endPoint, baselineCoordinate, topColor, baseColor) => {{
        const startTop = normalizedPoint(startPoint);
        const endTop = normalizedPoint(endPoint);
        const startBase = volumeBaselinePoint(startPoint, baselineCoordinate);
        const endBase = volumeBaselinePoint(endPoint, baselineCoordinate);
        if (!startBase || !endBase) return;
        const p0 = project(matrix, startTop, glCanvas.width, glCanvas.height).ndc;
        const p1 = project(matrix, endTop, glCanvas.width, glCanvas.height).ndc;
        const p2 = project(matrix, startBase, glCanvas.width, glCanvas.height).ndc;
        const p3 = project(matrix, endBase, glCanvas.width, glCanvas.height).ndc;
        pushVertex(vertices, p0, topColor);
        pushVertex(vertices, p1, topColor);
        pushVertex(vertices, p2, baseColor);
        pushVertex(vertices, p2, baseColor);
        pushVertex(vertices, p1, topColor);
        pushVertex(vertices, p3, baseColor);
      }};
      const buildGridVertices = (matrix) => {{
        const vertices = [];
        for (let i = 0; i <= 10; i += 1) {{
          const value = -1 + i * 0.2;
          addLine(vertices, matrix, [-1, value, -1], [1, value, -1], [0.50, 0.57, 0.63, 0.28]);
          addLine(vertices, matrix, [value, -1, -1], [value, 1, -1], [0.50, 0.57, 0.63, 0.28]);
          addLine(vertices, matrix, [-1, -1, value], [1, -1, value], [0.50, 0.57, 0.63, 0.18]);
          addLine(vertices, matrix, [value, -1, -1], [value, -1, 1], [0.50, 0.57, 0.63, 0.18]);
        }}
        addLine(vertices, matrix, [-1, -1, -1], [1, -1, -1], [...variableColors[xAxisVariable], 1]);
        addLine(vertices, matrix, [-1, -1, -1], [-1, 1, -1], [...variableColors[yAxisVariable], 1]);
        addLine(vertices, matrix, [-1, -1, -1], [-1, -1, 1], [...variableColors[zAxisVariable], 1]);
        return vertices;
      }};
      const buildTrajectoryVertices = (matrix) => {{
        const vertices = [];
        const revealTime = traceAnimation.active
          ? (traceAnimation.timeDomain === 'normalized' ? normalizedTimeToRaw(traceAnimation.currentNormalizedTime) : traceAnimation.currentDataTime)
          : data.maxs.time;
        for (const breath of data.breaths) {{
          const rgb = hexToRgb(breath.color);
          const color = [rgb[0], rgb[1], rgb[2], 0.74];
          for (let index = 0; index < breath.points.length - 1; index += 1) {{
            const startPoint = breath.points[index];
            const endPoint = breath.points[index + 1];
            const startTime = pointValue(startPoint, 'time');
            const endTime = pointValue(endPoint, 'time');
            if (startTime > revealTime) continue;
            let visibleEndPoint = endPoint;
            if (endTime > revealTime) {{
              const span = endTime - startTime || 1;
              visibleEndPoint = interpolatePoint(startPoint, endPoint, Math.max(0, Math.min(1, (revealTime - startTime) / span)));
            }}
            addRibbon(vertices, matrix, normalizedPoint(startPoint), normalizedPoint(visibleEndPoint), blendedThickness(startPoint, visibleEndPoint), color);
          }}
        }}
        return vertices;
      }};
      const buildVolumeFillVertices = (matrix) => {{
        const vertices = [];
        if (volumeAxisIndex() < 0) return vertices;
        const revealTime = traceAnimation.active
          ? (traceAnimation.timeDomain === 'normalized' ? normalizedTimeToRaw(traceAnimation.currentNormalizedTime) : traceAnimation.currentDataTime)
          : data.maxs.time;
        for (const breath of data.breaths) {{
          const baselineCoordinate = volumeBaselineCoordinate(breath);
          for (let index = 0; index < breath.points.length - 1; index += 1) {{
            const startPoint = breath.points[index];
            const endPoint = breath.points[index + 1];
            const startTime = pointValue(startPoint, 'time');
            const endTime = pointValue(endPoint, 'time');
            if (startTime > revealTime) continue;
            let visibleEndPoint = endPoint;
            if (endTime > revealTime) {{
              const span = endTime - startTime || 1;
              visibleEndPoint = interpolatePoint(startPoint, endPoint, Math.max(0, Math.min(1, (revealTime - startTime) / span)));
            }}
            const fillColors = volumeFillColorsForSegment(breath, startPoint, visibleEndPoint, index);
            addVolumeFill(vertices, matrix, startPoint, visibleEndPoint, baselineCoordinate, fillColors.top, fillColors.base);
          }}
        }}
        return vertices;
      }};
      const renderLabels = (matrix) => {{
        const ctx = labelCanvas.getContext('2d');
        ctx.clearRect(0, 0, labelCanvas.width, labelCanvas.height);
        ctx.font = `${{13 * (window.devicePixelRatio || 1)}}px sans-serif`;
        ctx.fillStyle = '#1f2933';
        ctx.fillText(`VentWaveforms WebGL Explorer v1.4 High Thickness`, 16, 26 * (window.devicePixelRatio || 1));
        const [minThickness, maxThickness] = thicknessRange();
        ctx.fillText(`Axes: ${{variableLabels[xAxisVariable]}} / ${{variableLabels[yAxisVariable]}} / ${{variableLabels[zAxisVariable]}}    Thickness: ${{variableLabels[thicknessVariable]}} ${{minThickness.toFixed(1)}}-${{maxThickness.toFixed(1)}}px    Rotation: ${{camera.mode === 'quaternion' ? 'Quaternion' : 'Euler'}}    Grid: ${{dataScale === 'normalized' ? 'Normalized 0-1' : 'Raw values'}}    Fill: ${{volumeFillPatternInput.options[volumeFillPatternInput.selectedIndex].text}}`, 16, 48 * (window.devicePixelRatio || 1));
        if (traceAnimation.active) {{
          const elapsed = traceAnimation.timeDomain === 'normalized' ? traceAnimation.currentNormalizedTime : traceAnimation.currentDataTime - traceAnimation.startDataTime;
          const duration = traceAnimation.timeDomain === 'normalized' ? 1 : traceAnimation.endDataTime - traceAnimation.startDataTime;
          const label = traceAnimation.timeDomain === 'normalized' ? 'fast replay' : 'real-time replay';
          const suffix = traceAnimation.timeDomain === 'normalized' ? ' fast' : 's';
          ctx.fillText(`Trace ${{label}}: ${{elapsed.toFixed(2)}}${{suffix}} / ${{duration.toFixed(2)}}${{suffix}}`, 16, 70 * (window.devicePixelRatio || 1));
        }}
        const tickLabels = [
          [[1.08, -1, -1], variableLabels[xAxisVariable]],
          [[-1, 1.08, -1], variableLabels[yAxisVariable]],
          [[-1, -1, 1.08], variableLabels[zAxisVariable]],
        ];
        for (const [position, label] of tickLabels) {{
          const projected = project(matrix, position, labelCanvas.width, labelCanvas.height).screen;
          ctx.fillText(label, projected[0], projected[1]);
        }}
        ctx.fillStyle = '#52616b';
        for (let i = 0; i <= 4; i += 1) {{
          const n = -1 + i * 0.5;
          const unit = (n + 1) / 2;
          const labels = [
            [[n, -1.08, -1], gridTickLabel(xAxisVariable, unit)],
            [[-1.08, n, -1], gridTickLabel(yAxisVariable, unit)],
            [[-1, -1.08, n], gridTickLabel(zAxisVariable, unit)],
          ];
          for (const [position, label] of labels) {{
            const projected = project(matrix, position, labelCanvas.width, labelCanvas.height).screen;
            ctx.fillText(label, projected[0], projected[1]);
          }}
        }}
      }};
      const renderWebGlScene = () => {{
        const size = resizeCanvases();
        const matrix = cameraMatrix(size.width, size.height);
        gl.clearColor(0.972, 0.984, 1.0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        drawVertices(gl.TRIANGLES, buildVolumeFillVertices(matrix));
        drawVertices(gl.LINES, buildGridVertices(matrix));
        drawVertices(gl.TRIANGLES, buildTrajectoryVertices(matrix));
        renderLabels(matrix);
      }};
      const draw = () => {{
        const selectedBreath = breathFilter.value === 'all' ? null : Number(breathFilter.value);
        renderWebGlScene();
        renderLoop(pvSvg, pvData, selectedBreath);
        renderLoop(fvSvg, fvData, selectedBreath);
        renderLoop(pfSvg, pfData, selectedBreath);
        document.querySelectorAll('tbody tr[data-breath]').forEach((row) => {{
          row.style.display = selectedBreath === null || Number(row.dataset.breath) === selectedBreath ? '' : 'none';
        }});
      }};
      const animateThicknessChange = (nextVariable) => {{
        const token = ++thicknessAnimationToken;
        renderedThicknessVariable = thicknessVariable;
        thicknessVariable = nextVariable;
        const start = performance.now();
        const step = (now) => {{
          if (token !== thicknessAnimationToken) return;
          thicknessBlend = Math.min(1, (now - start) / 1000);
          draw();
          if (thicknessBlend < 1) {{
            requestAnimationFrame(step);
          }} else {{
            renderedThicknessVariable = thicknessVariable;
          }}
        }};
        requestAnimationFrame(step);
      }};
      const easeInOut = (t) => t * t * (3 - 2 * t);
      const resetCameraHome = () => {{
        camera.yaw = -0.72;
        camera.pitch = 0.52;
        camera.orientation = quatFromEulerCamera();
        camera.distance = 4.2;
        camera.target = [0, 0, 0];
        draw();
      }};
      const stepCamera = (name) => {{
        if (name === 'iso') {{
          resetCameraHome();
          return;
        }}
        const stepDef = cameraSteps[name];
        if (!stepDef) return;
        const token = ++cameraAnimationToken;
        const startYaw = camera.yaw;
        const startPitch = camera.pitch;
        const yawDelta = stepDef.yaw;
        const pitchDelta = stepDef.pitch;
        const startOrientation = camera.orientation || quatFromEulerCamera();
        const pitchAxis = quatRotate(startOrientation, [1, 0, 0]);
        const yawStep = quatFromAxisAngle([0, 1, 0], yawDelta);
        const pitchStep = quatFromAxisAngle(pitchAxis, -pitchDelta);
        const targetOrientation = quatMultiply(yawStep, quatMultiply(pitchStep, startOrientation));
        const start = performance.now();
        const durationMs = 180;
        const animateStep = (now) => {{
          if (token !== cameraAnimationToken) return;
          const t = Math.min(1, (now - start) / durationMs);
          const eased = easeInOut(t);
          if (camera.mode === 'quaternion') {{
            camera.orientation = quatSlerp(startOrientation, targetOrientation, eased);
          }} else {{
            camera.yaw = startYaw + yawDelta * eased;
            camera.pitch = startPitch + pitchDelta * eased;
            normalizeCameraAngles();
          }}
          draw();
          if (t < 1) requestAnimationFrame(animateStep);
        }};
        requestAnimationFrame(animateStep);
      }};
      const updateTraceAnimationStatus = () => {{
        if (!traceAnimation.active) {{
          traceAnimationStatus.textContent = `Full trace shown. Replay: ${{traceAnimation.timeDomain === 'normalized' ? 'fast 1s' : 'real time'}}. Grid: ${{dataScale === 'normalized' ? 'normalized 0-1' : 'raw values'}}.`;
          return;
        }}
        if (traceAnimation.timeDomain === 'normalized') {{
          traceAnimationStatus.textContent = `Fast replay ${{traceAnimation.currentNormalizedTime.toFixed(3)}} / 1.000`;
        }} else {{
          const elapsed = traceAnimation.currentDataTime - traceAnimation.startDataTime;
          const duration = traceAnimation.endDataTime - traceAnimation.startDataTime;
          traceAnimationStatus.textContent = `Real-time replay ${{elapsed.toFixed(2)}}s / ${{duration.toFixed(2)}}s`;
        }}
      }};
      const stopTraceAnimation = (showFullTrace = true) => {{
        traceAnimation.active = false;
        traceAnimation.frameToken += 1;
        traceAnimationToggle.textContent = 'Animate Time';
        traceAnimationToggle.setAttribute('aria-pressed', 'false');
        if (showFullTrace) {{
          traceAnimation.currentDataTime = traceAnimation.endDataTime;
          traceAnimation.currentNormalizedTime = 1;
        }}
        updateTraceAnimationStatus();
        draw();
      }};
      const startTraceAnimation = () => {{
        traceAnimation.active = true;
        traceAnimation.frameToken += 1;
        const token = traceAnimation.frameToken;
        traceAnimation.startWallTime = performance.now();
        traceAnimation.currentDataTime = traceAnimation.startDataTime;
        traceAnimation.currentNormalizedTime = 0;
        traceAnimationToggle.textContent = 'Stop Animation';
        traceAnimationToggle.setAttribute('aria-pressed', 'true');
        const stepTrace = (now) => {{
          if (!traceAnimation.active || token !== traceAnimation.frameToken) return;
          const elapsedSeconds = (now - traceAnimation.startWallTime) / 1000;
          if (traceAnimation.timeDomain === 'normalized') {{
            traceAnimation.currentNormalizedTime = Math.min(1, elapsedSeconds);
            traceAnimation.currentDataTime = normalizedTimeToRaw(traceAnimation.currentNormalizedTime);
          }} else {{
            traceAnimation.currentDataTime = Math.min(traceAnimation.endDataTime, traceAnimation.startDataTime + elapsedSeconds);
            traceAnimation.currentNormalizedTime = rawTimeToNormalized(traceAnimation.currentDataTime);
          }}
          updateTraceAnimationStatus();
          draw();
          if ((traceAnimation.timeDomain === 'normalized' && traceAnimation.currentNormalizedTime < 1) || (traceAnimation.timeDomain === 'raw' && traceAnimation.currentDataTime < traceAnimation.endDataTime)) {{
            requestAnimationFrame(stepTrace);
          }} else {{
            stopTraceAnimation(true);
          }}
        }};
        updateTraceAnimationStatus();
        draw();
        requestAnimationFrame(stepTrace);
      }};
      const updateAxes = () => {{
        xAxisVariable = xAxisInput.value;
        yAxisVariable = yAxisInput.value;
        zAxisVariable = zAxisInput.value;
        draw();
      }};
      xAxisInput.addEventListener('change', updateAxes);
      yAxisInput.addEventListener('change', updateAxes);
      zAxisInput.addEventListener('change', updateAxes);
      thicknessInput.addEventListener('change', () => {{
        if (thicknessInput.value !== thicknessVariable) animateThicknessChange(thicknessInput.value);
      }});
      const updateThicknessRange = () => {{
        thicknessMin = Number(thicknessMinInput.value);
        thicknessMax = Number(thicknessMaxInput.value);
        draw();
      }};
      thicknessMinInput.addEventListener('input', updateThicknessRange);
      thicknessMaxInput.addEventListener('input', updateThicknessRange);
      breathFilter.addEventListener('change', draw);
      clearFilterButton.addEventListener('click', () => {{
        breathFilter.value = 'all';
        draw();
      }});
      settingsButton.addEventListener('click', () => {{
        const isOpen = settingsPanel.hidden;
        settingsPanel.hidden = !isOpen;
        settingsButton.setAttribute('aria-expanded', String(isOpen));
      }});
      cameraModeToggle.addEventListener('click', () => {{
        if (camera.mode === 'euler') {{
          camera.orientation = quatFromEulerCamera();
          camera.mode = 'quaternion';
          cameraModeToggle.textContent = 'Quaternion';
          cameraModeToggle.setAttribute('aria-pressed', 'true');
        }} else {{
          camera.orientation = camera.orientation || quatFromEulerCamera();
          syncEulerFromQuaternion();
          camera.mode = 'euler';
          cameraModeToggle.textContent = 'Euler';
          cameraModeToggle.setAttribute('aria-pressed', 'false');
        }}
        draw();
      }});
      traceAnimationToggle.addEventListener('click', () => {{
        if (traceAnimation.active) {{
          stopTraceAnimation(true);
        }} else {{
          startTraceAnimation();
        }}
      }});
      timeDomainToggle.addEventListener('click', () => {{
        if (traceAnimation.active) stopTraceAnimation(true);
        traceAnimation.timeDomain = traceAnimation.timeDomain === 'raw' ? 'normalized' : 'raw';
        timeDomainToggle.textContent = traceAnimation.timeDomain === 'normalized' ? 'Fast replay' : 'Real time';
        timeDomainToggle.setAttribute('aria-pressed', String(traceAnimation.timeDomain === 'normalized'));
        updateTraceAnimationStatus();
        draw();
      }});
      dataScaleToggle.addEventListener('click', () => {{
        dataScale = dataScale === 'raw' ? 'normalized' : 'raw';
        dataScaleToggle.textContent = dataScale === 'normalized' ? 'Normalized 0-1' : 'Raw values';
        dataScaleToggle.setAttribute('aria-pressed', String(dataScale === 'normalized'));
        updateTraceAnimationStatus();
        draw();
      }});
      volumeFillPatternInput.addEventListener('change', () => {{
        volumeFillPattern = volumeFillPatternInput.value;
        draw();
      }});
      ringConnectToggle.addEventListener('click', async () => {{
        try {{
          if (ringControl.connected) {{
            await disconnectRing();
          }} else {{
            await connectRing();
          }}
        }} catch (error) {{
          setRingStatus(`Ring connection failed: ${{error.message}}`);
          ringControl.connected = false;
          ringControl.writeCharacteristic = null;
          updateRingUi();
        }}
      }});
      ringControlToggle.addEventListener('click', () => {{
        setRingActive(!ringControl.active);
        setRingStatus(ringControl.active ? 'Ring control enabled for chart rotation.' : 'Ring connected, chart control paused.');
        applyRingCamera();
      }});
      ringZeroButton.addEventListener('click', () => {{
        ringControl.zeroPose = ringPoseOnly(ringControl.lastMotion);
        setRingStatus(`Zeroed ring at ${{ringControl.zeroPose.rotX}}, ${{ringControl.zeroPose.rotY}}, ${{ringControl.zeroPose.rotZ}}`);
        applyRingCamera();
      }});
      document.querySelectorAll('[data-ring-pose]').forEach((button) => {{
        button.addEventListener('click', () => {{
          const pose = ringControl.poses[button.dataset.ringPose];
          if (!pose) return;
          ringControl.zeroPose = ringPoseOnly(pose);
          setRingStatus(`Using ${{button.textContent}} as zero: ${{pose.rotX}}, ${{pose.rotY}}, ${{pose.rotZ}}`);
          applyRingCamera();
        }});
      }});
      resetCameraButton.addEventListener('click', resetCameraHome);
      document.querySelectorAll('[data-camera-step]').forEach((button) => {{
        button.addEventListener('click', () => stepCamera(button.dataset.cameraStep));
      }});
      glCanvas.addEventListener('contextmenu', (event) => event.preventDefault());
      glCanvas.addEventListener('pointerdown', (event) => {{
        pointer.active = true;
        pointer.button = event.button;
        pointer.lastX = event.clientX;
        pointer.lastY = event.clientY;
        glCanvas.setPointerCapture(event.pointerId);
      }});
      glCanvas.addEventListener('pointermove', (event) => {{
        if (!pointer.active) return;
        const dx = event.clientX - pointer.lastX;
        const dy = event.clientY - pointer.lastY;
        pointer.lastX = event.clientX;
        pointer.lastY = event.clientY;
        if (pointer.button === 2 || event.buttons === 4) {{
          camera.target[0] -= dx * 0.004 * camera.distance;
          camera.target[1] += dy * 0.004 * camera.distance;
        }} else {{
          if (camera.mode === 'quaternion') {{
            camera.orientation = camera.orientation || quatFromEulerCamera();
            const yawDrag = quatFromAxisAngle([0, 1, 0], dx * 0.008);
            const pitchAxis = quatRotate(camera.orientation, [1, 0, 0]);
            const pitchDrag = quatFromAxisAngle(pitchAxis, -dy * 0.008);
            camera.orientation = quatMultiply(yawDrag, quatMultiply(pitchDrag, camera.orientation));
          }} else {{
            camera.yaw += dx * 0.008;
            camera.pitch += dy * 0.008;
            normalizeCameraAngles();
          }}
        }}
        draw();
      }});
      glCanvas.addEventListener('pointerup', () => {{
        pointer.active = false;
      }});
      glCanvas.addEventListener('wheel', (event) => {{
        event.preventDefault();
        camera.distance = Math.max(1.4, Math.min(14, camera.distance * (event.deltaY > 0 ? 1.08 : 0.92)));
        draw();
      }}, {{ passive: false }});
      window.addEventListener('resize', draw);
      updateRingUi();
      draw();
    }})();
  </script>
</body>
</html>
"""
