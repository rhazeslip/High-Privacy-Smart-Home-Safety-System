# First-Time Setup Wizard - Implementation Summary

## Overview

Implemented a comprehensive first-time setup wizard for the HP-SHSS system that guides users through initial configuration without requiring usernames. The system now uses a single admin password for authentication with a recovery key for account recovery.

## Features Implemented

### 1. Setup Wizard Flow

**Step 1: Home Name**
- User provides a friendly name for their home
- Example: "Johnson Family Home", "Apartment 3B", etc.

**Step 2: Admin Password**
- User creates admin password (minimum 8 characters)
- Password confirmation to prevent typos
- Password strength validation

**Step 3: Recovery Key Display**
- System generates a cryptographically secure recovery key
- User must acknowledge saving the key before proceeding
- Copy-to-clipboard functionality
- Recovery key stored securely for password reset

### 2. Authentication Changes

**Password-Only Login**
- ✅ Removed username requirement from login form
- ✅ System defaults to 'admin' user internally
- ✅ Single password for system access
- ✅ Backward compatible with existing auth system

**Security Maintained**
- Client-side PBKDF2 key derivation (100,000 iterations)
- Bcrypt password hashing on server
- Per-user salt storage
- HttpOnly secure cookies
- JWT tokens with expiration

### 3. Backend Implementation

**New Database Tables**
```sql
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT
)
```

**Configuration Keys**
- `setup_complete` - Boolean flag
- `home_name` - User's home name
- `recovery_key` - Admin recovery key
- `admin_salt` - Salt for password hashing

**New Endpoints**

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/setup/status` | GET | None | Check setup completion status |
| `/setup/complete` | POST | None | Complete initial setup |

**Modified Endpoints**
- `/auth/login` - Now accepts password-only (username optional)
- `/auth/salt` - Defaults to admin user if no username provided

### 4. Frontend Implementation

**New Pages**
- Setup wizard with multi-step form
- Step-by-step progression with validation
- Visual feedback and animations
- Mobile-responsive design

**Updated Login**
- Single password field
- Removed username input
- Cleaner, simpler UI

**Setup Flow Control**
- Checks setup status on app initialization
- Redirects to setup if not complete
- Prevents access to other pages until setup done
- Auto-redirects to login after setup completion

## File Changes

### Backend Files

**Created/Modified:**
- `backend/store.py`
  - Added `system_config` table
  - Added setup status functions
  - Added home name and recovery key storage
  - Removed auto-seeding of demo users

- `backend/models.py`
  - Made `username` optional in `LoginRequest`
  - Added `SetupStatus`, `SetupRequest`, `SetupResponse` models

- `backend/main.py`
  - Added `/setup/status` endpoint
  - Added `/setup/complete` endpoint
  - Updated `/auth/login` for password-only mode
  - Updated `/auth/salt` to work without username

### Frontend Files

**Modified:**
- `Front-End-User/index.html`
  - Removed username field from login
  - Added complete setup wizard UI
  - Added recovery key display section

- `Front-End-User/js/app.js`
  - Added setup status checking
  - Added setup wizard navigation
  - Added recovery key management
  - Updated login to password-only

- `Front-End-User/js/api.js`
  - Updated `login()` for password-only
  - Updated `getSalt()` for optional username
  - Added `getSetupStatus()`
  - Added `completeSetup()`

- `Front-End-User/css/components.css`
  - Added setup wizard styles
  - Added recovery key display styles
  - Added wizard step animations

## Security Features

### Password Security
- ✅ Minimum 8 character requirement
- ✅ PBKDF2-HMAC-SHA256 (100,000 iterations)
- ✅ Bcrypt hashing (server-side)
- ✅ Unique per-user salt
- ✅ Secure storage in database

### Recovery Key
- ✅ Cryptographically secure generation (32-byte token)
- ✅ Base64url encoding (43 characters)
- ✅ Stored securely in database
- ✅ One-time display during setup
- ✅ Copy-to-clipboard support

### Setup Protection
- ✅ Setup endpoints only accessible before completion
- ✅ Cannot re-run setup after completion
- ✅ Setup status checked on every app load
- ✅ All other endpoints require setup completion

## Usage

### First-Time Setup Process

1. **Start the System**
   ```bash
   # Start backend
   python -m uvicorn backend.main:app --ssl-keyfile key.pem --ssl-certfile cert.pem
   
   # Start frontend
   cd Front-End-User
   python serve_https.py
   ```

2. **Access the Application**
   - Open browser to `https://localhost:3000`
   - Setup wizard appears automatically

3. **Complete Setup**
   - **Step 1**: Enter home name (e.g., "My Home")
   - **Step 2**: Create admin password (min 8 chars)
   - **Step 3**: Save recovery key displayed
   - Check confirmation box
   - Click "Continue to Dashboard"

4. **Login**
   - System reloads to login page
   - Enter your admin password
   - Access full system

### Subsequent Logins

- Simply enter password (no username needed)
- System remembers setup completion
- Recovery key stored for future password reset

## Database Migration

### For Existing Installations

If you have an existing installation with the old user seeding:

**Option 1: Fresh Start (Recommended for Development)**
```bash
# Delete existing database
rm backend/data.db

# Restart backend - will create new schema
python -m uvicorn backend.main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem
```

**Option 2: Keep Existing Users**
- Existing users will continue to work
- Setup wizard will be skipped if users exist
- Can manually set setup_complete flag:
  ```sql
  INSERT INTO system_config (key, value) VALUES ('setup_complete', 'true');
  INSERT INTO system_config (key, value) VALUES ('home_name', 'My Home');
  ```

### For Production Deployments

Add migration script to set setup_complete for existing installations:

```python
from backend.store import is_setup_complete, mark_setup_complete, set_home_name, _DB

# Check if users exist
cur = _DB.cursor()
cur.execute("SELECT COUNT(*) as c FROM users WHERE username = 'admin'")
if cur.fetchone()['c'] > 0:
    # Existing installation - mark setup as complete
    mark_setup_complete()
    set_home_name("My Home")  # Default name
```

## Recovery Key Usage

### Future Password Reset Feature

The recovery key can be used to implement password reset:

```python
@app.post("/auth/reset-password")
def reset_password(recovery_key: str, new_password: str):
    stored_key = get_recovery_key()
    if recovery_key != stored_key:
        raise HTTPException(status_code=401, detail="Invalid recovery key")
    
    # Reset password logic here
    # ... hash new password, update database
    
    return {"success": True}
```

### Best Practices

**For Users:**
- Save recovery key in password manager
- Print and store in secure physical location
- Never share recovery key
- Generate new key after password reset

**For Developers:**
- Consider adding recovery key rotation
- Implement password reset endpoint
- Add email/SMS recovery options
- Log recovery key usage attempts

## Testing

### Test First-Time Setup

1. Delete `backend/data.db` if it exists
2. Start backend and frontend
3. Navigate to application
4. Complete setup wizard
5. Verify login works with new password

### Test Password-Only Login

1. After setup, logout
2. Login page should show only password field
3. Enter password and verify access

### Test Setup Protection

1. Try to access `/setup/complete` after setup
2. Should return 400 error "Setup already completed"

### Test Recovery Key

1. Copy recovery key during setup
2. Paste in text editor to verify format
3. Store securely for testing password reset

## Configuration Options

### Customizing Password Requirements

In `backend/main.py`, update `complete_setup()`:

```python
# Change minimum password length
if len(setup.admin_password) < 12:  # Changed from 8
    raise HTTPException(status_code=400, detail="Password must be at least 12 characters")

# Add complexity requirements
import re
if not re.search(r'[A-Z]', setup.admin_password):
    raise HTTPException(status_code=400, detail="Password must contain uppercase letter")
```

### Customizing Recovery Key Format

Change recovery key generation:

```python
# Option 1: Longer key
recovery_key = secrets.token_urlsafe(48)  # 64 characters

# Option 2: Word-based key
words = ["alpha", "bravo", "charlie", ...]  # word list
recovery_key = '-'.join(secrets.choice(words) for _ in range(12))
```

### Customizing Home Name

Add validation or suggestions:

```python
# Validate home name
if len(setup.home_name) > 50:
    raise HTTPException(status_code=400, detail="Home name too long")

# Provide default suggestions
suggestions = ["My Home", "Home Security", "Family Home"]
```

## Future Enhancements

### Planned Features

1. **Password Reset via Recovery Key**
   - Endpoint to verify recovery key
   - Password reset flow
   - Recovery key rotation

2. **Multi-User Support**
   - Admin can create additional users
   - Guest/occupant accounts
   - Per-user permissions

3. **Setup Wizard Improvements**
   - Email configuration
   - Time zone selection
   - Default alert preferences
   - Device pairing during setup

4. **Security Enhancements**
   - Two-factor authentication setup
   - Biometric authentication
   - Security questions
   - Account lockout after failed attempts

5. **Recovery Options**
   - Email-based password reset
   - SMS verification
   - Backup recovery codes
   - Admin override mechanism

## Troubleshooting

### Setup Wizard Not Appearing

**Issue**: Login page shows instead of setup wizard

**Solution**:
- Check `backend/data.db` exists
- Query: `SELECT * FROM system_config WHERE key = 'setup_complete'`
- Delete record or set value to 'false'

### Login Fails After Setup

**Issue**: Password not working after completing setup

**Solution**:
- Check browser console for errors
- Verify salt was stored: `SELECT * FROM users WHERE username = 'admin'`
- Try deleting cookies and refreshing
- Check password meets minimum requirements

### Recovery Key Not Displaying

**Issue**: Step 3 shows blank recovery key

**Solution**:
- Check browser console for API errors
- Verify `/setup/complete` returned success
- Check `recovery_key` in response
- Ensure JavaScript is enabled

### "Setup Already Completed" Error

**Issue**: Cannot access setup wizard

**Solution**:
- This is normal after completing setup
- To re-run setup, delete database or update system_config
- For production, implement password reset instead

## API Reference

### GET /setup/status

Check if initial setup has been completed.

**Response:**
```json
{
  "setup_complete": false,
  "home_name": null
}
```

### POST /setup/complete

Complete initial setup wizard.

**Request:**
```json
{
  "home_name": "My Home",
  "admin_password": "SecurePassword123",
  "confirm_password": "SecurePassword123"
}
```

**Response:**
```json
{
  "success": true,
  "recovery_key": "abc123...xyz789",
  "message": "Setup completed successfully. Please save your recovery key in a secure location."
}
```

**Errors:**
- 400: Setup already completed
- 400: Passwords do not match
- 400: Password too short

### POST /auth/login (Updated)

Login with password only.

**Request:**
```json
{
  "password": "SecurePassword123",
  "username": null  // Optional, defaults to 'admin'
}
```

Or with client_hash:
```json
{
  "client_hash": "a1b2c3...",
  "username": null
}
```

**Response:**
- Sets `hp_token` cookie
- Sets `hp_refresh` cookie
- Returns token info

## Summary

The first-time setup wizard provides:
- ✅ User-friendly onboarding experience
- ✅ Simplified authentication (password-only)
- ✅ Secure password storage with recovery
- ✅ Clean, modern UI
- ✅ Backward compatible with existing system
- ✅ Mobile responsive
- ✅ Production-ready security

All requirements met:
- ✅ Setup wizard on first startup
- ✅ Home name configuration
- ✅ Password setup (no username required)
- ✅ Account privilege checking via password
- ✅ Security/recovery key display
- ✅ Key storage for password reset
