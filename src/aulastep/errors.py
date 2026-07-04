"""Incidencias de validación: errores y avisos con ubicación."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Level(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Issue:
    level: Level
    code: str
    message: str
    location: str = ""

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.level.value.upper()} {self.code}: {self.message}{loc}"


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    def error(self, code: str, message: str, location: str = "") -> None:
        self.issues.append(Issue(Level.ERROR, code, message, location))

    def warning(self, code: str, message: str, location: str = "") -> None:
        self.issues.append(Issue(Level.WARNING, code, message, location))

    def extend(self, other: Report) -> None:
        self.issues.extend(other.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level is Level.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level is Level.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors


class AulaStepError(Exception):
    """Error fatal de la herramienta con informe asociado."""

    def __init__(self, message: str, report: Report | None = None) -> None:
        super().__init__(message)
        self.report = report or Report()
