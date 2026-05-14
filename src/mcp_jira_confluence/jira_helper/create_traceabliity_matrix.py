# type: ignore
import urllib3

from qa_assistant.manager_helpers.traceability_helper import TraceabilityHelper
from qa_assistant.project_helper.projects import Projects

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == "__main__":
    project = Projects.einvy
    tc = TraceabilityHelper(project=project)
    issues = tc.get_jira_issues_for_traceability_matrix()
    cases = tc.get_tests_from_allure()
    tc.create_trace_ability_matrix(issues=issues, cases=cases)
