// Controller for the dictionary lookup tool.
// Distinguishes between a word that truly does not exist (404) and any other
// kind of failure (mapped to 502 by the service layer).

const { lookupWord } = require('../services/dictionary.service');

async function handleDictionary(req, res, next) {
  try {
    const word = req.body && req.body.word;

    if (!word || typeof word !== 'string') {
      return res.status(400).json({ error: 'Missing required field: word' });
    }

    const result = await lookupWord(word);

    if (!result) {
      return res.status(404).json({ error: 'Word not found' });
    }

    const responseBody = {
      word: result.word,
      meaning: result.meaning,
      example: result.example
    };

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleDictionary
};

