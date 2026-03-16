// Very small in-memory TTL cache built on top of a Map.
// This avoids any external infrastructure (Redis, databases) while still
// preventing repeated calls to slow or rate-limited APIs for the same key.

const store = new Map();

/**
 * Store a value with a time-to-live.
 * Using absolute expiry timestamps keeps lookup logic simple and avoids
 * background timers that could misbehave on shared hosting.
 *
 * @param {string} key
 * @param {*} value
 * @param {number} ttlMs - time to live in milliseconds
 */
function set(key, value, ttlMs) {
  if (!key || typeof ttlMs !== 'number' || ttlMs <= 0) {
    // Silently ignore invalid cache usage to avoid breaking tool flows.
    return;
  }

  const expiresAt = Date.now() + ttlMs;
  store.set(key, { value, expiresAt });
}

/**
 * Retrieve a cached value if it is still valid.
 * Expired entries are eagerly removed so the cache does not grow unbounded
 * during long-running processes.
 *
 * @param {string} key
 * @returns {*} cached value or null
 */
function get(key) {
  if (!key) {
    return null;
  }

  const entry = store.get(key);
  if (!entry) {
    return null;
  }

  if (entry.expiresAt <= Date.now()) {
    store.delete(key);
    return null;
  }

  return entry.value;
}

/**
 * Remove a single key from the cache.
 * Controllers can use this to invalidate specific entries if needed in future
 * without exposing the underlying Map implementation.
 *
 * @param {string} key
 */
function clear(key) {
  if (!key) {
    return;
  }
  store.delete(key);
}

module.exports = {
  set,
  get,
  clear
};

