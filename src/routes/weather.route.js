const express = require('express');
const router = express.Router();
const { handleWeather } = require('../controllers/weather.controller');

// Weather tool entrypoint.
router.post('/', handleWeather);

module.exports = router;

