// Controller for the weather tool.
// Handles input validation, cache usage, and response formatting while delegating
// the actual API call to the OpenWeather service.

const { getCurrentWeather } = require('../services/openweather.service');
const cache = require('../utils/cache');
const { formatTemp, formatHumidity, formatWind } = require('../utils/formatter');

const TEN_MINUTES_MS = 10 * 60 * 1000;

async function handleWeather(req, res, next) {
  try {
    let city = req.body && req.body.city;

    if (!city || typeof city !== 'string') {
      return res.status(400).json({ error: 'Missing required field: city' });
    }

    // Basic sanitization: remove non-printable characters and trim.
    city = city.trim().replace(/[\x00-\x1F\x7F]/g, '');

    if (city.length > 100) {
      return res.status(400).json({ error: 'City name is too long' });
    }

    const cacheKey = `weather:${city.toLowerCase()}`;
    const cached = cache.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }

    const data = await getCurrentWeather(city);

    const responseBody = {
      location: data.location || city,
      temperature: formatTemp(data.temp),
      feels_like: formatTemp(data.feels_like),
      condition: data.condition || '',
      humidity: formatHumidity(data.humidity),
      wind_speed: formatWind(data.wind_speed)
    };

    cache.set(cacheKey, responseBody, TEN_MINUTES_MS);

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleWeather
};

