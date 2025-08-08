import subprocess
import json
import time
import platform
from datetime import datetime, timedelta
from typing import Dict, Set, List, Tuple
import os
from database import AttendanceDatabase

class AttendanceTracker:
    def __init__(self, config_path: str = "config.json", employees_path: str = "employees.json", db_path: str = "attendance.db"):
        """Initialize the attendance tracker with configuration and database."""
        self.config_path = config_path
        self.employees_path = employees_path
        self.config = self.load_config()
        self.employees = self.load_employees()
        self.scan_interval = self.config.get("scan_interval_seconds", 60)
        self.office_timeout_hour = self.config.get("office_timeout_hour", 17)
        self.office_timeout_minute = self.config.get("office_timeout_minute", 0)

        self.db = AttendanceDatabase(db_path)
        
        # State tracking for each employee
        # {mac: {"is_present": bool, "last_seen": datetime, "time_in": datetime, "on_break": bool, "break_start_time": datetime}}
        self.employee_states = {}
        self._initialize_employee_states()
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
    def _initialize_employee_states(self):
        """Initialize employee states from the database for the current day."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        for mac, name in self.employees.items():
            employee_info = self.db.get_employee_by_mac(mac)
            if employee_info:
                summary = self.db.get_daily_summary_for_employee(employee_info["id"], today_str)
                if summary and summary["status"] == "Present":
                    # If employee was marked present today and not timed out
                    self.employee_states[mac] = {
                        "is_present": True,
                        "last_seen": datetime.now(), # Assume still present if last status was Present
                        "time_in": datetime.strptime(f"{today_str} {summary['time_in']}", 
                                                     "%Y-%m-%d %H:%M:%S") if summary["time_in"] else None,
                        "on_break": False, # Cannot determine break status from summary, assume not on break
                        "break_start_time": None
                    }
                else:
                    self.employee_states[mac] = {
                        "is_present": False,
                        "last_seen": None,
                        "time_in": None,
                        "on_break": False,
                        "break_start_time": None
                    }
            else:
                self.employee_states[mac] = {
                    "is_present": False,
                    "last_seen": None,
                    "time_in": None,
                    "on_break": False,
                    "break_start_time": None
                }

    def load_config(self) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {self.config_path} not found. Using default settings.")
            return {"scan_interval_seconds": 60, "office_timeout_hour": 17, "office_timeout_minute": 0}
        except json.JSONDecodeError:
            print(f"Invalid JSON in {self.config_path}. Using default settings.")
            return {"scan_interval_seconds": 60, "office_timeout_hour": 17, "office_timeout_minute": 0}

    def load_employees(self) -> dict:
        """Load employees from employees.json file."""
        try:
            with open(self.employees_path, 'r') as f:
                employees_list = json.load(f)
            
            # Convert list to dict for compatibility
            employees_dict = {}
            for emp in employees_list:
                employees_dict[emp['mac_address']] = emp['name']
            
            return employees_dict
        except FileNotFoundError:
            print(f"Employees file {self.employees_path} not found. Using empty employee list.")
            return {}
        except json.JSONDecodeError:
            print(f"Invalid JSON in {self.employees_path}. Using empty employee list.")
            return {}
        except Exception as e:
            print(f"Error loading employees: {e}")
            return {}
    
    def get_connected_devices(self) -> Set[str]:
        """Get MAC addresses of devices connected to the local network."""
        connected_macs = set()
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            potential_mac = parts[1]
                            if self.is_valid_mac(potential_mac):
                                normalized_mac = self.normalize_mac(potential_mac)
                                connected_macs.add(normalized_mac)
            else:
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '(' in line and ')' in line and 'at' in line:
                            parts = line.split(' at ')
                            if len(parts) >= 2:
                                mac_part = parts[1].split(' ')[0]
                                if self.is_valid_mac(mac_part):
                                    normalized_mac = self.normalize_mac(mac_part)
                                    connected_macs.add(normalized_mac)
                                    
        except subprocess.TimeoutExpired:
            print("ARP command timed out")
        except Exception as e:
            print(f"Error getting connected devices: {e}")
            
        return connected_macs
    
    def is_valid_mac(self, mac: str) -> bool:
        """Check if a string is a valid MAC address."""
        if not mac:
            return False
        clean_mac = mac.replace('-', '').replace(':', '').replace('.', '')
        if len(clean_mac) != 12:
            return False
        try:
            int(clean_mac, 16)
            return True
        except ValueError:
            return False
    
    def normalize_mac(self, mac: str) -> str:
        """Normalize MAC address to lowercase with dashes."""
        clean_mac = mac.replace('-', '').replace(':', '').replace('.', '').lower()
        return '-'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
    
    def get_employee_name(self, mac: str) -> str:
        """Get employee name from MAC address."""
        return self.employees.get(mac, f"Unknown ({mac})")
    
    def process_scan_results(self, detected_macs: Set[str]) -> List[Tuple[str, str, datetime]]:
        """Process scan results and generate attendance events."""
        current_time = datetime.now()
        today_str = current_time.strftime("%Y-%m-%d")
        events = []
        
        known_detected = {mac for mac in detected_macs if mac in self.employees}
        
        for mac in self.employees:
            employee_info = self.db.get_employee_by_mac(mac)
            if not employee_info: # Should not happen if sync_employees_from_json is called
                continue
            employee_id = employee_info["id"]
            
            current_state = self.employee_states.get(mac, {})
            was_present = current_state.get("is_present", False)
            on_break = current_state.get("on_break", False)
            time_in = current_state.get("time_in")
            
            is_currently_present = mac in known_detected
            
            # Handle Time-In
            if is_currently_present and not was_present:
                event_type = "time_in"
                self.db.log_attendance_event(mac, event_type, current_time)
                events.append((mac, event_type, current_time))
                self.employee_states[mac]["is_present"] = True
                self.employee_states[mac]["last_seen"] = current_time
                self.employee_states[mac]["time_in"] = current_time
                self.employee_states[mac]["on_break"] = False
                self.employee_states[mac]["break_start_time"] = None
                
                # Update daily summary: set time_in and status to Present
                self.db.update_daily_summary(employee_id, today_str, 
                                             time_in=current_time.strftime("%H:%M:%S"), status="Present")

            # Handle Break Start
            elif was_present and not is_currently_present and not on_break:
                event_type = "break_start"
                self.db.log_attendance_event(mac, event_type, current_time)
                events.append((mac, event_type, current_time))
                self.employee_states[mac]["is_present"] = False
                self.employee_states[mac]["last_seen"] = current_time
                self.employee_states[mac]["on_break"] = True
                self.employee_states[mac]["break_start_time"] = current_time
                
                # Update daily summary: status to On Break
                self.db.update_daily_summary(employee_id, today_str, status="On Break")

            # Handle Break End
            elif not was_present and is_currently_present and on_break:
                event_type = "break_end"
                self.db.log_attendance_event(mac, event_type, current_time)
                events.append((mac, event_type, current_time))
                self.employee_states[mac]["is_present"] = True
                self.employee_states[mac]["last_seen"] = current_time
                self.employee_states[mac]["on_break"] = False
                self.employee_states[mac]["break_start_time"] = None
                
                # Update daily summary: status to Present, recalculate break duration
                durations = self.db.calculate_durations(employee_id, today_str)
                self.db.update_daily_summary(employee_id, today_str, status="Present", 
                                             total_break_duration=durations["total_break_duration"])

            # Handle Time-Out (if employee was present and is now absent, and not on break)
            elif was_present and not is_currently_present and not on_break and time_in:
                # This is a final time_out for the day, not just a break
                event_type = "time_out"
                self.db.log_attendance_event(mac, event_type, current_time)
                events.append((mac, event_type, current_time))
                self.employee_states[mac]["is_present"] = False
                self.employee_states[mac]["last_seen"] = current_time
                self.employee_states[mac]["on_break"] = False
                
                # Update daily summary: set time_out and status to Absent, recalculate work duration
                durations = self.db.calculate_durations(employee_id, today_str)
                self.db.update_daily_summary(employee_id, today_str, 
                                             time_out=current_time.strftime("%H:%M:%S"), status="Absent",
                                             total_work_duration=durations["total_work_duration"])

            # Update last seen for currently present employees
            if is_currently_present:
                self.employee_states[mac]["last_seen"] = current_time
            
            # Automatic 5:00 PM timeout
            timeout_time = current_time.replace(hour=self.office_timeout_hour, minute=self.office_timeout_minute, second=0, microsecond=0)
            if current_time >= timeout_time and was_present and time_in and not on_break:
                # Check if already timed out today
                summary = self.db.get_daily_summary_for_employee(employee_id, today_str)
                if summary and summary["status"] != "Timed Out":
                    event_type = "timeout_5pm"
                    self.db.log_attendance_event(mac, event_type, timeout_time)
                    events.append((mac, event_type, timeout_time))
                    self.employee_states[mac]["is_present"] = False
                    self.employee_states[mac]["last_seen"] = timeout_time
                    
                    # Update daily summary: set time_out to 5 PM and status to Timed Out
                    durations = self.db.calculate_durations(employee_id, today_str)
                    self.db.update_daily_summary(employee_id, today_str, 
                                                 time_out=timeout_time.strftime("%H:%M:%S"), status="Timed Out",
                                                 total_work_duration=durations["total_work_duration"])

        # Export daily summary to CSV at the end of the day or on significant event
        # For simplicity, let's export it every scan for now, or when a time_out/timeout_5pm event occurs
        self.db.export_daily_summary_to_csv(today_str)

        return events
    
    def scan_once(self) -> List[Tuple[str, str, datetime]]:
        """Perform one scan and return any events."""
        print(f"Scanning network at {datetime.now().strftime('%H:%M:%S')}...")
        detected_macs = self.get_connected_devices()
        print(f"Detected {len(detected_macs)} devices")
        
        events = self.process_scan_results(detected_macs)
        return events
    
    def start_monitoring(self):
        """Start continuous monitoring loop."""
        print("Starting WiFi Attendance Tracker...")
        print(f"Monitoring {len(self.employees)} employees")
        print(f"Scan interval: {self.scan_interval} seconds")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                self.scan_once()
                time.sleep(self.scan_interval)
        except KeyboardInterrupt:
            print("\nStopping attendance tracker...")
    
    def get_current_status(self) -> Dict[str, dict]:
        """Get current attendance status of all employees."""
        status = {}
        current_time = datetime.now()
        
        for mac, name in self.employees.items():
            state = self.employee_states.get(mac, {})
            is_present = state.get("is_present", False)
            last_seen_time = state.get("last_seen")
            on_break = state.get("on_break", False)
            
            display_status = "Present" if is_present else ("On Break" if on_break else "Absent")
            
            status[mac] = {
                'name': name,
                'mac': mac,
                'is_present': is_present,
                'status': display_status,
                'last_seen': last_seen_time.strftime('%Y-%m-%d %H:%M:%S') if last_seen_time else 'Never',
                'time_in': state.get('time_in').strftime('%H:%M:%S') if state.get('time_in') else 'N/A'
            }
        
        return status

    def sync_employees_from_json(self):
        """Sync employees from employees.json to database."""
        try:
            with open(self.employees_path, 'r') as f:
                employees_list = json.load(f)
            
            synced_count = 0
            for emp in employees_list:
                name = emp.get('name')
                mac_address = emp.get('mac_address')
                picture_path = emp.get('picture')
                
                if name and mac_address:
                    if self.db.add_employee(name, mac_address, picture_path=picture_path):
                        synced_count += 1
                        # Also initialize daily summary for today if not exists
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        employee_info = self.db.get_employee_by_mac(mac_address)
                        if employee_info:
                            self.db.update_daily_summary(employee_info['id'], today_str, status='Absent')

            print(f"Synced {synced_count} new employees from {self.employees_path}")
            return synced_count
            
        except FileNotFoundError:
            print(f"Employees file {self.employees_path} not found")
            return 0
        except json.JSONDecodeError:
            print(f"Invalid JSON in {self.employees_path}")
            return 0
        except Exception as e:
            print(f"Error syncing employees: {e}")
            return 0

if __name__ == "__main__":
    tracker = AttendanceTracker()
    tracker.sync_employees_from_json()
    tracker.start_monitoring()

