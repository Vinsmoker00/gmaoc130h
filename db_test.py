import sqlite3
conn = sqlite3.connect("jobcards.db")
print(conn.execute("PRAGMA table_info(periodic_visits)").fetchall())
conn.close()