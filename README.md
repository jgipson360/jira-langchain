# Jira LangChain Automation Tool

Automated Jira ticket creation using LangChain and Jira Toolkit. Generates epics, stories, and tasks from text input based on configurable Jira connection settings.

## Fun Fact 🏠

This project was born out of a very real need! I was facing a massive family home cleanup project involving deep cleaning, and organization across multiple rooms. With hundreds of interconnected tasks, dependencies, and different family members involved, I needed a way to quickly organize everything in Jira without spending hours clicking through the interface. What started as "I need to create 50+ tickets for a home cleanup project" became a robust automation tool that handles complex project structures, smart epic mapping, and dependency relationships. Sometimes the best software comes from solving your own immediate problems! 🐛➡️✅

## Features

### 🚀 Advanced Automation
- **🧠 Intelligent LLM Fallback**: When structured parsing fails, Claude/Gemini automatically extracts issues from natural language text
- **🎯 Dynamic Epic Discovery**: Automatically finds and maps existing epics in your Jira project - no hardcoded configurations needed
- **🔗 Smart Dependency Linking**: Creates "blocks/blocked by" relationships between issues automatically with intelligent resolution
- **⚡ Robust Multi-Format Parsing**: Handles both structured ticket formats and natural language descriptions seamlessly
- **🔄 Placeholder Epic Creation**: Creates missing epics when stories reference non-existent parents

### 🎨 Enhanced User Experience
- **📝 Text-to-Jira**: Parse structured text files and create Jira tickets automatically
- **🤖 LLM Enhancement**: Use Claude or Gemini to enhance ticket descriptions and acceptance criteria
- **🏃‍♂️ Command Line Interface**: Easy-to-use CLI with dry-run mode for safe testing
- **🔄 Batch Processing**: Create multiple related tickets with dependencies in a single run
- **🔍 Verbose Mode**: Detailed output for debugging and validation

### 🔧 Smart Integration
- **📊 Epic-Story Linking**: Automatically links stories to their parent epics using discovered field mappings
- **🏷️ Label Management**: Parses and creates labels, handling spaces and special characters intelligently
- **✅ Field Discovery**: Automatically discovers Jira project fields (Epic Link, Parent, etc.)
- **🔒 Secure Configuration**: Environment-based configuration with API token support
- **📋 Multiple Issue Types**: Support for Epics, Stories, and Tasks with proper hierarchy
- **🎯 Priority Support**: Handles priority fields for all issue types with proper validation

## Quick Start

### Prerequisites

- Python 3.9 or higher
- A Jira instance with API access
- (Optional) Anthropic API key for LLM enhancement

### 1. Setup

```bash
# Clone or download the project
cd jira-langchain

# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Create your `.env` file:

```bash
# Interactive setup
python main.py setup

# Or copy and edit the example
cp .env.example .env
# Edit .env with your credentials
```

Required configuration:
- **Jira URL**: Your Atlassian instance URL
- **Jira Username**: Your email address
- **Jira API Token**: Generate from Atlassian Account Settings
- **Project Key**: Your Jira project key
- **LLM API Key**: Claude (Anthropic) or Gemini (Google) API key

### 3. Usage

```bash
# Test with sample file (dry run)
python main.py -i test_tickets.txt --dry-run

# Create tickets with LLM enhancement
python main.py -i tickets.txt --enhance

# Verbose output
python main.py -i tickets.txt --verbose
```

## Input Format

The tool supports multiple input formats and automatically detects the best parsing approach:

### 📋 Structured Format
For maximum control, use the structured format:

```
epic:

Epic 1: [Epic Title]
Epic Name: [Epic Name for Jira]
Description: [Detailed description of the epic]
Business Outcome: [Expected business outcome]
Priority: [Highest/High/Medium/Low/Lowest]

Epic 1: [Epic Title] - User Stories
Story 1: [Story Title]
Story Key: [PROJECT-KEY]-1
Priority: [Priority Level]
Parent: [EPIC-PREFIX]
Dependencies: [EPIC-PREFIX - Task Name], [Another Epic - Task Name]
Estimated Effort: [8 hours]
Labels: [backend, api, critical]
As a [user type] I want [functionality] So that [benefit]
Acceptance Criteria:
* [Criterion 1]
* [Criterion 2]
* [Criterion 3]

Story 2: [Another Story Title]
Story Key: [PROJECT-KEY]-2
Priority: [Priority Level]
As a [user type] I want [functionality] So that [benefit]
Acceptance Criteria:
* [Criterion 1]
* [Criterion 2]
```

### 🧠 Natural Language Format
The tool also handles natural language descriptions thanks to LLM fallback:

```
We need to clean up the kitchen and organize everything.

First, we should deal with the organization issue in the pantry.
This involves removing all items, cleaning the area, and then restocking.

Then we need to deep clean all surfaces including:
- Countertops and backsplash
- Inside of all cabinets
- Appliance exteriors and interiors
- Floor mopping and baseboards

Finally, we should organize everything by category and label containers.
```

**The system will automatically:**
- 🎯 Detect epic relationships and create missing parent epics
- 🔗 Parse and resolve dependencies between tasks
- 🏷️ Extract and clean labels from text
- 📊 Link stories to appropriate epics using existing project structure
- 🤖 Fall back to LLM parsing when structured parsing is incomplete

## Sample Tickets

### Epic Format Example
```
Epic 1: SETUP - Project Setup & Planning
Epic Name: SETUP - Initial Project Setup & Planning
Description:
For teams starting a new project who need to establish foundational elements and planning structure, the Project Setup & Planning epic provides a comprehensive framework for project initialization. This epic covers initial requirements gathering, resource allocation, and timeline establishment to ensure project success from the start.
Business Outcome:
Establishes solid project foundation within 1-2 weeks, ensuring all team members are aligned on objectives, timelines, and deliverables.
Priority: Highest

Epic 2: DEV - Development & Implementation
Epic Name: DEV - Core Development & Implementation
Description:
For development teams who need to implement core functionality and features, the Development & Implementation epic provides structured approach to coding, testing, and integration activities.
Business Outcome:
Delivers working software components within planned timeline while maintaining quality standards.
Priority: High
```

### Story Format Example
```
Story: [SETUP] Requirements Gathering Session
Parent: SETUP
As a project manager
I want to conduct comprehensive requirements gathering sessions
So that I can ensure all stakeholder needs are captured and documented.
Acceptance Criteria:

Schedule meetings with all key stakeholders
Prepare structured interview questions
Document functional requirements clearly
Identify non-functional requirements
Create requirements traceability matrix
Obtain stakeholder sign-off on requirements
Establish change control process

Priority: Highest
Dependencies: None
Estimated Effort: 16 hours
Labels: planning, requirements, stakeholders

Story: [SETUP] Development Environment Setup
Parent: SETUP
As a developer
I want to set up a standardized development environment
So that I can begin coding with all necessary tools and dependencies.
Acceptance Criteria:

Install required IDE and extensions
Set up version control repositories
Configure build tools and dependencies
Establish coding standards and linting rules
Create documentation templates
Test environment connectivity
Verify all team members can access shared resources

Priority: High
Dependencies: [SETUP] Requirements Gathering Session
Estimated Effort: 8 hours
Labels: development, environment, tools

Story: [DEV] API Endpoint Development
Parent: DEV
As a backend developer
I want to implement REST API endpoints
So that frontend applications can interact with the system.
Acceptance Criteria:

Design API specification and documentation
Implement CRUD operations for core entities
Add input validation and error handling
Create comprehensive unit tests
Implement authentication and authorization
Add API rate limiting and security headers
Update API documentation with examples

Priority: High
Dependencies: [SETUP] Development Environment Setup
Estimated Effort: 24 hours
Labels: backend, api, security
```

## Command Line Options

```bash
python main.py [OPTIONS]

Options:
  -i, --input-file PATH    Path to input text file [required]
  -d, --dry-run           Parse and display without creating tickets
  -e, --enhance           Use LLM to enhance descriptions
  -v, --verbose           Enable verbose output
  -c, --config PATH       Path to custom .env file
  --help                  Show help message
```

## Configuration

### Jira Setup

1. **Generate API Token**:
   - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Create API token
   - Copy the token to your `.env` file

2. **Find Project Key**:
   - Go to your Jira project
   - Look at the URL or project settings
   - Use the short key (e.g., "PROJ" for project "PROJ-123")

### LLM Setup

**For Claude (Anthropic)**:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key
```

**For Gemini (Google)**:
```bash
LLM_PROVIDER=google
GOOGLE_API_KEY=your-api-key
```

## Examples

### Basic Usage
```bash
# Parse and preview tickets (always test first!)
python main.py -i tickets.txt --dry-run

# Create tickets with automatic epic discovery
python main.py -i tickets.txt

# Create with AI enhancement and verbose output
python main.py -i tickets.txt --enhance --verbose
```

### Advanced Usage
```bash
# Use custom config file
python main.py -i tickets.txt -c production.env

# Process multiple files with batch operations
for file in tickets/*.txt; do
    python main.py -i "$file" --enhance
done

# Test complex natural language processing
python main.py -i messy_notes.txt --dry-run --verbose
```

## Troubleshooting

### Common Issues

1. **"Missing required Jira configuration"**
   - Check your `.env` file exists and has all required fields
   - Verify API token is correct

2. **"Failed to connect to Jira"**
   - Verify Jira URL is correct (include https://)
   - Check API token permissions
   - Ensure project key exists and you have access

3. **"Import errors"**
   - Activate virtual environment: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`

4. **"LLM API errors"**
   - Verify API key is correct
   - Check API quota/limits
   - Ensure LLM_PROVIDER matches your API key type

5. **"ChatAnthropic validation errors"**
   - Ensure both model name and API key are provided
   - Test connection with: `python -c "from langchain_anthropic import ChatAnthropic; import os; llm = ChatAnthropic(model='claude-3-5-sonnet-20240620', anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')); print('✅ Connection successful')"`

6. **"Epic mapping issues"**
   - The system automatically discovers epics - no manual configuration needed
   - Check that existing epics follow naming conventions (e.g., "PREP - Kitchen Cleanup")
   - Use `--verbose` to see epic discovery process

7. **"Dependency resolution problems"**
   - Dependencies are automatically resolved using epic prefixes and task names
   - Use format: `[EPIC-PREFIX - Task Name]` for best results
   - Check `--dry-run` output to verify dependency links

8. **"LLM fallback not working"**
   - Ensure LLM_PROVIDER is set correctly (anthropic/google)
   - Check API key permissions and quotas
   - LLM fallback activates when structured parsing finds few/incomplete issues

### Advanced Features Troubleshooting

**Dynamic Epic Discovery**
```bash
# Test epic discovery independently
python main.py -i empty_file.txt --dry-run --verbose
# Look for "🔍 Discovered X epics" messages
```

**Dependency Linking**
```bash
# Verify dependency format in input
# Use: Dependencies: [KITCH - Clean counters], [PREP - Remove items]
python main.py -i tickets.txt --dry-run --verbose
# Check for "🔗 Resolved dependency" messages
```

**LLM Fallback Activation**
```bash
# Test with natural language input
python main.py -i natural_language.txt --dry-run --verbose
# Look for "🤖 Structured parsing incomplete - trying LLM fallback"
```

### Debug Mode

Run with verbose output to see detailed information:
```bash
python main.py -i tickets.txt --verbose --dry-run
```

## Development

### Project Structure
```
jira-langchain/
├── main.py              # CLI interface
├── jira_integration.py  # Jira API integration
├── parser.py           # Text parsing logic
├── requirements.txt    # Dependencies
├── setup.sh           # Setup script
├── .env.example       # Configuration template
└── test_tickets.txt # Example input
```

### Adding New Features

1. **New Issue Types**: Update `parser.py` and `jira_integration.py`
2. **New LLM Providers**: Add to `jira_integration.py`
3. **New Input Formats**: Extend `TextParser` class

## API Reference

### Jira Integration
- Based on [LangChain Jira Tool](https://python.langchain.com/docs/integrations/tools/jira/)
- Uses Atlassian Python API for direct integration
- Supports both API token and OAuth authentication

### LLM Integration
- **Claude**: Uses `langchain-anthropic` package
- **Gemini**: Uses `langchain-google-genai` package
- Extensible for other providers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
