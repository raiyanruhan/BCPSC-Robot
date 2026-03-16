// Service wrapper around the GNews API.
// The controller interface stays the same (topic in, normalized headlines out),
// but the underlying provider is now gnews.io instead of NewsData.io.

const axios = require('axios');
const { GNEWS_API_KEY } = require('../config/env');

async function getNewsByTopic(topic) {
  if (!GNEWS_API_KEY) {
    const err = new Error('GNews API key is not configured');
    err.status = 502;
    throw err;
  }

  // Use the generic search endpoint with as few restrictive filters as possible.
  // This avoids country/category combinations that can easily yield empty sets,
  // especially on the free tier, while still letting the "topic" drive results.
  const url = 'https://gnews.io/api/v4/search';

  try {
    const params = {
      apikey: GNEWS_API_KEY,
      lang: 'en',
      q: topic || 'news',
      max: 5
    };

    const response = await axios.get(url, {
      params,
      timeout: 8000
    });

    const articles = Array.isArray(response.data.articles)
      ? response.data.articles
      : [];

    const headlines = articles
      .filter((item) => item && item.title && item.description)
      .slice(0, 5)
      .map((item) => ({
        title: item.title,
        source_id: item.source && item.source.name ? item.source.name : null,
        description: item.description,
        link: item.url || null
      }));

    return headlines;
  } catch (error) {
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      // Return empty headlines as fallback on timeout.
      return [];
    }
    const err = new Error('Failed to fetch news data from GNews');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  getNewsByTopic
};

