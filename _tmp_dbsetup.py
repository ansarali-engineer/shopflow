import pymysql

def try_connect(label, **kw):
    try:
        c = pymysql.connect(host="127.0.0.1", port=3306,
                             user="shopflow_user", password="StrongPass123!",
                             charset="utf8mb4", **kw)
        print(f"{label}: AUTH OK -> connected")
        c.close()
    except pymysql.err.OperationalError as e:
        print(f"{label}: {e.args[0]} {e.args[1]}")

try_connect("no db")
try_connect("db=shopflow", db="shopflow")
try_connect("db=shopflow + init_command",
            db="shopflow",
            init_command="SET sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1")
try_connect("db=mysql (system db that exists)", db="mysql")
