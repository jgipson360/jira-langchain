"""Tests for the text parser module."""

from parser import AcceptanceCriteria, IssueType, JiraIssue, Priority, TextParser


class TestTextParser:
    """Test cases for the TextParser class."""

    def test_parse_epic(self):
        """Test parsing a simple epic."""
        sample_text = """
epic:

Epic 1: Test Epic
Epic Name: TEST-EPIC - Test Epic Name
Description: This is a test epic description
Business Outcome: Test business outcome
Priority: High
"""
        parser = TextParser()
        issues = parser.parse_text(sample_text)

        assert len(issues) == 1
        epic = issues[0]
        assert epic.issue_type == IssueType.EPIC
        assert epic.title == "TEST-EPIC - Test Epic Name"
        assert "test epic description" in epic.description.lower()
        assert epic.business_outcome == "Test business outcome"
        assert epic.priority == Priority.HIGH

    def test_parse_story(self):
        """Test parsing a user story."""
        sample_text = """
Epic 1: Test Epic - User Stories
Story 1: Test Story
Story Key: TEST-1
Priority: Medium
As a user I want to test the system So that I can verify it works
Acceptance Criteria:
* Test criterion 1
* Test criterion 2
"""
        parser = TextParser(enable_llm_fallback=False)
        issues = parser.parse_text(sample_text)

        # Should parse both the epic and the story
        assert len(issues) == 2

        # Find the story
        story = None
        epic = None
        for issue in issues:
            if issue.issue_type == IssueType.STORY and issue.title == "Test Story":
                story = issue
            elif issue.issue_type == IssueType.EPIC:
                epic = issue

        assert story is not None, "Story not found"
        assert epic is not None, "Epic not found"

        # Test story properties
        assert story.title == "Test Story"
        assert story.story_key == "TEST-1"
        assert len(story.acceptance_criteria) == 2
        assert story.acceptance_criteria[0].description == "Test criterion 1"
        assert (
            story.description
            == "As a user I want to test the system So that I can verify it works"
        )

    def test_parse_multiple_issues(self):
        """Test parsing multiple issues."""
        sample_text = """
epic:

Epic 1: Test Epic
Epic Name: TEST-EPIC - Test Epic Name
Description: This is a test epic description
Business Outcome: Test business outcome
Priority: High

Epic 1: Test Epic - User Stories
Story 1: Test Story
Story Key: TEST-1
Priority: Medium
As a user I want to test the system So that I can verify it works
Acceptance Criteria:
* Test criterion 1
* Test criterion 2
"""
        parser = TextParser(enable_llm_fallback=False)
        issues = parser.parse_text(sample_text)

        assert len(issues) == 3

        # Find the issues
        epics = [issue for issue in issues if issue.issue_type == IssueType.EPIC]
        stories = [issue for issue in issues if issue.issue_type == IssueType.STORY]

        assert len(epics) == 2
        assert len(stories) == 1

        # Check the main epic
        main_epic = next(
            (epic for epic in epics if epic.epic_name == "TEST-EPIC - Test Epic Name"),
            None,
        )
        assert main_epic is not None
        assert main_epic.title == "TEST-EPIC - Test Epic Name"
        assert main_epic.description == "This is a test epic description"

        # Check the story
        story = stories[0]
        assert story.title == "Test Story"
        assert story.story_key == "TEST-1"
        assert len(story.acceptance_criteria) == 2

    def test_parse_empty_text(self):
        """Test parsing empty text."""
        parser = TextParser()
        issues = parser.parse_text("")

        assert len(issues) == 0

    def test_priority_parsing(self):
        """Test priority parsing."""
        parser = TextParser()

        # Test various priority formats
        assert parser._parse_priority("Highest") == Priority.HIGHEST
        assert parser._parse_priority("highest") == Priority.HIGHEST
        assert parser._parse_priority("High") == Priority.HIGH
        assert parser._parse_priority("Medium") == Priority.MEDIUM
        assert parser._parse_priority("Low") == Priority.LOW
        assert parser._parse_priority("Lowest") == Priority.LOWEST
        assert parser._parse_priority("Invalid") == Priority.MEDIUM


class TestJiraIssue:
    """Test cases for the JiraIssue class."""

    def test_jira_issue_creation(self):
        """Test creating a JiraIssue."""
        issue = JiraIssue(
            title="Test Issue",
            description="Test description",
            issue_type=IssueType.STORY,
            priority=Priority.HIGH,
        )

        assert issue.title == "Test Issue"
        assert issue.description == "Test description"
        assert issue.issue_type == IssueType.STORY
        assert issue.priority == Priority.HIGH
        assert issue.acceptance_criteria == []

    def test_jira_issue_with_acceptance_criteria(self):
        """Test creating a JiraIssue with acceptance criteria."""
        criteria = [
            AcceptanceCriteria("Criterion 1"),
            AcceptanceCriteria("Criterion 2"),
        ]

        issue = JiraIssue(
            title="Test Issue",
            description="Test description",
            issue_type=IssueType.STORY,
            acceptance_criteria=criteria,
        )

        assert len(issue.acceptance_criteria) == 2
        assert issue.acceptance_criteria[0].description == "Criterion 1"
        assert issue.acceptance_criteria[1].description == "Criterion 2"


class TestAcceptanceCriteria:
    """Test cases for the AcceptanceCriteria class."""

    def test_acceptance_criteria_creation(self):
        """Test creating an AcceptanceCriteria."""
        criteria = AcceptanceCriteria("Test criterion")

        assert criteria.description == "Test criterion"
