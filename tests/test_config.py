"""Tests for the config module."""

from mcp_jira_confluence.config import ConfluenceConfig, JiraConfig, ProxyConfig


class TestProxyConfig:
    def test_default_bypass_is_empty(self, monkeypatch):
        monkeypatch.delenv("MCP_BYPASS_DOMAINS", raising=False)
        config = ProxyConfig()
        assert config.bypass_domains == []

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_BYPASS_DOMAINS", "*.example.com, internal.corp")
        config = ProxyConfig()
        assert "*.example.com" in config.bypass_domains
        assert "internal.corp" in config.bypass_domains

    def test_wildcard_match(self):
        config = ProxyConfig(bypass_domains=["*.example.com"])
        assert config.should_bypass("https://jira.example.com/api")
        assert config.should_bypass("https://anything.example.com/")
        assert config.should_bypass("https://sub.team.example.com/")

    def test_exact_match(self):
        config = ProxyConfig(bypass_domains=["confluence.example.com"])
        assert config.should_bypass("https://confluence.example.com/page")
        assert not config.should_bypass("https://other.example.com/")

    def test_no_match(self):
        config = ProxyConfig(bypass_domains=["*.example.com"])
        assert not config.should_bypass("https://api.anthropic.com/v1/messages")
        assert not config.should_bypass("https://github.com/")

    def test_env_dict_clears_proxy(self):
        config = ProxyConfig(bypass_domains=["*.example.com"])
        env = config.get_env_dict()
        assert env["HTTP_PROXY"] == ""
        assert env["HTTPS_PROXY"] == ""
        assert "*.example.com" in env["NO_PROXY"]

    def test_env_dict_empty_no_proxy_when_no_bypass(self):
        config = ProxyConfig(bypass_domains=[])
        env = config.get_env_dict()
        assert env["NO_PROXY"] == ""


class TestJiraConfig:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_PERSONAL_TOKEN", "test-token")
        config = JiraConfig.from_env()
        assert config.url == "https://jira.example.com"
        assert config.personal_token == "test-token"

    def test_auth_dict_uses_token_for_pat(self):
        config = JiraConfig(url="https://example.com", personal_token="abc")
        assert config.get_auth_dict() == {"token": "abc"}

    def test_auth_dict_basic(self):
        config = JiraConfig(url="https://example.com", username="user", token="pass")
        assert config.get_auth_dict() == {"username": "user", "password": "pass"}

    def test_auth_dict_empty(self):
        config = JiraConfig(url="https://example.com")
        assert config.get_auth_dict() == {}


class TestConfluenceConfig:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("CONFLUENCE_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_PERSONAL_TOKEN", "test-token")
        config = ConfluenceConfig.from_env()
        assert config.url == "https://confluence.example.com"
        assert config.personal_token == "test-token"

    def test_auth_dict_uses_token_for_pat(self):
        config = ConfluenceConfig(url="https://example.com", personal_token="abc")
        assert config.get_auth_dict() == {"token": "abc"}

    def test_auth_dict_basic(self):
        config = ConfluenceConfig(
            url="https://example.com", username="user", token="pass"
        )
        assert config.get_auth_dict() == {"username": "user", "password": "pass"}
