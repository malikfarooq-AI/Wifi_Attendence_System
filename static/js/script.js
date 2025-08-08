// WiFi Attendance Tracker - Advanced JavaScript

class AttendanceTracker {
    constructor() {
        this.isMonitoring = false;
        this.updateInterval = null;
        this.employees = [];
        this.events = [];
        this.summary = [];
        this.searchQuery = '';
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoUpdate();
        this.updateCurrentTime();
        
        // Set today's date in summary date input
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('summaryDate').value = today;
    }
    
    setupEventListeners() {
        // Control buttons
        document.getElementById('startBtn').addEventListener('click', () => this.startMonitoring());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopMonitoring());
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshData());
        document.getElementById('exportBtn').addEventListener('click', () => this.exportCSV());
        
        // Search functionality
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('clearSearchBtn').addEventListener('click', () => this.clearSearch());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        document.getElementById('searchInput').addEventListener('input', (e) => {
            if (e.target.value === '') this.clearSearch();
        });
        
        // Modal buttons
        document.getElementById('addEmployeeBtn').addEventListener('click', () => this.openModal('addEmployeeModal'));
        document.getElementById('settingsBtn').addEventListener('click', () => this.openModal('settingsModal'));
        
        // Form submissions
        document.getElementById('addEmployeeForm').addEventListener('submit', (e) => this.handleAddEmployee(e));
        document.getElementById('changePasswordForm').addEventListener('submit', (e) => this.handleChangePassword(e));
        document.getElementById('deleteEmployeeForm').addEventListener('submit', (e) => this.handleDeleteEmployee(e));
        document.getElementById('modifyEmployeeForm').addEventListener('submit', (e) => this.handleModifyEmployee(e));
        
        // Summary date change
        document.getElementById('summaryDate').addEventListener('change', () => this.loadDailySummary());
        document.getElementById('summaryRefreshBtn').addEventListener('click', () => this.loadDailySummary());
        
        // Event date filter
        document.getElementById('eventDateFilter').addEventListener('change', () => this.loadEvents());
        
        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                this.closeModal(modal.id);
            });
        });
        
        // Close modal when clicking outside
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal.id);
                }
            });
        });
    }
    
    async loadInitialData() {
        await Promise.all([
            this.loadSystemStatus(),
            this.loadEmployees(),
            this.loadEvents(),
            this.loadDailySummary(),
            this.loadSummaryStats()
        ]);
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            document.getElementById('systemStatus').textContent = status.is_monitoring ? 'Monitoring' : 'Stopped';
            document.getElementById('systemStatus').className = `status-value ${status.is_monitoring ? 'monitoring' : 'stopped'}`;
            document.getElementById('employeeCount').textContent = status.employee_count;
            document.getElementById('scanInterval').textContent = `${status.scan_interval} seconds`;
            document.getElementById('officeTimeout').textContent = status.office_timeout;
            
            this.isMonitoring = status.is_monitoring;
            this.updateControlButtons();
            
        } catch (error) {
            console.error('Error loading system status:', error);
            this.showNotification('Error loading system status', 'error');
        }
    }
    
    async loadEmployees() {
        try {
            const response = await fetch('/api/employees');
            this.employees = await response.json();
            this.renderEmployees();
        } catch (error) {
            console.error('Error loading employees:', error);
            this.showNotification('Error loading employees', 'error');
        }
    }
    
    async loadEvents() {
        try {
            const dateFilter = document.getElementById('eventDateFilter').value;
            const url = dateFilter ? `/api/attendance_events?date=${dateFilter}&limit=50` : '/api/attendance_events?limit=50';
            const response = await fetch(url);
            this.events = await response.json();
            this.renderEvents();
        } catch (error) {
            console.error('Error loading events:', error);
            this.showNotification('Error loading events', 'error');
        }
    }
    
    async loadDailySummary() {
        try {
            const date = document.getElementById('summaryDate').value;
            const response = await fetch(`/api/daily_summary?date=${date}`);
            this.summary = await response.json();
            this.renderDailySummary();
        } catch (error) {
            console.error('Error loading daily summary:', error);
            this.showNotification('Error loading daily summary', 'error');
        }
    }
    
    async loadSummaryStats() {
        try {
            const date = document.getElementById('summaryDate').value;
            const response = await fetch(`/api/summary_stats?date=${date}`);
            const stats = await response.json();
            
            document.getElementById('presentCount').textContent = stats.present_count || 0;
            document.getElementById('absentCount').textContent = stats.absent_count || 0;
            document.getElementById('breakCount').textContent = stats.on_break_count || 0;
            document.getElementById('timeoutCount').textContent = stats.timed_out_count || 0;
            
        } catch (error) {
            console.error('Error loading summary stats:', error);
        }
    }
    
    renderEmployees() {
        const container = document.getElementById('employeeList');
        
        if (this.employees.length === 0) {
            container.innerHTML = '<div class="loading">No employees found</div>';
            return;
        }
        
        // Filter employees based on search query
        const filteredEmployees = this.searchQuery 
            ? this.employees.filter(emp => 
                emp.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                emp.mac.toLowerCase().includes(this.searchQuery.toLowerCase())
              )
            : this.employees;
        
        if (filteredEmployees.length === 0) {
            container.innerHTML = '<div class="loading">No employees match your search</div>';
            return;
        }
        
        container.innerHTML = filteredEmployees.map(employee => `
            <div class="employee-card" onclick="attendanceTracker.showEmployeeDetails('${employee.mac}')">
                <div class="employee-avatar">
                    ${employee.picture ? 
                        `<img src="${employee.picture}" alt="${employee.name}" onerror="this.style.display='none'; this.parentNode.textContent='${employee.name.charAt(0).toUpperCase()}'">` :
                        employee.name.charAt(0).toUpperCase()
                    }
                </div>
                <div class="employee-info">
                    <div class="employee-name">${employee.name}</div>
                    <div class="employee-mac">${employee.mac}</div>
                </div>
                <div class="employee-status">
                    <span class="status-badge ${employee.status.toLowerCase().replace(' ', '')}">${employee.status}</span>
                    <div class="employee-time">
                        ${employee.time_in !== 'N/A' ? `In: ${employee.time_in}` : 'Not checked in'}
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    renderEvents() {
        const container = document.getElementById('eventsList');
        
        if (this.events.length === 0) {
            container.innerHTML = '<div class="loading">No recent events</div>';
            return;
        }
        
        container.innerHTML = this.events.map(event => `
            <div class="event-item ${event.event_type}">
                <div class="event-icon">
                    <i class="fas ${this.getEventIcon(event.event_type)}"></i>
                </div>
                <div class="event-content">
                    <div class="event-name">${event.employee_name}</div>
                    <div class="event-type">${this.formatEventType(event.event_type)}</div>
                </div>
                <div class="event-time">${event.time_ago}</div>
            </div>
        `).join('');
    }
    
    renderDailySummary() {
        const container = document.getElementById('summaryTable');
        
        if (this.summary.length === 0) {
            container.innerHTML = '<div class="loading">No summary data for selected date</div>';
            return;
        }
        
        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Employee</th>
                        <th>Time In</th>
                        <th>Time Out</th>
                        <th>Work Duration</th>
                        <th>Break Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.summary.map(emp => `
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <div class="employee-avatar" style="width: 32px; height: 32px; font-size: 12px;">
                                        ${emp.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                        <div style="font-weight: 600;">${emp.name}</div>
                                        <div style="font-size: 11px; color: var(--text-muted);">${emp.mac_address}</div>
                                    </div>
                                </div>
                            </td>
                            <td>${emp.time_in || 'N/A'}</td>
                            <td>${emp.time_out || 'N/A'}</td>
                            <td>${emp.total_work_formatted}</td>
                            <td>${emp.total_break_formatted}</td>
                            <td><span class="status-badge ${emp.status.toLowerCase().replace(' ', '')}">${emp.status}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
    
    getEventIcon(eventType) {
        const icons = {
            'time_in': 'fa-sign-in-alt',
            'time_out': 'fa-sign-out-alt',
            'break_start': 'fa-coffee',
            'break_end': 'fa-play',
            'timeout_5pm': 'fa-clock'
        };
        return icons[eventType] || 'fa-circle';
    }
    
    formatEventType(eventType) {
        const formats = {
            'time_in': 'Time In',
            'time_out': 'Time Out',
            'break_start': 'Break Start',
            'break_end': 'Break End',
            'timeout_5pm': '5 PM Timeout'
        };
        return formats[eventType] || eventType;
    }
    
    async startMonitoring() {
        try {
            const response = await fetch('/api/start_monitoring', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.isMonitoring = true;
                this.updateControlButtons();
                this.showNotification('Monitoring started successfully', 'success');
                await this.loadSystemStatus();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error starting monitoring:', error);
            this.showNotification('Error starting monitoring', 'error');
        }
    }
    
    async stopMonitoring() {
        try {
            const response = await fetch('/api/stop_monitoring', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.isMonitoring = false;
                this.updateControlButtons();
                this.showNotification('Monitoring stopped', 'warning');
                await this.loadSystemStatus();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error stopping monitoring:', error);
            this.showNotification('Error stopping monitoring', 'error');
        }
    }
    
    async refreshData() {
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        await this.loadInitialData();
        this.showNotification('Data refreshed', 'success');
    }
    
    async exportCSV() {
        try {
            const date = document.getElementById('summaryDate').value;
            const response = await fetch(`/api/export_csv?date=${date}`);
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('CSV exported successfully', 'success');
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error exporting CSV:', error);
            this.showNotification('Error exporting CSV', 'error');
        }
    }
    
    performSearch() {
        this.searchQuery = document.getElementById('searchInput').value.trim();
        this.renderEmployees();
        
        if (this.searchQuery) {
            this.showNotification(`Searching for: ${this.searchQuery}`, 'info');
        }
    }
    
    clearSearch() {
        this.searchQuery = '';
        document.getElementById('searchInput').value = '';
        this.renderEmployees();
    }
    
    updateControlButtons() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        startBtn.disabled = this.isMonitoring;
        stopBtn.disabled = !this.isMonitoring;
    }
    
    startAutoUpdate() {
        // Update data every 10 seconds
        this.updateInterval = setInterval(() => {
            if (this.isMonitoring) {
                this.loadEmployees();
                this.loadEvents();
                this.loadSummaryStats();
            }
        }, 10000);
    }
    
    updateCurrentTime() {
        const updateTime = () => {
            const now = new Date();
            document.getElementById('currentTime').textContent = now.toLocaleTimeString();
        };
        
        updateTime();
        setInterval(updateTime, 1000);
    }
    
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('show');
        
        // Load settings data if opening settings modal
        if (modalId === 'settingsModal') {
            this.loadSystemStatus();
        }
    }
    
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('show');
        
        // Reset forms
        const forms = modal.querySelectorAll('form');
        forms.forEach(form => form.reset());
    }
    
    async handleAddEmployee(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const employeeData = {
            name: formData.get('name'),
            mac: formData.get('mac').toLowerCase(),
            picture: formData.get('picture'),
            password: formData.get('password')
        };
        
        try {
            const response = await fetch('/api/add_employee', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(employeeData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Employee added successfully', 'success');
                this.closeModal('addEmployeeModal');
                await this.loadEmployees();
                await this.loadSystemStatus();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error adding employee:', error);
            this.showNotification('Error adding employee', 'error');
        }
    }
    
    async handleChangePassword(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const newPassword = formData.get('newPassword');
        const confirmPassword = formData.get('confirmPassword');
        
        if (newPassword !== confirmPassword) {
            this.showNotification('Passwords do not match', 'error');
            return;
        }
        
        const passwordData = {
            currentPassword: formData.get('currentPassword'),
            newPassword: newPassword
        };
        
        try {
            const response = await fetch('/api/change_password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(passwordData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Password changed successfully', 'success');
                this.closeModal('settingsModal');
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showNotification('Error changing password', 'error');
        }
    }
    
    showEmployeeDetails(mac) {
        const employee = this.employees.find(emp => emp.mac === mac);
        if (!employee) return;
        
        const modal = document.getElementById('employeeDetailsModal');
        const content = document.getElementById('employeeDetailsContent');
        
        content.innerHTML = `
            <div style="text-align: center; margin-bottom: 20px;">
                <div class="employee-avatar" style="width: 80px; height: 80px; font-size: 32px; margin: 0 auto 12px;">
                    ${employee.picture ? 
                        `<img src="${employee.picture}" alt="${employee.name}" style="width: 100%; height: 100%; object-fit: cover;">` :
                        employee.name.charAt(0).toUpperCase()
                    }
                </div>
                <h3>${employee.name}</h3>
                <p style="color: var(--text-muted); font-family: monospace;">${employee.mac}</p>
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Current Status:</span>
                    <span class="status-badge ${employee.status.toLowerCase().replace(' ', '')}">${employee.status}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Time In:</span>
                    <span class="info-value">${employee.time_in}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Last Seen:</span>
                    <span class="info-value">${employee.last_seen}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Is Present:</span>
                    <span class="info-value">${employee.is_present ? 'Yes' : 'No'}</span>
                </div>
            </div>
        `;
        
        this.openModal('employeeDetailsModal');
        
        // Store current employee for delete/modify operations
        this.currentEmployee = employee;
        
        // Add event listeners for delete and modify buttons
        document.getElementById('deleteEmployeeBtn').onclick = () => this.openDeleteEmployeeModal();
        document.getElementById('modifyEmployeeBtn').onclick = () => this.openModifyEmployeeModal();
    }
    
    openDeleteEmployeeModal() {
        if (!this.currentEmployee) return;
        
        // Populate delete employee info
        document.getElementById('deleteEmployeeInfo').innerHTML = `
            <div style="text-align: center; padding: 15px; background: #fee; border: 1px solid #fcc; border-radius: 8px;">
                <h4>${this.currentEmployee.name}</h4>
                <p style="font-family: monospace; color: #666;">${this.currentEmployee.mac}</p>
                <p style="color: #999;">Status: ${this.currentEmployee.status}</p>
            </div>
        `;
        
        // Clear password field
        document.getElementById('deleteAdminPassword').value = '';
        
        this.closeModal('employeeDetailsModal');
        this.openModal('deleteEmployeeModal');
    }
    
    openModifyEmployeeModal() {
        if (!this.currentEmployee) return;
        
        // Pre-fill the form with current employee data
        document.getElementById('modifyEmployeeName').value = this.currentEmployee.name;
        document.getElementById('modifyEmployeeMac').value = this.currentEmployee.mac;
        document.getElementById('modifyEmployeePicture').value = this.currentEmployee.picture || '';
        document.getElementById('modifyAdminPassword').value = '';
        
        this.closeModal('employeeDetailsModal');
        this.openModal('modifyEmployeeModal');
    }
    
    async handleDeleteEmployee(e) {
        e.preventDefault();
        
        if (!this.currentEmployee) {
            this.showNotification('No employee selected', 'error');
            return;
        }
        
        const formData = new FormData(e.target);
        const password = formData.get('password');
        
        if (!password) {
            this.showNotification('Please enter admin password', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/delete_employee', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    employee_id: this.getEmployeeIdByMac(this.currentEmployee.mac),
                    password: password
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                this.closeModal('deleteEmployeeModal');
                await this.loadEmployees();
                await this.loadSummaryStats();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error deleting employee:', error);
            this.showNotification('Error deleting employee', 'error');
        }
    }
    
    async handleModifyEmployee(e) {
        e.preventDefault();
        
        if (!this.currentEmployee) {
            this.showNotification('No employee selected', 'error');
            return;
        }
        
        const formData = new FormData(e.target);
        const name = formData.get('name');
        const mac_address = formData.get('mac_address');
        const picture_path = formData.get('picture_path');
        const password = formData.get('password');
        
        if (!password) {
            this.showNotification('Please enter admin password', 'error');
            return;
        }
        
        if (!name || !mac_address) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/modify_employee', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    employee_id: this.getEmployeeIdByMac(this.currentEmployee.mac),
                    name: name,
                    mac_address: mac_address,
                    picture_path: picture_path,
                    password: password
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                this.closeModal('modifyEmployeeModal');
                await this.loadEmployees();
                await this.loadSummaryStats();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error modifying employee:', error);
            this.showNotification('Error modifying employee', 'error');
        }
    }
    
    getEmployeeIdByMac(mac) {
        // Since we don't have employee ID in the frontend data, we'll need to get it from the API
        // For now, we'll use the MAC address as identifier and let the backend handle the ID lookup
        return mac;
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const title = type.charAt(0).toUpperCase() + type.slice(1);
        notification.innerHTML = `
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        `;
        
        container.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Global functions for modal management
function closeModal(modalId) {
    if (window.attendanceTracker) {
        window.attendanceTracker.closeModal(modalId);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.attendanceTracker = new AttendanceTracker();
});

