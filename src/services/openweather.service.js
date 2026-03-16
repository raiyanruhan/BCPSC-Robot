// Service for talking to the OpenWeather current weather API.
// This file only knows how to call the API and normalize the raw response;
// it does not perform any formatting (units, strings) so controllers stay in control.

const axios = require('axios');
const { OPENWEATHER_API_KEY } = require('../config/env');

async function getCurrentWeather(city) {
  if (!OPENWEATHER_API_KEY) {
    const err = new Error('OpenWeather API key is not configured');
    err.status = 502;
    throw err;
  }

  const url = 'https://api.openweathermap.org/data/2.5/weather';

  try {
    const response = await axios.get(url, {
      params: {
        q: city,
        appid: OPENWEATHER_API_KEY,
        units: 'metric'
      },
      timeout: 5000 // Weather is critical, but should be fast
    });

    const data = response.data;

    return {
      temp: data.main && data.main.temp,
      feels_like: data.main && data.main.feels_like,
      condition:
        Array.isArray(data.weather) && data.weather[0] ? data.weather[0].main : null,
      humidity: data.main && data.main.humidity,
      wind_speed: data.wind && data.wind.speed,
      location: data.name
    };
  } catch (error) {
    // Map any upstream failure to a 502 so the client knows the dependency failed.
    const err = new Error('Failed to fetch weather data from OpenWeather');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  getCurrentWeather
};

