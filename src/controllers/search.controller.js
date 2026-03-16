// Controller for the Google search tool.
// Validates the input query and delegates the web search to the Google CSE service.

const { searchWeb } = require('../services/googlecse.service');

async function handleSearch(req, res, next) {
  try {
    let query = req.body && req.body.query;

    if (!query || typeof query !== 'string') {
      return res.status(400).json({ error: 'Missing required field: query' });
    }

    // Basic sanitization: remove excessive whitespace and control characters.
    query = query.trim().replace(/[\x00-\x1F\x7F]/g, '');

    if (query.length > 200) {
      return res.status(400).json({ error: 'Search query is too long' });
    }

    const results = await searchWeb(query);

    const responseBody = {
      results
    };

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleSearch
};

