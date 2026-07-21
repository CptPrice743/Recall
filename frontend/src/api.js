/**
 * Recall API Client
 * 
 * This module manages communication with the Recall backend.
 * To integrate with a real backend, update the BASE_URL below
 * and implement the `/api/query` endpoint on your server.
 */

// Toggle this to true to force real API calls, or false to use simulator settings.
const USE_REAL_BACKEND = false; 
const BASE_URL = 'http://localhost:5000'; // Replace with your backend URL

// Canned prototype archive sources
export const PROTOTYPE_SOURCES = {
  shirtPost: {
    type: 'post',
    platform: 'IG',
    title: '@harbor.goods — Spring drop 02',
    meta: 'APR 12',
    full: 'Saved from Instagram · @harbor.goods\n\n“Spring drop 02 is live. The Harbor overshirt in tide stripe — blue/cream, brushed cotton, boxy fit. Limited run, ships worldwide.”',
    fullMeta: 'INSTAGRAM · SAVED APR 12, 10:41 PM'
  },
  shirtShot: {
    type: 'shot',
    title: 'Screenshot_2026-04-14_09.12.png',
    meta: 'APR 14',
    img: { 
      label: 'IMG · 1170 × 2532', 
      caption: 'SCREENSHOT — PRODUCT PAGE, STRIPED TEE',
      src: '/striped_tee_screenshot.jpg' 
    },
    full: 'OCR — “Breton Tee — Navy / Ecru · $48 · 100% organic cotton. Classic boat neck, relaxed fit. Size guide · Add to cart”',
    fullMeta: 'SCREENSHOT · APR 14 · CAMERA ROLL'
  },
  shirtNote: {
    type: 'note',
    title: 'To buy — spring',
    meta: 'APR 15',
    full: 'To buy — spring\n\n— linen trousers (check the usual place first)\n— striped overshirt (the blue one from IG)\n— replace running socks\n— sunscreen, the non-greasy one',
    fullMeta: 'NOTE · EDITED APR 15'
  },
  cabinFile: {
    type: 'file',
    platform: 'PDF',
    title: 'Checkin_Guide_Riverbend_Cabin.pdf',
    meta: 'JUN 20',
    full: 'Check-in Guide — Riverbend Cabin (p. 2 of 6)\n\nWi-Fi: TROUTHOUSE-5G\nPassword: riverbend2214\nRouter is in the hallway closet — power-cycle it if the signal drops.\nDoor code: 4415#',
    fullMeta: 'PDF · 6 PAGES · SAVED JUN 20'
  },
  cabinNote: {
    type: 'note',
    title: 'June cabin trip',
    meta: 'JUN 21',
    full: 'June cabin trip\n\nwifi: TROUTHOUSE-5G / riverbend2214\ndoor code 4415#\ncheckout by 11am Sunday\nhost: Dana (text, don’t call)',
    fullMeta: 'NOTE · EDITED JUN 21'
  }
};

/**
 * Returns a canned response for local prototyping based on query keywords.
 */
export function getMockAnswer(q, model) {
  const S = PROTOTYPE_SOURCES;
  const t = q.toLowerCase();

  const makeAnswer = (answer, srcs) => ({
    kind: 'answer',
    answer,
    model,
    sources: srcs.map(s => ({ ...s }))
  });

  if (/stripe|shirt|overshirt/.test(t)) {
    return makeAnswer(
      'Most likely the blue-and-cream striped overshirt from an Instagram post you saved on April 12 — @harbor.goods, their “Spring drop 02”[1]. Two days later you also screenshotted a breton-stripe tee product page — navy on ecru, $48[2] — and your spring to-buy note lists “striped overshirt (the blue one from IG)”[3].\n\nThe overshirt is the stronger match; the tee has thinner stripes.',
      [S.shirtPost, S.shirtShot, S.shirtNote]
    );
  }
  if (/wifi|wi-fi|cabin|airbnb|password/.test(t)) {
    return makeAnswer(
      'TROUTHOUSE-5G, password riverbend2214.\n\nIt’s on page 2 of the host’s check-in PDF[1], and you copied it into your “June cabin trip” note along with the door code (4415#)[2].',
      [S.cabinFile, S.cabinNote]
    );
  }
  if (/blue|navy|colou?r/.test(t)) {
    return makeAnswer(
      'The @harbor.goods overshirt is mid-blue on cream — they call it “tide stripe”[1]. The tee in your screenshot is the darker one: navy on ecru[2].',
      [S.shirtPost, S.shirtShot]
    );
  }
  if (/tax|deadline/.test(t)) {
    return {
      kind: 'noresults',
      body: 'Nothing in your archive mentions tax deadlines — no notes, screenshots, saved posts, or files matched.'
    };
  }

  return makeAnswer(
    'I couldn’t find a confident match for that in your archive.\n\n(Prototype note: only a few questions have canned answers — try the striped shirt, the cabin wifi, or the tax-deadline example from a fresh session.)',
    []
  );
}

/**
 * Sends a query to the backend, supporting simulator modes.
 * 
 * Expected Backend JSON Response for SUCCESS:
 * {
 *   "kind": "answer",
 *   "answer": "Answer text with citation tokens like [1] and [2]...",
 *   "model": "gemini-3.5-flash",
 *   "sources": [
 *     { "type": "post", "platform": "IG", "title": "Title", "meta": "Date", "full": "Body", "fullMeta": "Footer" }
 *   ]
 * }
 * 
 * Expected Backend JSON Response for NO RESULTS:
 * {
 *   "kind": "noresults",
 *   "body": "Explanation message..."
 * }
 * 
 * Backend HTTP Errors:
 * - 401 Unauthorized (Invalid Token)
 * - 429 Too Many Requests (Rate Limit)
 * - 500/503 (Server/Service down)
 */
export async function queryArchive(query, token, model, simMode = 'normal', coldStartSeconds = 8) {
  // 1. Real Backend Branch
  if (USE_REAL_BACKEND) {
    try {
      const response = await fetch(`${BASE_URL}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query, model })
      });

      if (response.status === 401) {
        throw { status: 401, message: 'TOKEN REJECTED · 401\n\nThe backend refused your access token. It may have been rotated — paste the current one and ask again.' };
      }
      if (response.status === 429) {
        throw { status: 429, message: 'RATE LIMITED · 429\n\nThe underlying API quota was hit. Your question is kept — wait a few seconds and retry.' };
      }
      if (!response.ok) {
        throw { status: response.status, message: `Backend error (${response.status}). Check server logs.` };
      }

      return await response.json();
    } catch (err) {
      if (err.status) throw err;
      throw { status: 503, message: 'BACKEND UNREACHABLE\n\nNo response — the backend never woke up. Check that it’s deployed and reachable, then retry. Your question is kept.' };
    }
  }

  // 2. Simulated Prototyping Branch
  return new Promise((resolve, reject) => {
    const delay = (ms) => new Promise(res => setTimeout(res, ms));

    const runSimulation = async () => {
      await delay(1500); // Simulate network latency

      switch (simMode) {
        case 'reject':
          reject({
            status: 401,
            message: 'TOKEN REJECTED · 401\n\nThe backend refused your access token. It may have been rotated — paste the current one and ask again.'
          });
          break;

        case 'rate':
          reject({
            status: 429,
            message: 'RATE LIMITED · 429\n\nThe underlying API quota was hit. Your question is kept — wait a few seconds and retry.'
          });
          break;

        case 'down':
          // Wait for cold start duration, then error
          await delay(coldStartSeconds * 1000);
          reject({
            status: 503,
            message: 'BACKEND UNREACHABLE\n\nNo response — the backend never woke up. Check that it’s deployed and reachable, then retry. Your question is kept.'
          });
          break;

        case 'cold':
          // Simulate cold start delay
          await delay(coldStartSeconds * 1000);
          resolve(getMockAnswer(query, model));
          break;

        case 'normal':
        default:
          resolve(getMockAnswer(query, model));
          break;
      }
    };

    runSimulation();
  });
}
