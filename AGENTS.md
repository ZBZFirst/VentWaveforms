# Agent Notes

VentWaveforms is a local private project under:

`/home/paulwasthere/AndroidStudioProjects/VentWaveforms`

Do not publish, initialize a GitHub remote, or copy this project into another repository unless the user explicitly requests it.

## Project Shape

- `plot_waveforms.py` is a small CLI wrapper.
- `ventwaveforms/xlsx_loader.py` is the current XLSX input adapter for captured RTOS waveform samples.
- `ventwaveforms/analysis.py` contains breath-boundary and per-breath metric logic.
- `ventwaveforms/views.py` builds loop and trajectory view data/markup.
- `ventwaveforms/renderer.py` renders the standalone HTML review page.
- `ventwaveforms/archive.py` manages generated HTML archive copies.
- `data.xlsx` is the current source dataset and is intentionally kept at the project root because the existing scripts default to that path.
- `waveforms.html` is generated output from `plot_waveforms.py` and is also kept at the root because that is the script default.
- `artifacts/html_versions/` contains archived generated HTML versions.

## Working Rules

- Keep source-layout changes conservative unless the user asks for a refactor.
- Treat `data.xlsx`, `waveforms.html`, and archived generated HTML as private local work product.
- Prefer adding tests and validation before changing metric logic.
- If moving files, update `plot_waveforms.py` defaults and documentation in the same change.
- Add new RTOS capture formats as input adapters rather than coupling them to the HTML renderer.
