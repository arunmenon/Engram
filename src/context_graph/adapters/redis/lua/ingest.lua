-- Atomic event ingestion with dedup.
--
-- KEYS[1] = stream key         (e.g. "events:__global__")
-- KEYS[2] = json key           (e.g. "evt:{event_id}")
-- KEYS[3] = dedup sorted set   (e.g. "dedup:events")
-- KEYS[4] = session stream key (e.g. "events:session:{session_id}")
--
-- ARGV[1] = event_id (string UUID)
-- ARGV[2] = event JSON payload (string)
-- ARGV[3] = occurred_at_epoch_ms (number, used as dedup set score)
-- ARGV[4] = max_stream_len (number, 0 = uncapped; approximate MAXLEN for XADD)
--
-- Returns: stream entry ID (string)
--   - If the event already exists (dedup hit), returns the previously stored entry ID.
--   - If the event is new, atomically writes to all keys and returns the new entry ID.

local stream_key = KEYS[1]
local json_key   = KEYS[2]
local dedup_key  = KEYS[3]

local event_id           = ARGV[1]
local event_json         = ARGV[2]
local occurred_at_ms     = ARGV[3]
local max_stream_len     = tonumber(ARGV[4]) or 0

-- Step 1: Check dedup sorted set for existing event_id
local existing_score = redis.call('ZSCORE', dedup_key, event_id)
if existing_score then
    -- Event already ingested — retrieve stored global_position from JSON doc
    local stored_json = redis.call('JSON.GET', json_key, '$.global_position')
    if stored_json then
        -- JSON.GET returns a JSON array string like '["1707644400000-0"]'
        -- Extract the value between quotes
        local position = string.match(stored_json, '"([^"]+)"')
        if position then
            return position
        end
    end
    -- Fallback: return a sentinel indicating dedup hit but position unknown
    return "DEDUP"
end

-- Step 2a: XADD to the global stream — Redis auto-assigns the entry ID
-- When max_stream_len > 0, use approximate MAXLEN to cap stream growth (ADR-0014)
local entry_id
if max_stream_len > 0 then
    entry_id = redis.call('XADD', stream_key, 'MAXLEN', '~', max_stream_len, '*', 'event_id', event_id)
else
    entry_id = redis.call('XADD', stream_key, '*', 'event_id', event_id)
end

-- Step 2b: XADD to the per-session stream
if KEYS[4] then
    redis.call('XADD', KEYS[4], '*', 'event_id', event_id)
end

-- Step 3: JSON.SET — store the full event document (ADR-0014: two-step approach)
-- First, store the complete JSON document as-is
redis.call('JSON.SET', json_key, '$', event_json)
-- Then, set global_position via JSON path to avoid fragile string.gsub patching
redis.call('JSON.SET', json_key, '$.global_position', '"' .. entry_id .. '"')

-- Step 4: ZADD to dedup set — score is occurred_at_epoch_ms for TTL-based cleanup
redis.call('ZADD', dedup_key, occurred_at_ms, event_id)

return entry_id
