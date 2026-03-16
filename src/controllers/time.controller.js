// Controller for the time tool.
// Uses the server clock and Intl.DateTimeFormat to present time in the
// Asia/Dhaka timezone without relying on any external services.

async function handleTime(req, res, next) {
  try {
    const now = new Date();

    // Format time and date in the Asia/Dhaka timezone so callers do not need
    // to do their own timezone arithmetic.
    const timeFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Dhaka',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });

    const dateFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Dhaka',
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    const dayFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Dhaka',
      weekday: 'long'
    });

    const time = timeFormatter.format(now);
    const date = dateFormatter.format(now);
    const day = dayFormatter.format(now);

    const responseBody = {
      time,
      date,
      day,
      timezone: 'Asia/Dhaka'
    };

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleTime
};

