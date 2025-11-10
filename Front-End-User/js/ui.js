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
                    if (page === 'devices') window.app.loadDevices();
                    else if (page === 'history') window.app.loadHistory();
                    else if (page === 'settings') window.app.loadSettings();
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

        // Update navigation active state
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === pageId);
        });

        // Show selected page element (ids are like 'dashboard-page')
        document.querySelectorAll('.page').forEach(page => {
            page.classList.toggle('active', page.id === `${pageId}-page`);
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
                        ` : '<span class="acknowledged-badge">✓ Acknowledged</span>'}
                    </div>
                </div>
            </div>
        `;
    },

    getAlertIcon(level) {
        switch(level.toLowerCase()) {
            case 'critical': return '⚠️';
            case 'warning': return '⚡';
            case 'info': return 'ℹ️';
            default: return '📝';
        }
    },

    // Devices
    renderDevice(device) {
        return `
            <div class="device-card">
                <div class="device-header">
                    <span class="device-name">${device.name}</span>
                    <span class="device-status ${device.online ? 'online' : 'offline'}">
                        ${device.online ? 'Online' : 'Offline'}
                    </span>
                </div>
                <div class="device-details">
                    <div class="detail-item">
                        <div class="detail-label">Status</div>
                        <div class="detail-value">${device.value}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Last Update</div>
                        <div class="detail-value">${new Date(device.last_update).toLocaleTimeString()}</div>
                    </div>
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