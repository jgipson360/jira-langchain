import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Priority(str, Enum):
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class IssueType(str, Enum):
    EPIC = "Epic"
    STORY = "Story"
    TASK = "Task"


@dataclass
class AcceptanceCriteria:
    description: str


@dataclass
class JiraIssue:
    title: str
    description: str
    issue_type: IssueType
    priority: Priority = Priority.MEDIUM
    story_key: Optional[str] = None
    acceptance_criteria: List[AcceptanceCriteria] = None
    business_outcome: Optional[str] = None
    epic_name: Optional[str] = None
    parent: Optional[str] = None
    dependencies: Optional[str] = None
    estimated_effort: Optional[str] = None
    labels: Optional[str] = None

    def __post_init__(self):
        if self.acceptance_criteria is None:
            self.acceptance_criteria = []


class TextParser:
    """Parser for text input containing Jira tickets in the specified format."""

    def __init__(self, enable_llm_fallback: bool = True):
        self.current_section = None
        self.current_issue = None
        self.issues = []
        self.enable_llm_fallback = enable_llm_fallback
        self.llm = None

        # Initialize LLM if fallback is enabled
        if self.enable_llm_fallback:
            self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the LLM for fallback parsing."""
        try:
            provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

            if provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    print("⚠️  ANTHROPIC_API_KEY not found - LLM fallback disabled")
                    return None
                return ChatAnthropic(
                    model="claude-3-5-sonnet-20240620", anthropic_api_key=api_key
                )
            elif provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI

                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    print("⚠️  GOOGLE_API_KEY not found - LLM fallback disabled")
                    return None
                return ChatGoogleGenerativeAI(
                    model="gemini-pro", google_api_key=api_key
                )
            else:
                print(
                    f"⚠️  Unsupported LLM provider: {provider} - LLM fallback disabled"
                )
                return None

        except ImportError as e:
            print(f"⚠️  LLM library not available: {e} - LLM fallback disabled")
            return None
        except Exception as e:
            print(f"⚠️  Could not initialize LLM: {e} - LLM fallback disabled")
            return None

    def parse_file(self, file_path: str) -> List[JiraIssue]:
        """Parse a text file and extract Jira issues."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse_text(content)

    def parse_text(self, text: str) -> List[JiraIssue]:
        """Parse text content and extract Jira issues."""
        self.issues = []
        lines = text.split("\n")

        # Detect format by looking for key patterns
        has_epic_pattern = any(re.match(r"^Epic \d+:", line.strip()) for line in lines)
        has_story_pattern = any(line.strip().startswith("Story: ") for line in lines)

        if has_epic_pattern:
            issues = self._parse_epic_format(lines)
        elif has_story_pattern:
            issues = self._parse_story_format(lines)
        else:
            # Try to parse as story format by default
            issues = self._parse_story_format(lines)

        # Check if we should use LLM fallback
        if self._should_use_llm_fallback(text, issues):
            print("🤖 Structured parsing incomplete - trying LLM fallback...")
            llm_issues = self._parse_with_llm(text)
            if llm_issues:
                print(f"✅ LLM fallback extracted {len(llm_issues)} issues")
                return llm_issues
            else:
                print("⚠️  LLM fallback failed - using structured parsing results")

        return issues

    def _parse_epic_format(self, lines: List[str]) -> List[JiraIssue]:
        """Parse the original epic format."""
        current_epic = None
        current_story = None
        current_description = []
        current_acceptance_criteria = []
        in_acceptance_criteria = False
        in_description = False
        in_business_outcome = False

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for Epic section (Epic 1:, Epic 2:, etc.)
            if re.match(r"^Epic \d+:", line):
                if current_epic:
                    self._finalize_epic(current_epic, current_description)
                current_epic = {}
                current_description = []
                in_description = False
                in_business_outcome = False

                # Extract epic title from "Epic 1: Title"
                epic_match = re.search(r"Epic \d+: (.+)", line)
                if epic_match:
                    current_epic["title"] = epic_match.group(1).strip()
                continue

            # Check for Epic Name
            if line.startswith("Epic Name:"):
                if current_epic is not None:
                    current_epic["epic_name"] = line.replace("Epic Name:", "").strip()
                continue

            # Check for Description section
            if line.startswith("Description:"):
                if current_epic is not None:
                    in_description = True
                    in_business_outcome = False
                    # Check if description is on the same line
                    desc_text = line.replace("Description:", "").strip()
                    if desc_text:
                        current_description = [desc_text]
                    else:
                        current_description = []
                continue

            # Check for Business Outcome section
            if line.startswith("Business Outcome:"):
                if current_epic is not None:
                    in_description = False
                    in_business_outcome = True
                    # Check if business outcome is on the same line
                    bo_text = line.replace("Business Outcome:", "").strip()
                    if bo_text:
                        current_epic["business_outcome"] = bo_text
                    else:
                        current_epic["business_outcome"] = ""
                continue

            # Check for Priority
            if line.startswith("Priority:"):
                priority_str = line.replace("Priority:", "").strip()
                if current_epic is not None:
                    current_epic["priority"] = self._parse_priority(priority_str)
                in_description = False
                in_business_outcome = False
                continue

            # Check for Story section
            if line.startswith("Story "):
                if current_story:
                    self._finalize_story(current_story, current_acceptance_criteria)
                current_story = {}
                current_acceptance_criteria = []
                in_acceptance_criteria = False
                in_description = False
                in_business_outcome = False

                # Extract story title
                story_match = re.search(r"Story \d+: (.+)", line)
                if story_match:
                    current_story["title"] = story_match.group(1).strip()
                continue

            # Check for Story Key
            if line.startswith("Story Key:"):
                if current_story is not None:
                    story_key = line.replace("Story Key:", "").strip()
                    current_story["story_key"] = story_key
                continue

            # Check for user story format
            if line.startswith("As a ") and current_story is not None:
                current_story["user_story"] = line
                continue

            # Check for Acceptance Criteria
            if line.startswith("Acceptance Criteria:"):
                in_acceptance_criteria = True
                in_description = False
                in_business_outcome = False
                continue

            # Parse acceptance criteria items
            if in_acceptance_criteria and line.startswith("*"):
                criteria_text = line.replace("*", "").strip()
                current_acceptance_criteria.append(AcceptanceCriteria(criteria_text))
                continue

            # Handle description content
            if in_description and current_epic is not None:
                current_description.append(line)
                continue

            # Handle business outcome content
            if in_business_outcome and current_epic is not None:
                if current_epic.get("business_outcome"):
                    current_epic["business_outcome"] += " " + line
                else:
                    current_epic["business_outcome"] = line
                continue

        # Finalize any remaining issues
        if current_epic:
            self._finalize_epic(current_epic, current_description)
        if current_story:
            self._finalize_story(current_story, current_acceptance_criteria)

        return self.issues

    def _parse_story_format(self, lines: List[str]) -> List[JiraIssue]:
        """Parse the new story format."""
        current_story = None
        current_acceptance_criteria = []
        in_acceptance_criteria = False
        user_story_lines = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for Story section
            if line.startswith("Story: "):
                if current_story:
                    self._finalize_new_story(current_story, current_acceptance_criteria)

                current_story = {}
                current_acceptance_criteria = []
                in_acceptance_criteria = False
                user_story_lines = []

                # Extract story title from "Story: [PREFIX] Title"
                story_title = line.replace("Story: ", "").strip()
                current_story["title"] = story_title
                continue

            # Check for Parent
            if line.startswith("Parent: ") and current_story is not None:
                current_story["parent"] = line.replace("Parent: ", "").strip()
                continue

            # Check for user story format (As a... I want... So that ...)
            if current_story is not None and (
                line.startswith("As a ")
                or line.startswith("I want ")
                or line.startswith("So that ")
            ):
                user_story_lines.append(line)
                continue

            # Check for Acceptance Criteria
            if line.startswith("Acceptance Criteria:"):
                in_acceptance_criteria = True
                # Save user story as description
                if current_story is not None and user_story_lines:
                    current_story["description"] = "\n".join(user_story_lines)
                continue

            # Parse acceptance criteria items (no bullet points in new format)
            if (
                in_acceptance_criteria
                and line
                and not line.startswith("Priority:")
                and not line.startswith("Dependencies:")
                and not line.startswith("Estimated Effort:")
                and not line.startswith("Labels:")
            ):
                current_acceptance_criteria.append(AcceptanceCriteria(line))
                continue

            # Check for Priority
            if line.startswith("Priority:") and current_story is not None:
                priority_str = line.replace("Priority:", "").strip()
                current_story["priority"] = self._parse_priority(priority_str)
                in_acceptance_criteria = False
                continue

            # Check for Dependencies
            if line.startswith("Dependencies:") and current_story is not None:
                current_story["dependencies"] = line.replace(
                    "Dependencies:", ""
                ).strip()
                continue

            # Check for Estimated Effort
            if line.startswith("Estimated Effort:") and current_story is not None:
                current_story["estimated_effort"] = line.replace(
                    "Estimated Effort:", ""
                ).strip()
                continue

            # Check for Labels
            if line.startswith("Labels:") and current_story is not None:
                current_story["labels"] = line.replace("Labels:", "").strip()
                continue

        # Finalize any remaining story
        if current_story:
            self._finalize_new_story(current_story, current_acceptance_criteria)

        return self.issues

    def _finalize_epic(self, epic_data: Dict, description_lines: List[str]):
        """Finalize and add an epic to the issues list."""
        # Use epic_name if available, otherwise use title, otherwise default
        title = epic_data.get("epic_name") or epic_data.get("title", "Untitled Epic")
        description = " ".join(description_lines) if description_lines else ""

        epic = JiraIssue(
            title=title,
            description=description,
            issue_type=IssueType.EPIC,
            priority=epic_data.get("priority", Priority.MEDIUM),
            business_outcome=epic_data.get("business_outcome"),
            epic_name=epic_data.get("epic_name"),
        )

        self.issues.append(epic)

    def _finalize_story(
        self, story_data: Dict, acceptance_criteria: List[AcceptanceCriteria]
    ):
        """Finalize and add a story to the issues list."""
        title = story_data.get("title", "Untitled Story")
        description = story_data.get("user_story", "")

        story = JiraIssue(
            title=title,
            description=description,
            issue_type=IssueType.STORY,
            priority=Priority.MEDIUM,  # Default priority for stories
            story_key=story_data.get("story_key"),
            acceptance_criteria=acceptance_criteria,
        )

        self.issues.append(story)

    def _finalize_new_story(
        self, story_data: Dict, acceptance_criteria: List[AcceptanceCriteria]
    ):
        """Finalize and add a new format story to the issues list."""
        title = story_data.get("title", "Untitled Story")
        description = story_data.get("description", "")

        story = JiraIssue(
            title=title,
            description=description,
            issue_type=IssueType.STORY,
            priority=story_data.get("priority", Priority.MEDIUM),
            story_key=story_data.get("story_key"),
            acceptance_criteria=acceptance_criteria,
            parent=story_data.get("parent"),
            dependencies=story_data.get("dependencies"),
            estimated_effort=story_data.get("estimated_effort"),
            labels=story_data.get("labels"),
        )

        self.issues.append(story)

    def _parse_priority(self, priority_str: str) -> Priority:
        """Parse priority string into Priority enum."""
        priority_mapping = {
            "highest": Priority.HIGHEST,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
            "lowest": Priority.LOWEST,
        }

        return priority_mapping.get(priority_str.lower(), Priority.MEDIUM)

    def _should_use_llm_fallback(self, text: str, issues: List[JiraIssue]) -> bool:
        """Determine if LLM fallback should be used."""
        if not self.enable_llm_fallback or not self.llm:
            return False

        # Use LLM fallback if:
        # 1. No issues were found
        # 2. Text is substantial but few issues were found (likely incomplete parsing)
        # 3. Issues have mostly empty descriptions or acceptance criteria

        if not issues:
            return True

        # Check if text is substantial but we found very few issues
        text_lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(text_lines) > 20 and len(issues) < 3:
            return True

        # Check if issues are mostly empty (poor parsing quality)
        empty_issues = 0
        for issue in issues:
            if (not issue.description or len(issue.description.strip()) < 10) and (
                not issue.acceptance_criteria or len(issue.acceptance_criteria) == 0
            ):
                empty_issues += 1

        # If more than half the issues are empty, use LLM fallback
        if empty_issues > len(issues) / 2:
            return True

        return False

    def _parse_with_llm(self, text: str) -> List[JiraIssue]:
        """Use LLM to extract Jira issues from text."""
        if not self.llm:
            return []

        try:
            from langchain.schema import HumanMessage, SystemMessage

            system_prompt = """You are an expert at extracting Jira issues from text.
            Given text content, extract all Epics, Stories, and Tasks with their details.

            Return the result as a JSON array of objects with this exact structure:
            [
              {
                "title": "Issue title",
                "description": "Full description",
                "issue_type": "Epic|Story|Task",
                "priority": "Highest|High|Medium|Low|Lowest",
                "story_key": "optional story key",
                "acceptance_criteria": ["criterion 1", "criterion 2"],
                "business_outcome": "optional business outcome",
                "epic_name": "optional epic name",
                "parent": "optional parent reference",
                "dependencies": "optional dependencies",
                "estimated_effort": "optional effort estimate",
                "labels": "optional labels"
              }
            ]

            Guidelines:
            - Extract all issues you can find
            - Use "Story" as default issue type if unclear
            - Use "Medium" as default priority if unclear
            - Combine multi-line content appropriately
            - Extract acceptance criteria as separate items
            - Be comprehensive but accurate
            """

            human_message = HumanMessage(
                content=f"""
            Please extract all Jira issues from this text:

            {text}

            Return only the JSON array, no other text.
            """
            )

            response = self.llm.invoke(
                [SystemMessage(content=system_prompt), human_message]
            )

            # Parse the LLM response
            return self._parse_llm_response(response.content)

        except Exception as e:
            print(f"⚠️  LLM parsing failed: {e}")
            return []

    def _parse_llm_response(self, response_content: str) -> List[JiraIssue]:
        """Parse LLM response into JiraIssue objects."""
        try:
            # Clean up the response to extract JSON
            content = response_content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            # Parse JSON
            issues_data = json.loads(content)

            if not isinstance(issues_data, list):
                print("⚠️  LLM response is not a list")
                return []

            issues = []
            for item in issues_data:
                try:
                    # Map the LLM response to JiraIssue
                    issue = JiraIssue(
                        title=item.get("title", "Untitled"),
                        description=item.get("description", ""),
                        issue_type=self._parse_issue_type(
                            item.get("issue_type", "Story")
                        ),
                        priority=self._parse_priority(item.get("priority", "Medium")),
                        story_key=item.get("story_key"),
                        acceptance_criteria=[
                            AcceptanceCriteria(desc)
                            for desc in item.get("acceptance_criteria", [])
                        ],
                        business_outcome=item.get("business_outcome"),
                        epic_name=item.get("epic_name"),
                        parent=item.get("parent"),
                        dependencies=item.get("dependencies"),
                        estimated_effort=item.get("estimated_effort"),
                        labels=item.get("labels"),
                    )
                    issues.append(issue)
                except Exception as e:
                    print(f"⚠️  Error parsing issue from LLM response: {e}")
                    continue

            return issues

        except json.JSONDecodeError as e:
            print(f"⚠️  Could not parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Error processing LLM response: {e}")
            return []

    def _parse_issue_type(self, issue_type_str: str) -> IssueType:
        """Parse issue type string into IssueType enum."""
        issue_type_mapping = {
            "epic": IssueType.EPIC,
            "story": IssueType.STORY,
            "task": IssueType.TASK,
        }
        return issue_type_mapping.get(issue_type_str.lower(), IssueType.STORY)
