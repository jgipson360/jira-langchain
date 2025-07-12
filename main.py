#!/usr/bin/env python3
"""
Automated Jira ticket creation using LangChain and Jira Toolkit.
Generates epics, stories, and tasks from text input.
"""

import sys
from typing import List

import click

from jira_integration import JiraIntegration
from parser import JiraIssue, TextParser


@click.command()
@click.option(
    "--input-file",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to the text file containing ticket descriptions",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Parse and display tickets without creating them in Jira",
)
@click.option(
    "--enhance", "-e", is_flag=True, help="Use LLM to enhance ticket descriptions"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to custom .env configuration file",
)
def main(input_file: str, dry_run: bool, enhance: bool, verbose: bool, config: str):
    """
    Create Jira tickets from text input using LangChain and Jira Toolkit.

    Example usage:
    python main.py -i tickets.txt
    python main.py -i tickets.txt --dry-run
    python main.py -i tickets.txt --enhance
    """

    if config:
        # Load custom config file
        from dotenv import load_dotenv

        load_dotenv(config)

    try:
        # Parse the input file
        if verbose:
            click.echo(f"Parsing input file: {input_file}")

        parser = TextParser()
        issues = parser.parse_file(input_file)

        if not issues:
            click.echo("No issues found in the input file.", err=True)
            sys.exit(1)

        if verbose:
            click.echo(f"Found {len(issues)} issues:")
            for i, issue in enumerate(issues, 1):
                click.echo(f"  {i}. {issue.issue_type.value}: {issue.title}")

        # Display parsed issues
        display_issues(issues)

        if dry_run:
            click.echo("\n🔍 Dry run mode - no tickets will be created in Jira")
            return

        # Initialize Jira integration
        if verbose:
            click.echo("\nInitializing Jira connection...")

        try:
            jira_integration = JiraIntegration()
        except ValueError as e:
            click.echo(f"❌ Configuration error: {e}", err=True)
            click.echo("Please check your .env file or use --config option")
            sys.exit(1)

        # Test connection
        try:
            project_info = jira_integration.get_project_info()
            if verbose:
                if isinstance(project_info, dict):
                    click.echo(
                        f"✅ Connected to project: {project_info.get('name', 'Unknown')}"
                    )
                else:
                    click.echo(f"✅ Connected to Jira: {project_info}")
        except Exception as e:
            click.echo(f"❌ Failed to connect to Jira: {e}", err=True)
            sys.exit(1)

        # Enhance with LLM if requested
        if enhance:
            if verbose:
                click.echo("\n🤖 Enhancing tickets with LLM...")

            enhanced_issues = []
            for issue in issues:
                try:
                    enhanced_issue = jira_integration.enhance_with_llm(issue)
                    enhanced_issues.append(enhanced_issue)
                    if verbose:
                        click.echo(f"  ✅ Enhanced: {issue.title}")
                except Exception as e:
                    click.echo(f"  ⚠️  Could not enhance '{issue.title}': {e}")
                    enhanced_issues.append(issue)

            issues = enhanced_issues

        # Create tickets
        if not click.confirm(f"\n🎫 Create {len(issues)} tickets in Jira?"):
            click.echo("Operation cancelled.")
            return

        if verbose:
            click.echo("\n📝 Creating tickets...")

        results = jira_integration.create_issues_batch(issues)

        # Display results
        click.echo("\n✅ Tickets created successfully:")
        for result in results:
            if isinstance(result, dict) and "key" in result:
                ticket_url = f"{jira_integration.jira_url}/browse/{result['key']}"
                click.echo(f"  • {result['key']}: {ticket_url}")
            else:
                click.echo(f"  • {result}")

        click.echo(f"\n🎉 Created {len(results)} tickets successfully!")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def display_issues(issues: List[JiraIssue]):
    """Display parsed issues in a formatted way."""
    click.echo("\n📋 Parsed Issues:")
    click.echo("=" * 50)

    for i, issue in enumerate(issues, 1):
        click.echo(f"\n{i}. {issue.issue_type.value}: {issue.title}")
        click.echo(f"   Priority: {issue.priority.value}")

        if issue.epic_name:
            click.echo(f"   Epic Name: {issue.epic_name}")

        if issue.parent:
            click.echo(f"   Parent Epic: {issue.parent}")

        if issue.story_key:
            click.echo(f"   Story Key: {issue.story_key}")

        if issue.dependencies:
            click.echo(f"   Dependencies: {issue.dependencies}")

        if issue.estimated_effort:
            click.echo(f"   Estimated Effort: {issue.estimated_effort}")

        if issue.labels:
            click.echo(f"   Labels: {issue.labels}")

        if issue.description:
            # Truncate long descriptions
            desc = (
                issue.description[:100] + "..."
                if len(issue.description) > 100
                else issue.description
            )
            click.echo(f"   Description: {desc}")

        if issue.business_outcome:
            outcome = (
                issue.business_outcome[:100] + "..."
                if len(issue.business_outcome) > 100
                else issue.business_outcome
            )
            click.echo(f"   Business Outcome: {outcome}")

        if issue.acceptance_criteria:
            click.echo(
                f"   Acceptance Criteria: {len(issue.acceptance_criteria)} items"
            )


@click.command()
@click.option("--url", prompt="Jira URL", help="Your Jira instance URL")
@click.option("--username", prompt="Username", help="Your Jira username/email")
@click.option(
    "--api-token", prompt="API Token", hide_input=True, help="Your Jira API token"
)
@click.option("--project-key", prompt="Project Key", help="Jira project key")
@click.option(
    "--llm-provider",
    type=click.Choice(["anthropic", "google"]),
    default="anthropic",
    help="LLM provider",
)
@click.option(
    "--llm-api-key", prompt="LLM API Key", hide_input=True, help="LLM API key"
)
def setup(
    url: str,
    username: str,
    api_token: str,
    project_key: str,
    llm_provider: str,
    llm_api_key: str,
):
    """Interactive setup to create .env configuration file."""

    env_content = f"""# Jira Configuration
JIRA_URL={url}
JIRA_USERNAME={username}
JIRA_API_TOKEN={api_token}
JIRA_PROJECT_KEY={project_key}

# Default Jira Issue Types
DEFAULT_EPIC_TYPE=Epic
DEFAULT_STORY_TYPE=Story
DEFAULT_TASK_TYPE=Task

# LLM Configuration
LLM_PROVIDER={llm_provider}
"""

    if llm_provider == "anthropic":
        env_content += f"ANTHROPIC_API_KEY={llm_api_key}\n"
    elif llm_provider == "google":
        env_content += f"GOOGLE_API_KEY={llm_api_key}\n"

    with open(".env", "w") as f:
        f.write(env_content)

    click.echo("✅ Configuration saved to .env file")
    click.echo("You can now run: python main.py -i your_tickets.txt")


if __name__ == "__main__":
    # Check if setup command is requested
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        main()
