# import os
#
# import urllib3
#
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#
# JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
# CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN")
# EMAIL_USER = os.environ.get("EMAIL_USER")
# EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
# ACCOUNT_USER = os.environ.get("ACCOUNT_USER")
# ACCOUNT_PASSWORD = os.environ.get("ACCOUNT_PASSWORD")
#
# assert JIRA_TOKEN is not None, (
#     "Укажите параметры JIRA_TOKEN,"
#     "export JIRA_TOKEN=SAFSAFE;\n"
# )
# assert EMAIL_USER is not None, "Укажите параметры EMAIL_USER и EMAIL_PASSWORD"
#
# key = None
# just_do_it = None
