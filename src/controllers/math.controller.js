// Controller for the math evaluation tool.
// Uses mathjs locally so no external API is involved, and converts parse or
// evaluation errors into clean 400 responses instead of generic 500 errors.

const math = require('mathjs');

async function handleMath(req, res, next) {
  try {
    const expression = req.body && req.body.expression;

    if (!expression || typeof expression !== 'string') {
      return res.status(400).json({ error: 'Missing required field: expression' });
    }

    let result;
    try {
      // math.evaluate can throw for invalid syntax or unsupported constructs.
      result = math.evaluate(expression);
    } catch (mathErr) {
      return res.status(400).json({ error: 'Invalid or unparseable expression' });
    }

    const responseBody = {
      expression,
      result: String(result)
    };

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleMath
};

