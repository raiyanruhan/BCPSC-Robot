// Centralized Express error handling middleware.
// This ensures every failure path returns the same JSON structure so the
// ElevenLabs agent can rely on consistent error messages.

// eslint-disable-next-line no-unused-vars
module.exports = function errorHandler(err, req, res, next) {
  // Always log the full error server-side for debugging and monitoring.
  console.error(err);

  // Prefer an explicit status set by controllers/services, otherwise default.
  const status = err.status && Number.isInteger(err.status) ? err.status : 500;

  // Never leak stack traces or internal details to clients in production.
  const isProduction = process.env.NODE_ENV === 'production';
  const message =
    err.publicMessage ||
    err.message ||
    (status === 500 ? 'Internal server error' : 'Request failed');

  const payload = { error: message };

  // In non-production environments you might want stack traces, but the
  // requirements explicitly say not to expose them, so we never include them.
  res.status(status).json(payload);
};

