#!/usr/bin/env python3
"""
Test script for Jira LangChain integration
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")

    try:
        import dotenv

        # Test that we can access the load_dotenv function
        _ = dotenv.load_dotenv
        print("  ✅ python-dotenv imported successfully")
    except ImportError as e:
        print(f"  ❌ python-dotenv import failed: {e}")
        return False

    try:
        from parser import JiraIssue, TextParser

        # Test that we can access the classes
        _ = JiraIssue
        _ = TextParser
        print("  ✅ parser module imported successfully")
    except ImportError as e:
        print(f"  ❌ parser module import failed: {e}")
        return False

    # Test LangChain imports (these might fail if not properly installed)
    try:
        from langchain_community.tools.jira.tool import JiraAction

        # Test that we can access the class
        _ = JiraAction
        print("  ✅ langchain-community imported successfully")
    except ImportError as e:
        print(f"  ⚠️  langchain-community import failed: {e}")
        print("     This is expected if not installed yet")

    try:
        from langchain_anthropic import ChatAnthropic

        # Test that we can access the class
        _ = ChatAnthropic
        print("  ✅ langchain-anthropic imported successfully")
    except ImportError as e:
        print(f"  ⚠️  langchain-anthropic import failed: {e}")
        print("     This is expected if not installed yet")

    return True


def test_parser():
    """Test the text parser with sample data."""
    print("\n🧪 Testing text parser...")

    try:
        from parser import TextParser

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

        parser = TextParser()
        issues = parser.parse_text(sample_text)

        print(f"  ✅ Parsed {len(issues)} issues")

        for i, issue in enumerate(issues):
            print(f"    {i+1}. {issue.issue_type.value}: {issue.title}")
            if issue.acceptance_criteria:
                print(
                    f"       Acceptance Criteria: {len(issue.acceptance_criteria)} items"
                )

        return True

    except Exception as e:
        print(f"  ❌ Parser test failed: {e}")
        return False


def test_config():
    """Test configuration setup."""
    print("\n🧪 Testing configuration...")

    env_example = Path(".env.example")
    if env_example.exists():
        print("  ✅ .env.example file exists")
    else:
        print("  ❌ .env.example file missing")
        return False

    env_file = Path(".env")
    if env_file.exists():
        print("  ✅ .env file exists")

        # Check if it has required fields
        with open(env_file, "r") as f:
            content = f.read()
            required_fields = [
                "JIRA_URL",
                "JIRA_USERNAME",
                "JIRA_API_TOKEN",
                "JIRA_PROJECT_KEY",
                "LLM_PROVIDER",
            ]

            missing_fields = []
            for field in required_fields:
                if field not in content:
                    missing_fields.append(field)

            if missing_fields:
                print(f"  ⚠️  Missing required fields in .env: {missing_fields}")
            else:
                print("  ✅ All required fields present in .env")
    else:
        print("  ⚠️  .env file doesn't exist - you'll need to create it")

    return True


def test_sample_file():
    """Test that sample file exists and can be parsed."""
    print("\n🧪 Testing sample file...")

    sample_file = Path("sample_tickets.txt")
    if sample_file.exists():
        print("  ✅ sample_tickets.txt exists")

        try:
            from parser import TextParser

            parser = TextParser()
            issues = parser.parse_file(str(sample_file))
            print(f"  ✅ Successfully parsed {len(issues)} issues from sample file")
            return True
        except Exception as e:
            print(f"  ❌ Failed to parse sample file: {e}")
            return False
    else:
        print("  ❌ sample_tickets.txt missing")
        return False


def main():
    """Run all tests."""
    print("🧪 Running Jira LangChain Test Suite")
    print("=" * 40)

    tests = [test_imports, test_parser, test_config, test_sample_file]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Test {test.__name__} failed with exception: {e}")
            failed += 1

    print("\n" + "=" * 40)
    print(f"🧪 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file with Jira and LLM credentials")
        print("2. Run: python main.py -i sample_tickets.txt --dry-run")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
