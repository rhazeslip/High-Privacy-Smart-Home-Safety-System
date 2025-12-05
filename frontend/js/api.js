// API wrapper for making authenticated requests
// Version: 1.2 - Added unpair and repair device methods
const api = {
    base: location.origin.replace(/:\d+$/, ':8000').replace('http:', 'https:') || 'https://127.0.0.1:8000',
    
    async request(path, opts = {}) {
        const url = this.base + path;
        opts.headers = opts.headers || {};
        opts.headers['Content-Type'] = 'application/json';
        opts.credentials = 'include';
        
        const res = await fetch(url, opts);
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.detail || 'Request failed');
        }
        
        return data;
    },

    // PBKDF2 helper (Web Crypto) - derive a hex string
    async _deriveClientHash(password, saltBase64, iterations = 100000, keyLen = 32) {
        const enc = new TextEncoder();
        const pwKey = await crypto.subtle.importKey('raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']);
        const salt = Uint8Array.from(atob(saltBase64), c => c.charCodeAt(0));
        const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations, hash: 'SHA-256' }, pwKey, keyLen * 8);
        const hashBytes = new Uint8Array(bits);
        // return hex
        return Array.from(hashBytes).map(b => b.toString(16).padStart(2, '0')).join('');
    },

    // Get admin salt from server (base64)
    async getSalt() {
        return this.request('/auth/salt');
    },

    // Auth endpoints: login performs client-side PBKDF2 using salt returned from server
    async login(password) {
        // Fetch salt for admin
        const saltResp = await this.getSalt();
        const salt = saltResp && saltResp.salt;
        if (!salt) throw new Error('Unable to retrieve salt');
        const client_hash = await this._deriveClientHash(password, salt);
        // Send client_hash (hex) to login endpoint
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ client_hash })
        });
    },

    async logout() {
        return this.request('/auth/logout', { method: 'POST' });
    },

    // Alerts endpoints
    async getAlerts() {
        return this.request('/alerts');
    },

    async acknowledgeAlert(alertId) {
        return this.request(`/alerts/${alertId}/ack`, { method: 'POST' });
    },

    async getAlertHistory() {
        return this.request('/alerts/history?include_ack=true&limit=200');
    },

    // Status endpoints
    async getStatus() {
        return this.request('/status');
    },

    // Settings endpoints
    async getSettings() {
        return this.request('/settings');
    },

    async updateSettings(settings) {
        return this.request('/settings', {
            method: 'POST',
            body: JSON.stringify(settings)
        });
    },

    // Devices
    async getDevices() {
        return this.request('/devices');
    },

    // Device Discovery and Pairing
    async discoverDevices(startPort = 8080, count = 20) {
        return this.request(`/devices/discover?start_port=${startPort}&count=${count}`);
    },

    async pairDevice(deviceId, port, pairingCode = null, name = null, location = null) {
        return this.request('/devices/pair', {
            method: 'POST',
            body: JSON.stringify({
                device_id: deviceId,
                port: port,
                pairing_code: pairingCode,
                name: name,
                location: location
            })
        });
    },

    async getRegisteredDevices() {
        return this.request('/devices/registered');
    },

    async updateDevice(deviceId, updates) {
        return this.request(`/devices/${deviceId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
    },

    async removeDevice(deviceId) {
        return this.request(`/devices/${deviceId}`, {
            method: 'DELETE'
        });
    },

    async unpairDevice(deviceId) {
        return this.request(`/devices/${deviceId}/unpair`, {
            method: 'POST'
        });
    },

    async repairDevice(deviceId, port, pairingCode) {
        return this.request(`/devices/${deviceId}/repair`, {
            method: 'POST',
            body: JSON.stringify({
                port: port,
                pairing_code: pairingCode
            })
        });
    },

    async getDeviceStatus(deviceId) {
        return this.request(`/devices/${deviceId}/status`);
    },

    // Setup wizard
    async getSetupStatus() {
        return this.request('/setup/status');
    },

    async completeSetup(homeName, adminPassword, confirmPassword) {
        return this.request('/setup/complete', {
            method: 'POST',
            body: JSON.stringify({
                home_name: homeName,
                admin_password: adminPassword,
                confirm_password: confirmPassword
            })
        });
    },

    async resetPassword(recoveryKey, newPassword, confirmPassword) {
        return this.request('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({
                recovery_key: recoveryKey,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });
    },

    async changePassword(currentPassword, newPassword) {
        // Get salt for current user
        const saltResp = await this.getSalt();
        const salt = saltResp && saltResp.salt;
        if (!salt) throw new Error('Unable to retrieve salt');
        
        // Hash current password with salt
        const currentHash = await this._deriveClientHash(currentPassword, salt);
        
        return this.request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password_hash: currentHash,
                new_password: newPassword
            })
        });
    },

    async refreshDevices() {
        return this.request('/devices/refresh', {
            method: 'POST'
        });
    }
};