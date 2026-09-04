import sqlite3
con=sqlite3.connect('./aicouncil.db')
cur=con.cursor()
cur.execute('select name from sqlite_master where type="table"')
print(cur.fetchall())
cur.execute('select count(*) from users')
print("users count", cur.fetchone())
con.close()
