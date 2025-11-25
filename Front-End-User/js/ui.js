// UI components and rendering logic
const ui = {
    pages: ['dashboard', 'devices', 'history', 'settings'],
    
    // Navigation
    initNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            const page = item.dataset.page;
            // Only attach nav handler to items that represent pages
            if (!page) return;
            item.addEventListener('click', (e) => {
                // Prevent navigation to protected pages when not authenticated
                if (page !== 'login' && window.app && !window.app.isAuthenticated) {
                    // show login page instead
                    this.showPage('login');
                    // optionally scroll to top
                    window.setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }), 100);
                    return;
                }
                this.showPage(page);
                // Trigger page-specific data loading
                if (window.app) {
                    // Stop any existing refresh intervals
                    if (window.app.devicesRefreshInterval) {
                        clearInterval(window.app.devicesRefreshInterval);
                        window.app.devicesRefreshInterval = null;
                    }
                    
                    // Use setTimeout to ensure page is rendered before loading data
                    setTimeout(() => {
                        if (page === 'devices') {
                            window.app.loadDevices();
                            // Start auto-refresh for devices page (every 5 seconds)
                            window.app.devicesRefreshInterval = setInterval(() => {
                                window.app.loadDevices();
                            }, 5000);
                        }
                        else if (page === 'history') window.app.loadHistory();
                        else if (page === 'settings') window.app.loadSettings();
                    }, 0);
                }
            });
        });
    },

    showPage(pageId) {
        // If trying to access a protected page while unauthenticated, force login
        const protectedPages = ['dashboard', 'devices', 'history', 'settings'];
        if (protectedPages.includes(pageId) && window.app && !window.app.isAuthenticated) {
            pageId = 'login';
        }
        
        // Clear password field when navigating away from login page
        if (pageId !== 'login') {
            const passwordField = document.getElementById('password');
            if (passwordField) {
                passwordField.value = '';
            }
        }
        
        // Update navigation active state
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === pageId);
        });

        // Show selected page element (ids are like 'dashboard-page')
        const targetPageId = `${pageId}-page`;
        
        document.querySelectorAll('.page').forEach(page => {
            const isActive = page.id === targetPageId;
            page.classList.toggle('active', isActive);
        });
    },

    // Alerts
    renderAlert(alert) {
        return `
            <div class="alert-item ${alert.level.toLowerCase()}">
                <div class="alert-icon ${alert.level.toLowerCase()}">
                    ${this.getAlertIcon(alert.level)}
                </div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title || 'Alert'}</div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-meta">
                        ${alert.location} • ${new Date(alert.created_at).toLocaleString()}
                        ${!alert.acknowledged ? `
                            <button class="alert-ack-btn" data-alert-id="${alert.id}">
                                Acknowledge
                            </button>
                        ` : '<span class="acknowledged-badge">Acknowledged</span>'}
                    </div>
                </div>
            </div>
        `;
    },

    getAlertIcon(level) {
        switch(level.toLowerCase()) {
            case 'critical': return '!';
            case 'warning': return '!';
            case 'info': return 'i';
            default: return '*';
        }
    },

    // Devices
    renderDevice(device) {
        // Handle both registered device format and sensor reading format
        const deviceValue = device.current_value !== undefined ? device.current_value : device.value;
        const lastUpdate = device.last_reading || device.last_seen || device.last_update;
        const deviceName = device.name || `${device.type.capitalize()} - ${device.location}`;
        
        // Format the device value based on type
        let valueDisplay = deviceValue !== undefined ? deviceValue : 'N/A';
        if (device.type === 'temp' && deviceValue !== undefined) {
            valueDisplay = `${deviceValue}°C`;
        } else if (device.type === 'door' || device.type === 'window' || device.type === 'garage') {
            valueDisplay = deviceValue === 'open' ? 'Open' : deviceValue === 'closed' ? 'Closed' : 'N/A';
        } else if (device.type === 'smoke' || device.type === 'fire' || device.type === 'co' || device.type === 'gas') {
            valueDisplay = deviceValue !== undefined ? `${deviceValue} ppm` : 'N/A';
        } else if (device.type === 'water') {
            valueDisplay = deviceValue > 0 ? 'Detected' : deviceValue === 0 ? 'No Water' : 'N/A';
        }
        
        return `
            <div class="device-card">
                <div class="device-header">
                    <span class="device-name">${deviceName}</span>
                    <span class="device-status ${device.online ? 'online' : device.paired ? 'offline' : 'unpaired'}">
                        ${device.online ? 'Online' : device.paired ? 'Offline' : 'Unpaired'}
                    </span>
                </div>
                <div class="device-info">
                    <div class="device-type">${device.type.toUpperCase()}</div>
                    <div class="device-location">${device.location}</div>
                </div>
                <div class="device-reading">
                    <div class="reading-label">Current Value</div>
                    <div class="reading-value">${valueDisplay}</div>
                </div>
                <div class="device-details">
                    <div class="detail-item">
                        <div class="detail-label">Battery</div>
                        <div class="detail-value">${device.battery || 100}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Last Update</div>
                        <div class="detail-value">${lastUpdate ? new Date(lastUpdate).toLocaleTimeString() : 'Never'}</div>
                    </div>
                </div>
                <div class="device-actions">
                    <button class="device-edit-btn" data-device-id="${device.device_id || device.id}" data-device='${JSON.stringify(device).replace(/'/g, "&apos;")}'>
                        Edit
                    </button>
                </div>
            </div>
        `;
    },

    renderDashboardDevice(device) {
        const deviceValue = device.current_value !== undefined ? device.current_value : device.value;
        const deviceName = device.name || `${device.type.capitalize()} - ${device.location}`;
        
        // Format the device value based on type
        let valueDisplay = deviceValue !== undefined ? deviceValue : 'N/A';
        if (device.type === 'temp' && deviceValue !== undefined) {
            valueDisplay = `${deviceValue}°C`;
        } else if (device.type === 'door' || device.type === 'window' || device.type === 'garage') {
            valueDisplay = deviceValue === 'open' ? 'Open' : deviceValue === 'closed' ? 'Closed' : 'N/A';
        } else if (device.type === 'smoke' || device.type === 'fire' || device.type === 'co' || device.type === 'gas') {
            valueDisplay = deviceValue !== undefined ? `${deviceValue} ppm` : 'N/A';
        } else if (device.type === 'water') {
            valueDisplay = deviceValue > 0 ? 'Detected' : deviceValue === 0 ? 'No Water' : 'N/A';
        }
        
        return `
            <div class="dashboard-device-item">
                <div class="dashboard-device-header">
                    <span class="dashboard-device-name">${deviceName}</span>
                    <span class="device-status ${device.online ? 'online' : 'offline'}">
                        ${device.online ? 'Online' : 'Offline'}
                    </span>
                </div>
                <div class="dashboard-device-info">
                    <span class="dashboard-device-type">${device.type.toUpperCase()}</span>
                    <span class="dashboard-device-value">${valueDisplay}</span>
                </div>
            </div>
        `;
    },

    // History
    renderHistoryEntry(entry) {
        return `
            <tr>
                <td>${new Date(entry.created_at).toLocaleString()}</td>
                <td>
                    <span class="badge ${entry.level.toLowerCase()}">
                        ${entry.level}
                    </span>
                </td>
                <td>${entry.location}</td>
                <td>${entry.message}</td>
                <td>${entry.acknowledged ? 'Acknowledged' : 'Open'}</td>
            </tr>
        `;
    },

    // Utils
    showError(message) {
        const error = document.getElementById('login-error');
        error.textContent = message;
        error.style.display = 'block';
    },

    hideError() {
        const error = document.getElementById('login-error');
        error.style.display = 'none';
    }
};