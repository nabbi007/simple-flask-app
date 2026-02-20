import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

DB_PATH = Path(os.environ.get("PLANNER_DB_PATH", Path(__file__).with_name("planner.db")))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            goal_hours INTEGER NOT NULL DEFAULT 8,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            priority TEXT NOT NULL CHECK(priority IN ('High', 'Medium', 'Low')),
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Done')),
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS study_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            block_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            focus TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """
    )
    db.commit()
    db.close()


def duration_hours(start_time, end_time):
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return 0.0
    seconds = (end - start).total_seconds()
    return max(0.0, seconds / 3600.0)


@app.route("/")
def home():
    db = get_db()
    subjects = db.execute(
        "SELECT id, name, goal_hours, created_at FROM subjects ORDER BY created_at DESC"
    ).fetchall()
    deadlines = db.execute(
        """
        SELECT d.id, d.subject_id, s.name AS subject_name, d.title, d.due_date, d.priority, d.status
        FROM deadlines d
        JOIN subjects s ON s.id = d.subject_id
        ORDER BY d.due_date ASC
        """
    ).fetchall()
    blocks = db.execute(
        """
        SELECT b.id, b.subject_id, s.name AS subject_name, b.block_date, b.start_time, b.end_time, b.focus, b.completed
        FROM study_blocks b
        JOIN subjects s ON s.id = b.subject_id
        ORDER BY b.block_date ASC, b.start_time ASC
        """
    ).fetchall()

    subject_cards = []
    for subject in subjects:
        subject_blocks = [b for b in blocks if b["subject_id"] == subject["id"]]
        total_hours = sum(duration_hours(b["start_time"], b["end_time"]) for b in subject_blocks)
        completed_hours = sum(
            duration_hours(b["start_time"], b["end_time"]) for b in subject_blocks if b["completed"]
        )
        progress = 0
        if subject["goal_hours"] > 0:
            progress = min(100, int((completed_hours / subject["goal_hours"]) * 100))

        subject_cards.append(
            {
                "id": subject["id"],
                "name": subject["name"],
                "goal_hours": subject["goal_hours"],
                "planned_hours": round(total_hours, 1),
                "completed_hours": round(completed_hours, 1),
                "progress": progress,
                "pending_deadlines": sum(
                    1
                    for d in deadlines
                    if d["subject_id"] == subject["id"] and d["status"] == "Pending"
                ),
            }
        )

    timeline_items = []
    for d in deadlines:
        timeline_items.append(
            {
                "kind": "deadline",
                "id": d["id"],
                "subject_name": d["subject_name"],
                "title": d["title"],
                "priority": d["priority"],
                "status": d["status"],
                "date": d["due_date"],
                "time": "23:59",
            }
        )
    for b in blocks:
        timeline_items.append(
            {
                "kind": "block",
                "id": b["id"],
                "subject_name": b["subject_name"],
                "title": b["focus"],
                "priority": "Study Block",
                "status": "Done" if b["completed"] else "Pending",
                "date": b["block_date"],
                "time": b["start_time"],
                "range": f"{b['start_time']} - {b['end_time']}",
            }
        )

    timeline_items.sort(key=lambda item: (item["date"], item["time"]))

    return render_template(
        "index.html",
        subjects=subjects,
        subject_cards=subject_cards,
        timeline_items=timeline_items,
        today=datetime.now().strftime("%Y-%m-%d"),
        total_pending=sum(1 for d in deadlines if d["status"] == "Pending"),
    )


@app.route("/subjects", methods=["POST"])
def add_subject():
    name = request.form.get("name", "").strip()
    goal_hours = request.form.get("goal_hours", "8").strip()
    if not name:
        flash("Subject name is required.")
        return redirect(url_for("home"))

    try:
        goal = max(1, int(goal_hours))
    except ValueError:
        flash("Goal hours must be a number.")
        return redirect(url_for("home"))

    db = get_db()
    try:
        db.execute("INSERT INTO subjects(name, goal_hours) VALUES(?, ?)", (name, goal))
        db.commit()
        flash("Subject added.")
    except sqlite3.IntegrityError:
        flash("That subject already exists.")
    return redirect(url_for("home"))


@app.route("/deadlines", methods=["POST"])
def add_deadline():
    subject_id = request.form.get("subject_id", "").strip()
    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "").strip()
    priority = request.form.get("priority", "Medium").strip()
    if not (subject_id and title and due_date):
        flash("Deadline requires subject, title, and due date.")
        return redirect(url_for("home"))

    db = get_db()
    db.execute(
        "INSERT INTO deadlines(subject_id, title, due_date, priority) VALUES(?, ?, ?, ?)",
        (subject_id, title, due_date, priority if priority in {"High", "Medium", "Low"} else "Medium"),
    )
    db.commit()
    flash("Deadline added.")
    return redirect(url_for("home"))


@app.route("/blocks", methods=["POST"])
def add_study_block():
    subject_id = request.form.get("subject_id", "").strip()
    block_date = request.form.get("block_date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    focus = request.form.get("focus", "").strip()
    if not (subject_id and block_date and start_time and end_time and focus):
        flash("Study block requires all fields.")
        return redirect(url_for("home"))

    if duration_hours(start_time, end_time) <= 0:
        flash("End time must be after start time.")
        return redirect(url_for("home"))

    db = get_db()
    db.execute(
        """
        INSERT INTO study_blocks(subject_id, block_date, start_time, end_time, focus)
        VALUES(?, ?, ?, ?, ?)
        """,
        (subject_id, block_date, start_time, end_time, focus),
    )
    db.commit()
    flash("Study block scheduled.")
    return redirect(url_for("home"))


@app.route("/deadlines/<int:deadline_id>/toggle", methods=["POST"])
def toggle_deadline(deadline_id):
    db = get_db()
    row = db.execute("SELECT status FROM deadlines WHERE id = ?", (deadline_id,)).fetchone()
    if row:
        next_status = "Done" if row["status"] == "Pending" else "Pending"
        db.execute("UPDATE deadlines SET status = ? WHERE id = ?", (next_status, deadline_id))
        db.commit()
    return redirect(url_for("home"))


@app.route("/blocks/<int:block_id>/toggle", methods=["POST"])
def toggle_block(block_id):
    db = get_db()
    row = db.execute("SELECT completed FROM study_blocks WHERE id = ?", (block_id,)).fetchone()
    if row:
        next_value = 0 if row["completed"] else 1
        db.execute("UPDATE study_blocks SET completed = ? WHERE id = ?", (next_value, block_id))
        db.commit()
    return redirect(url_for("home"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
