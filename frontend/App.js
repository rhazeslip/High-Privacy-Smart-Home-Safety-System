// Modern frontend app for HP-SHSS with real-time activity feed
// Features:
// - Activity feed with filters and search
// - Device status monitoring
// - System settings and configuration
// - Secure authentication

const API_BASE = location.origin.replace(/:\d+$/, ':8000').replace('http:', 'https:') || 'https://127.0.0.1:8000';

function qs(sel) { return document.querySelector(sel); }

// Use cookie-based auth: backend sets HttpOnly secure cookie 'hp_token'.
// For fetch to send cookies we must set credentials: 'include'.
async function api(path, opts = {}){
	const url = API_BASE + path;
	opts.headers = opts.headers || {};
	opts.headers['Content-Type'] = 'application/json';
	opts.credentials = 'include';
	const res = await fetch(url, opts);
	const data = await res.json();
	if (!res.ok) {
		throw new Error(data.detail || 'Request failed');
	}
	if(res.status === 401){
		// not authenticated
		showLogin();
		throw new Error(data.detail || 'Unauthorized');
	}
	return data;
}

/* UI helpers */
function showLogin(){
	qs('#login-section').style.display = 'block';
	qs('#dashboard').style.display = 'none';
	qs('#logout').style.display = 'none';
}
function showDashboard(){
	qs('#login-section').style.display = 'none';
	qs('#dashboard').style.display = 'block';
	qs('#logout').style.display = 'inline-block';
}

function createEventCard(event) {
    return `
        <div class="event-card">
            <div class="event-icon ${event.level.toLowerCase()}">
                ${getEventIcon(event.level)}
            </div>
            <div class="event-details">
                <div class="event-title">${event.title}</div>
                <div class="event-meta">${event.message} • ${new Date(event.created_at).toLocaleString()}</div>
            </div>
        </div>
    `;
}

function createDeviceCard(device) {
    return `
        <div class="device-card">
            <div class="device-name">${device.name}</div>
            <div class="device-status">
                <div class="device-percentage">${device.value}%</div>
                <div class="status-badge ${device.status.toLowerCase()}">${device.status}</div>
            </div>
        </div>
    `;
}

function getEventIcon(level) {
    switch(level.toLowerCase()) {
        case 'info': return '🔵';
        case 'success': return '✅';
        case 'warning': return '⚠️';
        case 'error': return '❌';
        default: return '📝';
    }
}

async function handleLogin(e){
    e.preventDefault();
    const username = qs('#username').value;
    const password = qs('#password').value;
    try{
        await api('/auth/login', {method: 'POST', body: JSON.stringify({username,password})});
        await loadDashboard();
        showDashboard();
    }catch(err){
		qs('#login-error').textContent = err.message || 'Login failed';
	}
}

async function loadDashboard(){
    try {
        // Get system status and alerts
        const [status, alerts] = await Promise.all([
            api('/status'),
            api('/alerts')
        ]);

        // Update event feed
        const eventsList = qs('#events-list');
        eventsList.innerHTML = '';
        
        if(!alerts || alerts.length === 0){ 
            eventsList.innerHTML = createEventCard({
                level: 'info',
                title: 'System running normally',
                message: 'No active alerts',
                created_at: new Date()
            });
        } else {
            alerts.forEach(alert => {
                eventsList.innerHTML += createEventCard({
                    level: alert.level,
                    title: alert.title,
                    message: `${alert.message} (${alert.location})`,
                    created_at: alert.created_at
                });
            });
        }

        // Update device status grid
        const devicesGrid = qs('#devices-grid');
        devicesGrid.innerHTML = '';
        
        // Convert sensor data to device cards
        Object.entries(status.sensors || {}).forEach(([name, data]) => {
            devicesGrid.innerHTML += createDeviceCard({
                name: name,
                value: typeof data.value === 'number' ? data.value : 100,
                status: data.online ? 'Online' : 'Offline'
            });
        });
	}catch(err){ console.warn(err); }

	// Settings
		try{
			const settings = await api('/settings');
		qs('#armed').checked = !!settings.armed;
		qs('#mode').value = settings.mode || 'home';
		qs('#notify_email').value = settings.notify_email || '';
	}catch(err){ console.warn('No settings endpoint or not authenticated.'); }
}

async function loadHistory(){
	try{
		const history = await api('/alerts/history?include_ack=true&limit=200');
		const list = qs('#alerts-history-list');
		list.innerHTML = '';
		if(!history || history.length === 0){ list.innerHTML = '<li>No history found</li>'; return }
		history.forEach(a =>{
			const li = document.createElement('li');
			li.className = 'alert ' + a.level;
			li.innerHTML = `<strong>${a.title}</strong> <span class="meta">${a.location} • ${new Date(a.created_at).toLocaleString()}</span>
				<div>${a.message}</div> <div class="meta">Acknowledged: ${a.acknowledged}</div>`;
			list.appendChild(li);
		});
	}catch(err){ console.warn('Unable to load history', err); }
}

async function saveSettings(e){
	e.preventDefault();
	const payload = {
		armed: qs('#armed').checked,
		mode: qs('#mode').value,
		notify_email: qs('#notify_email').value
	};
	try{
		const res = await api('/settings', {method:'POST', body: JSON.stringify(payload)});
		if(res && res.ok){
			qs('#settings-status').textContent = 'Saved';
			setTimeout(()=> qs('#settings-status').textContent = '', 2000);
		}
	}catch(err){
		qs('#settings-status').textContent = 'Save failed (admin only)';
	}
}

async function logout(){
	try{
		await api('/auth/logout', {method: 'POST'});
	}catch(e){ /* ignore */ }
	showLogin();
}

function init(){
	qs('#login-form').addEventListener('submit', handleLogin);
	qs('#settings-form').addEventListener('submit', saveSettings);
	qs('#logout').addEventListener('click', logout);
	qs('#show-history').addEventListener('click', async ()=>{
		const hist = qs('#alerts-history');
		if(hist.style.display === 'none'){
			await loadHistory();
			hist.style.display = 'block';
			qs('#show-history').textContent = 'Hide history';
		}else{
			hist.style.display = 'none';
			qs('#show-history').textContent = 'Show history';
		}
	});
	// If logged in, go straight to dashboard
	// Probe /auth/me to determine if a valid cookie is present.
		api('/auth/me').then(user => {
			if(user && user.username){ loadDashboard().then(showDashboard); }
		}).catch(async ()=> {
			// Try to silently refresh access token using refresh cookie
			try{
				await api('/auth/refresh', {method: 'POST'});
				// if refresh succeeded, probe /auth/me again
				const u = await api('/auth/me');
				if(u && u.username){ loadDashboard().then(showDashboard); return; }
			}catch(e){ /* ignore */ }
			showLogin();
		});
}

window.addEventListener('DOMContentLoaded', init);
