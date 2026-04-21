# VentWaveforms

Local-only ventilator waveform exploration project.

This project is intentionally private and local. It is not currently a git repository and should not be pushed to GitHub without an explicit review of the source dataset and generated waveform output.

## What is here

- `data.xlsx`: source ventilator waveform dataset used by the parser.
- `plot_waveforms.py`: small CLI wrapper for the renderer.
- `ventwaveforms/xlsx_loader.py`: XLSX adapter for captured waveform samples.
- `ventwaveforms/analysis.py`: breath boundary detection and per-breath metrics.
- `ventwaveforms/views.py`: SVG/WebGL dataset builders for loops and trajectories.
- `ventwaveforms/renderer.py`: standalone HTML page renderer.
- `ventwaveforms/archive.py`: generated HTML archive helper.
- `waveforms.html`: generated standalone waveform visualization.
- `artifacts/html_versions/`: archived generated HTML versions.

## Current status

The core workflow parses the XLSX dataset, computes breath boundaries and respiratory-rate style summaries, and renders waveform, loop, and interactive WebGL trajectory views into a standalone HTML file.

The internal modules now keep the RTOS-capture boundary explicit: loaders convert a captured file into normalized time/phase/signal arrays, analysis computes derived breath metrics, and rendering stays separate from the input format.

Known work still needed:

- Add tests around waveform parsing and breath metric calculations.
- Review metric naming and clinical interpretation before sharing output outside the local workspace.
- Decide whether archived generated HTML versions should remain in the project or be regenerated as needed.

## Run locally

Render the waveform HTML:

```bash
python3 plot_waveforms.py
```

Or render from a different captured dataset/output path:

```bash
python3 plot_waveforms.py path/to/input.xlsx -o path/to/waveforms.html
```

## Local-only guardrail

Before ever initializing git or publishing this project, review:

- `data.xlsx`
- `waveforms.html`
- `artifacts/html_versions/`

Those files may contain private local work product or source data.
