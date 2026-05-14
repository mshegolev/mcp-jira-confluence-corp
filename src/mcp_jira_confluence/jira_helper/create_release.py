# type: ignore
from qa_assistant.manager_helpers.release_helper import ReleaseHelper
from qa_assistant.project_helper.projects import Projects

if __name__ == "__main__":
    project = Projects.einvy
    fix_version = "v0.17.0"

    send_planning_mail = False
    move_qa_debt = False
    create = True
    released = False
    task_moving = False

    release = ReleaseHelper(project=project, fix_version=fix_version)
    if task_moving:
        release.set_actual_status_for_story(fix_version=fix_version)

    if create:
        release.prepare_all_tasks_in_release(fix_version=fix_version, ignore_closed=True)
        release.set_actual_status_for_story(fix_version=fix_version)
        release.create_release(fix_version=fix_version)
    if send_planning_mail:
        release.send_email_plan_to_install(
            fix_version="v0.16.1",
            install_date="13.04.2023",
            install_time="с 09:00 до 10:00",
            devops="Юлдубаев Анур",
            qa_verification_task="EINVY-2095",
            dry_run=True,
        )
    if move_qa_debt:
        release.JiraHelper.move_subtask_qa_to_debt_story(fix_version_name=fix_version, ignore_release_task=True)
    if released:
        release.JiraHelper.move_subtask_qa_to_debt_story(fix_version_name=fix_version)
        release.close_release(fix_version=fix_version)
