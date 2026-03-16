// Service wrapper around the Free Dictionary API.
// This module hides the sometimes-complex response shape and gives controllers
// a predictable object or null when the word does not exist.

const axios = require('axios');

async function lookupWord(word) {
  const url = `https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(
    word
  )}`;

  try {
    const response = await axios.get(url, {
      validateStatus: () => true,
      timeout: 10000
    });

    if (response.status === 404) {
      // The API signals missing entries via 404 with a JSON body.
      return null;
    }

    if (response.status < 200 || response.status >= 300) {
      const err = new Error('Failed to fetch dictionary entry');
      err.status = 502;
      throw err;
    }

    const data = Array.isArray(response.data) ? response.data[0] : null;
    if (!data) {
      return null;
    }

    const wordText = data.word || word;
    const meanings = Array.isArray(data.meanings) ? data.meanings : [];
    const firstMeaning = meanings[0] || {};
    const definitions = Array.isArray(firstMeaning.definitions)
      ? firstMeaning.definitions
      : [];
    const firstDefinition = definitions[0] || {};

    return {
      word: wordText,
      meaning: firstDefinition.definition || null,
      example: firstDefinition.example || null
    };
  } catch (error) {
    if (error.status) {
      throw error;
    }
    const err = new Error('Failed to fetch dictionary entry');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  lookupWord
};

