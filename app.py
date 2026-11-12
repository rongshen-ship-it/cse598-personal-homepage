"""Personal Homepage with AI Assistant — CSE/MB 598, Project 1.

Stack: Python + Flask. All homepage content lives in content.json, and
every item carries a visibility tag: public / signed_in / selected / owner.

The key rule: before anything is shown on the page or sent to the language
model, visible_items(role) filters content.json by the visitor's role.
The assistant only ever sees what the current visitor is allowed to see.
"""
import json
import os
import re
import secrets
import time
import urllib.request

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

VISIBILITY_LEVELS = {"public": 0, "signed_in": 1, "selected": 2, "owner": 3}
SELECTED_VISITORS = set(
    v for v in os.environ.get("SELECTED_VISITORS", "").split(",") if v
)


def load_content():
    path = os.path.join(os.path.dirname(__file__), "content.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def visitor_role():
    # Demo only: the role comes from the switcher on the homepage.
    # Replaced by verified Beagle sign-in (see README, "Beagle sign-in").
    return session.get("role", "public")


def visible_items(role):
    """Return only the content.json items this visitor may see."""
    level = VISIBILITY_LEVELS[role]
    out = {}
    for section, items in load_content().items():
        kept = [
            it
            for it in items
            if VISIBILITY_LEVELS[it.get("visibility", "public")] <= level
        ]
        if kept:
            out[section] = kept
    return out


@app.route("/")
def index():
    role = visitor_role()
    return render_template(
        "index.html", role=role, content=visible_items(role)
    )


@app.route("/api/role", methods=["POST"])
def set_role():
    """Demo-only role switcher. Removed once Beagle sign-in works."""
    role = (request.json or {}).get("role", "public")
    if role not in VISIBILITY_LEVELS:
        return jsonify({"error": "unknown role"}), 400
    session["role"] = role
    return jsonify({"role": role})


@app.route("/api/auth/nonce")
def nonce():
    """Single-use nonce for Beagle sign-in (120 s expiry, per Beagle docs)."""
    value = secrets.token_urlsafe(24)
    session["beagle_nonce"] = {"value": value, "expires": time.time() + 120}
    return jsonify({"nonce": value})


@app.route("/api/auth/beagle", methods=["POST"])
def beagle_auth():
    # TODO (week 2): verify the XEdDSA signature server-side before minting
    # a session. See README "Beagle sign-in" and
    # https://beagle.chat/en/docs/beagle-connect/
    return jsonify(
        {"error": "Beagle server verification not implemented yet"}
    ), 501


@app.route("/api/chat", methods=["POST"])
def chat():
    role = visitor_role()
    message = ((request.json or {}).get("message") or "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400
    visible = visible_items(role)
    context = "\n".join(
        f"- {it.get('title', '')}: {it.get('text', '')}"
        for items in visible.values()
        for it in items
    )
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        answer = ask_llm(message, context, key)
    else:
        answer = keyword_answer(message, visible)
    return jsonify({"role": role, "answer": answer})


def keyword_answer(message, visible):
    """Fallback when no LLM key is set: search only the visible content."""
    words = [w for w in re.findall(r"[a-z0-9]+", message.lower()) if len(w) > 2]
    best, score = None, 0
    for items in visible.values():
        for it in items:
            text = (it.get("title", "") + " " + it.get("text", "")).lower()
            s = sum(1 for w in words if w in text)
            if s > score:
                best, score = it, s
    if best:
        return best.get("text", "")
    return (
        "I can only answer from the information on this page that you are "
        "allowed to see. Try asking about my education, experience, or projects."
    )


def ask_llm(message, context, key):
    """Ask the model with ONLY the visitor-permitted content as context."""
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the assistant on Rong Shen Eaton's personal "
                        "homepage. Answer ONLY from the information below. If "
                        "the information is not there, say so; never invent "
                        "details.\n\n" + context
                    ),
                },
                {"role": "user", "content": message},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
