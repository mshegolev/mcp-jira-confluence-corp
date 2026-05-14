# type: ignore
import argparse
import logging
from typing import Optional

import urllib3
from jira import Issue

from qa_assistant.manager_helpers.issue_types import IssueTypes
from qa_assistant.manager_helpers.jira_helper import JiraHelper
from qa_assistant.project_helper.projects import Project, Projects
from qa_assistant.staff_helper.employees import Employees
from qa_assistant.staff_helper.engineer import Engineer
from qa_assistant.staff_helper.roles import Roles
from qa_assistant.staff_helper.task_types import TaskType

urllib3.disable_warnings()


def create_tech_subtask(summary, parent_key, project, fix_version) -> None:
    j = JiraHelper(project=project)
    issue = j.get_issue(parent_key)
    issue = j.create_subtask(
        parent_task_key=issue.key,
        task_type=TaskType.TechDoc.task,
        assignee=Employees().get_project_engineers(project),
        task_name=summary,
        fix_version=fix_version,
    )

    logging.info(f"Created tech doc subtask: {issue.key}")


def create_dev_subtask(project, fix_version) -> None:
    j = JiraHelper(project=project)
    issues = j.get_issues_all_in_release(fix_version_name=fix_version, without_closed_issue=True)
    issues = [_ for _ in issues if j.is_story_or_story_enabler(_.key)]
    for issue in issues:
        is_subtask_exist = False
        for sub_task in issue.fields.subtasks:
            if str(IssueTypes.development_sub_task_id) == sub_task.fields.issuetype.id:
                is_subtask_exist = True
                break
        if is_subtask_exist:
            continue

        assignee = (
            issue.fields.assignee.raw.get("name")
            if issue.fields.assignee.raw.get("name") in [Employees.yabatalo, Employees.dvpolsh1, Employees.svpolichno]
            else Employees.sa0000jiraqaqueue
        )
        issue = j.create_subtask(
            parent_task_key=issue.key,
            task_type=TaskType.Dev.development_sub_task,
            assignee=assignee,
            task_name=issue.fields.summary,
            fix_version=fix_version,
        )

        logging.info(f"Created dev subtask: {issue.key}")


def create_story_enabler(summary: str, project: str, fix_version: list) -> Issue:
    j = JiraHelper(project=project)

    task = {
        "project": j.project.key,
        "summary": summary,
        "description": summary,
        "issuetype": {"name": IssueTypes.story_enabler_name},
        "fixVersions": fix_version,
    }
    issue = j._jira.create_issue(fields=task)
    assert issue
    logging.info(f"Created story enabler: https://jira.mts.ru/browse/{issue.key}")
    return issue


def create_tasks(
    parent_key: str,
    tasks: Optional[list | str],
    assignees: Optional[str | Engineer | list],
    move_qa_task_to_qa_debt: bool = False,
    create_if_exist: bool = False,
) -> None:
    project = get_project_by_parent_key(parent_key)
    j = JiraHelper(project=project)
    if isinstance(tasks, str):
        tasks = [tasks]
    elif not isinstance(tasks, list):
        raise NameError("В метод можно передовать только задачу или список задач")
    if isinstance(assignees, str):
        assignees = [assignees]
    elif isinstance(assignees, Engineer):
        assignees = [assignees.name]
    elif not isinstance(assignees, list):
        raise NameError("В метод можно передовать только иполнителя или список исполнителей")

    for current_assignee in assignees:
        for task_type in tasks:
            # todo: if parent_key is sabtask, crate subtask for parent_key and set the name of checked subtask
            task_name = None
            if not j.is_parent_task(key=parent_key):
                task_name = j.get_issue(parent_key).fields.summary
                parent_key = j.get_issue_parent_key(key=parent_key)
            if not j.is_parent_task(key=parent_key):
                logging.error("ERROR: this is not a parent task!!!!")
                continue
            if (
                j.is_sub_task_exists(parent_task=parent_key, sub_task_type=task_type)
                or j.get_linked(issue=parent_key, linked_type="parent of", labels=task_type)
            ) and not create_if_exist:
                logging.warning(
                    f"WARNING: {parent_key}: Задача {task_type} уже создана, параметр create_if_exist=False"
                )
                continue
            else:
                issue = j.create_subtask(
                    parent_task_key=parent_key,
                    task_type=task_type,
                    assignee=current_assignee,
                    task_name=task_name,
                )
                logging.info(
                    "INFO: New task created ",
                    parent_key,
                    issue.id,
                    issue.key,
                    current_assignee,
                    task_type,
                )
    if move_qa_task_to_qa_debt:
        p_key = j.get_issue(parent_key)
        fix_version = p_key.fields.fixVersions[0].name
        j.move_subtask_qa_to_debt_story(fix_version_name=fix_version)
    return None


def do(
    parent: Optional[str] = None,
    task_types: Optional[list] = None,
    project: Optional[str | Project] = None,
) -> None:
    validation_key_and_project(parent, project)
    if not project:
        project = Projects.einvy
    j = JiraHelper(project=project)
    parent_issues = [parent] if parent else j.get_all_story_keys()
    task_types = task_types if task_types else TaskType.QA.all

    for parent_issue in parent_issues:
        for issue_type in task_types:
            if not j.is_sub_task_exists(parent_task=parent_issue, sub_task_type=issue_type):
                j.create_subtask(parent_task_key=parent_issue, task_type=issue_type)


def validation_key_and_project(parent: str, project: str) -> None:
    if parent and project:
        assert project in parent, "Задача от другого проекта"
    if project:
        assert project in [Projects.any]


def get_auto_qa(project) -> str:
    emp = Employees()
    engineers = emp.get_engineers(project_key=project, qualification=Roles.auto)
    return engineers[0] if engineers else emp.get_service_user()


def get_manual_qa(project) -> str:
    emp = Employees()
    engineers = emp.get_engineers(project_key=project, qualification=Roles.manual)
    return engineers[0] if engineers else emp.get_service_user()


def create_all_qa_with_assignee(parent_key, manual_qa=None, auto_qa=None, tasks=None) -> None:
    assignee = None
    manual_qa_tasks = [
        TaskType.QA.manual,
        TaskType.QA.verification,
        TaskType.DevOps.deploy_stage,
        TaskType.TechDoc.techdoc,
    ]
    aqa_tasks = [TaskType.QA.auto]
    if tasks is None:
        tasks = manual_qa_tasks + aqa_tasks
    elif isinstance(tasks, str):
        tasks = [tasks]

    is_valid_key(parent_key)
    project = get_project_by_parent_key(parent_key)

    for task in tasks:
        if task in manual_qa_tasks:
            assignee = get_manual_qa(project)
        elif task in aqa_tasks:
            assignee = get_auto_qa(project)
        create_tasks(parent_key=parent_key, tasks=task, assignees=assignee)


def is_valid_key(issue_key) -> None:
    assert issue_key != "", "Задайте номер родительской задачи"
    is_valid = False
    for project in [prop for prop in dir(Projects) if not str(prop).startswith("_")]:
        if project.lower() in issue_key.lower():
            is_valid = True
    assert is_valid, f"Задача {issue_key} от другого проекта"


def get_project_by_parent_key(issue_key: str) -> str:
    is_valid_key(issue_key)
    for _ in Projects.any:
        if _.name.lower() in issue_key.lower():
            return _.key
    return ""


def arg_parser() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-k",
        "--key",
        type=str,
        dest="key",
        help="Parrent _ key, example: EINVY-439",
        default=None,
    )
    parser.add_argument(
        "-jdi",
        "--just_do_it",
        dest="just_do_it",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If you need to do all, just enable do, example: --just_do_it",
    )
    args = parser.parse_args()
    for _ in args._get_kwargs():
        globals()[f"{_[0]}"] = _[1]
    return globals()


def get_jira_issues_for_test(project: Projects.einvy.key, fixVersion) -> None:
    if isinstance(project, Project):
        project_key = project.key
    elif isinstance(project, str):
        assert project in Projects.any, f"{project} Не найден в существующих проектах {Projects.any}"
        project_key = project
    elif not isinstance(project, str):
        raise NameError("Укажите корректный проект einvy, gld")
    j = JiraHelper(project=project)
    if project == Projects.einvy:
        jql_str = (
            f'project={project_key} and fixVersion="{fixVersion}" '
            f'and type in ("Story", "Story Enabler") and (labels !=qa_skip or labels is EMPTY )'
        )

    else:
        raise NameError("Нужно сформировать запрос для получения историй на тестирование")
    issues = j.get_issues_jql(jql_str=jql_str)
    return [issue.key for issue in issues]


if __name__ == "__main__":
    arg_parser()

    key = "EINVY-2918"

    keys = []
    # keys = get_jira_issues_for_test(project=Projects.einvy, fixVersion="v0.15.0")

    if keys:
        for _ in keys:
            logging.info(f"create task with {_}")
            create_all_qa_with_assignee(parent_key=_, tasks=TaskType.QA.verify_auto)
    if key:
        logging.info(f"create task with {key}")
        create_all_qa_with_assignee(
            parent_key=key, tasks=TaskType.QA.all
        )  # if just_do_it:  #     logging.info("You choose JUST DO IT, LETS ROCK!!!")  #     do()  #     logging.info("ENJOY!!!")

    # task_types = [TaskType.TechDoc.techdoc]  # assignees = Employees.dvmark10  # create_tasks(parent_key=key, tasks=task_types, assignees=assignees)
