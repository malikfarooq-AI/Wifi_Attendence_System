# WiFi Attendance Tracker - Employee Management Version

## Overview

The WiFi-Based Attendance & Break Tracker is an advanced employee time tracking system that monitors attendance by detecting MAC addresses of devices connected to the local WiFi network. This enhanced version includes comprehensive employee management features, password protection, and a modern web interface.

## Key Features

### 🔐 **Employee Management**
- **Add New Employees**: Password-protected employee addition with admin authentication
- **Search Functionality**: Search employees by name or MAC address
- **Employee Pictures**: Support for employee profile pictures
- **Password Protection**: Secure admin access with customizable passwords (default: 1122)

### ⏰ **Advanced Time Tracking**
- **Time-In/Time-Out**: Automatic detection of first arrival and final departure
- **Break Monitoring**: Tracks when employees go on break and return
- **5:00 PM Auto-Timeout**: Employees automatically marked as timed out at office closing
- **Duration Calculations**: Precise tracking of total work time and break time

### 📊 **Comprehensive Reporting**
- **Real-time Dashboard**: Live employee status updates every 10 seconds
- **Daily Attendance Sheets**: Detailed CSV reports with formatted durations
- **Event History**: Complete audit trail of all attendance events
- **Summary Statistics**: Daily overview with present/absent/break/timeout counts

### 🌐 **Modern Web Interface**
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Live status changes and notifications
- **Interactive Dashboard**: Modern UI with statistics cards and employee cards
- **Modal Dialogs**: Professional forms for employee management

### 🔧 **System Features**
- **Non-Admin Operation**: Attempts to run without administrator privileges
- **Offline Operation**: Works completely without internet connection
- **Database Storage**: SQLite database for persistent data storage
- **JSON Configuration**: Separate employee data file for easy management
- **Integrated Application**: Single entry point for all functionality

## System Requirements

- **Operating System**: Windows 10/11, Linux, or macOS
- **Python**: 3.7 or higher
- **Network**: Local WiFi network access
- **Permissions**: Network scanning capabilities (admin/root recommended but not required)

## Installation

### Quick Setup (Windows)

1. **Extract the Project**
   ```
   Extract wifi_attendance_tracker_advanced.zip to your desired location
   ```

2. **Run Setup Script**
   ```
   Double-click setup.bat
   ```

3. **Configure Employees**
   ```
   Edit employees.json with your employee data
   ```

4. **Start the Application**
   ```
   Double-click run.bat or run: python main.py
   ```

### Manual Installation

1. **Install Python Dependencies**
   ```bash
   pip install flask flask-cors bcrypt
   ```

2. **Configure System**
   ```bash
   # Edit config.json for system settings
   # Edit employees.json for employee data
   ```

3. **Run Application**
   ```bash
   python main.py
   ```

## Configuration

### config.json
```json
{
  "scan_interval_seconds": 60,
  "web_port": 5000,
  "office_timeout_hour": 17,
  "office_timeout_minute": 0
}
```

### employees.json
```json
[
  {
    "name": "John Doe",
    "mac_address": "aa-bb-cc-dd-ee-ff",
    "picture": "static/img/john_doe.jpg"
  },
  {
    "name": "Jane Smith",
    "mac_address": "11-22-33-44-55-66",
    "picture": "static/img/jane_smith.jpg"
  }
]
```

## Usage

### Starting the Application

#### Web Interface Mode (Default)
```bash
python main.py
```
Access the web interface at: http://localhost:5000

#### Console Mode
```bash
python main.py --console
```

#### Custom Port
```bash
python main.py --port 8080
```

#### System Status
```bash
python main.py --status
```

### Web Interface Features

#### Dashboard Overview
- **System Status**: Current monitoring state and employee count
- **Statistics Cards**: Real-time counts of present, absent, on break, and timed out employees
- **Employee Status**: Live employee cards with status badges and time information
- **Recent Events**: Timeline of latest attendance events

#### Employee Management
1. **Adding Employees**:
   - Click "Add Employee" button
   - Fill in employee name and MAC address
   - Optionally add picture path
   - Enter admin password (default: 1122)
   - Click "Add Employee"

2. **Searching Employees**:
   - Use the search box to find employees by name or MAC address
   - Results update in real-time

3. **Changing Admin Password**:
   - Click "Settings" button
   - Enter current password and new password
   - Click "Change Password"

#### Monitoring Controls
- **Start Monitoring**: Begin attendance tracking
- **Stop Monitoring**: Pause attendance tracking
- **Refresh Data**: Manually update all data
- **Export CSV**: Download daily attendance summary

### Employee Pictures

To add employee pictures:

1. **Create Image Directory**:
   ```
   Create: static/img/ directory
   ```

2. **Add Picture Files**:
   ```
   Place images in: static/img/employee_name.jpg
   ```

3. **Update Configuration**:
   ```json
   {
     "name": "John Doe",
     "mac_address": "aa-bb-cc-dd-ee-ff",
     "picture": "static/img/john_doe.jpg"
   }
   ```

## How It Works

### MAC Address Detection
The system uses the `arp -a` command to scan for devices on the local network. When an employee's device (identified by MAC address) is detected:

1. **First Detection**: Marked as "Time In"
2. **Continuous Presence**: Status remains "Present"
3. **Temporary Absence**: Marked as "On Break" if gone for short period
4. **Extended Absence**: Marked as "Time Out" if gone for extended period
5. **5:00 PM Timeout**: Automatically marked as "Timed Out" at office closing

### Status Logic
- **Present**: Device currently detected on network
- **Absent**: Device not detected and no previous activity today
- **On Break**: Device temporarily not detected but was present earlier
- **Timed Out**: Device not detected after 5:00 PM or extended absence

### Data Storage
- **SQLite Database**: Stores all attendance events and employee data
- **CSV Logs**: Daily attendance summaries exported to `logs/` directory
- **JSON Files**: Configuration and employee data in human-readable format

## Security Features

### Password Protection
- **Admin Authentication**: Required for adding new employees
- **Password Hashing**: Secure bcrypt hashing for stored passwords
- **Default Password**: 1122 (changeable through web interface)
- **Session Security**: No persistent login sessions for security

### Data Privacy
- **Local Storage**: All data stored locally, no cloud transmission
- **Offline Operation**: No internet connection required
- **Encrypted Passwords**: Admin passwords securely hashed
- **Access Control**: Employee management requires authentication

## Troubleshooting

### Common Issues

#### "Permission Denied" Errors
- **Windows**: Run Command Prompt as Administrator
- **Linux/macOS**: Use `sudo python main.py`
- **Alternative**: Use non-admin mode (limited network scanning)

#### No Employees Detected
1. Verify MAC addresses in `employees.json`
2. Check if devices are connected to same network
3. Ensure WiFi is enabled on employee devices
4. Run `python main.py --status` to check configuration

#### Web Interface Not Loading
1. Check if port 5000 is available
2. Try different port: `python main.py --port 8080`
3. Verify firewall settings
4. Check console for error messages

#### Database Errors
1. Delete `attendance.db` to reset database
2. Restart application to recreate tables
3. Check file permissions in project directory

### Network Scanning Limitations

#### Non-Admin Mode
When running without administrator privileges:
- Limited network scanning capabilities
- May not detect all devices
- Reduced accuracy in some network configurations
- Employee management features work normally

#### Admin Mode (Recommended)
- Full network scanning capabilities
- Accurate device detection
- Complete attendance tracking
- All features fully functional

## File Structure

```
wifi_attendance_tracker/
├── main.py                 # Main application entry point
├── attendance_tracker.py   # Core attendance tracking logic
├── database.py            # Database operations
├── auth.py                # Authentication management
├── web_interface.py       # Flask web interface (legacy)
├── config.json            # System configuration
├── employees.json         # Employee data
├── requirements.txt       # Python dependencies
├── setup.bat             # Windows setup script
├── run.bat               # Windows run script
├── templates/
│   └── index.html        # Web interface template
├── static/
│   ├── css/
│   │   └── style.css     # Web interface styles
│   ├── js/
│   │   └── script.js     # Web interface JavaScript
│   └── img/              # Employee pictures directory
├── logs/                 # CSV export directory
└── attendance.db         # SQLite database
```

## API Endpoints

The web interface provides REST API endpoints:

### System Status
- `GET /api/status` - Get system status
- `POST /api/start_monitoring` - Start monitoring
- `POST /api/stop_monitoring` - Stop monitoring

### Employee Management
- `GET /api/employees` - Get all employees
- `POST /api/add_employee` - Add new employee (requires password)
- `GET /api/search_employees?q=query` - Search employees

### Attendance Data
- `GET /api/attendance_events` - Get attendance events
- `GET /api/daily_summary?date=YYYY-MM-DD` - Get daily summary
- `GET /api/summary_stats?date=YYYY-MM-DD` - Get summary statistics
- `GET /api/export_csv?date=YYYY-MM-DD` - Export CSV

### Authentication
- `POST /api/change_password` - Change admin password

## Advanced Configuration

### Custom Office Hours
Edit `config.json`:
```json
{
  "office_timeout_hour": 18,
  "office_timeout_minute": 30
}
```

### Scan Interval
Adjust monitoring frequency:
```json
{
  "scan_interval_seconds": 30
}
```

### Web Port
Change web interface port:
```json
{
  "web_port": 8080
}
```

## Development

### Adding New Features
1. **Backend**: Modify `main.py` or create new modules
2. **Frontend**: Update `templates/index.html` and `static/` files
3. **Database**: Add new tables/columns in `database.py`
4. **API**: Add new endpoints in `main.py`

### Testing
```bash
# Test database functionality
python database.py

# Test authentication
python auth.py

# Test attendance tracking
python attendance_tracker.py

# Check system status
python main.py --status
```

## Support

### Getting Help
1. Check this README for common solutions
2. Run `python main.py --status` for system diagnostics
3. Check log files in `logs/` directory
4. Verify configuration files are properly formatted

### Reporting Issues
When reporting issues, include:
- Operating system and Python version
- Error messages from console
- Configuration files (remove sensitive data)
- Steps to reproduce the issue

## License

This project is provided as-is for educational and internal business use. Please ensure compliance with local privacy and employment laws when monitoring employee attendance.

## Version History

### Version 3.0 (Current)
- Employee management with password protection
- Enhanced web interface with modern design
- Non-admin operation support
- Employee pictures and search functionality
- Integrated single-file application

### Version 2.0
- Advanced time tracking with breaks
- 5:00 PM automatic timeout
- Daily attendance summaries
- Web interface with real-time updates

### Version 1.0
- Basic MAC address detection
- Simple console interface
- CSV logging

---

**WiFi Attendance Tracker - Employee Management Version**  
*Advanced MAC Detection with Employee Management Features*  
*Version 3.0 - 2025*

