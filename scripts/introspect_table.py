#!/usr/bin/env python3
"""Genera un spec YAML del scaffold leyendo la estructura de una tabla existente.

    # listar tablas / colecciones
    python scripts/introspect_table.py --url-env SRC_DB_URL --list-tables

    # tabla -> spec (a stdout, o a un archivo con -o)
    python scripts/introspect_table.py --url-env SRC_DB_URL --table clientes \\
        -o scripts/scaffold/specs/examples/customers.yaml

    # y scaffoldear de una
    python scripts/introspect_table.py --url-env SRC_DB_URL --table clientes \\
        -o /tmp/customers.yaml --then-scaffold

Motores (URL de SQLAlchemy / pymongo):
    postgresql://user:pass@host:5432/db
    mysql://user:pass@host:3306/db          (-> mysql+pymysql)
    mariadb://user:pass@host:3306/db        (-> mariadb+pymysql)
    mssql://user:pass@host:1433/db          (-> mssql+pymssql; o mssql+pyodbc://...)
    mongodb://user:pass@host:27017/db

Preferí `--url-env VAR` a `--url`: así la contraseña no queda en el historial de la shell.
Drivers: cd backend && ./venv/bin/pip install -r requirements-introspect.txt
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.scaffold import introspect  # noqa: E402
from scripts.scaffold.introspect.mapping import table_to_spec, to_yaml  # noqa: E402
from scripts.scaffold.spec import FORM_MODES, SCOPING_MODES, spec_from_dict, validate  # noqa: E402


def _resolve_url(args, parser) -> str:
    if args.url:
        return args.url
    value = os.environ.get(args.url_env, "").strip()
    if not value:
        parser.error(f"la variable de entorno {args.url_env!r} está vacía o no existe")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="introspect_table",
        description="Lee una tabla/colección (PostgreSQL, MySQL, MariaDB, MSSQL, MongoDB) "
                    "y genera un spec YAML para scripts/scaffold_resource.py.",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="URL de conexión (evitá pasar la contraseña así; ver --url-env)")
    src.add_argument("--url-env", metavar="VAR", help="nombre de la variable de entorno con la URL")

    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--table", help="tabla (SQL) o colección (Mongo) a leer")
    what.add_argument("--list-tables", action="store_true", help="lista tablas/colecciones y sale")

    parser.add_argument("--schema", help="esquema SQL (ej. public, dbo); default: el del usuario")
    parser.add_argument("--database", help="base Mongo, si la URL no la indica")
    parser.add_argument("--sample", type=int, default=200, help="Mongo: documentos a muestrear (200)")
    parser.add_argument("--infer-enums", type=int, default=0, metavar="N",
                        help="Mongo: proponer enum para strings con <= N valores distintos (0 = no)")

    parser.add_argument("--singular", help="nombre singular del recurso (default: derivado de la tabla)")
    parser.add_argument("--plural", help="nombre plural del recurso (default: derivado de la tabla)")
    parser.add_argument("--label-singular")
    parser.add_argument("--label-plural")
    parser.add_argument("--icon", help="icono lucide-react (default: Box)")
    parser.add_argument("--scoping", choices=sorted(SCOPING_MODES), default="none")
    parser.add_argument("--dimension", help="dimensión para --scoping attribute")
    parser.add_argument("--form-mode", choices=sorted(FORM_MODES), default="modal",
                        help="alta/edición en el frontend: modal o página del dashboard")

    parser.add_argument("-o", "--output", help="archivo YAML de salida (default: stdout)")
    parser.add_argument("--force", action="store_true", help="sobrescribir --output si existe")
    parser.add_argument("--then-scaffold", action="store_true",
                        help="tras escribir --output, correr scaffold_resource.py con ese spec")
    args = parser.parse_args(argv)

    if args.then_scaffold and not args.output:
        parser.error("--then-scaffold requiere --output")
    if args.scoping == "attribute" and not args.dimension:
        parser.error("--scoping attribute requiere --dimension")

    url = _resolve_url(args, parser)

    if args.list_tables:
        for name in introspect.list_tables(url, schema=args.schema, database=args.database):
            print(name)
        return 0

    table = introspect.introspect(url, args.table, schema=args.schema, database=args.database,
                                  sample=args.sample, enum_threshold=args.infer_enums)
    spec_dict, warnings = table_to_spec(
        table,
        singular=args.singular, plural=args.plural,
        label_singular=args.label_singular, label_plural=args.label_plural,
        icon=args.icon, scoping_mode=args.scoping, dimension=args.dimension,
        form_mode=args.form_mode,
    )

    for w in warnings:
        print(f"  aviso: {w}", file=sys.stderr)

    errors, spec_warnings = validate(spec_from_dict(spec_dict))
    for w in spec_warnings:
        print(f"  aviso: {w}", file=sys.stderr)
    if errors:
        # se escribe igual: el usuario corrige el YAML a mano (ej. --plural reservado)
        print("\nEl spec generado tiene errores; corregilos en el YAML antes de scaffoldear:",
              file=sys.stderr)
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)

    text = to_yaml(spec_dict, table=table, warnings=warnings)

    if not args.output:
        sys.stdout.write(text)
        return 1 if errors else 0

    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"ERROR: {out} ya existe (usá --force para sobrescribir)", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Spec escrito en {out}  ({len(spec_dict['fields'])} campo(s), {len(warnings)} aviso(s))",
          file=sys.stderr)

    if errors:
        return 1
    if args.then_scaffold:
        from scripts.scaffold.cli import main as scaffold_main
        return scaffold_main(["--from", str(out)])
    print(f"Siguiente paso:  python scripts/scaffold_resource.py --from {out} --dry-run",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
