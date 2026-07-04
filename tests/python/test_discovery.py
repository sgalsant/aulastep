"""Pruebas del descubrimiento y ordenación de pasos."""

from aulastep.discovery import discover_steps
from aulastep.errors import Report


def test_orden_por_nombre_de_archivo(make_activity):
    root = make_activity(
        {
            "03-tres.md": "---\nid: tres\ntitulo: Tres\n---\nx",
            "01-uno.md": "---\nid: uno\ntitulo: Uno\n---\nx",
            "02-dos.md": "---\nid: dos\ntitulo: Dos\n---\nx",
        }
    )
    report = Report()
    steps = discover_steps(root, report)
    assert [s.slug for s in steps] == ["uno", "dos", "tres"]
    assert report.ok


def test_nombre_invalido_es_error(make_activity):
    root = make_activity({"1-mal.md": "x", "01-Mayusculas.md": "x", "01_guion_bajo.md": "x"})
    report = Report()
    discover_steps(root, report)
    codes = [i.code for i in report.errors]
    assert codes.count("PASO_NOMBRE_INVALIDO") == 3


def test_prefijo_duplicado_es_error(make_activity):
    root = make_activity(
        {
            "01-a.md": "---\nid: a\ntitulo: A\n---\nx",
            "01-b.md": "---\nid: b\ntitulo: B\n---\nx",
        }
    )
    report = Report()
    discover_steps(root, report)
    assert any(i.code == "PASO_PREFIJO_DUPLICADO" for i in report.errors)


def test_salto_de_numeracion_es_aviso(make_activity):
    root = make_activity(
        {
            "01-a.md": "---\nid: a\ntitulo: A\n---\nx",
            "05-b.md": "---\nid: b\ntitulo: B\n---\nx",
        }
    )
    report = Report()
    discover_steps(root, report)
    assert report.ok
    assert any(i.code == "PASO_SALTO_NUMERACION" for i in report.warnings)


def test_carpeta_pasos_ausente(tmp_path):
    report = Report()
    discover_steps(tmp_path, report)
    assert any(i.code == "PASOS_AUSENTES" for i in report.errors)


def test_prefijo_de_tres_digitos_permitido(make_activity):
    root = make_activity({"100-cien.md": "---\nid: cien\ntitulo: Cien\n---\nx"})
    report = Report()
    steps = discover_steps(root, report)
    assert report.ok and steps[0].number == 100
