"""XLSX input adapter for captured ventilator waveform samples."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .constants import NS

def col_letters(cell_ref: str) -> str:
    letters = []
    for ch in cell_ref:
        if ch.isalpha():
            letters.append(ch)
        else:
            break
    return "".join(letters)


def parse_xlsx(path: Path) -> tuple[list[str], list[float], list[int], dict[str, list[float]]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for si in shared_root.findall("a:si", NS):
            shared_strings.append("".join((node.text or "") for node in si.iterfind(".//a:t", NS)))

        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = list(sheet_root.find("a:sheetData", NS).findall("a:row", NS))

    headers: list[str] = []
    time_values: list[float] = []
    phase_values: list[int] = []
    signals = {"data 1": [], "data 2": [], "data 3": []}

    for row_index, row in enumerate(rows):
        values: dict[str, str] = {}
        for cell in row.findall("a:c", NS):
            ref = cell.attrib["r"]
            cell_type = cell.attrib.get("t")
            raw_node = cell.find("a:v", NS)
            raw_value = None if raw_node is None else raw_node.text
            if cell_type == "s" and raw_value is not None:
                raw_value = shared_strings[int(raw_value)]
            if raw_value is not None:
                values[col_letters(ref)] = raw_value

        if row_index == 0:
            headers = [values[key] for key in ["A", "B", "C", "D", "E"]]
            continue

        time_values.append(float(values["A"]))
        phase_values.append(int(float(values["B"])))
        signals["data 1"].append(float(values["C"]))
        signals["data 2"].append(float(values["D"]))
        signals["data 3"].append(float(values["E"]))

    return headers, time_values, phase_values, signals
