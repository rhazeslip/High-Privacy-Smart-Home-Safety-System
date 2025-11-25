// Main application logic
const app = {
    alerts: [],
    devices: [],
    updateInterval: null,
    devicesRefreshInterval: null,
    isAuthenticated: false,
    setupComplete: false,
    recoveryKey: null,
    _ackListenerAttached: false,

    async init() {
        // Initialize event listeners first (needed for setup wizard)
        this.initEventListeners();
        
        // Initialize theme
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.applyTheme(savedTheme);
        
        // Check setup status first
        try {
            const setupStatus = await api.getSetupStatus();
            this.setupComplete = setupStatus.setup_complete;
            
            if (!this.setupComplete) {
                // Show setup wizard
                const sidebar = document.querySelector('.sidebar');
                if (sidebar) sidebar.style.display = 'none';
                ui.showPage('setup');
                this.setupNextStep(1);
                return;
            }
        } catch (err) {
            // If we can't check status, assume setup needed
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) sidebar.style.display = 'none';
            ui.showPage('setup');
            this.setupNextStep(1);
            return;
        }

        // Initialize UI for normal operation
        ui.initNavigation();
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
        
        if (sidebar) {
            if (isAuth) {
                sidebar.style.display = 'flex';
                // Load and display home name
                this.loadHomeName();
            } else {
                sidebar.style.display = 'none';
            }
        }
        
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

        // Password reset links
        const showResetLink = document.getElementById('show-reset-link');
        const backToLoginLink = document.getElementById('back-to-login-link');
        
        if (showResetLink) {
            showResetLink.addEventListener('click', (e) => {
                e.preventDefault();
                ui.showPage('reset');
            });
        }
        
        if (backToLoginLink) {
            backToLoginLink.addEventListener('click', (e) => {
                e.preventDefault();
                ui.showPage('login');
            });
        }

        // Password reset form
        const resetForm = document.getElementById('reset-form');
        if (resetForm) {
            resetForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handlePasswordReset();
            });
        }

        // Logout
        document.getElementById('logout').addEventListener('click', () => this.handleLogout());

        // Hamburger menu toggle
        const hamburgerMenu = document.getElementById('hamburger-menu');
        const sidebar = document.querySelector('.sidebar');
        if (hamburgerMenu && sidebar) {
            hamburgerMenu.addEventListener('click', () => {
                sidebar.classList.toggle('mobile-open');
                hamburgerMenu.classList.toggle('active');
            });
            
            // Close sidebar when clicking outside on smaller screens
            document.addEventListener('click', (e) => {
                const isSmallScreen = window.innerWidth <= 900 || 
                    (window.innerHeight <= 600 && window.innerWidth <= 1200);
                if (isSmallScreen) {
                    if (!sidebar.contains(e.target) && !hamburgerMenu.contains(e.target)) {
                        sidebar.classList.remove('mobile-open');
                        hamburgerMenu.classList.remove('active');
                    }
                }
            });
        }

        // Alert filters
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => this.filterAlerts(btn.dataset.filter));
        });

        // Settings
        const saveSettingsBtn = document.getElementById('save-settings-btn');
        const changePasswordForm = document.getElementById('change-password-form');
        
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }
        
        if (changePasswordForm) {
            changePasswordForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.changePassword();
            });
        }

        // Device Setup Wizard
        const scanBtn = document.getElementById('scan-devices-btn');
        if (scanBtn) scanBtn.addEventListener('click', () => this.scanForDevices());
        
        // Device Setup Modal
        const openDeviceSetupBtn = document.getElementById('open-device-setup-btn');
        const closeDeviceSetupBtn = document.getElementById('close-device-setup-btn');
        const deviceSetupModal = document.getElementById('device-setup-modal');
        
        if (openDeviceSetupBtn) {
            openDeviceSetupBtn.addEventListener('click', () => {
                deviceSetupModal.classList.add('active');
                document.body.style.overflow = 'hidden';
            });
        }
        
        if (closeDeviceSetupBtn) {
            closeDeviceSetupBtn.addEventListener('click', () => {
                deviceSetupModal.classList.remove('active');
                document.body.style.overflow = '';
            });
        }
        
        // Close modal when clicking outside
        if (deviceSetupModal) {
            deviceSetupModal.addEventListener('click', (e) => {
                if (e.target === deviceSetupModal) {
                    deviceSetupModal.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });
        }
        
        // Setup wizard step navigation
        const step1NextBtn = document.getElementById('setup-step-1-next');
        const step2BackBtn = document.getElementById('setup-step-2-back');
        const step2CompleteBtn = document.getElementById('setup-step-2-complete');
        const copyRecoveryBtn = document.getElementById('copy-recovery-key-btn');
        const finishSetupBtn = document.getElementById('finish-setup-btn');
        
        if (step1NextBtn) step1NextBtn.addEventListener('click', () => this.setupNextStep(2));
        if (step2BackBtn) step2BackBtn.addEventListener('click', () => this.setupNextStep(1));
        if (step2CompleteBtn) step2CompleteBtn.addEventListener('click', () => this.completeSetup());
        if (copyRecoveryBtn) copyRecoveryBtn.addEventListener('click', () => this.copyRecoveryKey());
        if (finishSetupBtn) finishSetupBtn.addEventListener('click', () => this.finishSetup());
        
        // Setup wizard recovery confirmation
        const recoveryCheckbox = document.getElementById('recovery-confirmed');
        if (recoveryCheckbox) {
            recoveryCheckbox.addEventListener('change', (e) => {
                const finishBtn = document.getElementById('finish-setup-btn');
                if (finishBtn) finishBtn.disabled = !e.target.checked;
            });
        }
        
        // Device Edit Modal
        const closeDeviceEditBtn = document.getElementById('close-device-edit-btn');
        const deviceEditModal = document.getElementById('device-edit-modal');
        const deviceEditForm = document.getElementById('device-edit-form');
        const unpairDeviceBtn = document.getElementById('unpair-device-btn');
        const deleteDeviceBtn = document.getElementById('delete-device-btn');
        
        if (closeDeviceEditBtn) {
            closeDeviceEditBtn.addEventListener('click', () => {
                deviceEditModal.classList.remove('active');
            });
        }
        
        if (deviceEditModal) {
            deviceEditModal.addEventListener('click', (e) => {
                if (e.target === deviceEditModal) {
                    deviceEditModal.classList.remove('active');
                }
            });
        }
        
        if (deviceEditForm) {
            deviceEditForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveDeviceChanges();
            });
        }
        
        if (unpairDeviceBtn) {
            unpairDeviceBtn.addEventListener('click', () => {
                this.handleUnpairDevice();
            });
        }
        
        const repairDeviceBtn = document.getElementById('repair-device-btn');
        if (repairDeviceBtn) {
            repairDeviceBtn.addEventListener('click', () => {
                this.handleRepairDevice();
            });
        }
        
        if (deleteDeviceBtn) {
            deleteDeviceBtn.addEventListener('click', () => {
                this.handleDeleteDevice();
            });
        }
        
        // Refresh devices button
        const refreshDevicesBtn = document.getElementById('refresh-devices-btn');
        if (refreshDevicesBtn) {
            refreshDevicesBtn.addEventListener('click', async () => {
                refreshDevicesBtn.disabled = true;
                refreshDevicesBtn.textContent = 'Refreshing...';
                try {
                    await this.loadDevices();
                    // Brief success indicator
                    refreshDevicesBtn.textContent = 'Refreshed!';
                    setTimeout(() => {
                        refreshDevicesBtn.textContent = 'Refresh';
                    }, 1000);
                } catch (err) {
                    console.error('Refresh error:', err);
                    refreshDevicesBtn.textContent = 'Error';
                    setTimeout(() => {
                        refreshDevicesBtn.textContent = 'Refresh';
                    }, 2000);
                } finally {
                    refreshDevicesBtn.disabled = false;
                }
            });
        }
        
        // Delegate click events for device edit buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.device-edit-btn')) {
                const btn = e.target.closest('.device-edit-btn');
                const deviceData = JSON.parse(btn.dataset.device);
                this.openDeviceEditModal(deviceData);
            }
        });
    },

    async handleLogin() {
        const errorDiv = document.getElementById('login-error');
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
        
        try {
            const password = document.getElementById('password').value;
            
            await api.login(password);
            
            // Mark authenticated and update UI
            this.isAuthenticated = true;
            
            this.setAuthUI(true);
            
            await this.startDashboard();
        } catch (err) {
            console.error('Login failed:', err);
            errorDiv.textContent = err.message || 'Login failed';
            errorDiv.style.display = 'block';
        }
    },

    async handlePasswordReset() {
        const errorDiv = document.getElementById('reset-error');
        errorDiv.textContent = '';
        
        try {
            const recoveryKey = document.getElementById('reset-recovery-key').value;
            const newPassword = document.getElementById('reset-new-password').value;
            const confirmPassword = document.getElementById('reset-confirm-password').value;
            
            const result = await api.resetPassword(recoveryKey, newPassword, confirmPassword);
            
            if (result.success) {
                alert('Password reset successfully! Please login with your new password.');
                // Clear form
                document.getElementById('reset-form').reset();
                // Redirect to login
                ui.showPage('login');
            }
        } catch (err) {
            errorDiv.textContent = err.message;
        }
    },

    async handleLogout() {
        try {
            await api.logout();
            clearInterval(this.updateInterval);
            if (this.devicesRefreshInterval) {
                clearInterval(this.devicesRefreshInterval);
                this.devicesRefreshInterval = null;
            }
            this.isAuthenticated = false;
            this.setAuthUI(false);
            ui.showPage('login');
        } catch (err) {
            console.error('Logout failed:', err);
        }
    },

    async startDashboard() {
        ui.showPage('dashboard');
        // Ping devices to get current values before first update
        await api.refreshDevices().catch(() => {}); // Don't fail if refresh fails
        await this.updateDashboard();
        
        // Start real-time updates every 3 seconds for more responsive alerts
        this.updateInterval = setInterval(() => {
            this.updateDashboard();
        }, 3000);
    },

    async updateDashboard() {
        try {
            const [status, alerts, devices] = await Promise.all([
                api.getStatus(),
                api.getAlerts(),
                api.getRegisteredDevices()
            ]);

            // Update status cards
            document.getElementById('sensors-online').textContent = status.sensors_online;
            
            // Update total devices count (only paired devices)
            const pairedDevices = devices.filter(d => d.paired);
            const totalDevicesEl = document.getElementById('total-devices');
            if (totalDevicesEl) totalDevicesEl.textContent = pairedDevices.length;

            // Update alerts list
            this.alerts = alerts;
            this.renderAlerts();
            
            // Update device status display
            this.renderDashboardDevices(devices);

            // Update last update time
            const lastUpdateEl = document.getElementById('last-update-time');
            if (lastUpdateEl) lastUpdateEl.textContent = new Date().toLocaleTimeString();
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
        
        // Remove alerts that no longer exist
        Array.from(alertsList.querySelectorAll('.alert-item')).forEach(el => {
            if (!newAlertIds.has(el.dataset.alertId)) {
                el.remove();
            }
        });
        
        // Add new alerts
        this.alerts.forEach(alert => {
            if (!currentAlertIds.has(alert.id)) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = ui.renderAlert(alert);
                alertsList.appendChild(tempDiv.firstElementChild);
            }
        });
        
        // Handle empty state
        if (this.alerts.length === 0 && alertsList.children.length === 0) {
            alertsList.innerHTML = '<div class="empty-state">No active alerts</div>';
        } else if (this.alerts.length > 0) {
            // Remove empty state if it exists
            const emptyState = alertsList.querySelector('.empty-state');
            if (emptyState) emptyState.remove();
        }

        // Update counter
        const counterEl = document.getElementById('active-alert-count');
        if (counterEl) counterEl.textContent = this.alerts.length;

        // Attach event listeners to acknowledge buttons using event delegation
        this.attachAckButtonListeners();
    },

    renderDashboardDevices(devices) {
        const dashboardDevices = document.getElementById('dashboard-devices');
        if (!dashboardDevices) return;
        
        const pairedDevices = devices.filter(d => d.paired);
        
        if (pairedDevices.length === 0) {
            dashboardDevices.innerHTML = '<div class="empty-state">No devices paired</div>';
            return;
        }
        
        dashboardDevices.innerHTML = pairedDevices.map(device => ui.renderDashboardDevice(device)).join('');
    },

    attachAckButtonListeners() {
        // Use event delegation to handle dynamically created buttons
        // Only attach once during initialization
        if (!this._ackListenerAttached) {
            document.addEventListener('click', (e) => {
                if (e.target.matches('.alert-ack-btn')) {
                    const alertId = e.target.dataset.alertId;
                    if (alertId) this.acknowledgeAlert(alertId);
                }
            });
            this._ackListenerAttached = true;
        }
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
        const devicesGrid = document.getElementById('devices-grid');
        
        // Only render if we're on the devices page
        if (!devicesGrid) return;
        
        try {
            // Try to ping devices for current values, but don't fail if it doesn't work
            try {
                await api.refreshDevices();
            } catch (refreshErr) {
                console.warn('Could not refresh devices:', refreshErr);
            }
            
            const devices = await api.getRegisteredDevices();
            console.log('Loaded devices from backend:', devices);
            
            // Filter to only show paired devices on the main devices page
            const pairedDevices = devices.filter(device => device.paired);
            console.log('Paired devices:', pairedDevices);
            
            if (pairedDevices.length === 0) {
                devicesGrid.innerHTML = '<div class="empty-state">No devices registered yet. Click "Add Device" to get started.</div>';
                return;
            }
            
            devicesGrid.innerHTML = pairedDevices.map(device => ui.renderDevice(device)).join('');
        } catch (err) {
            console.error('Failed to load devices:', err);
            if (devicesGrid) {
                devicesGrid.innerHTML = '<div class="empty-state">Failed to load devices</div>';
            }
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
            
            // Load home name
            if (settings.home_name) {
                const homeNameInput = document.getElementById('setting-home-name');
                if (homeNameInput) homeNameInput.value = settings.home_name;
            }
            
            // Load theme (default to dark)
            const theme = localStorage.getItem('theme') || 'dark';
            const themeSelect = document.getElementById('setting-theme');
            if (themeSelect) themeSelect.value = theme;
        } catch (err) {
            console.error('Failed to load settings:', err);
        }
    },
    
    async loadHomeName() {
        try {
            const settings = await api.getSettings();
            const homeNameDisplay = document.getElementById('home-name-display');
            if (homeNameDisplay && settings.home_name) {
                homeNameDisplay.textContent = settings.home_name;
            }
        } catch (err) {
            console.error('Failed to load home name:', err);
        }
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
            const homeNameInput = document.getElementById('setting-home-name');
            const themeSelect = document.getElementById('setting-theme');
            
            if (!homeNameInput || !themeSelect) return;
            
            const homeName = homeNameInput.value;
            const theme = themeSelect.value;
            
            // Save home name to backend
            if (homeName) {
                await api.updateSettings({ home_name: homeName });
                // Update sidebar display
                const homeNameDisplay = document.getElementById('home-name-display');
                if (homeNameDisplay) homeNameDisplay.textContent = homeName;
            }
            
            // Save theme to localStorage and apply
            localStorage.setItem('theme', theme);
            this.applyTheme(theme);
            
            alert('Settings saved successfully!');
        } catch (err) {
            console.error('Failed to save settings:', err);
            alert('Failed to save settings: ' + err.message);
        }
    },
    
    async changePassword() {
        const errorDiv = document.getElementById('password-change-error');
        if (!errorDiv) return;
        
        errorDiv.textContent = '';
        
        try {
            const currentPassword = document.getElementById('setting-current-password').value;
            const newPassword = document.getElementById('setting-new-password').value;
            const confirmPassword = document.getElementById('setting-confirm-password').value;
            
            if (newPassword !== confirmPassword) {
                errorDiv.textContent = 'New passwords do not match';
                return;
            }
            
            if (newPassword.length < 8) {
                errorDiv.textContent = 'Password must be at least 8 characters';
                return;
            }
            
            // Call API to change password
            await api.changePassword(currentPassword, newPassword);
            
            alert('Password changed successfully!');
            document.getElementById('change-password-form').reset();
        } catch (err) {
            errorDiv.textContent = err.message || 'Failed to change password';
        }
    },
    
    applyTheme(theme) {
        // Apply theme class to body element
        if (theme === 'light') {
            document.body.classList.add('light-theme');
            document.body.classList.remove('dark-theme');
        } else if (theme === 'dark' || !theme) {
            document.body.classList.add('dark-theme');
            document.body.classList.remove('light-theme');
        } else {
            // Auto - detect system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
                document.body.classList.add('dark-theme');
                document.body.classList.remove('light-theme');
            } else {
                document.body.classList.add('light-theme');
                document.body.classList.remove('dark-theme');
            }
        }
    },

    async scanForDevices() {
        const scanBtn = document.getElementById('scan-devices-btn');
        const statusDiv = document.getElementById('scan-status');
        
        // Intelligent defaults: scan common device ports
        const startPort = 8080;
        const count = 50; // Scan 50 ports (8080-8129) to cover typical device range

        try {
            scanBtn.disabled = true;
            scanBtn.textContent = 'Scanning...';
            if (statusDiv) statusDiv.innerHTML = '<p class="info">Scanning for devices on your network...</p>';

            const result = await api.discoverDevices(startPort, count);
            
            if (result.devices.length === 0) {
                if (statusDiv) statusDiv.innerHTML = `<p class="warning">No devices found. Scanned ports ${startPort}-${startPort + count - 1}.</p>`;
                document.getElementById('discovered-devices').innerHTML = '<p class="empty-state">No devices discovered.</p>';
            } else {
                if (statusDiv) statusDiv.innerHTML = `<p class="success">Found ${result.devices.length} device(s)!</p>`;
                this.displayDiscoveredDevices(result.devices);
            }
        } catch (err) {
            if (statusDiv) statusDiv.innerHTML = `<p class="error">Scan failed: ${err.message}</p>`;
            console.error('Device scan failed:', err);
        } finally {
            scanBtn.disabled = false;
            scanBtn.textContent = 'Scan for Devices';
        }
    },

    async displayDiscoveredDevices(devices) {
        const container = document.getElementById('discovered-devices');
        
        // Check backend database for which devices are actually paired
        let registeredDevices = [];
        try {
            registeredDevices = await api.getRegisteredDevices();
        } catch (err) {
            console.warn('Could not fetch registered devices:', err);
        }
        
        // Create a map of device_id -> paired status from backend (source of truth)
        const pairedMap = {};
        registeredDevices.forEach(d => {
            pairedMap[d.device_id] = d.paired;
        });
        
        container.innerHTML = devices.map(device => {
            // Use backend database as source of truth for pairing status
            const isPaired = pairedMap[device.device_id] === true;
            
            return `
            <div class="device-card discovered">
                <div class="device-header">
                    <h4>${device.type.toUpperCase()}</h4>
                    <span class="device-badge">Port ${device.port}</span>
                </div>
                <div class="device-details">
                    <p><strong>Device ID:</strong> ${device.device_id}</p>
                    <p><strong>Type:</strong> ${device.type}</p>
                    <p><strong>Model:</strong> ${device.model}</p>
                    <p><strong>Firmware:</strong> ${device.firmware_version}</p>
                    <p><strong>Status:</strong> ${isPaired ? 'Paired' : 'Not Paired'}</p>
                </div>
                ${!isPaired ? `
                    <div class="device-actions">
                        <input type="text" 
                               class="device-name-input" 
                               id="device-name-${device.device_id}" 
                               placeholder="Device Name (e.g., Front Door)"
                               required>
                        <input type="text" 
                               class="device-location-input" 
                               id="device-location-${device.device_id}" 
                               placeholder="Location (e.g., Entrance)"
                               required>
                        <input type="text" 
                               class="pairing-code-input" 
                               id="pairing-code-${device.device_id}" 
                               placeholder="Pairing Code"
                               maxlength="6">
                        <button class="btn-primary pair-btn" 
                                data-device-id="${device.device_id}" 
                                data-port="${device.port}">
                            Pair Device
                        </button>
                    </div>
                ` : '<p class="success">Already paired</p>'}
            </div>
        `}).join('');

        // Add event listeners for pair buttons
        container.querySelectorAll('.pair-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const deviceId = btn.dataset.deviceId;
                const port = parseInt(btn.dataset.port);
                const nameInput = document.getElementById(`device-name-${deviceId}`);
                const locationInput = document.getElementById(`device-location-${deviceId}`);
                const pairingCodeInput = document.getElementById(`pairing-code-${deviceId}`);
                
                const name = nameInput ? nameInput.value.trim() : null;
                const location = locationInput ? locationInput.value.trim() : null;
                const pairingCode = pairingCodeInput ? pairingCodeInput.value : null;
                
                if (!name || !location) {
                    alert('Please enter both device name and location');
                    return;
                }
                
                this.pairDevice(deviceId, port, pairingCode, name, location);
            });
        });
    },

    async pairDevice(deviceId, port, pairingCode, name, location) {
        try {
            const result = await api.pairDevice(deviceId, port, pairingCode, name, location);
            if (result.success) {
                alert(`Device ${name} paired successfully!`);
                // Close the modal
                const modal = document.getElementById('device-setup-modal');
                if (modal) {
                    modal.style.display = 'none';
                    modal.classList.remove('active');
                    document.body.style.overflow = '';
                }
                // Reload devices page if we're on it
                await this.loadDevices();
            } else {
                alert(`Pairing failed: ${result.message}`);
            }
        } catch (err) {
            alert(`Pairing failed: ${err.message}`);
            console.error('Pairing error:', err);
        }
    },

    async unpairDevice(deviceId) {
        try {
            await api.unpairDevice(deviceId);
            alert('Device unpaired successfully');
        } catch (err) {
            alert(`Failed to unpair device: ${err.message}`);
            console.error('Unpair device error:', err);
        }
    },

    async repairDevice(deviceId, port) {
        const pairingCode = prompt(`Enter the pairing code for device ${deviceId}:`);
        if (!pairingCode) return;

        try {
            await api.repairDevice(deviceId, port, pairingCode);
            alert('Device repaired successfully');
        } catch (err) {
            alert(`Failed to repair device: ${err.message}`);
            console.error('Repair device error:', err);
        }
    },

    async removeDevice(deviceId) {
        try {
            await api.removeDevice(deviceId);
            alert('Device removed successfully');
        } catch (err) {
            alert(`Failed to remove device: ${err.message}`);
            console.error('Remove device error:', err);
        }
    },

    // Device Edit Modal Methods
    openDeviceEditModal(device) {
        this.currentEditingDevice = device;
        
        // Populate form fields
        document.getElementById('edit-device-name').value = device.name || '';
        document.getElementById('edit-device-location').value = device.location || '';
        document.getElementById('edit-device-id').textContent = device.device_id || device.id;
        document.getElementById('edit-device-type').textContent = device.type || 'Unknown';
        document.getElementById('edit-device-port').textContent = device.port || 'N/A';
        document.getElementById('edit-device-paired').textContent = device.paired ? 'Paired' : 'Unpaired';
        
        // Show/hide appropriate buttons based on paired status
        const unpairBtn = document.getElementById('unpair-device-btn');
        const repairBtn = document.getElementById('repair-device-btn');
        
        if (device.paired) {
            unpairBtn.style.display = 'block';
            repairBtn.style.display = 'none';
        } else {
            unpairBtn.style.display = 'none';
            repairBtn.style.display = 'block';
        }
        
        // Show modal
        const modal = document.getElementById('device-edit-modal');
        if (modal) modal.classList.add('active');
    },

    async saveDeviceChanges() {
        const deviceId = this.currentEditingDevice.device_id || this.currentEditingDevice.id;
        const newName = document.getElementById('edit-device-name').value.trim();
        const newLocation = document.getElementById('edit-device-location').value.trim();
        
        if (!newName || !newLocation) {
            alert('Please fill in all fields');
            return;
        }
        
        // Validate name and location length
        if (newName.length < 2 || newName.length > 50) {
            alert('Device name must be between 2 and 50 characters');
            return;
        }
        
        if (newLocation.length < 2 || newLocation.length > 50) {
            alert('Location must be between 2 and 50 characters');
            return;
        }
        
        // Basic sanitization - remove potentially dangerous characters
        const sanitize = (str) => str.replace(/[<>"']/g, '');
        const sanitizedName = sanitize(newName);
        const sanitizedLocation = sanitize(newLocation);
        
        try {
            // Call API to update device
            await api.updateDevice(deviceId, { name: sanitizedName, location: sanitizedLocation });
            
            alert('Device updated successfully');
            
            // Close modal
            const modal = document.getElementById('device-edit-modal');
            if (modal) modal.classList.remove('active');
            
            // Refresh devices list
            await this.loadDevices();
        } catch (err) {
            alert(`Failed to update device: ${err.message}`);
            console.error('Update device error:', err);
        }
    },

    async handleUnpairDevice() {
        const device = this.currentEditingDevice;
        const deviceId = device.device_id || device.id;
        const deviceName = device.name;
        
        if (!confirm(`Are you sure you want to unpair "${deviceName}"? You can repair it later.`)) {
            return;
        }
        
        try {
            const result = await api.unpairDevice(deviceId);
            alert('Device unpaired successfully');
            
            // Close modal
            const modal = document.getElementById('device-edit-modal');
            if (modal) modal.classList.remove('active');
            
            // Refresh devices list
            await this.loadDevices();
        } catch (err) {
            alert(`Failed to unpair device: ${err.message}`);
            console.error('Unpair device error:', err);
        }
    },

    async handleRepairDevice() {
        const device = this.currentEditingDevice;
        const deviceId = device.device_id || device.id;
        const deviceName = device.name;
        const port = device.port;
        
        const pairingCode = prompt(`Enter the pairing code for "${deviceName}" (port ${port}):`);
        if (!pairingCode) {
            return; // User cancelled
        }
        
        try {
            const result = await api.repairDevice(deviceId, port, pairingCode);
            alert('Device repaired successfully');
            
            // Close modal
            const modal = document.getElementById('device-edit-modal');
            if (modal) modal.classList.remove('active');
            
            // Refresh devices list
            await this.loadDevices();
        } catch (err) {
            alert(`Failed to repair device: ${err.message}`);
            console.error('Repair device error:', err);
        }
    },

    async handleDeleteDevice() {
        const device = this.currentEditingDevice;
        const deviceId = device.device_id || device.id;
        const deviceName = device.name;
        
        if (!confirm(`Are you sure you want to permanently delete "${deviceName}"? This cannot be undone.`)) {
            return;
        }
        
        try {
            const result = await api.removeDevice(deviceId);
            alert('Device deleted successfully');
            
            // Close modal
            const modal = document.getElementById('device-edit-modal');
            if (modal) modal.classList.remove('active');
            
            // Refresh devices list
            await this.loadDevices();
        } catch (err) {
            alert(`Failed to delete device: ${err.message}`);
            console.error('Delete device error:', err);
        }
    },

    // Setup wizard methods
    setupNextStep(step) {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(s => s.classList.add('hidden'));
        // Show target step
        const targetStep = document.getElementById(`setup-step-${step}`);
        if (targetStep) {
            targetStep.classList.remove('hidden');
        } else {
            console.error('Setup step not found:', step);
        }
    },

    async completeSetup() {
        const homeNameInput = document.getElementById('setup-home-name').value.trim();
        const homeName = homeNameInput || 'My Home';
        const password = document.getElementById('setup-password').value;
        const confirmPassword = document.getElementById('setup-confirm-password').value;

        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return;
        }

        if (password.length < 8) {
            alert('Password must be at least 8 characters');
            return;
        }

        try {
            const result = await api.completeSetup(homeName, password, confirmPassword);
            
            if (result.success) {
                this.recoveryKey = result.recovery_key;
                document.getElementById('recovery-key-text').textContent = result.recovery_key;
                this.setupNextStep(3);
            } else {
                alert('Setup failed: ' + result.message);
            }
        } catch (err) {
            alert('Setup failed: ' + err.message);
            console.error('Setup error:', err);
        }
    },

    copyRecoveryKey() {
        const keyText = document.getElementById('recovery-key-text').textContent;
        navigator.clipboard.writeText(keyText).then(() => {
            alert('Recovery key copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
            alert('Failed to copy to clipboard. Please copy manually.');
        });
    },

    async finishSetup() {
        this.setupComplete = true;
        // Reload the page to start fresh with login
        window.location.reload();
    }
};

// Make app globally accessible for UI checks
window.app = app;

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => app.init());