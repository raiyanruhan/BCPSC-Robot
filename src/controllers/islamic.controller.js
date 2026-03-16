// Controller for Islamic information tools.
// Supports two types: prayer_times (requires city) and hijri_date (no city).
// Any unknown type results in a clear 400 error so the agent can correct usage.

const { getPrayerTimes, getHijriDateForToday } = require('../services/islamic.service');

async function handleIslamic(req, res, next) {
  try {
    const type = req.body && req.body.type;
    const city = req.body && req.body.city;

    if (!type || typeof type !== 'string') {
      return res.status(400).json({ error: 'Missing required field: type' });
    }

    if (type === 'prayer_times') {
      if (!city || typeof city !== 'string') {
        return res.status(400).json({ error: 'Missing required field: city' });
      }

      const data = await getPrayerTimes(city);

      const responseBody = {
        type: 'prayer_times',
        city: data.city,
        country: data.country,
        date: data.date,
        fajr: data.fajr,
        dhuhr: data.dhuhr,
        asr: data.asr,
        maghrib: data.maghrib,
        isha: data.isha
      };

      return res.json(responseBody);
    }

    if (type === 'hijri_date') {
      const data = await getHijriDateForToday();

      const responseBody = {
        type: 'hijri_date',
        hijri_date: data.hijri_date,
        gregorian_date: data.gregorian_date
      };

      return res.json(responseBody);
    }

    return res.status(400).json({
      error: 'Invalid type. Use: prayer_times, hijri_date'
    });
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleIslamic
};

