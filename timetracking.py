from datetime import datetime, date, timedelta
import os
import json
import base64
import requests
import math
import dateutil.tz

class Jira:
    def __init__(self, id, url, email, api_key, auth_type):
        self.id = id
        self.url = url
        self.email = email
        self.api_key = api_key
        self.auth_type = auth_type

class Project:
    def __init__(self, key, jira):
        self.key = key
        self.jira = jira
        

def create_worklog_object(timeSpentSeconds, started, comment):
    data = {}
    data['timeSpentSeconds'] = timeSpentSeconds
    data['started'] = started
    data['comment'] = comment
    return data
def get_project_from_ticket(key_string, project_list) -> Project:
    for project in project_list:
        if key_string.startswith(project.key):
            return project
    return None
def reformat_toggl_date(date: str) -> str:
    return date.split('+')[0]+".000+0000"
def create_basic_authorization(username, password) -> str:
    token = f"{username}:{password}"
    encoded_token = base64.b64encode(token.encode('utf-8')).decode('utf-8')
    return f"Basic {encoded_token}"
def create_bearer_authorization(password) -> str:
    token = f"{password}"
    return f'Bearer {token}'
def create_headers(auth_type, username, password):
    if auth_type == "bearer":
        auth_header = create_bearer_authorization(password)
    else:
        auth_header = create_basic_authorization(username, password)
    result = {'Content-Type': 'application/json'}
    result['Authorization'] = auth_header
    return result
def get_entry_duration(duration: int, is_round_up: bool) -> int:
    if (is_round_up):
        return math.ceil(duration / 900) * 900
    return duration
def get_entry_comment(description: str) -> str:
    parts = description.split(" - ", 1)
    if len(parts) > 1:
        return parts[1]
    return ""
def get_local_time_offset() -> timedelta:
    # get the current time in your local timezone
    local_time = datetime.now()
    # get the UTC offset of your local timezone
    local_tz = dateutil.tz.tzlocal()
    result = local_tz.utcoffset(local_time)
    if not result:
        result = timedelta()
    return result
def convert_local_time_to_utc(datetime: datetime) -> datetime:
    return datetime - get_local_time_offset()

current_dir = os.path.dirname(os.path.abspath(__file__))
settings_file = os.path.join(current_dir, 'timetrack-settings.json')
with open(settings_file) as f:
    json_data = f.read()

settings = json.loads(json_data)
# Create Jira instances
jiras = {}
for jira_data in settings['jiras']:
    jira = Jira(jira_data['id'], jira_data['url'], jira_data['email'], jira_data['api_key'], jira_data['auth_type'])
    jiras[jira.id] = jira

# Create Project instances
projects = []
for project_data in settings['projects']:
    jira_id = project_data['jiraId']
    jira = jiras[jira_id]
    project = Project(project_data['key'], jira)
    projects.append(project)

toggl_headers = create_headers("basic", settings['toggl_api_key'], "api_token")

# Enter dates and convert them to UTC
print(F"Enter the dates in this format: {date.today().strftime('%Y-%m-%d')}")
start_date_input = input("Start date (or press enter for todays date): ")
end_date_input = input("End date (or press enter for todays date): ")
if not start_date_input:
    start_date_input = date.today().strftime('%Y-%m-%d')
if not end_date_input:
    end_date_input = date.today().strftime('%Y-%m-%d')
start_date_input = F"{start_date_input}T00:00:00"
end_date_input = F"{end_date_input}T23:59:59"
start_date = convert_local_time_to_utc(datetime.strptime(start_date_input, "%Y-%m-%dT%H:%M:%S"))
end_date = convert_local_time_to_utc(datetime.strptime(end_date_input, "%Y-%m-%dT%H:%M:%S"))

# Get Toggl time entries
toggl_params = {'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'), 'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
response = requests.get(settings['toggl_api_endpoint'], headers=toggl_headers, params=toggl_params)
time_entries = []
if response.ok:
    time_entries = response.json()
else:
    print("Toggl API returned an error")

tickets = []
for entry in time_entries:
    project = get_project_from_ticket(entry['description'], projects)
    if not project:
        print(F"Project not found for entry: {entry['description']}")
        continue
    ticket = entry['description'].split()[0]
    tickets.append(ticket)
    duration = get_entry_duration(entry['duration'], settings['roundTimeUp'])
    comment = get_entry_comment(entry['description'])
    entry_startdate = reformat_toggl_date(entry['start'])

    jira_issue_endpoint = f"{project.jira.url}rest/api/2/issue/{ticket}/worklog"
    jira_headers = create_headers(project.jira.auth_type, project.jira.email, project.jira.api_key)
    jira_body = create_worklog_object(duration, entry_startdate, comment)

    response = requests.post(jira_issue_endpoint, headers=jira_headers, json=jira_body)
    if response.status_code == 200 or response.status_code == 201:
        print(F"Added worklog with duration {duration}s and startDate {entry_startdate} to ticket {ticket}")
        continue
    elif response.status_code == 404:
        print(F"Skipping ticket {ticket}")
        continue
    else:
        print(F"Error: status code: {response.status_code} request body:{response.request.body} request endpoint: {response.request.url} response:{response.json()}")
input("Press enter to exit")
