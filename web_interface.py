from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import threading
import time
from datetime import datetime, date, timedelta
from attendance_tracker import AttendanceTracker
from database import AttendanceDatabase

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables
tracker = None
db = None
latest_events = []
is_monitoring = False

def initialize_system():
    """Initialize the attendance tracking system."""
    global tracker, db
    tracker = AttendanceTracker()
    db = AttendanceDatabase()
    
    # Sync employees from config to database
    db.sync_employees_from_config()

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

@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current system status."""
    return jsonify({
        'is_monitoring': is_monitoring,
        'employee_count': len(tracker.employees) if tracker else 0,
        'scan_interval': tracker.scan_interval if tracker else 60,
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'office_timeout': f"{tracker.office_timeout_hour:02d}:{tracker.office_timeout_minute:02d}" if tracker else "17:00"
    })

@app.route('/api/employees')
def get_employees():
    """Get all employees and their current status."""
    if not tracker:
        return jsonify([])
    
    status = tracker.get_current_status()
    employees = []
    
    for mac, info in status.items():
        employees.append({
            'name': info['name'],
            'mac': info['mac'],
            'is_present': info['is_present'],
            'status': info['status'],
            'last_seen': info['last_seen'],
            'time_in': info['time_in']
        })
    
    return jsonify(employees)

@app.route('/api/events')
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

@app.route('/api/daily_summary')
def get_daily_summary():
    """Get daily attendance summary."""
    if not db:
        return jsonify([])
    
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    summary = db.get_daily_summary(date_str)
    
    # Format durations for display
    for employee in summary:
        employee['total_break_formatted'] = format_duration(employee['total_break_duration'])
        employee['total_work_formatted'] = format_duration(employee['total_work_duration'])
    
    return jsonify(summary)

@app.route('/api/summary_stats')
def get_summary_stats():
    """Get summary statistics for the dashboard."""
    if not db:
        return jsonify({})
    
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
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

@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """Stop the attendance monitoring."""
    global is_monitoring
    is_monitoring = False
    return jsonify({'success': True, 'message': 'Monitoring stopped'})

@app.route('/api/export_csv')
def export_csv():
    """Export daily summary to CSV."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not available'})
    
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    try:
        db.export_daily_summary_to_csv(date_str)
        return jsonify({'success': True, 'message': f'CSV exported for {date_str}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Export failed: {str(e)}'})

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

if __name__ == '__main__':
    # Initialize the system
    initialize_system()
    
    # Get port from config
    port = tracker.config.get('web_port', 5000) if tracker else 5000
    
    print(f"Starting WiFi Attendance Tracker Web Interface on port {port}")
    print(f"Open your browser and go to: http://localhost:{port}")
    
    # Start monitoring automatically
    is_monitoring = True
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=port, debug=False)

