# Jira Manager CLI Tool

A powerful command-line tool to connect to your Jira account (Cloud or Server) and manage projects, boards, and generate executive-ready weekly reports with intelligent issue summaries.

## Features

🔗 **Universal Jira Support** - Works with both Jira Cloud and Jira Server instances  
🔍 **Smart Project Search** - Find projects by name or key instantly  
📋 **Board Management** - Select boards by project or add specific board IDs  
📊 **Executive Reports** - Generate markdown reports with intelligent business impact summaries  
🎯 **Issue Filtering** - View issues by status (In Progress, In Review, Done, etc.)  
⚡ **Multiple Authentication** - Supports API tokens and Personal Access Tokens  
🛡️ **Secure Configuration** - Saves credentials locally for repeated use  

## Quick Start

### 1. Install Dependencies
```bash
pip install -r jira_requirements.txt
```

### 2. Initial Setup
```bash
python jira_manager.py setup
```

This interactive setup will:
- Connect to your Jira instance (Cloud or Server)
- Configure authentication (API token or Personal Access Token)
- Let you select projects and boards you work with

### 3. Generate Your First Report
```bash
# Generate weekly report for a specific board
python jira_manager.py weekly-report [BOARD_ID]

# Example:
python jira_manager.py weekly-report 21633
```

## Installation

### Prerequisites
- Python 3.7 or higher
- Access to a Jira instance (Cloud or Server)
- Valid Jira credentials

### Setup Steps

1. **Clone or download the files:**
   - `jira_manager.py` - Main application
   - `jira_requirements.txt` - Python dependencies

2. **Install Python dependencies:**
   ```bash
   pip install -r jira_requirements.txt
   ```

3. **Get your Jira credentials:**

   **For Jira Cloud (*.atlassian.net):**
   - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Create an API token
   - Use your email + API token for authentication

   **For Jira Server:**
   - Use your username + password, OR
   - Create a Personal Access Token in Jira Settings

4. **Run initial setup:**
   ```bash
   python jira_manager.py setup
   ```

## Usage Guide

### Initial Configuration

#### Setup Your Connection
```bash
python jira_manager.py setup
```

This will guide you through:
- Entering your Jira URL
- Choosing authentication method
- Testing the connection
- Selecting projects and boards

### Project Management

#### Select Projects by Name
```bash
python jira_manager.py select-project
```

Options:
1. Search by project name or key
2. Browse all projects
3. Select all projects

#### View Selected Projects
```bash
python jira_manager.py projects
```

### Board Management

#### Select Boards from Projects
```bash
python jira_manager.py select-boards
```

#### Add Specific Board by ID
```bash
python jira_manager.py add-board [BOARD_ID]

# Example:
python jira_manager.py add-board 21633
```

#### View Board Summaries
```bash
python jira_manager.py boards
```

### Issue Management

#### View Issues by Status
```bash
# Show issues for a specific board
python jira_manager.py board-issues [BOARD_ID]

# Show issues for all selected boards
python jira_manager.py all-board-issues

# Custom status filters
python jira_manager.py board-issues [BOARD_ID] --status "To Do" "In Progress" "Done"
```

### Weekly Reports

#### Generate Executive Reports
```bash
# Full report with executive summaries
python jira_manager.py weekly-report [BOARD_ID]

# Fast report without summaries
python jira_manager.py weekly-report [BOARD_ID] --no-summary

# Custom filename
python jira_manager.py weekly-report [BOARD_ID] --output "Executive_Report.md"

# Custom time period
python jira_manager.py weekly-report [BOARD_ID] --days 14
```

#### Report Features

**Executive Summary includes:**
- Clean issue description (JIRA markup removed)
- Current status and priority
- Component and scope analysis
- Latest comments and updates
- **Intelligent Business Impact Assessment:**
  - 🔴 **HIGH** - Critical business impact requiring immediate attention
  - 🟡 **MEDIUM** - Moderate business impact, should be prioritized  
  - 🟢 **LOW** - Minimal business impact, can be addressed in normal workflow

**Report Sections:**
- **Started** - Work begun in the past week
- **Completed** - Work finished in the past week  
- **Blocked/Off-track** - Issues requiring attention
- **Risks** - Template for management assessment

### Utility Commands

#### Test Connection
```bash
python jira_manager.py test
```

#### View Current Configuration
```bash
python jira_manager.py list
```

## Configuration

### Configuration File
Settings are stored in `jira_config.json`:

```json
{
  "base_url": "https://issues.redhat.com",
  "email": "user@company.com",
  "api_token": "your_api_token",
  "auth_method": "basic",
  "api_version": "v2",
  "selected_projects": [
    {"key": "OCM", "name": "OpenShift Cluster Manager"}
  ],
  "selected_boards": [
    {"id": "21633", "name": "OCM Kanban", "type": "kanban"}
  ]
}
```

### Finding Board IDs

Board IDs can be found in Jira URLs:
```
https://issues.redhat.com/secure/RapidBoard.jspa?rapidView=21633
                                                          ^^^^^
                                                       Board ID
```

## Examples

### Daily Workflow Example
```bash
# Check current board status
python jira_manager.py board-issues 21633

# Generate weekly report for management
python jira_manager.py weekly-report 21633 --output "Weekly_Status_$(date +%Y-%m-%d).md"
```

### Multi-Board Management
```bash
# Add multiple boards
python jira_manager.py add-board 21633  # OCM Kanban
python jira_manager.py add-board 22050  # Another board

# Generate reports for all boards
python jira_manager.py all-board-issues
```

### Executive Reporting
```bash
# Generate comprehensive executive report
python jira_manager.py weekly-report 21633 \
  --output "Executive_Weekly_Report_$(date +%Y-%m-%d).md" \
  --days 7
```

## Troubleshooting

### Common Issues

**Connection Failed:**
```bash
# Test your connection
python jira_manager.py test

# Re-run setup if needed
python jira_manager.py setup
```

**No Boards Found:**
- Use `python jira_manager.py add-board [ID]` to add boards manually
- Check board permissions in Jira

**Authentication Errors:**
- Verify API token is still valid
- For Jira Server, try Personal Access Token instead
- Check if 2FA is interfering with authentication

**Date/Timezone Errors:**
- The tool automatically handles timezone differences
- If issues persist, try `--no-summary` for faster processing

### Performance Tips

- Use `--no-summary` for quick reports (5-10 seconds vs 30-60 seconds)
- Limit time ranges with `--days` parameter for large boards
- Test connection with `python jira_manager.py test` if experiencing slowness

## Advanced Usage

### API Compatibility
- **Jira Cloud**: Uses REST API v3 by default
- **Jira Server**: Automatically detects and uses REST API v2
- **Agile/Board APIs**: Tries multiple endpoints for maximum compatibility

### Batch Operations
```bash
# Generate reports for multiple boards
for board_id in 21633 22050 22100; do
  python jira_manager.py weekly-report $board_id --output "Report_${board_id}_$(date +%Y%m%d).md"
done
```

## Contributing

This tool was designed for Red Hat's Jira instance but works with any Jira Cloud or Server deployment.

### Extending the Tool
- Add new report formats in `generate_weekly_report()`
- Customize business impact scoring in `_assess_business_impact()`
- Add new issue filters in `get_board_issues_by_status()`

## Security

- Credentials are stored locally in `jira_config.json`
- API tokens are recommended over passwords
- No credentials are transmitted except to your specified Jira instance
- Use Personal Access Tokens for enhanced security in Jira Server

## License

This tool is designed for internal productivity and integrates with Atlassian Jira instances.

---

**Generated with Claude Code** - An AI-powered development assistant
