"""Breath-boundary and per-breath waveform analysis."""

from __future__ import annotations

import statistics

def build_phase_segments(times: list[float], phases: list[int]) -> list[dict[str, float | int]]:
    if not times:
        return []

    dt_candidates = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    fallback_dt = statistics.median(dt_candidates) if dt_candidates else 0.0
    segments = []
    start_index = 0

    for index in range(1, len(phases)):
        if phases[index] != phases[start_index]:
            end_time = times[index]
            segments.append(
                {
                    "phase": phases[start_index],
                    "start": times[start_index],
                    "end": end_time,
                }
            )
            start_index = index

    segments.append(
        {
            "phase": phases[start_index],
            "start": times[start_index],
            "end": times[-1] + fallback_dt,
        }
    )
    return segments


def mean_or_none(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def median_or_none(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def analyze_breaths(times: list[float], phases: list[int]) -> dict[str, object]:
    insp_starts: list[float] = []
    insp_ends: list[float] = []

    for index in range(1, len(phases)):
        if phases[index - 1] == 0 and phases[index] == 1:
            insp_starts.append(times[index])
        if phases[index - 1] == 1 and phases[index] == 0:
            insp_ends.append(times[index])

    ti_values: list[float] = []
    te_values: list[float] = []
    cycle_start_values: list[float] = []
    cycle_end_values: list[float] = []
    ie_ratios: list[float] = []

    for index in range(min(len(insp_starts), len(insp_ends))):
        if insp_ends[index] > insp_starts[index]:
            ti_values.append(insp_ends[index] - insp_starts[index])

    for index in range(min(len(insp_starts) - 1, len(insp_ends))):
        te = insp_starts[index + 1] - insp_ends[index]
        if te > 0:
            te_values.append(te)

    for index in range(len(insp_starts) - 1):
        cycle_start_values.append(insp_starts[index + 1] - insp_starts[index])

    for index in range(len(insp_ends) - 1):
        cycle_end_values.append(insp_ends[index + 1] - insp_ends[index])

    for ti, te in zip(ti_values[: len(te_values)], te_values):
        if ti > 0:
            ie_ratios.append(te / ti)

    duration = times[-1] - times[0] if times else 0.0
    dt_values = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    median_dt = statistics.median(dt_values) if dt_values else 0.0
    error_samples = sum(1 for phase in phases if phase == 2)
    error_segments = sum(1 for i in range(1, len(phases)) if phases[i - 1] != 2 and phases[i] == 2)

    return {
        "breath_count_1_to_0": len(insp_ends),
        "inspiration_start_count_0_to_1": len(insp_starts),
        "complete_cycles": max(0, min(len(insp_starts) - 1, len(insp_ends))),
        "respiratory_rate_bpm_from_breath_count": (len(insp_ends) / duration * 60.0) if duration else None,
        "respiratory_rate_bpm_from_cycle_mean": (60.0 / statistics.mean(cycle_end_values)) if cycle_end_values else None,
        "inspiratory_time_s_mean": mean_or_none(ti_values),
        "inspiratory_time_s_median": median_or_none(ti_values),
        "expiratory_time_s_mean": mean_or_none(te_values),
        "expiratory_time_s_median": median_or_none(te_values),
        "e_to_i_ratio_mean": mean_or_none(ie_ratios),
        "e_to_i_ratio_median": median_or_none(ie_ratios),
        "i_to_e_ratio_mean": mean_or_none([1.0 / ratio for ratio in ie_ratios if ratio > 0]),
        "i_to_e_ratio_median": median_or_none([1.0 / ratio for ratio in ie_ratios if ratio > 0]),
        "cycle_time_s_mean_from_1_to_0": mean_or_none(cycle_end_values),
        "cycle_time_s_median_from_1_to_0": median_or_none(cycle_end_values),
        "cycle_time_s_mean_from_0_to_1": mean_or_none(cycle_start_values),
        "cycle_time_s_median_from_0_to_1": median_or_none(cycle_start_values),
        "error_sample_count": error_samples,
        "error_segment_count": error_segments,
        "error_time_s_estimate": error_samples * median_dt,
        "breath_end_times_s": insp_ends,
        "inspiration_start_times_s": insp_starts,
    }


def build_breath_rows(
    times: list[float],
    phases: list[int],
    signals: dict[str, list[float]],
) -> list[dict[str, float | int | None]]:
    flow = signals["data 1"]
    pressure = signals["data 2"]
    volume = signals["data 3"]

    start_indices: list[int] = []
    end_indices: list[int] = []
    for index in range(1, len(phases)):
        if phases[index - 1] == 0 and phases[index] == 1:
            start_indices.append(index)
        if phases[index - 1] == 1 and phases[index] == 0:
            end_indices.append(index)

    breath_rows: list[dict[str, float | int | None]] = []
    for breath_number, (start_idx, end_idx) in enumerate(zip(start_indices, end_indices), start=1):
        if end_idx <= start_idx:
            continue

        next_start_idx = start_indices[breath_number] if breath_number < len(start_indices) else len(times) - 1
        insp_flow = flow[start_idx:end_idx]
        insp_pressure = pressure[start_idx:end_idx]
        cycle_pressure = pressure[start_idx:next_start_idx]
        exp_pressure = pressure[end_idx:next_start_idx]
        cycle_volume = volume[start_idx:next_start_idx]
        exp_flow = flow[end_idx:next_start_idx]

        ti = times[end_idx] - times[start_idx]
        te = times[next_start_idx] - times[end_idx] if next_start_idx > end_idx and breath_number < len(start_indices) else None
        total = times[next_start_idx] - times[start_idx] if next_start_idx > start_idx and breath_number < len(start_indices) else None

        breath_rows.append(
            {
                "breath": breath_number,
                "t_start": times[start_idx],
                "t_end": times[end_idx],
                "ti": ti,
                "te": te,
                "t_total": total,
                "i_to_e": (ti / te) if te and te > 0 else None,
                "peak_flow_insp": max(insp_flow) if insp_flow else None,
                "peak_flow_exp": min(exp_flow) if exp_flow else None,
                "pip": max(insp_pressure) if insp_pressure else None,
                "peep_est": min(exp_pressure) if exp_pressure else None,
                "pressure_min": min(cycle_pressure) if cycle_pressure else None,
                "pressure_max": max(cycle_pressure) if cycle_pressure else None,
                "volume_start": volume[start_idx],
                "volume_end_insp": volume[end_idx - 1],
                "volume_delta_insp": volume[end_idx - 1] - volume[start_idx],
                "tidal_volume_est": (max(cycle_volume) - min(cycle_volume)) if cycle_volume else None,
            }
        )

    return breath_rows


def build_breath_slices(phases: list[int], times: list[float]) -> list[dict[str, int | float | None]]:
    start_indices: list[int] = []
    end_indices: list[int] = []
    for index in range(1, len(phases)):
        if phases[index - 1] == 0 and phases[index] == 1:
            start_indices.append(index)
        if phases[index - 1] == 1 and phases[index] == 0:
            end_indices.append(index)

    slices = []
    for breath_number, (start_idx, end_idx) in enumerate(zip(start_indices, end_indices), start=1):
        if end_idx <= start_idx:
            continue
        next_start_idx = start_indices[breath_number] if breath_number < len(start_indices) else len(times) - 1
        slices.append(
            {
                "breath": breath_number,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "next_start_idx": next_start_idx,
                "t_start": times[start_idx],
                "t_end": times[end_idx],
                "t_next": times[next_start_idx] if next_start_idx < len(times) else None,
            }
        )
    return slices
