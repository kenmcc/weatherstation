import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("weather.db")
c = conn.cursor()
nodes = c.execute('''select distinct node from data''').fetchall()
errorConditions = []
now = datetime.now()
for n in nodes:
  node = n[0]
  sql = "SELECT date, batt from data where node=='{0}' order by date desc limit 1".format(node)
  data = c.execute(sql).fetchone()
  lastComms = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")
  batt = float(data[1])
  if lastComms < now-timedelta(minutes=15):
    errorConditions.append("Lost comms with node {0} since {1}".format(node, lastComms))
  if batt < float(2.9):
    errorConditions.append("Battery in node {0} is low: {1}".format(node, batt))

print ",".join(errorConditions)
