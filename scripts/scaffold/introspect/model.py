"""Representación neutral de una columna leída de una BD externa.

Cada backend (`sql.py`, `mongo.py`) traduce sus tipos nativos a un `kind` común;
`mapping.py` decide después qué tipo de campo del spec corresponde a cada `kind`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Clases de tipo que entienden los backends. `unsupported` = no se puede generar.
KINDS = {
    "string", "text", "int", "float", "decimal", "bool", "enum",
    "date", "datetime", "uuid", "objectid", "unsupported",
}


@dataclass
class ColumnInfo:
    name: str
    kind: str
    raw_type: str  # tipo nativo, sólo para mensajes ("VARCHAR(80)", "bsonType=date")
    nullable: bool = True
    # default ya normalizado: literal Python, "now" / "today", o None si no es simple
    default: Any = None
    is_pk: bool = False
    fk_target: str | None = None  # "tabla.columna"
    enum_values: list[str] = field(default_factory=list)
    max_length: int | None = None


@dataclass
class TableInfo:
    name: str
    source: str  # descripción de la conexión, sin contraseña
    columns: list[ColumnInfo]
    warnings: list[str] = field(default_factory=list)
