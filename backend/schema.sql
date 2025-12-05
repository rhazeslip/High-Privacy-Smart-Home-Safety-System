BEGIN EXECUTE IMMEDIATE 'DROP VIEW v_open_alerts'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP VIEW v_online_devices'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP VIEW v_recent_critical'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE alerts CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE sensor_history CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE sensors CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE devices CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE config CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE refresh_tokens CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE sensor_history_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

CREATE SEQUENCE sensor_history_seq START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;

CREATE TABLE sensors (
    sensor_id VARCHAR2(255) PRIMARY KEY,
    type VARCHAR2(255) NOT NULL,
    value VARCHAR2(4000) NOT NULL,
    location VARCHAR2(255) DEFAULT 'Unknown',
    ts VARCHAR2(50) NOT NULL
);

CREATE TABLE alerts (
    id VARCHAR2(255) PRIMARY KEY,
    level VARCHAR2(50) NOT NULL,
    title VARCHAR2(255) NOT NULL,
    message VARCHAR2(4000),
    sensor_id VARCHAR2(255) NOT NULL,
    location VARCHAR2(255) DEFAULT 'Unknown',
    created_at VARCHAR2(50) NOT NULL,
    acknowledged NUMBER(1) DEFAULT 0,
    CONSTRAINT fk_alerts_sensor FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id) ON DELETE CASCADE
);

CREATE TABLE sensor_history (
    id NUMBER PRIMARY KEY,
    sensor_id VARCHAR2(255) NOT NULL,
    type VARCHAR2(255) NOT NULL,
    value VARCHAR2(4000) NOT NULL,
    location VARCHAR2(255),
    ts VARCHAR2(50) NOT NULL,
    CONSTRAINT fk_history_sensor FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id) ON DELETE CASCADE
);

CREATE OR REPLACE TRIGGER sensor_history_bi
BEFORE INSERT ON sensor_history
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT sensor_history_seq.NEXTVAL INTO :NEW.id FROM DUAL;
    END IF;
END;
/

CREATE TABLE devices (
    device_id VARCHAR2(255) PRIMARY KEY,
    name VARCHAR2(255),
    type VARCHAR2(255),
    location VARCHAR2(255),
    port NUMBER(10),
    paired NUMBER(1) DEFAULT 0,
    shared_secret VARCHAR2(4000),
    model VARCHAR2(255) DEFAULT 'HP-SHSS-SIM',
    firmware_version VARCHAR2(50) DEFAULT '1.0.0',
    added_at VARCHAR2(50),
    last_seen VARCHAR2(50),
    battery NUMBER(3) DEFAULT 100
);

CREATE TABLE config (
    key VARCHAR2(255) PRIMARY KEY,
    value VARCHAR2(4000),
    category VARCHAR2(255) DEFAULT 'system'
);

CREATE TABLE refresh_tokens (
    token VARCHAR2(4000) PRIMARY KEY,
    expires_at VARCHAR2(50) NOT NULL
);

CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX idx_alerts_sensor ON alerts(sensor_id);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX idx_sensor_history_sensor ON sensor_history(sensor_id);
CREATE INDEX idx_sensor_history_ts ON sensor_history(ts DESC);
CREATE INDEX idx_devices_type ON devices(type);
CREATE INDEX idx_config_category ON config(category);

CREATE OR REPLACE VIEW v_open_alerts AS
SELECT id, level, title, message, sensor_id, location, created_at
FROM alerts
WHERE acknowledged = 0
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW v_online_devices AS
SELECT device_id, name, type, location, last_seen, battery
FROM devices
WHERE paired = 1
  AND TO_TIMESTAMP(last_seen, 'YYYY-MM-DD"T"HH24:MI:SS') > SYSTIMESTAMP - INTERVAL '5' MINUTE;

CREATE OR REPLACE VIEW v_recent_critical AS
SELECT id, title, message, sensor_id, location, created_at
FROM alerts
WHERE level = 'critical'
  AND TO_TIMESTAMP(created_at, 'YYYY-MM-DD"T"HH24:MI:SS') > SYSTIMESTAMP - INTERVAL '24' HOUR
ORDER BY created_at DESC;

