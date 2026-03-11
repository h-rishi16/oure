import sqlite3
from datetime import datetime, timezone, timedelta

db_path = "/Users/hrishi/.oure/cache.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Insert mock history data for 25544 vs 43205
primary = "25544"
secondary = "43205"
tca = datetime.now(timezone.utc) + timedelta(days=2)

for i in range(10, 0, -1):
    eval_time = datetime.now(timezone.utc) - timedelta(hours=i)
    # Pc goes from high to low (or fluctuating)
    pc = 1e-4 * (i / 5.0)
    miss_dist = 0.5 + (i * 0.1)
    
    warning_level = "GREEN"
    if pc >= 1e-3:
        warning_level = "RED"
    elif pc >= 1e-5:
        warning_level = "YELLOW"
        
    cursor.execute("""
        INSERT INTO risk_history (primary_id, secondary_id, evaluation_time, tca, pc, miss_distance_km, warning_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (primary, secondary, eval_time.isoformat(), tca.isoformat(), pc, miss_dist, warning_level))

conn.commit()
conn.close()
print("Mock history injected.")
