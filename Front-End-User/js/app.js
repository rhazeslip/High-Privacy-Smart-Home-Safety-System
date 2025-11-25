// Main application logic
const app = {
    alerts: [],
    devices: [],
    updateInterval: null,
    devicesRefreshInterval: null,
    isAuthenticated: false,
    setupComplete: false,
    recoveryKey: null,

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
                console.log('Setup not complete, showing wizard');
                const sidebar = document.querySelector('.sidebar');
                if (sidebar) sidebar.style.display = 'none';
                ui.showPage('setup');
                this.setupNextStep(1);
                return;
            }
        } catch (err) {
            console.error('Failed to check setup status:', err);
            // If we can't check status, assume setup needed
            console.log('Setup check failed, showing wizard');
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
        const refreshBtn = document.getElementById('refresh-registered-btn');
        if (scanBtn) scanBtn.addEventListener('click', () => this.scanForDevices());
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadRegisteredDevices());
        
        // Device Setup Modal
        const openDeviceSetupBtn = document.getElementById('open-device-setup-btn');
        const closeDeviceSetupBtn = document.getElementById('close-device-setup-btn');
        const deviceSetupModal = document.getElementById('device-setup-modal');
        
        if (openDeviceSetupBtn) {
            openDeviceSetupBtn.addEventListener('click', () => {
                deviceSetupModal.classList.add('active');
                this.loadRegisteredDevices(); // Load current devices when opening
            });
        }
        
        if (closeDeviceSetupBtn) {
            closeDeviceSetupBtn.addEventListener('click', () => {
                deviceSetupModal.classList.remove('active');
            });
        }
        
        // Close modal when clicking outside
        if (deviceSetupModal) {
            deviceSetupModal.addEventListener('click', (e) => {
                if (e.target === deviceSetupModal) {
                    deviceSetupModal.classList.remove('active');
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
                } finally {
                    refreshDevicesBtn.disabled = false;
                    refreshDevicesBtn.textContent = 'Refresh';
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
            
            console.log('Attempting login...');
            await api.login(password);
            console.log('Login successful, updating UI...');
            
            // Mark authenticated and update UI
            this.isAuthenticated = true;
            console.log('Set isAuthenticated to:', this.isAuthenticated);
            console.log('window.app.isAuthenticated:', window.app.isAuthenticated);
            
            this.setAuthUI(true);
            
            console.log('Starting dashboard...');
            await this.startDashboard();
            console.log('Dashboard started');
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
        console.log('startDashboard: calling ui.showPage(dashboard)');
        ui.showPage('dashboard');
        console.log('startDashboard: calling updateDashboard');
        await this.updateDashboard();
        console.log('startDashboard: updateDashboard complete');
        
        // Start real-time updates every 3 seconds for more responsive alerts
        this.updateInterval = setInterval(() => {
            this.updateDashboard();
        }, 3000);
        console.log('startDashboard: interval started');
    },

    async updateDashboard() {
        console.log('updateDashboard: starting');
        try {
            console.log('updateDashboard: fetching status, alerts, and devices');
            const [status, alerts, devices] = await Promise.all([
                api.getStatus(),
                api.getAlerts(),
                api.getDevices()
            ]);
            console.log('updateDashboard: received data', { status, alerts, devices });

            // Update status cards
            document.getElementById('sensors-online').textContent = status.sensors_online;
            
            // Update total devices count
            const totalDevicesEl = document.getElementById('total-devices');
            if (totalDevicesEl) totalDevicesEl.textContent = devices.length;

            // Update alerts list and stream
            this.alerts = alerts;
            this.renderAlerts();

            // Update last update time
            document.getElementById('last-update-time').textContent = new Date().toLocaleTimeString();
            console.log('updateDashboard: complete');
        } catch (err) {
            console.error('Dashboard update failed:', err);
            console.error('Error details:', err.message, err.stack);
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
            const devices = await api.getRegisteredDevices();
            // Filter to only show paired devices on the main devices page
            const pairedDevices = devices.filter(device => device.paired);
            const devicesGrid = document.getElementById('devices-grid');
            
            if (pairedDevices.length === 0) {
                devicesGrid.innerHTML = '<div class="empty-state">No devices registered yet. Click "Add Device" to get started.</div>';
                return;
            }
            
            devicesGrid.innerHTML = pairedDevices.map(device => ui.renderDevice(device)).join('');
        } catch (err) {
            console.error('Failed to load devices:', err);
            const devicesGrid = document.getElementById('devices-grid');
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

    displayDiscoveredDevices(devices) {
        const container = document.getElementById('discovered-devices');
        container.innerHTML = devices.map(device => `
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
                    <p><strong>Status:</strong> ${device.requires_pairing ? 'Not Paired' : 'Paired'}</p>
                </div>
                ${device.requires_pairing ? `
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
        `).join('');

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
                // Refresh both lists
                await this.scanForDevices();
                await this.loadRegisteredDevices();
            } else {
                alert(`Pairing failed: ${result.message}`);
            }
        } catch (err) {
            alert(`Pairing failed: ${err.message}`);
            console.error('Pairing error:', err);
        }
    },

    async loadRegisteredDevices() {
        try {
            const devices = await api.getRegisteredDevices();
            const container = document.getElementById('registered-devices');
            
            if (devices.length === 0) {
                container.innerHTML = '<p class="empty-state">No devices registered yet.</p>';
                return;
            }

            container.innerHTML = devices.map(device => `
                <div class="device-card registered">
                    <div class="device-header">
                        <h4>${device.name}</h4>
                        <span class="device-badge ${device.online ? 'online' : device.paired ? 'offline' : 'unpaired'}">
                            ${device.online ? 'Online' : device.paired ? 'Offline' : 'Unpaired'}
                        </span>
                    </div>
                    <div class="device-details">
                        <p><strong>Type:</strong> ${device.type}</p>
                        <p><strong>Location:</strong> ${device.location}</p>
                        <p><strong>Port:</strong> ${device.port}</p>
                        <p><strong>Device ID:</strong> ${device.device_id}</p>
                        ${device.current_value ? `<p><strong>Current Value:</strong> ${device.current_value}</p>` : ''}
                        ${device.last_reading ? `<p><strong>Last Reading:</strong> ${new Date(device.last_reading).toLocaleString()}</p>` : ''}
                        <p><strong>Added:</strong> ${new Date(device.added_at).toLocaleString()}</p>
                    </div>
                    <div class="device-actions">
                        ${device.paired ? `
                            <button class="btn-warning unpair-btn" data-device-id="${device.device_id}">
                                Unpair Device
                            </button>
                        ` : `
                            <button class="btn-primary repair-btn" data-device-id="${device.device_id}" data-port="${device.port}">
                                Repair Device
                            </button>
                        `}
                        <button class="btn-danger remove-btn" data-device-id="${device.device_id}">
                            Remove Device
                        </button>
                    </div>
                </div>
            `).join('');

            // Add event listeners for unpair buttons
            container.querySelectorAll('.unpair-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const deviceId = btn.dataset.deviceId;
                    if (confirm(`Are you sure you want to unpair device ${deviceId}? You can repair it later.`)) {
                        await this.unpairDevice(deviceId);
                    }
                });
            });

            // Add event listeners for repair buttons
            container.querySelectorAll('.repair-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const deviceId = btn.dataset.deviceId;
                    const port = btn.dataset.port;
                    await this.repairDevice(deviceId, port);
                });
            });

            // Add event listeners for remove buttons
            container.querySelectorAll('.remove-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const deviceId = btn.dataset.deviceId;
                    if (confirm(`Are you sure you want to permanently remove device ${deviceId}?`)) {
                        await this.removeDevice(deviceId);
                    }
                });
            });
        } catch (err) {
            console.error('Failed to load registered devices:', err);
        }
    },

    async unpairDevice(deviceId) {
        try {
            await api.unpairDevice(deviceId);
            alert('Device unpaired successfully');
            await this.loadRegisteredDevices();
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
            await this.loadRegisteredDevices();
        } catch (err) {
            alert(`Failed to repair device: ${err.message}`);
            console.error('Repair device error:', err);
        }
    },

    async removeDevice(deviceId) {
        try {
            await api.removeDevice(deviceId);
            alert('Device removed successfully');
            await this.loadRegisteredDevices();
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
        
        try {
            // Call API to update device
            await api.updateDevice(deviceId, { name: newName, location: newLocation });
            
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
        
        console.log('Unpairing device:', { deviceId, deviceName, device });
        
        if (!confirm(`Are you sure you want to unpair "${deviceName}"? You can repair it later.`)) {
            return;
        }
        
        try {
            const result = await api.unpairDevice(deviceId);
            console.log('Unpair result:', result);
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
        
        console.log('Repairing device:', { deviceId, deviceName, port, device });
        
        const pairingCode = prompt(`Enter the pairing code for "${deviceName}" (port ${port}):`);
        if (!pairingCode) {
            return; // User cancelled
        }
        
        try {
            const result = await api.repairDevice(deviceId, port, pairingCode);
            console.log('Repair result:', result);
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
        
        console.log('Deleting device:', { deviceId, deviceName, device });
        
        if (!confirm(`Are you sure you want to permanently delete "${deviceName}"? This cannot be undone.`)) {
            return;
        }
        
        try {
            const result = await api.removeDevice(deviceId);
            console.log('Delete result:', result);
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
        console.log('Setup wizard: moving to step', step);
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
        const homeName = document.getElementById('setup-home-name').value;
        const password = document.getElementById('setup-password').value;
        const confirmPassword = document.getElementById('setup-confirm-password').value;

        // Validate
        if (!homeName) {
            alert('Please enter a home name');
            return;
        }

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