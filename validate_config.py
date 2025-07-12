#!/usr/bin/env python3
"""
Configuration validator for Jira LangChain integration
"""

import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv


class ConfigValidator:
    """Validates configuration for Jira LangChain integration."""

    def __init__(self, config_file: str = ".env"):
        self.config_file = config_file
        self.errors = []
        self.warnings = []

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Validate configuration and return success status with errors/warnings."""

        # Check if config file exists
        if not Path(self.config_file).exists():
            self.errors.append(f"Configuration file '{self.config_file}' not found")
            return False, self.errors, self.warnings

        # Load environment variables
        load_dotenv(self.config_file)

        # Validate Jira configuration
        self._validate_jira_config()

        # Validate LLM configuration
        self._validate_llm_config()

        # Check for optional configurations
        self._check_optional_config()

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_jira_config(self):
        """Validate Jira-specific configuration."""

        # Required Jira fields
        required_fields = {
            "JIRA_URL": "Jira instance URL",
            "JIRA_USERNAME": "Jira username/email",
            "JIRA_API_TOKEN": "Jira API token",
            "JIRA_PROJECT_KEY": "Jira project key",
        }

        for field, description in required_fields.items():
            value = os.getenv(field)
            if not value:
                self.errors.append(f"Missing required field: {field} ({description})")
            elif field == "JIRA_URL":
                self._validate_url(value, field)
            elif field == "JIRA_PROJECT_KEY":
                self._validate_project_key(value)

    def _validate_llm_config(self):
        """Validate LLM-specific configuration."""

        provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

        if provider not in ["anthropic", "google"]:
            self.errors.append(
                f"Invalid LLM_PROVIDER: {provider}. Must be 'anthropic' or 'google'"
            )
            return

        # Check for appropriate API key
        if provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                self.errors.append(
                    "ANTHROPIC_API_KEY required when LLM_PROVIDER is 'anthropic'"
                )
            elif not api_key.startswith("sk-"):
                self.warnings.append("ANTHROPIC_API_KEY should start with 'sk-'")

        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.errors.append(
                    "GOOGLE_API_KEY required when LLM_PROVIDER is 'google'"
                )
            elif len(api_key) < 20:
                self.warnings.append("GOOGLE_API_KEY seems too short")

    def _validate_url(self, url: str, field_name: str):
        """Validate URL format."""
        if not url.startswith(("http://", "https://")):
            self.errors.append(f"{field_name} must start with http:// or https://")

        if not url.endswith(".atlassian.net") and "atlassian" not in url:
            self.warnings.append(f"{field_name} doesn't look like an Atlassian URL")

    def _validate_project_key(self, project_key: str):
        """Validate Jira project key format."""
        if not project_key.isupper():
            self.warnings.append("JIRA_PROJECT_KEY should typically be uppercase")

        if len(project_key) < 2 or len(project_key) > 10:
            self.warnings.append("JIRA_PROJECT_KEY should be 2-10 characters long")

        if not project_key.isalnum() and "-" not in project_key:
            self.warnings.append(
                "JIRA_PROJECT_KEY should contain only letters, numbers, and hyphens"
            )

    def _check_optional_config(self):
        """Check optional configuration settings."""

        # Check issue types
        default_types = {
            "DEFAULT_EPIC_TYPE": "Epic",
            "DEFAULT_STORY_TYPE": "Story",
            "DEFAULT_TASK_TYPE": "Task",
        }

        for field, default_value in default_types.items():
            value = os.getenv(field)
            if value and value != default_value:
                self.warnings.append(
                    f"Non-standard {field}: '{value}' (default: '{default_value}')"
                )


def main():
    """Main validation function."""
    print("🔍 Validating Jira LangChain Configuration...")
    print("=" * 50)

    validator = ConfigValidator()
    success, errors, warnings = validator.validate()

    if errors:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"  • {error}")

    if warnings:
        print("\n⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  • {warning}")

    if success:
        print("\n✅ Configuration is valid!")
        print("\nYou can now run:")
        print("  python main.py -i sample_tickets.txt --dry-run")
    else:
        print(f"\n❌ Configuration validation failed with {len(errors)} errors")
        print("\nPlease fix the errors above and try again.")
        print("You can also run: python main.py setup")

        return 1

    return 0


if __name__ == "__main__":
    exit(main())
