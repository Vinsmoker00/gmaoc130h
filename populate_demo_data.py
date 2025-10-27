"""
populate_demo_data.py

Usage:
    python populate_demo_data.py

This script populates jobcards.db (in the current folder) with:
 - jobcards (sample set from SMP 515 list)
 - materials (sample PN rows from SMP 883)
 - jobcard_materials links (random 1-3 materials per card)
 - workshops (if not present)
 - workshop_tasks (some sample assignments)
 - aircrafts (sample aircraft)
 - periodic_visits (sample ongoing VPs for A/B/C types)
 - visit_cards (cards attached to each VP)

Run it once. It will NOT delete existing data (safe inserts).
"""

import os, random, sqlite3, time
from datetime import datetime

DB_FILE = "jobcards.db"

# --- sample data (pulled/derived from SMP 515 / SMP 883 snippets you uploaded) ---
SMP_A_CARDS = [
    "A-16","A-17","A-18","A-19","A-20","A-21","A-22","A-23","A-24","A-25","A-26","A-27","A-28","A-29","A-30","A-31","A-32"
]
SMP_B_CARDS = [
    "B-1","B-2","B-3","B-4","B-5","B-6","B-7","B-8","B-9","B-10","B-11","B-12-01","B-17","B-18","B-19","B-20","B-21"
]
SMP_C_CARDS = [
    "C-1","C-2","C-4","C-5","C-6","C-7","C-8","C-9","C-10","C-11","C-12","C-14","C-15","C-20"
]

# example materials (PNs sampled from SMP 883 snippets). Add more by parsing SMP_883 later.
SAMPLE_MATERIALS = [
    {"part_number":"99-2868-001-101","designation":"Bolt assembly 99-2868-001-101","category":"Rechange","stock":10},
    {"part_number":"99-2868-002-103","designation":"Bearing 99-2868-002-103","category":"Reparable","stock":4},
    {"part_number":"99-2720-006-101","designation":"Seal 99-2720-006-101","category":"Rechange","stock":12},
    {"part_number":"990-2230-003","designation":"Nut 990-2230-003","category":"Rechange","stock":50},
    {"part_number":"998-3870-508","designation":"Gasket 998-3870-508","category":"Rechange","stock":8},
    {"part_number":"99836","designation":"Washer 99836","category":"Rechange","stock":200},
    {"part_number":"99-2720-004-101","designation":"Clip 99-2720-004-101","category":"Outillage","stock":5},
    {"part_number":"99-2720-006-103","designation":"Pin 99-2720-006-103","category":"Reparable","stock":3},
]

DEFAULT_WORKSHOPS = ['MOTEUR', 'EQT/BORD', 'RADIO', 'APG', 'HELICE', 'FUEL', 'CHAUD', 'MARS', 'S/S', 'DRS', 'NDI']

SAMPLE_AIRCRAFT = [
    {"matriculation":"C-130H-001","type":"C-130H","base":"Base A"},
    {"matriculation":"C-130H-002","type":"C-130H","base":"Base B"},
    {"matriculation":"C-130H-003","type":"C-130H","base":"Base C"},
]

def connect():
    if not os.path.exists(DB_FILE):
        raise RuntimeError(f"Database {DB_FILE} not found. Run your app once to create it.")
    return sqlite3.connect(DB_FILE)

def insert_jobcards(conn, card_list, prefix_label):
    c = conn.cursor()
    inserted = []
    for card_no in card_list:
        # create a filename-like label and minimal parsed_json placeholder (you will replace with real parsed JSON later)
        filename = f"{card_no}.pdf"
        parsed_json = str([{"paragraph": f"Paragraph 1 of {card_no}", "steps": ["A.","B."]}])
        try:
            c.execute("INSERT OR IGNORE INTO jobcards (filename, card_no, parsed_json) VALUES (?, ?, ?)",
                      (filename, card_no, parsed_json))
            conn.commit()
        except Exception as e:
            print("jobcard insert error", e)
        # fetch id
        c.execute("SELECT id FROM jobcards WHERE filename=?", (filename,))
        row = c.fetchone()
        if row:
            inserted.append((row[0], card_no, filename))
    return inserted

def insert_materials(conn):
    c = conn.cursor()
    inserted = []
    for m in SAMPLE_MATERIALS:
        # use serial_number as None to allow multiple items later
        try:
            c.execute("""
                INSERT OR IGNORE INTO materials (part_number, serial_number, designation, category, stock)
                VALUES (?, ?, ?, ?, ?)
            """, (m["part_number"], None, m["designation"], m["category"], m["stock"]))
            conn.commit()
        except Exception as e:
            print("material insert error", e)
        c.execute("SELECT id FROM materials WHERE part_number=?", (m["part_number"],))
        row = c.fetchone()
        if row:
            inserted.append((row[0], m["part_number"]))
    return inserted

def insert_workshops(conn):
    c = conn.cursor()
    for w in DEFAULT_WORKSHOPS:
        c.execute("INSERT OR IGNORE INTO workshops (name) VALUES (?)", (w,))
    conn.commit()
    # return list
    c.execute("SELECT id, name FROM workshops")
    return c.fetchall()

def insert_aircrafts(conn):
    c = conn.cursor()
    inserted = []
    for a in SAMPLE_AIRCRAFT:
        c.execute("INSERT OR IGNORE INTO aircrafts (matriculation, type, base) VALUES (?, ?, ?)",
                  (a["matriculation"], a["type"], a["base"]))
    conn.commit()
    c.execute("SELECT id, matriculation FROM aircrafts")
    return c.fetchall()

def create_visit(conn, aircraft_text, vp_type, selected_card_ids):
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO periodic_visits (aircraft, start_date, status, vp_type) VALUES (?, ?, ?, ?)",
              (aircraft_text, now, "ongoing", vp_type))
    visit_id = c.lastrowid
    # attach cards with sequence order
    seq = 1
    for cid in selected_card_ids:
        c.execute("INSERT INTO visit_cards (visit_id, card_id, status, sequence) VALUES (?, ?, ?, ?)",
                  (visit_id, cid, "pending", seq))
        seq += 1
    conn.commit()
    return visit_id

def link_jobcards_to_materials(conn, jobcard_rows, material_rows):
    """
    Simple random linking: assign 1-3 materials per jobcard.
    """
    c = conn.cursor()
    mat_ids = [m[0] for m in material_rows]
    for jc in jobcard_rows:
        jobcard_id = jc[0]
        picks = random.sample(mat_ids, k=random.randint(1, min(3, len(mat_ids))))
        for mid in picks:
            c.execute("INSERT INTO jobcard_materials (jobcard_id, material_id) VALUES (?, ?)", (jobcard_id, mid))
    conn.commit()

def create_sample_workshop_tasks(conn, jobcard_rows, workshop_rows):
    c = conn.cursor()
    # assign a random workshop to each jobcard at card level
    for jc in jobcard_rows:
        jobcard_id = jc[0]
        w = random.choice(workshop_rows)
        wid = w[0]
        # create a card-level task
        c.execute("""
            INSERT INTO workshop_tasks (workshop_id, card_id, paragraph, step, substep, assignment_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (wid, jobcard_id, None, None, None, 'card'))
    conn.commit()

def main():
    conn = connect()
    print("Connected to", DB_FILE)

    # 1) ensure workshops exist
    workshops = insert_workshops(conn)
    print(f"Workshops present: {len(workshops)}")

    # 2) insert materials
    material_rows = insert_materials(conn)
    print(f"Materials inserted: {len(material_rows)}")

    # 3) insert jobcards A/B/C
    inserted_a = insert_jobcards(conn, SMP_A_CARDS, 'A')
    inserted_b = insert_jobcards(conn, SMP_B_CARDS, 'B')
    inserted_c = insert_jobcards(conn, SMP_C_CARDS, 'C')
    total_cards = inserted_a + inserted_b + inserted_c
    print(f"Jobcards inserted/found: {len(total_cards)}")

    # 4) link jobcards <-> materials
    link_jobcards_to_materials(conn, total_cards, material_rows)
    print("Linked jobcards to materials.")

    # 5) create some workshop_tasks
    create_sample_workshop_tasks(conn, total_cards, workshops)
    print("Created sample workshop task links.")

    # 6) aircrafts
    a_rows = insert_aircrafts(conn)
    print(f"Aircrafts inserted/found: {len(a_rows)}")

    # 7) create demo periodic visits (VPs) for A, B, C types
    # mapping rule: A -> jobcards starting with A-, etc.
    c = conn.cursor()
    # fetch ids for each prefix
    def ids_by_prefix(prefix):
        c.execute("SELECT id FROM jobcards WHERE card_no LIKE ? ORDER BY id", (f"{prefix}%",))
        return [r[0] for r in c.fetchall()]

    a_ids = ids_by_prefix('A-')
    b_ids = ids_by_prefix('B-')
    c_ids = ids_by_prefix('C-')

    # create one VP per aircraft: A for first, B for second, C for third (if available)
    created_visits = []
    if len(a_rows) >= 1:
        v1 = create_visit(conn, a_rows[0][1], 'A', a_ids[:8])  # attach first 8 A cards
        created_visits.append(v1)
    if len(a_rows) >= 2:
        v2 = create_visit(conn, a_rows[1][1], 'B', b_ids[:8])  # attach first 8 B cards
        created_visits.append(v2)
    if len(a_rows) >= 3:
        v3 = create_visit(conn, a_rows[2][1], 'C', c_ids[:8])  # attach first 8 C cards
        created_visits.append(v3)

    print("Created visits:", created_visits)
    print("Demo data population finished.")

    conn.close()

if __name__ == "__main__":
    main()
