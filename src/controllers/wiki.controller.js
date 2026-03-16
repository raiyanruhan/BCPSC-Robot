// Controller for the Wikipedia summary tool.
// Ensures a topic is provided and handles the distinction between a missing
// page (404) and general upstream failures (502 via the service).

const { getSummary } = require('../services/wiki.service');

async function handleWiki(req, res, next) {
  try {
    const topic = req.body && req.body.topic;

    if (!topic || typeof topic !== 'string') {
      return res.status(400).json({ error: 'Missing required field: topic' });
    }

    const summary = await getSummary(topic);

    if (!summary) {
      return res.status(404).json({ error: 'Wikipedia page not found' });
    }

    const responseBody = {
      title: summary.title,
      summary: summary.extract,
      url: summary.url
    };

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleWiki
};

