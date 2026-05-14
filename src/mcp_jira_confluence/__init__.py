"""MCP server for Jira and Confluence with MTS proxy support."""

__version__ = "0.1.0"
__author__ = "Mikhail Shegolev"

from .client import JiraConfluenceClient
from .config import ProxyConfig, JiraConfig, ConfluenceConfig

__all__ = [
    "JiraConfluenceClient",
    "ProxyConfig",
    "JiraConfig",
    "ConfluenceConfig",
]
