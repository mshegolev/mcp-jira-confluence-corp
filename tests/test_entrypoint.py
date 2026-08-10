"""Entry-point smoke tests — the console script must actually start.

Before this file, ``coverage`` reported **0%** for ``server.py``,
``jira_tools.py``, ``confluence_tools.py``, ``workflow_tools.py`` and
``prompts.py``. Not "thinly covered" — never imported. The whole suite could be
green while ``mcp-jira-confluence-corp`` died on its first import, which is
exactly what happened when ``mcp`` 2.0 removed ``mcp.server.fastmcp``: to an MCP
client that looks like an opaque transport failure, easy to misread as a bad
token or URL.

What these tests walk is the path a real client walks, and nothing else did::

    console_scripts metadata → mcp_jira_confluence.server:main
        → create_server() → register_*_tools() → mcp.run() → stdio

Everything is offline. ``JiraConfluenceClient`` builds its ``atlassian`` clients
lazily (see the ``jira`` / ``confluence`` properties), so constructing the server
touches neither Jira nor Confluence and needs no PAT.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from importlib.metadata import entry_points

import pytest

CONSOLE_SCRIPT = "mcp-jira-confluence-corp"

# Env vars the server must NOT require in order to start. An MCP client launches
# the process first and only then discovers whether it is configured; a server
# that refuses to boot without a PAT cannot even report that it is misconfigured.
CONFIG_ENV_VARS = [
    "JIRA_URL",
    "JIRA_USERNAME",
    "JIRA_TOKEN",
    "JIRA_PERSONAL_TOKEN",
    "CONFLUENCE_URL",
    "CONFLUENCE_USERNAME",
    "CONFLUENCE_TOKEN",
    "CONFLUENCE_PERSONAL_TOKEN",
    "MCP_BYPASS_DOMAINS",
]

# One representative per registration module, so a whole register_*_tools() call
# silently dropping out of create_server() is caught by name and not just by count.
TOOLS_BY_MODULE = {
    "jira_tools": "jira_get_issue",
    "confluence_tools": "confluence_get_page",
    "workflow_tools": "jira_daily_standup_summary",
}
EXPECTED_TOOL_COUNT = 35
EXPECTED_PROMPT_COUNT = 6


def _console_script_entry_point():
    """Return the console_scripts entry point from installed distribution metadata."""
    eps = [ep for ep in entry_points(group="console_scripts") if ep.name == CONSOLE_SCRIPT]
    assert eps, (
        f"console script {CONSOLE_SCRIPT!r} is not registered in installed metadata — "
        f"either the package is not installed (run `pip install -e '.[dev]'`) or "
        f"[project.scripts] in pyproject.toml no longer declares it"
    )
    return eps[0]


def test_console_script_is_declared_and_resolves() -> None:
    """``[project.scripts]`` points at a real, callable target.

    Loading the entry point imports ``mcp_jira_confluence.server``, which imports
    every tool module. A broken import anywhere below the facade fails here.
    """
    ep = _console_script_entry_point()
    assert ep.value == "mcp_jira_confluence.server:main", f"unexpected entry-point target: {ep.value}"

    main = ep.load()  # <- imports the facade; this is where a dead package dies
    assert callable(main), f"entry point {ep.value} resolved to a non-callable: {main!r}"

    from mcp_jira_confluence.server import main as facade_main

    assert main is facade_main, "console script resolves to a different object than mcp_jira_confluence.server.main"


def test_console_script_starts_and_exits_cleanly_on_eof() -> None:
    """Run the real entry point in a fresh interpreter and let stdio hit EOF.

    The closest offline approximation of "an MCP client launched the server":
    metadata lookup, import, ``main()``, ``create_server()``, ``mcp.run()`` over
    stdio, then a clean shutdown when the transport closes. An import-time or
    registration-time explosion shows up as a non-zero exit plus a traceback.
    """
    program = (
        "from importlib.metadata import entry_points\n"
        f"ep = next(e for e in entry_points(group='console_scripts') if e.name == {CONSOLE_SCRIPT!r})\n"
        "ep.load()()\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", program],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"console script exited with {proc.returncode} instead of shutting down cleanly on EOF.\n"
        f"--- stderr ---\n{proc.stderr}\n--- stdout ---\n{proc.stdout}"
    )
    assert "Traceback" not in proc.stderr, f"console script printed a traceback:\n{proc.stderr}"


def test_console_script_keeps_stdout_clean_for_the_protocol() -> None:
    """stdio transport owns stdout — a stray print corrupts the JSON-RPC stream.

    ``server.py`` deliberately routes logging to stderr for this reason. A log
    line or ``print`` that leaks to stdout desynchronises the client's parser and
    surfaces as an unreadable protocol error rather than as a logging bug.
    """
    program = (
        "from importlib.metadata import entry_points\n"
        f"ep = next(e for e in entry_points(group='console_scripts') if e.name == {CONSOLE_SCRIPT!r})\n"
        "ep.load()()\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", program],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.stdout == "", f"non-protocol bytes written to stdout by the stdio server:\n{proc.stdout!r}"


def test_create_server_registers_every_tool_module() -> None:
    """``create_server()`` must wire all four registration calls, not merely build a FastMCP."""
    from mcp_jira_confluence.server import create_server

    tools = asyncio.run(create_server().list_tools())
    names = {t.name for t in tools}

    for module, sample in TOOLS_BY_MODULE.items():
        assert sample in names, f"{sample!r} missing — register_{module.replace('_tools', '')}_tools() did not run"

    assert len(tools) == EXPECTED_TOOL_COUNT, f"expected {EXPECTED_TOOL_COUNT} tools, got {len(tools)}: {sorted(names)}"


def test_every_tool_is_describable_over_the_protocol() -> None:
    """``list_tools()`` builds each tool's JSON Schema from its annotations.

    A malformed signature therefore fails here rather than at a client's first
    handshake, and a tool with no description is one an agent cannot choose.
    """
    from mcp_jira_confluence.server import create_server

    for t in asyncio.run(create_server().list_tools()):
        assert t.description, f"tool {t.name} has no description — agents pick tools by description"
        assert t.inputSchema, f"tool {t.name} has no input schema"


def test_prompts_are_registered() -> None:
    """Prompts live in a separate registry; losing them must not be silent."""
    from mcp_jira_confluence.server import create_server

    prompts = asyncio.run(create_server().list_prompts())
    assert len(prompts) == EXPECTED_PROMPT_COUNT, (
        f"expected {EXPECTED_PROMPT_COUNT} prompts, got {len(prompts)}: {sorted(p.name for p in prompts)}"
    )


def test_server_builds_with_no_configuration_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every JIRA_*/CONFLUENCE_* var and the server must still come up.

    Connections are lazy by design. If someone moves credential resolution into
    ``JiraConfluenceClient.__init__`` or into a module import, the client gets a
    server that will not start instead of a tool returning an actionable error.
    """
    for var in CONFIG_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    from mcp_jira_confluence.server import create_server

    assert len(asyncio.run(create_server().list_tools())) == EXPECTED_TOOL_COUNT


def test_building_the_server_makes_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Startup must be offline — CI has no route to a corporate Atlassian host.

    Guards the laziness contract directly: any eager ``requests`` call during
    ``create_server()`` (a whoami probe, a server-info check) would both hang CI
    and make the console script unstartable outside the corporate network.
    """
    import requests.adapters

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("create_server() attempted a network call; startup must stay lazy and offline")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", _forbidden)

    from mcp_jira_confluence.server import create_server

    assert asyncio.run(create_server().list_tools())
