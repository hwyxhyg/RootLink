export default async function handler(req, res) {
  // Allow CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { text, session_id, lang = 'en' } = req.body;

  const ip =
    (req.headers['x-forwarded-for'] || '').split(',')[0].trim() ||
    req.socket?.remoteAddress ||
    'unknown';

  // Record visit
  fetch(`${process.env.SUPABASE_URL}/rest/v1/visits`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: process.env.SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${process.env.SUPABASE_SERVICE_KEY}`
    },
    body: JSON.stringify({
      ip,
      session_id
    })
  }).catch(() => {});

  if (!text) {
    return res.status(400).json({ error: 'Missing text' });
  }

  try {
    const response = await fetch(
      'https://ywgvb8rbmk.coze.site/stream_run',
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${process.env.COZE_TOKEN}`,
          'Content-Type': 'application/json'
        },

        body: JSON.stringify({
          content: {
            query: {
              prompt: [
                {
                  type: 'text',
                  content: {
                    text
                  }
                }
              ],
              lang
            }
          },

          type: 'query',

          session_id: session_id || 'default_session',

          project_id: 7608474915389521966
        })
      }
    );

    if (!response.ok) {
      const err = await response.text();

      return res.status(response.status).json({
        error: err
      });
    }

    // Stream Coze response back to frontend
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      const chunk = decoder.decode(value, {
        stream: true
      });

      res.write(chunk);
    }

    res.end();
  } catch (err) {
    console.error(err);

    return res.status(500).json({
      error: err.message
    });
  }
}
