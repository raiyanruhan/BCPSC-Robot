// Service wrapper for the Wikipedia REST API summary endpoint.
// Controllers rely on this module to abstract HTTP details and simply return
// either a structured summary object or null when the page is missing.

const axios = require('axios');

async function getSummary(topic) {
  const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(
    topic
  )}`;

  try {
    const response = await axios.get(url, {
      headers: {
        // Wikipedia requires a meaningful User-Agent for server-side requests.
        'User-Agent': 'robot-tools-server/1.0 (https://example.com)'
      },
      validateStatus: () => true,
      timeout: 10000
    });

    if (response.status === 404) {
      return null;
    }

    if (response.status < 200 || response.status >= 300) {
      const err = new Error('Failed to fetch Wikipedia summary');
      err.status = 502;
      throw err;
    }

    const data = response.data;

    return {
      title: data.title,
      extract: data.extract,
      url:
        data.content_urls &&
        data.content_urls.desktop &&
        data.content_urls.desktop.page
          ? data.content_urls.desktop.page
          : null
    };
  } catch (error) {
    if (error.status) {
      throw error;
    }

    const err = new Error('Failed to fetch Wikipedia summary');
    err.status = 502;
    throw err;
  }
}

module.exports = {
  getSummary
};

