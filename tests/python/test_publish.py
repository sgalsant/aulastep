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


def test_indice_con_busqueda_y_filtro(tmp_path):
    source = _make_source(tmp_path, ["redes-uno", "ofimatica-dos"])
    # Módulos distintos y un título con tildes para probar la normalización
    for name, titulo, modulo in [
        ("redes-uno", "Configuración de VLAN", "Servicios en Red"),
        ("ofimatica-dos", "Documentos en Writer", "Aplicaciones Ofimáticas"),
    ]:
        p = source / name / "actividad.yml"
        s = p.read_text(encoding="utf-8")
        s = s.replace("titulo: Título de la actividad", f"titulo: {titulo}")
        s = s.replace("modulo: Nombre del módulo", f"modulo: {modulo}")
        p.write_text(s, encoding="utf-8")

    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")

    # Controles renderizados pero ocultos: sin JS se ve la lista completa
    assert '<div class="filtros" id="filtros" hidden>' in html
    assert 'id="buscador"' in html and 'id="contador"' in html
    # El filtro de módulo se genera desde los módulos publicados, ordenados
    assert html.index('value="Aplicaciones Ofimáticas"') < html.index('value="Servicios en Red"')
    # data-attributes por tarjeta: módulo literal y blob de búsqueda normalizado
    assert 'data-modulo="Servicios en Red"' in html
    assert "configuracion de vlan" in html  # sin tildes y en minúsculas
    assert 'data-buscar="' in html
    # Estado vacío presente (el JS lo muestra cuando no hay coincidencias)
    assert 'id="sin-resultados" hidden' in html
    # La licencia sigue en las fichas y en el pie
    assert html.count("CC BY-NC-SA 4.0") >= 2


def test_indice_sin_modulos_no_rompe(tmp_path):
    """Actividades sin campo modulo: el desplegable solo trae 'Todos'."""
    source = _make_source(tmp_path, ["suelta"])
    p = source / "suelta" / "actividad.yml"
    s = p.read_text(encoding="utf-8").replace("  modulo: Nombre del módulo\n", "")
    p.write_text(s, encoding="utf-8")
    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert html.count("<option") == 1  # solo «Todos los módulos»
    assert 'data-modulo=""' in html


def test_fecha_de_actualizacion_desde_git(tmp_path):
    import subprocess

    source = _make_source(tmp_path, ["con-historia"])
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=source, check=True)
    subprocess.run(["git", "add", "-A"], cwd=source, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "alta"],
        cwd=source,
        check=True,
        env={"GIT_COMMITTER_DATE": "2026-03-15T10:00:00+01:00", "PATH": "/usr/bin:/bin"},
    )
    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "actualizada 15/03/2026" in html


def test_sin_historial_git_no_se_inventa_fecha(tmp_path):
    source = _make_source(tmp_path, ["sin-git"])
    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "<span>actualizada " not in html  # mejor ninguna fecha que una falsa


def _git(source, *args, date=None):
    import subprocess

    env = None
    if date:
        env = {"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date, "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", *args], cwd=source, check=True, env=env, capture_output=True)


def test_distintivos_nueva_y_actualizada(tmp_path):
    from datetime import UTC, datetime

    source = _make_source(tmp_path, ["veterana", "recien-creada"])
    _git(source, "init", "-q")
    _git(source, "config", "user.email", "t@t")
    _git(source, "config", "user.name", "t")
    ahora = datetime.now(UTC).isoformat()

    # veterana: creada hace mucho…
    _git(source, "add", "veterana")
    _git(source, "commit", "-q", "-m", "alta veterana", date="2026-01-10T10:00:00+00:00")
    # …y retocada ahora → «Actualizada»
    (source / "veterana" / "recursos" / "nota.txt").write_text("retoque", encoding="utf-8")
    _git(source, "add", "veterana")
    _git(source, "commit", "-q", "-m", "retoque", date=ahora)
    # recien-creada: primer commit ahora → «Nueva»
    _git(source, "add", "recien-creada")
    _git(source, "commit", "-q", "-m", "alta nueva", date=ahora)

    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert ">Nueva</span>" in html and ">Actualizada</span>" in html
    # La nueva NO debe llevar «Actualizada» ni la retocada «Nueva»
    import re

    fichas = re.findall(r'<a class="card".*?</a>', html, re.S)
    por_id = {re.search(r'href="([^"]+)/"', f).group(1): f for f in fichas}
    assert (
        "badge-nueva" in por_id["recien-creada"]
        and "badge-actualizada" not in por_id["recien-creada"]
    )
    assert "badge-actualizada" in por_id["veterana"] and "badge-nueva" not in por_id["veterana"]


def test_sin_cambios_recientes_no_hay_distintivo(tmp_path):
    source = _make_source(tmp_path, ["antigua"])
    _git(source, "init", "-q")
    _git(source, "config", "user.email", "t@t")
    _git(source, "config", "user.name", "t")
    _git(source, "add", "-A")
    _git(source, "commit", "-q", "-m", "alta", date="2026-01-10T10:00:00+00:00")
    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert ">Nueva</span>" not in html and ">Actualizada</span>" not in html
    assert "actualizada 10/01/2026" in html  # la fecha sí, el distintivo no


def test_indice_incluye_estado_en_url(tmp_path):
    source = _make_source(tmp_path, ["una"])
    _, site = publish(source, output=tmp_path / "_site", clean=True)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "URLSearchParams" in html and "replaceState" in html
    assert 'params.get("q")' in html and 'params.get("modulo")' in html


def test_borrador_se_valida_pero_no_se_publica(tmp_path):
    source = _make_source(tmp_path, ["visible", "en-el-horno"])
    p = source / "en-el-horno" / "actividad.yml"
    p.write_text(
        p.read_text(encoding="utf-8").replace("  tema:", "  publicada: false\n  tema:"),
        encoding="utf-8",
    )

    report, site = publish(source, output=tmp_path / "_site", clean=True)
    assert site is not None
    assert any(i.code == "BORRADOR_OMITIDO" for i in report.warnings)
    # Fuera del índice y sin subcarpeta compilada
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "en-el-horno" not in html and 'href="visible/"' in html
    assert not (site / "en-el-horno").exists()
    # build/preview no se ven afectados: el borrador compila por sí solo
    from aulastep.compiler import build

    b_report, dist = build(source / "en-el-horno", output=tmp_path / "borrador-dist")
    assert b_report.ok and dist is not None


def test_borrador_roto_sigue_bloqueando_el_catalogo(tmp_path):
    """La gracia del borrador es que el CI lo vigila: si no valida, falla."""
    source = _make_source(tmp_path, ["visible", "borrador-roto"])
    p = source / "borrador-roto" / "actividad.yml"
    p.write_text(
        p.read_text(encoding="utf-8").replace("  tema:", "  publicada: false\n  tema:"),
        encoding="utf-8",
    )
    (source / "borrador-roto" / "pasos" / "01-presentacion.md").write_text(
        ':::task{id="sin-cierre"}\nrota', encoding="utf-8"
    )
    report, site = publish(source, output=tmp_path / "_site", clean=True)
    assert site is None
    assert any(i.code == "PUBLICACION_ACTIVIDAD_INVALIDA" for i in report.errors)
