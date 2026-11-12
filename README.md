# Personal Homepage with AI Assistant

CSE/MB 598 — AI Agents for Academic and Career Networking, Project 1.
Owner: Rong Shen Eaton (individual project).

A personal website that presents my introduction, résumé, skills, and
project portfolio, with an AI assistant that answers visitors' questions
and helps draft updates. Every piece of content carries a visibility tag,
and the assistant only ever sees what the current visitor is allowed to see.

## How permissions work

Visibility levels, from widest to narrowest:

| Tag | Who can see it |
| --- | --- |
| `public` | Anyone, no sign-in |
| `signed_in` | Any visitor signed in with Beagle |
| `selected` | Only visitors the owner picked (Beagle userids in `SELECTED_VISITORS`) |
| `owner` | Only the owner |

All content lives in `content.json`. Before anything is shown on the page
or sent to the language model, `visible_items(role)` filters it by the
visitor's role. The permission check is a plain filter on the JSON file —
the model never receives content the visitor may not see.

## Project structure

```
app.py                 Flask app: pages, chat API, auth stubs
content.json           All homepage content, each item visibility-tagged
templates/index.html   Homepage template
static/style.css       Plain styling
requirements.txt       Python dependencies (Flask only)
```

## Run it locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000

## The assistant

`POST /api/chat` takes a visitor's question, filters `content.json` to
what that visitor may see, and answers from that filtered content only.

- If `OPENROUTER_API_KEY` is set in the environment, the filtered content
  is sent as context to the model (default `openai/gpt-4o-mini`, override
  with `OPENROUTER_MODEL`). Only permitted content is sent — nothing else.
- If no key is set, a simple keyword search over the visible content
  answers instead. No key, no cloud call.

Never put an API key in the repo. Use an environment variable or a local
`.env` file (`.env` is git-ignored).

## Beagle sign-in

Status: stubbed in week 1, wired in week 2.

- `GET /api/auth/nonce` issues a single-use nonce (120 s expiry), as the
  Beagle docs require.
- `POST /api/auth/beagle` currently returns 501: server-side signature
  verification is not implemented yet.
- The homepage has a demo role switcher (Public / Signed in / Selected /
  Owner) so the permission filtering can be tested end to end before
  Beagle verification lands. It is clearly marked demo-only and will be
  removed once real sign-in works.

Docs: https://beagle.chat/en/docs/beagle-connect/

Beagle sign-in uses the npm client `@decentnetwork/beagle-connect` and
server verification with `@decentnetwork/peer` (XEdDSA, not Ed25519 — the
public half of the key *is* the userid). The server must verify the
`decent-auth` prefix, our own origin, and the single-use nonce before
minting a session. Because our backend is Python, the week-2 plan is a
small Node.js verification service using `@decentnetwork/peer`, or a
Python XEdDSA implementation — whichever proves simpler.

## Deployment

Not deployed yet. Target for the final demonstration: a hosted Python
service (e.g. Render or PythonAnywhere) with the same code and
`content.json`, plus the Beagle sign-in flow above.
