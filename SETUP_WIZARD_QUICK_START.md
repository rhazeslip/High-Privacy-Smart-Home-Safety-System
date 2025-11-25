# Setup Wizard Quick Start Guide

## Testing the First-Time Setup Wizard

### Prerequisites
- Backend dependencies installed (`pip install -r backend/requirements.txt`)
- Frontend server ready
- SSL certificates in place (cert.pem, key.pem)

### Step-by-Step Testing

#### 1. Reset to Fresh State (Optional)
```bash
# If you want to test from scratch
cd backend
del data.db  # Windows
# or
rm data.db   # Linux/Mac
```

#### 2. Start the Backend
```bash
# From project root
python -m uvicorn backend.main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:8000
```

#### 3. Start the Frontend
```bash
cd Front-End-User
python serve_https.py
```

Expected output:
```
Serving HTTPS on 0.0.0.0 port 3000 (https://0.0.0.0:3000/)
```

#### 4. Access the Application
1. Open browser to `https://localhost:3000`
2. Accept the self-signed certificate warning (click Advanced → Proceed)

#### 5. Complete Setup Wizard

**You should see the setup wizard automatically!**

##### Step 1: Name Your Home
- Enter a home name (e.g., "Johnson Family Home")
- Click "Next"

##### Step 2: Set Admin Password
- Enter a password (minimum 8 characters)
  - Example: `MySecurePassword123`
- Confirm the password
- Click "Complete Setup"

##### Step 3: Save Recovery Key
- **Important**: Copy the recovery key displayed
  - Click "Copy to Clipboard" button
  - Or manually select and copy the key
- Paste it somewhere safe (password manager, secure note, etc.)
  - Example key: `xK7m_9pQ2vL5nH8rT3yW1cF4gJ6sA0uB_8dE2xR5zN9`
- Check the box "I have saved my recovery key"
- Click "Continue to Dashboard"

#### 6. Login
- Page reloads automatically
- You'll see the login page with only a password field
- Enter the password you created in Step 2
- Click "Sign in"

#### 7. Verify System Access
- You should now see the Dashboard
- Navigation sidebar should be visible
- System should show status information

### What Changed?

#### Before Setup Wizard
- Login required username AND password
- Default users: admin/admin123, alice/alice123
- No first-time configuration

#### After Setup Wizard
- **No username required** - just password
- Custom home name displayed
- Recovery key for password reset
- Personalized experience

### Testing Scenarios

#### Test 1: Password-Only Login
✅ No username field visible
✅ Only password required
✅ Login works with setup password

#### Test 2: Setup Cannot Be Re-Run
1. Logout from the system
2. Try to access `https://localhost:8000/setup/status`
3. Should return: `{"setup_complete": true, "home_name": "Your Home Name"}`
4. Try to POST to `/setup/complete`
5. Should get error: `{"detail": "Setup already completed"}`

#### Test 3: Recovery Key Storage
1. Check database: `sqlite3 backend/data.db`
2. Query: `SELECT * FROM system_config WHERE key = 'recovery_key';`
3. Should show the recovery key

#### Test 4: Home Name Display
1. After setup, home name is stored
2. Query: `SELECT * FROM system_config WHERE key = 'home_name';`
3. Should match what you entered

### Common Issues & Solutions

#### Issue: Setup wizard doesn't appear
**Solution**: 
- Delete `backend/data.db` to reset
- Or manually update: `UPDATE system_config SET value = 'false' WHERE key = 'setup_complete';`

#### Issue: Login fails after setup
**Solution**:
- Make sure you're entering the correct password
- Check browser console for errors
- Try clearing cookies and refreshing
- Verify data.db exists and has admin user

#### Issue: Recovery key is blank
**Solution**:
- Check browser console for JavaScript errors
- Ensure API call succeeded (check Network tab)
- Verify backend is running on HTTPS

#### Issue: "Invalid password" error
**Solution**:
- Password might not have been hashed correctly
- Check that salt was stored in database
- Try setting up again with fresh database

### Database Schema Verification

Check that setup created all necessary data:

```bash
sqlite3 backend/data.db
```

```sql
-- Check setup status
SELECT * FROM system_config;

-- Should show:
-- setup_complete | true
-- home_name | Your Home Name
-- recovery_key | xxxxx...
-- admin_salt | base64string...

-- Check admin user
SELECT username, role, salt FROM users;

-- Should show:
-- admin | Admin | base64string...
```

### Recovery Key Format

The recovery key is:
- 43 characters long
- Base64url encoded
- Cryptographically secure (32 bytes of random data)
- Example: `xK7m_9pQ2vL5nH8rT3yW1cF4gJ6sA0uB_8dE2xR5zN9`

### Security Notes

✅ **What's Secure:**
- Password hashed with PBKDF2 (100k iterations) + bcrypt
- Recovery key cryptographically random
- HTTPS required for all communications
- HttpOnly cookies prevent XSS attacks
- No usernames prevent enumeration attacks

⚠️ **Important:**
- Save recovery key in secure location
- Don't share recovery key
- Use strong password (min 8 chars)
- Consider enabling 2FA in future

### Next Steps After Setup

1. **Add Devices**
   - Navigate to "Device Setup"
   - Scan for emulated devices
   - Pair devices with your system

2. **Configure Settings**
   - Go to Settings page
   - Set notification preferences
   - Configure arming modes

3. **Monitor Security**
   - View Dashboard for alerts
   - Check device status
   - Review alert history

### Development Tips

#### Resetting for Testing
```bash
# Quick reset script
cd backend
rm data.db
cd ..
python -m uvicorn backend.main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem
```

#### Testing Different Passwords
- Try very short password (< 8 chars) - should fail
- Try mismatched passwords - should fail
- Try strong password - should succeed

#### Inspecting Setup State
```python
# Python script to check setup status
from backend.store import is_setup_complete, get_home_name, get_recovery_key

print(f"Setup complete: {is_setup_complete()}")
print(f"Home name: {get_home_name()}")
print(f"Recovery key: {get_recovery_key()}")
```

### Production Deployment Notes

When deploying to production:

1. **Backup Recovery Key**: Store in secure backup system
2. **HTTPS Required**: Always use valid SSL certificates
3. **Strong Passwords**: Enforce strong password policy
4. **Rate Limiting**: Add rate limiting to login/setup endpoints
5. **Monitoring**: Log setup attempts and suspicious activity
6. **Recovery Process**: Implement password reset via recovery key

### Success Checklist

After completing setup, verify:
- ✅ Setup wizard completed successfully
- ✅ Recovery key saved securely
- ✅ Can login with password only (no username)
- ✅ Dashboard loads correctly
- ✅ Navigation works
- ✅ Settings accessible
- ✅ Device management available
- ✅ Alerts system functional

## Summary

The setup wizard provides:
- **Simplified onboarding** - 3 easy steps
- **Password-only authentication** - no username needed
- **Recovery key** - never lose access
- **Personalization** - custom home name
- **Security** - enterprise-grade password storage
- **User-friendly** - clean, modern interface
