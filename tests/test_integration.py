"""Integration tests for the Jira LangChain system."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from parser import TextParser


class TestIntegration:
    """Integration test cases."""

    def test_sample_file_parsing(self):
        """Test parsing the sample tickets file."""
        # Create a sample file for testing
        sample_content = """
epic:

Epic 1: Test Epic
Epic Name: TEST-EPIC - Test Epic Name
Description: This is a test epic description for integration testing
Business Outcome: Validate the parsing and integration workflow
Priority: High

Epic 1: Test Epic - User Stories
Story 1: Integration Test Story
Story Key: TEST-1
Priority: Medium
As a developer I want to test the integration So that I can ensure the system works end-to-end
Acceptance Criteria:
* Parser correctly extracts epic information
* Parser correctly extracts story information
* All data types are properly converted
"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(sample_content)
            temp_file = f.name

        try:
            # Test parsing
            parser = TextParser()
            issues = parser.parse_file(temp_file)

            # Verify results
            assert len(issues) == 2

            # Check epic
            epic = issues[0]
            assert epic.title == "TEST-EPIC - Test Epic Name"
            assert "integration testing" in epic.description
            assert (
                epic.business_outcome == "Validate the parsing and integration workflow"
            )

            # Check story
            story = issues[1]
            assert story.title == "Integration Test Story"
            assert story.story_key == "TEST-1"
            assert len(story.acceptance_criteria) == 3

        finally:
            # Clean up
            os.unlink(temp_file)

    def test_main_module_imports(self):
        """Test that main modules can be imported successfully."""
        # Test parser import
        from parser import IssueType, Priority, TextParser

        # Test that classes can be instantiated
        parser = TextParser()
        assert parser is not None

        # Test enum values
        assert IssueType.EPIC == "Epic"
        assert Priority.HIGH == "High"

    @patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://test.atlassian.net",
            "JIRA_USERNAME": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEY": "TEST",
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "test-key",
        },
    )
    def test_jira_integration_initialization(self):
        """Test JiraIntegration initialization with mocked environment."""
        # Mock the LangChain components to avoid actual API calls
        with (
            patch("jira_integration.JiraAction") as mock_jira_action,
            patch("jira_integration.ChatAnthropic") as mock_chat_anthropic,
        ):

            # Configure mocks
            mock_jira_action.return_value = MagicMock()
            mock_chat_anthropic.return_value = MagicMock()

            # Test import and initialization
            from jira_integration import JiraIntegration

            # This should not raise an exception
            jira_integration = JiraIntegration()
            assert jira_integration is not None
            assert jira_integration.jira_url == "https://test.atlassian.net"
            assert jira_integration.project_key == "TEST"
