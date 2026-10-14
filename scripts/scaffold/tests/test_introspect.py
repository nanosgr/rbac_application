"""Tests de la introspección de BD -> spec (scripts/introspect_table.py).

Sin servidores: SQL contra SQLite (mismo `sqlalchemy.inspect`), tipos de cada dialecto
instanciados a mano, y Mongo con las funciones puras de inferencia.
"""
import sqlite3
from datetime import datetime
from decimal import Decimal

import pytest
import sqlalchemy as sa
import yaml
from sqlalchemy.dialects import mssql, mysql, postgresql

from scripts import introspect_table
from scripts.scaffold.introspect import introspect, is_mongo
from scripts.scaffold.introspect.mapping import singular_plural, snake_case, table_to_spec, to_yaml
from scripts.scaffold.introspect.model import ColumnInfo, TableInfo
from scripts.scaffold.introspect.mongo import infer_from_docs, infer_from_json_schema
from scripts.scaffold.introspect.sql import (
    _enum_from_checks, classify_type, normalize_url, parse_server_default, safe_source,
)
from scripts.scaffold.render import build_context, make_env, new_revision_id
from scripts.scaffold.spec import spec_from_dict, validate

DDL = """
CREATE TABLE warehouses (id INTEGER PRIMARY KEY, name VARCHAR(50));
CREATE TABLE Customers (
  CustomerID INTEGER PRIMARY KEY,
  CustomerName VARCHAR(120) NOT NULL,
  notes TEXT,
  credit_limit NUMERIC(12,2) DEFAULT 0,
  rating FLOAT,
  is_active BOOLEAN NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','blocked','vip')),
  birth_date DATE,
  last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
  warehouse_id INTEGER REFERENCES warehouses(id),
  avatar BLOB,
  created_at DATETIME
);
"""


@pytest.fixture
def sqlite_url(tmp_path):
    path = tmp_path / "src.db"
    con = sqlite3.connect(path)
    con.executescript(DDL)
    con.close()
    return f"sqlite:///{path}"


def _fields(spec):
    return {f["name"]: f for f in spec["fields"]}


# ------------------------------------------------------------------ SQL e2e


def test_sqlite_table_to_spec(sqlite_url):
    table = introspect(sqlite_url, "Customers")
    spec, warnings = table_to_spec(table)
    f = _fields(spec)

    assert spec["resource"]["singular"] == "customer"
    assert spec["resource"]["plural"] == "customers"
    # PK, estructurales y no soportados fuera
    assert not {"customer_id", "id", "created_at", "avatar"} & set(f)
    assert f["customer_name"] == {"name": "customer_name", "type": "string", "optional": False}
    assert f["notes"]["type"] == "text"
    assert f["credit_limit"]["type"] == "money" and f["credit_limit"]["default"] == 0.0
    assert f["rating"]["type"] == "float"
    assert f["is_active"] == {"name": "is_active", "type": "bool", "optional": False, "default": True}
    assert f["status"]["type"] == "enum"
    assert [e["value"] for e in f["status"]["enum_values"]] == ["active", "blocked", "vip"]
    assert f["status"]["default"] == "active"
    assert f["birth_date"]["type"] == "date"
    assert f["last_seen"]["type"] == "datetime" and f["last_seen"]["default"] == "now"
    assert f["warehouse_id"]["type"] == "int"

    joined = "\n".join(warnings)
    for needle in ("CustomerID", "renombrada", "FK a warehouses.id", "avatar", "created_at", "decimal"):
        assert needle in joined


def test_generated_yaml_is_a_valid_spec_and_renders(sqlite_url):
    table = introspect(sqlite_url, "Customers")
    spec_dict, warnings = table_to_spec(table, form_mode="page", icon="Users")
    text = to_yaml(spec_dict, table=table, warnings=warnings)
    assert text.startswith("# Spec generado")

    spec = spec_from_dict(yaml.safe_load(text))
    assert validate(spec)[0] == []
    assert spec.form_mode == "page"

    ctx = build_context(spec, head_rev="x", new_rev=new_revision_id())
    env = make_env()
    for tpl in ("frontend/page.tsx.jinja", "frontend/form_page.tsx.jinja",
                "backend/model_block.py.jinja", "backend/migration.py.jinja"):
        assert env.get_template(tpl).render(**ctx)


def test_cli_writes_output(sqlite_url, tmp_path, capsys):
    out = tmp_path / "customers.yaml"
    rc = introspect_table.main(["--url", sqlite_url, "--table", "Customers", "-o", str(out),
                                "--plural", "clients", "--singular", "client"])
    assert rc == 0
    data = yaml.safe_load(out.read_text())
    assert data["resource"]["plural"] == "clients"
    # no pisa sin --force
    assert introspect_table.main(["--url", sqlite_url, "--table", "Customers", "-o", str(out)]) == 1


def test_cli_list_tables(sqlite_url, capsys):
    assert introspect_table.main(["--url", sqlite_url, "--list-tables"]) == 0
    assert capsys.readouterr().out.split() == ["Customers", "warehouses"]


def test_cli_url_env(sqlite_url, monkeypatch, capsys):
    monkeypatch.setenv("SRC_DB_URL", sqlite_url)
    assert introspect_table.main(["--url-env", "SRC_DB_URL", "--table", "Customers"]) == 0
    assert "customer_name" in capsys.readouterr().out


def test_missing_table_is_clean_error(sqlite_url):
    with pytest.raises(SystemExit, match="No existe la tabla"):
        introspect(sqlite_url, "nope")


# -------------------------------------------------------- tipos por dialecto


@pytest.mark.parametrize("sa_type, kind", [
    (postgresql.ENUM("a", "b", name="e"), "enum"),
    (postgresql.UUID(), "uuid"),
    (postgresql.TIMESTAMP(timezone=True), "datetime"),
    (postgresql.JSONB(), "unsupported"),
    (postgresql.BYTEA(), "unsupported"),
    (postgresql.DOUBLE_PRECISION(), "float"),
    (postgresql.NUMERIC(10, 2), "decimal"),
    (mysql.TINYINT(display_width=1), "bool"),
    (mysql.TINYINT(display_width=4), "int"),
    (mysql.LONGTEXT(), "text"),
    (mysql.ENUM("x", "y"), "enum"),
    (mysql.DATETIME(), "datetime"),
    (mssql.BIT(), "bool"),
    (mssql.MONEY(), "decimal"),
    (mssql.UNIQUEIDENTIFIER(), "uuid"),
    (mssql.DATETIMEOFFSET(), "datetime"),
    (mssql.DATETIME2(), "datetime"),
    (mssql.NTEXT(), "text"),
    (sa.Date(), "date"),
    (sa.BigInteger(), "int"),
    (sa.Time(), "unsupported"),
])
def test_classify_type(sa_type, kind):
    assert classify_type(sa_type)[0] == kind


def test_classify_string_lengths():
    assert classify_type(mssql.NVARCHAR(80))[:2] == ("string", 80)
    assert classify_type(mssql.NVARCHAR(None))[:2] == ("string", None)  # nvarchar(max)


def test_unbounded_varchar_maps_to_text():
    table = TableInfo(name="t", source="x", columns=[
        ColumnInfo(name="short", kind="string", raw_type="VARCHAR(80)", max_length=80),
        ColumnInfo(name="unbounded", kind="string", raw_type="VARCHAR", max_length=None),
        ColumnInfo(name="long", kind="string", raw_type="VARCHAR(1000)", max_length=1000),
    ])
    f = _fields(table_to_spec(table)[0])
    assert (f["short"]["type"], f["unbounded"]["type"], f["long"]["type"]) == ("string", "text", "text")


@pytest.mark.parametrize("raw, kind, expected", [
    ("'pending'::character varying", "string", "pending"),
    ("((0))", "int", 0),
    ("('abc')", "string", "abc"),
    ("N'abc'", "string", "abc"),
    ("(getdate())", "datetime", "now"),
    ("CURRENT_TIMESTAMP", "datetime", "now"),
    ("now()", "datetime", "now"),
    ("CURRENT_DATE", "date", "today"),
    ("nextval('orders_id_seq'::regclass)", "int", None),
    ("true", "bool", True),
    ("'1'", "bool", "1"),
    ("12.50", "decimal", 12.5),
    ("NULL", "string", None),
    (None, "string", None),
])
def test_parse_server_default(raw, kind, expected):
    assert parse_server_default(raw, kind) == expected


def test_enum_from_postgres_any_check():
    checks = [{"sqltext": "((status)::text = ANY ((ARRAY['new'::character varying, "
                          "'done'::character varying])::text[]))"}]
    assert _enum_from_checks("status", checks) == ["new", "done"]
    assert _enum_from_checks("other", checks) == []


def test_enum_from_checks_skips_compound():
    checks = [{"sqltext": "status IN ('a','b') AND qty > 0"}]
    assert _enum_from_checks("status", checks) == []


# ------------------------------------------------------------------ helpers


def test_normalize_url_adds_driver():
    assert normalize_url("mysql://u:p@h/db")[0] == "mysql+pymysql://u:p@h/db"
    assert normalize_url("mariadb://u:p@h/db")[0] == "mariadb+pymysql://u:p@h/db"
    assert normalize_url("mssql://u:p@h/db")[0] == "mssql+pymssql://u:p@h/db"
    assert normalize_url("postgres://u:p@h/db")[0] == "postgresql+psycopg2://u:p@h/db"
    assert normalize_url("mssql+pyodbc://u:p@h/db") == ("mssql+pyodbc://u:p@h/db", None)


def test_safe_source_hides_password():
    assert "secreto" not in safe_source("postgresql://u:secreto@h/db")


def test_is_mongo():
    assert is_mongo("mongodb://h/db") and is_mongo("mongodb+srv://h/db")
    assert not is_mongo("postgresql://h/db")


@pytest.mark.parametrize("name, expected", [
    ("CustomerName", "customer_name"),
    ("customer-name", "customer_name"),
    ("Customer Name", "customer_name"),
    ("HTTPStatus", "http_status"),
    ("2fa_code", "f_2fa_code"),
])
def test_snake_case(name, expected):
    assert snake_case(name) == expected


@pytest.mark.parametrize("table, expected", [
    ("customers", ("customer", "customers")),
    ("categories", ("category", "categories")),
    ("boxes", ("box", "boxes")),
    ("addresses", ("address", "addresses")),
    ("inventory", ("inventory", "inventorys")),
    ("dbo.Products", ("product", "products")),
])
def test_singular_plural(table, expected):
    assert singular_plural(table) == expected


# -------------------------------------------------------------------- Mongo


def test_mongo_infer_from_docs():
    class ObjectId:  # stand-in de bson.ObjectId (se detecta por nombre de clase)
        pass

    docs = [
        {"_id": 1, "name": "a", "qty": 1, "price": 1.5, "ok": True, "when": datetime(2026, 1, 1),
         "ref": ObjectId(), "tags": ["x"], "kind": "small"},
        {"_id": 2, "name": "b", "qty": 2.5, "ok": False, "when": None, "kind": "big", "note": "x" * 400},
        {"_id": 3, "name": "c", "qty": 3, "price": Decimal("2"), "ok": True, "kind": "small"},
        {"_id": 4, "name": "d", "qty": 4, "ok": True, "kind": "big"},
    ]
    cols, warnings = infer_from_docs(docs, enum_threshold=3)
    by = {c.name: c for c in cols}
    assert "_id" not in by
    assert by["name"].kind == "string" and not by["name"].nullable
    assert by["qty"].kind == "float"  # int + float
    assert by["ok"].kind == "bool"
    assert by["when"].kind == "datetime" and by["when"].nullable
    assert by["ref"].kind == "objectid"
    assert by["tags"].kind == "unsupported"
    assert by["kind"].kind == "enum" and by["kind"].enum_values == ["big", "small"]
    assert by["note"].nullable and by["note"].max_length == 400
    assert any("mezclados" in w for w in warnings)  # price: float + Decimal

    spec, _ = table_to_spec(TableInfo(name="items", source="mongodb://h/db", columns=cols))
    f = _fields(spec)
    assert f["note"]["type"] == "text" and f["name"]["type"] == "string"
    assert "tags" not in f
    assert validate(spec_from_dict(spec))[0] == []


def test_mongo_enum_inference_off_by_default():
    docs = [{"kind": "a"}, {"kind": "b"}, {"kind": "a"}, {"kind": "b"}]
    cols, _ = infer_from_docs(docs)
    assert cols[0].kind == "string"


def test_mongo_empty_collection():
    cols, warnings = infer_from_docs([])
    assert cols == [] and "vacía" in warnings[0]


def test_mongo_json_schema():
    schema = {
        "bsonType": "object",
        "required": ["title", "status"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "title": {"bsonType": "string", "maxLength": 80},
            "body": {"bsonType": "string", "maxLength": 5000},
            "status": {"bsonType": "string", "enum": ["open", "closed"]},
            "count": {"bsonType": ["int", "null"]},
            "amount": {"bsonType": "decimal"},
            "due": {"bsonType": "date"},
            "meta": {"bsonType": "object"},
        },
    }
    cols, _ = infer_from_json_schema(schema)
    by = {c.name: c for c in cols}
    assert "_id" not in by
    assert by["title"].kind == "string" and not by["title"].nullable
    assert by["status"].kind == "enum" and by["status"].enum_values == ["open", "closed"]
    assert by["count"].kind == "int" and by["count"].nullable
    assert by["amount"].kind == "decimal"
    assert by["due"].kind == "datetime"
    assert by["meta"].kind == "unsupported"
    f = _fields(table_to_spec(TableInfo(name="posts", source="m", columns=cols))[0])
    assert f["title"]["type"] == "string" and f["body"]["type"] == "text"
