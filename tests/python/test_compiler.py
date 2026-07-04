"""Pruebas del compilador, del andamiaje y de la actividad de ejemplo del repo."""

import json
from pathlib import Path

from aulastep.compiler import build
from aulastep.project import load_project
from aulastep.scaffold import init_activity

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "dhcp-kea"


def test_build_genera_dist_completa(make_activity, tmp_path):
    report, dist = build(make_activity(), output=tmp_path / "salida")
    assert report.ok and dist is not None
    assert (dist / "index.html").is_file()
    assert (dist / "activity.json").is_file()
    assert (dist / "assets" / "app.js").is_file()
    assert (dist / "assets" / "styles.css").is_file()
    assert (dist / "assets" / "themes.css").is_file()
    assert (dist / "assets" / "vendor" / "jszip.min.js").is_file()
    assert (dist / "assets" / "vendor" / "purify.min.js").is_file()


def test_activity_json_usa_camel_case(make_activity, tmp_path):
    _, dist = build(make_activity(), output=tmp_path / "salida")
    data = json.loads((dist / "activity.json").read_text(encoding="utf-8"))
    assert data["schemaVersion"] == "1.0"
    assert data["generator"]["name"] == "AulaStep"
    assert "steps" in data


def test_build_con_base_url(make_activity, tmp_path):
    _, dist = build(make_activity(), output=tmp_path / "salida", base_url="/mi-repo")
    html = (dist / "index.html").read_text(encoding="utf-8")
    assert '<base href="/mi-repo/">' in html


def test_build_no_compila_con_errores(make_activity, tmp_path):
    root = make_activity({"01-a.md": "sin front matter"})
    report, dist = build(root, output=tmp_path / "salida")
    assert dist is None and not report.ok


def test_init_crea_actividad_valida(tmp_path):
    target = init_activity(tmp_path / "mi-practica")
    loader = load_project(target)
    assert loader.report.ok, [str(i) for i in loader.report.issues]
    assert len(loader.compiled.steps) == 2


def test_ejemplo_dhcp_kea_valida_sin_errores():
    loader = load_project(EXAMPLE)
    assert loader.report.ok, [str(i) for i in loader.report.issues]
    assert len(loader.compiled.steps) == 7
    ids = [s.id for s in loader.compiled.steps]
    assert ids[0] == "presentacion" and ids[-1] == "entrega"


def test_ejemplo_no_filtra_soluciones(tmp_path):
    report, dist = build(EXAMPLE, output=tmp_path / "dist")
    assert report.ok
    payload = (dist / "activity.json").read_text(encoding="utf-8")
    assert '"correct"' not in payload
