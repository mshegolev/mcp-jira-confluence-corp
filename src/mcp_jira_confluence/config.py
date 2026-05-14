"""Configuration for Jira/Confluence MCP server with MTS proxy support.

Supports both custom implementation and qa_assistant helpers:
- ForkedFrom: /opt/develop/qa_assistant (ConfluenceHelper, JiraHelper)
- ProxySupport: Automatic bypass for internal MTS domains
- SSLVerify: Disabled by default for self-signed MTS certs
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass
class ProxyConfig:
    """Proxy configuration for MTS corporate network."""

    # SSH tunnel proxy (for Anthropic API and external HTTPS)
    socks5_host: str = "127.0.0.1"
    socks5_port: int = 11111
    http_tunnel_host: str = "127.0.0.1"
    http_tunnel_port: int = 11112

    # Internal MTS domains that should BYPASS proxy
    bypass_domains: list[str] = field(
        default_factory=lambda: [
            "*.mts.ru",
            "*.services.mts.ru",
            "confluence.mts.ru",
            "jira.mts.ru",
            "gitlab.services.mts.ru",
            "sregistry.mts.ru",
            "allure.services.mts.ru",
            "sonarqube.services.mts.ru",
        ]
    )

    # SSL verification (set to False for self-signed MTS certs)
    verify_ssl: bool = False

    def should_bypass(self, url: str) -> bool:
        """Check if URL should bypass proxy (internal MTS domain)."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        for domain in self.bypass_domains:
            if domain.startswith("*."):
                # Wildcard domain like *.mts.ru
                suffix = domain[2:]  # Remove *.
                if hostname.endswith(suffix):
                    return True
            else:
                # Exact match
                if hostname == domain:
                    return True

        return False

    def get_env_dict(self) -> dict[str, str]:
        """Return environment variables dict for requests/urllib."""
        return {
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "http_proxy": "",
            "https_proxy": "",
            "NO_PROXY": ",".join(self.bypass_domains),
            "no_proxy": ",".join(self.bypass_domains),
        }


@dataclass
class JiraConfig:
    """Jira connection configuration."""

    url: str
    username: Optional[str] = None
    token: Optional[str] = None
    personal_token: Optional[str] = None

    # Load from environment if not provided
    @classmethod
    def from_env(cls) -> "JiraConfig":
        """Load configuration from environment variables."""
        return cls(
            url=os.getenv("JIRA_URL", "https://jira.mts.ru"),
            username=os.getenv("JIRA_USERNAME"),
            token=os.getenv("JIRA_TOKEN"),
            personal_token=os.getenv("JIRA_PERSONAL_TOKEN"),
        )

    def get_auth_dict(self) -> dict:
        """Return auth dict for atlassian.Jira."""
        if self.personal_token:
            return {"personal_token": self.personal_token}
        elif self.token:
            return {"token": self.token}
        elif self.username:
            return {"username": self.username, "password": self.token}
        else:
            return {}


@dataclass
class ConfluenceConfig:
    """Confluence connection configuration."""

    url: str
    username: Optional[str] = None
    token: Optional[str] = None
    personal_token: Optional[str] = None

    # Load from environment if not provided
    @classmethod
    def from_env(cls) -> "ConfluenceConfig":
        """Load configuration from environment variables."""
        return cls(
            url=os.getenv("CONFLUENCE_URL", "https://confluence.mts.ru"),
            username=os.getenv("CONFLUENCE_USERNAME"),
            token=os.getenv("CONFLUENCE_TOKEN"),
            personal_token=os.getenv("CONFLUENCE_PERSONAL_TOKEN"),
        )

    def get_auth_dict(self) -> dict:
        """Return auth dict for atlassian.Confluence."""
        if self.personal_token:
            return {"personal_token": self.personal_token}
        elif self.token:
            return {"token": self.token}
        elif self.username:
            return {"username": self.username, "password": self.token}
        else:
            return {}
