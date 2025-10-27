import os
import time
import re
import sqlite3
import pdfplumber
import pandas as pd
import sqlite3
from datetime import datetime, timezone, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, request

app = Flask(__name__)
app.secret_key = "supersecret"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_FILE = "jobcards.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Job cards table (main library of parsed cards)
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            card_no TEXT,
            parsed_json TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attachments (drawings, diagrams, etc. linked to a card)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(card_id) REFERENCES jobcards(id)
        )
    """)

    # Periodic maintenance visits (one record per PV started)
    c.execute("""
        CREATE TABLE IF NOT EXISTS periodic_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aircraft TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            status TEXT,  -- e.g. 'ongoing', 'finished'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Cards assigned to a periodic visit (link table)
    c.execute("""
        CREATE TABLE IF NOT EXISTS visit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER,
            card_id INTEGER,
            estimated_hours REAL,
            status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'done'
            FOREIGN KEY(visit_id) REFERENCES periodic_visits(id),
            FOREIGN KEY(card_id) REFERENCES jobcards(id)
        )
    """)

        # Workshops table (list of workshops)
    c.execute("""
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # Mapping table: links workshops to tasks
    c.execute("""
        CREATE TABLE IF NOT EXISTS workshop_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id INTEGER,
            card_id INTEGER,
            paragraph TEXT,
            step TEXT,
            substep TEXT,
            assignment_level TEXT, -- 'card', 'paragraph', 'step', 'substep'
            status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'done'
            FOREIGN KEY(workshop_id) REFERENCES workshops(id),
            FOREIGN KEY(card_id) REFERENCES jobcards(id)
        )
    """)
        # Materials master table
    c.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT,
            serial_number TEXT UNIQUE,
            designation TEXT,
            fsc TEXT,
            niin TEXT,
            nsn TEXT,
            category TEXT,          -- Rechange / Reparable / Outillage / Banc d'essai
            workshop_id INTEGER,    -- optional: main responsible workshop
            position TEXT,
            dotation INTEGER,
            avionne INTEGER,
            stock INTEGER,
            att_rpn INTEGER,
            rpn INTEGER,
            calibration_date TEXT,          -- YYYY-MM-DD
            calibration_expiration TEXT,    -- YYYY-MM-DD
            FOREIGN KEY(workshop_id) REFERENCES workshops(id)
        )
    """)

    # Link between jobcards and materials
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobcard_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jobcard_id INTEGER,
            material_id INTEGER,
            FOREIGN KEY(jobcard_id) REFERENCES jobcards(id),
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
    """)

    # Link between workshops and materials (extra to workshop_id in materials)
    c.execute("""
        CREATE TABLE IF NOT EXISTS workshop_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id INTEGER,
            material_id INTEGER,
            FOREIGN KEY(workshop_id) REFERENCES workshops(id),
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS aircrafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matriculation TEXT UNIQUE NOT NULL,
        type TEXT,
        base TEXT,
        notes TEXT
    )
    """)

    # Periodic visits: link to aircraft by id instead of plain string
    c.execute("""
    CREATE TABLE IF NOT EXISTS periodic_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aircraft_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(aircraft_id) REFERENCES aircrafts(id)
    )
    """)

    # Visit cards (unchanged here)
    c.execute("""
    CREATE TABLE IF NOT EXISTS visit_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id INTEGER,
        card_id INTEGER,
        status TEXT,
        sequence INTEGER,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        suspended INTEGER DEFAULT 0,
        suspended_reason TEXT,
        FOREIGN KEY(visit_id) REFERENCES periodic_visits(id),
        FOREIGN KEY(card_id) REFERENCES jobcards(id)
    )
    """)


    conn.commit()
    conn.close()

def ensure_jobcard_meta():
    """Add pdf_filename, warnings, cautions, notes columns to jobcards table if missing."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # get column names
    c.execute("PRAGMA table_info(jobcards)")
    cols = [r[1] for r in c.fetchall()]
    # columns we want
    extras = {
        "pdf_filename": "TEXT",
        "warnings": "TEXT",
        "cautions": "TEXT",
        "notes": "TEXT"
    }
    for col, typ in extras.items():
        if col not in cols:
            # sqlite cannot add column with NOT NULL default easily; we add a simple column
            c.execute(f"ALTER TABLE jobcards ADD COLUMN {col} {typ}")
    conn.commit()
    conn.close()




def seed_workshops():
    """Populate default workshops if they don't exist."""
    default_workshops = ['MOTEUR', 'EQT/BORD', 'RADIO', 'APG', 'HELICE',
                         'FUEL', 'CHAUD', 'MARS', 'S/S', 'DRS', 'NDI']
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for w in default_workshops:
        c.execute("INSERT OR IGNORE INTO workshops (name) VALUES (?)", (w,))
    conn.commit()
    conn.close()


def ensure_periodic_visits_extra_cols():
    """Ensure periodic_visits has vp_type column."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA table_info(periodic_visits)")
    cols = [r[1] for r in c.fetchall()]
    if "vp_type" not in cols:
        c.execute("ALTER TABLE periodic_visits ADD COLUMN vp_type TEXT")
    conn.commit()
    conn.close()

def ensure_visit_cards_columns():
    """Ensure visit_cards has useful columns: estimated_hours, sequence, started_at, completed_at, suspended, suspended_reason."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA table_info(visit_cards)")
    cols = [r[1] for r in c.fetchall()]
    extras = {
        "sequence": "INTEGER",
        "started_at": "TIMESTAMP",
        "completed_at": "TIMESTAMP",
        "suspended": "INTEGER DEFAULT 0",
        "suspended_reason": "TEXT",
        "estimated_hours": "REAL"
    }
    for col, typ in extras.items():
        if col not in cols:
            c.execute(f"ALTER TABLE visit_cards ADD COLUMN {col} {typ}")
    conn.commit()
    conn.close()

def ensure_vp_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # visit_cards extra columns already added in earlier helper but ensure again safely
    c.execute("PRAGMA table_info(visit_cards)")
    existing_cols = [r[1] for r in c.fetchall()]
    extras = {
        "sequence": "INTEGER",
        "started_at": "TIMESTAMP",
        "completed_at": "TIMESTAMP",
        "suspended": "INTEGER DEFAULT 0",
        "suspended_reason": "TEXT",
        "estimated_hours": "REAL"
    }
    for col, typ in extras.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE visit_cards ADD COLUMN {col} {typ}")

    # Create table to record paragraph/step completion & interruptions
    c.execute("""
        CREATE TABLE IF NOT EXISTS paragraph_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_card_id INTEGER,
            paragraph_index INTEGER,
            paragraph_text TEXT,
            step_index INTEGER,
            step_text TEXT,
            technician_name TEXT,
            technician_rank TEXT,
            status TEXT, -- 'done', 'interrupted'
            interruption_reason TEXT,
            interruption_type TEXT, -- 'material','personnel','other'
            notes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(visit_card_id) REFERENCES visit_cards(id)
        )
    """)

    # Keep jobcard_materials, materials, workshop_materials assumed present from previous steps.

    conn.commit()
    conn.close()

def ensure_aircraft_id_column():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA table_info(periodic_visits)")
    cols = [r[1] for r in c.fetchall()]
    if "aircraft_id" not in cols:
        c.execute("ALTER TABLE periodic_visits ADD COLUMN aircraft_id INTEGER")
    conn.commit()
    conn.close()


def ensure_progress_tables():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS card_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER,
            card_id INTEGER,
            paragraph TEXT,
            step TEXT,
            substep TEXT,
            technician TEXT,
            rank TEXT,
            status TEXT, -- done / interrupted / pending
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()
ensure_jobcard_meta()
ensure_periodic_visits_extra_cols()
ensure_visit_cards_columns()
ensure_vp_db()
ensure_aircraft_id_column()
ensure_progress_tables()
seed_workshops()

@app.route("/")
def home():
    return render_template("home.html")


def parse_job_card(pdf_path):
    job_data = []
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    lines = text.splitlines()
    current_paragraph = None
    current_steps = []

    for line in lines:
        line = line.strip()
        if re.match(r"^\d+\.", line):  # Paragraph
            if current_paragraph:
                job_data.append({"paragraph": current_paragraph, "steps": current_steps})
            current_paragraph = line
            current_steps = []
        elif re.match(r"^[A-Z]\.", line):  # Step
            current_steps.append(line)

    if current_paragraph:
        job_data.append({"paragraph": current_paragraph, "steps": current_steps})

    # Build table rows (no paragraph repetition)
    rows = []
    for p in job_data:
        if p["steps"]:
            # First row has paragraph + first step
            rows.append([p["paragraph"], p["steps"][0]])
            # Following rows: only steps
            for step in p["steps"][1:]:
                rows.append(["", step])
        else:
            rows.append([p["paragraph"], ""])

    df = pd.DataFrame(rows, columns=["Paragraph", "Step"])
    return job_data, df


@app.route("/upload_jobcard", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected!", "danger")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected!", "danger")
            return redirect(request.url)

        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM jobcards WHERE filename=?", (file.filename,))
            existing = c.fetchone()

            if existing:
                flash("Job card already exists. Showing from library.", "info")
                conn.close()
                return redirect(url_for("library"))

            # Save and parse new
            file.save(filepath)
            parsed_json, df = parse_job_card(filepath)

            # Save into DB
            c.execute("INSERT INTO jobcards (filename, card_no, parsed_json) VALUES (?, ?, ?)",
                    (file.filename, file.filename.split(".")[0], str(parsed_json)))
            card_id = c.lastrowid   # ✅ get the ID of the new record
            conn.commit()
            conn.close()

            rows = df.values.tolist()
            return render_template("table.html",
                                card_name=file.filename,
                                table_data=rows,
                                card_id=card_id)   # ✅ now card_id is defined

    return render_template("upload.html")

@app.route("/library")
def library():
    updated = request.args.get("updated")
    if updated:
        flash("✅ Order updated successfully!", "success")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # ✅ join with attachments to count images
    c.execute("""
        SELECT j.id, j.filename, j.card_no, j.uploaded_at,
               COUNT(a.id) as drawings_count
        FROM jobcards j
        LEFT JOIN attachments a ON j.id = a.card_id
        GROUP BY j.id
        ORDER BY j.uploaded_at DESC
    """)
    jobcards = c.fetchall()
    conn.close()

    return render_template("library.html", jobcards=jobcards)



@app.route("/view/<int:card_id>")
def view_card(card_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT filename, parsed_json, pdf_filename, warnings, cautions, notes FROM jobcards WHERE id=?", (card_id,))
    result = c.fetchone()

    c.execute("SELECT id, filename FROM attachments WHERE card_id=?", (card_id,))
    attachments = c.fetchall()
    conn.close()

    if not result:
        flash("Job card not found.", "danger")
        return redirect(url_for("library"))

    filename, parsed_json, pdf_filename, warnings, cautions, notes = result
    import ast
    job_data = ast.literal_eval(parsed_json)

    rows = []
    for p in job_data:
        if p["steps"]:
            rows.append([p["paragraph"], p["steps"][0]])
            for step in p["steps"][1:]:
                rows.append(["", step])
        else:
            rows.append([p["paragraph"], ""])

    return render_template(
        "view.html",
        card_name=filename,
        table_data=rows,
        card_id=card_id,
        attachments=attachments,
        pdf_filename=pdf_filename,
        warnings=warnings,
        cautions=cautions,
        notes=notes
    )

    
from flask import jsonify

@app.route("/edit/<int:card_id>")
@app.route("/edit/<int:card_id>")
def edit_card(card_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT filename, parsed_json, pdf_filename, warnings, cautions, notes FROM jobcards WHERE id=?", (card_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        flash("Job card not found.", "danger")
        return redirect(url_for("library"))

    filename, parsed_json, pdf_filename, warnings, cautions, notes = result

    # attachments
    c.execute("SELECT id, filename FROM attachments WHERE card_id=?", (card_id,))
    attachments = c.fetchall()

    # all workshops
    c.execute("SELECT id, name FROM workshops ORDER BY name")
    workshops = c.fetchall()

    # existing assignments for this card (if you still need)
    c.execute("""
        SELECT wt.id, wt.workshop_id, w.name, wt.paragraph, wt.step, wt.substep, wt.assignment_level, wt.status
        FROM workshop_tasks wt
        JOIN workshops w ON wt.workshop_id = w.id
        WHERE wt.card_id = ?
    """, (card_id,))
    assignments_raw = c.fetchall()
    conn.close()

    # parse job_data
    import ast, json
    try:
        # parsed_json was stored as str(job_data). We try ast.literal_eval, but allow json as well.
        job_data = ast.literal_eval(parsed_json) if parsed_json else []
    except Exception:
        try:
            job_data = json.loads(parsed_json) if parsed_json else []
        except Exception:
            job_data = []

    # build assignments_map as before
    assignments_map = {}
    for row in assignments_raw:
        at_id, workshop_id, workshop_name, para, step, substep, level, status = row
        key = (para or "", step or "", substep or "")
        assignments_map.setdefault(key, []).append({
            "task_id": at_id,
            "workshop_id": workshop_id,
            "workshop_name": workshop_name,
            "level": level,
            "status": status
        })

    return render_template("edit.html",
                           card_name=filename,
                           job_data=job_data,
                           card_id=card_id,
                           attachments=attachments,
                           workshops=workshops,
                           assignments_map=assignments_map,
                           pdf_filename=pdf_filename,
                           warnings=warnings,
                           cautions=cautions,
                           notes=notes)


@app.route("/reorder/<int:card_id>", methods=["POST"])
def reorder_card(card_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "No data received"}), 400

    job_data = []
    current_paragraph = None
    steps_buffer = []

    for row in data:
        para = row["paragraph"].strip()
        step = row["step"].strip()

        if para:  # new paragraph starts
            if current_paragraph is not None:
                job_data.append({"paragraph": current_paragraph, "steps": steps_buffer})
            current_paragraph = para
            steps_buffer = []

        if step:
            steps_buffer.append(step)

    if current_paragraph:
        job_data.append({"paragraph": current_paragraph, "steps": steps_buffer})

    # overwrite DB with this new structure
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE jobcards SET parsed_json=? WHERE id=?", (str(job_data), card_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/upload_drawing/<int:card_id>", methods=["POST"])
@app.route("/upload_drawing/<int:card_id>", methods=["POST"])
def upload_drawing(card_id):
    if "file" not in request.files:
        flash("No file selected", "danger")
        return redirect(url_for("edit_card", card_id=card_id))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("edit_card", card_id=card_id))

    draw_folder = os.path.join(UPLOAD_FOLDER, "drawings")
    os.makedirs(draw_folder, exist_ok=True)

    filepath = os.path.join(draw_folder, file.filename)
    file.save(filepath)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO attachments (card_id, filename) VALUES (?, ?)", (card_id, file.filename))
    conn.commit()
    conn.close()

    flash("Drawing uploaded successfully!", "success")
    return redirect(url_for("edit_card", card_id=card_id))

from flask import send_from_directory

@app.route('/uploads/drawings/<filename>')
def uploaded_drawing(filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, 'drawings'), filename)

@app.route("/delete_drawing/<int:attachment_id>/<int:card_id>", methods=["POST"])
def delete_drawing(attachment_id, card_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT filename FROM attachments WHERE id=?", (attachment_id,))
    result = c.fetchone()
    if result:
        filename = result[0]
        filepath = os.path.join(UPLOAD_FOLDER, "drawings", filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        c.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
        conn.commit()
    conn.close()

    flash("Drawing deleted successfully!", "success")
    return redirect(url_for("edit_card", card_id=card_id))


@app.route("/replace_drawing/<int:attachment_id>/<int:card_id>", methods=["POST"])
def replace_drawing(attachment_id, card_id):
    if "file" not in request.files:
        flash("No file selected", "danger")
        return redirect(url_for("edit_card", card_id=card_id))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("edit_card", card_id=card_id))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT filename FROM attachments WHERE id=?", (attachment_id,))
    result = c.fetchone()
    if result:
        old_filename = result[0]
        old_path = os.path.join(UPLOAD_FOLDER, "drawings", old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)  # remove old file

        new_path = os.path.join(UPLOAD_FOLDER, "drawings", file.filename)
        file.save(new_path)

        # update DB entry
        c.execute("UPDATE attachments SET filename=? WHERE id=?", (file.filename, attachment_id))
        conn.commit()
    conn.close()

    flash("Drawing replaced successfully!", "success")
    return redirect(url_for("edit_card", card_id=card_id))

import ast  # used when reading parsed_json from DB

# -- assign task(s) to workshop(s) --
@app.route("/assign_task", methods=["POST"])
def assign_task():
    card_id = request.form.get("card_id")
    workshop_ids = request.form.getlist("workshop_ids")  # list of workshop ids (strings)
    paragraph = request.form.get("paragraph", "") or ""
    step = request.form.get("step", "") or ""
    substep = request.form.get("substep", "") or ""
    assignment_level = request.form.get("assignment_level", "step")  # default 'step'

    if not card_id or not workshop_ids:
        flash("Missing card_id or workshops selected", "danger")
        return redirect(request.referrer or url_for("library"))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for wid in workshop_ids:
        # avoid exact duplicate
        c.execute("""
            SELECT id FROM workshop_tasks
            WHERE workshop_id=? AND card_id=? AND paragraph=? AND step=? AND substep=? AND assignment_level=?
        """, (wid, card_id, paragraph, step, substep, assignment_level))
        if not c.fetchone():
            c.execute("""
                INSERT INTO workshop_tasks (workshop_id, card_id, paragraph, step, substep, assignment_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (wid, card_id, paragraph, step, substep, assignment_level))
    conn.commit()
    conn.close()

    flash("Assignment saved.", "success")
    return redirect(request.referrer or url_for("edit_card", card_id=card_id))


# -- remove an assignment (unassign) --
@app.route("/unassign_task/<int:task_id>", methods=["POST"])
def unassign_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT card_id FROM workshop_tasks WHERE id=?", (task_id,))
    row = c.fetchone()
    card_id = row[0] if row else None
    c.execute("DELETE FROM workshop_tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    flash("Assignment removed.", "success")
    return redirect(request.referrer or url_for("edit_card", card_id=card_id if card_id else 0))


# -- workshops list page --
@app.route("/workshops")
def workshops_list():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT w.id, w.name,
               (SELECT COUNT(*) FROM workshop_tasks t WHERE t.workshop_id = w.id) AS task_count
        FROM workshops w
        ORDER BY w.name
    """)
    workshops = c.fetchall()
    conn.close()
    return render_template("workshops.html", workshops=workshops)


# -- workshop details (tasks assigned to that workshop) --
@app.route("/workshop/<int:workshop_id>")
def workshop_detail(workshop_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM workshops WHERE id=?", (workshop_id,))
    workshop = c.fetchone()
    if not workshop:
        conn.close()
        flash("Workshop not found.", "danger")
        return redirect(url_for("workshops_list"))

    # fetch assigned tasks (join to jobcards to get filename)
    c.execute("""
        SELECT wt.id, wt.card_id, j.filename, wt.paragraph, wt.step, wt.substep, wt.assignment_level, wt.status
        FROM workshop_tasks wt
        LEFT JOIN jobcards j ON wt.card_id = j.id
        WHERE wt.workshop_id = ?
        ORDER BY j.filename, wt.paragraph
    """, (workshop_id,))
    tasks = c.fetchall()
    conn.close()
    return render_template("workshop_detail.html", workshop=workshop, tasks=tasks)


# -- change status of a workshop_task (pending / in_progress / done) --
@app.route("/workshop_task_status/<int:task_id>", methods=["POST"])
def workshop_task_status(task_id):
    new_status = request.form.get("status")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE workshop_tasks SET status=? WHERE id=?", (new_status, task_id))
    conn.commit()
    # fetch card_id for redirect
    c.execute("SELECT card_id FROM workshop_tasks WHERE id=?", (task_id,))
    row = c.fetchone()
    conn.close()
    return redirect(request.referrer or url_for("library"))

# -------- MATERIALS --------

@app.route("/materials")
def materials_list():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT m.id, m.part_number, m.serial_number, m.designation,
               m.category, m.stock, m.avionne, m.dotation,
               w.name as workshop_name
        FROM materials m
        LEFT JOIN workshops w ON m.workshop_id = w.id
        ORDER BY m.designation
    """)
    materials = c.fetchall()
    conn.close()
    return render_template("materials.html", materials=materials)


@app.route("/material/new", methods=["GET", "POST"])
def material_new():
    if request.method == "POST":
        part_number = request.form.get("part_number")
        serial_number = request.form.get("serial_number")
        designation = request.form.get("designation")
        fsc = request.form.get("fsc")
        niin = request.form.get("niin")
        nsn = request.form.get("nsn")
        category = request.form.get("category")
        workshop_id = request.form.get("workshop_id") or None
        position = request.form.get("position")
        dotation = request.form.get("dotation") or 0
        avionne = request.form.get("avionne") or 0
        stock = request.form.get("stock") or 0
        att_rpn = request.form.get("att_rpn") or 0
        rpn = request.form.get("rpn") or 0
        calibration_date = request.form.get("calibration_date")
        calibration_expiration = request.form.get("calibration_expiration")

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO materials (
                part_number, serial_number, designation, fsc, niin, nsn,
                category, workshop_id, position, dotation, avionne, stock,
                att_rpn, rpn, calibration_date, calibration_expiration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (part_number, serial_number, designation, fsc, niin, nsn,
              category, workshop_id, position, dotation, avionne, stock,
              att_rpn, rpn, calibration_date, calibration_expiration))
        conn.commit()
        conn.close()

        flash("Material added successfully!", "success")
        return redirect(url_for("materials_list"))

    # GET: fetch workshops for dropdown
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM workshops ORDER BY name")
    workshops = c.fetchall()
    conn.close()
    return render_template("material_form.html", workshops=workshops, material=None)


@app.route("/material/<int:material_id>/edit", methods=["GET", "POST"])
def material_edit(material_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if request.method == "POST":
        # update
        data = (
            request.form.get("part_number"),
            request.form.get("serial_number"),
            request.form.get("designation"),
            request.form.get("fsc"),
            request.form.get("niin"),
            request.form.get("nsn"),
            request.form.get("category"),
            request.form.get("workshop_id") or None,
            request.form.get("position"),
            request.form.get("dotation") or 0,
            request.form.get("avionne") or 0,
            request.form.get("stock") or 0,
            request.form.get("att_rpn") or 0,
            request.form.get("rpn") or 0,
            request.form.get("calibration_date"),
            request.form.get("calibration_expiration"),
            material_id
        )
        c.execute("""
            UPDATE materials SET
                part_number=?, serial_number=?, designation=?, fsc=?, niin=?, nsn=?,
                category=?, workshop_id=?, position=?, dotation=?, avionne=?, stock=?,
                att_rpn=?, rpn=?, calibration_date=?, calibration_expiration=?
            WHERE id=?
        """, data)
        conn.commit()
        conn.close()
        flash("Material updated successfully!", "success")
        return redirect(url_for("materials_list"))

    # GET: fetch record + workshops
    c.execute("SELECT * FROM materials WHERE id=?", (material_id,))
    material = c.fetchone()
    c.execute("SELECT id, name FROM workshops ORDER BY name")
    workshops = c.fetchall()
    conn.close()
    return render_template("material_form.html", workshops=workshops, material=material)


@app.route("/material/<int:material_id>/delete", methods=["POST"])
def material_delete(material_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM materials WHERE id=?", (material_id,))
    conn.commit()
    conn.close()
    flash("Material deleted.", "success")
    return redirect(url_for("materials_list"))


@app.route('/uploads/pdfs/<filename>')
def uploaded_pdf(filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, 'pdfs'), filename)

@app.route("/card/import", methods=["GET", "POST"])
def import_card():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        # ensure pdf folder
        pdf_folder = os.path.join(UPLOAD_FOLDER, "pdfs")
        os.makedirs(pdf_folder, exist_ok=True)
        save_name = file.filename
        filepath = os.path.join(pdf_folder, save_name)
        file.save(filepath)

        # parse job card from pdf (use your parse_job_card function)
        parsed_json, df = parse_job_card(filepath)  # adapt if parse_job_card returns different shape

        # store the new jobcard w/ pdf_filename and parsed_json
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO jobcards (filename, card_no, parsed_json, pdf_filename)
            VALUES (?, ?, ?, ?)
        """, (save_name, save_name.split(".")[0], str(parsed_json), save_name))
        card_id = c.lastrowid
        conn.commit()
        conn.close()

        flash("PDF imported and job card created. You can now edit the card.", "success")
        return redirect(url_for("edit_card", card_id=card_id))
    # GET
    return render_template("import_card.html")

@app.route("/card/new", methods=["GET","POST"])
def create_card():
    if request.method == "POST":
        filename = request.form.get("filename") or f"manual_{int(time.time())}.card"
        card_no = request.form.get("card_no") or filename.split(".")[0]
        # empty parsed_json initially
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO jobcards (filename, card_no, parsed_json) VALUES (?, ?, ?)",
                  (filename, card_no, str([])))
        card_id = c.lastrowid
        conn.commit()
        conn.close()
        flash("Manual card created — now edit it.", "success")
        return redirect(url_for("edit_card", card_id=card_id))
    return render_template("create_card.html")

from flask import jsonify

# Save parsed structure JSON
@app.route("/card/save_structure/<int:card_id>", methods=["POST"])
def save_card_structure(card_id):
    data = request.get_json()
    if not data or 'job_data' not in data:
        return "No job_data received", 400
    job_data = data['job_data']
    # basic validation: ensure it's a list of dicts
    if not isinstance(job_data, list):
        return "job_data must be a list", 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE jobcards SET parsed_json=? WHERE id=?", (str(job_data), card_id))
    conn.commit()
    conn.close()
    return jsonify({"status":"ok"})

# Save meta (warnings, cautions, notes)
@app.route("/card/save_meta/<int:card_id>", methods=["POST"])
def save_card_meta(card_id):
    warnings = request.form.get("warnings", "")
    cautions = request.form.get("cautions", "")
    notes = request.form.get("notes", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE jobcards SET warnings=?, cautions=?, notes=? WHERE id=?", (warnings, cautions, notes, card_id))
    conn.commit()
    conn.close()
    flash("Metadata saved.", "success")
    return redirect(url_for("edit_card", card_id=card_id))

# Upload/replace PDF attached to card
@app.route("/card/replace_pdf/<int:card_id>", methods=["POST"])
def replace_card_pdf(card_id):
    file = request.files.get("file")
    if not file:
        flash("No file uploaded.", "danger")
        return redirect(url_for("edit_card", card_id=card_id))

    pdf_folder = os.path.join(UPLOAD_FOLDER, "pdfs")
    os.makedirs(pdf_folder, exist_ok=True)
    save_name = file.filename
    filepath = os.path.join(pdf_folder, save_name)
    file.save(filepath)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE jobcards SET pdf_filename=? WHERE id=?", (save_name, card_id))
    conn.commit()
    conn.close()

    flash("PDF uploaded and linked to card.", "success")
    return redirect(url_for("edit_card", card_id=card_id))

@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # show ongoing visits
    c.execute("""
        SELECT id, aircraft, aircraft_id, start_date, end_date, status, vp_type, created_at
        FROM periodic_visits
        WHERE status LIKE 'ongoing%' OR status='ongoing' OR status LIKE 'Started%' OR status='Started'
        ORDER BY start_date DESC, created_at DESC
    """)
    raw_visits = c.fetchall()
    visits = []
    for v in raw_visits:
        vid, aircraft_text, aircraft_id, start_date, end_date, status, vp_type, created_at = v
        # compute counts safely
        c.execute("SELECT COUNT(*) FROM visit_cards WHERE visit_id=?", (vid,))
        total = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM visit_cards WHERE visit_id=? AND status='done'", (vid,))
        done = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM visit_cards WHERE visit_id=? AND status='in_progress'", (vid,))
        inprog = c.fetchone()[0] or 0
        pending = max(total - done - inprog, 0)
        pct = int((done / total) * 100) if total > 0 else 0

        visits.append({
            "id": vid,
            "aircraft": aircraft_text or ("#"+str(aircraft_id) if aircraft_id else "N/A"),
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "type": vp_type or "N/A",
            "total": total,
            "done": done,
            "in_progress": inprog,
            "pending": pending,
            "pct": pct
        })
    conn.close()
    return render_template("dashboard.html", visits=visits)

# ---------- API: visit detail for expanded card ----------
@app.route("/api/visit/<int:visit_id>/detail")
def api_visit_detail(visit_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # visit info
    c.execute("SELECT id, aircraft, aircraft_id, start_date, end_date, status, vp_type FROM periodic_visits WHERE id=?", (visit_id,))
    v = c.fetchone()
    if not v:
        conn.close()
        return jsonify({"error":"visit not found"}), 404
    vid, aircraft_text, aircraft_id, start_date, end_date, status, vp_type = v
    # gather visit_cards and jobcard info
    c.execute("""
        SELECT vc.id, vc.card_id, vc.status, vc.sequence, vc.started_at, vc.completed_at, vc.estimated_hours
        FROM visit_cards vc WHERE vc.visit_id=? ORDER BY vc.sequence IS NULL, vc.sequence, vc.id
    """, (visit_id,))
    vc_rows = c.fetchall()
    items = []
    for row in vc_rows:
        vc_id, card_id, vc_status, sequence, started_at, completed_at, est_hours = row
        # jobcard summary
        c.execute("SELECT filename, parsed_json, pdf_filename FROM jobcards WHERE id=?", (card_id,))
        jc = c.fetchone()
        if jc:
            filename, parsed_json, pdf_filename = jc
        else:
            filename, parsed_json, pdf_filename = ("Unknown", "[]", None)
        # try parse jobcard structure
        import ast, json
        try:
            job_data = ast.literal_eval(parsed_json) if parsed_json else []
        except Exception:
            try:
                job_data = json.loads(parsed_json) if parsed_json else []
            except Exception:
                job_data = []
        # get assigned workshops for this card (aggregated)
        c.execute("""
            SELECT w.id, w.name FROM workshop_tasks wt
            JOIN workshops w ON wt.workshop_id = w.id
            WHERE wt.card_id=?
            GROUP BY w.id
        """, (card_id,))
        workshops = [{"id":r[0],"name":r[1]} for r in c.fetchall()]

        # materials required for this jobcard (via jobcard_materials)
        c.execute("""
            SELECT m.id, m.part_number, m.serial_number, m.designation, m.category, m.stock, m.avionne, m.dotation, m.calibration_expiration
            FROM jobcard_materials jm
            JOIN materials m ON jm.material_id = m.id
            WHERE jm.jobcard_id = ?
        """, (card_id,))
        mats = []
        for m in c.fetchall():
            mats.append({
                "id": m[0],
                "part_number": m[1],
                "serial_number": m[2],
                "designation": m[3],
                "category": m[4],
                "stock": m[5] or 0,
                "avionne": m[6] or 0,
                "dotation": m[7] or 0,
                "calibration_expiration": m[8]
            })

        # paragraph/step status history (grouped per paragraph/step)
        c.execute("""
            SELECT paragraph_index, step_index, status, technician_name, technician_rank, interruption_reason, interruption_type, timestamp, notes
            FROM paragraph_status WHERE visit_card_id=? ORDER BY timestamp
        """, (vc_id,))
        ps_rows = c.fetchall()
        paragraph_history = []
        for pr in ps_rows:
            paragraph_history.append({
                "paragraph_index": pr[0],
                "step_index": pr[1],
                "status": pr[2],
                "technician_name": pr[3],
                "technician_rank": pr[4],
                "interruption_reason": pr[5],
                "interruption_type": pr[6],
                "timestamp": pr[7],
                "notes": pr[8]
            })

        items.append({
            "visit_card_id": vc_id,
            "card_id": card_id,
            "filename": filename,
            "status": vc_status,
            "sequence": sequence,
            "started_at": started_at,
            "completed_at": completed_at,
            "estimated_hours": est_hours,
            "job_data": job_data,
            "workshops": workshops,
            "materials": mats,
            "paragraph_history": paragraph_history,
        })
    conn.close()
    return jsonify({
        "visit": {"id": vid, "aircraft": aircraft_text, "start_date": start_date, "end_date": end_date, "status": status, "type": vp_type},
        "cards": items
    })

# ---------- API: start a card ----------
@app.route("/api/visit/<int:visit_id>/card/<int:visit_card_id>/start", methods=["POST"])
def api_start_card(visit_id, visit_card_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE visit_cards SET status='in_progress', started_at=? WHERE id=? AND visit_id=?", (now, visit_card_id, visit_id))
    conn.commit()
    conn.close()
    return jsonify({"status":"ok","started_at":now})

# ---------- API: complete a card ----------
@app.route("/api/visit/<int:visit_id>/card/<int:visit_card_id>/complete", methods=["POST"])
def api_complete_card(visit_id, visit_card_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE visit_cards SET status='done', completed_at=? WHERE id=? AND visit_id=?", (now, visit_card_id, visit_id))
    conn.commit()
    conn.close()
    return jsonify({"status":"ok","completed_at":now})



################## testing ##################


@app.route("/periodic/test_create")
def periodic_test_create():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # insert a periodic_visits
    c.execute("INSERT INTO periodic_visits (aircraft, start_date, status) VALUES (?, ?, ?)",
              ("C-130H-TEST-001", now, "ongoing"))
    visit_id = c.lastrowid
    # pick up to 6 jobcards
    c.execute("SELECT id FROM jobcards LIMIT 6")
    rows = c.fetchall()
    seq = 1
    for r in rows:
        jid = r[0]
        c.execute("""INSERT INTO visit_cards (visit_id, card_id, status, sequence) VALUES (?, ?, ?, ?)""",
                  (visit_id, jid, "pending", seq))
        seq += 1
    conn.commit()
    conn.close()
    flash("Sample periodic visit created.", "success")
    return redirect(url_for("dashboard"))

##################################################3

@app.route("/aircrafts")
def list_aircrafts():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, matriculation, type, base, notes FROM aircrafts ORDER BY matriculation")
    aircrafts = c.fetchall()
    conn.close()
    return render_template("aircrafts.html", aircrafts=aircrafts)


@app.route("/aircrafts/new", methods=["GET", "POST"])
def new_aircraft():
    if request.method == "POST":
        matriculation = request.form.get("matriculation")
        typ = request.form.get("type")
        base = request.form.get("base")
        notes = request.form.get("notes")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO aircrafts (matriculation, type, base, notes) VALUES (?, ?, ?, ?)",
                  (matriculation, typ, base, notes))
        conn.commit()
        conn.close()
        flash("Aircraft added.", "success")
        return redirect(url_for("list_aircrafts"))
    return render_template("aircraft_form.html", aircraft=None)


@app.route("/aircrafts/edit/<int:aircraft_id>", methods=["GET", "POST"])
def edit_aircraft(aircraft_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if request.method == "POST":
        matriculation = request.form.get("matriculation")
        typ = request.form.get("type")
        base = request.form.get("base")
        notes = request.form.get("notes")
        c.execute("UPDATE aircrafts SET matriculation=?, type=?, base=?, notes=? WHERE id=?",
                  (matriculation, typ, base, notes, aircraft_id))
        conn.commit()
        conn.close()
        flash("Aircraft updated.", "success")
        return redirect(url_for("list_aircrafts"))

    c.execute("SELECT id, matriculation, type, base, notes FROM aircrafts WHERE id=?", (aircraft_id,))
    aircraft = c.fetchone()
    conn.close()
    return render_template("aircraft_form.html", aircraft=aircraft)


@app.route("/aircrafts/delete/<int:aircraft_id>", methods=["POST"])
def delete_aircraft(aircraft_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM aircrafts WHERE id=?", (aircraft_id,))
    conn.commit()
    conn.close()
    flash("Aircraft deleted.", "success")
    return redirect(url_for("list_aircrafts"))




@app.route("/api/progress", methods=["POST"])
def api_progress():
    data = request.get_json()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO card_progress (visit_id, card_id, paragraph, step, substep,
                                   technician, rank, status, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("visit_id"),
        data.get("card_id"),
        data.get("paragraph"),
        data.get("step"),
        data.get("substep"),
        data.get("technician"),
        data.get("rank"),
        data.get("status"),
        data.get("reason")
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --------- Create VP route (always attaches selected cards) ----------
@app.route("/vp/new", methods=["GET", "POST"])
def new_vp():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # fetch aircraft for dropdown
    try:
        c.execute("SELECT id, matriculation FROM aircrafts ORDER BY matriculation")
        aircrafts = c.fetchall()
    except Exception:
        aircrafts = []

    # fetch jobcards
    c.execute("SELECT id, filename, card_no, parsed_json FROM jobcards ORDER BY filename")
    jobcards = c.fetchall()

    if request.method == "POST":
        aircraft_select = request.form.get("aircraft_select")
        aircraft_new = request.form.get("aircraft_new", "").strip()
        if aircraft_select:
            # get matriculation text
            c.execute("SELECT matriculation FROM aircrafts WHERE id=?", (aircraft_select,))
            row = c.fetchone()
            aircraft_text = row[0] if row else aircraft_new or "UNKNOWN"
        else:
            aircraft_text = aircraft_new or "UNKNOWN"

        vp_type = request.form.get("vp_type", "General")
        start_date = request.form.get("start_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        end_date = request.form.get("end_date") or None

        # Insert the visit (legacy 'aircraft' text kept)
        c.execute("""
            INSERT INTO periodic_visits (aircraft, start_date, end_date, status, vp_type)
            VALUES (?, ?, ?, ?, ?)
        """, (aircraft_text, start_date, end_date, "ongoing", vp_type))
        visit_id = c.lastrowid

        # Attach selected cards (checkboxes named card_ids)
        card_ids = request.form.getlist("card_ids")
        seq = 1
        for cid in card_ids:
            # optional estimated hours per card
            est_val = request.form.get(f"est_{cid}")
            try:
                est_hours = float(est_val) if est_val not in (None, "") else None
            except:
                est_hours = None
            c.execute("""
                INSERT INTO visit_cards (visit_id, card_id, status, sequence, estimated_hours)
                VALUES (?, ?, ?, ?, ?)
            """, (visit_id, cid, "pending", seq, est_hours))
            seq += 1

            # Also: if parsed_json contains paragraphs we may want to create initial entries in paragraph_status
            # but leaving on-demand when technician marks done/interrupt is fine

        conn.commit()
        conn.close()
        flash("Periodic Visit created and job cards attached.", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    today = date.today().isoformat()
    return render_template("new_vp.html", aircrafts=aircrafts, jobcards=jobcards, today=today)


# --------- Delete visit API (DELETE) ----------
@app.route("/api/visit/<int:visit_id>/delete", methods=["DELETE"])
def api_delete_visit(visit_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # delete paragraph_status entries
    c.execute("DELETE FROM paragraph_status WHERE visit_card_id IN (SELECT id FROM visit_cards WHERE visit_id=?)", (visit_id,))
    # delete visit_cards
    c.execute("DELETE FROM visit_cards WHERE visit_id=?", (visit_id,))
    # delete visit record
    c.execute("DELETE FROM periodic_visits WHERE id=?", (visit_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --------- Paragraph done endpoint (ensure exists) ----------
@app.route("/api/visit/<int:visit_id>/card/<int:visit_card_id>/paragraph/done", methods=["POST"])
def api_paragraph_done(visit_id, visit_card_id):
    payload = request.json or request.form
    paragraph_index = int(payload.get("paragraph_index", -1))
    step_index = payload.get("step_index")
    try:
        step_index = int(step_index) if step_index not in (None, "") else None
    except:
        step_index = None
    tech_name = payload.get("technician_name", "unknown")
    tech_rank = payload.get("technician_rank", "")
    notes = payload.get("notes", "")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # find card_id
    c.execute("SELECT card_id FROM visit_cards WHERE id=? AND visit_id=?", (visit_card_id, visit_id))
    row = c.fetchone()
    paragraph_text = None
    step_text = None
    if row:
        card_id = row[0]
        c.execute("SELECT parsed_json FROM jobcards WHERE id=?", (card_id,))
        pj = c.fetchone()
        if pj and pj[0]:
            import ast, json
            try:
                job_data = ast.literal_eval(pj[0])
            except Exception:
                try:
                    job_data = json.loads(pj[0])
                except Exception:
                    job_data = []
            if 0 <= paragraph_index < len(job_data):
                paragraph_text = job_data[paragraph_index].get("paragraph")
                if step_index is not None:
                    steps = job_data[paragraph_index].get("steps", [])
                    if 0 <= step_index < len(steps):
                        step_text = steps[step_index]
    # insert status
    c.execute("""
        INSERT INTO paragraph_status (visit_card_id, paragraph_index, paragraph_text, step_index, step_text,
                                      technician_name, technician_rank, status, notes)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (visit_card_id, paragraph_index, paragraph_text, step_index, step_text, tech_name, tech_rank, "done", notes))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# --------- Paragraph interruption endpoint (ensure exists) ----------
@app.route("/api/visit/<int:visit_id>/card/<int:visit_card_id>/paragraph/interruption", methods=["POST"])
def api_paragraph_interrupt(visit_id, visit_card_id):
    payload = request.json or request.form
    paragraph_index = int(payload.get("paragraph_index", -1))
    step_index = payload.get("step_index")
    try:
        step_index = int(step_index) if step_index not in (None, "") else None
    except:
        step_index = None
    tech_name = payload.get("technician_name", "unknown")
    tech_rank = payload.get("technician_rank", "")
    interruption_type = payload.get("interruption_type", "other")
    interruption_reason = payload.get("interruption_reason", "")
    notes = payload.get("notes", "")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # fetch paragraph/step text
    c.execute("SELECT card_id FROM visit_cards WHERE id=? AND visit_id=?", (visit_card_id, visit_id))
    row = c.fetchone()
    paragraph_text = None
    step_text = None
    if row:
        card_id = row[0]
        c.execute("SELECT parsed_json FROM jobcards WHERE id=?", (card_id,))
        pj = c.fetchone()
        if pj and pj[0]:
            import ast, json
            try:
                job_data = ast.literal_eval(pj[0])
            except Exception:
                try:
                    job_data = json.loads(pj[0])
                except Exception:
                    job_data = []
            if 0 <= paragraph_index < len(job_data):
                paragraph_text = job_data[paragraph_index].get("paragraph")
                if step_index is not None:
                    steps = job_data[paragraph_index].get("steps", [])
                    if 0 <= step_index < len(steps):
                        step_text = steps[step_index]
    # record interruption
    c.execute("""
        INSERT INTO paragraph_status (visit_card_id, paragraph_index, paragraph_text, step_index, step_text,
                                      technician_name, technician_rank, status, interruption_reason, interruption_type, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (visit_card_id, paragraph_index, paragraph_text, step_index, step_text, tech_name, tech_rank, "interrupted", interruption_reason, interruption_type, notes))
    # if material interruption mark suspended
    if interruption_type == 'material':
        c.execute("UPDATE visit_cards SET suspended=1, suspended_reason=? WHERE id=?", (interruption_reason, visit_card_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})



if __name__ == "__main__":
    app.run(debug=True)
