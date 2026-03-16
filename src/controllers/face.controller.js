// Face context controllers.
// The Raspberry Pi pushes face recognition state to the server, and the
// ElevenLabs agent can request a short "who is in front" context snapshot.
//
// This is intentionally in-memory and last-write-wins to keep the server
// stateless and compatible with shared hosting constraints (no DB/Redis).

let currentFace = null;

function setCurrentFace(nextFace) {
  currentFace = nextFace;
}

function getCurrentFace() {
  return currentFace;
}

async function handleFaceUpdate(req, res, next) {
  try {
    const body = req.body || {};

    // Pi always sends person, but it can also explicitly send { person: null }
    // when no face is detected.
    const hasPersonField = Object.prototype.hasOwnProperty.call(body, 'person');
    if (!hasPersonField) {
      return res.status(400).json({ error: 'Missing required field: person' });
    }

    const person = body.person;
    const confidence =
      typeof body.confidence === 'number' && !Number.isNaN(body.confidence)
        ? body.confidence
        : null;
    const language =
      typeof body.language === 'string' && body.language.trim()
        ? body.language.trim()
        : null;

    setCurrentFace({
      person: person === undefined ? null : person,
      confidence,
      language,
      received_at: Date.now()
    });

    // Keep Pi acknowledgment simple so it can send frequently.
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

async function handleGetFaceContext(req, res, next) {
  try {
    const face = getCurrentFace();
    const now = Date.now();

    // Treat stale (older than 10 seconds) as "no one in front".
    if (!face || !face.received_at || now - face.received_at > 10 * 1000 || face.person === null) {
      return res.json({
        success: true,
        data: {
          person_detected: false,
          person: null,
          summary: 'No one is currently in front of the camera.'
        }
      });
    }

    const secondsAgo = Math.max(0, Math.round((now - face.received_at) / 1000));
    const preferredLanguage = face.language === 'bn' ? 'bn' : 'en';

    if (face.person === 'unknown') {
      return res.json({
        success: true,
        data: {
          person_detected: true,
          person: 'unknown',
          confidence: typeof face.confidence === 'number' ? face.confidence : 0.0,
          preferred_language: preferredLanguage,
          seconds_ago: secondsAgo,
          summary: 'Someone is in front of the camera but I do not recognise them.'
        }
      });
    }

    // Recognized person name (string).
    return res.json({
      success: true,
      data: {
        person_detected: true,
        person: face.person,
        confidence: typeof face.confidence === 'number' ? face.confidence : null,
        preferred_language: preferredLanguage,
        seconds_ago: secondsAgo,
        summary: `${face.person} is currently in front of the camera. He prefers ${
          preferredLanguage === 'bn' ? 'Bangla' : 'English'
        }.`
      }
    });
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleFaceUpdate,
  handleGetFaceContext,
  // Exported for testability and to keep state explicit.
  setCurrentFace,
  getCurrentFace
};

