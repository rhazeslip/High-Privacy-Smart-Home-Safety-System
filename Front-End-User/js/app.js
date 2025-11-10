// Main application logic
const app = {
    alerts: [],
    devices: [],
    updateInterval: null,
    isAuthenticated: false,

    async init() {
        // Initialize UI
        ui.initNavigation();
        this.initEventListeners();
        // Check authentication (simple cookie presence check)
        const isLoggedIn = document.cookie.includes('hp_token');
        this.isAuthenticated = !!isLoggedIn;
        this.setAuthUI(this.isAuthenticated);

        if (this.isAuthenticated) {
            await this.startDashboard();
        } else {
            ui.showPage('login');
        }
    },

    setAuthUI(isAuth) {
        const sidebar = document.querySelector('.sidebar');
        const logoutBtn = document.getElementById('logout');
        if (sidebar) sidebar.classList.toggle('hide', !isAuth);
        if (logoutBtn) logoutBtn.classList.toggle('hide', !isAuth);
        // Ensure login page is visible when unauthenticated
        if (!isAuth) ui.showPage('login');
    },

    initEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleLogin();
        });

        // Logout
        document.getElementById('logout').addEventListener('click', () => this.handleLogout());

        // System arm/disarm
        document.getElementById('arm-system').addEventListener('click', () => this.toggleSystemArm());

        // Mode selection
        document.getElementById('mode').addEventListener('change', (e) => this.updateMode(e.target.value));

        // Alert filters
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => this.filterAlerts(btn.dataset.filter));
        });

        // Settings form
        document.getElementById('settings-page').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });
    },

    async handleLogin() {
        try {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            await api.login(username, password);
            // Mark authenticated and update UI
            this.isAuthenticated = true;
            this.setAuthUI(true);
            await this.startDashboard();
        } catch (err) {
            ui.showError(err.message);
        }
    },

    async handleLogout() {
        try {
            await api.logout();
            clearInterval(this.updateInterval);
            this.isAuthenticated = false;
            this.setAuthUI(false);
            ui.showPage('login');
        } catch (err) {
            console.error('Logout failed:', err);
        }
    },

    async startDashboard() {
        ui.showPage('dashboard');
        await this.updateDashboard();
        
        // Start real-time updates every 3 seconds for more responsive alerts
        this.updateInterval = setInterval(() => {
            this.updateDashboard();
        }, 3000);
    },

    async updateDashboard() {
        try {
            const [status, alerts] = await Promise.all([
                api.getStatus(),
                api.getAlerts()
            ]);

            // Update status cards
            document.getElementById('sensors-online').textContent = status.sensors_online;
            // Correct ID for active alerts count
            const activeCountEl = document.getElementById('active-alert-count');
            if (activeCountEl) activeCountEl.textContent = alerts.length;

            // Update alerts list and stream
            this.alerts = alerts;
            this.renderAlerts();

            // Update last update time
            document.getElementById('last-update-time').textContent = new Date().toLocaleTimeString();
        } catch (err) {
            console.error('Dashboard update failed:', err);
        }
    },

    renderAlerts() {
        // Main alerts list - only update if alerts changed
        const alertsList = document.getElementById('alerts-list');
        const currentAlertIds = new Set(
            Array.from(alertsList.querySelectorAll('.alert-item'))
                .map(el => el.dataset.alertId)
        );
        
        const newAlertIds = new Set(this.alerts.map(a => a.id));
        
        // Only re-render if the alerts have actually changed
        const alertsChanged = this.alerts.length !== currentAlertIds.size ||
            !this.alerts.every(a => currentAlertIds.has(a.id));
        
        if (alertsChanged) {
            alertsList.innerHTML = this.alerts.length ? 
                this.alerts.map(alert => ui.renderAlert(alert)).join('') :
                '<div class="empty-state">No active alerts</div>';
        }

        // Real-time stream - only update if changed
        const alertsStream = document.getElementById('alerts-stream');
        const streamAlertIds = new Set(
            Array.from(alertsStream.querySelectorAll('.alert-item'))
                .map(el => el.dataset.alertId)
        );
        
        const streamAlerts = this.alerts
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 10);
        
        const streamChanged = streamAlerts.length !== streamAlertIds.size ||
            !streamAlerts.every(a => streamAlertIds.has(a.id));
        
        if (streamChanged) {
            alertsStream.innerHTML = streamAlerts
                .map(alert => ui.renderAlert(alert))
                .join('');
        }

        // Update counter
        document.getElementById('active-alert-count').textContent = this.alerts.length;

        // Attach event listeners to acknowledge buttons using event delegation
        this.attachAckButtonListeners();
    },

    attachAckButtonListeners() {
        // Use event delegation to handle dynamically created buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.alert-ack-btn')) {
                const alertId = e.target.dataset.alertId;
                if (alertId) this.acknowledgeAlert(alertId);
            }
        }, { once: false });
    },

    async acknowledgeAlert(alertId) {
        try {
            await api.acknowledgeAlert(alertId);
            await this.updateDashboard();
        } catch (err) {
            console.error('Failed to acknowledge alert:', err);
        }
    },

    async loadDevices() {
        try {
            const devices = await api.getDevices();
            const devicesGrid = document.getElementById('devices-grid');
            devicesGrid.innerHTML = devices.length ?
                devices.map(device => ui.renderDevice(device)).join('') :
                '<div class="empty-state">No devices connected</div>';
        } catch (err) {
            console.error('Failed to load devices:', err);
        }
    },

    async loadHistory() {
        try {
            const history = await api.getAlertHistory();
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = history.length ?
                history.map(entry => ui.renderHistoryEntry(entry)).join('') :
                '<tr><td colspan="5" class="empty-state">No history available</td></tr>';
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    },

    async loadSettings() {
        try {
            const settings = await api.getSettings();
            // Populate settings form with current values
            if (settings.armed) document.getElementById('arm-system').checked = true;
            if (settings.mode) document.getElementById('mode').value = settings.mode;
            if (settings.notify_email) document.getElementById('notify_email').value = settings.notify_email;
            if (settings.notify_critical !== undefined) document.getElementById('notify_critical').checked = settings.notify_critical;
            if (settings.notify_all !== undefined) document.getElementById('notify_all').checked = settings.notify_all;
            if (settings.auto_arm !== undefined) document.getElementById('auto_arm').value = settings.auto_arm;
            if (settings.auto_night_mode !== undefined) document.getElementById('auto_night_mode').checked = settings.auto_night_mode;
        } catch (err) {
            console.error('Failed to load settings:', err);
        }
    },

    toggleSystemArm() {
        const armCheckbox = document.getElementById('arm-system');
        const isArmed = armCheckbox.checked;
        console.log(`System ${isArmed ? 'armed' : 'disarmed'}`);
        // Could trigger an API call to update backend state if needed
    },

    updateMode(mode) {
        console.log(`Mode changed to: ${mode}`);
        // Could trigger an API call to update backend state if needed
    },

    filterAlerts(filter) {
        // Update active filter button
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });

        // Filter alerts
        const filtered = filter === 'all' ?
            this.alerts :
            this.alerts.filter(alert => alert.level.toLowerCase() === filter);
        
        // Update display
        document.getElementById('alerts-list').innerHTML = filtered.length ?
            filtered.map(alert => ui.renderAlert(alert)).join('') :
            '<div class="empty-state">No matching alerts</div>';
    },

    async saveSettings() {
        try {
            const settings = {
                armed: document.getElementById('arm-system').checked,
                mode: document.getElementById('mode').value,
                notify_email: document.getElementById('notify_email').value,
                notify_critical: document.getElementById('notify_critical').checked,
                notify_all: document.getElementById('notify_all').checked,
                auto_arm: parseInt(document.getElementById('auto_arm').value) || 0,
                auto_night_mode: document.getElementById('auto_night_mode').checked
            };

            await api.updateSettings(settings);
            alert('Settings saved successfully');
        } catch (err) {
            console.error('Failed to save settings:', err);
            alert('Failed to save settings');
        }
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => app.init());