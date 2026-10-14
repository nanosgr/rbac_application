"""Mapeo tipo-de-campo -> representaciones en cada capa (Python, TS, SQLAlchemy, form).

Genera los fragmentos de código concretos que las plantillas insertan. Timestamps
(`created_at` / `updated_at`) y `owner_id` NO pasan por acá: son estructurales y los
arman las plantillas directamente.
"""
from __future__ import annotations

from .spec import ResourceField

# tipo -> (ts_type, sa_type, form_input)
_BASE = {
    "string": ("string", "sa.String()", "text"),
    "text": ("string", "sa.String()", "textarea"),
    "int": ("number", "sa.Integer()", "number"),
    "float": ("number", "sa.Float()", "number"),
    "money": ("number", "sa.Float()", "number"),
    "bool": ("boolean", "sa.Boolean()", "checkbox"),
    "enum": ("string", "sa.String()", "select"),
    "date": ("string", "sa.Date()", "date"),
    "datetime": ("string", "sa.DateTime(timezone=True)", "datetime-local"),
}

_NUMERIC = {"int", "float", "money"}
_DATES = {"date", "datetime"}

# tipo -> anotación Python
_PY = {
    "string": "str", "text": "str", "int": "int", "float": "float", "money": "float",
    "bool": "bool", "enum": "str", "date": "date", "datetime": "datetime",
}


def ts_type(f: ResourceField) -> str:
    # una fecha opcional vacía viaja como `null` (el backend no acepta '')
    if f.type in _DATES and f.optional:
        return "string | null"
    return _BASE[f.type][0]


def form_input(f: ResourceField) -> str:
    return _BASE[f.type][2]


def _enum_default(f: ResourceField) -> str:
    val = f.default if f.default is not None else (f.enum_values[0].value if f.enum_values else "")
    return str(val)


# --------------------------------------------------------------------- python


def model_base_line(f: ResourceField) -> str:
    """Línea del campo en `<S>Base` (SQLModel)."""
    if f.type in ("string", "text"):
        return f"{f.name}: str" if not f.optional else f"{f.name}: Optional[str] = None"
    if f.type == "int":
        d = 0 if f.default is None else int(f.default)
        return f"{f.name}: Optional[int] = None" if f.optional else f"{f.name}: int = {d}"
    if f.type in ("float", "money"):
        d = 0.0 if f.default is None else float(f.default)
        return f"{f.name}: Optional[float] = None" if f.optional else f"{f.name}: float = {d}"
    if f.type == "bool":
        d = True if f.default is None else bool(f.default)
        return f"{f.name}: Optional[bool] = None" if f.optional else f"{f.name}: bool = {d}"
    if f.type == "enum":
        if f.default is not None:
            return f'{f.name}: str = {str(f.default)!r}'
        if f.optional:
            return f"{f.name}: Optional[str] = None"
        return f'{f.name}: str = {_enum_default(f)!r}'
    if f.type in _DATES:
        py = _PY[f.type]
        ann = f"Optional[{py}]" if f.optional else py
        if f.default is None:
            return f"{f.name}: {ann} = None" if f.optional else f"{f.name}: {ann}"
        if str(f.default) in ("today", "now"):
            factory = "date.today" if f.type == "date" else "datetime.now"
            return f"{f.name}: {ann} = Field(default_factory={factory})"
        return f"{f.name}: {ann} = {py}.fromisoformat({str(f.default)!r})"
    raise ValueError(f.type)


def dto_update_line(f: ResourceField) -> str:
    """Línea del campo en `<S>Update` (todo Optional[...] = None)."""
    return f"{f.name}: Optional[{_PY[f.type]}] = None"


def py_query_annot(f: ResourceField) -> str:
    """Anotación del filtro en el endpoint `GET /` (siempre opcional)."""
    return f"Optional[{_PY[f.type]}]"


# --------------------------------------------------------------------- alembic


def migration_column(f: ResourceField) -> str:
    ts, sa, _ = _BASE[f.type]
    nullable = "True" if f.optional else "False"
    extra = ""
    if f.type == "enum":
        extra = f", server_default={_enum_default(f)!r}"
    elif f.type == "bool" and not f.optional:
        default = "1" if (f.default is None or bool(f.default)) else "0"
        extra = f", server_default=sa.text(\"'{default}'\")"
    elif f.type == "datetime" and str(f.default) == "now":
        extra = ", server_default=sa.func.now()"
    elif f.type == "date" and str(f.default) == "today":
        extra = ", server_default=sa.func.current_date()"
    return f"sa.Column('{f.name}', {sa}, nullable={nullable}{extra})"


# ------------------------------------------------------------------- typescript


def ts_interface_line(f: ResourceField, *, force_optional: bool = False) -> str:
    opt = "?" if (f.optional or force_optional) else ""
    return f"{f.name}{opt}: {ts_type(f)};"


def ts_create_line(f: ResourceField) -> str:
    # enum siempre opcional en el Create DTO (tiene server_default), como orders.status;
    # una fecha con default (`today`/`now`/ISO) también: si viaja vacía, decide el backend
    has_date_default = f.type in _DATES and f.default is not None
    opt = "?" if (f.optional or f.type == "enum" or has_date_default) else ""
    return f"{f.name}{opt}: {ts_type(f)};"


# ---------------------------------------------------------------- form helpers


def ts_empty_value(f: ResourceField) -> str:
    """Valor inicial del campo en `emptyForm` (frontend)."""
    if f.type in ("string", "text"):
        return "''"
    if f.type in _NUMERIC:
        return "0"
    if f.type == "bool":
        return "true" if (f.default is None or bool(f.default)) else "false"
    if f.type == "enum":
        return f"'{_enum_default(f)}'"
    if f.type in _DATES:
        return "''"
    raise ValueError(f.type)
