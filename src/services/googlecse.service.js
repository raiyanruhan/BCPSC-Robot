// Service for Google Custom Search Engine (CSE).
// Responsible only for calling the CSE JSON API and shaping the minimal data
// needed by the controller, not for any wording or presentation decisions.

const axios = require('axios');
const { GOOGLE_CSE_KEY, GOOGLE_CSE_ENGINE_ID } = require('../config/env');

async function searchWeb(query) {
  if (!GOOGLE_CSE_KEY || !GOOGLE_CSE_ENGINE_ID) {
    const err = new Error('Google CSE credentials are not configured');
    err.status = 502;
    throw err;
  }

  const url = 'https://www.googleapis.com/customsearch/v1';

  try {
    const response = await axios.get(url, {
      params: {
        q: query,
        key: GOOGLE_CSE_KEY,
        cx: GOOGLE_CSE_ENGINE_ID,
        num: 3
      },
      timeout: 8000 // Slightly lower than default 10s to fail faster
    });

    const items = Array.isArray(response.data.items) ? response.data.items : [];

    const results = items.slice(0, 3).map((item) => ({
      title: item.title || '',
      snippet: item.snippet || '',
      link: item.link || ''
    }));

    return results;
  } catch (error) {
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      // Return an empty list as fallback instead of throwing 502.
      return [];
    }
    const err = new Error('Failed to perform Google Custom Search');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  searchWeb
};

