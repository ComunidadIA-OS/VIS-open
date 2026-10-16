"""Lectura y escritura de las tablas de anotación en CSV, con validación."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


def write_rows(rows: Iterable[M], model: type[M], path: Path) -> None:
    columns = list(model.model_fields)
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            data = row.model_dump(mode="json")
            writer.writerow({c: "" if data[c] is None else data[c] for c in columns})


def read_rows(model: type[M], path: Path) -> list[M]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = set(model.model_fields) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"faltan columnas: {sorted(missing)}")
        return [
            model.model_validate({k: (v if v != "" else None) for k, v in raw.items()})
            for raw in reader
        ]
