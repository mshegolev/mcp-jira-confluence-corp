# mypy: ignore-errors

import html
import logging
import pathlib
import re
from datetime import date
from typing import Any, Optional

import pandas as pd
from atlassian import Confluence
from atlassian.errors import ApiError

from config.config import ACCOUNT_PASSWORD, ACCOUNT_USER, CONFLUENCE_TOKEN, CONFLUENCE_URL, JIRA_URL
from qa_assistant.confluence_helper.creator_qa_space import CreatorQaSpace
from qa_assistant.confluence_helper.templates import (
    CONFLUENCE_RELEASE_TEMPLATES,
    TITLE_PAGE_TRACEABILITY_MATRIX,
    TITLE_PARENT_RELEASES,
    template_content_performance_release,
    template_content_traceability_matrix,
)
from qa_assistant.exceptions.exceptions import CantFindReleaseDescription
from qa_assistant.manager_helpers.issue_types import IssueTypes
from qa_assistant.manager_helpers.jira_helper import JiraHelper
from qa_assistant.manager_helpers.version_helper import VersionHelper
from qa_assistant.project_helper.projects import Project


class GenerateLoadPage:
    def __init__(  # noqa: С901
        self,
        conclusions=None,
        recommendations=None,
        devops=None,
        crq_number=None,
        period_and_time=None,
        short_description=None,
        risks=None,
        unavailable_processes=None,
        purpose_of_work=None,
        reason_for_change=None,
        description_of_dependencies=None,
        affect_gql_contract=None,
        working_description=None,
        rollback_plan=None,
        user_impact=None,
    ):
        if conclusions is None:
            self.conclusions = ""
        else:
            self.conclusions = conclusions
        if recommendations is None:
            self.recommendations = ""
        else:
            self.recommendations = recommendations
        if devops is None:
            self.devops = ""
        else:
            self.devops = devops
        if crq_number is None:
            self.crq_number = ""
        else:
            self.crq_number = crq_number

        if period_and_time is None:
            self.period_and_time = ""
        else:
            self.period_and_time = period_and_time

        if short_description is None:
            self.short_description = ""
        else:
            self.short_description = short_description

        if risks is None:
            self.risks = ""
        else:
            self.risks = risks

        if unavailable_processes is None:
            self.unavailable_processes = ""
        else:
            self.unavailable_processes = unavailable_processes

        if purpose_of_work is None:
            self.purpose_of_work = ""
        else:
            self.purpose_of_work = purpose_of_work

        if reason_for_change is None:
            self.reason_for_change = ""
        else:
            self.reason_for_change = reason_for_change

        if description_of_dependencies is None:
            self.description_of_dependencies = ""
        else:
            self.description_of_dependencies = description_of_dependencies

        if affect_gql_contract is None:
            self.affect_gql_contract = ""
        else:
            self.affect_gql_contract = affect_gql_contract

        if working_description is None:
            self.working_description = ""
        else:
            self.working_description = working_description

        if rollback_plan is None:
            self.rollback_plan = ""
        else:
            self.rollback_plan = rollback_plan

        if user_impact is None:
            self.user_impact = ""
        else:
            self.user_impact = user_impact

    def __str__(self):
        return template_content_performance_release.substitute(
            conclusions=self.conclusions,
            devops=self.devops,
            crq_number=self.crq_number,
            period_and_time=self.period_and_time,
            short_description=self.short_description,
            risks=self.risks,
            unavailable_processes=self.unavailable_processes,
            purpose_of_work=self.purpose_of_work,
            reason_for_change=self.reason_for_change,
            description_of_dependencies=self.description_of_dependencies,
            affect_gql_contract=self.affect_gql_contract,
            working_description=self.working_description,
            rollback_plan=self.rollback_plan,
            user_impact=self.user_impact,
            recommendations=self.recommendations,
        )


class GenerateTraceAbilityMatrixPage:
    def __init__(self, table_row=None):
        if table_row is None:
            self.table_row = ""
        else:
            self.table_row = table_row

    def __str__(self):
        return template_content_traceability_matrix.substitute(table_row=self.table_row)


class ConfluenceHelper(CreatorQaSpace):
    def __init__(self, project: Project):
        assert isinstance(project, Project)
        self.project = project
        self.project_name = project.name
        self.space = project.space

        if CONFLUENCE_TOKEN:
            self._confluence = Confluence(
                url=CONFLUENCE_URL,
                token=CONFLUENCE_TOKEN,
                verify_ssl=False,
            )
        else:
            self._confluence = Confluence(
                url=CONFLUENCE_URL,
                username=ACCOUNT_USER,
                password=ACCOUNT_PASSWORD,
                verify_ssl=False,
            )
        self._version_helper_value: Optional[VersionHelper] = None
        self._jira_helper_value: Optional[JiraHelper] = None

    @property
    def JiraHelper(self) -> JiraHelper:
        if self._jira_helper_value is None:
            self._jira_helper_value = JiraHelper(project=self.project)
        return self._jira_helper_value

    @property
    def VersionHelper(self) -> VersionHelper:
        if self._version_helper_value is None:
            self._version_helper_value = VersionHelper(project=self.project)
        return self._version_helper_value

    def generate_release_page(self, fix_version: str, override_versions: bool = True):
        qa_task = self.generate_qa_task_section(fix_version)
        goals = self.generate_goals_section(fix_version)
        release_content = self.generate_issues_section(fix_version)
        # todo: fix sso auth
        if override_versions:
            integration_system_versions = self.VersionHelper.get_integration_versions_html()
        else:
            integration_system_versions = ""
        affect_gql_contract = self.get_graphql_schema_changes(fix_version=fix_version)
        if not affect_gql_contract:
            affect_gql_contract = "<h4> совместима </h4>"

        template = CONFLUENCE_RELEASE_TEMPLATES.get(self.project.key, None)
        if template is None:
            raise NameError(f"Установите шаблон для проекта {self.project.key}")
        content = template.substitute(
            fix_version=fix_version,
            goals=goals,
            qa_verification_task=qa_task,
            release_content=release_content,
            project=self.project.key,
            integration_system_versions=integration_system_versions,
            affect_gql_contract=affect_gql_contract,
        )
        return content

    def generate_issues_section(self, fix_version, contents=""):
        errors_section = "<h2>9.1. Исправленные ошибки</h2>"
        story_section = "<h2>9.2. Сделанные истории</h2>"
        is_bug_section_exists = False
        if not contents:
            issues = self.JiraHelper.get_issues_release_notes(fix_version=fix_version)
            for issue in issues:
                if int(issue.fields.issuetype.id) in [IssueTypes(project=self.project).bug_id]:
                    errors_section += self.create_li_string(issue)
                    is_bug_section_exists = True
                else:
                    story_section += self.create_li_string(issue)
            if not is_bug_section_exists:
                errors_section += "<p>нет</p>"
            contents = errors_section + story_section
        return contents

    def create_li_string(self, issue):
        url = JIRA_URL + "/browse/" + str(issue.key)
        key = issue.key
        name = self.clean_string_for_xhtml(issue.fields.summary)
        return f"""<li>[<a href="{url}">{key}</a>]<span> </span>{name}</li>"""

    @staticmethod
    def clean_string_for_xhtml(string):
        cleaned_string = html.escape(string)
        return cleaned_string

    def generate_qa_task_section(self, fix_version):
        qa_task = self.JiraHelper.get_qa_verification_task(fix_version=fix_version)
        if not qa_task:
            # Fallback: используем Release-задачу (v2) вместо подзадачи верификации
            qa_task = self.JiraHelper.get_issue_release(fix_version_name=fix_version, release_type="v2")
        if not qa_task:
            logging.warning(f"Не найдена задача на релиз для: {fix_version}")
            return "<em>задача релиза не найдена</em>"
        url = self.JiraHelper.jira_options.get("server", "") + "/browse/" + qa_task.key
        return f"""<a href="{url}">{qa_task.key}</a>"""

    def get_fix_versions(self):
        return self.JiraHelper.get_versions()

    def create_release_page(
        self,
        fix_version: str,
        space=None,
        title=None,
        body=None,
        parent_page_id=None,
        override_page=False,
        override_versions=True,
    ) -> Any:
        if (
            self.JiraHelper.is_release_task_closed(fix_version=fix_version)
            and self._confluence.get_page_id(space, TITLE_PARENT_RELEASES)
            and override_page is False
        ):
            return self

        if space is None:
            space = self.space
        if title is None:
            title = f"Релиз {self.project.key.upper()} {fix_version}"
        if body is None:
            body = self.generate_release_page(fix_version=fix_version, override_versions=override_versions)
        if parent_page_id is None:
            parent_page_id = self._confluence.get_page_id(space, TITLE_PARENT_RELEASES)
        assert parent_page_id is not None, "Создайте главную страницу Релизы в проекте"
        if override_page or not self._confluence.get_page_id(space=space, title=title):
            release_page = self._confluence.update_or_create(parent_id=parent_page_id, title=title, body=body)
            assert release_page, "Что-то пошло не так, страница не создана"
        else:
            page_id = self._confluence.get_page_id(space=space, title=title)
            release_page = self._confluence.get_page_by_id(page_id=page_id)
        url = release_page.get("_links").get("base") + release_page.get("_links").get("webui")
        logging.info(msg=f"Описание релиза {fix_version}: {url}")
        return self

    def get_page_id(self, title, space=None) -> int | None:
        page_id = None
        if space is None:
            space = self.space
        try:
            page_id = self._confluence.get_page_id(space, title)
        except Exception as e:
            logging.warning(e)
        return page_id

    def get_release_page_link(self, fix_version):
        title = f"Релиз {self.project.key.upper()} {fix_version}"
        page_id = self._confluence.get_page_id(self.space, title)
        if page_id:
            link = CONFLUENCE_URL + "/pages/viewpage.action?pageId=%s" % page_id
        else:
            raise NameError("Страница с релизом не найдена! Создайте страницу.")
        return link

    def get_goal_raw_description(self, fix_version: str) -> str:
        """Получает описание версии релиза из Jira.

        Args:
            fix_version: Название версии релиза.

        Returns:
            Описание версии из Jira или пустая строка если описание не заполнено.

        Raises:
            CantFindReleaseDescription: Если версия не найдена в Jira.
        """
        try:
            version = self.JiraHelper._jira.get_project_version_by_name(self.project.key, fix_version)
        except Exception as e:
            logging.error(f"Не удалось получить версию {fix_version} из Jira: {e}")
            raise CantFindReleaseDescription(fix_version) from e

        if version is None:
            logging.error(f"Версия {fix_version} не найдена в проекте {self.project.key}")
            raise CantFindReleaseDescription(fix_version)

        # Проверяем что description существует и не пустое
        description = getattr(version, "description", None)

        if description is None or (isinstance(description, str) and description.strip() == ""):
            jira_url = f"{JIRA_URL}/projects/{self.project.key}/versions"
            warning_msg = (
                f"\n{'=' * 60}\n"
                f"ПРЕДУПРЕЖДЕНИЕ: Поле 'Description' не заполнено для версии {fix_version}\n"
                f"{'=' * 60}\n"
                f"\n"
                f"Раздел 'Цели релиза' будет пустым.\n"
                f"\n"
                f"Рекомендации:\n"
                f"  1. Откройте Jira: {jira_url}\n"
                f"  2. Найдите версию: {fix_version}\n"
                f"  3. Заполните поле 'Description' (цели релиза, номера историй/багов)\n"
                f"\n"
                f"{'=' * 60}"
            )
            logging.warning(warning_msg)
            return ""

        return description

    def generate_goals_section(self, fix_version: str):
        result = ""
        pattern = self.project_name + r"-\d+"
        description = self.get_goal_raw_description(fix_version=fix_version)

        issues = re.findall(pattern, description)
        if issues:
            for issue in issues:
                _ = self.JiraHelper.get_issue(issue)
                key = _.key
                name = _.fields.summary
                url = self.JiraHelper._jira.server_url + "/browse/" + key
                result += f"""<li>[<a href="{url}">{key}</a>]<span> </span>{name}</li>"""
        else:
            result = description

        return result

    def create_load_page(
        self,
        title="QA - НТ - FORIS - PROD - 2023-06-19",
        target_system="FORIS",
        override: bool = False,
        override_conclusions: bool = False,
        override_recommendations: bool = False,
    ) -> str:
        parent_page = "QA - НТ - " + target_system
        page_id = self.get_page_id(title=title, space=self.project.space)
        if page_id is None or override is True:
            conclusions = None if override_conclusions else self.get_page_exist_conclusions(page_id)
            recommendations = None if override_recommendations else self.get_page_exist_recommendations(page_id)
            performance_page_content = str(
                self.generate_load_page(conclusions=conclusions, recommendations=recommendations)
            )
            parent_page_id = self._confluence.get_page_id(self.project.space, parent_page)
            assert parent_page_id is not None, "Создайте главную страницу для отчетов по тестированию"
            performance_page = self._confluence.update_or_create(
                parent_id=parent_page_id, title=title, body=performance_page_content
            )
            assert performance_page, "Что-то пошло не так, станица не создана"
            url = performance_page.get("_links").get("base") + performance_page.get("_links").get("webui")
            logging.info(url)
        return url

    @staticmethod
    def generate_traceability_matrix_page(table_row=None):
        return GenerateTraceAbilityMatrixPage(table_row=table_row)

    @staticmethod
    def generate_load_page(
        conclusions=None,
        recommendations=None,
        devops=None,
        crq_number=None,
        period_and_time=None,
        short_description=None,
        risks=None,
        unavailable_processes=None,
        purpose_of_work=None,
        reason_for_change=None,
        description_of_dependencies=None,
        affect_gql_contract=None,
        working_description=None,
        rollback_plan=None,
        user_impact=None,
    ):
        return GenerateLoadPage(
            conclusions,
            recommendations,
            devops,
            crq_number,
            period_and_time,
            short_description,
            risks,
            unavailable_processes,
            purpose_of_work,
            reason_for_change,
            description_of_dependencies,
            affect_gql_contract,
            working_description,
            rollback_plan,
            user_impact,
        )

    def get_graphql_schema_changes(self, fix_version) -> str | None:
        title = f"Ошибки совместимости сабграфа {fix_version}"
        page_content = None
        if self._confluence.page_exists(self.project.space, title):
            schema_validation_page_id = self._confluence.get_page_id(self.project.space, title=title)
            if schema_validation_page_id:
                page_content = self._confluence.get_page_by_id(
                    schema_validation_page_id, "space,body.view,version,container"
                )
                page_content = page_content.get("body").get("view").get("value")
        return page_content

    @staticmethod
    def generate_performance_page(
        devops=None,
        period_and_time=None,
        crq_number=None,
        short_description=None,
        risks=None,
        unavailable_process=None,
        purpose_of_work=None,
        reason_for_change=None,
        description_of_dependencies=None,
        affect_gql_contract=None,
        working_description=None,
        rollback_plan=None,
        user_impact=None,
        testing_act=None,
    ):
        template = template_content_performance_release
        if devops is None:
            devops = "Щеголев М.В."
        if period_and_time is None:
            period_and_time = "30.05.2023 с 11:00 по 30.05.2023 16:00"
        if crq_number is None:
            crq_number = "Будет добавлен после согласования работ"
        if short_description is None:
            short_description = (
                "<p>Профиль №12:</p>"
                "<p>на GetInvolvedProductsByMsisdn плавный рост за 2 минут"
                " до 200 RPS + 10 минут нагрузку в 200 RPS</p>"
            )
        if risks is None:
            risks = (
                "Возможное влияние на Регионы: МСК, Поволжье, ЮГ, СЗ, Сибирь: - "
                "Может быть влияние на потребителей GetProducts. - По методам CustomerInformation"
                " влияние может быть на CM - По GetInvolvedProductsByMsisdn на ОМ, RD, FIGA."
            )
        if unavailable_process is None:
            unavailable_process = (
                "<p>Возможное влияние</p><p>на Регионы: МСК, Поволжье, ЮГ, СЗ, Сибирь: - "
                "Может быть влияние на потребителей GetProducts. - По методам CustomerInformation "
                "влияние может быть на CM - По GetInvolvedProductsByMsisdn на ОМ, RD, FIGA. </p>"
            )
        if purpose_of_work is None:
            purpose_of_work = (
                "<p>Профиль №12:</p> <p>на GetInvolvedProductsByMsisdn плавный рост за 2 минут до "
                "200 RPS + 10 минут нагрузку в 200 RPS</p>"
            )
        if reason_for_change is None:
            reason_for_change = "Испытания проводятся повторно на новых данных 5 млн с запросом через Федерацию (реализация на стороне EP)"

        if description_of_dependencies is None:
            description_of_dependencies = "<p>Возможное влияние на Регионы: МСК, Поволжье, ЮГ, СЗ, Сибирь: - Может быть влияние на потребителей GetProducts. - По методам CustomerInformation влияние может быть на CM - По GetInvolvedProductsByMsisdn на ОМ, RD, FIGA. </p>"

        if affect_gql_contract is None:
            affect_gql_contract = "нет"

        if working_description is None:
            working_description = "<p> TBD!Описать каждый раунд!!!! ${load_rounds}</p>"

        if rollback_plan is None:
            rollback_plan = """
            <p>
            Если пользователь находиться в активной сессии, нажать "CTRL+C".
            Если пользователь подключился к контейнеру, то выполнить команду "kill $(ps aux | grep '[p]ython3 -m
            locust' | awk '{print $1}')"</p>"""
        if user_impact is None:
            user_impact = """<p> Возможное влияние на Регионы: МСК, Поволжье, ЮГ, СЗ, Сибирь: При деградации сервисов FIGA возможны
                таймауты
                от
                Foris для внешних систем-потребителей (Единое Окно, Мой МТС, ЛК МТС Бизнес и другие) по запросам
                получения
                информации по услугам, тарифным планам, информации по абоненту. Для служб OrderManagement,
                CustomerManagement:
                Если превысим кол-во свободных потоков то получим ошибки Connection timeout Если нагрузка на сервера,
                где
                работаю эти службы, приблизиться 100% по ресурсам, то возможно увеличение времени работы этих методов и
                как
                следствие влияние на сервисные операции, блокировки и продажи. P.s. по предварительной оценке рост
                нагрузки
                на
                указанные службы + 100% от дневной нагрузки.</p>"""

        if testing_act is None:
            testing_act = """<p> Раздел Результаты испытаний, методики испытаний</p>"""

        content = template.safe_substitute(
            devops=devops,
            period_and_time=period_and_time,
            crq_number=crq_number,
            short_description=short_description,
            risks=risks,
            unavailable_process=unavailable_process,
            purpose_of_work=purpose_of_work,
            reason_for_change=reason_for_change,
            description_of_dependencies=description_of_dependencies,
            affect_gql_contract=affect_gql_contract,
            working_description=working_description,
            rollback_plan=rollback_plan,
            user_impact=user_impact,
            testing_act=testing_act,
        )

        return content

    def get_child_pages(self, parent_page_title="QA - НТ - FORIS") -> list:
        parent_page_id = self._confluence.get_page_id(space=self.space, title=parent_page_title)
        child_pages = self._confluence.get_child_pages(parent_page_id)
        return child_pages

    def rename_pages(self, current_title, new_title):
        parent_id = self._confluence.get_page_id(space=self.space, title=current_title)
        old_page_content = self._confluence.get_page_by_title(space=self.space, title=current_title, expand="body")
        new_page_content = self._confluence.update_page(
            old_page_content["id"],
            title=new_title,
            body=old_page_content["body"],
            parent_id=parent_id,
            type="page",
            representation="storage",
        )
        return new_page_content

    def get_page_exist_conclusions(self, page_id) -> str | None:
        pattern = r"<h1>Выводы</h1>(.*)<h1>Рекомендации</h1>"
        return self.get_section_from_page(page_id=page_id, pattern=pattern)

    def get_section_from_page(self, page_id, pattern) -> str | None:
        try:
            content = (
                self._confluence.get_page_by_id(page_id, expand="body.storage").get("body").get("storage").get("value")
            )
            section = re.search(pattern, content)
            if section is not None:
                return section.group(1)
            else:
                return None
        except (ApiError, AttributeError) as e:
            logging.info(e)
            return None

    def get_page_exist_recommendations(self, page_id) -> str | None:
        pattern = r"<h1>Рекомендации</h1>(.*)"
        return self.get_section_from_page(page_id=page_id, pattern=pattern)

    def create_page_traceability_matrix(
        self,
        report_file,
        space=None,
        title=None,
        body=None,
        parent_page_id=None,
        override_page=False,
        parent_title=None,
    ):
        report_file_name = pathlib.Path(report_file).name

        if parent_title is None:
            parent_title = TITLE_PAGE_TRACEABILITY_MATRIX

        if title is None:
            title = TITLE_PAGE_TRACEABILITY_MATRIX + " " + str(date.today())

        if self._confluence.get_page_id(space, title) and override_page is False:
            return self

        if space is None:
            space = self.space

        if body is None:
            body = self.generate_content_page_traceability_matrix(report_file)

        if parent_page_id is None:
            parent_page_id = self._confluence.get_page_id(space, parent_title)

        assert parent_page_id is not None, f"Создайте главную страницу {parent_title} в проекте"
        if override_page or not self._confluence.get_page_id(space=space, title=title):
            page_traceability_matrix = self._confluence.update_or_create(
                parent_id=parent_page_id, title=title, body=body
            )
            self._confluence.attach_file(
                filename=report_file,
                name=report_file_name,
                page_id=page_traceability_matrix.get("id"),
                title=title,
                space=self.space,
            )
            assert page_traceability_matrix, "Что-то пошло не так, страница не создана"
        else:
            page_id = self._confluence.get_page_id(space=space, title=title)
            page_traceability_matrix = self._confluence.get_page_by_id(page_id=page_id)
        url = page_traceability_matrix.get("_links").get("base") + page_traceability_matrix.get("_links").get("webui")
        logging.info(f" Создана страница матрицы покрытия требований: {url}")
        return self

    def generate_content_page_traceability_matrix(self, report, today=None) -> str:
        report_file_name = pathlib.Path(report).name
        if today is None:
            today = str(date.today())
        df = pd.read_excel(report, sheet_name="coverage", header=0, dtype=int)

        row_numbers = df.loc[0, :].values.flatten().tolist()[1:]

        table_row = "<tr>"
        table_row += f"<td><p>{today}</p></td>"
        for number in row_numbers:
            table_row += f"<td><p>{number}</p></td>"
        table_row += f'<td><p><ac:link><ri:attachment ri:filename="{report_file_name}" /></ac:link></p></td>'
        table_row += "</tr>"

        template = str(self.generate_traceability_matrix_page(table_row=table_row))

        return template

    def is_page_exists(self, name_page):
        return self._confluence.page_exists(space=self.space, title=name_page)

    def page_creator(self, parent_id=None, parent_title=None, page_title=None, body=None):
        if parent_id is None and parent_title is not None:
            parent_id = self._confluence.get_page_id(space=self.space, title=parent_title)
        else:
            msg = f"Задайте {parent_id} или {parent_title}"
            logging.error(msg=msg)
        if page_title is None:
            page_title = "Page title"
        if body is None:
            body = "<h1>!Черновик</h1>"
        response = self._confluence.create_page(space=self.space, title=page_title, body=body, parent_id=parent_id)
        return response

    def create_qa_space(self):
        qa_space = self.generate_space_architecture()

        for main_section, sections in qa_space.items():
            if not self.is_page_exists(main_section):
                self.page_creator(
                    parent_id=None,
                    parent_title=None,
                    page_title=main_section,
                    body=None,
                )
            for section in sections:
                page_title = list(section.keys())[0]
                pages = list(section.values())[0]
                if len(pages) == 0:
                    continue
                if not self.is_page_exists(page_title):
                    self.page_creator(
                        parent_id=None,
                        parent_title=main_section,
                        page_title=page_title,
                        body=None,
                    )
                for page in pages:
                    for key, value in page.items():
                        if value is True:
                            if not self.is_page_exists(key):
                                self.page_creator(parent_title=page_title, page_title=key)
        return self

    def search_by_summary(self, summary: str):
        """Поиск в Confluence информации по тексту"""
        # Use the method with its supported parameters, then filter results
        results = self._confluence.get_all_pages_from_space_raw(space=self.space, start=0, limit=50)

        # After getting results, filter them manually (not ideal for performance)
        filtered_results = []
        for page in results.get("results", []):
            # Implement your own filtering logic here based on summary
            if summary.lower() in page.get("title", "").lower():
                filtered_results.append(page)

        return filtered_results

    def search_cql(self, cql_query: str, limit: int = 5) -> list[dict]:
        """Поиск страниц через CQL (Confluence Query Language).

        Args:
            cql_query: CQL запрос (например, 'text ~ "Data Source" AND space = "EINVY"').
            limit: Максимальное количество результатов.

        Returns:
            Список словарей с полями title, id, excerpt.
        """
        try:
            result = self._confluence.cql(cql_query, limit=limit)
            pages = []
            for item in result.get("results", []):
                content = item.get("content", item)
                pages.append(
                    {
                        "title": content.get("title", ""),
                        "id": content.get("id", ""),
                        "excerpt": (item.get("excerpt", "") or "")[:300],
                    }
                )
            return pages
        except Exception as e:
            logging.warning("Ошибка CQL поиска в Confluence: %s", e)
            return []

    def get_page_body(self, page_id: str | int, max_chars: int = 1000) -> str:
        """Получить текстовое содержимое страницы (HTML-теги удалены).

        Args:
            page_id: ID страницы Confluence.
            max_chars: Максимальная длина возвращаемого текста.

        Returns:
            Текст страницы без HTML тегов, обрезанный до max_chars.
        """
        try:
            page = self._confluence.get_page_by_id(page_id, expand="body.storage")
            raw_html = page.get("body", {}).get("storage", {}).get("value", "")
            text = re.sub(r"<[^>]+>", " ", raw_html)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
        except Exception as e:
            logging.warning("Ошибка получения body страницы %s: %s", page_id, e)
            return ""
