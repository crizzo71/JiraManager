#!/usr/bin/env python3
"""
Jira Project and Board Manager

A command-line tool to access your Jira account and manage projects and boards.
Provides interactive setup and management of Jira resources.
"""

import os
import json
import base64
import argparse
import getpass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import requests
from requests.auth import HTTPBasicAuth

CONFIG_FILE = 'jira_config.json'

class JiraManager:
    def __init__(self):
        self.base_url = None
        self.email = None
        self.api_token = None
        self.personal_token = None
        self.auth_method = 'basic'  # 'basic' or 'token'
        self.api_version = None  # Will be detected: 'v2' or 'v3'
        self.session = requests.Session()
        self.selected_projects = []
        self.selected_boards = []
        
    def load_config(self) -> bool:
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.base_url = config.get('base_url')
                    self.email = config.get('email')
                    self.api_token = config.get('api_token')
                    self.personal_token = config.get('personal_token')
                    self.auth_method = config.get('auth_method', 'basic')
                    self.api_version = config.get('api_version')
                    self.selected_projects = config.get('selected_projects', [])
                    self.selected_boards = config.get('selected_boards', [])
                    
                    if self.base_url and ((self.auth_method == 'basic' and self.email and self.api_token) or 
                                         (self.auth_method == 'token' and self.personal_token)):
                        self.setup_session()
                        return True
            except (json.JSONDecodeError, KeyError):
                print("Invalid configuration file. Please run setup again.")
        return False
    
    def save_config(self):
        """Save configuration to file"""
        config = {
            'base_url': self.base_url,
            'email': self.email,
            'api_token': self.api_token,
            'personal_token': self.personal_token,
            'auth_method': self.auth_method,
            'api_version': self.api_version,
            'selected_projects': self.selected_projects,
            'selected_boards': self.selected_boards
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {CONFIG_FILE}")
    
    def setup_session(self):
        """Setup authenticated session"""
        if self.auth_method == 'token':
            self.session.headers.update({
                'Authorization': f'Bearer {self.personal_token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
        else:
            self.session.auth = HTTPBasicAuth(self.email, self.api_token)
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
    
    def interactive_setup(self):
        """Interactive setup to gather Jira credentials and preferences"""
        print("🔧 Jira Manager Setup")
        print("=" * 50)
        
        # Get Jira instance details
        print("\n1. Jira Instance Details")
        print("Enter your Jira URL:")
        print("  • Jira Cloud: https://yourcompany.atlassian.net")
        print("  • Jira Server: https://jira.yourcompany.com")
        
        while True:
            self.base_url = input("Jira URL: ").strip().rstrip('/')
            
            # Fix common typos
            if self.base_url.startswith('htpps://'):
                self.base_url = self.base_url.replace('htpps://', 'https://')
                print(f"Fixed typo: {self.base_url}")
            elif self.base_url.startswith('htpp://'):
                self.base_url = self.base_url.replace('htpp://', 'https://')
                print(f"Fixed typo: {self.base_url}")
            elif not self.base_url.startswith(('http://', 'https://')):
                self.base_url = 'https://' + self.base_url
                print(f"Added https: {self.base_url}")
            
            # Validate URL format
            if self.base_url.startswith(('http://', 'https://')):
                break
            else:
                print("❌ Invalid URL format. Please enter a valid URL (e.g., https://issues.redhat.com)")
        
        # Detect if this is likely a Server instance
        is_server = not '.atlassian.net' in self.base_url.lower()
        if is_server:
            print("🔍 Detected possible Jira Server instance")
        
        print("\n2. Authentication Method")
        if is_server:
            print("For Jira Server, choose your authentication method:")
            print("1. Basic Auth (username + password)")
            print("2. Personal Access Token (if available)")
        else:
            print("Choose your authentication method:")
            print("1. Basic Auth (email + API token)")
            print("2. Personal Access Token")
        
        auth_choice = input("Enter choice (1 or 2): ").strip()
        
        if auth_choice == "2":
            self.auth_method = 'token'
            if is_server:
                print("\n3. Personal Access Token")
                print("Enter your Jira Server Personal Access Token")
                print("(Create one in Jira: Profile > Personal Access Tokens)")
            else:
                print("\n3. Personal Access Token")
                print("Enter your Jira Personal Access Token")
                print("(Create one in Jira: Settings > Personal Access Tokens)")
            self.personal_token = getpass.getpass("Personal Token: ").strip()
        else:
            self.auth_method = 'basic'
            if is_server:
                print("\n3. Basic Authentication")
                print("Enter your Jira Server credentials:")
                self.email = input("Username: ").strip()
                self.api_token = getpass.getpass("Password: ").strip()
            else:
                print("\n3. Basic Authentication")
                print("You'll need your email and an API token from Atlassian Account Settings")
                print("(Go to: https://id.atlassian.com/manage-profile/security/api-tokens)")
                self.email = input("Email: ").strip()
                self.api_token = getpass.getpass("API Token: ").strip()
        
        # Setup session for testing
        self.setup_session()
        
        # Test connection
        print("\n4. Testing connection...")
        if not self.test_connection():
            print("❌ Connection failed. Please check your credentials.")
            return False
        
        print("✅ Connection successful!")
        
        # Select projects
        print("\n5. Select Projects")
        self.select_projects()
        
        # Select boards
        print("\n6. Select Boards")
        self.select_boards()
        
        # Save configuration
        self.save_config()
        print("\n✅ Setup complete!")
        return True
    
    def test_connection(self) -> bool:
        """Test Jira API connection"""
        try:
            print(f"Testing connection to: {self.base_url}")
            if self.auth_method == 'token':
                print("Using Personal Access Token authentication")
            else:
                print(f"Using email: {self.email}")
            
            # Try API v3 first (Cloud), fallback to v2 (Server)
            api_endpoint = f"{self.base_url}/rest/api/3/myself"
            response = self.session.get(api_endpoint)
            
            # If v3 fails, try v2 for Jira Server
            if response.status_code == 404 or (response.status_code == 200 and response.text.strip().startswith('<')):
                print("API v3 not found, trying API v2 (Jira Server)...")
                api_endpoint = f"{self.base_url}/rest/api/2/myself"
                response = self.session.get(api_endpoint)
                self.api_version = 'v2'
            else:
                self.api_version = 'v3'
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    user_info = response.json()
                    print(f"Connected as: {user_info.get('displayName', 'Unknown User')}")
                    return True
                except json.JSONDecodeError:
                    print("⚠️  Got 200 response but invalid JSON. Checking response content...")
                    print(f"Response content: {response.text[:200]}...")
                    
                    # Check if this might be HTML (non-API endpoint)
                    if response.text.strip().startswith('<'):
                        print("❌ Received HTML response instead of JSON.")
                        print("   This might not be a Jira Cloud instance or the URL is incorrect.")
                        print("   Make sure you're using the correct Jira Cloud URL.")
                        return False
                    else:
                        print("❌ Unexpected response format.")
                        return False
            elif response.status_code == 401:
                print("❌ Authentication failed. Please check:")
                print("   • Your email address is correct")
                print("   • Your API token is valid and not expired")
                print("   • You have access to this Jira instance")
                return False
            elif response.status_code == 403:
                print("❌ Access forbidden. You may not have permission to access this Jira instance.")
                return False
            elif response.status_code == 404:
                print("❌ Jira instance not found. Please check your URL.")
                print("   • Make sure the URL is correct (e.g., https://yourcompany.atlassian.net)")
                print("   • Verify this is a Jira Cloud instance")
                return False
            else:
                print(f"❌ Unexpected error: {response.status_code}")
                try:
                    error_details = response.json()
                    print(f"Error details: {error_details}")
                except:
                    print(f"Response text: {response.text}")
                return False
        except requests.ConnectionError as e:
            print(f"❌ Network connection error: {e}")
            print("   • Check your internet connection")
            print("   • Verify the Jira URL is accessible")
            return False
        except requests.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Fetch all projects"""
        try:
            # Use detected API version or try both
            if self.api_version == 'v2':
                api_endpoint = f"{self.base_url}/rest/api/2/project"
            else:
                api_endpoint = f"{self.base_url}/rest/api/3/project"
            
            print(f"Trying to fetch projects from: {api_endpoint}")
            response = self.session.get(api_endpoint)
            
            # Check if we got HTML instead of JSON (indicates wrong endpoint or auth issue)
            if response.status_code == 200 and response.text.strip().startswith('<'):
                print("Got HTML response, trying other API version...")
                if self.api_version != 'v2':
                    api_endpoint = f"{self.base_url}/rest/api/2/project"
                    print(f"Trying: {api_endpoint}")
                    response = self.session.get(api_endpoint)
            elif response.status_code == 404 and self.api_version != 'v2':
                print("API v3 not found, trying API v2...")
                api_endpoint = f"{self.base_url}/rest/api/2/project"
                print(f"Trying: {api_endpoint}")
                response = self.session.get(api_endpoint)
            
            print(f"Projects API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    projects = response.json()
                    print(f"Successfully fetched {len(projects)} projects")
                    return projects
                except json.JSONDecodeError as e:
                    print(f"Failed to parse projects JSON: {e}")
                    print(f"Response content (first 200 chars): {response.text[:200]}...")
                    return []
            else:
                print(f"Failed to fetch projects: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return []
        except requests.RequestException as e:
            print(f"Network error fetching projects: {e}")
            return []
    
    def get_boards(self) -> List[Dict[str, Any]]:
        """Fetch all boards using multiple methods"""
        boards = []
        
        # Method 1: Try Agile API (works for both Cloud and some Server instances)
        try:
            print("Trying Agile API for boards...")
            response = self.session.get(f"{self.base_url}/rest/agile/1.0/board")
            print(f"Agile API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    boards = data.get('values', [])
                    print(f"Found {len(boards)} boards via Agile API")
                    if boards:
                        return boards
                except json.JSONDecodeError as e:
                    print(f"Agile API JSON decode error: {e}")
            else:
                print(f"Agile API failed: {response.status_code}")
                if response.status_code == 401:
                    print("Authentication issue with Agile API")
                elif response.status_code == 403:
                    print("No permission to access Agile API")
                elif response.status_code == 404:
                    print("Agile API not available (common in older Jira Server)")
        except requests.RequestException as e:
            print(f"Agile API error: {e}")
        
        # Method 2: Try GreenHopper API (older Jira Server)
        try:
            print("Trying GreenHopper API for boards...")
            response = self.session.get(f"{self.base_url}/rest/greenhopper/1.0/rapidview")
            print(f"GreenHopper API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    views = data.get('views', [])
                    print(f"Found {len(views)} rapid views via GreenHopper API")
                    
                    # Convert GreenHopper format to standard board format
                    for view in views:
                        board = {
                            'id': view.get('id'),
                            'name': view.get('name'),
                            'type': 'scrum' if view.get('sprintSupportEnabled', False) else 'kanban',
                            'location': {
                                'projectKey': self._extract_project_from_filter(view.get('filter', {}).get('query', ''))
                            }
                        }
                        boards.append(board)
                    
                    if boards:
                        return boards
                except json.JSONDecodeError as e:
                    print(f"GreenHopper API JSON decode error: {e}")
            else:
                print(f"GreenHopper API failed: {response.status_code}")
        except requests.RequestException as e:
            print(f"GreenHopper API error: {e}")
        
        # Method 3: Create mock boards based on projects (fallback)
        if not boards and self.selected_projects:
            print("No boards found via APIs, creating project-based entries...")
            for project in self.selected_projects:
                board = {
                    'id': f"project-{project['key']}",
                    'name': f"{project['name']} (Project View)",
                    'type': 'project',
                    'location': {
                        'projectKey': project['key']
                    }
                }
                boards.append(board)
        
        print(f"Total boards found: {len(boards)}")
        return boards
    
    def _extract_project_from_filter(self, filter_query: str) -> str:
        """Extract project key from JQL filter query"""
        import re
        if not filter_query:
            return 'N/A'
        
        # Look for "project = KEY" or "project in (KEY)" patterns
        match = re.search(r'project\s*(?:=|in)\s*(?:\()?[\'"]*([A-Z][A-Z0-9]*)', filter_query, re.IGNORECASE)
        if match:
            return match.group(1)
        return 'N/A'
    
    def get_issue_details(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific issue"""
        try:
            # Try API v3 first, fallback to v2
            if self.api_version == 'v2':
                api_endpoint = f"{self.base_url}/rest/api/2/issue/{issue_key}"
            else:
                api_endpoint = f"{self.base_url}/rest/api/3/issue/{issue_key}"
            
            # Request additional fields for detailed information
            params = {
                'expand': 'changelog,renderedFields',
                'fields': 'summary,description,status,assignee,priority,issuetype,created,updated,components,labels,fixVersions,comment'
            }
            
            response = self.session.get(api_endpoint, params=params)
            
            if response.status_code == 404 and self.api_version != 'v2':
                # Try v2 if v3 fails
                api_endpoint = f"{self.base_url}/rest/api/2/issue/{issue_key}"
                response = self.session.get(api_endpoint, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch details for {issue_key}: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"Error fetching details for {issue_key}: {e}")
            return None
    
    def generate_executive_summary(self, issue_details: Dict[str, Any]) -> str:
        """Generate an executive summary for an issue"""
        if not issue_details:
            return "Unable to generate summary - issue details not available."
        
        fields = issue_details.get('fields', {})
        key = issue_details.get('key', 'Unknown')
        
        # Extract key information
        summary = fields.get('summary', 'No summary available')
        description = fields.get('description', '')
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
        priority = fields.get('priority', {}).get('name', 'Unknown')
        status = fields.get('status', {}).get('name', 'Unknown')
        assignee = fields.get('assignee')
        assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
        
        # Get components and labels
        components = [c.get('name', '') for c in fields.get('components', [])]
        labels = fields.get('labels', [])
        
        # Get recent comments (last 2)
        comments = fields.get('comment', {}).get('comments', [])
        recent_comments = comments[-2:] if len(comments) > 0 else []
        
        # Build executive summary
        summary_parts = []
        
        # Basic description
        if description:
            # Clean up description (remove markup, truncate)
            clean_desc = self._clean_jira_text(description)
            if len(clean_desc) > 200:
                clean_desc = clean_desc[:197] + "..."
            summary_parts.append(f"**Description:** {clean_desc}")
        
        # Current status and priority
        summary_parts.append(f"**Current Status:** {status} | **Priority:** {priority}")
        
        # Components and scope
        if components:
            summary_parts.append(f"**Components:** {', '.join(components)}")
        
        # Recent activity/comments
        if recent_comments:
            latest_comment = recent_comments[-1]
            comment_author = latest_comment.get('author', {}).get('displayName', 'Unknown')
            comment_text = self._clean_jira_text(latest_comment.get('body', ''))
            if len(comment_text) > 100:
                comment_text = comment_text[:97] + "..."
            summary_parts.append(f"**Latest Update ({comment_author}):** {comment_text}")
        
        # Business impact assessment
        impact_level = self._assess_business_impact(issue_type, priority, labels, description)
        summary_parts.append(f"**Business Impact:** {impact_level}")
        
        return '\n'.join(summary_parts)
    
    def _clean_jira_text(self, text: str) -> str:
        """Clean JIRA markup from text"""
        if not text:
            return ""
        
        import re
        
        # Remove common JIRA markup
        text = re.sub(r'\{[^}]*\}', '', text)  # Remove {code}, {color}, etc.
        text = re.sub(r'\[~[^\]]*\]', '', text)  # Remove user mentions
        text = re.sub(r'\[[^\]]*\|[^\]]*\]', '', text)  # Remove links
        text = re.sub(r'h[1-6]\. ', '', text)  # Remove headers
        text = re.sub(r'[*_#]+', '', text)  # Remove emphasis markup
        text = re.sub(r'\n+', ' ', text)  # Replace newlines with spaces
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        return text.strip()
    
    def _assess_business_impact(self, issue_type: str, priority: str, labels: List[str], description: str) -> str:
        """Assess business impact based on issue characteristics"""
        impact_score = 0
        
        # Priority-based scoring
        priority_lower = priority.lower()
        if 'critical' in priority_lower or 'highest' in priority_lower:
            impact_score += 4
        elif 'high' in priority_lower:
            impact_score += 3
        elif 'medium' in priority_lower:
            impact_score += 2
        else:
            impact_score += 1
        
        # Type-based scoring
        type_lower = issue_type.lower()
        if 'bug' in type_lower and ('critical' in type_lower or 'blocker' in type_lower):
            impact_score += 2
        elif 'security' in type_lower:
            impact_score += 2
        elif 'feature' in type_lower or 'epic' in type_lower:
            impact_score += 1
        
        # Labels and description keywords
        high_impact_keywords = ['outage', 'down', 'critical', 'security', 'data loss', 'customer impact', 'revenue']
        text_to_check = ' '.join(labels + [description]).lower()
        
        for keyword in high_impact_keywords:
            if keyword in text_to_check:
                impact_score += 1
                break
        
        # Determine impact level
        if impact_score >= 6:
            return "🔴 **HIGH** - Critical business impact requiring immediate attention"
        elif impact_score >= 4:
            return "🟡 **MEDIUM** - Moderate business impact, should be prioritized"
        else:
            return "🟢 **LOW** - Minimal business impact, can be addressed in normal workflow"
    
    def get_board_by_id(self, board_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific board by ID"""
        try:
            # Try Agile API first
            response = self.session.get(f"{self.base_url}/rest/agile/1.0/board/{board_id}")
            if response.status_code == 200:
                return response.json()
            
            # Try GreenHopper API
            response = self.session.get(f"{self.base_url}/rest/greenhopper/1.0/rapidview/{board_id}")
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': data.get('id'),
                    'name': data.get('name'),
                    'type': 'scrum' if data.get('sprintSupportEnabled', False) else 'kanban',
                    'location': {
                        'projectKey': self._extract_project_from_filter(data.get('filter', {}).get('query', ''))
                    }
                }
        except:
            pass
        return None
    
    def find_project_by_name(self, projects: List[Dict[str, Any]], search_term: str) -> List[Dict[str, Any]]:
        """Find projects by name or key (case insensitive)"""
        search_term = search_term.lower()
        matches = []
        
        for project in projects:
            project_name = project['name'].lower()
            project_key = project['key'].lower()
            
            if (search_term in project_name or 
                search_term in project_key or 
                project_name == search_term or 
                project_key == search_term):
                matches.append(project)
        
        return matches
    
    def select_projects(self):
        """Interactive project selection with name search"""
        projects = self.get_projects()
        if not projects:
            print("No projects found or unable to fetch projects.")
            return
        
        print(f"\nFound {len(projects)} projects available.")
        print("\nProject Selection Options:")
        print("1. Enter project name or key to search")
        print("2. List all projects and select by number")
        print("3. Select all projects")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # Search by name/key
            while True:
                search_term = input("\nEnter project name or key to search: ").strip()
                if not search_term:
                    print("Please enter a search term.")
                    continue
                
                matches = self.find_project_by_name(projects, search_term)
                
                if not matches:
                    print(f"No projects found matching '{search_term}'")
                    retry = input("Try another search? (y/n): ").strip().lower()
                    if retry != 'y':
                        self.selected_projects = []
                        return
                    continue
                
                print(f"\nFound {len(matches)} matching project(s):")
                print("-" * 60)
                
                for i, project in enumerate(matches, 1):
                    project_type = project.get('projectTypeKey', 'unknown')
                    lead = project.get('lead', {}).get('displayName', 'Unknown')
                    print(f"{i:2}. {project['name']} ({project['key']}) - {project_type}")
                    print(f"    Lead: {lead}")
                
                if len(matches) == 1:
                    # Single match - auto select
                    self.selected_projects = [{'key': matches[0]['key'], 'name': matches[0]['name']}]
                    print(f"\nSelected: {matches[0]['name']} ({matches[0]['key']})")
                    break
                else:
                    # Multiple matches - let user choose
                    print(f"\nSelect from matches (1-{len(matches)}, 'all' for all matches):")
                    selection = input("Selection: ").strip()
                    
                    if selection.lower() == 'all':
                        self.selected_projects = [{'key': p['key'], 'name': p['name']} for p in matches]
                    else:
                        try:
                            choice_idx = int(selection) - 1
                            if 0 <= choice_idx < len(matches):
                                selected_project = matches[choice_idx]
                                self.selected_projects = [{'key': selected_project['key'], 'name': selected_project['name']}]
                            else:
                                print("Invalid selection.")
                                continue
                        except ValueError:
                            print("Invalid selection.")
                            continue
                    break
        
        elif choice == "3":
            # Select all projects
            self.selected_projects = [{'key': p['key'], 'name': p['name']} for p in projects]
            
        else:
            # List all and select by number (original behavior)
            print(f"\nAll {len(projects)} projects:")
            print("-" * 60)
            
            for i, project in enumerate(projects, 1):
                project_type = project.get('projectTypeKey', 'unknown')
                lead = project.get('lead', {}).get('displayName', 'Unknown')
                print(f"{i:2}. {project['name']} ({project['key']}) - {project_type}")
                print(f"    Lead: {lead}")
            
            print("\nEnter project numbers to select (comma-separated, or 'all' for all projects):")
            selection = input("Projects: ").strip()
            
            if selection.lower() == 'all':
                self.selected_projects = [{'key': p['key'], 'name': p['name']} for p in projects]
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',') if x.strip()]
                    self.selected_projects = [
                        {'key': projects[i]['key'], 'name': projects[i]['name']} 
                        for i in indices if 0 <= i < len(projects)
                    ]
                except ValueError:
                    print("Invalid selection. No projects selected.")
                    self.selected_projects = []
        
        print(f"\nSelected {len(self.selected_projects)} project(s):")
        for project in self.selected_projects:
            print(f"  • {project['name']} ({project['key']})")
    
    def filter_boards_by_project(self, boards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter boards to only show those belonging to selected projects"""
        if not self.selected_projects:
            return boards
        
        selected_project_keys = [p['key'] for p in self.selected_projects]
        filtered_boards = []
        
        for board in boards:
            # Check if board belongs to any selected project
            board_project_key = board.get('location', {}).get('projectKey')
            if board_project_key in selected_project_keys:
                filtered_boards.append(board)
        
        return filtered_boards
    
    def select_boards(self):
        """Interactive board selection filtered by selected projects"""
        if not self.selected_projects:
            print("\n⚠️  No projects selected. Please select projects first.")
            return
        
        all_boards = self.get_boards()
        if not all_boards:
            print("No boards found or unable to fetch boards.")
            return
        
        # Filter boards by selected projects
        boards = self.filter_boards_by_project(all_boards)
        
        if not boards:
            print(f"\nNo boards found for selected project(s):")
            for project in self.selected_projects:
                print(f"  • {project['name']} ({project['key']})")
            
            print(f"\nFound {len(all_boards)} total boards, but none match your selected project(s).")
            print("\nOptions:")
            print("1. Add a board by ID (if you know the board ID)")
            print("2. View all boards to find the right one")
            print("3. Skip board selection")
            
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                self._add_board_by_id_interactive()
                return
            elif choice == "2":
                self._select_from_all_boards(all_boards)
                return
            else:
                self.selected_boards = []
                return
        
        print(f"\nFound {len(boards)} board(s) in selected project(s):")
        for project in self.selected_projects:
            print(f"  • {project['name']} ({project['key']})")
        
        print("\nAvailable boards:")
        print("-" * 60)
        
        for i, board in enumerate(boards, 1):
            board_type = board.get('type', 'unknown')
            project_key = board.get('location', {}).get('projectKey', 'N/A')
            print(f"{i:2}. {board['name']} ({board_type}) - Project: {project_key}")
        
        print(f"\nSelect boards (1-{len(boards)}, comma-separated, or 'all' for all boards):")
        selection = input("Boards: ").strip()
        
        if selection.lower() == 'all':
            self.selected_boards = [
                {
                    'id': b['id'], 
                    'name': b['name'], 
                    'type': b.get('type'),
                    'project_key': b.get('location', {}).get('projectKey')
                } 
                for b in boards
            ]
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',') if x.strip()]
                self.selected_boards = [
                    {
                        'id': boards[i]['id'], 
                        'name': boards[i]['name'], 
                        'type': boards[i].get('type'),
                        'project_key': boards[i].get('location', {}).get('projectKey')
                    } 
                    for i in indices if 0 <= i < len(boards)
                ]
            except ValueError:
                print("Invalid selection. No boards selected.")
                self.selected_boards = []
        
        print(f"\nSelected {len(self.selected_boards)} board(s):")
        for board in self.selected_boards:
            print(f"  • {board['name']} ({board['type']}) - Project: {board.get('project_key', 'N/A')}")
    
    def _add_board_by_id_interactive(self):
        """Interactive method to add a board by ID"""
        while True:
            board_id = input("\nEnter board ID (e.g., 21633): ").strip()
            if not board_id:
                print("Please enter a board ID.")
                continue
            
            print(f"Looking up board ID: {board_id}...")
            board = self.get_board_by_id(board_id)
            
            if board:
                board_entry = {
                    'id': board['id'],
                    'name': board['name'],
                    'type': board.get('type', 'unknown'),
                    'project_key': board.get('location', {}).get('projectKey', 'N/A')
                }
                
                # Check if already exists
                existing_ids = [str(b['id']) for b in self.selected_boards]
                if str(board['id']) not in existing_ids:
                    self.selected_boards.append(board_entry)
                    print(f"✅ Added board: {board['name']} (ID: {board['id']})")
                    
                    # Ask if they want to add more
                    add_more = input("Add another board? (y/n): ").strip().lower()
                    if add_more != 'y':
                        break
                else:
                    print(f"⚠️  Board already selected: {board['name']}")
                    break
            else:
                print(f"❌ Board with ID {board_id} not found or not accessible")
                retry = input("Try another board ID? (y/n): ").strip().lower()
                if retry != 'y':
                    break
    
    def _select_from_all_boards(self, all_boards):
        """Allow selection from all boards regardless of project"""
        print(f"\nShowing all {len(all_boards)} boards:")
        print("-" * 80)
        
        # Show boards in pages to avoid overwhelming output
        page_size = 20
        start_idx = 0
        
        while start_idx < len(all_boards):
            end_idx = min(start_idx + page_size, len(all_boards))
            
            print(f"\nBoards {start_idx + 1}-{end_idx} of {len(all_boards)}:")
            for i in range(start_idx, end_idx):
                board = all_boards[i]
                board_type = board.get('type', 'unknown')
                project_key = board.get('location', {}).get('projectKey', 'N/A')
                print(f"{i+1:3}. {board['name']} ({board_type}) - Project: {project_key} - ID: {board['id']}")
            
            if end_idx < len(all_boards):
                action = input(f"\nEnter board numbers (comma-separated), 'next' for more, or 'done': ").strip()
                if action.lower() == 'next':
                    start_idx = end_idx
                    continue
                elif action.lower() == 'done':
                    break
            else:
                action = input(f"\nEnter board numbers to select (comma-separated): ").strip()
            
            # Process selection
            if action and action.lower() not in ['next', 'done']:
                try:
                    indices = [int(x.strip()) - 1 for x in action.split(',') if x.strip()]
                    selected_boards = []
                    
                    for idx in indices:
                        if 0 <= idx < len(all_boards):
                            board = all_boards[idx]
                            board_entry = {
                                'id': board['id'],
                                'name': board['name'],
                                'type': board.get('type', 'unknown'),
                                'project_key': board.get('location', {}).get('projectKey', 'N/A')
                            }
                            selected_boards.append(board_entry)
                    
                    if selected_boards:
                        self.selected_boards.extend(selected_boards)
                        print(f"\nAdded {len(selected_boards)} board(s):")
                        for board in selected_boards:
                            print(f"  • {board['name']} (ID: {board['id']})")
                except ValueError:
                    print("Invalid selection format.")
            
            break
    
    def list_selected_resources(self):
        """Display currently selected projects and boards"""
        print("📋 Current Selection")
        print("=" * 50)
        
        print(f"\nProjects ({len(self.selected_projects)}):")
        if self.selected_projects:
            for project in self.selected_projects:
                print(f"  • {project['name']} ({project['key']})")
        else:
            print("  No projects selected")
        
        print(f"\nBoards ({len(self.selected_boards)}):")
        if self.selected_boards:
            for board in self.selected_boards:
                print(f"  • {board['name']} ({board['type']}) - ID: {board['id']}")
        else:
            print("  No boards selected")
    
    def get_project_issues(self, project_key: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get issues for a specific project"""
        try:
            jql = f"project = {project_key} ORDER BY updated DESC"
            params = {
                'jql': jql,
                'maxResults': max_results,
                'fields': 'summary,status,assignee,priority,created,updated'
            }
            
            # Try API v3 first, fallback to v2
            response = self.session.get(f"{self.base_url}/rest/api/3/search", params=params)
            if response.status_code == 404:
                response = self.session.get(f"{self.base_url}/rest/api/2/search", params=params)
            
            if response.status_code == 200:
                return response.json().get('issues', [])
            else:
                print(f"Failed to fetch issues for {project_key}: {response.status_code}")
                return []
        except requests.RequestException as e:
            print(f"Error fetching issues for {project_key}: {e}")
            return []
    
    def get_board_issues(self, board_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get issues for a specific board using multiple methods"""
        issues = []
        
        # Method 1: Try Agile API
        try:
            params = {'maxResults': max_results}
            response = self.session.get(f"{self.base_url}/rest/agile/1.0/board/{board_id}/issue", params=params)
            if response.status_code == 200:
                issues = response.json().get('issues', [])
                print(f"Found {len(issues)} issues via Agile API")
                return issues
            else:
                print(f"Agile API failed for board issues: {response.status_code}")
        except requests.RequestException as e:
            print(f"Agile API error for board issues: {e}")
        
        # Method 2: Try GreenHopper API
        try:
            response = self.session.get(f"{self.base_url}/rest/greenhopper/1.0/xboard/work/allData/?rapidViewId={board_id}")
            if response.status_code == 200:
                data = response.json()
                issues_data = data.get('issuesData', {}).get('issues', [])
                # Convert GreenHopper format to standard format
                for issue_data in issues_data:
                    issue = {
                        'key': issue_data.get('key'),
                        'id': issue_data.get('id'),
                        'fields': {
                            'summary': issue_data.get('summary'),
                            'status': {
                                'name': issue_data.get('statusName', 'Unknown'),
                                'id': issue_data.get('statusId')
                            },
                            'assignee': {
                                'displayName': issue_data.get('assigneeName', 'Unassigned')
                            } if issue_data.get('assigneeName') else None,
                            'priority': {
                                'name': issue_data.get('priorityName', 'Unknown')
                            },
                            'issuetype': {
                                'name': issue_data.get('typeName', 'Unknown')
                            }
                        }
                    }
                    issues.append(issue)
                print(f"Found {len(issues)} issues via GreenHopper API")
                return issues
            else:
                print(f"GreenHopper API failed for board issues: {response.status_code}")
        except requests.RequestException as e:
            print(f"GreenHopper API error for board issues: {e}")
        
        # Method 3: Fallback - get issues by project if we know the project
        board_info = self.get_board_by_id(str(board_id))
        if board_info:
            project_key = board_info.get('location', {}).get('projectKey')
            if project_key and project_key != 'N/A':
                print(f"Fallback: Getting issues for project {project_key}")
                return self.get_project_issues(project_key, max_results)
        
        return issues
    
    def get_board_issues_by_status(self, board_id: str, statuses: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get board issues grouped by status"""
        if statuses is None:
            statuses = ['In Progress', 'In Review', 'Done', 'To Do', 'New', 'Open']
        
        all_issues = self.get_board_issues(board_id)
        issues_by_status = {}
        
        for status in statuses:
            issues_by_status[status] = []
        
        # Also create a catch-all for unmapped statuses
        issues_by_status['Other'] = []
        
        for issue in all_issues:
            issue_status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
            
            # Try to find matching status (case-insensitive, partial match)
            matched_status = None
            for status in statuses:
                if status.lower() in issue_status.lower() or issue_status.lower() in status.lower():
                    matched_status = status
                    break
            
            if matched_status:
                issues_by_status[matched_status].append(issue)
            else:
                issues_by_status['Other'].append(issue)
        
        # Remove empty categories
        return {k: v for k, v in issues_by_status.items() if v}
    
    def display_board_issues(self, board_id: str, statuses: List[str] = None):
        """Display board issues grouped by status"""
        if statuses is None:
            statuses = ['In Progress', 'In Review', 'Done']
        
        print(f"\n📋 Board Issues (ID: {board_id})")
        print("=" * 80)
        
        issues_by_status = self.get_board_issues_by_status(board_id, statuses + ['To Do', 'New', 'Open'])
        
        if not any(issues_by_status.values()):
            print("No issues found for this board.")
            return
        
        for status in statuses:
            if status in issues_by_status:
                issues = issues_by_status[status]
                print(f"\n🔸 {status.upper()} ({len(issues)} issues)")
                print("-" * 60)
                
                for issue in issues:
                    key = issue.get('key', 'Unknown')
                    summary = issue.get('fields', {}).get('summary', 'No summary')
                    assignee = issue.get('fields', {}).get('assignee')
                    assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
                    priority = issue.get('fields', {}).get('priority', {}).get('name', 'Unknown')
                    issue_type = issue.get('fields', {}).get('issuetype', {}).get('name', 'Unknown')
                    
                    # Truncate long summaries
                    if len(summary) > 60:
                        summary = summary[:57] + "..."
                    
                    print(f"  • {key}: {summary}")
                    print(f"    👤 {assignee_name} | 🏷️  {issue_type} | ⚡ {priority}")
        
        # Show other statuses if any
        other_statuses = [k for k in issues_by_status.keys() if k not in statuses]
        if other_statuses:
            print(f"\n🔸 OTHER STATUSES")
            print("-" * 60)
            for status in other_statuses:
                issues = issues_by_status[status]
                print(f"  {status}: {len(issues)} issues")
    
    def show_board_summary(self):
        """Show summary of selected boards with issues by status"""
        if not self.selected_boards:
            print("No boards selected. Run 'select-boards' first.")
            return
        
        print("📊 Board Summary")
        print("=" * 50)
        
        for board in self.selected_boards:
            board_name = board['name']
            board_id = board['id']
            board_type = board.get('type', 'unknown')
            
            print(f"\n🔸 {board_name} ({board_type}) - ID: {board_id}")
            
            # Get issue counts by status
            issues_by_status = self.get_board_issues_by_status(str(board_id))
            
            if issues_by_status:
                total_issues = sum(len(issues) for issues in issues_by_status.values())
                print(f"   Total issues: {total_issues}")
                
                status_summary = []
                for status, issues in issues_by_status.items():
                    status_summary.append(f"{status}: {len(issues)}")
                
                print(f"   Status breakdown: {', '.join(status_summary)}")
            else:
                print("   No issues found")
    
    def get_issues_by_date_range(self, board_id: str, days_back: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get board issues filtered by date range and categorized by activity"""
        all_issues = self.get_board_issues(board_id)
        # Use timezone-aware datetime to match JIRA dates
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        categorized_issues = {
            'started': [],      # Issues moved to In Progress in past week
            'completed': [],    # Issues moved to Done in past week
            'blocked': [],      # Issues in blocked/off-track states
            'other': []         # All other issues
        }
        
        for issue in all_issues:
            issue_status = issue.get('fields', {}).get('status', {}).get('name', '').lower()
            
            # Parse dates (try multiple formats)
            created_date = self._parse_jira_date(issue.get('fields', {}).get('created'))
            updated_date = self._parse_jira_date(issue.get('fields', {}).get('updated'))
            
            # Categorize based on status and dates
            if any(blocked_term in issue_status for blocked_term in ['blocked', 'impediment', 'hold', 'waiting', 'stuck']):
                categorized_issues['blocked'].append(issue)
            elif any(done_term in issue_status for done_term in ['done', 'closed', 'resolved', 'complete']):
                # Check if completed in the past week
                if updated_date and self._compare_dates(updated_date, cutoff_date):
                    categorized_issues['completed'].append(issue)
                else:
                    categorized_issues['other'].append(issue)
            elif any(progress_term in issue_status for progress_term in ['progress', 'development', 'active', 'working']):
                # Check if started in the past week
                if updated_date and self._compare_dates(updated_date, cutoff_date):
                    categorized_issues['started'].append(issue)
                else:
                    categorized_issues['other'].append(issue)
            else:
                categorized_issues['other'].append(issue)
        
        return categorized_issues
    
    def _compare_dates(self, date1: datetime, date2: datetime) -> bool:
        """Safely compare two datetime objects handling timezone differences"""
        try:
            # If both dates have timezone info, compare directly
            if date1.tzinfo is not None and date2.tzinfo is not None:
                return date1 >= date2
            # If neither has timezone info, compare directly
            elif date1.tzinfo is None and date2.tzinfo is None:
                return date1 >= date2
            # If only one has timezone info, make them compatible
            else:
                # Convert timezone-naive to UTC if the other is timezone-aware
                if date1.tzinfo is None and date2.tzinfo is not None:
                    from datetime import timezone
                    date1 = date1.replace(tzinfo=timezone.utc)
                elif date2.tzinfo is None and date1.tzinfo is not None:
                    from datetime import timezone
                    date2 = date2.replace(tzinfo=timezone.utc)
                return date1 >= date2
        except Exception as e:
            print(f"Date comparison error: {e}")
            return False
    
    def _parse_jira_date(self, date_str: str) -> Optional[datetime]:
        """Parse JIRA date string to datetime object"""
        if not date_str:
            return None
        
        # Common JIRA date formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',  # 2024-01-15T10:30:45.123+0000
            '%Y-%m-%dT%H:%M:%S%z',     # 2024-01-15T10:30:45+0000
            '%Y-%m-%dT%H:%M:%S.%fZ',   # 2024-01-15T10:30:45.123Z
            '%Y-%m-%dT%H:%M:%SZ',      # 2024-01-15T10:30:45Z
            '%Y-%m-%d',                # 2024-01-15
        ]
        
        for fmt in formats:
            try:
                # Handle Z timezone
                clean_date = date_str.replace('Z', '+0000') if date_str.endswith('Z') else date_str
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        
        return None
    
    def generate_weekly_report(self, board_id: str, output_file: str = None, include_summaries: bool = True) -> str:
        """Generate a weekly Kanban board report in markdown format"""
        if output_file is None:
            # Create filename with current date
            current_date = datetime.now().strftime('%Y-%m-%d')
            output_file = f"Weekly_Kanban_Report_{current_date}.md"
        
        # Get board info
        board_info = self.get_board_by_id(str(board_id))
        board_name = board_info.get('name', f'Board {board_id}') if board_info else f'Board {board_id}'
        
        # Get categorized issues
        issues_by_activity = self.get_issues_by_date_range(board_id, 7)
        
        # Generate report content
        report_date = datetime.now().strftime('%B %d, %Y')
        week_start = (datetime.now() - timedelta(days=7)).strftime('%B %d')
        week_end = datetime.now().strftime('%B %d, %Y')
        
        summary_note = "\n*Note: Executive summaries included for each issue.*" if include_summaries else ""
        
        markdown_content = f"""# Weekly Kanban Board Report
**Board:** {board_name}  
**Report Date:** {report_date}  
**Period:** {week_start} - {week_end}  {summary_note}

---

## Started
*Jiras (with links), or other, work started in the past week*

{self._format_issues_for_report(issues_by_activity['started'], 'started', include_summaries)}

---

## Completed
*Jiras (with links), or other, work completed in the past week*

{self._format_issues_for_report(issues_by_activity['completed'], 'completed', include_summaries)}

---

## Blocked / Off-track
*Jiras (with links), or other, work blocked or off-track in the past week*

{self._format_issues_for_report(issues_by_activity['blocked'], 'blocked', include_summaries)}

---

## Risks
*Manager assessment of any risks and mitigation steps*

<!-- TODO: Add risk assessment and mitigation steps -->
- **Risk 1:** [Describe risk]
  - *Mitigation:* [Describe mitigation steps]
- **Risk 2:** [Describe risk]
  - *Mitigation:* [Describe mitigation steps]

---

*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} using Jira Manager*
"""
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return output_file
    
    def _format_issues_for_report(self, issues: List[Dict[str, Any]], category: str, include_summaries: bool = True) -> str:
        """Format issues for markdown report with optional executive summaries"""
        if not issues:
            return "*No items for this period.*\n"
        
        formatted_lines = []
        
        for issue in issues:
            key = issue.get('key', 'Unknown')
            summary = issue.get('fields', {}).get('summary', 'No summary')
            assignee = issue.get('fields', {}).get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            priority = issue.get('fields', {}).get('priority', {}).get('name', 'Unknown')
            status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
            
            # Create JIRA link
            jira_link = f"[{key}]({self.base_url}/browse/{key})"
            
            # Format line based on category
            if category == 'started':
                formatted_lines.append(f"### {jira_link}: {summary}")
                formatted_lines.append(f"**Assignee:** {assignee_name} | **Priority:** {priority}")
            elif category == 'completed':
                formatted_lines.append(f"### ✅ {jira_link}: {summary}")
                formatted_lines.append(f"**Assignee:** {assignee_name}")
            elif category == 'blocked':
                formatted_lines.append(f"### 🚫 {jira_link}: {summary}")
                formatted_lines.append(f"**Status:** {status} | **Assignee:** {assignee_name}")
                formatted_lines.append(f"**Blocking Reason:** *[TODO: Add blocking reason]*")
            
            # Add executive summary if requested
            if include_summaries:
                print(f"🔍 Generating executive summary for {key}...")
                issue_details = self.get_issue_details(key)
                if issue_details:
                    exec_summary = self.generate_executive_summary(issue_details)
                    formatted_lines.append(f"\n**Executive Summary:**")
                    formatted_lines.append(exec_summary)
                    print(f"✅ Summary generated for {key}")
                else:
                    formatted_lines.append(f"\n**Executive Summary:** Unable to fetch detailed information for this issue.")
                    print(f"❌ Failed to fetch details for {key}")
            else:
                print(f"⏭️  Skipping summary for {key} (summaries disabled)")
            
            formatted_lines.append("")  # Add spacing between issues
            
        return '\n'.join(formatted_lines)
    
    def show_project_summary(self):
        """Show summary of selected projects"""
        if not self.selected_projects:
            print("No projects selected. Run 'setup' first.")
            return
        
        print("📊 Project Summary")
        print("=" * 50)
        
        for project in self.selected_projects:
            print(f"\n🔸 {project['name']} ({project['key']})")
            issues = self.get_project_issues(project['key'], 10)
            print(f"   Recent issues: {len(issues)}")
            
            if issues:
                print("   Latest issues:")
                for issue in issues[:3]:
                    summary = issue['fields']['summary'][:50] + "..." if len(issue['fields']['summary']) > 50 else issue['fields']['summary']
                    status = issue['fields']['status']['name']
                    print(f"     • {issue['key']}: {summary} [{status}]")
    
    def show_board_summary(self):
        """Show summary of selected boards"""
        if not self.selected_boards:
            print("No boards selected. Run 'setup' first.")
            return
        
        print("📊 Board Summary")
        print("=" * 50)
        
        for board in self.selected_boards:
            print(f"\n🔸 {board['name']} ({board['type']})")
            issues = self.get_board_issues(str(board['id']), 10)
            print(f"   Issues: {len(issues)}")
            
            if issues:
                print("   Latest issues:")
                for issue in issues[:3]:
                    summary = issue['fields']['summary'][:50] + "..." if len(issue['fields']['summary']) > 50 else issue['fields']['summary']
                    status = issue['fields']['status']['name']
                    print(f"     • {issue['key']}: {summary} [{status}]")

def main():
    parser = argparse.ArgumentParser(description='Jira Project and Board Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    subparsers.add_parser('setup', help='Interactive setup for Jira connection and preferences')
    
    # Select project command
    subparsers.add_parser('select-project', help='Select a project by name or key')
    
    # Select boards command
    subparsers.add_parser('select-boards', help='Select boards from currently selected projects')
    
    # Add board by ID command
    add_board_parser = subparsers.add_parser('add-board', help='Add a specific board by ID')
    add_board_parser.add_argument('board_id', help='Board ID to add (e.g., 21633)')
    
    # List command
    subparsers.add_parser('list', help='List selected projects and boards')
    
    # Project summary
    subparsers.add_parser('projects', help='Show summary of selected projects')
    
    # Board summary
    subparsers.add_parser('boards', help='Show summary of selected boards')
    
    # Board issues command
    board_issues_parser = subparsers.add_parser('board-issues', help='Show issues for a specific board by status')
    board_issues_parser.add_argument('board_id', nargs='?', help='Board ID to show issues for')
    board_issues_parser.add_argument('--status', nargs='*', default=['In Progress', 'In Review', 'Done'], 
                                    help='Status filters (default: In Progress, In Review, Done)')
    
    # All board issues command
    subparsers.add_parser('all-board-issues', help='Show issues for all selected boards')
    
    # Weekly report command
    weekly_report_parser = subparsers.add_parser('weekly-report', help='Generate weekly Kanban board report')
    weekly_report_parser.add_argument('board_id', nargs='?', help='Board ID to generate report for')
    weekly_report_parser.add_argument('--output', '-o', help='Output filename (default: kanban_report_YYYYMMDD.md)')
    weekly_report_parser.add_argument('--days', type=int, default=7, help='Number of days back to analyze (default: 7)')
    weekly_report_parser.add_argument('--no-summary', action='store_true', help='Skip executive summaries for faster generation')
    
    # Test connection
    subparsers.add_parser('test', help='Test Jira connection')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize Jira manager
    jira = JiraManager()
    
    if args.command == 'setup':
        jira.interactive_setup()
    else:
        # Load existing configuration
        if not jira.load_config():
            print("No configuration found. Please run 'setup' first.")
            return
        
        if args.command == 'test':
            if jira.test_connection():
                print("✅ Connection successful!")
            else:
                print("❌ Connection failed!")
        
        elif args.command == 'select-project':
            print("🔍 Project Selection")
            print("=" * 50)
            jira.select_projects()
            jira.save_config()
        
        elif args.command == 'select-boards':
            print("📋 Board Selection")
            print("=" * 50)
            jira.select_boards()
            jira.save_config()
        
        elif args.command == 'add-board':
            print(f"🎯 Adding Board ID: {args.board_id}")
            print("=" * 50)
            board = jira.get_board_by_id(args.board_id)
            if board:
                # Add to selected boards
                board_entry = {
                    'id': board['id'],
                    'name': board['name'],
                    'type': board.get('type', 'unknown'),
                    'project_key': board.get('location', {}).get('projectKey', 'N/A')
                }
                
                # Check if already exists
                existing_ids = [b['id'] for b in jira.selected_boards]
                if str(board['id']) not in [str(id) for id in existing_ids]:
                    jira.selected_boards.append(board_entry)
                    jira.save_config()
                    print(f"✅ Added board: {board['name']} (ID: {board['id']})")
                else:
                    print(f"⚠️  Board already selected: {board['name']}")
            else:
                print(f"❌ Board with ID {args.board_id} not found or not accessible")
        
        elif args.command == 'list':
            jira.list_selected_resources()
        
        elif args.command == 'projects':
            jira.show_project_summary()
        
        elif args.command == 'boards':
            jira.show_board_summary()
        
        elif args.command == 'board-issues':
            if args.board_id:
                jira.display_board_issues(args.board_id, args.status)
            else:
                # Show issues for all selected boards
                if not jira.selected_boards:
                    print("No boards selected. Run 'select-boards' first or specify a board ID.")
                    return
                
                for board in jira.selected_boards:
                    jira.display_board_issues(str(board['id']), args.status)
                    print("\n" + "="*80 + "\n")
        
        elif args.command == 'all-board-issues':
            if not jira.selected_boards:
                print("No boards selected. Run 'select-boards' first.")
                return
            
            for board in jira.selected_boards:
                print(f"\n📋 {board['name']} (ID: {board['id']})")
                jira.display_board_issues(str(board['id']), ['In Progress', 'In Review', 'Done'])
                print("\n" + "="*80)
        
        elif args.command == 'weekly-report':
            if args.board_id:
                board_id = args.board_id
            else:
                # Use first selected board if no board ID provided
                if not jira.selected_boards:
                    print("No boards selected and no board ID provided. Run 'select-boards' first or specify a board ID.")
                    return
                board_id = str(jira.selected_boards[0]['id'])
                print(f"Using selected board: {jira.selected_boards[0]['name']} (ID: {board_id})")
            
            include_summaries = not args.no_summary
            summary_text = "with executive summaries" if include_summaries else "without executive summaries"
            print(f"📊 Generating weekly report for board {board_id} ({summary_text})...")
            
            # Update the method call to include days parameter
            issues_by_activity = jira.get_issues_by_date_range(board_id, args.days)
            
            # Show what we found before generating
            total_issues = len(issues_by_activity['started']) + len(issues_by_activity['completed']) + len(issues_by_activity['blocked'])
            print(f"\n📋 Found {total_issues} issues to include in report:")
            print(f"   Started: {len(issues_by_activity['started'])} items")
            print(f"   Completed: {len(issues_by_activity['completed'])} items")
            print(f"   Blocked: {len(issues_by_activity['blocked'])} items")
            
            if total_issues == 0:
                print("⚠️  No issues found for the specified time period. Report will contain template sections only.")
            
            # Generate report
            print(f"\n🔄 Generating markdown report...")
            output_file = jira.generate_weekly_report(board_id, args.output, include_summaries)
            
            print(f"\n✅ Weekly report generated successfully!")
            print(f"📄 File: {output_file}")
            print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if include_summaries and total_issues > 0:
                print("📝 Executive summaries included for all issues")
            elif total_issues > 0:
                print("⚡ Quick report generated (no executive summaries)")

if __name__ == '__main__':
    main()