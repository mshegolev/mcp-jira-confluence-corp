"""XHTML шаблон для Confluence-страницы аудита тестирования PBC."""

from string import Template

# Confluence Storage Format (XHTML) — шаблон страницы аудита PBC
EP_AUDIT_PAGE_TEMPLATE = Template(
    """<ac:structured-macro ac:name="info" ac:schema-version="1">
<ac:rich-text-body>
<p>Автоматически сгенерировано: <strong>${generated_date}</strong> | QA Assistant EP Audit</p>
</ac:rich-text-body>
</ac:structured-macro>

<h1>1. Паспорт PBC</h1>
<table>
<tbody>
<tr><th>Поле</th><th>Значение</th></tr>
<tr><td>Ключ</td><td><strong>${pbc_key}</strong></td></tr>
<tr><td>Название</td><td>${pbc_name}</td></tr>
<tr><td>Tribe</td><td>${tribe}</td></tr>
<tr><td>Jira ID</td><td>${jira_id}</td></tr>
<tr><td>Allure TestOps ID</td><td>${testops_id}</td></tr>
<tr><td>SonarQube</td><td>${sonarqube_pattern}</td></tr>
<tr><td>GitLab</td><td>${gitlab_pattern}</td></tr>
</tbody>
</table>

<h1>2. Quality Gates Summary</h1>
${quality_gates_section}

<h1>3. Тестовое покрытие (Allure TestOps)</h1>
${allure_section}

<h1>4. Test Gap Analysis</h1>
${test_gap_section}

<h1>5. Качество кода (SonarQube)</h1>
${sonarqube_section}

<h1>6. Дефекты (Jira)</h1>
${jira_defects_section}

<h1>7. CI/CD и процесс (GitLab)</h1>
${gitlab_section}

<h1>8. Зрелость тестирования</h1>
${maturity_section}

<h1>9. Риски и рекомендации</h1>
${risks_section}
"""
)


def _status_macro(status: str, text: str) -> str:
    """Генерирует Confluence status macro.

    Args:
        status: green/yellow/red/grey
        text: Текст статуса
    """
    color_map = {"green": "Green", "yellow": "Yellow", "red": "Red", "grey": "Grey"}
    color = color_map.get(status, "Grey")
    return f'<ac:structured-macro ac:name="status" ac:schema-version="1"><ac:parameter ac:name="colour">{color}</ac:parameter><ac:parameter ac:name="title">{text}</ac:parameter></ac:structured-macro>'


def _metric_status(value, good_threshold, warn_threshold, higher_is_better=True, fmt="{:.1f}%") -> str:
    """Возвращает status macro для метрики.

    Args:
        value: Значение метрики (может быть None)
        good_threshold: Порог для green
        warn_threshold: Порог для yellow
        higher_is_better: True если больше = лучше
        fmt: Формат отображения
    """
    if value is None:
        return _status_macro("grey", "N/A")

    val = float(value)
    text = fmt.format(val)

    if higher_is_better:
        if val >= good_threshold:
            return _status_macro("green", text)
        elif val >= warn_threshold:
            return _status_macro("yellow", text)
        else:
            return _status_macro("red", text)
    else:
        if val <= good_threshold:
            return _status_macro("green", text)
        elif val <= warn_threshold:
            return _status_macro("yellow", text)
        else:
            return _status_macro("red", text)


def render_quality_gates_section(gates_data: dict) -> str:
    """Рендерит секцию Quality Gates."""
    if not gates_data:
        return "<p><em>Quality Gates не настроены или данные недоступны</em></p>"

    overall = gates_data.get("overall_status", "unknown")
    score = gates_data.get("overall_score", 0)
    status_color = {"passed": "green", "warning": "yellow", "failed": "red"}.get(overall, "grey")

    rows = f"""<p>Общий статус: {_status_macro(status_color, f"{overall.upper()} ({score:.0f}/100)")}</p>
<table>
<tbody>
<tr><th>Gate</th><th>Статус</th><th>Score</th><th>Нарушения</th></tr>"""

    for gate in gates_data.get("gates", []):
        g_status = gate.get("status", "unknown")
        g_color = {"passed": "green", "warning": "yellow", "failed": "red"}.get(g_status, "grey")
        rows += f"""<tr>
<td>{gate.get('name', gate.get('code', ''))}</td>
<td>{_status_macro(g_color, g_status.upper())}</td>
<td>{gate.get('score', 0):.0f}</td>
<td>{gate.get('violations_count', 0)}</td>
</tr>"""

    rows += "</tbody></table>"
    return rows


def render_allure_section(allure_data: dict) -> str:
    """Рендерит секцию тестового покрытия."""
    if not allure_data:
        return "<p><em>Allure TestOps не настроен для данного PBC</em></p>"

    return f"""<table>
<tbody>
<tr><th>Метрика</th><th>Значение</th><th>Benchmark</th></tr>
<tr><td>Всего тест-кейсов</td><td><strong>{allure_data.get('total_testcases', 0)}</strong></td><td>—</td></tr>
<tr><td>Автоматизированные</td><td>{allure_data.get('automated_testcases', 0)}</td><td>—</td></tr>
<tr><td>Ручные</td><td>{allure_data.get('manual_testcases', 0)}</td><td>—</td></tr>
<tr><td>Automation Rate</td><td>{_metric_status(allure_data.get('automation_rate'), 60, 40)}</td><td>&gt; 60%</td></tr>
<tr><td>Pass Rate</td><td>{_metric_status(allure_data.get('test_pass_rate'), 95, 85)}</td><td>&gt; 95%</td></tr>
<tr><td>Flaky Rate</td><td>{_metric_status(allure_data.get('flaky_rate'), 5, 10, higher_is_better=False)}</td><td>&lt; 5%</td></tr>
<tr><td>Запусков</td><td>{allure_data.get('total_launches', 0)}</td><td>—</td></tr>
</tbody>
</table>"""


def render_test_gap_section(gap_data: dict) -> str:
    """Рендерит секцию Test Gap Analysis."""
    if not gap_data:
        return "<p><em>Test Gap Analysis не выполнен</em></p>"

    return f"""<table>
<tbody>
<tr><th>Метрика</th><th>Значение</th><th>Benchmark</th></tr>
<tr><td>Story всего</td><td>{gap_data.get('stories_total', 0)}</td><td>—</td></tr>
<tr><td>Story покрыты тестами</td><td>{gap_data.get('stories_covered', 0)}</td><td>—</td></tr>
<tr><td>Story без тестов</td><td>{gap_data.get('stories_uncovered', 0)}</td><td>—</td></tr>
<tr><td>Gap Rate</td><td>{_metric_status(gap_data.get('gap_rate'), 20, 30, higher_is_better=False)}</td><td>&lt; 20%</td></tr>
</tbody>
</table>"""


def render_sonarqube_section(sonar_data: dict) -> str:
    """Рендерит секцию SonarQube."""
    if not sonar_data:
        return "<p><em>SonarQube не настроен для данного PBC</em></p>"

    qg = sonar_data.get("quality_gate_status", "")
    qg_color = "green" if qg == "OK" else ("red" if qg else "grey")
    qg_text = qg if qg else "N/A"

    return f"""<table>
<tbody>
<tr><th>Метрика</th><th>Значение</th><th>Benchmark</th></tr>
<tr><td>Coverage</td><td>{_metric_status(sonar_data.get('coverage'), 60, 40)}</td><td>&gt; 60%</td></tr>
<tr><td>Bugs</td><td>{_metric_status(sonar_data.get('bugs'), 0, 5, higher_is_better=False, fmt='{:.0f}')}</td><td>0</td></tr>
<tr><td>Vulnerabilities</td><td>{_metric_status(sonar_data.get('vulnerabilities'), 0, 3, higher_is_better=False, fmt='{:.0f}')}</td><td>0</td></tr>
<tr><td>Code Smells</td><td>{sonar_data.get('code_smells', 0)}</td><td>—</td></tr>
<tr><td>Tech Debt</td><td>{sonar_data.get('tech_debt_days', 'N/A')}d</td><td>—</td></tr>
<tr><td>Duplications</td><td>{_metric_status(sonar_data.get('duplicated_lines_density'), 3, 5, higher_is_better=False)}</td><td>&lt; 3%</td></tr>
<tr><td>Quality Gate</td><td>{_status_macro(qg_color, qg_text)}</td><td>OK</td></tr>
</tbody>
</table>"""


def render_jira_defects_section(jira_data: dict) -> str:
    """Рендерит секцию дефектов из Jira."""
    if not jira_data:
        return "<p><em>Данные Jira недоступны</em></p>"

    return f"""<table>
<tbody>
<tr><th>Метрика</th><th>Значение</th><th>Benchmark</th></tr>
<tr><td>Открытые баги</td><td>{jira_data.get('open_bugs', 0)}</td><td>—</td></tr>
<tr><td>Critical/Blocker</td><td>{_metric_status(jira_data.get('critical_bugs', 0) + jira_data.get('blocker_bugs', 0), 0, 2, higher_is_better=False, fmt='{:.0f}')}</td><td>0</td></tr>
<tr><td>Reopened</td><td>{jira_data.get('reopened_bugs', 0)}</td><td>—</td></tr>
<tr><td>MTTR (часы)</td><td>{_metric_status(jira_data.get('mttr_hours'), 24, 48, higher_is_better=False, fmt='{:.1f}h')}</td><td>&lt; 24h</td></tr>
<tr><td>Баги за 7д (создано)</td><td>{jira_data.get('bugs_created_last_7d', 0)}</td><td>—</td></tr>
<tr><td>Баги за 7д (закрыто)</td><td>{jira_data.get('bugs_closed_last_7d', 0)}</td><td>—</td></tr>
</tbody>
</table>"""


def render_gitlab_section(gitlab_data: dict) -> str:
    """Рендерит секцию CI/CD."""
    if not gitlab_data:
        return "<p><em>GitLab не настроен для данного PBC</em></p>"

    return f"""<table>
<tbody>
<tr><th>Метрика</th><th>Значение</th><th>Benchmark</th></tr>
<tr><td>Pipeline Success Rate</td><td>{_metric_status(gitlab_data.get('pipeline_success_rate'), 90, 75)}</td><td>&gt; 90%</td></tr>
<tr><td>Pipelines (total)</td><td>{gitlab_data.get('pipelines_total', 0)}</td><td>—</td></tr>
<tr><td>Pipelines (failed)</td><td>{gitlab_data.get('pipelines_failed', 0)}</td><td>—</td></tr>
<tr><td>MR Review Rate</td><td>{_metric_status(gitlab_data.get('mr_review_rate'), 80, 60)}</td><td>&gt; 80%</td></tr>
<tr><td>MR (total)</td><td>{gitlab_data.get('total_mrs', 0)}</td><td>—</td></tr>
<tr><td>MR Lead Time</td><td>{_metric_status(gitlab_data.get('avg_mr_lead_time_hours'), 24, 48, higher_is_better=False, fmt='{:.1f}h')}</td><td>&lt; 24h</td></tr>
</tbody>
</table>"""


def render_maturity_section(maturity_data: dict) -> str:
    """Рендерит секцию зрелости тестирования."""
    if not maturity_data:
        return "<p><em>Оценка зрелости не проводилась</em></p>"

    level = maturity_data.get("level", 0)
    level_color = "green" if level >= 3 else ("yellow" if level >= 2 else "red")

    rows = f"<p>Уровень зрелости: {_status_macro(level_color, f'Level {level}')}</p>"

    dimensions = maturity_data.get("dimensions", {})
    if dimensions:
        rows += """<table>
<tbody>
<tr><th>Направление</th><th>Уровень</th></tr>"""
        for dim_name, dim_level in dimensions.items():
            d_color = "green" if dim_level >= 3 else ("yellow" if dim_level >= 2 else "red")
            rows += f"<tr><td>{dim_name}</td><td>{_status_macro(d_color, f'Level {dim_level}')}</td></tr>"
        rows += "</tbody></table>"

    return rows


def render_risks_section(violations: list) -> str:
    """Рендерит секцию рисков и рекомендаций из нарушений benchmarks."""
    if not violations:
        return '<ac:structured-macro ac:name="info" ac:schema-version="1"><ac:rich-text-body><p>Критичных нарушений benchmarks не обнаружено.</p></ac:rich-text-body></ac:structured-macro>'

    rows = """<table>
<tbody>
<tr><th>#</th><th>Область</th><th>Проблема</th><th>Benchmark</th><th>Приоритет</th></tr>"""
    for i, v in enumerate(violations, 1):
        severity = v.get("severity", "medium")
        s_color = {"high": "red", "medium": "yellow", "low": "green"}.get(severity, "grey")
        rows += f"""<tr>
<td>{i}</td>
<td>{v.get('area', '')}</td>
<td>{v.get('problem', '')}</td>
<td>{v.get('benchmark', '')}</td>
<td>{_status_macro(s_color, severity.upper())}</td>
</tr>"""

    rows += "</tbody></table>"
    return rows
