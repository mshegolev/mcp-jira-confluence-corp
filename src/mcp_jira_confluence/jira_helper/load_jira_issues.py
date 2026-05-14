# type: ignore
import json
import logging
import os
import pathlib
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

from jira import Issue
from jira.resources import Version, Worklog
from psycopg2.extras import Json

from qa_assistant.datamodels.metabase_issue import MetabaseIssue
from qa_assistant.datamodels.metabase_launch import MetabaseLaunch
from qa_assistant.datamodels.metabase_sonarqube import MetabaseSonarqube
from qa_assistant.datamodels.metabase_testcase import MetabaseTestcase
from qa_assistant.datamodels.metabase_tis import MetabaseTisIssue
from qa_assistant.datamodels.metabase_version import MetabaseVersion
from qa_assistant.manager_helpers.jira_loader import JiraHelper, JiraLoader, SupportedDbms
from qa_assistant.project_helper.projects import Project, Projects


class MetricHelper:
    def __init__(
        self,
        project: Project = Projects.einvy,
        db_name: Optional[str] = None,
        db_path: Optional[str | pathlib.Path] = None,
    ) -> None:
        self.project = project
        self.db_name = db_name
        self.db_path = db_path
        self._jira_helper: Optional[JiraHelper] = None

    @property
    def JiraHelper(self) -> JiraHelper:
        if self._jira_helper is None:
            self._jira_helper = JiraHelper(project=self.project)
        return self._jira_helper

    @staticmethod
    def load_data_for_all_projects(
        db_path: Optional[pathlib.Path | str] = None, project: Optional[Project] = None
    ) -> bool:
        if project is None:
            projects = Projects.any
        else:
            projects = [project]
        if db_path is None:
            db_path = MetricHelper.create_sqlite_db(db_path)
        for project in projects:
            db_name = project.key + "_jira"
            loader = JiraLoader(project=project, db_name=db_name, db_path=db_path)
            data = loader.load_only_raw(db_name=db_name)
            logging.info(f"Всего загружено: {data}")
        return True

    @staticmethod
    def create_sqlite_db(
        db_path: Optional[str | pathlib.Path] = None,
        dir_path: str = "/opt/develop/metabase/",
    ) -> pathlib.Path:
        if db_path is None:
            _dir_path = pathlib.Path(dir_path)
            _dir_path.mkdir(parents=True, exist_ok=True)
            _db_path = _dir_path / f"{date.today()}_raw_jira.db"
        return _db_path

    @staticmethod
    def create_worklog_tbl(
        project: Project,
        db_name: Optional[str] = None,
        db_path: Optional[pathlib.Path | str] = None,
    ) -> int:
        result = 0
        if db_name is None:
            db_name = project.key + "_worklog"
        if db_path is None:
            MetricHelper.create_sqlite_db(db_path)
        loader = JiraLoader(project=project, db_path=db_path, db_name=db_name)
        loader.create_worklog_tbl(db_path=db_path, db_name=db_name)
        issues = loader.get_worklog_section()
        # todo: get wls
        # get from wl createat date, author, and timespant
        # save this from new tbl prj-name-worklogs
        # next action create select from prj-name-worklogs with group by createat.
        #
        columns = ["pk", "uuid", "key", "worklog"]
        for issue in issues:
            wls = json.loads(issue[2])
            for wl in wls:
                pk = None
                uniq_uuid = str(uuid.uuid4())
                key = issue[1]
                worklog = json.dumps(wl)
                cols = ",".join(["'" + _ + "'" for _ in columns])
                vals = str("?," * len(columns)).removesuffix(",")
                query = f"INSERT INTO '{db_name}' ({cols}) VALUES ({vals})"
                values = [pk, uniq_uuid, key, worklog]
                loader.db.execute(query=query, values=values)
                logging.info(wl)
                result += 1
        logging.info(f"Загружено {result} задач в бд {db_path}/{db_name}")
        return result

    @staticmethod
    def create_qa_velocity_tbl(
        project: Project,
        table_name: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> bool:
        if table_name is None:
            table_name = project.key.lower() + "_qa_velocity"

        # Ensure we have a valid db_path
        if db_path is None:
            db_path = str(MetricHelper.create_sqlite_db())

        loader = JiraLoader(project=project, db_path=db_path, db_name=table_name)
        issues = loader.get_qa_velocity_raws()
        loader.create_qa_velocity_tbl(issues, db_path=db_path, table_name=table_name)
        return True

    @staticmethod
    def create_metabase_data(
        project: "Project",
        table_name: Optional[str] = None,
        db_path: Optional[str] = None,
        db_name: Optional[str] = None,
        raw_data_table_name: Optional[str] = None,
        save_worklog: bool = False,
        save_issue: bool = False,
        save_labels: bool = False,
        save_issue_change: bool = False,
    ) -> None:
        if table_name is None:
            table_name = f"{project.key.lower()}_issue_worklog"
        if db_name is None:
            db_name = "main"
        if raw_data_table_name is None:
            raw_data_table_name = f"{project.key.lower()}_jira"

        if db_path is None:
            base_dir = "/opt/develop/metabase"
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, f"{date.today()}_raw_jira.db")
            if not os.path.isfile(db_path):
                raise NameError("База не создана, создайте базу данных или укажите правильный путь!")

        loader = JiraLoader(project=project, db_path=db_path, db_name=db_name)
        loader.create_issue_worklog_tbl(db_path=db_path)
        loader.create_issue_tbl(db_path=db_path)
        loader.create_issue_label_tbl(db_path=db_path)
        loader.create_issue_change_tbl(db_path=db_path)

        raw_issues = loader.get_from_raw(table_name=raw_data_table_name)

        for (raw_json_str,) in raw_issues:
            issue_data: Dict[str, Any] = json.loads(raw_json_str)

            if save_worklog:
                total = issue_data.get("fields", {}).get("worklog", {}).get("total", 0)
                if total > 0:
                    logging.info(f"Сохраняем worklog для задачи: {issue_data['key']}")
                    worklogs = loader._jira.worklogs(issue_data["key"])
                    MetricHelper.save_to_worklog_table(
                        key=issue_data["key"],
                        worklogs=worklogs,
                        loader=loader,
                        table_name=table_name,
                    )

            if save_issue:
                MetricHelper.save_to_issue_table(
                    issue=issue_data,
                    loader=loader,
                    table_name=table_name,
                )

            if save_labels:
                MetricHelper.save_to_issue_label_table(
                    issue=issue_data,
                    loader=loader,
                    table_name="issue_label",
                )

            if save_issue_change:
                MetricHelper().save_to_issue_change_table(
                    issue=issue_data,
                    loader=loader,
                    table_name="issue_change",
                )

        logging.info("Загрузка данных в таблицы завершена.")

    @staticmethod
    def save_to_worklog_table(key: str, worklogs: List[Worklog], loader: JiraLoader, table_name: str) -> None:
        for worklog in worklogs:
            try:
                minutes_spent = int(int(worklog.raw["timeSpentSeconds"]) / 60)
            except Exception as e:
                logging.error(e)
                logging.error(f"НЕТ нормальных секунд: {worklog.raw['timeSpentSeconds']}")
                minutes_spent = 0
            values = {
                "key": key,
                "created": worklog.raw["created"],
                "updated": worklog.raw["updated"],
                "start_date": worklog.raw["started"],
                "author": worklog.raw["author"]["name"],
                "update_author": worklog.raw["updateAuthor"]["name"],
                "minutes_spent": minutes_spent,
            }
            loader.insert_worklog_to_sqlite(wl=values, tbl_name=table_name)

    @staticmethod
    def save_to_issue_table(issue: Dict[Any, Any], loader: JiraLoader, table_name: str = "_") -> Dict[str, Any]:
        values = {
            "id": "",
            "key": "",
            "project": "",
            "epic_key": "",
            "type": "",
            "status": "",
            "priority": "",
            "summary": "",
            "reporter": "",
            "assignee": "",
            "resolution": "",
            "created": "",
            "updated": "",
            "original_estimate": "",
            "remaining_estimate": "",
            "time_spent": "",
            "severity": "",
        }
        i = 0
        while i < 15:
            try:
                values["id"] = issue.get("id", "") if values["id"] == "" else values["id"]
                values["key"] = issue.get("key", "") if values["key"] == "" else values["key"]
                values["project"] = (
                    str(issue.get("fields", {}).get("project").get("key")) if values["key"] == "" else values["project"]
                )
                values["epic_key"] = str(issue.get("fields", {}).get("epic"))
                values["type"] = str(issue.get("fields", {}).get("issuetype").get("name"))
                values["status"] = str(issue.get("fields", {}).get("status").get("name"))
                values["priority"] = str(issue.get("fields", {}).get("priority").get("name"))
                values["summary"] = str(issue.get("fields", {}).get("summary"))
                values["reporter"] = str(issue.get("fields", {}).get("reporter").get("name"))
                values["assignee"] = (
                    str(issue.get("fields", {}).get("assignee").get("name"))
                    if values["assignee"] == ""
                    else values["assignee"]
                )
                values["resolution"] = (
                    str(issue.get("fields", {}).get("resolution").get("name"))
                    if values["resolution"] == ""
                    else values["resolution"]
                )
                values["created"] = (
                    str(issue.get("fields", {}).get("created")) if values["created"] == "" else values["created"]
                )
                values["updated"] = (
                    str(issue.get("fields", {}).get("updated")) if values["updated"] == "" else values["updated"]
                )
                values["original_estimate"] = (
                    str(issue.get("fields", {}).get("original_estimate"))
                    if values["original_estimate"] == ""
                    else values["original_estimate"]
                )
                values["remaining_estimate"] = (
                    str(issue.get("fields", {}).get("remaining_estimate"))
                    if values["remaining_estimate"] == ""
                    else values["remaining_estimate"]
                )
                values["time_spent"] = (
                    str(issue.get("fields", {}).get("time_spent"))
                    if values["time_spent"] == ""
                    else values["time_spent"]
                )
                values["severity"] = (
                    str(issue.get("fields", {}).get("severity")) if values["severity"] == "" else values["severity"]
                )
                break
            except Exception as e:
                i += 1
                if e:
                    logging.warning(e)
                    for k, v in values.items():
                        if v == "":
                            values[k] = "None"
                            break

        loader.insert_issue_to_dbms(values=values, table_name=table_name)
        return values

    @classmethod
    def save_to_issue_label_table(
        cls,
        issue: Optional[Dict[str, Any] | Tuple[Any]],
        loader: JiraLoader,
        table_name: Optional[object] = None,
    ) -> bool:
        if table_name is None:
            table_name = "issue_label"
        labels = issue.get("fields").get("labels")  # type: ignore
        key = issue.get("key")  # type: ignore
        if len(labels) == 0:
            return False
        for label in labels:
            values = {"key": key, "labels": label}
            loader.db.insert_issue_label_to_sqlite(values=values, table_name=table_name)
        return True

    def get_loader(self, db_name: Optional[str] = None) -> JiraLoader:
        if db_name is None:
            db_name = "qmh"
        return JiraLoader(project=self.project, db_name=db_name, dbms=SupportedDbms.POSTGRESQL)

    @staticmethod
    def get_metabase_launch(launch: Optional[Dict[str, Any] | MetabaseLaunch]) -> MetabaseLaunch:
        return launch if isinstance(launch, MetabaseLaunch) else MetabaseLaunch(launch)

    @staticmethod
    def get_metabase_case(testcase: Optional[Dict[str, Any]]) -> MetabaseTestcase:
        return MetabaseTestcase(testcase)

    def get_metabase_issue(self, issue: Optional[Issue | Dict[str, Any]]) -> MetabaseIssue:
        if isinstance(issue, Issue):
            return MetabaseIssue(issue)
        elif isinstance(issue, dict):
            _ = self.JiraHelper.create_jira_issue_row(issue)
            return MetabaseIssue(_)
        else:
            return MetabaseIssue()

    def save_to_meta_table_issue_link(self, issues_list: List[MetabaseIssue]) -> bool:
        """
        Сохраняет связи между задачами в таблицу jira.issue_link.

        :param issues_list: Список объектов MetabaseIssue.
        :return: True, если успешно сохранено, иначе False.
        """
        loader = self.get_loader()
        table_name = "jira.issue_link"

        if not isinstance(issues_list, list):
            issues_list = [self.get_metabase_issue(issues_list)]

        if not issues_list:
            logging.warning("Передан пустой список задач для сохранения связей.")
            return False

        columns = MetabaseIssue.metabase_issue_link_fields
        keys: List[str] = [cast(str, item.key) for item in issues_list]
        primary_key = "key"

        delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)
        delete_success = loader.db.execute(delete_query, delete_params)

        if not delete_success:
            logging.warning(f"Ошибка при удалении записей из таблицы {table_name}.")
            return False
        logging.debug(f"Удалены старые записи для {len(issues_list)} задач.")

        values = [
            tuple(link) for item in issues_list for link in getattr(item, "issue_link_values", []) if link
        ] or list()

        if not values:
            logging.warning(f"Не найдено связанных задач для {len(issues_list)} записей.")
            return False

        insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)
        insert_success = loader.db.execute_many(insert_query, insert_params)

        if not insert_success:
            logging.error(f"Ошибка при добавлении записей в таблицу {table_name}.")
            return False

        logging.debug(f"Добавлено {len(values)} записей в таблицу {table_name}.")
        logging.debug(f"Обработано {self.project} - Jira задач: {len(issues_list)}.")
        return True

    def save_to_meta_table_version(self, version: Version) -> bool:
        loader = self.get_loader()
        table_name = "jira.version"
        metabase_version = MetabaseVersion(version=version, project=self.project)
        loader.insert_version_to_dbms(values=metabase_version.version_values, table_name=table_name)
        logging.debug(msg=f"Записали в БД версию {self.project}: {metabase_version.name}")
        return True

    def save_to_meta_table_issue_infrastructure(self, issue: List[Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.issue_infrastructure"
        if isinstance(issue, list):
            columns = MetabaseIssue.metabase_issue_infrastructure_fields
            keys = [_.key for _ in issue]
            primary_key = "key"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []

            for i in issue:
                for x in i.issue_infrastructure_values:
                    values.append(tuple(x))
            if not values:
                return 0
            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)
        return len(issue)

    def save_to_meta_table_issue_component(self, issue: List[Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.issue_component"
        if isinstance(issue, list):
            columns = MetabaseIssue.metabase_issue_component_fields
            keys = [_.key for _ in issue]
            primary_key = "key"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []
            for i in issue:
                for x in i.issue_component_values:
                    values.append(tuple(x))
            if not values:
                return 0
            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

        return len(issue)

    def save_to_meta_table_issue_fix_version(self, issue: List[Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.issue_fix_version"
        if isinstance(issue, list):
            columns = MetabaseIssue.metabase_issue_fix_version_fields
            keys = [_.key for _ in issue]
            primary_key = "key"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []
            for i in issue:
                for x in i.issue_fix_version_values:
                    values.append(tuple(x))
            if not values:
                return 0
            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(issue)
        else:
            issue = self.get_metabase_issue(issue)
            loader.insert_issue_fix_version_to_dbms(values=issue.issue_fix_version_values, table_name=table_name)
            return True

    def save_to_meta_table_issue_label(self, issue: List[Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.issue_label"
        if isinstance(issue, list):
            columns = MetabaseIssue.metabase_issue_label_fields
            keys = [_.key for _ in issue]
            primary_key = "key"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            # values = [_.issue_label_values for _ in issue]
            values = []
            for i in issue:
                for x in i.issue_label_values:
                    values.append(tuple(x))
            if not values:
                return 0
            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(issue)

        else:
            issue = self.get_metabase_issue(issue)
            return loader.insert_issue_label_to_dbms(values=issue.issue_label_values, table_name=table_name)

    def save_to_meta_table_issue_v2(self, issues: List[Any]) -> int:
        table_name = "jira.issue"
        loader = self.get_loader()
        keys = [_.key for _ in issues]
        delete_query, delete_params = loader.get_delete_query_v2(table_name=table_name, key_field="key", keys=keys)
        loader.db.execute(delete_query, delete_params)

        values = [_.issue_values for _ in issues]
        if not values:
            return 0
        insert_query, insert_params = loader.get_insert_query_v2(
            table_name=table_name,
            columns=MetabaseIssue.metabase_issue_fields,
            values=values,
        )
        loader.db.execute_many(insert_query, insert_params)

        return len(issues)

    def save_to_issue_change_table(
        self,
        issue: Dict[Any, Any] | Tuple[Any],
        loader: Optional[JiraLoader] = None,
        table_name: Optional[str] = None,
    ) -> int:
        result = []
        if loader is None:
            loader = self.get_loader()
        if table_name is None:
            table_name = "jira.issue_change"

        if isinstance(issue, list):
            columns = MetabaseIssue.metabase_issue_change_fields
            keys = [_.get("key") for _ in issue]
            primary_key = "key"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)
            values = []
            for i in issue:
                values += self.get_changelog_values_from_issue(i)
            if not values:
                return 0
            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(issue)
        else:
            if not isinstance(issue, dict):
                raise NameError("Метод принимает только dict или list[dict]")
            result += self.get_changelog_values_from_issue(issue)
            for values in result:
                loader.insert_issue_changelog_to_dbms(values=values, table_name=table_name)
            logging.debug(msg=f"Записали в БД changelog для: {issue.get('key')}")
            return 1

    @staticmethod
    def get_changelog_values_from_issue(issue: Dict[str, Any]) -> List[Tuple[Any | None, ...]]:
        result: list[tuple[Any | None, ...]] = []
        key = issue.get("key")
        changelog = issue.get("changelog")
        if not changelog:
            return result
        for histories in changelog.get("histories", [{}]):
            created = histories.get("created", None)
            author = histories.get("author", {}).get("name", None)

            for item in histories.get("items", [{}]):
                if item.get("field", "") not in ["status"]:
                    continue
                field = item.get("field")
                # fieldtype = item.get("fieldtype", None)
                from_value = item.get("fromString", None)
                to_value = item.get("toString", None)

                result.append(tuple([key, author, created, from_value, to_value, field]))
        return result

    def save_to_meta_table_launch(self, launch: List[MetabaseLaunch]) -> int:
        table_name = "jira.launch"
        chunks = launch
        columns = MetabaseLaunch.metabase_launch_fields
        primary_key = "launch_id"
        delete_id_key = "launch_id"
        attr_values = "launch_values"
        return self.__save_unify_table(
            table_name=table_name,
            chunks=chunks,
            columns=columns,
            delete_id_key=delete_id_key,
            primary_key=primary_key,
            attr_values=attr_values,
        )

    def save_to_meta_table_launch_old(self, launch: List[MetabaseLaunch]) -> int:
        loader = self.get_loader()
        table_name = "jira.launch"
        if isinstance(launch, list):
            columns = MetabaseLaunch.metabase_launch_fields
            keys = [_.get("id") for _ in launch]
            primary_key = "launch_id"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = [tuple(self.get_metabase_launch(_).launch_values) for _ in launch]
            if not values:
                return 0

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(launch)
        else:
            raise BaseException("нужно реализовать")

    def save_to_meta_table_launch_variables(self, launches: List[MetabaseLaunch]) -> None:
        table_name = "jira.launch_variable"
        chunks = launches
        columns = MetabaseLaunch.metabase_launch_variable_fields
        primary_key = "launch_id"
        delete_id_key = "launch_id"
        attr_values = "launch_variable_values"
        self.__save_unify_table(
            table_name=table_name,
            chunks=chunks,
            columns=columns,
            delete_id_key=delete_id_key,
            primary_key=primary_key,
            attr_values=attr_values,
        )

    def save_to_meta_table_launch_statistic(self, launch: List[MetabaseLaunch]) -> None:
        table_name = "jira.launch_statistic"
        chunks = launch
        columns = MetabaseLaunch.metabase_launch_statistic_fields
        primary_key = "launch_id"
        delete_id_key = "launch_id"
        attr_values = "launch_statistic_values"
        self.__save_unify_table(
            table_name=table_name,
            chunks=chunks,
            columns=columns,
            delete_id_key=delete_id_key,
            primary_key=primary_key,
            attr_values=attr_values,
        )

    def __save_unify_table(
        self,
        table_name: str,
        chunks: List[Any],
        columns: List[str],
        delete_id_key: str,
        primary_key: str,
        attr_values: str,
    ) -> int:
        keys: list[str] = []
        loader = self.get_loader()
        if isinstance(chunks, list):
            try:
                if len(chunks) == 0:
                    keys = []
                elif isinstance(chunks[0], dict):
                    keys = [_.get(delete_id_key, None) for _ in chunks if isinstance(_, dict)]
                else:
                    keys = [_.get(delete_id_key) for _ in chunks]

            except AttributeError as e:
                msg = f'Ошибка {e.args[0]}.На данных {str(chunks)}, вызов метода _.get("{delete_id_key}") для case'
                logging.error(msg)

            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []
            for chunk in chunks:
                chunk_values = getattr(chunk, attr_values)
                if isinstance(chunk_values, list) and len(chunk_values) > 0:
                    if isinstance(chunk_values[0], list):
                        for chunk_value in chunk_values:
                            if isinstance(chunk_value, list):
                                values.append(tuple(chunk_value))
                            elif isinstance(chunk_value, tuple):
                                values.append(chunk_value)
                            else:
                                values.append(tuple(chunk_value))
                    elif isinstance(chunk_values[0], tuple):
                        for chunk_value in chunk_values:
                            values.append(chunk_value)
                    else:
                        values.append(tuple(chunk_values))
                elif isinstance(chunk_values, tuple):
                    values.append(chunk_values)
                else:
                    values.append(tuple(chunk_values))

            values = [_ for _ in values if _]
            if len(values) == 0 or not values[0]:
                return 0

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(chunks)
        else:
            raise NotImplementedError("Нужно реализовать")  # noqa: B016

    def save_to_meta_table_launch_tag(self, launches: List[MetabaseLaunch]) -> None:
        table_name = "jira.launch_tag"
        chunks = launches
        columns = MetabaseLaunch.metabase_launch_tag_fields
        primary_key = "launch_id"
        delete_id_key = "launch_id"
        attr_values = "launch_tag_values"
        self.__save_unify_table(
            table_name=table_name,
            chunks=chunks,
            columns=columns,
            delete_id_key=delete_id_key,
            primary_key=primary_key,
            attr_values=attr_values,
        )

    def save_to_meta_table_launch_tag_deprecated(self, launch: List[MetabaseLaunch]) -> int:
        loader = self.get_loader()
        table_name = "jira.launch_tag"
        if isinstance(launch, list):
            columns = MetabaseLaunch.metabase_launch_tag_fields
            try:
                keys = [_.get("id", None) for _ in launch if isinstance(_, dict)]
            except AttributeError as e:
                msg = f'Ошибка {e.args[0]}.На данных {str(launch)}, вызов метода _.get("id") для case'
                logging.error(msg)

            primary_key = "launch_id"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []
            for launch_element in launch:
                for tag in self.get_metabase_launch(launch_element).launch_tag_values:
                    values.append(tuple(tag))
            if not values:
                return 0

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(launch)
        else:
            raise BaseException("Нужно реализовать")

    def save_to_meta_table_case_tag(self, case: Optional[List[Any] | MetabaseTestcase | Dict[str, Any]]) -> int:
        loader = self.get_loader()
        table_name = "jira.testcase_tag"
        if isinstance(case, list):
            columns = MetabaseTestcase.metabase_testcase_tag_fields
            try:
                keys = [_.get("id", None) for _ in case if isinstance(_, dict)]
            except AttributeError as e:
                msg = f'Ошибка {e.args[0]}.На данных {str(case)}, вызов метода _.get("id") для case'
                logging.error(msg)

            primary_key = "testcase_id"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []
            for c in case:
                for tag in self.get_metabase_case(c).testcase_tags_values:
                    values.append(tuple(tag))
            if not values:
                return 0

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(case)
        elif isinstance(case, MetabaseTestcase):
            loader.insert_testcase_link_to_dbms(values=case.testcase_links_values, table_name=table_name)
            return 1
        elif isinstance(case, dict):
            case = self.get_metabase_case(case)
            loader.insert_testcase_link_to_dbms(values=case.testcase_links_values, table_name=table_name)
            return 1
        else:
            raise RuntimeError(f"Неизвестный тип case: f{type(case)}")

    def save_to_meta_table_case_link(self, case: List[Any] | MetabaseTestcase | Dict[Any, Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.testcase_link"
        if isinstance(case, list):
            columns = MetabaseTestcase.metabase_testcase_link_fields
            keys = [_.get("id") for _ in case]
            primary_key = "testcase_id"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = []
            for c in case:
                for link in self.get_metabase_case(c).testcase_links_values:
                    values.append(tuple(link))
            if not values:
                return 0

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(case)
        elif isinstance(case, MetabaseTestcase):
            loader.insert_testcase_link_to_dbms(values=case.testcase_links_values, table_name=table_name)
            return 1
        elif isinstance(case, dict):
            case = self.get_metabase_case(case)
            loader.insert_testcase_link_to_dbms(values=case.testcase_links_values, table_name=table_name)
            return 1
        else:
            raise RuntimeError(f"Неизвестный тип case: {type(case)}")

    def save_to_meta_table_case(self, case: List[Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.testcase"
        if isinstance(case, list):
            columns = MetabaseTestcase.metabase_testcase_fields
            keys = [_.get("id") for _ in case]
            primary_key = "testcase_id"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            values = [tuple(self.get_metabase_case(_).testcase_values) for _ in case]
            if not values:
                return 0

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)

            loader.db.execute_many(insert_query, insert_params)

            return len(case)
        else:
            case = self.get_metabase_case(case)
            return loader.insert_testcase_to_dbms(values=case.testcase_values, table_name=table_name)

    def execute_function_insert_qa_queue_issue(self) -> None:
        loader = self.get_loader()
        query = "select jira.insert_qa_queue_issue_v3('%s')" % self.project.key.upper()
        loader.db.execute(query=query)

    def execute_function_add_qa_progress_agg(self) -> None:
        loader = self.get_loader()
        query = "select jira.add_qa_progress_agg('%s')" % self.project.key.upper()
        loader.db.execute(query=query)

    def get_launch_id(self, last_days: int = 5) -> int:
        loader = self.get_loader()
        project_id = self.project.testops_id
        created_date = (datetime.now() - timedelta(days=last_days)).strftime("%Y-%m-%d")
        query = f"select launch_id from jira.launch where createddate >='{created_date}' and projectid={project_id} order by launch_id asc limit 1"
        response = loader.db.select_query(query=query)
        return 0 if len(response) == 0 else int(response[0][0])

    def save_to_meta_table_processing_results(self, processing_results: Dict[str, Any]) -> int:
        loader = self.get_loader()
        table_name = "jira.processing_results"

        if not processing_results:
            return 0

        timestamp = datetime.utcnow()

        json_data = json.dumps(processing_results)

        columns = ["timestamp", "data"]
        values = [(timestamp, json_data)]

        insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)
        loader.db.execute_many(insert_query, insert_params)

        return len(processing_results)

    def save_to_meta_table_issue_tis(self, tis: Optional[List[MetabaseTisIssue]]) -> int:
        loader = self.get_loader()
        table_name = "jira.issue_tis"
        if not tis:
            return 0

        if isinstance(tis, list):
            keys = [_.key for _ in tis]
            primary_key = "key"
            delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

            loader.db.execute(delete_query, delete_params)

            columns = MetabaseTisIssue.metabase_tis_fields
            values = [_.metabase_values for _ in tis]

            insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)
            loader.db.execute_many(insert_query, insert_params)
        else:
            raise RuntimeError(f"Неизвестный тип tis: {type(tis)}, принимаем только список list[MetabaseTisIssue]")
        return len(tis)

    def save_to_meta_table_sonarqube_metrics(self, data: Optional[List[MetabaseSonarqube]]) -> int:
        table_name = "jira.sonarqube_metrics"
        primary_key = "key"
        loader = self.get_loader()
        if not data:
            return 0

        keys = [getattr(_, primary_key) for _ in data]
        delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)
        loader.db.execute(delete_query, delete_params)

        columns = MetabaseSonarqube.metabase_sqb_fields
        values = [_.metabase_values for _ in data]

        insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)
        loader.db.execute_many(insert_query, insert_params)
        return len(data)

    def save_sonarqube_data(self, data: dict[str, Any]) -> Any:
        """
        Сохраняет данные анализа SonarQube в базу данных PostgreSQL

        :param data: Словарь с данными анализа SonarQube
        :return: ID созданной записи анализа
        """
        # Подключение к базе данных
        loader = self.get_loader()
        conn = loader.db.connection

        try:
            component = data["component"]["key"]
            service = data["component"]["name"]
            qualifier = data["component"]["qualifier"]
            project_key = data["component"]["project_key"]
            with conn.cursor() as cursor:
                # 1. Сохраняем проект
                cursor.execute(
                    """
                       WITH upsert AS (
                       UPDATE jira.ref_projects
                       SET service    = %s,
                           qualifier  = %s,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE project_key = %s RETURNING 1
                        )
                       INSERT
                       INTO jira.ref_projects (component, service, qualifier, project_key)
                       SELECT %s,
                              %s,
                              %s,
                              %s WHERE NOT EXISTS (SELECT 1 FROM upsert);
                               """,
                    (
                        service,
                        qualifier,
                        project_key,
                        component,
                        service,
                        qualifier,
                        project_key,
                    ),
                )

                # 2. Сохраняем период анализа (поле period может отсутствовать)
                period_data = data.get("period")
                period_id = None
                if period_data:
                    cursor.execute(
                        """
                                   INSERT INTO jira.ref_analysis_periods (period_index, period_mode, period_date)
                                   VALUES (%s, %s, %s) ON CONFLICT (period_index, period_mode, period_date) DO NOTHING
                        RETURNING period_id;
                                   """,
                        (
                            period_data["index"],
                            period_data["mode"],
                            period_data["date"],
                        ),
                    )
                    period_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None

                # 3. Получаем статус quality gate
                quality_gate_status = next(
                    (m["value"] for m in data["component"]["measures"] if m["metric"] == "alert_status"),
                    "UNKNOWN",
                )

                # 4. Сохраняем основной анализ
                cursor.execute(
                    """
                               INSERT INTO jira.fact_sonarqube_analyses (component, period_id, analysis_timestamp,
                                                                         quality_gate_status)
                               VALUES (%s, %s, CURRENT_TIMESTAMP, %s) RETURNING analysis_id;
                               """,
                    (component, period_id, quality_gate_status),
                )

                analysis_id = cursor.fetchone()[0]

                # 5. Сохраняем все метрики
                for measure in data["component"]["measures"]:
                    metric_key = measure["metric"]
                    metric_value = measure.get("value")
                    is_best_value = measure.get("bestValue")

                    # Определяем, является ли значение JSON-объектом
                    raw_data = None
                    if metric_value and metric_value.startswith("{") and metric_value.endswith("}"):
                        try:
                            raw_data = Json(json.loads(metric_value))
                            metric_value = None  # Оригинальное значение сохраняем только в raw_data
                        except json.JSONDecodeError:
                            pass

                    cursor.execute(
                        """
                                   INSERT INTO jira.fact_sonarqube_metrics (analysis_id, metric_key, metric_value,
                                                                            is_best_value, raw_data)
                                   VALUES (%s, %s, %s, %s, %s);
                                   """,
                        (
                            analysis_id,
                            metric_key,
                            metric_value,
                            is_best_value,
                            raw_data,
                        ),
                    )

                conn.commit()
                logging.info(f"Данные успешно сохранены. ID анализа: {analysis_id}")
                return analysis_id

        except Exception as e:
            conn.rollback()
            logging.error(f"Ошибка при сохранении данных: {e}")
            raise
        # NOTE: do NOT close conn here — it is a shared QaPostgreSqlHelper connection.
        # Closing it here makes all subsequent save_sonarqube_data calls fail silently
        # because QaPostgreSqlHelper._connection stays set to the closed object.

    def save_to_meta_table_project(self) -> None:
        table_name = "jira.project"
        loader = self.get_loader()
        conn = loader.db.connection
        try:
            cursor = conn.cursor()
            query = f"""
                    INSERT INTO {table_name} (
                    "key",
                    "name",
                    jira_id,
                    allure_id,
                    confluence_space
                )
                SELECT
                    '{self.project.key}'         AS "key",
                   '{self.project.name}'   AS "name",
                    {self.project.jira_id}       AS jira_id,
                    {self.project.testops_id}          AS allure_id,
                    '{self.project.space}'     AS confluence_space
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM jira.project p
                    WHERE p."key" = '{self.project.key}'
                );
            """
            cursor.execute(query)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Ошибка при сохранении данных: {e}")
            raise
        finally:
            conn.close()

    def update_label_bug_prod(self) -> None:
        # TODO: абстракции потекли qick win, переделать, в рамках задачи по багам с прода
        issue_label_table = "issue_label"
        raw_bugs_table = "issue_raw_bugs"
        loader = self.get_loader()
        logging.info("Add label to issue_label")
        query = f"""INSERT INTO {issue_label_table} ("key", label)
                   SELECT jr."key", 'bug_prod'
                   FROM {raw_bugs_table} AS jr
                   WHERE jr.key <> '1'
                     AND NOT EXISTS (
                       SELECT 1
                       FROM {issue_label_table} AS il
                       WHERE il.key = jr.key
                     AND il.label = 'bug_prod'
                       )"""
        loader.db.insert_query(query)

    def save_to_issue_raw_data(self, data: List[Dict[str, Any]]) -> int:
        # TODO: абстракции потекли qick win, переделать, в рамках задачи по багам с прода
        loader = self.get_loader()
        table_name = "jira.issue_raw_bugs"

        if not data:
            return 0

        keys = [_.get("key", "") for _ in data]
        primary_key = "key"
        delete_query, delete_params = loader.get_delete_query_v2(table_name, primary_key, keys)

        columns = ["key", "data"]
        values = [(_.get("key", ""), Json(_)) for _ in data]

        loader.db.execute(delete_query, delete_params)

        insert_query, insert_params = loader.get_insert_query_v2(table_name, columns, values)
        loader.db.execute_many(insert_query, insert_params)

        return len(data)
