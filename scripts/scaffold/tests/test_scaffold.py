"""Tests unitarios del generador de scaffold.

Correr desde la raíz del repo:  python -m pytest scripts/scaffold/tests -q
(requiere las deps dev: jinja2, pyyaml, pytest)
"""
import ast
import textwrap
from pathlib import Path

import pytest

from scripts.scaffold import blocks, domain_files, frontend
from scripts.scaffold.alembic_head import current_head
from scripts.scaffold.cli import build_insertions, find_repo_root
from scripts.scaffold.inserts import InsertionSet
from scripts.scaffold.render import build_context, make_env, new_revision_id
from scripts.scaffold.spec import Spec, load_spec, validate
from scripts.scaffold.strip import strip_marker_blocks

REPO = find_repo_root(Path(__file__))
SPEC_OWN = REPO / "scripts/scaffold/specs/examples/products.yaml"


def _spec_own() -> Spec:
    return load_spec(SPEC_OWN)


def _write_spec(tmp_path, body: str) -> Path:
    p = tmp_path / "s.yaml"
    p.write_text(textwrap.dedent(body))
    return p


# --------------------------------------------------------------------- alembic


def test_current_head_is_single():
    head = current_head(REPO)
    assert head and isinstance(head, str)


# ------------------------------------------------------------------------ spec


def test_spec_products_valid():
    errors, _ = validate(_spec_own())  # sin repo_root -> no chequea marcadores
    assert errors == []


def test_spec_rejects_reserved(tmp_path):
    spec = load_spec(_write_spec(tmp_path, """
        resource: { singular: user, plural: users }
        fields: [{ name: x, type: string }]
    """))
    errors, _ = validate(spec)
    assert any("reservado" in e for e in errors)


def test_spec_rejects_enum_without_values(tmp_path):
    spec = load_spec(_write_spec(tmp_path, """
        resource: { singular: item, plural: items }
        fields: [{ name: kind, type: enum }]
    """))
    errors, _ = validate(spec)
    assert any("enum_values" in e for e in errors)


def test_spec_attribute_adds_dimension_field(tmp_path):
    spec = load_spec(_write_spec(tmp_path, """
        resource: { singular: box, plural: boxes }
        fields: [{ name: label, type: string }]
        scoping: { mode: attribute, dimension: zone }
    """))
    assert any(f.name == "zone" and not f.optional for f in spec.fields)
    assert spec.has_owner and spec.is_scoped


# --------------------------------------------------------------------- inserts


def test_insertion_requires_unique_anchor(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("a = 1\nb = 2\na = 1\n")
    iset = InsertionSet(repo_root=tmp_path)
    iset.add_insertion("x.py", "a = 1", "z = 9", "after", "py", "T:X")
    with pytest.raises(ValueError):
        iset.render()


def test_insertion_roundtrip_is_identity(tmp_path):
    f = tmp_path / "x.py"
    original = "import os\n\n\nVALUE = 1\n"
    f.write_text(original)
    iset = InsertionSet(repo_root=tmp_path)
    iset.add_insertion("x.py", "VALUE = 1", "EXTRA = 2", "before", "py", "T:X")
    (_, new), = [(o, n) for o, n in iset.render().values()]
    assert "T:X:START" in new
    back, removed = strip_marker_blocks(new, "T:X")
    assert removed == 1
    assert back == original


# --------------------------------------------------------------- render / compile


@pytest.mark.parametrize("scope_mode", ["none", "own", "attribute"])
def test_generated_backend_is_valid_python(tmp_path, scope_mode):
    body = {
        "none": "scoping: { mode: none }",
        "own": "scoping: { mode: own }",
        "attribute": "scoping: { mode: attribute, dimension: zone }",
    }[scope_mode]
    spec = load_spec(_write_spec(tmp_path, f"""
        resource: {{ singular: widget, plural: widgets, icon: Box }}
        fields:
          - {{ name: title, type: string }}
          - {{ name: qty, type: int }}
          - {{ name: kind, type: enum, filterable: true, enum_values: [{{value: a, label: A}}, {{value: b, label: B}}] }}
        {body}
    """))
    assert validate(spec)[0] == []
    env = make_env()
    ctx = build_context(spec, head_rev="deadbeef", new_rev=new_revision_id())
    for tpl in ("backend/model_block.py.jinja", "backend/service_block.py.jinja",
                "backend/api_router.py.jinja", "backend/migration.py.jinja",
                "backend/test_resource.py.jinja"):
        ast.parse(env.get_template(tpl).render(**ctx))
    # deps helpers sólo aplica a non-scoped
    if not spec.is_scoped:
        ast.parse("def require_permissions(x):\n    pass\n" + blocks.deps_helpers(spec))


@pytest.mark.parametrize("mode", ["none", "own", "attribute"])
def test_build_insertions_produce_valid_python(tmp_path, mode):
    """Contra el árbol real: cada anchor resuelve y los .py editados parsean."""
    body = {
        "none": "scoping: { mode: none }",
        "own": "scoping: { mode: own }",
        "attribute": "scoping: { mode: attribute, dimension: zone }",
    }[mode]
    # sin campos filterable -> cubre la firma de count() sin `*`
    spec = load_spec(_write_spec(tmp_path, f"""
        resource: {{ singular: gadget, plural: gadgets, icon: Box }}
        fields:
          - {{ name: title, type: string }}
          - {{ name: qty, type: int }}
        {body}
    """))
    env = make_env()
    ctx = build_context(spec, head_rev=current_head(REPO), new_rev=new_revision_id())
    rendered = build_insertions(spec, REPO, ctx, env).render()
    assert len(rendered) > 10
    for path, (_old, new) in rendered.items():
        if path.suffix == ".py":
            ast.parse(new, filename=str(path))


# --------------------------------------------------------------- domain_files


def test_domain_files_consistent():
    spec = _spec_own()
    marks = domain_files.files_with_markers(spec)
    dels = domain_files.files_to_delete(spec, REPO)
    assert "backend/app/models/models.py" in marks
    assert f"backend/app/api/{spec.resource.plural}.py" in dels
    # un archivo no puede estar en las dos listas
    assert not (set(marks) & set(dels))


# ------------------------------------------------------------------ form_mode

_FORM_SPEC = """
    resource: {{ singular: gizmo, plural: gizmos, icon: Box }}
    fields:
      - {{ name: title, type: string }}
      - {{ name: due, type: date, optional: true }}
      - {{ name: at, type: datetime, default: now }}
    scoping: {{ mode: {mode} }}
    frontend: {{ form_mode: {form_mode} }}
"""


def _form_spec(tmp_path, form_mode, mode="none"):
    return load_spec(_write_spec(tmp_path, _FORM_SPEC.format(form_mode=form_mode, mode=mode)))


def test_spec_rejects_invalid_form_mode(tmp_path):
    spec = _form_spec(tmp_path, "drawer")
    assert any("form_mode" in e for e in validate(spec)[0])


def test_form_mode_defaults_to_modal(tmp_path):
    spec = load_spec(_write_spec(tmp_path, """
        resource: { singular: item, plural: items }
        fields: [{ name: x, type: string }]
    """))
    assert spec.form_mode == "modal" and not spec.uses_form_page


def test_modal_mode_renders_modal(tmp_path):
    spec = _form_spec(tmp_path, "modal")
    ctx = build_context(spec, head_rev="x", new_rev=new_revision_id())
    page = make_env().get_template("frontend/page.tsx.jinja").render(**ctx)
    assert "<Modal" in page and "useNavigate" not in page
    assert "toPayload(formData)" in page and "fromLocalInput" in page


@pytest.mark.parametrize("mode", ["none", "own"])
def test_page_mode_renders_form_page(tmp_path, mode):
    spec = _form_spec(tmp_path, "page", mode)
    assert validate(spec)[0] == []
    env = make_env()
    ctx = build_context(spec, head_rev="x", new_rev=new_revision_id())
    page = env.get_template("frontend/page.tsx.jinja").render(**ctx)
    form = env.get_template("frontend/form_page.tsx.jinja").render(**ctx)
    assert "<Modal" not in page and "Modal'" not in page
    assert "navigate('/gizmos/new')" in page and "/gizmos/${item.id}/edit" in page
    assert "export default function GizmosFormPage" in form
    assert "gizmoService.getById(recordId)" in form
    assert "navigate('/gizmos')" in form and "toPayload(formData)" in form


def test_page_mode_wiring_roundtrip_is_byte_clean(tmp_path):
    """Las rutas extra quedan dentro del bloque de marcadores: quitarlo deja el archivo intacto."""
    spec = _form_spec(tmp_path, "page")
    env = make_env()
    ctx = build_context(spec, head_rev=current_head(REPO), new_rev=new_revision_id())
    iset = build_insertions(spec, REPO, ctx, env)
    rendered = iset.render()

    app = rendered[REPO / "frontend/src/App.tsx"][1]
    assert '<Route path="/gizmos/new"' in app and '<Route path="/gizmos/:id/edit"' in app
    assert "import GizmosForm from '@/pages/GizmosForm';" in app

    for path, (old, new) in rendered.items():
        if old is None:  # archivo nuevo: lo borra remove_domain, no se le quitan bloques
            continue
        back, _ = strip_marker_blocks(new, spec.marker_tag)
        assert back == old, path

    assert REPO / "frontend/src/pages/GizmosForm.tsx" in iset._new
    assert "frontend/src/pages/GizmosForm.tsx" in domain_files.files_to_delete(spec)


def test_modal_mode_has_no_form_page(tmp_path):
    spec = _form_spec(tmp_path, "modal")
    iset = build_insertions(spec, REPO, build_context(spec, head_rev="x", new_rev="y"), make_env())
    assert REPO / "frontend/src/pages/GizmosForm.tsx" not in iset._new
    assert not any(p.endswith("Form.tsx") for p in domain_files.files_to_delete(spec))


# ---------------------------------------------------------------- date / datetime


def test_date_typemap(tmp_path):
    from scripts.scaffold import typemap
    spec = load_spec(_write_spec(tmp_path, """
        resource: { singular: item, plural: items }
        fields:
          - { name: d_req, type: date }
          - { name: d_opt, type: date, optional: true }
          - { name: d_today, type: date, default: today }
          - { name: d_iso, type: date, default: 2026-01-15 }
          - { name: t_now, type: datetime, default: now }
          - { name: t_opt, type: datetime, optional: true }
    """))
    assert validate(spec)[0] == []
    f = {x.name: x for x in spec.fields}
    assert typemap.model_base_line(f["d_req"]) == "d_req: date"
    assert typemap.model_base_line(f["d_opt"]) == "d_opt: Optional[date] = None"
    assert typemap.model_base_line(f["d_today"]) == "d_today: date = Field(default_factory=date.today)"
    assert typemap.model_base_line(f["d_iso"]) == "d_iso: date = date.fromisoformat('2026-01-15')"
    assert typemap.model_base_line(f["t_now"]) == "t_now: datetime = Field(default_factory=datetime.now)"
    assert typemap.dto_update_line(f["t_opt"]) == "t_opt: Optional[datetime] = None"
    assert "sa.Date()" in typemap.migration_column(f["d_req"])
    assert "server_default=sa.func.now()" in typemap.migration_column(f["t_now"])
    assert "server_default=sa.func.current_date()" in typemap.migration_column(f["d_today"])
    assert typemap.ts_interface_line(f["d_opt"]) == "d_opt?: string | null;"
    assert typemap.ts_create_line(f["t_now"]) == "t_now?: string;"
    assert typemap.ts_create_line(f["d_req"]) == "d_req: string;"

    assert 'type="date"' in frontend.form_field(spec, f["d_req"])
    assert 'type="datetime-local"' in frontend.form_field(spec, f["t_opt"])
    assert "toLocaleDateString" in frontend.column(spec, f["d_req"])
    assert "toLocalInput(item.t_opt)" in frontend.form_pick(spec)
    payload = frontend.payload_fn(spec)
    assert "d_opt: f.d_opt ? f.d_opt : null," in payload
    assert "t_now: f.t_now ? fromLocalInput(f.t_now) : undefined," in payload
    assert "!formData.d_req?.trim()" in frontend.required_string_check(spec)


@pytest.mark.parametrize("body, needle", [
    ("{ name: d, type: date, default: now }", "default"),
    ("{ name: d, type: datetime, default: ayer }", "default"),
    ("{ name: d, type: date, filterable: true }", "filterable"),
])
def test_date_validation(tmp_path, body, needle):
    spec = load_spec(_write_spec(tmp_path, f"""
        resource: {{ singular: item, plural: items }}
        fields: [{body}]
    """))
    assert any(needle in e for e in validate(spec)[0])
