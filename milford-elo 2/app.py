"""
Milford Elo Ranking — a small Flask app.

Run locally:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000

The page (templates/index.html) does all Elo math in the browser by replaying
every vote in order, so the server only stores players and votes.
"""
import os
import sqlite3
import time
import uuid

from flask import Flask, g, jsonify, request, send_file, abort

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "elo.db"))
UPLOAD_DIR = os.path.join(BASE, "static", "uploads")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB uploads

# Starting roster (id, name). Photos live in static/photos/<id>.jpg
ROSTER = [
    ("rascati", "Rascati"), ("nate", "Nate"), ("horse", "Horse"), ("walat", "Walat"),
    ("lefave", "Lefave"), ("finney", "Finney"), ("brian", "Brian"), ("hurley", "Hurley"),
    ("brad", "Brad"), ("judge", "Judge"), ("sebas", "Sebas"), ("marcus", "Marcus"),
    ("crozier", "Crozier"), ("jeremy", "Jeremy"), ("ben", "Ben"), ("gabe", "Gabe"),
    ("schuld", "Schuld"), ("craig", "Craig"), ("david", "David"), ("nick", "Nick"),
    ("nobles", "Nobles"), ("roman", "Roman"),
]


# ---------- database ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            photo TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            a TEXT NOT NULL,
            b TEXT NOT NULL,
            result TEXT NOT NULL CHECK (result IN ('a','b','draw')),
            at INTEGER NOT NULL,
            voter TEXT
        );
        """
    )
    if conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 0:
        now = int(time.time() * 1000)
        for pid, name in ROSTER:
            photo = f"/static/photos/{pid}.jpg"
            if not os.path.exists(os.path.join(BASE, "static", "photos", f"{pid}.jpg")):
                photo = ""
            conn.execute(
                "INSERT INTO players (id, name, photo, created_at) VALUES (?,?,?,?)",
                (pid, name, photo, now),
            )
    conn.commit()
    conn.close()


def new_id():
    return uuid.uuid4().hex[:12]


# ---------- pages ----------
@app.get("/")
def index():
    return send_file(os.path.join(BASE, "templates", "index.html"))


# ---------- API ----------
@app.get("/api/state")
def state():
    players = [
        {"id": r["id"], "name": r["name"], "photo": r["photo"], "createdAt": r["created_at"]}
        for r in db().execute("SELECT * FROM players")
    ]
    matches = [
        {"id": r["id"], "a": r["a"], "b": r["b"], "result": r["result"], "at": r["at"], "by": r["voter"]}
        for r in db().execute("SELECT * FROM matches ORDER BY at")
    ]
    return jsonify(players=players, matches=matches)


@app.post("/api/players")
def add_player():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:32]
    if not name:
        abort(400)
    exists = db().execute("SELECT 1 FROM players WHERE lower(name)=lower(?)", (name,)).fetchone()
    if exists:
        abort(409)
    pid = new_id()
    db().execute(
        "INSERT INTO players (id, name, photo, created_at) VALUES (?,?,?,?)",
        (pid, name, "", int(time.time() * 1000)),
    )
    db().commit()
    return jsonify(id=pid), 201


@app.patch("/api/players/<pid>")
def update_player(pid):
    data = request.get_json(silent=True) or {}
    photo = data.get("photo")
    if not isinstance(photo, str) or not photo.startswith("/static/"):
        abort(400)
    cur = db().execute("UPDATE players SET photo=? WHERE id=?", (photo, pid))
    db().commit()
    if cur.rowcount == 0:
        abort(404)
    return "", 204


@app.post("/api/matches")
def add_match():
    data = request.get_json(silent=True) or {}
    a, b, result = data.get("a"), data.get("b"), data.get("result")
    if not a or not b or a == b or result not in ("a", "b", "draw"):
        abort(400)
    found = db().execute("SELECT COUNT(*) FROM players WHERE id IN (?,?)", (a, b)).fetchone()[0]
    if found != 2:
        abort(400)
    mid = new_id()
    db().execute(
        "INSERT INTO matches (id, a, b, result, at, voter) VALUES (?,?,?,?,?,?)",
        (mid, a, b, result, int(time.time() * 1000), str(data.get("by") or "")[:40] or None),
    )
    db().commit()
    return jsonify(id=mid), 201


@app.delete("/api/matches/<mid>")
def delete_match(mid):
    db().execute("DELETE FROM matches WHERE id=?", (mid,))
    db().commit()
    return "", 204


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        abort(400)
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        abort(400)
    name = new_id() + ext
    f.save(os.path.join(UPLOAD_DIR, name))
    return jsonify(url=f"/static/uploads/{name}"), 201


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
