"""
Nexonic — Knowledge Preservation System
Flask backend: serves HTML, handles admin auth, and exposes DB management API.
"""

from flask import Flask, render_template, request, jsonify, session
import sqlite3
import os
import base64
import requests as http_req
from pathlib import Path
from functools import wraps
from datetime import datetime
from typing import Optional

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nexonic-secret-key-2024-xK9pQ7")

# ── Configuration ────────────────────────────────────────────────────────────
SQL_FOLDER = Path("./sql")
SQL_FOLDER.mkdir(exist_ok=True)

ADMIN_USER = "admin"
ADMIN_PASS = "admin"

DB_EXTENSIONS = {".db", ".sqlite", ".sqlite3"}
ALLOWED_EXTENSIONS = DB_EXTENSIONS | {".sql"}

# ── GitHub Upload Configuration ───────────────────────────────────────────────
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "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")
GITHUB_OWNER   = "Lizardfol"
GITHUB_REPO    = "Nexanic"
GITHUB_BRANCH  = "main"
GITHUB_FOLDER  = "database"
GITHUB_ALLOWED = {".json", ".mp3", ".mp4", ".txt"}


# ── Auth helpers ─────────────────────────────────────────────────────────────
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized", "code": 401}), 401
        return f(*args, **kwargs)
    return decorated


def _safe_path(filename: str) -> Optional[Path]:
    """Return a safe path inside SQL_FOLDER, or None if suspicious."""
    name = Path(filename).name  # strips any directory traversal
    path = SQL_FOLDER / name
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    return path


def _db_conn(filename: str):
    """Return (conn, error_string). conn is None on failure."""
    path = _safe_path(filename)
    if path is None or not path.exists():
        return None, "File not found or not allowed"
    if path.suffix.lower() not in DB_EXTENSIONS:
        return None, "Not a SQLite database file"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn, None


# ── Page routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}
    if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASS:
        session["admin_logged_in"] = True
        return jsonify({"ok": True, "message": "Welcome, admin!"})
    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/status")
def auth_status():
    return jsonify({"authenticated": bool(session.get("admin_logged_in"))})


# ── Database API ──────────────────────────────────────────────────────────────
@app.route("/api/db/files")
@require_admin
def list_files():
    files = []
    for p in sorted(SQL_FOLDER.iterdir()):
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        st = p.stat()
        files.append({
            "name": p.name,
            "size": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            "type": "database" if p.suffix.lower() in DB_EXTENSIONS else "sql_script",
            "ext": p.suffix.lower(),
        })
    return jsonify({"files": files, "folder": str(SQL_FOLDER.resolve())})


@app.route("/api/db/<filename>/tables")
@require_admin
def get_tables(filename):
    conn, err = _db_conn(filename)
    if err:
        return jsonify({"error": err}), 404
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') ORDER BY name"
        )
        items = [{"name": r["name"], "type": r["type"]} for r in cur.fetchall()]
        return jsonify({"items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/db/<filename>/schema/<table>")
@require_admin
def get_schema(filename, table):
    conn, err = _db_conn(filename)
    if err:
        return jsonify({"error": err}), 404
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info([{table}])")
        columns = [
            {"name": r["name"], "type": r["type"], "pk": bool(r["pk"]), "notnull": bool(r["notnull"])}
            for r in cur.fetchall()
        ]
        return jsonify({"columns": columns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/db/<filename>/data/<table>")
@require_admin
def get_data(filename, table):
    conn, err = _db_conn(filename)
    if err:
        return jsonify({"error": err}), 404

    limit = min(request.args.get("limit", 50, type=int), 1000)
    offset = request.args.get("offset", 0, type=int)
    sort_col = request.args.get("sort", None)
    sort_dir = "DESC" if request.args.get("dir", "asc").lower() == "desc" else "ASC"
    search = request.args.get("search", "").strip()

    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info([{table}])")
        col_info = [{"name": r["name"], "type": r["type"], "pk": bool(r["pk"])} for r in cur.fetchall()]
        col_names = [c["name"] for c in col_info]

        where_clause = ""
        params: list = []
        if search and col_names:
            conditions = " OR ".join(f"CAST([{c}] AS TEXT) LIKE ?" for c in col_names)
            where_clause = f" WHERE {conditions}"
            params = [f"%{search}%"] * len(col_names)

        order_clause = ""
        if sort_col and sort_col in col_names:
            order_clause = f" ORDER BY [{sort_col}] {sort_dir}"

        cur.execute(f"SELECT COUNT(*) AS cnt FROM [{table}]{where_clause}", params)
        total = cur.fetchone()["cnt"]

        cur.execute(
            f"SELECT * FROM [{table}]{where_clause}{order_clause} LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        rows = [dict(r) for r in cur.fetchall()]

        return jsonify({
            "columns": col_info,
            "rows": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/db/<filename>/query", methods=["POST"])
@require_admin
def execute_query(filename):
    conn, err = _db_conn(filename)
    if err:
        return jsonify({"error": err}), 404

    data = request.get_json(force=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    try:
        cur = conn.cursor()
        cur.execute(query)
        if cur.description:
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            return jsonify({"columns": columns, "rows": rows, "affected": len(rows), "type": "select"})
        else:
            conn.commit()
            return jsonify({"columns": [], "rows": [], "affected": cur.rowcount, "type": "modify"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/db/sql/<filename>")
@require_admin
def read_sql_script(filename):
    path = _safe_path(filename)
    if path is None or not path.exists() or path.suffix.lower() != ".sql":
        return jsonify({"error": "SQL script not found"}), 404
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return jsonify({"content": content, "filename": path.name})


# ── GitHub Upload API ─────────────────────────────────────────────────────────
def _gh_headers():
    """Always use Bearer — works for classic PATs and fine-grained tokens alike."""
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _gh_error(resp):
    """Return a human-readable error string from a GitHub API response."""
    try:
        body = resp.json()
    except Exception:
        return f"HTTP {resp.status_code}"

    if resp.status_code == 401:
        return "Bad credentials — GITHUB_TOKEN is invalid or expired"
    if resp.status_code == 403:
        return "Forbidden — token lacks 'Contents: write' permission on this repo"
    if resp.status_code == 404:
        return "Not found — check repo name, branch, and folder path"
    if resp.status_code == 422:
        return "Unprocessable — SHA conflict or invalid payload"
    return body.get("message") or f"GitHub error {resp.status_code}"


@app.route("/api/admin/github-test")
@require_admin
def github_test():
    """Quick credential / repo-access check."""
    if not GITHUB_TOKEN:
        return jsonify({"ok": False, "error": "GITHUB_TOKEN env var is not set"}), 503

    url  = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
    resp = http_req.get(url, headers=_gh_headers(), timeout=10)
    if resp.status_code == 200:
        d = resp.json()
        return jsonify({"ok": True, "repo": d.get("full_name"), "private": d.get("private")})
    return jsonify({"ok": False, "error": _gh_error(resp)}), resp.status_code


@app.route("/api/admin/github-files")
@require_admin
def github_list_files():
    """List all files in the database/ folder on GitHub."""
    if not GITHUB_TOKEN:
        return jsonify({"ok": False, "error": "GITHUB_TOKEN env var is not set"}), 503

    url  = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
    resp = http_req.get(url, headers=_gh_headers(), timeout=10)
    if resp.status_code == 200:
        items = [
            {
                "name":         f["name"],
                "size":         f["size"],
                "sha":          f["sha"],
                "download_url": f["download_url"],
                "html_url":     f["html_url"],
                "type":         f["type"],
            }
            for f in resp.json()
            if f.get("type") == "file"
        ]
        return jsonify({"ok": True, "files": items})
    return jsonify({"ok": False, "error": _gh_error(resp)}), resp.status_code


@app.route("/api/admin/github-upload", methods=["POST"])
@require_admin
def github_upload():
    if not GITHUB_TOKEN:
        return jsonify({"error": "GITHUB_TOKEN env var is not set on the server"}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in GITHUB_ALLOWED:
        return jsonify({"error": "Only .json, .mp3, .mp4, .txt files are allowed"}), 400

    file_bytes = f.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        return jsonify({"error": "File too large — max 25 MB"}), 413

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in f.filename)
    api_url   = (
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/contents/{GITHUB_FOLDER}/{safe_name}"
    )

    # Fetch existing SHA so we can overwrite instead of failing with 422
    sha  = None
    chk  = http_req.get(api_url, headers=_gh_headers(), timeout=10)
    if chk.status_code == 200:
        sha = chk.json().get("sha")
    elif chk.status_code == 401:
        return jsonify({"error": _gh_error(chk)}), 401

    payload = {
        "message": f"Upload {safe_name} via Nexonic Admin",
        "content": base64.b64encode(file_bytes).decode("utf-8"),
        "branch":  GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    resp = http_req.put(api_url, headers=_gh_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201):
        gh_content = resp.json().get("content", {})
        return jsonify({
            "success":      True,
            "filename":     safe_name,
            "html_url":     gh_content.get("html_url", ""),
            "download_url": gh_content.get("download_url", ""),
        })

    return jsonify({"error": _gh_error(resp)}), resp.status_code


# ── Sample DB seed ────────────────────────────────────────────────────────────
def _seed_sample_db():
    db_path = SQL_FOLDER / "nexonic_demo.db"
    if db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS knowledge_entries (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        title          TEXT    NOT NULL,
        category       TEXT,
        location       TEXT,
        person_name    TEXT,
        date_recorded  TEXT,
        summary        TEXT,
        language       TEXT    DEFAULT 'hu',
        duration_sec   INTEGER,
        verified       INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id       INTEGER REFERENCES knowledge_entries(id),
        started_at     TEXT,
        ended_at       TEXT,
        questions_asked INTEGER,
        robot_id       TEXT    DEFAULT 'NEX-001'
    );

    CREATE TABLE IF NOT EXISTS tags (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER REFERENCES knowledge_entries(id),
        tag      TEXT NOT NULL
    );
    """)

    entries = [
        ("ZIL váltó javítása", "Mesterségek", "Nyíregyháza", "Kovács János", "2024-03-15",
         "A régi ZIL teherautók váltójának javítási technikái, amelyeket az 1960-as évek mechanikusai alkalmaztak. "
         "Az alkatrészek már nem kaphatók, de a helyi műszaki tudás segítségével pótolhatók.", "hu", 1842, 1),
        ("Tirpák savanyítás", "Gasztronómia", "Nyíregyháza", "Szabó Erzsébet", "2024-03-22",
         "A tirpák káposzta savanyításának hagyományos módszere, amelyet csak a Nyíregyháza környéki falvakban ismernek. "
         "A só és a köményes fűszer arányát csak szájhagyomány útján adják tovább.", "hu", 2134, 1),
        ("Régi méhészeti technikák", "Mesterségek", "Debrecen", "Nagy Sándor", "2024-04-02",
         "Hagyományos méhészeti módszerek, amelyeket a Hortobágy melletti falvakban alkalmaztak. "
         "A természetes gyógyításra és a legelőváltásra vonatkozó generációs tudás.", "hu", 3201, 1),
        ("Helyi legendák — Tisza-part", "Néphagyomány", "Tokaj", "Kiss Margit", "2024-04-10",
         "A Tisza melletti falvak szóbeli hagyományai: árvizek, csodák és határkövek történetei. "
         "Ezek a legendák megmagyarázzák, hogyan alakult ki a helyi közösség identitása.", "hu", 1567, 0),
        ("Elfeledett asztalosmesterség", "Mesterségek", "Miskolc", "Tóth Béla", "2024-04-18",
         "A XIX. századi bükki asztalosok különleges csapolási és ragasztási technikái, "
         "amelyeket ma már sehol sem tanítanak. A bútorkészítés apáról fiúra szállt fogásai.", "hu", 2876, 1),
        ("Traditional ZIL gearbox repair", "Crafts", "Nyíregyháza", "John Kovacs", "2024-03-15",
         "Repair techniques for old ZIL truck gearboxes used by mechanics in the 1960s. "
         "Parts are no longer available but local technical knowledge provides substitutes.", "en", 1842, 1),
    ]

    cur.executemany(
        "INSERT INTO knowledge_entries (title,category,location,person_name,date_recorded,summary,language,duration_sec,verified) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        entries,
    )

    sessions_data = [
        (1, "2024-03-15T10:00:00", "2024-03-15T10:30:42", 5, "NEX-001"),
        (2, "2024-03-22T14:00:00", "2024-03-22T14:35:34", 6, "NEX-001"),
        (3, "2024-04-02T09:00:00", "2024-04-02T09:53:21", 8, "NEX-002"),
        (4, "2024-04-10T11:00:00", "2024-04-10T11:26:07", 4, "NEX-001"),
        (5, "2024-04-18T15:00:00", "2024-04-18T15:47:56", 7, "NEX-002"),
    ]
    cur.executemany(
        "INSERT INTO sessions (entry_id,started_at,ended_at,questions_asked,robot_id) VALUES (?,?,?,?,?)",
        sessions_data,
    )

    tags_data = [
        (1, "szerszám"), (1, "szovjet"), (1, "gépjármű"),
        (2, "recept"), (2, "savanyítás"), (2, "tirpák"),
        (3, "méhészet"), (3, "természet"), (3, "Hortobágy"),
        (4, "legenda"), (4, "Tisza"), (4, "árvíz"),
        (5, "bútor"), (5, "fafeldolgozás"), (5, "Bükk"),
    ]
    cur.executemany("INSERT INTO tags (entry_id,tag) VALUES (?,?)", tags_data)

    conn.commit()
    conn.close()
    print(f"[nexonic] Sample database created: {db_path}")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _seed_sample_db()
    app.run(debug=True, port=5005, host="0.0.0.0")
