// Small, shared formatting helpers.
// Keeping these in one place avoids sprinkling magic strings and units
// throughout controllers, which makes responses easier to keep consistent.

/**
 * Append Celsius unit to a numeric temperature value.
 * Accepts numbers or numeric strings to be forgiving with upstream data.
 *
 * @param {number|string} value
 * @returns {string}
 */
function formatTemp(value) {
  return String(value) + '°C';
}

/**
 * Append kilometres-per-hour unit to a numeric wind speed.
 *
 * @param {number|string} value
 * @returns {string}
 */
function formatWind(value) {
  return String(value) + ' km/h';
}

/**
 * Append percentage sign to humidity values.
 *
 * @param {number|string} value
 * @returns {string}
 */
function formatHumidity(value) {
  return String(value) + '%';
}

module.exports = {
  formatTemp,
  formatWind,
  formatHumidity
};

