import sqlite3

con = sqlite3.connect("shadowops.db")
tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in shadowops.db:", tables)
con.close()
