"""Confluence page templates."""

import pathlib
from string import Template

from config.config import PROJECT_ROOT_PATH

TITLE_PARENT_RELEASES = "Релизы"
TITLE_PARENT_REPORTING = "QA - Отчетность"
TITLE_PAGE_TRACEABILITY_MATRIX = "QA - Матрица покрытия требований"

template_content_GLD = Template(
    pathlib.Path(
        PROJECT_ROOT_PATH.as_posix() + "/qa_assistant/templates/confluence_templates/template_content_GLD.html"
    ).read_text(encoding="utf-8")
)

template_content_EINVY = Template(
    pathlib.Path(
        PROJECT_ROOT_PATH.as_posix() + "/qa_assistant/templates/confluence_templates/template_content_EINVY.html"
    ).read_text(encoding="utf-8")
)
template_content_EDOFFR = Template(
    pathlib.Path(
        PROJECT_ROOT_PATH.as_posix() + "/qa_assistant/templates/confluence_templates/template_content_EDOFFR.html"
    ).read_text(encoding="utf-8")
)
template_content_ESCART = Template(
    pathlib.Path(
        PROJECT_ROOT_PATH.as_posix() + "/qa_assistant/templates/confluence_templates/template_content_ESCART.html"
    ).read_text(encoding="utf-8")
)

template_content_performance_release = Template(
    pathlib.Path(
        PROJECT_ROOT_PATH.as_posix()
        + "/qa_assistant/templates/confluence_templates/template_content_performance_release.html"
    ).read_text(encoding="utf-8")
)

template_content_traceability_matrix = Template(
    pathlib.Path(
        PROJECT_ROOT_PATH.as_posix() + "/qa_assistant/templates/confluence_templates/template_traceability_matrix.html"
    ).read_text(encoding="utf-8")
)

CONFLUENCE_RELEASE_TEMPLATES = {
    "EINVY": template_content_EINVY,
    "ESCART": template_content_ESCART,
    "EDOFFR": template_content_EDOFFR,
    "GLD": template_content_GLD,
}
