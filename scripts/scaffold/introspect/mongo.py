"""Introspección MongoDB.

1. Si la colección tiene un validador `$jsonSchema`, se usa ese (es el contrato declarado).
2. Si no, se infiere el esquema muestreando documentos (`$sample`): por campo, el tipo
   dominante; `nullable` si falta o es null en algún documento.

Sólo campos de primer nivel: subdocumentos y arrays se omiten con aviso. `_id` se ignora
(el recurso generado usa `id` autoincremental).
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any, Iterable

from .model import ColumnInfo, TableInfo

# bsonType de $jsonSchema -> kind
_BSON_KINDS = {
    "string": "string",
    "int": "int",
    "long": "int",
    "double": "float",
    "decimal": "decimal",
    "bool": "bool",
    "date": "datetime",
    "timestamp": "datetime",
    "objectId": "objectid",
    "binData": "unsupported",
    "object": "unsupported",
    "array": "unsupported",
}

def safe_source(url: str) -> str:
    return re.sub(r"//([^:/@]+):[^@]*@", r"//\1:***@", url)


def _client(url: str):
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit(
            "Falta pymongo para introspección MongoDB.\n"
            "  cd backend && ./venv/bin/pip install pymongo\n"
            "  (o todos: ./venv/bin/pip install -r requirements-introspect.txt)"
        ) from exc
    return MongoClient(url, serverSelectionTimeoutMS=5000)


def _database(client, database: str | None):
    if database:
        return client[database]
    try:
        return client.get_default_database()
    except Exception as exc:  # pymongo.errors.ConfigurationError
        raise SystemExit(
            "La URL de Mongo no indica base de datos: usá mongodb://host/<db> o --database <db>"
        ) from exc


def _connection_error(url: str, exc: Exception) -> SystemExit:
    detail = str(exc).strip().splitlines()[0][:300]
    return SystemExit(f"No se pudo conectar a {safe_source(url)}:\n  {detail}")


def list_collections(url: str, database: str | None = None) -> list[str]:
    from pymongo.errors import PyMongoError
    client = _client(url)
    try:
        return sorted(_database(client, database).list_collection_names())
    except PyMongoError as exc:
        raise _connection_error(url, exc) from exc
    finally:
        client.close()


def introspect(url: str, collection: str, *, database: str | None = None,
               sample: int = 200, enum_threshold: int = 0) -> TableInfo:
    client = _client(url)
    from pymongo.errors import PyMongoError
    try:
        db = _database(client, database)
        infos = list(db.list_collections(filter={"name": collection}))
        if not infos:
            available = ", ".join(sorted(db.list_collection_names())[:20])
            raise SystemExit(f"No existe la colección {collection!r}. Disponibles: {available or '(ninguna)'}")
        schema = ((infos[0].get("options") or {}).get("validator") or {}).get("$jsonSchema")
        source = safe_source(url)
        if schema:
            cols, warnings = infer_from_json_schema(schema)
            warnings.insert(0, "esquema tomado del validador $jsonSchema de la colección")
        else:
            docs = list(db[collection].aggregate([{"$sample": {"size": sample}}]))
            cols, warnings = infer_from_docs(docs, enum_threshold=enum_threshold)
            warnings.insert(0, f"esquema inferido de {len(docs)} documento(s) muestreados")
        return TableInfo(name=collection, source=source, columns=cols, warnings=warnings)
    except PyMongoError as exc:
        raise _connection_error(url, exc) from exc
    finally:
        client.close()


# ------------------------------------------------------------------ $jsonSchema


def infer_from_json_schema(schema: dict) -> tuple[list[ColumnInfo], list[str]]:
    warnings: list[str] = []
    required = set(schema.get("required") or [])
    cols: list[ColumnInfo] = []
    for name, prop in (schema.get("properties") or {}).items():
        if name == "_id":
            continue
        raw = prop.get("bsonType", prop.get("type", "string"))
        types = [raw] if isinstance(raw, str) else list(raw)
        nullable = name not in required or "null" in types
        types = [t for t in types if t != "null"] or ["string"]
        if len(types) > 1:
            warnings.append(f"{name}: bsonType múltiple {types}, se usa {types[0]!r}")
        kind = _BSON_KINDS.get(types[0], "unsupported")
        enum_values = [str(v) for v in (prop.get("enum") or []) if v is not None]
        if enum_values and kind == "string":
            kind = "enum"
        cols.append(ColumnInfo(
            name=name, kind=kind, raw_type=f"bsonType={types[0]}", nullable=nullable,
            enum_values=enum_values if kind == "enum" else [],
            # sin maxLength declarado se asume string corto (no textarea)
            max_length=prop.get("maxLength", 0) if kind == "string" else None,
        ))
    return cols, warnings


# --------------------------------------------------------------------- muestreo


def _value_kind(v: Any) -> str:
    # bool antes que int: en Python bool es subclase de int
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "string"
    if isinstance(v, datetime):
        return "datetime"
    tname = type(v).__name__
    if tname == "ObjectId":
        return "objectid"
    if tname in ("Decimal128", "Decimal"):
        return "decimal"
    if tname == "UUID" or (tname == "Binary" and getattr(v, "subtype", None) in (3, 4)):
        return "uuid"
    return "unsupported"  # dict, list, bytes, ...


def infer_from_docs(docs: Iterable[dict], *, enum_threshold: int = 0) -> tuple[list[ColumnInfo], list[str]]:
    """Infiere columnas de una muestra de documentos (función pura, testeable sin servidor).

    `enum_threshold > 0`: un campo string con <= N valores distintos (y al menos 2
    documentos por valor en promedio) se propone como `enum`.
    """
    docs = list(docs)
    warnings: list[str] = []
    if not docs:
        warnings.append("la colección está vacía: no hay campos para inferir")
        return [], warnings

    order: list[str] = []
    kinds: dict[str, Counter] = {}
    present: Counter = Counter()
    nulls: Counter = Counter()
    max_len: dict[str, int] = {}
    distinct: dict[str, set] = {}

    for doc in docs:
        for key, value in doc.items():
            if key == "_id":
                continue
            if key not in kinds:
                order.append(key)
                kinds[key] = Counter()
                distinct[key] = set()
            present[key] += 1
            if value is None:
                nulls[key] += 1
                continue
            k = _value_kind(value)
            kinds[key][k] += 1
            if k == "string":
                max_len[key] = max(max_len.get(key, 0), len(value))
                if len(distinct[key]) <= max(enum_threshold, 0):
                    distinct[key].add(value)

    cols: list[ColumnInfo] = []
    for key in order:
        counter = kinds[key]
        if not counter:
            kind = "string"
            warnings.append(f"{key}: siempre null en la muestra, se asume string")
        elif set(counter) <= {"int", "float"}:
            kind = "float" if "float" in counter else "int"
        elif len(counter) > 1:
            kind = counter.most_common(1)[0][0]
            warnings.append(f"{key}: tipos mezclados {dict(counter)}, se usa {kind!r}")
        else:
            kind = next(iter(counter))

        enum_values: list[str] = []
        if (kind == "string" and enum_threshold > 0
                and 1 < len(distinct[key]) <= enum_threshold
                and counter["string"] >= 2 * len(distinct[key])):
            kind = "enum"
            enum_values = sorted(distinct[key])

        if kind == "unsupported":
            raw = "subdocumento/array"
        else:
            raw = f"muestra={dict(counter)}"
        cols.append(ColumnInfo(
            name=key, kind=kind, raw_type=raw,
            nullable=present[key] < len(docs) or nulls[key] > 0,
            enum_values=enum_values,
            # largo máximo visto: > 255 lo convierte en `text` (ver mapping.TEXT_THRESHOLD)
            max_length=max_len.get(key, 0) if kind == "string" else None,
        ))
    return cols, warnings
