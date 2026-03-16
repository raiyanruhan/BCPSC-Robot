// Service wrapper around a public Quran API.
// This module hides the HTTP details and returns a normalized verse object
// that controllers can safely expose to the ElevenLabs agent or the robot.

const axios = require('axios');

/**
 * Fetch a single Quran ayah in Arabic plus a translation.
 * Uses api.alquran.cloud editions:
 *  - Arabic: quran-simple
 *  - English: en.asad
 *  - Bangla: bn.bengali
 *
 * @param {number} surahNumber
 * @param {number} ayahNumber
 * @param {'en'|'bn'} language
 * @returns {Promise<{arabic_text:string, translation:string, translator:string, surah_name_arabic:string, surah_name_english:string}>}
 */
async function getQuranVerse(surahNumber, ayahNumber, language) {
  const lang = language === 'bn' ? 'bn' : 'en';

  // We fetch Arabic and translation separately so the controller can always
  // combine them, regardless of which translation the caller requested.
  const arabicEdition = 'quran-simple';
  const translationEdition = lang === 'bn' ? 'bn.bengali' : 'en.asad';

  const base = 'https://api.alquran.cloud/v1/ayah';
  const ayahRef = `${surahNumber}:${ayahNumber}`;

  try {
    const [arabicRes, transRes] = await Promise.all([
      axios.get(`${base}/${ayahRef}/${arabicEdition}`, { timeout: 10000 }),
      axios.get(`${base}/${ayahRef}/${translationEdition}`, { timeout: 10000 })
    ]);

    if (
      !arabicRes.data ||
      arabicRes.data.status !== 'OK' ||
      !arabicRes.data.data ||
      !transRes.data ||
      transRes.data.status !== 'OK' ||
      !transRes.data.data
    ) {
      const err = new Error('Failed to fetch Quran verse');
      err.status = 502;
      throw err;
    }

    const arabicAyah = arabicRes.data.data;
    const transAyah = transRes.data.data;

    const arabicText = arabicAyah.text;
    const translationText = transAyah.text;
    const surahInfo = arabicAyah.surah || {};

    const translator =
      (transAyah.edition && transAyah.edition.englishName) || 'Unknown';

    return {
      arabic_text: arabicText,
      translation: translationText,
      translator,
      surah_name_arabic: surahInfo.name || '',
      surah_name_english: surahInfo.englishName || ''
    };
  } catch (error) {
    const err = new Error('Failed to fetch Quran verse');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  getQuranVerse
};

