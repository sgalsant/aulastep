"""Pruebas de validación integral del proyecto (ProjectLoader)."""

from aulastep.project import load_project

STEP = """---
id: {sid}
titulo: Paso
---

{body}
"""


def _codes(loader):
    return [i.code for i in loader.report.issues]


def test_actividad_valida_compila(make_activity):
    loader = load_project(make_activity())
    assert loader.report.ok
    assert loader.compiled is not None
    assert loader.compiled.steps[0].segments[0].type == "html"
    assert "<strong>mundo</strong>" in loader.compiled.steps[0].segments[0].html


def test_id_directiva_duplicado(make_activity):
    body = ':::task{id="rep"}\na\n:::\n\n:::task{id="rep"}\nb\n:::'
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert "DIRECTIVA_ID_DUPLICADO" in _codes(loader)


def test_directiva_sin_id(make_activity):
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=":::task\nx\n:::")}))
    assert "DIRECTIVA_SIN_ID" in _codes(loader)


def test_recurso_ausente(make_activity):
    body = "![alt](recursos/no-existe.png)"
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert "RECURSO_AUSENTE" in _codes(loader)


def test_recurso_ruta_insegura(make_activity):
    body = "[mal](../fuera.txt)"
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert "RECURSO_RUTA_INSEGURA" in _codes(loader)


def test_tema_desconocido(make_activity):
    yml = """schema_version: "1.0"
actividad: {id: demo, titulo: Demo, version: 1.0.0, tema: fucsia}
"""
    loader = load_project(make_activity(yml=yml))
    assert "TEMA_DESCONOCIDO" in _codes(loader)


def test_schema_incompatible(make_activity):
    yml = """schema_version: "2.0"
actividad: {id: demo, titulo: Demo, version: 1.0.0}
"""
    loader = load_project(make_activity(yml=yml))
    assert "SCHEMA_INCOMPATIBLE" in _codes(loader)


def test_enlace_paso_roto(make_activity):
    body = "[ver](paso:no-existe)"
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert "ENLACE_PASO_ROTO" in _codes(loader)


def test_enlace_paso_valido_se_reescribe(make_activity):
    steps = {
        "01-a.md": STEP.format(sid="a", body="[ver b](paso:b)"),
        "02-b.md": STEP.format(sid="b", body="fin"),
    }
    loader = load_project(make_activity(steps))
    assert loader.report.ok
    html = loader.compiled.steps[0].segments[0].html
    assert 'href="#/paso/b"' in html
    assert 'data-step-link="b"' in html


def test_single_choice_sin_marca_avisa(make_activity):
    body = ':::question{id="q" type="single-choice"}\n¿?\n\n- [ ] a\n- [ ] b\n:::'
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert loader.report.ok
    assert "PREGUNTA_MARCADO_UNICO" in [i.code for i in loader.report.warnings]


def test_choice_con_una_opcion_es_error(make_activity):
    body = ':::question{id="q" type="multi-choice"}\n¿?\n\n- [x] sola\n:::'
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert "PREGUNTA_SIN_OPCIONES" in _codes(loader)


def test_tipo_pregunta_invalido(make_activity):
    body = ':::question{id="q" type="dibujo"}\n¿?\n:::'
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert "PREGUNTA_TIPO_INVALIDO" in _codes(loader)


def test_soluciones_no_se_publican(make_activity):
    body = ':::question{id="q" type="single-choice"}\n¿?\n\n- [x] correcta\n- [ ] otra\n:::'
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert loader.report.ok
    payload = loader.compiled.to_json()
    assert '"correct"' not in payload
    assert "[x]" not in payload


def test_html_embebido_se_escapa(make_activity):
    body = "<script>alert(1)</script>"
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    html = loader.compiled.steps[0].segments[0].html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_hint_compila_como_desplegable(make_activity):
    body = ":::hint{}\nRevisa la salida de `ip -brief address`.\n:::"
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert loader.report.ok
    html = loader.compiled.steps[0].segments[0].html
    assert 'class="as-details as-details--hint"' in html
    assert "<summary>Pista</summary>" in html
    assert "data-guarded" not in html


def test_solution_compila_protegida_y_con_titulo(make_activity):
    body = ':::solution{summary="Solución del apartado 2"}\nLa máscara es `255.255.255.0`.\n:::'
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert loader.report.ok
    html = loader.compiled.steps[0].segments[0].html
    assert 'class="as-details as-details--solution"' in html
    assert 'data-guarded="true"' in html
    assert "<summary>Solución del apartado 2</summary>" in html


def test_hint_y_solution_no_cuentan_para_el_progreso(make_activity):
    body = ":::hint{}\npista\n:::\n\n:::solution{}\nsolución\n:::"
    loader = load_project(make_activity({"01-a.md": STEP.format(sid="a", body=body)}))
    assert loader.report.ok
    types = [seg.type for seg in loader.compiled.steps[0].segments]
    assert types == ["html", "html"]  # estáticos: sin id, sin required


def test_licencia_por_defecto_cc_by_nc_sa(make_activity):
    loader = load_project(make_activity())
    assert loader.report.ok
    lic = loader.compiled.activity["licencia"]
    assert lic["nombre"] == "CC BY-NC-SA 4.0"
    assert lic["url"].endswith("by-nc-sa/4.0/deed.es")
    assert len(lic["condiciones"]) == 4


def test_licencia_personalizada(make_activity):
    yml = """schema_version: "1.0"
actividad:
  id: demo
  titulo: Demo
  version: 1.0.0
  autor: Santiago Galván Sánchez
  licencia:
    nombre: CC BY 4.0
    nombre_completo: Creative Commons Atribución 4.0 Internacional
    url: https://creativecommons.org/licenses/by/4.0/deed.es
    condiciones:
      - se reconozca adecuadamente la autoría.
"""
    loader = load_project(make_activity(yml=yml))
    assert loader.report.ok, [str(i) for i in loader.report.issues]
    lic = loader.compiled.activity["licencia"]
    assert lic["nombre"] == "CC BY 4.0"
    assert loader.compiled.activity["autor"] == "Santiago Galván Sánchez"
    assert lic["condiciones"] == ["se reconozca adecuadamente la autoría."]
