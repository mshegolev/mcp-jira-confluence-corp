"""Configuration for Jira/Confluence MCP server with corporate proxy support.

The :class:`ProxyConfig` lets you list internal domains that should bypass any
system proxy (HTTP_PROXY/HTTPS_PROXY). This is useful in corporate networks
where an SSH tunnel for cloud APIs (e.g. Anthropic) would otherwise intercept
on-prem Atlassian traffic.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


def _parse_csv_env(name: str) -> list[str]:
    """Parse a comma-separated environment variable into a list."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class ProxyConfig:
    """Proxy configuration for corporate network environments.

    Attributes:
        bypass_domains: List of domain patterns that should bypass any system
            proxy. Supports exact match (``confluence.example.com``) and
            single-level wildcards (``*.example.com``). Loaded from the
            ``MCP_BYPASS_DOMAINS`` environment variable by default.
        verify_ssl: Whether to verify SSL certificates. Set to ``False`` for
            self-signed corporate certificates.
    """

    bypass_domains: list[str] = field(
        default_factory=lambda: _parse_csv_env("MCP_BYPASS_DOMAINS")
    )
    verify_ssl: bool = False

    def should_bypass(self, url: str) -> bool:
        """Return True if the URL host matches any configured bypass pattern."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        for domain in self.bypass_domains:
            if domain.startswith("*."):
                suffix = domain[2:]
                if hostname.endswith(suffix):
                    return True
            elif hostname == domain:
                return True

        return False

    def get_env_dict(self) -> dict[str, str]:
        """Return environment variables that disable system proxies for requests."""
        no_proxy = ",".join(self.bypass_domains) if self.bypass_domains else ""
        return {
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "http_proxy": "",
            "https_proxy": "",
            "NO_PROXY": no_proxy,
            "no_proxy": no_proxy,
        }


@dataclass
class JiraConfig:
    """Jira connection configuration."""

    url: str
    username: Optional[str] = None
    token: Optional[str] = None
    personal_token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "JiraConfig":
        """Load configuration from ``JIRA_*`` environment variables."""
        return cls(
            url=os.getenv("JIRA_URL", ""),
            username=os.getenv("JIRA_USERNAME"),
            token=os.getenv("JIRA_TOKEN"),
            personal_token=os.getenv("JIRA_PERSONAL_TOKEN"),
        )

    def get_auth_dict(self) -> dict:
        """Return the auth kwargs accepted by ``atlassian.Jira``.

        Priority:
            1. Basic Auth if a ``username`` is provided.
            2. Bearer token from ``personal_token`` (PAT).
            3. Bearer token from ``token``.
        """
        if self.username:
            return {"username": self.username, "password": self.token}
        if self.personal_token:
            return {"token": self.personal_token}
        if self.token:
            return {"token": self.token}
        return {}


@dataclass
class ConfluenceConfig:
    """Confluence connection configuration."""

    url: str
    username: Optional[str] = None
    token: Optional[str] = None
    personal_token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ConfluenceConfig":
        """Load configuration from ``CONFLUENCE_*`` environment variables."""
        return cls(
            url=os.getenv("CONFLUENCE_URL", ""),
            username=os.getenv("CONFLUENCE_USERNAME"),
            token=os.getenv("CONFLUENCE_TOKEN"),
            personal_token=os.getenv("CONFLUENCE_PERSONAL_TOKEN"),
        )

    def get_auth_dict(self) -> dict:
        """Return the auth kwargs accepted by ``atlassian.Confluence``.

        Priority:
            1. Basic Auth if a ``username`` is provided.
            2. Bearer token from ``personal_token`` (PAT).
            3. Bearer token from ``token``.
        """
        if self.username:
            return {"username": self.username, "password": self.token}
        if self.personal_token:
            return {"token": self.personal_token}
        if self.token:
            return {"token": self.token}
        return {}
