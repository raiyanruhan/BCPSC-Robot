// Controller for the news tool.
// Applies simple request validation, consults the cache, then calls the NewsData
// service to retrieve and normalize headlines for the agent.

const { getNewsByTopic } = require('../services/newsdata.service');
const cache = require('../utils/cache');

const TEN_MINUTES_MS = 10 * 60 * 1000;

async function handleNews(req, res, next) {
  try {
    const topic = req.body && req.body.topic;

    if (!topic || typeof topic !== 'string') {
      return res.status(400).json({ error: 'Missing required field: topic' });
    }

    const cacheKey = `news:${topic.toLowerCase()}`;
    const cached = cache.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }

    const headlinesRaw = await getNewsByTopic(topic);

    const responseBody = {
      headlines: headlinesRaw.map((item) => ({
        title: item.title,
        source: item.source_id || null,
        summary: item.description,
        url: item.link
      }))
    };

    cache.set(cacheKey, responseBody, TEN_MINUTES_MS);

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleNews
};

