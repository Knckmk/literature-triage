from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from models import PaperMetadata


def write_jsonl(path, records: Iterable[PaperMetadata | Mapping[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            payload = asdict(record) if is_dataclass(record) else dict(record)
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path) -> list[PaperMetadata]:
    input_path = Path(path)
    if not input_path.exists():
        return []

    papers: list[PaperMetadata] = []
    field_names = PaperMetadata.__dataclass_fields__.keys()
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            filtered = {key: payload[key] for key in field_names if key in payload}
            papers.append(PaperMetadata(**filtered))
    return papers
