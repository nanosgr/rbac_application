"""Lee la estructura de una tabla/colección externa y la convierte en un spec del scaffold.

Motores: PostgreSQL, MySQL, MariaDB, MSSQL (y SQLite) vía SQLAlchemy; MongoDB vía pymongo.
La tabla externa es sólo fuente de diseño: el recurso generado crea su propia tabla en
la BD de la app.
"""
from __future__ import annotations

from .model import ColumnInfo, TableInfo

__all__ = ["ColumnInfo", "TableInfo", "is_mongo", "introspect", "list_tables"]


def is_mongo(url: str) -> bool:
    return url.split("://", 1)[0].lower() in ("mongodb", "mongodb+srv")


def introspect(url: str, table: str, *, schema: str | None = None, database: str | None = None,
               sample: int = 200, enum_threshold: int = 0) -> TableInfo:
    """Despacha según el esquema de la URL. Los avisos de normalización van en `warnings`."""
    if is_mongo(url):
        from . import mongo
        return mongo.introspect(url, table, database=database, sample=sample,
                                enum_threshold=enum_threshold)
    from . import sql
    url, note = sql.normalize_url(url)
    info = sql.introspect(url, table, schema=schema)
    if note:
        info.warnings.insert(0, note)
    return info


def list_tables(url: str, *, schema: str | None = None, database: str | None = None) -> list[str]:
    if is_mongo(url):
        from . import mongo
        return mongo.list_collections(url, database)
    from . import sql
    return sql.list_tables(sql.normalize_url(url)[0], schema=schema)
