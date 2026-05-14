import logging
from typing import Any, Dict, List, Optional, Union, cast

from jira import JIRA, Issue, JIRAError

from qa_assistant.datamodels.jira_issue_status import (
    JiraIssueStatus,
    JiraIssueTransitionStatus,
    JiraIssueTransitionStatuses,
)
from qa_assistant.manager_helpers.constants import JIRA_FIELD_COMMAND_DECISION, JIRA_FIELD_VERSION_PICKER
from qa_assistant.manager_helpers.issue_types import IssueTypes


class WorkFlowMap:
    workflows: Dict[str, List[Dict[str, Any]]] = {
        "[MTS] Default Bug Workflow v 2.0": [
            {
                "current_status": JiraIssueStatus.READY_TO_INSTALL,
                "next_status": JiraIssueStatus.CLOSED,
                "transition_status": JiraIssueTransitionStatuses.CLOSE.name,
                "fields": {},
            },
        ],
        "[MTS] Story Workflow v 3.0": [
            {
                "current_status": JiraIssueStatus.BACKLOG,
                "next_status": JiraIssueStatus.PBR,
                "transition_status": JiraIssueTransitionStatuses.START_PBR.name,
            },
            {
                "current_status": JiraIssueStatus.PBR,
                "next_status": JiraIssueStatus.OPEN,
                "transition_status": JiraIssueTransitionStatuses.READY_TO_WORK.name,
            },
            {
                "current_status": JiraIssueStatus.OPEN,
                "next_status": JiraIssueStatus.IN_PROGRESS,
                "transition_status": JiraIssueTransitionStatuses.START_WORK.name,
            },
            {
                "current_status": JiraIssueStatus.IN_PROGRESS,
                "next_status": JiraIssueStatus.READY_FOR_REVIEW,
                "transition_status": JiraIssueTransitionStatuses.READY_FOR_REVIEW.name,
            },
            {
                "current_status": JiraIssueStatus.READY_FOR_REVIEW,
                "next_status": JiraIssueStatus.REVIEW,
                "transition_status": JiraIssueTransitionStatuses.START_REVIEW.name,
            },
            {
                "current_status": JiraIssueStatus.REVIEW,
                "next_status": JiraIssueStatus.READY_FOR_TEST,
                "transition_status": JiraIssueTransitionStatuses.READY_FOR_TEST.name,
            },
            {
                "current_status": JiraIssueStatus.READY_FOR_TEST,
                "next_status": JiraIssueStatus.TESTING,
                "transition_status": JiraIssueTransitionStatuses.START_TESTING.name,
            },
            {
                "current_status": JiraIssueStatus.TESTING,
                "next_status": JiraIssueStatus.READY_TO_CHECK,
                "transition_status": JiraIssueTransitionStatuses.FINISH_TESTING.name,
            },
            {
                "current_status": JiraIssueStatus.READY_TO_CHECK,
                "next_status": JiraIssueStatus.READY_TO_INSTALL,
                "transition_status": JiraIssueTransitionStatuses.APPROVE.name,
            },
            {
                "current_status": JiraIssueStatus.READY_TO_INSTALL,
                "next_status": JiraIssueStatus.CLOSED,
                "transition_status": JiraIssueTransitionStatuses.DONE.name,
            },
        ],
        "[MTS] Workflow Scheme v 3.0": [
            {
                "current_status": JiraIssueStatus.BACKLOG,
                "next_status": JiraIssueStatus.PBR,
                "transition_status": JiraIssueTransitionStatuses.TO_PBR.name,
            },
        ],
        "Default Subtask Workflow v 1.1": [
            {
                "current_status": JiraIssueStatus.OPEN,
                "next_status": JiraIssueStatus.IN_PROGRESS,
                "transition_status": JiraIssueTransitionStatuses.START_WORK.name,
            },
            {
                "current_status": JiraIssueStatus.IN_PROGRESS,
                "next_status": JiraIssueStatus.CLOSED,
                "transition_status": JiraIssueTransitionStatuses.DONE.name,
            },
        ],
        "Default Kanban Story Workflow v 1.1": [
            {
                "current_status": JiraIssueStatus.BACKLOG,
                "next_status": JiraIssueStatus.PBR,
                "transition_status": JiraIssueTransitionStatuses.TO_PBR.name,
            },
            {
                "current_status": JiraIssueStatus.PBR,
                "next_status": JiraIssueStatus.OPEN,
                "transition_status": JiraIssueTransitionStatuses.READY_TO_WORK.name,
            },
            {
                "current_status": JiraIssueStatus.OPEN,
                "next_status": JiraIssueStatus.IN_PROGRESS,
                "transition_status": JiraIssueTransitionStatuses.START_WORK.name,
            },
            {
                "current_status": JiraIssueStatus.IN_PROGRESS,
                "next_status": JiraIssueStatus.READY_FOR_DEVELOPMENT,
                "transition_status": JiraIssueTransitionStatuses.TO_DEVELOPMENT.name,
            },
            {
                "current_status": JiraIssueStatus.READY_FOR_DEVELOPMENT,
                "next_status": JiraIssueStatus.DEVELOPMENT,
                "transition_status": JiraIssueTransitionStatuses.START_DEVELOPMENT.name,
            },
            {
                "current_status": JiraIssueStatus.DEVELOPMENT,
                "next_status": JiraIssueStatus.REVIEW,
                "transition_status": JiraIssueTransitionStatuses.TO_REVIEW.name,
            },
            {
                "current_status": JiraIssueStatus.REVIEW,
                "next_status": JiraIssueStatus.READY_FOR_TEST,
                "transition_status": JiraIssueTransitionStatuses.TO_TEST.name,
            },
            {
                "current_status": JiraIssueStatus.READY_FOR_TEST,
                "next_status": JiraIssueStatus.TESTING,
                "transition_status": JiraIssueTransitionStatuses.START_TESTING.name,
            },
            {
                "current_status": JiraIssueStatus.TESTING,
                "next_status": JiraIssueStatus.READY_TO_CHECK,
                "transition_status": JiraIssueTransitionStatuses.FINISH_TESTING.name,
            },
            {
                "current_status": JiraIssueStatus.READY_TO_CHECK,
                "next_status": JiraIssueStatus.READY_TO_INSTALL,
                "transition_status": JiraIssueTransitionStatuses.APPROVE.name,
            },
            {
                "current_status": JiraIssueStatus.READY_TO_INSTALL,
                "next_status": JiraIssueStatus.CLOSED,
                "transition_status": JiraIssueTransitionStatuses.CLOSE.name,
            },
        ],
        "Default Story Enabler Workflow v 1.1": [
            {
                "current_status": JiraIssueStatus.BACKLOG,
                "next_status": JiraIssueStatus.PBR,
                "transition_status": JiraIssueTransitionStatuses.START_PBR.name,
            },
            {
                "current_status": JiraIssueStatus.PBR,
                "next_status": JiraIssueStatus.OPEN,
                "transition_status": JiraIssueTransitionStatuses.FINISH_PBR.name,
                "fields": {
                    "customfield_12300": {
                        "id": "31308",
                        "value": "Исследовательское",
                    }
                },
            },
            {
                "current_status": JiraIssueStatus.OPEN,
                "next_status": JiraIssueStatus.IN_PROGRESS,
                "transition_status": JiraIssueTransitionStatuses.START_WORK.name,
            },
            {
                "current_status": JiraIssueStatus.IN_PROGRESS,
                "next_status": JiraIssueStatus.READY_FOR_REVIEW,
                "transition_status": JiraIssueTransitionStatuses.READY_FOR_REVIEW.name,
            },
            {
                "current_status": JiraIssueStatus.READY_FOR_REVIEW,
                "next_status": JiraIssueStatus.REVIEW,
                "transition_status": JiraIssueTransitionStatuses.START_REVIEW.name,
            },
            {
                "current_status": JiraIssueStatus.REVIEW,
                "next_status": JiraIssueStatus.READY_FOR_TEST,
                "transition_status": JiraIssueTransitionStatuses.READY_FOR_TEST.name,
            },
            {
                "current_status": JiraIssueStatus.READY_FOR_TEST,
                "next_status": JiraIssueStatus.TESTING,
                "transition_status": JiraIssueTransitionStatuses.START_TESTING.name,
            },
            {
                "current_status": JiraIssueStatus.TESTING,
                "next_status": JiraIssueStatus.CLOSED,
                "transition_status": JiraIssueTransitionStatuses.DONE.name,
            },
            {
                "current_status": JiraIssueStatus.READY_TO_CHECK,
                "next_status": JiraIssueStatus.READY_TO_INSTALL,
                "transition_status": JiraIssueTransitionStatuses.APPROVE.name,
            },
            {
                "current_status": JiraIssueStatus.READY_TO_INSTALL,
                "next_status": JiraIssueStatus.CLOSED,
                "transition_status": JiraIssueTransitionStatuses.DONE.name,
            },
        ],
        "[MTS] Release Workflow 2.0": [
            {"current_status": "Created", "next_status": "Planning", "transition_status": "Plan"},
            {
                "current_status": "Planning",
                "next_status": "Building",
                "transition_status": "Build",
                "fields": {JIRA_FIELD_VERSION_PICKER: ["00000"]},
            },
            {"current_status": "Building", "next_status": "Testing", "transition_status": "Test"},
            {"current_status": "Testing", "next_status": "UAT", "transition_status": "To UAT"},
            {
                "current_status": "UAT",
                "next_status": "Deploy",
                "transition_status": "To Deploy",
                # "fields": {JIRA_FIELD_COMMAND_DECISION: {"value": "Рекомендовано к установке"}}
            },
            {"current_status": "Deploy", "next_status": "Released", "transition_status": "Released"},
            {"current_status": "Released", "next_status": "Closed", "transition_status": "Close"},
        ],
        "[MTS] Data Description Workflow": [
            {"current_status": "Backlog", "next_status": "Closed", "transition_status": "Cancel"},
        ],
    }


class JiraIssueMover:
    def __init__(self, jira: JIRA) -> None:
        self._jira: JIRA = jira

    def get_workflow_name(self, issue: Issue) -> str | None:
        _issue_type_mappings = "issueTypeMappings"
        _project_key = issue.fields.project.key
        _issue_type_id = issue.fields.issuetype.id

        workflow_name = ""
        try:
            wfs = self._jira.project_workflow_scheme(_project_key)
            workflow_name = wfs.raw.get(_issue_type_mappings, {}).get(_issue_type_id, "")

            permalink: str = cast(str, issue.permalink())

            msg = f"Для задачи {permalink} нашли workflow {workflow_name}"
            logging.debug(msg)
        except JIRAError as e:
            error_msgs = [
                "У вас нет прав для просмотра схемы бизнес-процесса завершенного проекта.",
                "You do not have permission to see the workflow scheme for the passed project.",
            ]
            if e.args[0] in error_msgs:
                msg = (
                    f"{issue.key} нет прав для пользователя на просмотр схемы workflow,"
                    f" нужно добавить права в настройках проекта Jira"
                )
                logging.error(msg)
                return None
        except UnboundLocalError as e:
            msg = f"Не нашли ни один wfs для проекта {_project_key}, ошибка {e.args[0]}"
            logging.error(msg)
            return None
        return workflow_name if workflow_name else None

    @staticmethod
    def get_transition_flow(current_status_name: str, workflow: List[Dict[Any, Any]]) -> Optional[Dict[Any, Any]]:
        for flow in workflow:
            if current_status_name == flow.get("current_status", {}):
                return flow
        logging.debug(f"не нашли {current_status_name} в {workflow}")
        return None

    def move_issue_to_final_status(
        self, issue: Issue, new_status_name: Optional[Union[JiraIssueStatus | str]], wf_name: Optional[str] = None
    ) -> bool:
        """
        Переходит по статусам workflow задачи до достижения заданного финального статуса.

        Args:
            issue: Объект задачи Jira.
            new_status_name: Желаемый финальный статус (строка или JiraIssueStatus).

        Returns:
            True — если задача переведена в нужный статус, иначе False.
        """
        if isinstance(new_status_name, JiraIssueStatus):
            new_status_name = new_status_name.value
        elif new_status_name is None:
            new_status_name = ""

        if wf_name is None:
            wf_name = self.get_workflow_name(issue)

        if wf_name is None and issue.fields.issuetype.name == "Release":
            wf_name = "[MTS] Release Workflow 2.0"

        if wf_name is None:
            return False

        workflow = WorkFlowMap.workflows.get(wf_name, [])
        max_tries = len(workflow)

        current_status_name = issue.fields.status.name
        tries = 0

        while current_status_name != new_status_name and tries <= max_tries:
            flow = self.get_transition_flow(current_status_name=current_status_name, workflow=workflow)
            if not flow:
                logging.error(
                    f"{issue.key} обновите workflow '{wf_name}': статус '{current_status_name}' не найден.\n{workflow}"
                )
                return False

            transition_status = flow.get("transition_status", "")
            fields = flow.get("fields", {})

            if not transition_status:
                logging.error(
                    f"{issue.key} обновите workflow '{wf_name}': статус '{current_status_name}' не содержит перехода.\n{workflow}"
                )
                return False

            try:
                transition_result = self._jira.transition_issue(
                    issue=issue, transition=transition_status, fields=fields
                )
                logging.info(
                    f"{issue.key}:  успешно перевели задачу {current_status_name} -> {new_status_name},"
                    f" c параметрами: {transition_status}, fields: {str(fields)}"
                )
            except (AttributeError, JIRAError) as e:
                logging.warning(
                    f"{issue.key} ошибка при переходе {current_status_name} → {new_status_name}, "
                    f"переход: '{transition_status}': {e}"
                )
                err_msg = str(e.args[0]) if e.args else ""

                if "You have open subtasks" in err_msg or "Invalid transition name" in err_msg:
                    return False

                transition_result = self._move_with_additional_fields(issue, new_status_name, transition_status)
            except Exception as e:
                logging.error("Непредвиденная ошибка: %s", e)
                transition_result = self._move_with_additional_fields(issue, new_status_name, transition_status)

            issue = self._jira.issue(issue.key)
            new_current_status = issue.fields.status.name

            if transition_result:
                logging.info(
                    f"{issue.key} переведена: {current_status_name} → {new_current_status} через '{transition_status}'"
                )

            if new_current_status == new_status_name:
                return True

            current_status_name = new_current_status
            tries += 1

        return bool(current_status_name == str(new_status_name))

    def move_with_additional_fields(
        self,
        issue: Issue,
        to_status: str,
        transition_status: str | JiraIssueTransitionStatus = JiraIssueTransitionStatuses.FINISH_PBR.name,
        fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self._move_with_additional_fields(
            issue=issue, to_status=to_status, transition_status=transition_status, fields=fields
        )

    def _move_with_additional_fields(
        self,
        issue: Issue,
        to_status: str = JiraIssueStatus.OPEN,
        transition_status: str | JiraIssueTransitionStatus = JiraIssueTransitionStatuses.FINISH_PBR.name,
        fields: Optional[Dict[Any, Any]] = None,
    ) -> bool:
        status = ""
        transition_status = (
            transition_status.name if isinstance(transition_status, JiraIssueTransitionStatus) else transition_status
        )
        field_direction: Dict[Any, Any] = fields if fields else {}
        comment_direction = None
        if issue.fields.issuetype.name in ("Story", "Story Enabler"):
            field_direction = {
                "customfield_12300": {
                    "id": "31308",
                    "value": "Исследовательское",
                }
            }
            status = JiraIssueTransitionStatuses.FINISH_PBR.name

        elif issue.fields.issuetype.name in ("Bug", "Ошибка"):
            field_direction = {"customfield_15812": {"id": "22057", "value": "1"}}
            status = JiraIssueTransitionStatuses.CLOSE.name

        elif issue.fields.issuetype.name == IssueTypes.release_name:
            if transition_status == JiraIssueTransitionStatuses.BUILD.name:
                version_name = issue.fields.summary.split(" ")[1]
                version = self._jira.get_project_version_by_name(
                    project=issue.fields.project.key,
                    version_name=version_name,
                )
                field_direction = {JIRA_FIELD_VERSION_PICKER: [str(version.id)]}
                status = transition_status
            elif transition_status == "To UAT":
                comment_direction = "Рекомендовано к установке"
                status = transition_status
            elif transition_status == "To Deploy":
                field_direction = {
                    JIRA_FIELD_COMMAND_DECISION: {"value": "Рекомендовано к установке"},
                    # "customfield_25000": "sa0000jiraqaqueue"},
                }
                comment_direction = "Рекомендовано к установке"
                status = transition_status
            else:
                field_direction = {}
        else:
            logging.error(f"{issue.key} укажите какое поле надо добавить при перемещении задачи")

        logging.info(f"{issue.key} переводим в статус {to_status}")

        try:
            self._jira.transition_issue(
                issue,
                status,
                comment=comment_direction,
                fields=field_direction,
            )
            msg = (
                f"{issue.key} перевели задачу, {issue.fields.status.name} > {to_status},"
                f" транзитивный статус {status} (запрошен: {transition_status})"
            )
            logging.info(msg)
            return True
        except Exception as e:
            msg = (
                f"{issue.key} ошибка при переводе из {issue.fields.status.name} > {to_status},"
                f" транзитивный статус {status} (запрошен: {transition_status}): {e}"
            )
            logging.error(msg)
        return False
