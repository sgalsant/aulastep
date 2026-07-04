"""Pruebas de la publicación de conjuntos de actividades (publish)."""

from pathlib import Path

from aulastep.publish import discover_activities, publish
from aulastep.scaffold import init_activity


def _make_source(tmp_path: Path, names: list[str]) -> Path:
    source = tmp_path / "actividades"
    source.mkdir()
    for name in names:
        init_activity(source / name)
    return source


def test_publica_cada_actividad_en_su_subcarpeta(tmp_path):
    source = _make_source(tmp_path, ["dhcp-basico", "ftp-vsftpd"])
    report, site = publish(source, output=tmp_path / "_site", clean=True)
    assert report.ok, [str(i) for i in report.issues]
    assert site is not None
    for aid in ("dhcp-basico", "ftp-vsftpd"):
        assert (site / aid / "index.html").is_file()
        assert (site / aid / "activity.json").is_file()
        assert (site / aid / "assets" / "app.js").is_file()


def test_indice_enlaza_todas_las_actividades(tmp_path):
    source = _make_source(tmp_path, ["dhcp-basico", "ftp-vsftpd"])
    _, site = publish(source, output=tmp_path / "_site", title="Servicios en Red")
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "Servicios en Red" in html
    assert 'href="dhcp-basico/"' in html
    assert 'href="ftp-vsftpd/"' in html
    assert "CC BY-NC-SA 4.0" in html  # la licencia por defecto aparece en las fichas


def test_carpeta_sin_actividades_es_error(tmp_path):
    empty = tmp_path / "vacia"
    empty.mkdir()
    report, site = publish(empty, output=tmp_path / "_site")
    assert site is None
    assert any(i.code == "PUBLICACION_SIN_ACTIVIDADES" for i in report.errors)


def test_actividad_invalida_bloquea_la_publicacion(tmp_path):
    source = _make_source(tmp_path, ["buena"])
    rota = source / "rota"
    (rota / "pasos").mkdir(parents=True)
    (rota / "actividad.yml").write_text("actividad: {id: rota}\n", encoding="utf-8")
    report, site = publish(source, output=tmp_path / "_site")
    assert site is None
    assert any(i.code == "PUBLICACION_ACTIVIDAD_INVALIDA" for i in report.errors)


def test_ids_duplicados_bloquean(tmp_path):
    source = _make_source(tmp_path, ["copia-a"])
    # Segunda carpeta distinta pero con el mismo id interno.
    duplicada = source / "copia-b"
    init_activity(duplicada)
    yml = (duplicada / "actividad.yml").read_text(encoding="utf-8")
    (duplicada / "actividad.yml").write_text(yml.replace("id: copia-b", "id: copia-a"))
    report, site = publish(source, output=tmp_path / "_site")
    assert site is None
    assert any(i.code == "PUBLICACION_ID_DUPLICADO" for i in report.errors)


def test_discover_ignora_carpetas_sin_yml(tmp_path):
    source = _make_source(tmp_path, ["una"])
    (source / "apuntes").mkdir()  # sin actividad.yml
    assert [p.name for p in discover_activities(source)] == ["una"]
