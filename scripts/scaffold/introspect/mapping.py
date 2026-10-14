"""`TableInfo` -> spec del scaffold (dict) + YAML comentado.

La tabla externa es sólo fuente de diseño: el recurso generado crea su propia tabla
(con `id`, `created_at`, `updated_at` y, si hay scoping, `owner_id`), así que esas
columnas se descartan acá.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import yaml

from .model import ColumnInfo, TableInfo

STRUCTURAL = {"id", "created_at", "updated_at", "owner_id"}

# Por encima de este largo un VARCHAR pasa a `text` (textarea en el form).
TEXT_THRESHOLD = 255


def snake_case(name: str) -> str:
    """`CustomerName` / `customer-name` / `Customer Name` -> `customer_name`."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name.strip())
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    s = re.sub(r"_+", "_", s)
    if not s:
        return "field"
    if s[0].isdigit():
        s = f"f_{s}"
    return s


def singular_plural(table: str) -> tuple[str, str]:
    """Inflexión mínima (inglés/español regulares). Sobrescribible por CLI."""
    base = snake_case(table.split(".")[-1])
    if base.endswith("ies") and len(base) > 3:
        return base[:-3] + "y", base
    if base.endswith(("sses", "xes", "zes", "ches", "shes")):
        return base[:-2], base
    if base.endswith("s") and not base.endswith("ss"):
        return base[:-1], base
    plural = base + ("es" if base.endswith(("s", "x", "z", "ch", "sh")) else "s")
    return base, plural


def humanize(snake: str) -> str:
    words = snake.replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else words


def _field_for(col: ColumnInfo, fname: str, warnings: list[str]) -> dict | None:
    """Un campo del spec, o None si la columna no se puede generar."""
    where = f"{col.name} ({col.raw_type})"
    kind = col.kind
    spec_type: str

    if col.fk_target:
        warnings.append(f"{where}: FK a {col.fk_target}; la relación no se genera, queda como valor plano")

    if kind == "string":
        spec_type = "text" if (col.max_length is None or col.max_length > TEXT_THRESHOLD) else "string"
    elif kind == "text":
        spec_type = "text"
    elif kind in ("uuid", "objectid"):
        spec_type = "string"
        warnings.append(f"{where}: {kind} se genera como string")
    elif kind == "int":
        spec_type = "int"
    elif kind == "float":
        spec_type = "float"
    elif kind == "decimal":
        spec_type = "money"
        warnings.append(f"{where}: decimal se genera como money (float); revisá la precisión")
    elif kind == "bool":
        spec_type = "bool"
    elif kind == "enum":
        spec_type = "enum" if col.enum_values else "string"
        if not col.enum_values:
            warnings.append(f"{where}: enum sin valores legibles, se genera como string")
    elif kind in ("date", "datetime"):
        spec_type = kind
    else:
        warnings.append(f"{where}: tipo no soportado por el scaffold, columna omitida")
        return None

    field: dict[str, Any] = {"name": fname, "type": spec_type, "optional": bool(col.nullable)}

    default = _coerce_default(spec_type, col.default, col.enum_values)
    if default is not None:
        field["default"] = default
    elif col.default is not None:
        warnings.append(f"{where}: default {col.default!r} no es un literal simple, se ignora")

    if spec_type == "enum":
        field["enum_values"] = [{"value": v, "label": humanize(v)} for v in col.enum_values]
        field["filterable"] = True
    return field


def _coerce_default(spec_type: str, value: Any, enum_values: list[str]) -> Any:
    if value is None:
        return None
    if spec_type == "date":
        return value if value == "today" or _is_iso(value, date_only=True) else None
    if spec_type == "datetime":
        return value if value == "now" or _is_iso(value) else None
    if value in ("now", "today"):
        return None
    try:
        if spec_type == "bool":
            if isinstance(value, bool):
                return value
            return {"1": True, "0": False, "true": True, "false": False}.get(str(value).lower())
        if spec_type == "int":
            return int(value)
        if spec_type in ("float", "money"):
            return float(value)
    except (TypeError, ValueError):
        return None
    if spec_type == "enum":
        return str(value) if str(value) in enum_values else None
    if spec_type in ("string", "text"):
        return None  # el scaffold no usa default en strings: se completan en el form
    return None


def _is_iso(value: Any, *, date_only: bool = False) -> bool:
    from datetime import date
    try:
        (date if date_only else datetime).fromisoformat(str(value))
        return True
    except ValueError:
        return False


def table_to_spec(
    table: TableInfo,
    *,
    singular: str | None = None,
    plural: str | None = None,
    label_singular: str | None = None,
    label_plural: str | None = None,
    icon: str | None = None,
    scoping_mode: str = "none",
    dimension: str | None = None,
    form_mode: str = "modal",
) -> tuple[dict, list[str]]:
    """Devuelve `(spec_dict, warnings)`."""
    warnings = list(table.warnings)
    auto_singular, auto_plural = singular_plural(table.name)
    singular = singular or auto_singular
    plural = plural or auto_plural

    pks = [c for c in table.columns if c.is_pk]
    single_pk = pks[0] if len(pks) == 1 else None
    if len(pks) > 1:
        warnings.append(
            f"PK compuesta ({', '.join(c.name for c in pks)}): el recurso usará `id` "
            f"autoincremental; las columnas se conservan como campos"
        )

    fields: list[dict] = []
    seen: set[str] = set()
    for col in table.columns:
        if col is single_pk:
            if col.name != "id":
                warnings.append(f"{col.name}: PK reemplazada por `id` autoincremental")
            continue
        fname = snake_case(col.name)
        if fname in STRUCTURAL:
            warnings.append(f"{col.name}: columna estructural, la genera el scaffold")
            continue
        if fname != col.name:
            warnings.append(f"{col.name}: renombrada a {fname!r} (snake_case)")
        if fname in seen:
            warnings.append(f"{col.name}: nombre {fname!r} duplicado tras normalizar, omitida")
            continue
        field = _field_for(col, fname, warnings)
        if field is not None:
            fields.append(field)
            seen.add(fname)

    spec: dict[str, Any] = {
        "resource": {
            "singular": singular,
            "plural": plural,
            "label_singular": label_singular or humanize(singular),
            "label_plural": label_plural or humanize(plural),
            "icon": icon or "Box",
        },
        "fields": fields,
        "scoping": {"mode": scoping_mode},
        "frontend": {"generate": True, "form_mode": form_mode},
        "docs": {"update_claude_md": True},
    }
    if dimension:
        spec["scoping"]["dimension"] = dimension
    return spec, warnings


# ------------------------------------------------------------------------ yaml


def _flow(value: Any) -> str:
    # se envuelve en lista: un escalar suelto sale con el marcador de fin `...`
    text = yaml.safe_dump([value], default_flow_style=True, allow_unicode=True,
                          sort_keys=False, width=10_000).strip()
    return text[1:-1]


def to_yaml(spec: dict, *, table: TableInfo, warnings: list[str]) -> str:
    """YAML con el mismo estilo que `specs/examples/*.yaml`, con cabecera comentada."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    out = [
        f"# Spec generado por scripts/introspect_table.py el {stamp}",
        f"# Origen: {table.source} -> {table.name}",
        "# Revisalo antes de scaffoldear:",
        f"#   python scripts/scaffold_resource.py --from <este archivo> --dry-run",
    ]
    if warnings:
        out.append("#")
        out.append("# Avisos de la introspección:")
        out += [f"#   - {w}" for w in warnings]
    out.append("")

    r = spec["resource"]
    out.append("resource:")
    for key in ("singular", "plural", "label_singular", "label_plural", "icon"):
        out.append(f"  {key}: {_flow(r[key])}")
    out.append("")

    out.append("fields:")
    for f in spec["fields"]:
        if f["type"] == "enum":
            out.append(f"  - name: {f['name']}")
            for key in ("type", "optional", "default", "filterable"):
                if key in f:
                    out.append(f"    {key}: {_flow(f[key])}")
            out.append("    enum_values:")
            out += [f"      - {_flow(ev)}" for ev in f["enum_values"]]
        else:
            out.append(f"  - {_flow(f)}")
    out.append("")

    for section in ("scoping", "frontend", "docs"):
        out.append(f"{section}:")
        for key, value in spec[section].items():
            out.append(f"  {key}: {_flow(value)}")
        out.append("")
    return "\n".join(out)
