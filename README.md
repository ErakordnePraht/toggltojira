# TogglToJira
Quick hack job to export Toggl entries to Jira

## How to install

**Installing required packages:**

```
pip install -r requirements.txt
```

## Setup

Create your own timetrack-settings.json file using timetrack-settings.json.example as a template.

- roundTimeUp - Rounds up the entries to the nearest 15min
- mergeEntries - Merges all toggl entries with the same description (rounding happens after the merge)
