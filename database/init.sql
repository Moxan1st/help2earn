-- Help2Earn Database Initialization Script
-- PostgreSQL with PostGIS extension

-- Enable PostGIS extension for geographic queries
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- FACILITIES TABLE
-- Stores accessibility facility data
-- ============================================

CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Facility type: ramp, toilet, elevator, wheelchair
    type VARCHAR(20) NOT NULL CHECK (type IN ('ramp', 'toilet', 'elevator', 'wheelchair')),

    -- Geographic location (PostGIS GEOGRAPHY type for accurate distance calculations)
    location GEOGRAPHY(POINT, 4326) NOT NULL,

    -- Image URL (stored in S3/R2)
    image_url TEXT NOT NULL,

    -- AI analysis result (JSON string)
    ai_analysis TEXT,

    -- Contributor's wallet address
    contributor_address VARCHAR(42) NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for geographic queries (find facilities within radius)
CREATE INDEX IF NOT EXISTS idx_facilities_location
ON facilities USING GIST(location);

-- Index for type filtering
CREATE INDEX IF NOT EXISTS idx_facilities_type
ON facilities(type);

-- Index for contributor queries
CREATE INDEX IF NOT EXISTS idx_facilities_contributor
ON facilities(contributor_address);

-- Index for timestamp queries
CREATE INDEX IF NOT EXISTS idx_facilities_created_at
ON facilities(created_at DESC);

-- Composite index for anti-fraud checks (location + type + time)
CREATE INDEX IF NOT EXISTS idx_facilities_fraud_check
ON facilities(type, updated_at DESC);


-- ============================================
-- REWARDS TABLE
-- Stores token reward records
-- ============================================

CREATE TABLE IF NOT EXISTS rewards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User's wallet address
    wallet_address VARCHAR(42) NOT NULL,

    -- Associated facility
    facility_id UUID REFERENCES facilities(id) ON DELETE SET NULL,

    -- Reward amount (in whole tokens, not wei)
    amount INTEGER NOT NULL CHECK (amount > 0),

    -- Blockchain transaction hash
    tx_hash VARCHAR(66),

    -- Reward type: new_facility, facility_update
    reward_type VARCHAR(20) DEFAULT 'new_facility',

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for wallet queries
CREATE INDEX IF NOT EXISTS idx_rewards_wallet
ON rewards(wallet_address);

-- Index for facility queries
CREATE INDEX IF NOT EXISTS idx_rewards_facility
ON rewards(facility_id);

-- Index for timestamp queries
CREATE INDEX IF NOT EXISTS idx_rewards_created_at
ON rewards(created_at DESC);


-- ============================================
-- VERIFICATION_LOGS TABLE
-- Audit trail for all verification attempts
-- ============================================

CREATE TABLE IF NOT EXISTS verification_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Request details
    wallet_address VARCHAR(42) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,

    -- Verification result
    success BOOLEAN NOT NULL,
    facility_type VARCHAR(20),
    confidence DECIMAL(3, 2),

    -- Failure reason if not successful
    failure_reason TEXT,

    -- Processing time in milliseconds
    processing_time_ms INTEGER,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for analytics
CREATE INDEX IF NOT EXISTS idx_verification_logs_created_at
ON verification_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_verification_logs_success
ON verification_logs(success);


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_facilities_updated_at ON facilities;
CREATE TRIGGER update_facilities_updated_at
    BEFORE UPDATE ON facilities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- USEFUL QUERIES (for reference)
-- ============================================

-- Find facilities within radius (example: 200m from a point)
-- SELECT id, type, ST_X(location::geometry) as lng, ST_Y(location::geometry) as lat,
--        ST_Distance(location, ST_SetSRID(ST_MakePoint(121.4737, 31.2304), 4326)::geography) as distance
-- FROM facilities
-- WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(121.4737, 31.2304), 4326)::geography, 200)
-- ORDER BY distance;

-- Check for duplicate (same type within 50m in last 15 days)
-- SELECT id, type, updated_at,
--        EXTRACT(DAY FROM NOW() - updated_at) as days_since_update
-- FROM facilities
-- WHERE type = 'ramp'
-- AND ST_DWithin(location, ST_SetSRID(ST_MakePoint(121.4737, 31.2304), 4326)::geography, 50)
-- AND updated_at > NOW() - INTERVAL '15 days';

-- Get user statistics
-- SELECT
--     wallet_address,
--     COUNT(*) as contribution_count,
--     SUM(amount) as total_earned
-- FROM rewards
-- GROUP BY wallet_address
-- ORDER BY total_earned DESC;


-- ============================================
-- SAMPLE DATA (for testing)
-- ============================================

-- Insert sample facilities (Shanghai area)
INSERT INTO facilities (type, location, image_url, ai_analysis, contributor_address) VALUES
('ramp', ST_SetSRID(ST_MakePoint(121.4737, 31.2304), 4326)::geography,
 'https://example.com/ramp1.jpg',
 '{"is_valid": true, "confidence": 0.95, "condition": "坡度适中，表面平整"}',
 '0x1234567890123456789012345678901234567890'),

('toilet', ST_SetSRID(ST_MakePoint(121.4750, 31.2310), 4326)::geography,
 'https://example.com/toilet1.jpg',
 '{"is_valid": true, "confidence": 0.92, "condition": "设施完善，有扶手"}',
 '0x1234567890123456789012345678901234567890'),

('elevator', ST_SetSRID(ST_MakePoint(121.4720, 31.2290), 4326)::geography,
 'https://example.com/elevator1.jpg',
 '{"is_valid": true, "confidence": 0.98, "condition": "电梯运行正常，有盲文按钮"}',
 '0x2345678901234567890123456789012345678901'),

('wheelchair', ST_SetSRID(ST_MakePoint(121.4745, 31.2315), 4326)::geography,
 'https://example.com/wheelchair1.jpg',
 '{"is_valid": true, "confidence": 0.88, "condition": "轮椅状态良好，可免费借用"}',
 '0x2345678901234567890123456789012345678901')
ON CONFLICT DO NOTHING;

-- Insert sample rewards
INSERT INTO rewards (wallet_address, facility_id, amount, tx_hash, reward_type)
SELECT
    '0x1234567890123456789012345678901234567890',
    id,
    50,
    '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab',
    'new_facility'
FROM facilities
WHERE contributor_address = '0x1234567890123456789012345678901234567890'
LIMIT 2
ON CONFLICT DO NOTHING;
