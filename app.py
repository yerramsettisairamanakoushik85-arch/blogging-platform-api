from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timezone

app = Flask(__name__)
DB = "blog.db"


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT NOT NULL,
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def post_data(row):
    data = dict(row)
    data["tags"] = data["tags"].split(",") if data["tags"] else []
    return data


def validate(data):
    required = ["title", "content", "category", "tags"]

    if not data:
        return "Request body is required"

    for field in required:
        if field not in data:
            return f"{field} is required"

    if not all(isinstance(data["tags"], str) for _ in [0]):
        if not isinstance(data["tags"], list):
            return "tags must be an array"

    if not isinstance(data["tags"], list):
        return "tags must be an array"

    return None


@app.route("/posts", methods=["POST"])
def create_post():
    data = request.get_json()
    error = validate(data)

    if error:
        return jsonify({"error": error}), 400

    now = datetime.now(timezone.utc).isoformat()

    conn = connect()
    cursor = conn.execute("""
        INSERT INTO posts
        (title, content, category, tags, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["title"],
        data["content"],
        data["category"],
        ",".join(data["tags"]),
        now,
        now
    ))

    conn.commit()
    post_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()

    return jsonify(post_data(row)), 201


@app.route("/posts", methods=["GET"])
def get_posts():
    term = request.args.get("term")

    conn = connect()

    if term:
        search = f"%{term}%"
        rows = conn.execute("""
            SELECT * FROM posts
            WHERE title LIKE ?
               OR content LIKE ?
               OR category LIKE ?
        """, (search, search, search)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM posts").fetchall()

    conn.close()

    return jsonify([post_data(row) for row in rows]), 200


@app.route("/posts/<int:post_id>", methods=["GET"])
def get_post(post_id):
    conn = connect()
    row = conn.execute(
        "SELECT * FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Post not found"}), 404

    return jsonify(post_data(row)), 200


@app.route("/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    data = request.get_json()
    error = validate(data)

    if error:
        return jsonify({"error": error}), 400

    conn = connect()
    existing = conn.execute(
        "SELECT * FROM posts WHERE id = ?", (post_id,)
    ).fetchone()

    if not existing:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        UPDATE posts
        SET title = ?, content = ?, category = ?, tags = ?, updatedAt = ?
        WHERE id = ?
    """, (
        data["title"],
        data["content"],
        data["category"],
        ",".join(data["tags"]),
        now,
        post_id
    ))

    conn.commit()
    row = conn.execute(
        "SELECT * FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    conn.close()

    return jsonify(post_data(row)), 200


@app.route("/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    conn = connect()
    cursor = conn.execute(
        "DELETE FROM posts WHERE id = ?", (post_id,)
    )
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "Post not found"}), 404

    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(port=5002, debug=True)