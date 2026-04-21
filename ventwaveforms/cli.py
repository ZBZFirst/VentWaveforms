"""Command line entry point for rendering captured waveform datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from .archive import archive_generated_html
from .renderer import render_html
from .xlsx_loader import parse_xlsx

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="data.xlsx", help="Path to the XLSX file")
    parser.add_argument(
        "-o",
        "--output",
        default="waveforms.html",
        help="Path to the generated HTML output",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    headers, times, phases, signals = parse_xlsx(input_path)
    document = render_html(headers, times, phases, signals)
    output_path.write_text(document, encoding="utf-8")
    archive_path = archive_generated_html(document, output_path)

    print(f"Wrote {output_path} from {input_path} with {len(times)} samples.")
    if archive_path is not None:
        print(f"Archived version to {archive_path}.")
    return 0
