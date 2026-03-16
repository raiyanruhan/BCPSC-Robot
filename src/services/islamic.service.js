// Service functions for AlAdhan Islamic API.
// These functions normalize responses for prayer times and Hijri date, leaving
// the choice of which type to call to the controller.

const axios = require('axios');

async function getPrayerTimes(city) {
  const url = 'https://api.aladhan.com/v1/timingsByCity';

  try {
    const response = await axios.get(url, {
      params: {
        city,
        country: 'Bangladesh',
        method: 1
      },
      timeout: 10000
    });

    const data = response.data && response.data.data ? response.data.data : {};
    const date = data.date || {};
    const hijri = date.hijri || {};
    const gregorian = date.gregorian || {};
    const timings = data.timings || {};

    return {
      city,
      country: 'Bangladesh',
      date: gregorian.readable || null,
      fajr: timings.Fajr || null,
      dhuhr: timings.Dhuhr || null,
      asr: timings.Asr || null,
      maghrib: timings.Maghrib || null,
      isha: timings.Isha || null
    };
  } catch (error) {
    const err = new Error('Failed to fetch prayer times from AlAdhan');
    err.status = 502;
    throw err;
  }
}

async function getHijriDateForToday() {
  // AlAdhan expects DD-MM-YYYY; building this manually avoids pull in date libs.
  const now = new Date();
  const day = String(now.getDate()).padStart(2, '0');
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const year = now.getFullYear();
  const formatted = `${day}-${month}-${year}`;

  const url = 'https://api.aladhan.com/v1/gToH';

  try {
    const response = await axios.get(url, {
      params: {
        date: formatted
      },
      timeout: 10000
    });

    const data = response.data && response.data.data ? response.data.data : {};
    const hijri = data.hijri || {};
    const gregorian = data.gregorian || {};

    const hijriDate = hijri.readable || null;
    const gregDate = gregorian.date || null;

    return {
      hijri_date: hijriDate,
      gregorian_date: gregDate
    };
  } catch (error) {
    const err = new Error('Failed to fetch Hijri date from AlAdhan');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  getPrayerTimes,
  getHijriDateForToday
};

