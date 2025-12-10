import os
import re
import json
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'app.log')
ACCESS_CSV = os.path.join(BASE_DIR, 'logs', 'access_log.csv')
ACTION_CSV = os.path.join(BASE_DIR, 'logs', 'action_log.csv')

def parse_log_line(line):
    # Log format: YYYY-MM-DD HH:MM:SS,mmm - LEVEL - TYPE: {json}
    # Example: 2025-12-08 10:21:14,764 - INFO - ACCESS_LOG: {...}
    
    # Extract timestamp and message using regex
    match = re.search(r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3})\s-\s\w+\s-\s(\w+_LOG):\s(.*)$', line)
    if not match:
        return None
    
    timestamp_str = match.group(1)
    log_type = match.group(2)
    json_str = match.group(3)
    
    try:
        data = json.loads(json_str)
        return {
            'timestamp': timestamp_str,
            'type': log_type,
            'data': data
        }
    except json.JSONDecodeError:
        return None

def main():
    if not os.path.exists(LOG_FILE):
        print(f"Log file not found: {LOG_FILE}")
        return

    access_logs = []
    action_logs = []

    print(f"Reading log file: {LOG_FILE}...")
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = parse_log_line(line.strip())
            if not parsed:
                continue
            
            if parsed['type'] == 'ACCESS_LOG':
                # Flatten structure for CSV
                row = {
                    'timestamp': parsed['timestamp'],
                    'ip': parsed['data'].get('ip'),
                    'user_id': parsed['data'].get('user_id', ''),
                    'method': parsed['data'].get('method'),
                    'path': parsed['data'].get('path'),
                    'status': parsed['data'].get('status'),
                    'duration_sec': parsed['data'].get('duration_sec'),
                    'cpu_percent': parsed['data'].get('cpu_percent'),
                    'search_query': parsed['data'].get('search_query', ''),
                    'search_mode': parsed['data'].get('search_mode', '')
                }
                access_logs.append(row)
            
            elif parsed['type'] == 'ACTION_LOG':
                details = parsed['data'].get('details', {})
                # Stringify details if it's a dict/list to fit in one CSV cell
                if isinstance(details, (dict, list)):
                    details_str = json.dumps(details, ensure_ascii=False)
                else:
                    details_str = str(details)

                row = {
                    'timestamp': parsed['timestamp'],
                    'user_id': parsed['data'].get('user_id', ''),
                    'action': parsed['data'].get('action'),
                    'url': parsed['data'].get('url'),
                    'details': details_str
                }
                action_logs.append(row)

    # Write Access Logs
    if access_logs:
        fieldnames = ['timestamp', 'ip', 'user_id', 'method', 'path', 'status', 'duration_sec', 'cpu_percent', 'search_query', 'search_mode']
        with open(ACCESS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(access_logs)
        print(f"Generated {ACCESS_CSV} ({len(access_logs)} records)")
    else:
        print("No access logs found.")

    # Write Action Logs
    if action_logs:
        fieldnames = ['timestamp', 'user_id', 'action', 'url', 'details']
        with open(ACTION_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(action_logs)
        print(f"Generated {ACTION_CSV} ({len(action_logs)} records)")
    else:
        print("No action logs found.")

if __name__ == '__main__':
    main()
