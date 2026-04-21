"""Generated HTML archive helpers."""

from __future__ import annotations

import re
from pathlib import Path

def archive_generated_html(document: str, output_path: Path) -> Path | None:
    title_match = re.search(r"<title>([^<]+)</title>", document)
    if not title_match:
        return None
    title = title_match.group(1).strip()
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    if not slug:
        return None
    archive_dir = output_path.parent / "artifacts" / "html_versions"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{slug}.html"
    archive_path.write_text(document, encoding="utf-8")
    return archive_path
