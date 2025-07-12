import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.jira.tool import JiraAction
from langchain_google_genai import ChatGoogleGenerativeAI

from parser import IssueType, JiraIssue

# Load environment variables
load_dotenv()


class JiraIntegration:
    """Integration with Jira using LangChain tools."""

    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL")
        self.jira_username = os.getenv("JIRA_USERNAME")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY")

        if not all(
            [self.jira_url, self.jira_username, self.jira_api_token, self.project_key]
        ):
            raise ValueError(
                "Missing required Jira configuration. " "Please check your .env file."
            )  # Set the environment variables that JiraAction expects
        os.environ["JIRA_INSTANCE_URL"] = self.jira_url
        os.environ["JIRA_CLOUD"] = "true"  # Indicate this is a cloud instance

        # Initialize Jira action for creating issues
        self.jira_action = JiraAction(
            jira_username=self.jira_username,
            jira_api_token=self.jira_api_token,
            jira_instance_url=self.jira_url,
            mode="create_issue",
        )

        # Initialize separate Jira action for getting project info
        self.jira_project_action = JiraAction(
            jira_username=self.jira_username,
            jira_api_token=self.jira_api_token,
            jira_instance_url=self.jira_url,
            mode="get_projects",
        )

        # Initialize LLM
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the LLM based on the provider setting."""
        provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

        if provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            return ChatAnthropic(
                model="claude-3-5-sonnet-20240620", anthropic_api_key=api_key
            )
        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            return ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def create_issue(self, issue: JiraIssue, epic_link: str = None) -> Dict[str, Any]:
        """Create a single Jira issue."""
        # Prepare the issue data
        issue_data = {
            "summary": issue.title,
            "description": self._format_description(issue),
            "project": {"key": self.project_key},
        }

        # Handle issue type - only Epic and Story are valid for this project
        if issue.issue_type == IssueType.EPIC:
            issue_data["issuetype"] = {"name": "Epic"}
            # Don't use customfield_10011 since it's not available in this project
            # The epic name will be included in the description instead
        else:
            # Convert all other types to Story since only Epic/Story are supported
            issue_data["issuetype"] = {"name": "Story"}

        # Add priority for stories (now that you've added the field)
        try:
            issue_data["priority"] = {"name": issue.priority.value}
        except Exception as e:
            print(f"⚠️  Could not set priority: {e}")

        # Add labels if they exist
        if issue.labels:
            # Parse labels from string (comma or space separated)
            labels_list = self._parse_labels(issue.labels)
            if labels_list:
                issue_data["labels"] = labels_list
                print(f"🏷️  Adding labels: {labels_list}")

        # Add epic link for stories
        if epic_link and issue.issue_type == IssueType.STORY:
            try:
                # Use the discovered Epic Link field
                epic_link_field = self._get_epic_link_field()

                if epic_link_field == "parent":
                    # Parent field expects a dict with key
                    issue_data[epic_link_field] = {"key": epic_link}
                else:
                    # Custom fields usually just take the key as string
                    issue_data[epic_link_field] = epic_link

                print(
                    f"🔗 Setting epic link using field {epic_link_field}: {epic_link}"
                )
            except Exception as e:
                print(f"⚠️  Could not set epic link: {e}")
                # Try some common fallbacks
                common_fields = ["parent", "customfield_10014", "customfield_10008"]
                for field in common_fields:
                    try:
                        if field == "parent":
                            issue_data[field] = {"key": epic_link}
                        else:
                            issue_data[field] = epic_link
                        print(
                            f"🔗 Epic link set using fallback field {field}: {epic_link}"
                        )
                        break
                    except Exception:
                        continue

        # Create the issue using Jira action
        fields_json = json.dumps(issue_data)

        try:
            result = self.jira_action.run(fields_json)
            print(f"✅ Issue created successfully: {issue.title}")
            print(f"Raw Jira response type: {type(result)}")
            print(f"Raw Jira response: {result}")

            # Return a consistent format
            if isinstance(result, str):
                # If it's a string, try to parse it or return a dict format
                return {"status": "created", "message": result}
            else:
                return result
        except Exception as e:
            print(f"Error creating issue: {e}")
            print(f"Issue data: {json.dumps(issue_data, indent=2)}")
            # Re-raise the exception to be caught by the caller
            raise

    def create_issues_batch(self, issues: List[JiraIssue]) -> List[Dict[str, Any]]:
        """Create multiple Jira issues."""
        results = []

        # Discover existing epics dynamically
        print("🔍 Discovering existing epics...")
        epic_mappings = self._discover_epic_mappings()

        if not epic_mappings:
            print("⚠️  No existing epics found or discovery failed")
        else:
            print(f"✅ Found {len(epic_mappings)} existing epics")

        # Store all created issues for dependency resolution
        all_issue_mappings = epic_mappings.copy()

        # Separate epics and stories
        epics = [issue for issue in issues if issue.issue_type == IssueType.EPIC]
        stories = [issue for issue in issues if issue.issue_type == IssueType.STORY]

        # Find all parent references in stories to identify missing epics
        story_parents = {issue.parent for issue in stories if issue.parent}

        # Create missing epics automatically
        for parent in story_parents:
            if parent not in epic_mappings:
                # Check if this epic is already in our epics list
                existing_epic = next(
                    (
                        epic
                        for epic in epics
                        if epic.epic_name and epic.epic_name.startswith(parent)
                    ),
                    None,
                )
                if not existing_epic:
                    print(f"🔄 Creating placeholder epic for parent: {parent}")
                    # Create a placeholder epic for this parent
                    from parser import Priority

                    placeholder_epic = JiraIssue(
                        title=f"{parent} - Epic",
                        description=f"Epic for {parent} related stories",
                        issue_type=IssueType.EPIC,
                        priority=Priority.MEDIUM,
                        epic_name=f"{parent} - Epic",
                    )
                    epics.append(placeholder_epic)

        # Create epics first and update mappings
        for issue in epics:
            result = self.create_issue(issue)
            results.append(result)
            # Extract the key and add to mappings
            issue_key = self._extract_issue_key(result)
            if issue_key:
                # Add to all_issue_mappings for dependency resolution
                all_issue_mappings[issue_key] = issue_key

                if issue.epic_name:
                    # Extract the prefix from epic name (e.g., "PREP" from "PREP - Emergency...")
                    epic_prefix = (
                        issue.epic_name.split(" - ")[0]
                        if " - " in issue.epic_name
                        else issue.epic_name.split()[0]  # fallback to first word
                    )
                    epic_mappings[epic_prefix] = issue_key
                    all_issue_mappings[epic_prefix] = issue_key
                    print(f"🔗 Epic mapping updated: {epic_prefix} -> {issue_key}")

        # Create stories and link them to epics
        for issue in stories:
            epic_link = None
            if issue.parent and issue.parent in epic_mappings:
                epic_link = epic_mappings[issue.parent]
                print(f"🔗 Linking story '{issue.title}' to epic {epic_link}")
            elif issue.parent:
                print(
                    f"⚠️  Epic '{issue.parent}' not found in mappings: {list(epic_mappings.keys())}"
                )

            result = self.create_issue(issue, epic_link=epic_link)
            results.append(result)

            # Add story to all_issue_mappings for dependency resolution
            issue_key = self._extract_issue_key(result)
            if issue_key:
                all_issue_mappings[issue_key] = issue_key
                # Also add by title for easier lookup
                all_issue_mappings[issue.title] = issue_key

            # Create dependency links if this issue has dependencies
            if issue.dependencies and issue_key:
                dependencies = self._parse_dependencies(issue.dependencies)
                resolved_deps = self._resolve_dependency_keys(
                    dependencies, all_issue_mappings
                )
                if resolved_deps:
                    self._create_issue_links(issue_key, resolved_deps)

        return results

    def _extract_issue_key(self, result) -> str:
        """Extract issue key from Jira API response."""
        if isinstance(result, dict):
            return result.get("key")
        elif isinstance(result, str):
            # Try to extract key from string response
            import re

            match = re.search(r"(GMLT-\d+)", result)
            return match.group(1) if match else None
        return None

    def _parse_labels(self, labels_string: str) -> List[str]:
        """Parse labels from string into a list of valid Jira labels."""
        if not labels_string:
            return []

        # Split by common separators and clean up
        import re

        # If there are commas, split by comma (most common case)
        if "," in labels_string:
            labels = [label.strip() for label in labels_string.split(",")]
        else:
            # For space-separated labels, be smarter about multi-word labels
            # Split by spaces but treat hyphenated words as single labels
            labels = re.split(r"\s+", labels_string.strip())

        # Clean up labels: remove empty strings, convert to valid format
        valid_labels = []
        for label in labels:
            label = label.strip()
            if label:
                # Jira labels cannot contain spaces, but can contain hyphens and underscores
                # Replace spaces with hyphens and remove other invalid chars
                clean_label = re.sub(r"\s+", "-", label)  # Replace spaces with hyphens
                clean_label = re.sub(
                    r"[^\w-]", "", clean_label
                )  # Keep only word chars and hyphens
                clean_label = re.sub(r"-+", "-", clean_label)  # Remove multiple hyphens
                clean_label = clean_label.strip("-")  # Remove leading/trailing hyphens
                if clean_label:
                    valid_labels.append(clean_label)

        return valid_labels

    def _format_description(self, issue: JiraIssue) -> str:
        """Format the description for Jira, including acceptance criteria."""
        description_parts = []

        # Add Epic Name prominently at the top for Epic issues
        if issue.issue_type == IssueType.EPIC and issue.epic_name:
            description_parts.append(f"**Epic Name:** {issue.epic_name}")
            description_parts.append("")  # Empty line for spacing

        # Add main description
        description_parts.append(issue.description)

        if issue.business_outcome:
            description_parts.append(
                f"\n**Business Outcome:** {issue.business_outcome}"
            )

        if issue.acceptance_criteria:
            description_parts.append("\n**Acceptance Criteria:**")
            for i, criteria in enumerate(issue.acceptance_criteria, 1):
                description_parts.append(f"{i}. {criteria.description}")

        return "\n".join(description_parts)

    def enhance_with_llm(self, issue: JiraIssue) -> JiraIssue:
        """Use LLM to enhance the issue description and details."""
        system_message = SystemMessage(
            content="""
        You are an expert at writing Jira tickets. Given a basic issue description,
        enhance it with:
        1. Clear, actionable acceptance criteria
        2. Improved description with technical details
        3. Better formatting for Jira

        Keep the original intent but make it more professional and detailed.
        """
        )

        human_message = HumanMessage(
            content=f"""
        Please enhance this Jira {issue.issue_type.value}:

        Title: {issue.title}
        Description: {issue.description}

        Current Acceptance Criteria:
        {[criteria.description for criteria in issue.acceptance_criteria]}

        Please provide an enhanced version with better formatting and
        more detailed acceptance criteria.
        """
        )

        try:
            response = self.llm.invoke([system_message, human_message])

            # Parse the LLM response and use it to enhance the description
            enhanced_description = (
                f"{issue.description}\n\n--- AI Enhanced ---\n{response.content}"
            )

            return JiraIssue(
                title=issue.title,
                description=enhanced_description,
                issue_type=issue.issue_type,
                priority=issue.priority,
                story_key=issue.story_key,
                acceptance_criteria=issue.acceptance_criteria,
                business_outcome=issue.business_outcome,
                epic_name=issue.epic_name,
            )
        except Exception as e:
            print(f"Warning: Could not enhance issue with LLM: {e}")
            return issue

    def get_project_info(self) -> Dict[str, Any]:
        """Get information about the Jira project."""
        return self.jira_project_action.run(self.project_key)

    def list_issue_types(self) -> List[Dict[str, Any]]:
        """List available issue types in the project."""
        instruction = "List all available issue types in the project"
        return self.jira_action.run(instruction)

    def _get_epic_link_field(self) -> str:
        """Discover the Epic Link field for this Jira project."""
        if hasattr(self, "_epic_link_field"):
            return self._epic_link_field

        try:
            # Initialize a Jira action for getting field info
            field_action = JiraAction(
                jira_username=self.jira_username,
                jira_api_token=self.jira_api_token,
                jira_instance_url=self.jira_url,
                mode="get_projects",
            )

            # Get project metadata to find epic link field
            project_info = field_action.run(self.project_key)
            print(f"🔍 Project info type: {type(project_info)}")
            print(f"🔍 Project info: {project_info}")

            # Try to discover the Epic Link field from project metadata
            discovered_field = self._get_project_fields()
            if discovered_field and isinstance(discovered_field, str):
                self._epic_link_field = discovered_field
            else:
                # Fall back to most common field
                self._epic_link_field = "customfield_10014"

            print(f"🔗 Using Epic Link field: {self._epic_link_field}")
            return self._epic_link_field

        except Exception as e:
            print(f"⚠️  Could not determine Epic Link field: {e}")
            # Fall back to most common field
            self._epic_link_field = "customfield_10014"
            return self._epic_link_field

    def _get_project_fields(self) -> Dict[str, Any]:
        """Get all available fields for this Jira project."""
        try:
            # Use the Jira REST API directly to get field information
            import base64

            import requests

            # Prepare authentication
            auth_string = f"{self.jira_username}:{self.jira_api_token}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
            }

            # Get project create metadata to find available fields
            url = f"{self.jira_url}/rest/api/2/issue/createmeta"
            params = {
                "projectKeys": self.project_key,
                "expand": "projects.issuetypes.fields",
            }

            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                metadata = response.json()
                print("🔍 Create metadata retrieved successfully")

                # Look for Epic Link field in the metadata
                for project in metadata.get("projects", []):
                    if project.get("key") == self.project_key:
                        for issue_type in project.get("issuetypes", []):
                            if issue_type.get("name") == "Story":
                                fields = issue_type.get("fields", {})

                                # Check for Epic Link field by name
                                for field_id, field_info in fields.items():
                                    field_name = field_info.get("name", "").lower()
                                    if "epic" in field_name and "link" in field_name:
                                        print(
                                            f"🔗 Found Epic Link field: {field_id} ({field_info.get('name')})"
                                        )
                                        return field_id

                                # Check for Parent field (which might be used for Epic links)
                                if "parent" in fields:
                                    parent_field = fields["parent"]
                                    parent_name = parent_field.get("name", "")
                                    print(
                                        f"🔗 Found Parent field: parent ({parent_name})"
                                    )
                                    # In some Jira setups, Parent field is used for Epic links
                                    return "parent"

                                # Check for custom fields that might be Epic Link
                                for field_id, field_info in fields.items():
                                    if field_id.startswith("customfield_"):
                                        field_name = field_info.get("name", "").lower()
                                        if "epic" in field_name:
                                            print(
                                                f"🔗 Found Epic-related field: {field_id} ({field_info.get('name')})"
                                            )
                                            return field_id

                return metadata
            else:
                print(f"⚠️  Failed to get create metadata: {response.status_code}")
                return None

        except Exception as e:
            print(f"⚠️  Error getting project fields: {e}")
            return None

    def _parse_dependencies(self, dependencies_string: str) -> List[str]:
        """Parse dependencies string to extract individual dependency references."""
        if not dependencies_string:
            return []

        # Dependencies can be in format: [PREP] Emergency Bed Bug Supply Purchase, [MSTR] Another Task
        # Or: PREP-123, MSTR-456
        # Or: Emergency Bed Bug Supply Purchase, Another Task

        dependencies = []

        # Split by comma first
        parts = [part.strip() for part in dependencies_string.split(",")]

        for part in parts:
            if not part:
                continue

            # Check if it's already a Jira key (e.g., GMLT-123)
            if re.match(r"^[A-Z]+-\d+$", part):
                dependencies.append(part)
            else:
                # Extract reference from format like "[PREP] Emergency Bed Bug Supply Purchase"
                # We'll store the full text for now and resolve it later
                dependencies.append(part.strip())

        return dependencies

    def _resolve_dependency_keys(
        self, dependencies: List[str], issue_mappings: Dict[str, str]
    ) -> List[str]:
        """Resolve dependency references to actual Jira issue keys."""
        resolved_keys = []

        for dep in dependencies:
            # If it's already a Jira key, use it directly
            if re.match(r"^[A-Z]+-\d+$", dep):
                resolved_keys.append(dep)
                continue

            # Skip dependencies that are obviously not issue references
            if dep.lower().startswith("none"):
                continue

            # Try to match against our issue mappings
            # Look for patterns like "[PREP] Emergency Bed Bug Supply Purchase"
            bracket_match = re.match(r"^\[([A-Z]+)\]\s*(.+)", dep)
            if bracket_match:
                epic_prefix = bracket_match.group(1)
                task_name = bracket_match.group(2).strip()

                # First, try to find an exact match by task name
                if task_name in issue_mappings:
                    resolved_keys.append(issue_mappings[task_name])
                    print(
                        f"🔗 Resolved dependency '{dep}' to specific story {issue_mappings[task_name]}"
                    )
                    continue

                # If no exact match, try to find by epic prefix and partial title match
                for title, key in issue_mappings.items():
                    if (
                        title.startswith(f"[{epic_prefix}]")
                        and task_name.lower() in title.lower()
                    ):
                        resolved_keys.append(key)
                        print(
                            f"🔗 Resolved dependency '{dep}' to story {key} (partial match)"
                        )
                        break
                else:
                    # If no specific story found, fall back to epic
                    if epic_prefix in issue_mappings:
                        epic_key = issue_mappings[epic_prefix]
                        resolved_keys.append(epic_key)
                        print(
                            f"🔗 Resolved dependency '{dep}' to epic {epic_key} (fallback)"
                        )
                    else:
                        print(f"⚠️  Could not resolve dependency: {dep}")
            else:
                # Try direct lookup by title
                if dep in issue_mappings:
                    resolved_keys.append(issue_mappings[dep])
                    print(f"🔗 Resolved dependency '{dep}' to {issue_mappings[dep]}")
                else:
                    print(f"⚠️  Could not parse dependency format: {dep}")

        return resolved_keys

    def _create_issue_links(self, issue_key: str, dependency_keys: List[str]):
        """Create issue links for dependencies (blocked by relationships)."""
        if not dependency_keys:
            return

        try:
            # Use direct Jira API to create issue links
            import base64

            import requests

            # Prepare authentication
            auth_string = f"{self.jira_username}:{self.jira_api_token}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
            }

            # Create issue links for each dependency
            for dep_key in dependency_keys:
                # Create a "Blocks" link (dependency blocks this issue)
                link_data = {
                    "type": {
                        "name": "Blocks"  # Common link type meaning dep_key blocks issue_key
                    },
                    "inwardIssue": {"key": issue_key},  # This issue is blocked by
                    "outwardIssue": {
                        "key": dep_key  # This dependency blocks the issue
                    },
                }

                url = f"{self.jira_url}/rest/api/2/issueLink"
                response = requests.post(url, headers=headers, json=link_data)

                if response.status_code in [200, 201]:
                    print(f"🔗 Created dependency link: {dep_key} blocks {issue_key}")
                else:
                    print(
                        f"⚠️  Failed to create dependency link: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            print(f"⚠️  Error creating issue links: {e}")

    def _discover_epic_mappings(self) -> Dict[str, str]:
        """Discover existing epics in the project and create mappings."""
        try:
            # Use direct Jira API to search for epics
            import base64

            import requests

            # Prepare authentication
            auth_string = f"{self.jira_username}:{self.jira_api_token}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
            }

            # Search for epics in the project
            url = f"{self.jira_url}/rest/api/2/search"
            params = {
                "jql": f"project = {self.project_key} AND issuetype = Epic",
                "fields": "key,summary,description",
                "maxResults": 100,
            }

            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                epics = data.get("issues", [])

                epic_mappings = {}
                print(f"🔍 Discovered {len(epics)} epics in project {self.project_key}")

                for epic in epics:
                    key = epic.get("key")
                    summary = epic.get("fields", {}).get("summary", "")

                    # Extract epic prefix from summary
                    # Look for patterns like "PREP - Title" or "[PREP] Title" or "KITCH - Title"
                    epic_prefix = None

                    # Pattern 1: [PREFIX] Title
                    bracket_match = re.match(r"^\[([A-Z]+)\]", summary)
                    if bracket_match:
                        epic_prefix = bracket_match.group(1)

                    # Pattern 2: PREFIX - Title
                    elif " - " in summary:
                        potential_prefix = summary.split(" - ")[0].strip()
                        if potential_prefix.isupper() and len(potential_prefix) <= 10:
                            epic_prefix = potential_prefix

                    # Pattern 3: PREFIX Title (no separator)
                    else:
                        words = summary.split()
                        if words and words[0].isupper() and len(words[0]) <= 10:
                            epic_prefix = words[0]

                    if epic_prefix:
                        epic_mappings[epic_prefix] = key
                        print(f"🔗 Mapped epic: {epic_prefix} -> {key} ({summary})")
                    else:
                        print(
                            f"⚠️  Could not extract prefix from epic: {key} ({summary})"
                        )

                return epic_mappings
            else:
                print(f"⚠️  Failed to search for epics: {response.status_code}")
                return {}

        except Exception as e:
            print(f"⚠️  Error discovering epic mappings: {e}")
            return {}
