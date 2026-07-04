"""Pruebas del flujo de corrección (aulastep grade)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from aulastep.grading import grade_folder, grade_work, inventory, read_aulawork
from aulastep.project import load_project

ACTIVITY_YML = """schema_version: "1.0"
actividad:
  id: demo-corr
  titulo: Demo corrección
  version: 1.0.0
alumno:
  campos:
    - {id: nombre, etiqueta: Nombre, obligatorio: true}
    - {id: grupo, etiqueta: Grupo, obligatorio: false}
"""

STEP = """---
id: unico
titulo: Paso único
---

:::task{id="t1" required="true"}
Haz algo.
:::

:::question{id="q-single" type="single-choice" required="true"}
¿Puerto DHCP?

- [ ] TCP 67
- [x] UDP 67
- [ ] UDP 68
:::

:::question{id="q-multi" type="multi-choice" required="true"}
¿Qué envía el servidor?

- [ ] Discover
- [x] Offer
- [x] Ack
:::

:::question{id="q-texto" type="long-text" required="true"}
Explica DORA.
:::

:::evidence{id="ev1" required="true"}
Captura.
:::
"""

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc000000301010018dd8db00000000049"
    "454e44ae426082"
)


def make_activity(tmp_path: Path) -> Path:
    root = tmp_path / "actividad"
    (root / "pasos").mkdir(parents=True)
    (root / "recursos").mkdir()
    (root / "actividad.yml").write_text(ACTIVITY_YML, encoding="utf-8")
    (root / "pasos" / "01-unico.md").write_text(STEP, encoding="utf-8")
    return root


def make_aulawork(
    path: Path,
    *,
    answers: dict | None = None,
    states: dict | None = None,
    student: dict | None = None,
    with_evidence: bool = True,
    activity_id: str = "demo-corr",
    version: str = "1.0.0",
    schema: str = "1.0",
    tamper: str | None = None,
) -> Path:
    entries: dict[str, bytes] = {
        "student.json": json.dumps(student or {"nombre": "Ana Pérez", "grupo": "2A"}).encode(),
        "answers.json": json.dumps(answers or {}).encode(),
        "progress.json": json.dumps(
            {
                "currentStepId": "unico",
                "startedAt": "2026-07-03T10:00:00.000Z",
                "updatedAt": "2026-07-03T10:30:00.000Z",
                "states": states or {},
            }
        ).encode(),
    }
    attachments = []
    if with_evidence:
        entries["evidence/ev1__captura.png"] = PNG_1PX
        attachments.append(
            {
                "id": "ev1",
                "kind": "evidence",
                "name": "captura.png",
                "mime": "image/png",
                "size": len(PNG_1PX),
                "description": "Mi captura",
                "path": "evidence/ev1__captura.png",
            }
        )
    entries["attachments.json"] = json.dumps(attachments).encode()

    integrity = {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}
    manifest = {
        "format": "aulawork",
        "schemaVersion": schema,
        "generator": {"name": "AulaStep", "version": "test"},
        "activity": {"id": activity_id, "version": version, "titulo": "Demo"},
        "exportedAt": "2026-07-03T10:31:00.000Z",
        "integrity": {"algorithm": "SHA-256", "files": integrity},
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for name, data in entries.items():
            if tamper == name:
                data = data + b"X"
            zf.writestr(name, data)
    return path


GOOD_ANSWERS = {
    "q-single": {
        "value": "q-single-op2",
        "type": "single-choice",
        "updatedAt": "2026-07-03T10:10:00Z",
    },
    "q-multi": {
        "value": ["q-multi-op2", "q-multi-op3"],
        "type": "multi-choice",
        "updatedAt": "2026-07-03T10:20:00Z",
    },
    "q-texto": {
        "value": "Discover, Offer, Request, Ack.",
        "type": "long-text",
        "updatedAt": "2026-07-03T10:25:00Z",
    },
}
GOOD_STATES = {"t1": {"done": True, "updatedAt": "2026-07-03T10:05:00Z"}}


def test_answer_key_solo_en_memoria(tmp_path):
    loader = load_project(make_activity(tmp_path))
    assert loader.report.ok
    key = loader.answer_key
    assert key["q-single"]["correct"] == ["q-single-op2"]
    assert sorted(key["q-multi"]["correct"]) == ["q-multi-op2", "q-multi-op3"]
    assert "q-texto" not in key  # las de texto no tienen clave
    assert '"correct"' not in loader.compiled.to_json()  # y jamás se publica


def test_lectura_valida_y_alteracion_detectada(tmp_path):
    ok = read_aulawork(
        make_aulawork(tmp_path / "ok.aulawork", answers=GOOD_ANSWERS, states=GOOD_STATES),
        "demo-corr",
        "1.0",
    )
    assert ok.ok and ok.student["nombre"] == "Ana Pérez"

    bad = read_aulawork(
        make_aulawork(tmp_path / "bad.aulawork", answers=GOOD_ANSWERS, tamper="answers.json"),
        "demo-corr",
        "1.0",
    )
    assert not bad.ok
    assert any("Integridad" in e for e in bad.errors)


def test_rechaza_otra_actividad_y_otro_esquema(tmp_path):
    otra = read_aulawork(
        make_aulawork(tmp_path / "otra.aulawork", activity_id="otra-cosa"), "demo-corr", "1.0"
    )
    assert not otra.ok and any("otra actividad" in e for e in otra.errors)
    esquema = read_aulawork(
        make_aulawork(tmp_path / "esq.aulawork", schema="2.0"), "demo-corr", "1.0"
    )
    assert not esquema.ok and any("incompatible" in e for e in esquema.errors)


def test_calificacion_completa(tmp_path):
    loader = load_project(make_activity(tmp_path))
    work = read_aulawork(
        make_aulawork(tmp_path / "w.aulawork", answers=GOOD_ANSWERS, states=GOOD_STATES),
        "demo-corr",
        "1.0",
    )
    grade = grade_work(work, inventory(loader), loader.answer_key)
    assert grade["required_total"] == 5
    assert grade["required_done"] == 5 and grade["required_pct"] == 100
    assert grade["choice_total"] == 2 and grade["choice_hits"] == 2
    assert grade["duration_min"] == 30  # 10:00 → 10:30 de progress.json... y respuestas antes


def test_calificacion_con_fallos_y_pendientes(tmp_path):
    loader = load_project(make_activity(tmp_path))
    answers = {
        "q-single": {"value": "q-single-op1", "type": "single-choice"},  # incorrecta
        "q-multi": {"value": ["q-multi-op2"], "type": "multi-choice"},  # parcial = incorrecta
        "q-texto": {"value": "   ", "type": "long-text"},  # en blanco → pendiente
    }
    work = read_aulawork(
        make_aulawork(tmp_path / "w.aulawork", answers=answers, states={}, with_evidence=False),
        "demo-corr",
        "1.0",
    )
    grade = grade_work(work, inventory(loader), loader.answer_key)
    assert grade["choice_hits"] == 0 and grade["choice_total"] == 2
    assert grade["required_done"] == 2  # solo las dos de elección respondidas
    items = {i["id"]: i for i in grade["items"]}
    assert items["q-single"]["correct"] is False and items["q-single"]["answered"] is True
    assert items["q-multi"]["correct"] is False
    assert items["q-texto"]["done"] is False
    assert items["ev1"]["done"] is False and items["t1"]["done"] is False


def test_grade_folder_genera_informe_csv_y_evidencias(tmp_path):
    activity = make_activity(tmp_path)
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    make_aulawork(entregas / "ana.aulawork", answers=GOOD_ANSWERS, states=GOOD_STATES)
    make_aulawork(
        entregas / "luis.aulawork",
        answers={"q-single": {"value": "q-single-op1", "type": "single-choice"}},
        student={"nombre": "Luis Gómez", "grupo": "2A"},
        with_evidence=False,
    )
    make_aulawork(entregas / "rota.aulawork", tamper="answers.json")  # alterada

    report, out = grade_folder(activity, entregas, output=tmp_path / "informe")
    assert out is not None
    assert any(i.code == "CORRECCION_ENTREGA_INVALIDA" for i in report.warnings)

    html = (out / "index.html").read_text(encoding="utf-8")
    assert "Ana Pérez" in html and "Luis Gómez" in html
    assert "rota.aulawork" in html and "Inválida" in html
    assert "✓ correcta" in html and "✗ incorrecta" in html
    assert "Mi captura" in html  # descripción de la evidencia
    assert (out / "evidencias" / "Ana-Perez-2A" / "ev1__captura.png").is_file()

    csv_text = (out / "resumen.csv").read_text(encoding="utf-8-sig")
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("archivo;Nombre;Grupo;")
    assert any("ana.aulawork;Ana Pérez" in line and ";5;5;100;2;2;" in line for line in lines)
    assert any("rota.aulawork" in line and "INVÁLIDA" in line for line in lines)


def test_grade_folder_sin_entregas(tmp_path):
    activity = make_activity(tmp_path)
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    report, out = grade_folder(activity, vacia, output=tmp_path / "informe")
    assert out is None
    assert any(i.code == "CORRECCION_SIN_ENTREGAS" for i in report.errors)


def test_corrupcion_de_zip_no_tumba_el_lote(tmp_path):
    """Alteración de bytes en crudo (rompe el CRC del ZIP, no solo el SHA-256)."""
    activity = make_activity(tmp_path)
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    make_aulawork(entregas / "buena.aulawork", answers=GOOD_ANSWERS, states=GOOD_STATES)
    rota = entregas / "bytes-rotos.aulawork"
    make_aulawork(rota, answers=GOOD_ANSWERS)
    rota.write_bytes(rota.read_bytes().replace(b"q-single-op2", b"q-single-op1"))

    _report, out = grade_folder(activity, entregas, output=tmp_path / "informe")
    assert out is not None  # el lote se completa
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "bytes-rotos.aulawork" in html and "corrupto" in html
    assert "Ana Pérez" in html  # la buena se corrigió


def test_informe_incluye_navegacion_entre_alumnos(tmp_path):
    activity = make_activity(tmp_path)
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    make_aulawork(entregas / "ana.aulawork", answers=GOOD_ANSWERS, states=GOOD_STATES)
    make_aulawork(
        entregas / "luis.aulawork",
        answers={},
        student={"nombre": "Luis Gómez", "grupo": "2A"},
        with_evidence=False,
    )
    make_aulawork(entregas / "rota.aulawork", tamper="answers.json")

    _report, out = grade_folder(activity, entregas, output=tmp_path / "informe")
    html = (out / "index.html").read_text(encoding="utf-8")
    # Barra: botones, selector y vuelta al resumen
    assert 'id="nav-prev"' in html and 'id="nav-next"' in html
    assert 'id="nav-alumnos"' in html and 'href="#resumen"' in html
    # El selector lista a los válidos y NO a la entrega rota
    assert html.count("<option") == 2
    assert "Ana Pérez" in html.split('id="nav-alumnos"')[1].split("</select>")[0]
    assert "rota.aulawork" not in html.split('id="nav-alumnos"')[1].split("</select>")[0]
    # Los ids de opción y de sección están alineados
    import re

    option_ids = re.findall(r'<option value="(entrega-\d+)"', html)
    section_ids = re.findall(r'<section class="student" id="(entrega-\d+)"', html)
    assert option_ids == section_ids
