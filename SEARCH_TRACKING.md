# Search Tracking Agent Documentation

## Overview
The **searchTrackAgent** automatically tracks when users search for passwords using the PassProtect system. This provides valuable insights into user behavior and enables the "Recent Searches" feature in the dashboard.

## How It Works

### 1. Automatic Logging
Every time a user searches for a password using:
- `read_password` tool - Logs the company name being searched
- `read_records` tool - Logs as "[LIST_ALL_RECORDS]"

The system automatically records:
- **search_date**: When the search occurred
- **companyName**: What company/service was searched for
- **search_by_user**: The user ID who performed the search

### 2. Database Schema
```sql
Table: searchlog
Columns:
- id (INT, PRIMARY KEY, AUTO_INCREMENT)
- search_date (DATETIME)
- companyName (VARCHAR(45))
- search_by_user (VARCHAR(45))
```

### 3. Dashboard Integration
The dashboard displays the **5 most recent searches** for the logged-in user:
- Shows company name
- Shows last search date/time
- Only displays actual company searches (excludes "[LIST_ALL_RECORDS]")
- Automatically updated each time the dashboard is viewed

## MCP Tool: get_recent_searches

### Description
Retrieves the most recent password searches for the authenticated user.

### Parameters
- `limit` (integer, optional): Maximum number of results to return (default: 10)

### Returns
JSON array of recent searches:
```json
[
  {
    "companyName": "Gmail",
    "last_searched": "2026-01-19 14:30:00"
  },
  {
    "companyName": "Netflix",
    "last_searched": "2026-01-19 10:15:00"
  }
]
```

### Security
- Only returns searches for the authenticated user
- Filters out system searches like "[LIST_ALL_RECORDS]"
- Groups by company name to avoid duplicates

## Implementation Details

### Files Modified

#### 1. mcp_server.py
- Added `log_search()` function to record searches
- Modified `read_password` to log company searches
- Modified `read_records` to log list operations
- Added `get_recent_searches` tool

#### 2. app.py
- Added `fetch_recent_searches()` async function
- Updated `/dashboard` route to fetch and pass recent searches

#### 3. templates/dashboard.html
- Added "Recent Searches" card
- Displays recent searches with timestamps

## Setup Instructions

### 1. Create the searchlog table
Run the SQL script:
```bash
mysql -u root -p quaziinfodb < create_searchlog_table.sql
```

Or execute directly in MySQL:
```sql
CREATE TABLE IF NOT EXISTS searchlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_date DATETIME NOT NULL,
    companyName VARCHAR(45) NOT NULL,
    search_by_user VARCHAR(45) NOT NULL,
    INDEX idx_user_date (search_by_user, search_date DESC),
    INDEX idx_company (companyName)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. Test the Feature
1. Login to PassProtect
2. Go to Chat interface
3. Search for some passwords (e.g., "Show me Gmail password")
4. Return to Dashboard
5. Verify "Recent Searches" card shows your searches

## Privacy & Data Management

### Data Retention
Currently, all searches are retained indefinitely. Consider adding:
- Automatic cleanup of old records (e.g., older than 90 days)
- User preference to disable search tracking
- Admin tools to manage search logs

### Example Cleanup Query
```sql
DELETE FROM searchlog 
WHERE search_date < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

## Future Enhancements

1. **Analytics Dashboard**
   - Most frequently searched companies
   - Search trends over time
   - Peak usage times

2. **Quick Access**
   - Click recent search to immediately retrieve password
   - Pin favorite searches

3. **Search Suggestions**
   - Auto-complete based on search history
   - Suggest related services

4. **Privacy Controls**
   - Toggle search tracking on/off
   - Clear search history option
   - Incognito search mode

## Troubleshooting

### Recent searches not appearing?
- Verify searchlog table exists: `SHOW TABLES LIKE 'searchlog';`
- Check table permissions for database user
- Verify searches are being logged: `SELECT * FROM searchlog ORDER BY search_date DESC LIMIT 10;`

### Search logging errors?
- Check console output for error messages
- Ensure USER_ID environment variable is being passed to MCP server
- Verify database connection in mcp_server.py

### Dashboard shows "No recent searches"?
- Perform a password search in the chat interface first
- Refresh the dashboard
- Check browser console for JavaScript errors
