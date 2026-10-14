"""Introspección SQL (PostgreSQL, MySQL, MariaDB, MSSQL, SQLite) vía `sqlalchemy.inspect`.

Un único camino para todos los motores: el inspector de SQLAlchemy ya normaliza los
tipos a sus clases genéricas (`sa.Integer`, `sa.String`, `sa.Enum`, ...). Acá sólo
se los clasifica en un `kind` (ver `model.KINDS`).
"""
from __future__ import annotations

import re
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import make_url

from .model import ColumnInfo, TableInfo

# esquema de URL sin driver -> driver que documentamos en requirements-introspect.txt
_DEFAULT_DRIVERS = {
    "mysql": "mysql+pymysql",
    "mariadb": "mariadb+pymysql",
    "mssql": "mssql+pymssql",
    "postgres": "postgresql+psycopg2",
    "postgresql": "postgresql+psycopg2",
}

# driver -> paquete pip
_DRIVER_PACKAGES = {
    "pymysql": "PyMySQL",
    "pymssql": "pymssql",
    "pyodbc": "pyodbc",
    "psycopg2": "psycopg2-binary",
    "mysqldb": "mysqlclient",
}


def normalize_url(url: str) -> tuple[str, str | None]:
    """Completa el driver si la URL no lo trae. Devuelve `(url, aviso | None)`."""
    scheme, sep, rest = url.partition("://")
    if not sep or "+" in scheme:
        return url, None
    target = _DEFAULT_DRIVERS.get(scheme.lower())
    if target is None:
        return url, None
    return f"{target}://{rest}", f"URL sin driver: se usa {target}"


def safe_source(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:  # noqa: BLE001 — sólo para mensajes
        return re.sub(r"//([^:/@]+):[^@]*@", r"//\1:***@", url)


def create_engine(url: str) -> sa.Engine:
    try:
        return sa.create_engine(url)
    except (ImportError, sa.exc.NoSuchModuleError) as exc:
        drivername = make_url(url).drivername
        driver = drivername.split("+", 1)[1] if "+" in drivername else drivername
        pkg = _DRIVER_PACKAGES.get(driver, driver)
        raise SystemExit(
            f"Falta el driver para {drivername!r} ({exc}).\n"
            f"  cd backend && ./venv/bin/pip install {pkg}\n"
            f"  (o todos: ./venv/bin/pip install -r requirements-introspect.txt)"
        ) from exc


def _connection_error(url: str, exc: Exception) -> SystemExit:
    detail = str(getattr(exc, "orig", None) or exc).strip().splitlines()[0]
    return SystemExit(f"No se pudo conectar a {safe_source(url)}:\n  {detail}")


def list_tables(url: str, schema: str | None = None) -> list[str]:
    engine = create_engine(url)
    try:
        insp = sa.inspect(engine)
        return sorted(insp.get_table_names(schema=schema))
    except sa.exc.DBAPIError as exc:
        raise _connection_error(url, exc) from exc
    finally:
        engine.dispose()


def introspect(url: str, table: str, schema: str | None = None) -> TableInfo:
    engine = create_engine(url)
    try:
        insp = sa.inspect(engine)
        if not insp.has_table(table, schema=schema):
            available = ", ".join(sorted(insp.get_table_names(schema=schema))[:20])
            raise SystemExit(f"No existe la tabla {table!r}. Disponibles: {available or '(ninguna)'}")
        return _read_table(insp, table, schema, source=safe_source(url))
    except sa.exc.DBAPIError as exc:
        raise _connection_error(url, exc) from exc
    finally:
        engine.dispose()


def _read_table(insp, table: str, schema: str | None, *, source: str) -> TableInfo:
    warnings: list[str] = []
    pk_cols = set((insp.get_pk_constraint(table, schema=schema) or {}).get("constrained_columns") or [])

    fks: dict[str, str] = {}
    for fk in insp.get_foreign_keys(table, schema=schema):
        cols, refs = fk.get("constrained_columns") or [], fk.get("referred_columns") or []
        for col, ref in zip(cols, refs):
            fks[col] = f"{fk.get('referred_table')}.{ref}"

    try:
        checks = insp.get_check_constraints(table, schema=schema)
    except NotImplementedError:
        checks = []
        warnings.append("el dialecto no expone CHECK constraints: no se infieren enums por CHECK")

    columns: list[ColumnInfo] = []
    for c in insp.get_columns(table, schema=schema):
        name = c["name"]
        kind, max_length, enum_values = classify_type(c["type"])
        if kind in ("string", "int") and not enum_values:
            check_values = _enum_from_checks(name, checks)
            if check_values:
                kind, enum_values = "enum", check_values
        columns.append(ColumnInfo(
            name=name,
            kind=kind,
            raw_type=_type_label(c["type"]),
            nullable=bool(c.get("nullable", True)),
            default=parse_server_default(c.get("default"), kind),
            is_pk=name in pk_cols,
            fk_target=fks.get(name),
            enum_values=enum_values,
            max_length=max_length,
        ))
    return TableInfo(name=table, source=source, columns=columns, warnings=warnings)


def _type_label(t: Any) -> str:
    try:
        return str(t)
    except Exception:  # noqa: BLE001 — algunos tipos reflejados no compilan sin dialecto
        return type(t).__name__


def classify_type(t: Any) -> tuple[str, int | None, list[str]]:
    """Tipo SQLAlchemy reflejado -> `(kind, max_length, enum_values)`."""
    name = type(t).__name__.upper()

    if isinstance(t, sa.Enum):
        return "enum", None, [str(v) for v in (t.enums or [])]
    if isinstance(t, sa.Boolean):  # incluye mssql.BIT
        return "bool", None, []
    # MySQL/MariaDB: TINYINT(1) es el booleano de facto
    if name == "TINYINT" and getattr(t, "display_width", None) == 1:
        return "bool", None, []
    if isinstance(t, sa.Integer):
        return "int", None, []
    if isinstance(t, sa.Float):  # antes que Numeric: Float hereda de Numeric
        return "float", None, []
    if isinstance(t, sa.Numeric) or name in ("MONEY", "SMALLMONEY"):
        return "decimal", None, []
    if isinstance(t, sa.DateTime):  # incluye TIMESTAMP, DATETIME2, DATETIMEOFFSET
        return "datetime", None, []
    if isinstance(t, sa.Date):
        return "date", None, []
    if isinstance(t, sa.Uuid) or name in ("UUID", "UNIQUEIDENTIFIER"):
        return "uuid", None, []
    # MySQL LONGTEXT/MEDIUMTEXT/TINYTEXT heredan de String, no de Text
    if isinstance(t, sa.Text) or name.endswith("TEXT"):  # TEXT, NTEXT, LONGTEXT, ...
        return "text", None, []
    if isinstance(t, sa.String):  # VARCHAR, NVARCHAR, CHAR, ...
        return "string", getattr(t, "length", None), []
    return "unsupported", None, []


_IN_RE = re.compile(r"\bIN\s*\(", re.IGNORECASE)
_ANY_RE = re.compile(r"=\s*ANY\s*\(", re.IGNORECASE)
_QUOTED_RE = re.compile(r"'((?:[^']|'')*)'")


def _enum_from_checks(column: str, checks: list[dict]) -> list[str]:
    """Valores de `CHECK (col IN ('a','b'))` o de la forma PostgreSQL `col = ANY (ARRAY[...])`."""
    col_re = re.compile(rf'(?<![\w.])[\["`]?{re.escape(column)}[\]"`]?(?!\w)', re.IGNORECASE)
    for chk in checks:
        text = chk.get("sqltext") or ""
        if not col_re.search(text) or not (_IN_RE.search(text) or _ANY_RE.search(text)):
            continue
        if " AND " in text.upper() or " OR " in text.upper():
            continue  # condiciones compuestas: no adivinar
        values = [v.replace("''", "'") for v in _QUOTED_RE.findall(text)]
        if values:
            return list(dict.fromkeys(values))
    return []


_CAST_RE = re.compile(r"::[\w\s\"\[\]().]+$")
_NOW_RE = re.compile(
    r"^(now\(\)|current_timestamp(\(\))?|getdate\(\)|sysdatetime\(\)|getutcdate\(\)|"
    r"sysutcdatetime\(\)|localtimestamp(\(\))?|statement_timestamp\(\)|"
    r"transaction_timestamp\(\)|clock_timestamp\(\))$",
    re.IGNORECASE,
)
_TODAY_RE = re.compile(r"^(current_date(\(\))?|curdate\(\))$", re.IGNORECASE)


def parse_server_default(raw: Any, kind: str) -> Any:
    """Default de servidor reflejado (texto SQL) -> literal simple, "now"/"today" o None."""
    if raw is None:
        return None
    text = str(raw).strip()
    # MSSQL envuelve en paréntesis: ((0)), ('abc'), (getdate())
    while len(text) >= 2 and text[0] == "(" and text[-1] == ")" and _balanced(text[1:-1]):
        text = text[1:-1].strip()
    text = _CAST_RE.sub("", text).strip()  # PostgreSQL: 'x'::character varying

    if _NOW_RE.match(text):
        return "now" if kind == "datetime" else ("today" if kind == "date" else None)
    if _TODAY_RE.match(text):
        return "today" if kind in ("date", "datetime") else None
    if text.upper() == "NULL" or "(" in text:
        return None  # nextval(...), funciones: no es un literal
    m = re.fullmatch(r"[Nn]?'((?:[^']|'')*)'", text)
    if m:
        return m.group(1).replace("''", "'")
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", text):
        return float(text)
    return None


def _balanced(text: str) -> bool:
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
