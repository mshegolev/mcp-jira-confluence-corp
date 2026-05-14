"""MCP Prompts — reusable templates for common Jira/Confluence workflows.

Prompts are first-class MCP primitives (alongside tools and resources). Unlike
tools, prompts do NOT call any API — they return a structured prompt the LLM
should follow next. The agent typically picks a prompt by name, FastMCP
substitutes the parameters, and the resulting messages are appended to the
conversation.

The prompts here encode opinionated workflows: how to write release notes,
how to audit a Confluence space, how to document a new feature, etc. They
deliberately reference the corresponding tool names (e.g.
``confluence_search``, ``jira_summarize_issue``) so the LLM knows which MCP
tools to call.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register every workflow prompt with the FastMCP server instance."""

    # ------------------------------------------------------------------
    # Confluence workflows
    # ------------------------------------------------------------------

    @mcp.prompt(
        name="confluence_create_release_notes",
        description=(
            "Draft a Confluence release-notes page from a set of Jira issues. "
            "Provide fix_version (and optionally space_key/parent_id) and the "
            "LLM will fetch the issues, group them, and produce a Storage-Format "
            "body ready for confluence_create_page."
        ),
    )
    def confluence_create_release_notes(
        fix_version: str,
        space_key: str,
        parent_id: Optional[str] = None,
    ) -> str:
        return f"""You are drafting Confluence release notes for fix version `{fix_version}` in space `{space_key}`.

Follow this workflow exactly:

1. Use `jira_search_issues` with JQL `fixVersion = "{fix_version}" ORDER BY issuetype, priority DESC` and `limit=100`.
2. Group the returned issues by `issuetype.name` (Story, Bug, Task, etc.).
3. For each group, list issues as a markdown bullet:
   `- [KEY] Summary (Status, Assignee)`
4. Convert your markdown into Confluence Storage Format (XHTML):
   - `<h1>` for the title, `<h2>` per issue-type group, `<ul><li>` for items.
   - Wrap Jira links with `<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">KEY</ac:parameter></ac:structured-macro>`.
5. Call `confluence_create_page` with:
   - `space_key="{space_key}"`
   - `title="Release Notes — {fix_version}"`
   - `parent_id={parent_id!r}` (omit if null)
   - `body=<your storage-format XHTML>`

Return the new page's URL and ID once created. Do not invent issue keys — only use what `jira_search_issues` returns.
"""

    @mcp.prompt(
        name="confluence_document_feature",
        description=(
            "Draft a Confluence feature documentation page from a Jira epic or "
            "story. The LLM will pull issue context, related links, and produce "
            "a structured page ready to publish."
        ),
    )
    def confluence_document_feature(
        issue_key: str,
        space_key: str,
        parent_id: Optional[str] = None,
        audience: str = "engineers",
    ) -> str:
        return f"""You are writing a Confluence feature page about Jira issue `{issue_key}` for audience: **{audience}**.

Workflow:

1. Call `jira_summarize_issue` with `issue_key="{issue_key}"`, `include_comments=true`, `include_changelog=false` to get the full context.
2. Call `jira_extract_links` with `issue_key="{issue_key}"` to discover related Confluence pages and Git repos. Surface these as a "Related" section.
3. For each Git link extracted, mention the repository name in the documentation.
4. Compose a Confluence Storage Format body with these sections:
   - `<h1>` page title (the issue summary).
   - `<h2>Overview</h2>` — 1-2 paragraphs explaining what this feature is, written for {audience}.
   - `<h2>Implementation</h2>` — bullets summarising the issue description.
   - `<h2>Related Jira</h2>` — link back to {issue_key} via the Jira macro.
   - `<h2>Related Documentation</h2>` — any Confluence links from step 2.
   - `<h2>Source Code</h2>` — any Git links from step 2.
5. Call `confluence_create_page` with:
   - `space_key="{space_key}"`
   - `title=<the issue summary>`
   - `parent_id={parent_id!r}` (omit if null)
   - `body=<your storage-format XHTML>`

Return the new page URL and ID.
"""

    @mcp.prompt(
        name="confluence_audit_page",
        description=(
            "Audit a Confluence page for staleness, broken links, missing "
            "metadata, and orphan child pages. Returns a written report."
        ),
    )
    def confluence_audit_page(page_id: str) -> str:
        return f"""Audit Confluence page `{page_id}` and produce a written report.

Run these tools in order:

1. `confluence_get_page` with `page_id="{page_id}"` to fetch metadata + body.
2. `confluence_get_page_history` with `page_id="{page_id}"` to learn when it was last modified and by whom.
3. `confluence_get_page_labels` with `page_id="{page_id}"` to check labels.
4. `confluence_get_page_children` with `page_id="{page_id}"` to list child pages.
5. `confluence_get_page_comments` with `page_id="{page_id}"` to surface unresolved feedback.

Then produce a report with these sections:

- **Freshness**: is the last update older than 90 days? Flag if yes.
- **Owner**: who is the last editor / page owner?
- **Labels**: are labels present? Suggest missing labels like `team-*`, `status-*`.
- **Body health**: is the body empty, very short (< 200 chars), or full of placeholder text like "TBD" / "TODO"?
- **Children**: list child pages. Flag any with the same title as the parent.
- **Open comments**: list comments still relevant.

End with a 1-3 line **Recommendation** ("Keep / Update / Archive / Merge into X").
"""

    @mcp.prompt(
        name="confluence_summarize_space",
        description=(
            "Survey a Confluence space and produce a structured summary: number "
            "of pages, recently updated, stale pages, top contributors."
        ),
    )
    def confluence_summarize_space(space_key: str, stale_days: int = 90) -> str:
        return f"""Produce a summary of Confluence space `{space_key}`.

Workflow:

1. Call `confluence_search` with `cql='space = {space_key} AND type = page'` and `limit=100` to enumerate pages. Use pagination (`offset=100`, etc.) if more than 100 pages exist; collect at most 500.
2. For each page, note `title`, `id`, and the `lastModified` field if available from search.
3. Compute these stats:
   - Total pages found.
   - Recently updated: pages modified in the last 30 days.
   - Stale pages: pages not modified in the last {stale_days} days.
4. Optional: for the top 3 oldest pages, also call `confluence_get_page_history` and report `lastUpdated.by.displayName`.

Output a markdown report with:
- **Overview**: total pages, recently updated, stale.
- **Top 10 recently updated pages** (id + title).
- **Top 10 stale pages** (id + title + lastModified).
- **Top 3 ancient pages**: who last edited them and when.
- **Recommendation**: one-paragraph suggestion ("review and refresh", "consider archiving", etc.).
"""

    # ------------------------------------------------------------------
    # Jira workflows
    # ------------------------------------------------------------------

    @mcp.prompt(
        name="jira_sprint_report",
        description=(
            "Produce a sprint review / retro-ready report for a given sprint, "
            "with completed vs. spillover work, blockers, and per-assignee load."
        ),
    )
    def jira_sprint_report(sprint_id: int) -> str:
        return f"""Compile a sprint review report for sprint `{sprint_id}`.

Workflow:

1. Call `jira_daily_standup_summary` with `sprint_id={sprint_id}` for status/assignee/blocker counts.
2. Call `jira_list_sprint_issues` with `sprint_id={sprint_id}` and `limit=200` to enumerate every issue.
3. Categorise issues:
   - **Completed**: status in (Done, Closed, Resolved).
   - **Spillover**: any other status — these will roll into the next sprint.
   - **Blocked**: status == 'Blocked' OR label contains 'blocked'.
4. For each Completed issue, list `KEY — Summary (assignee)`.
5. For each Spillover issue, list `KEY — Summary (status, assignee)`.

Produce a markdown report:
- **Sprint summary**: from step 1.
- **Completed work**: bullet list from step 4.
- **Spillover**: bullet list from step 5.
- **Blockers**: from step 1 (if any).
- **Per-assignee load**: top contributors and their completed/spillover ratio.
- **Recommendation**: 1-2 sentences for sprint retro (e.g. "WIP too high", "blocker pattern around X").
"""

    @mcp.prompt(
        name="jira_triage_my_issues",
        description=(
            "Triage the user's own assigned issues: identify what to work on "
            "next, what is stale, and what should be re-prioritised."
        ),
    )
    def jira_triage_my_issues(project_key: Optional[str] = None) -> str:
        scope = f"in project `{project_key}`" if project_key else "across all projects"
        return f"""Help me triage my assigned Jira issues {scope}.

Workflow:

1. Call `jira_get_my_issues` with `limit=100` and `project_key={project_key!r}` (omit if null).
2. For every issue in the result, classify it:
   - **Now**: priority is Highest/High AND status is "In Progress" or "To Do".
   - **Stale**: not updated in the last 14 days (use `fields.updated`).
   - **Blocked**: status == "Blocked" OR labels contains "blocked".
   - **Other**: everything else.
3. For up to 3 "Now" issues, optionally call `jira_summarize_issue` to give me a context-rich next-step suggestion.

Produce a structured markdown plan:
- **Work on now** (max 3): with a 1-sentence "next step" for each.
- **Stale (review)**: with last-updated date.
- **Blocked**: with the blocking reason if you can detect it from comments.
- **Defer**: everything else.

End with a one-paragraph **Recommendation** for how to spend the next 2 hours.
"""
