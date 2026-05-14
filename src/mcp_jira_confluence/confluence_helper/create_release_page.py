# type: ignore

from qa_assistant.confluence_helper.confluence_helper import ConfluenceHelper
from qa_assistant.project_helper.projects import Projects

project = Projects.einvy
fix_version = "v5.1.0"

if __name__ == "__main__":
    confluence = ConfluenceHelper(project=project)
    confluence.create_release_page(fix_version=fix_version)
