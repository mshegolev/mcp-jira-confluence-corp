#!/bin/bash
# Push mcp-jira-confluence to GitHub

# Set your GitHub username here
GITHUB_USERNAME="${GITHUB_USERNAME:-mshegolev}"

# Repository name
REPO_NAME="mcp-jira-confluence"

# Repository URL
REPO_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo "🚀 Pushing to GitHub..."
echo "Target: ${REPO_URL}"
echo ""

# Add remote
git remote add origin "${REPO_URL}"

# Push to main branch
git branch -M main
git push -u origin main

echo ""
echo "✅ Successfully pushed to ${REPO_URL}"
echo ""
echo "Next steps:"
echo "1. Add to your .mcp.json:"
echo "   \"jira-confluence\": {"
echo "     \"type\": \"stdio\","
echo "     \"command\": \"uvx\","
echo "     \"args\": ["
echo "       \"--from\",\"mcp-jira-confluence @ git+${REPO_URL}\","
echo "       \"mcp-jira-confluence\""
echo "     ],"
echo "     \"env\": {"
echo "       \"JIRA_URL\": \"https://jira.mts.ru\","
echo "       \"JIRA_PERSONAL_TOKEN\": \"...\","
echo "       \"CONFLUENCE_URL\": \"https://confluence.mts.ru\","
echo "       \"CONFLUENCE_PERSONAL_TOKEN\": \"...\","
echo "       \"HTTP_PROXY\": \"\","
echo "       \"HTTPS_PROXY\": \"\""
echo "     }"
echo "   }"
