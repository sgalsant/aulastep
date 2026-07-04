"""Pruebas del parser de directivas ':::tipo{...}'."""

from aulastep.directives import parse_attrs, parse_choices, split_chunks
from aulastep.errors import Report


def test_segmentacion_basica():
    body = 'Intro.\n\n:::task{id="t1" required="true"}\nHaz algo.\n:::\n\nFinal.'
    report = Report()
    chunks = split_chunks(body, report)
    assert report.ok
    kinds = [c.kind for c in chunks]
    assert kinds == ["markdown", "directive", "markdown"]
    directive = chunks[1].directive
    assert directive.kind == "task"
    assert directive.id == "t1"
    assert directive.required is True
    assert directive.body == "Haz algo."


def test_directiva_dentro_de_fence_no_se_interpreta():
    body = '```bash\n:::task{id="falsa"}\n:::\n```\n'
    report = Report()
    chunks = split_chunks(body, report)
    assert report.ok
    assert len(chunks) == 1
    assert chunks[0].kind == "markdown"
    assert ":::task" in chunks[0].text


def test_directiva_sin_cierre_es_error():
    report = Report()
    split_chunks(':::note{id="n"}\nsin cierre', report, "paso.md")
    assert any(i.code == "DIRECTIVA_SIN_CIERRE" for i in report.errors)


def test_directiva_desconocida_es_error():
    report = Report()
    split_chunks(':::baile{id="x"}\n:::', report)
    assert any(i.code == "DIRECTIVA_DESCONOCIDA" for i in report.errors)


def test_parse_attrs():
    attrs = parse_attrs('{id="q1" type="single-choice" required="true"}')
    assert attrs == {"id": "q1", "type": "single-choice", "required": "true"}


def test_parse_choices():
    prompt, options = parse_choices("¿Cuál?\n\n- [ ] Una\n- [x] Dos\n- [ ] Tres")
    assert prompt == "¿Cuál?"
    assert options == [("Una", False), ("Dos", True), ("Tres", False)]
