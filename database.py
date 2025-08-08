import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import csv

class AttendanceDatabase:
    def __init__(self, db_path: str = "attendance.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create employees table with password_hash and picture_path
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    mac_address TEXT UNIQUE NOT NULL,
                    password_hash TEXT, -- New: for employee management
                    picture_path TEXT,  -- New: path to employee picture
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create attendance_events table (replaces attendance_logs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    mac_address TEXT NOT NULL,
                    event_type TEXT NOT NULL, -- 'time_in', 'time_out', 'break_start', 'break_end', 'timeout_5pm'
                    timestamp TIMESTAMP NOT NULL,
                    date TEXT NOT NULL,
                    FOREIGN KEY (employee_id) REFERENCES employees (id)
                )
            """)
            
            # Create daily_attendance_summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_attendance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    time_in TEXT,
                    time_out TEXT,
                    total_break_duration INTEGER DEFAULT 0, -- in seconds
                    total_work_duration INTEGER DEFAULT 0, -- in seconds
                    status TEXT NOT NULL, -- 'Present', 'Absent', 'Timed Out'
                    UNIQUE(employee_id, date),
                    FOREIGN KEY (employee_id) REFERENCES employees (id)
                )
            """)

            # Create settings table for general application settings like admin password
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mac_address ON employees (mac_address)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_date ON attendance_events (date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_timestamp ON attendance_events (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_employee_date ON daily_attendance_summary (employee_id, date)")
            
            conn.commit()
    
    def add_employee(self, name: str, mac_address: str, password_hash: Optional[str] = None, picture_path: Optional[str] = None) -> bool:
        """Add a new employee to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO employees (name, mac_address, password_hash, picture_path) VALUES (?, ?, ?, ?)",
                    (name, mac_address.lower(), password_hash, picture_path)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # print(f"Employee with MAC address {mac_address} already exists")
            return False
        except Exception as e:
            print(f"Error adding employee: {e}")
            return False

    def update_employee(self, employee_id: int, name: Optional[str] = None, mac_address: Optional[str] = None, password_hash: Optional[str] = None, picture_path: Optional[str] = None) -> bool:
        """Update an existing employee's information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                update_fields = []
                update_values = []
                if name is not None: update_fields.append("name = ?"); update_values.append(name)
                if mac_address is not None: update_fields.append("mac_address = ?"); update_values.append(mac_address.lower())
                if password_hash is not None: update_fields.append("password_hash = ?"); update_values.append(password_hash)
                if picture_path is not None: update_fields.append("picture_path = ?"); update_values.append(picture_path)
                
                if not update_fields:
                    return False # Nothing to update

                query = f"UPDATE employees SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, (*update_values, employee_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating employee: {e}")
            return False

    def delete_employee(self, employee_id: int) -> bool:
        """Delete an employee from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting employee: {e}")
            return False
    
    def get_employee_by_mac(self, mac_address: str) -> Optional[Dict]:
        """Get employee information by MAC address."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, mac_address, password_hash, picture_path, created_at FROM employees WHERE mac_address = ?",
                (mac_address.lower(),)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'mac_address': row[2],
                    'password_hash': row[3],
                    'picture_path': row[4],
                    'created_at': row[5]
                }
        return None

    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Get employee information by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, mac_address, password_hash, picture_path, created_at FROM employees WHERE id = ?",
                (employee_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'mac_address': row[2],
                    'password_hash': row[3],
                    'picture_path': row[4],
                    'created_at': row[5]
                }
        return None
    
    def get_all_employees(self, search_query: Optional[str] = None) -> List[Dict]:
        """Get all employees from the database, optionally filtered by search query."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if search_query:
                search_query = f'%{search_query.lower()}%'
                cursor.execute(
                    "SELECT id, name, mac_address, password_hash, picture_path, created_at FROM employees WHERE LOWER(name) LIKE ? OR LOWER(mac_address) LIKE ? ORDER BY name",
                    (search_query, search_query)
                )
            else:
                cursor.execute('SELECT id, name, mac_address, password_hash, picture_path, created_at FROM employees ORDER BY name')
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'mac_address': row[2],
                    'password_hash': row[3],
                    'picture_path': row[4],
                    'created_at': row[5]
                }
                for row in rows
            ]
    
    def log_attendance_event(self, mac_address: str, event_type: str, timestamp: datetime = None) -> bool:
        """Log an attendance event to the attendance_events table."""
        if timestamp is None:
            timestamp = datetime.now()
        
        date_str = timestamp.strftime('%Y-%m-%d')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                employee = self.get_employee_by_mac(mac_address)
                employee_id = employee['id'] if employee else None
                
                cursor.execute("""
                    INSERT INTO attendance_events (employee_id, mac_address, event_type, timestamp, date)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee_id, mac_address.lower(), event_type, timestamp.strftime('%Y-%m-%d %H:%M:%S'), date_str))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error logging attendance event: {e}")
            return False
    
    def get_attendance_events(self, date: str = None, limit: int = 100) -> List[Dict]:
        """Get attendance events, optionally filtered by date."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if date:
                cursor.execute("""
                    SELECT ae.id, ae.mac_address, ae.event_type, ae.timestamp, ae.date,
                           e.name as employee_name
                    FROM attendance_events ae
                    LEFT JOIN employees e ON ae.employee_id = e.id
                    WHERE ae.date = ?
                    ORDER BY ae.timestamp DESC
                    LIMIT ?
                """, (date, limit))
            else:
                cursor.execute("""
                    SELECT ae.id, ae.mac_address, ae.event_type, ae.timestamp, ae.date,
                           e.name as employee_name
                    FROM attendance_events ae
                    LEFT JOIN employees e ON ae.employee_id = e.id
                    ORDER BY ae.timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'mac_address': row[1],
                    'event_type': row[2],
                    'timestamp': row[3],
                    'date': row[4],
                    'employee_name': row[5] or f"Unknown ({row[1]})"
                }
                for row in rows
            ]

    def update_daily_summary(self, employee_id: int, date_str: str, time_in: Optional[str] = None, 
                             time_out: Optional[str] = None, total_break_duration: Optional[int] = None,
                             total_work_duration: Optional[int] = None, status: Optional[str] = None):
        """Update or insert a daily attendance summary record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute("SELECT * FROM daily_attendance_summary WHERE employee_id = ? AND date = ?",
                           (employee_id, date_str))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update existing record
                update_fields = []
                update_values = []
                if time_in is not None: update_fields.append("time_in = ?"); update_values.append(time_in)
                if time_out is not None: update_fields.append("time_out = ?"); update_values.append(time_out)
                if total_break_duration is not None: update_fields.append("total_break_duration = ?"); update_values.append(total_break_duration)
                if total_work_duration is not None: update_fields.append("total_work_duration = ?"); update_values.append(total_work_duration)
                if status is not None: update_fields.append("status = ?"); update_values.append(status)
                
                if update_fields:
                    query = f"UPDATE daily_attendance_summary SET {', '.join(update_fields)} WHERE employee_id = ? AND date = ?"
                    cursor.execute(query, (*update_values, employee_id, date_str))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO daily_attendance_summary (employee_id, date, time_in, time_out, total_break_duration, total_work_duration, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (employee_id, date_str, time_in, time_out, total_break_duration, total_work_duration, status))
            
            conn.commit()

    def get_daily_summary_for_employee(self, employee_id: int, date_str: str) -> Optional[Dict]:
        """Get daily attendance summary for a specific employee on a specific date."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT das.id, e.name, e.mac_address, das.date, das.time_in, das.time_out,
                       das.total_break_duration, das.total_work_duration, das.status
                FROM daily_attendance_summary das
                JOIN employees e ON das.employee_id = e.id
                WHERE das.employee_id = ? AND das.date = ?
            """, (employee_id, date_str))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'mac_address': row[2],
                    'date': row[3],
                    'time_in': row[4],
                    'time_out': row[5],
                    'total_break_duration': row[6],
                    'total_work_duration': row[7],
                    'status': row[8]
                }
            return None

    def get_daily_summary(self, date_str: str = None) -> List[Dict]:
        """Get daily attendance summary for all employees, optionally filtered by date."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if date_str is None:
                date_str = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("""
                SELECT das.id, e.name, e.mac_address, das.date, das.time_in, das.time_out,
                       das.total_break_duration, das.total_work_duration, das.status
                FROM daily_attendance_summary das
                JOIN employees e ON das.employee_id = e.id
                WHERE das.date = ?
                ORDER BY e.name
            """, (date_str,))
            
            rows = cursor.fetchall()
            summary_list = []
            for row in rows:
                summary_list.append({
                    'id': row[0],
                    'name': row[1],
                    'mac_address': row[2],
                    'date': row[3],
                    'time_in': row[4],
                    'time_out': row[5],
                    'total_break_duration': row[6],
                    'total_work_duration': row[7],
                    'status': row[8]
                })
            return summary_list

    def calculate_durations(self, employee_id: int, date_str: str):
        """Calculate total break and work durations for an employee on a given day."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT event_type, timestamp FROM attendance_events
                WHERE employee_id = ? AND date = ?
                ORDER BY timestamp
            """, (employee_id, date_str))
            
            events = cursor.fetchall()
            
            time_in = None
            time_out = None
            total_break_duration = timedelta(0)
            total_work_duration = timedelta(0)
            
            last_event_time = None
            on_break = False
            
            for event_type, timestamp_str in events:
                current_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                if event_type == 'time_in':
                    if time_in is None: # Only set time_in once for the day
                        time_in = current_time
                    last_event_time = current_time
                    on_break = False
                elif event_type == 'time_out':
                    if time_in and last_event_time and not on_break:
                        total_work_duration += (current_time - last_event_time)
                    time_out = current_time
                    last_event_time = current_time
                    on_break = False
                elif event_type == 'break_start':
                    if time_in and last_event_time and not on_break:
                        total_work_duration += (current_time - last_event_time)
                    last_event_time = current_time
                    on_break = True
                elif event_type == 'break_end':
                    if time_in and last_event_time and on_break:
                        total_break_duration += (current_time - last_event_time)
                    last_event_time = current_time
                    on_break = False
                elif event_type == 'timeout_5pm':
                    if time_in and last_event_time and not on_break:
                        total_work_duration += (current_time - last_event_time)
                    time_out = current_time # Set time_out to 5 PM
                    last_event_time = current_time
                    on_break = False

            # If still present at the end of the day (no explicit time_out or 5pm timeout)
            # and there was a time_in event, calculate work duration up to now
            if time_in and time_out is None and last_event_time and not on_break:
                total_work_duration += (datetime.now() - last_event_time)

            return {
                'time_in': time_in.strftime('%H:%M:%S') if time_in else None,
                'time_out': time_out.strftime('%H:%M:%S') if time_out else None,
                'total_break_duration': int(total_break_duration.total_seconds()),
                'total_work_duration': int(total_work_duration.total_seconds())
            }

    def export_daily_summary_to_csv(self, date_str: str):
        """Export daily attendance summary to a CSV file."""
        summary_data = self.get_daily_summary(date_str)
        
        if not summary_data:
            print(f"No summary data for {date_str} to export.")
            return

        log_file = f"logs/attendance_summary_{date_str}.csv"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        fieldnames = ['Name', 'MAC Address', 'Date', 'Time In', 'Time Out', 'Total Break (HH:MM:SS)', 'Total Work (HH:MM:SS)', 'Status']
        
        with open(log_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in summary_data:
                # Convert seconds to HH:MM:SS format
                total_break_duration = row['total_break_duration'] or 0
                total_work_duration = row['total_work_duration'] or 0
                total_break_formatted = str(timedelta(seconds=total_break_duration))
                total_work_formatted = str(timedelta(seconds=total_work_duration))

                writer.writerow({
                    'Name': row['name'],
                    'MAC Address': row['mac_address'],
                    'Date': row['date'],
                    'Time In': row['time_in'] if row['time_in'] else 'N/A',
                    'Time Out': row['time_out'] if row['time_out'] else 'N/A',
                    'Total Break (HH:MM:SS)': total_break_formatted,
                    'Total Work (HH:MM:SS)': total_work_formatted,
                    'Status': row['status']
                })
        print(f"Daily summary for {date_str} exported to {log_file}")

    def sync_employees_from_config(self, config_path: str = "config.json"):
        """Sync employees from config file to database."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            employees = config.get('employees', {})
            synced_count = 0
            
            for mac_address, name in employees.items():
                if self.add_employee(name, mac_address):
                    synced_count += 1
                    # Also initialize daily summary for today if not exists
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    employee_info = self.get_employee_by_mac(mac_address)
                    if employee_info:
                        self.update_daily_summary(employee_info['id'], today_str, status='Absent')

            print(f"Synced {synced_count} new employees from config")
            return synced_count
            
        except FileNotFoundError:
            print(f"Config file {config_path} not found")
            return 0
        except json.JSONDecodeError:
            print(f"Invalid JSON in {config_path}")
            return 0
        except Exception as e:
            print(f"Error syncing employees: {e}")
            return 0

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value from the settings table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value in the settings table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error setting setting {key}: {e}")
            return False
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove attendance events and summaries older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM attendance_events WHERE timestamp < ?",
                    (cutoff_date_str,)
                )
                deleted_events = cursor.rowcount

                cursor.execute(
                    "DELETE FROM daily_attendance_summary WHERE date < ?",
                    (cutoff_date.strftime('%Y-%m-%d'),)
                )
                deleted_summaries = cursor.rowcount

                conn.commit()
                print(f"Cleaned up {deleted_events} old attendance events and {deleted_summaries} old summaries.")
                return deleted_events + deleted_summaries
        except Exception as e:
            print(f"Error cleaning up old logs: {e}")
            return 0

if __name__ == "__main__":
    # Test the database functionality
    db = AttendanceDatabase()
    
    # Sync employees from config
    db.sync_employees_from_config()
    
    # Display all employees
    employees = db.get_all_employees()
    print(f"\nTotal employees in database: {len(employees)}")
    for emp in employees:
        print(f"- {emp['name']} ({emp['mac_address']})")
    
    # Display recent events
    recent_events = db.get_attendance_events(limit=10)
    print(f"\nRecent attendance events: {len(recent_events)}")
    for event in recent_events:
        print(f"- {event['timestamp']}: {event['employee_name']} - {event['event_type']}")

    # Test daily summary export
    today = datetime.now().strftime('%Y-%m-%d')
    db.export_daily_summary_to_csv(today)

    # Example of logging events and updating summary
    # employee_mac = "f8-98-b9-7f-fe-0d"
    # employee_info = db.get_employee_by_mac(employee_mac)
    # if employee_info:
    #     db.log_attendance_event(employee_mac, 'time_in')
    #     db.update_daily_summary(employee_info['id'], today, time_in=datetime.now().strftime('%H:%M:%S'), status='Present')
    #     time.sleep(5)
    #     db.log_attendance_event(employee_mac, 'break_start')
    #     db.update_daily_summary(employee_info['id'], today, total_break_duration=db.calculate_durations(employee_info['id'], today)['total_break_duration'])
    #     time.sleep(5)
    #     db.log_attendance_event(employee_mac, 'break_end')
    #     db.update_daily_summary(employee_info['id'], today, total_break_duration=db.calculate_durations(employee_info['id'], today)['total_break_duration'])
    #     time.sleep(5)
    #     db.log_attendance_event(employee_mac, 'time_out')
    #     db.update_daily_summary(employee_info['id'], today, time_out=datetime.now().strftime('%H:%M:%S'), status='Absent', total_work_duration=db.calculate_durations(employee_info['id'], today)['total_work_duration'])

    # db.export_daily_summary_to_csv(today)



