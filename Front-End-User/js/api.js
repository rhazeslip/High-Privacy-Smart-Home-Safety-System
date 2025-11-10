// API wrapper for making authenticated requests
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

    // Get per-user salt from server (base64)
    async getSalt(username) {
        return this.request(`/auth/salt?username=${encodeURIComponent(username)}`);
    },

    // Auth endpoints: login now performs client-side PBKDF2 using salt returned from server
    async login(username, password) {
        // Fetch salt for the username
        const saltResp = await this.getSalt(username);
        const salt = saltResp && saltResp.salt;
        if (!salt) throw new Error('Unable to retrieve salt for user');
        const client_hash = await this._deriveClientHash(password, salt);
        // Send client_hash (hex) to login endpoint
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, client_hash })
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
    }
};