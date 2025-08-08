#!/usr/bin/env python3

import sys
import os
import argparse
import threading
import time
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS
from functools import wraps

# Import our modules
from attendance_tracker import AttendanceTracker
from database import AttendanceDatabase
from auth import AuthManager

# Flask app setup
app = Flask(__name__)
app.secret_key = 'wifi_attendance_tracker_secret_key_2025'  # Change this in production
CORS(app)

# Global variables
tracker = None
db = None
auth = None
latest_events = []
is_monitoring = False

# Dashboard password (can be changed via settings)
DASHBOARD_PASSWORD = "admin123"

def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def check_dashboard_password(password):
    """Check if the provided password matches the dashboard password."""
    return password == DASHBOARD_PASSWORD


def check_requirements():
    """Check if the system meets requirements."""
    issues = []
    
    # Check if config file exists
    if not os.path.exists('config.json'):
        issues.append("config.json file not found")
    
    # Check if employees file exists
    if not os.path.exists('employees.json'):
        issues.append("employees.json file not found")
    

    return issues

def initialize_system():
    """Initialize the attendance tracking system."""
    global tracker, db, auth
    
    # Initialize database first
    db = AttendanceDatabase()
    
    # Initialize authentication manager
    auth = AuthManager(db)
    
    # Initialize tracker
    tracker = AttendanceTracker()
    
    # Sync employees from JSON to database
    tracker.sync_employees_from_json()

def monitoring_loop():
    """Background monitoring loop."""
    global latest_events, is_monitoring
    
    while is_monitoring:
        try:
            events = tracker.scan_once()
            
            # Keep only the latest 50 events for the web interface
            latest_events.extend(events)
            latest_events = latest_events[-50:]  # Keep only last 50 events
            
            time.sleep(tracker.scan_interval)
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            time.sleep(5)  # Wait before retrying

# Web Interface Routes
@app.route('/')
def index():
    """Redirect to login page."""
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """Serve the login page."""
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@login_required
@app.route('/api/login', methods=['POST'])
def login():
    """Handle login authentication."""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if check_dashboard_password(password):
            session['logged_in'] = True
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Login error occurred'})

@app.route('/logout')
def logout():
    """Handle logout."""
    session.pop('logged_in', None)
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Serve the main dashboard page."""
    return render_template('index.html')

@login_required
@app.route('/api/status')
@login_required
def get_status():
    """Get current system status."""
    return jsonify({
        'is_monitoring': is_monitoring,
        'employee_count': len(tracker.employees) if tracker else 0,
        'scan_interval': tracker.scan_interval if tracker else 60,
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'office_timeout': f"{tracker.office_timeout_hour:02d}:{tracker.office_timeout_minute:02d}" if tracker else "17:00"
    })

@login_required
@app.route('/api/employees')
@login_required
def get_employees():
    """Get all employees and their current status."""
    if not tracker:
        return jsonify([])
    
    search_query = request.args.get('search', '').strip()
    
    status = tracker.get_current_status()
    employees = []
    
    for mac, info in status.items():
        # Get employee picture from database
        employee_info = db.get_employee_by_mac(mac)
        picture_path = employee_info.get('picture_path') if employee_info else None
        
        employee_data = {
            'name': info['name'],
            'mac': info['mac'],
            'is_present': info['is_present'],
            'status': info['status'],
            'last_seen': info['last_seen'],
            'time_in': info['time_in'],
            'picture': picture_path
        }
        
        # Apply search filter if provided
        if search_query:
            if (search_query.lower() in info['name'].lower() or 
                search_query.lower() in info['mac'].lower()):
                employees.append(employee_data)
        else:
            employees.append(employee_data)
    
    return jsonify(employees)

@app.route('/api/events')
@login_required
def get_recent_events():
    """Get recent attendance events."""
    global latest_events
    
    # Convert events to JSON-serializable format
    events_data = []
    for mac, event_type, timestamp in latest_events:
        employee_name = tracker.get_employee_name(mac) if tracker else f"Unknown ({mac})"
        events_data.append({
            'name': employee_name,
            'mac': mac,
            'event_type': event_type,
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': get_time_ago(timestamp)
        })
    
    # Sort by timestamp (most recent first)
    events_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify(events_data)

@login_required
@app.route('/api/attendance_events')
def get_attendance_events():
    """Get attendance events from database."""
    if not db:
        return jsonify([])
    
    date_filter = request.args.get('date')
    limit = int(request.args.get('limit', 50))
    
    events = db.get_attendance_events(date=date_filter, limit=limit)
    
    # Add time_ago field
    for event in events:
        timestamp = datetime.fromisoformat(event['timestamp'])
        event['time_ago'] = get_time_ago(timestamp)
    
    return jsonify(events)

@login_required
@app.route('/api/daily_summary')
def get_daily_summary():
    """Get daily attendance summary."""
    if not db:
        return jsonify([])
    
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    summary = db.get_daily_summary(date_str)
    
    # Format durations for display
    for employee in summary:
        employee['total_break_formatted'] = format_duration(employee['total_break_duration'])
        employee['total_work_formatted'] = format_duration(employee['total_work_duration'])
    
    return jsonify(summary)

@login_required
@app.route('/api/summary_stats')
def get_summary_stats():
    """Get summary statistics for the dashboard."""
    if not db:
        return jsonify({})
    
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    summary = db.get_daily_summary(date_str)
    
    stats = {
        'total_employees': len(summary),
        'present_count': len([emp for emp in summary if emp['status'] == 'Present']),
        'absent_count': len([emp for emp in summary if emp['status'] == 'Absent']),
        'on_break_count': len([emp for emp in summary if emp['status'] == 'On Break']),
        'timed_out_count': len([emp for emp in summary if emp['status'] == 'Timed Out']),
        'total_events': len(db.get_attendance_events(date=date_str, limit=1000))
    }
    
    return jsonify(stats)

@login_required
@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    """Start the attendance monitoring."""
    global is_monitoring
    
    if not is_monitoring:
        is_monitoring = True
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
        return jsonify({'success': True, 'message': 'Monitoring started'})
    else:
        return jsonify({'success': False, 'message': 'Monitoring already running'})

@login_required
@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """Stop the attendance monitoring."""
    global is_monitoring
    is_monitoring = False
    return jsonify({'success': True, 'message': 'Monitoring stopped'})

@login_required
@app.route('/api/export_csv')
def export_csv():
    """Export daily summary to CSV."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not available'})
    
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        db.export_daily_summary_to_csv(date_str)
        return jsonify({'success': True, 'message': f'CSV exported for {date_str}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Export failed: {str(e)}'})

@login_required
@app.route('/api/add_employee', methods=['POST'])
def add_employee():
    """Add a new employee with password authentication."""
    if not auth or not db:
        return jsonify({'success': False, 'message': 'Authentication system not available'})
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ['name', 'mac', 'password']):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Authenticate admin password
        if not auth.authenticate_admin(data['password']):
            return jsonify({'success': False, 'message': 'Invalid admin password'})
        
        # Validate MAC address format
        mac_address = data['mac'].lower().strip()
        if not is_valid_mac_format(mac_address):
            return jsonify({'success': False, 'message': 'Invalid MAC address format. Use: aa-bb-cc-dd-ee-ff'})
        
        # Add employee to database
        success = db.add_employee(
            name=data['name'].strip(),
            mac_address=mac_address,
            picture_path=data.get('picture', '').strip() or None
        )
        
        if success:
            # Also add to employees.json for persistence
            update_employees_json(data['name'].strip(), mac_address, data.get('picture', '').strip())
            
            # Reload tracker employees
            tracker.employees = tracker.load_employees()
            tracker._initialize_employee_states()
            
            return jsonify({'success': True, 'message': 'Employee added successfully'})
        else:
            return jsonify({'success': False, 'message': 'Employee with this MAC address already exists'})
            
    except Exception as e:
        print(f"Error adding employee: {e}")
        return jsonify({'success': False, 'message': f'Error adding employee: {str(e)}'})

@login_required
@app.route('/api/search_employees')
def search_employees():
    """Search employees by name or MAC address."""
    if not db:
        return jsonify([])
    
    search_query = request.args.get('q', '').strip()
    
    if not search_query:
        return jsonify([])
    
    employees = db.get_all_employees(search_query=search_query)
    
    # Format response
    result = []
    for emp in employees:
        result.append({
            'id': emp['id'],
            'name': emp['name'],
            'mac_address': emp['mac_address'],
            'picture_path': emp['picture_path'],
            'created_at': emp['created_at']
        })
    
    return jsonify(result)

@app.route('/api/delete_employee', methods=['POST'])
@login_required
def delete_employee():
    """Delete an employee with password authentication."""
    if not auth or not db:
        return jsonify({'success': False, 'message': 'Authentication system not available'})
    
    try:
        data = request.get_json()
        
        # Validate required fields - now accepting either employee_id or mac_address
        if not all(key in data for key in ['password']) or not any(key in data for key in ['employee_id', 'mac_address']):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Authenticate admin password
        if not auth.authenticate_admin(data['password']):
            return jsonify({'success': False, 'message': 'Invalid admin password'})
        
        # Get employee info - handle both employee_id and mac_address
        if 'employee_id' in data and isinstance(data['employee_id'], int):
            employee = db.get_employee_by_id(data['employee_id'])
        else:
            # If employee_id is actually a MAC address or mac_address is provided
            mac_address = data.get('employee_id', data.get('mac_address'))
            employee = db.get_employee_by_mac(mac_address)
        
        if not employee:
            return jsonify({'success': False, 'message': 'Employee not found'})
        
        # Delete employee from database
        success = db.delete_employee(employee['id'])
        
        if success:
            # Remove from employees.json for persistence
            remove_employee_from_json(employee['mac_address'])
            
            # Reload tracker employees
            tracker.employees = tracker.load_employees()
            tracker._initialize_employee_states()
            
            return jsonify({'success': True, 'message': f'Employee {employee["name"]} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete employee'})
            
    except Exception as e:
        print(f"Error deleting employee: {e}")
        return jsonify({'success': False, 'message': f'Error deleting employee: {str(e)}'})

@app.route('/api/modify_employee', methods=['POST'])
@login_required
def modify_employee():
    """Modify employee information with password authentication."""
    if not auth or not db:
        return jsonify({'success': False, 'message': 'Authentication system not available'})
    
    try:
        data = request.get_json()
        
        # Validate required fields - now accepting either employee_id or mac_address
        if not all(key in data for key in ['password']) or not any(key in data for key in ['employee_id', 'mac_address']):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Authenticate admin password
        if not auth.authenticate_admin(data['password']):
            return jsonify({'success': False, 'message': 'Invalid admin password'})
        
        # Get current employee info - handle both employee_id and mac_address
        if 'employee_id' in data and isinstance(data['employee_id'], int):
            employee = db.get_employee_by_id(data['employee_id'])
        else:
            # If employee_id is actually a MAC address or mac_address is provided
            mac_address = data.get('employee_id', data.get('mac_address'))
            employee = db.get_employee_by_mac(mac_address)
        
        if not employee:
            return jsonify({'success': False, 'message': 'Employee not found'})
        
        # Prepare update data
        update_data = {}
        if 'name' in data and data['name'].strip():
            update_data['name'] = data['name'].strip()
        if 'mac_address' in data and data['mac_address'].strip():
            new_mac = data['mac_address'].lower().strip()
            if not is_valid_mac_format(new_mac):
                return jsonify({'success': False, 'message': 'Invalid MAC address format. Use: aa-bb-cc-dd-ee-ff'})
            update_data['mac_address'] = new_mac
        if 'picture_path' in data:
            update_data['picture_path'] = data['picture_path'].strip() or None
        
        if not update_data:
            return jsonify({'success': False, 'message': 'No valid fields to update'})
        
        # Update employee in database
        success = db.update_employee(employee['id'], **update_data)
        
        if success:
            # Update employees.json for persistence
            update_employee_in_json(employee['mac_address'], update_data)
            
            # Reload tracker employees
            tracker.employees = tracker.load_employees()
            tracker._initialize_employee_states()
            
            return jsonify({'success': True, 'message': 'Employee updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update employee'})
            
    except Exception as e:
        print(f"Error modifying employee: {e}")
        return jsonify({'success': False, 'message': f'Error modifying employee: {str(e)}'})

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    """Change the admin password."""
    if not auth:
        return jsonify({'success': False, 'message': 'Authentication system not available'})
    
    try:
        data = request.get_json()
        
        if not all(key in data for key in ['currentPassword', 'newPassword']):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        success = auth.change_admin_password(data['currentPassword'], data['newPassword'])
        
        if success:
            return jsonify({'success': True, 'message': 'Password changed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Current password is incorrect'})
            
    except Exception as e:
        print(f"Error changing password: {e}")
        return jsonify({'success': False, 'message': f'Error changing password: {str(e)}'})

def is_valid_mac_format(mac):
    """Validate MAC address format."""
    if not mac:
        return False
    
    # Check for correct format: aa-bb-cc-dd-ee-ff
    parts = mac.split('-')
    if len(parts) != 6:
        return False
    
    for part in parts:
        if len(part) != 2:
            return False
        try:
            int(part, 16)
        except ValueError:
            return False
    
    return True

def update_employees_json(name, mac_address, picture_path):
    """Update the employees.json file with new employee."""
    try:
        # Read existing employees
        employees = []
        if os.path.exists('employees.json'):
            with open('employees.json', 'r') as f:
                employees = json.load(f)
        
        # Check if employee already exists
        for emp in employees:
            if emp.get('mac_address') == mac_address:
                return  # Already exists
        
        # Add new employee
        new_employee = {
            'name': name,
            'mac_address': mac_address,
            'picture': picture_path if picture_path else f"static/img/{name.lower().replace(' ', '_')}.jpg"
        }
        employees.append(new_employee)
        
        # Write back to file
        with open('employees.json', 'w') as f:
            json.dump(employees, f, indent=2)
            
    except Exception as e:
        print(f"Error updating employees.json: {e}")

def remove_employee_from_json(mac_address):
    """Remove an employee from employees.json file."""
    try:
        if not os.path.exists('employees.json'):
            return
        
        # Read existing employees
        with open('employees.json', 'r') as f:
            employees = json.load(f)
        
        # Remove employee with matching MAC address
        employees = [emp for emp in employees if emp.get('mac_address') != mac_address]
        
        # Write back to file
        with open('employees.json', 'w') as f:
            json.dump(employees, f, indent=2)
            
    except Exception as e:
        print(f"Error removing employee from employees.json: {e}")

def update_employee_in_json(old_mac_address, update_data):
    """Update an employee in employees.json file."""
    try:
        if not os.path.exists('employees.json'):
            return
        
        # Read existing employees
        with open('employees.json', 'r') as f:
            employees = json.load(f)
        
        # Find and update employee
        for emp in employees:
            if emp.get('mac_address') == old_mac_address:
                if 'name' in update_data:
                    emp['name'] = update_data['name']
                if 'mac_address' in update_data:
                    emp['mac_address'] = update_data['mac_address']
                if 'picture_path' in update_data:
                    emp['picture'] = update_data['picture_path'] or f"static/img/{emp['name'].lower().replace(' ', '_')}.jpg"
                break
        
        # Write back to file
        with open('employees.json', 'w') as f:
            json.dump(employees, f, indent=2)
            
    except Exception as e:
        print(f"Error updating employee in employees.json: {e}")

def get_time_ago(timestamp):
    """Get human-readable time difference."""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS."""
    if seconds is None:
        return "00:00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def run_console_mode():
    """Run the application in console mode (no web interface)."""
    print("Starting in console mode...")
    print("Press Ctrl+C to stop\n")
    
    initialize_system()
    
    try:
        tracker.start_monitoring()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

def run_web_mode(port=5000):
    """Run the application with web interface."""
    print("Starting integrated web interface mode...")
    
    # Initialize the system
    initialize_system()
    
    print(f"\nWeb interface will be available at:")
    print(f"  Local:    http://localhost:{port}")
    print(f"  Network:  http://0.0.0.0:{port}")
    print("\nPress Ctrl+C to stop\n")
    
    # Note about admin privileges
    print("Note: This application attempts to run without administrator privileges.")
    print("If network scanning fails, you may need to run as administrator/root.")
    print("Employee management features work regardless of privilege level.\n")
    
    # Start monitoring automatically
    global is_monitoring
    is_monitoring = True
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        is_monitoring = False
        sys.exit(0)

def show_status():
    """Show current system status."""
    print("System Status:")
    print("=" * 50)
    
    # Initialize system for status check
    initialize_system()
    
    # Check database
    try:
        employees = db.get_all_employees()
        print(f"Database: Connected")
        print(f"Employees: {len(employees)}")
        
        for emp in employees:
            picture_info = f" (Picture: {emp['picture_path']})" if emp['picture_path'] else ""
            print(f"  - {emp['name']} ({emp['mac_address']}){picture_info}")
        
        # Show recent events
        recent_events = db.get_attendance_events(limit=5)
        print(f"\nRecent Events: {len(recent_events)}")
        for event in recent_events[-5:]:
            print(f"  {event['timestamp']}: {event['employee_name']} - {event['event_type']}")
            
        # Show today's summary
        today = datetime.now().strftime('%Y-%m-%d')
        summary = db.get_daily_summary(today)
        print(f"\nToday's Summary ({today}):")
        for emp in summary:
            print(f"  {emp['name']}: {emp['status']} | In: {emp['time_in'] or 'N/A'} | Out: {emp['time_out'] or 'N/A'}")
            
    except Exception as e:
        print(f"Database: Error - {e}")
    
    # Check config
    try:
        import json
        with open('config.json', 'r') as f:
            config = json.load(f)
        print(f"\nConfiguration:")
        print(f"  Scan Interval: {config.get('scan_interval_seconds', 60)} seconds")
        print(f"  Web Port: {config.get('web_port', 5000)}")
        print(f"  Office Timeout: {config.get('office_timeout_hour', 17)}:{config.get('office_timeout_minute', 0):02d}")
    except Exception as e:
        print(f"\nConfiguration: Error - {e}")
    
    # Check employees.json
    try:
        with open('employees.json', 'r') as f:
            employees_json = json.load(f)
        print(f"\nEmployees JSON File:")
        print(f"  Configured Employees: {len(employees_json)}")
        for emp in employees_json:
            print(f"  - {emp.get('name', 'Unknown')} ({emp.get('mac_address', 'Unknown')})")
    except Exception as e:
        print(f"\nEmployees JSON: Error - {e}")
    
    # Check authentication
    try:
        print(f"\nAuthentication:")
        print(f"  Admin Password: {auth.get_current_admin_password_hint()}")
    except Exception as e:
        print(f"\nAuthentication: Error - {e}")

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description='WiFi-Based Attendance & Break Tracker - Employee Management Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run with web interface (default)
  python main.py --console          # Run in console mode only
  python main.py --status           # Show system status
  python main.py --port 8080        # Run web interface on port 8080
  
New Features:
  - Employee management (add, search, password protection)
  - Non-admin operation (where possible)
  - Enhanced web interface with employee pictures
  - Separate employees.json for better data management
  - Password-protected employee addition (default: 1122)
  
For more information, see README.md
        """
    )
    
    parser.add_argument(
        '--console', 
        action='store_true',
        help='Run in console mode without web interface'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show system status and exit'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port for web interface (default: 5000)'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Check requirements
    issues = check_requirements()
    if issues:
        print("⚠️  System Requirements Issues:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        
        # Create missing files with defaults
        if "config.json file not found" in str(issues):
            print("Creating default config.json...")
            default_config = {
                "scan_interval_seconds": 60,
                "web_port": 5000,
                "office_timeout_hour": 17,
                "office_timeout_minute": 0
            }
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=2)
        
        if "employees.json file not found" in str(issues):
            print("Creating default employees.json...")
            default_employees = [
                {
                    "name": "Sample Employee",
                    "mac_address": "aa-bb-cc-dd-ee-ff",
                    "picture": "static/img/sample.jpg"
                }
            ]
            with open('employees.json', 'w') as f:
                json.dump(default_employees, f, indent=2)
        
        print("Default files created. Please edit them with your actual data.\n")
    
    # Handle different modes
    if args.status:
        show_status()
        return
    
    if args.console:
        run_console_mode()
    else:
        run_web_mode(args.port)

if __name__ == "__main__":
    main()

