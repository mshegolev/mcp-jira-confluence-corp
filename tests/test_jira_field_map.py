"""Tests for Jira field mapping discovery."""

from mcp_jira_confluence.client import JiraConfluenceClient
from mcp_jira_confluence.config import ConfluenceConfig, JiraConfig, ProxyConfig
from mcp_jira_confluence.utils import render_field_map_markdown


class FakeJira:
    """Small fake covering the atlassian-python-api calls used by field maps."""

    def get_all_fields(self):
        return [
            {
                "id": "summary",
                "name": "Summary",
                "schema": {"type": "string", "system": "summary"},
            },
            {
                "id": "customfield_10000",
                "name": "RingCX Release",
                "schema": {
                    "type": "option",
                    "custom": "com.atlassian.jira.plugin.system.customfieldtypes:select",
                },
            },
        ]

    def issue_createmeta_issuetypes(self, project):
        assert project == "DATA"
        return {
            "projects": [
                {
                    "key": "DATA",
                    "issuetypes": [
                        {"id": "10001", "name": "QA Verification"},
                    ],
                }
            ]
        }

    def issue_createmeta_fieldtypes(self, project, issue_type_id):
        assert project == "DATA"
        assert issue_type_id == "10001"
        return {
            "projects": [
                {
                    "key": "DATA",
                    "issuetypes": [
                        {
                            "id": "10001",
                            "name": "QA Verification",
                            "fields": {
                                "summary": {
                                    "name": "Summary",
                                    "required": True,
                                    "schema": {"type": "string", "system": "summary"},
                                    "operations": ["set"],
                                },
                                "customfield_10000": {
                                    "name": "RingCX Release",
                                    "required": False,
                                    "schema": {
                                        "type": "option",
                                        "custom": (
                                            "com.atlassian.jira.plugin.system.customfieldtypes:"
                                            "select"
                                        ),
                                    },
                                    "allowedValues": [{"id": "1", "value": "2606161147"}],
                                    "operations": ["set"],
                                },
                            },
                        }
                    ],
                }
            ]
        }

    def issue_editmeta(self, key):
        assert key == "DATA-16199"
        return {
            "fields": {
                "summary": {
                    "name": "Summary",
                    "required": True,
                    "schema": {"type": "string", "system": "summary"},
                    "operations": ["set"],
                },
                "customfield_10000": {
                    "name": "RingCX Release",
                    "required": False,
                    "schema": {"type": "option", "custom": "select"},
                    "operations": ["set"],
                },
            }
        }

    def issue_fields(self, key):
        assert key == "DATA-16199"
        return {
            "summary": "Verify RINGCX v2606161147",
            "customfield_10000": {"id": "1", "value": "2606161147"},
        }


def make_client():
    client = JiraConfluenceClient(
        jira_config=JiraConfig(url="https://jira.example.com"),
        confluence_config=ConfluenceConfig(url="https://wiki.example.com"),
        proxy_config=ProxyConfig(),
    )
    client._jira = FakeJira()
    return client


def test_build_field_map_combines_global_project_and_issue_metadata():
    payload = make_client().build_field_map(
        project_key="DATA",
        issue_key="DATA-16199",
        max_rows=25,
    )

    assert payload["scope"] == {"project_key": "DATA", "issue_key": "DATA-16199"}
    assert payload["summary"]["global_field_count"] == 2
    assert payload["summary"]["project_issue_type_count"] == 1
    assert payload["summary"]["project_field_row_count"] == 2
    assert payload["summary"]["edit_field_row_count"] == 2
    assert payload["summary"]["total_rows"] == 6

    row = next(
        item
        for item in payload["rows"]
        if item["context"] == "edit" and item["field_id"] == "customfield_10000"
    )
    assert row["field_name"] == "RingCX Release"
    assert row["kind"] == "custom"
    assert row["sample_value"] == {"id": "1", "value": "2606161147"}


def test_render_field_map_markdown_groups_rows_and_truncates_tables():
    payload = make_client().build_field_map(
        project_key="DATA",
        issue_key="DATA-16199",
        max_rows=1,
    )

    rendered = render_field_map_markdown(payload)

    assert "# Jira Field Map" in rendered
    assert "Project create metadata" in rendered
    assert "Issue edit metadata" in rendered
    assert "| Context | Project | Issue Type | Field ID | Field Name | Kind |" in rendered
    assert "_Showing 1 of 2 rows._" in rendered
