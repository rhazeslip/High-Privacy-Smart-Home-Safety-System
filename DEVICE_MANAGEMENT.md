# Device Management Features

This document explains the device management features including pairing, unpairing, repairing, and removing devices.

## Device States

Devices can be in one of three states:

1. **Online** - Device is paired and responding to status checks
   - Badge: Green "● Online"
   - Actions: Unpair, Remove

2. **Offline** - Device is paired but not responding
   - Badge: Gray "○ Offline"
   - Actions: Unpair, Remove

3. **Unpaired** - Device exists in database but pairing has been removed
   - Badge: Orange "⚠ Unpaired"
   - Actions: Repair, Remove

## Device Operations

### Pairing a New Device

1. Navigate to the Devices page
2. Click "Discover Devices"
3. Enter custom name and location for the device
4. Enter the device's pairing code
5. Click "Pair Device"

The device will be added to the registered devices list with status "Online".

### Unpairing a Device

Unpairing removes the pairing credentials but keeps the device in the database:

1. Find the device in the registered devices list
2. Click "Unpair Device"
3. Confirm the action

Use this when:
- You need to temporarily disconnect a device
- The device credentials may be compromised
- You want to re-pair the device later with new credentials

### Repairing a Device

Repairing re-establishes connection with an unpaired device:

1. Find the unpaired device in the list (orange "⚠ Unpaired" badge)
2. Click "Repair Device"
3. Enter the device's pairing code
4. The device will be re-paired with the same name and location

Use this when:
- A device was previously unpaired
- Device credentials were reset
- Re-establishing communication after unpair

### Removing a Device

Removing permanently deletes the device from the database:

1. Find the device in the registered devices list
2. Click "Remove Device"
3. Confirm the permanent deletion

Use this when:
- Device is no longer needed
- Device is physically removed from the system
- Permanently retiring a device

⚠️ **Warning**: Remove is permanent. If you may need the device later, use Unpair instead.

## Backend Endpoints

### POST `/devices/{device_id}/unpair`
- Marks a device as unpaired
- Clears the shared secret
- Keeps device metadata (name, location, etc.)

### POST `/devices/{device_id}/repair`
- Re-pairs an unpaired device
- Requires pairing code
- Restores pairing with existing name/location

### DELETE `/devices/{device_id}`
- Permanently removes device from database
- Cannot be undone

## Security Considerations

- All device operations require admin privileges
- Pairing codes are required for both initial pairing and repair
- Shared secrets are cleared when unpairing
- Device removal is permanent and irreversible
