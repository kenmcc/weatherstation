# -*- coding: iso-8859-1 -*-
import sqlite3

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.dates as md
from pylab import *
from datetime import datetime, timedelta, time, date
import sys
from WeatherStation import dew_point, apparent_temp

nodes = {"2": "Outside", "10": "Kitchen", "21": "Bedroom"}

conn = sqlite3.connect("weather.db", detect_types=sqlite3.PARSE_COLNAMES|sqlite3.PARSE_DECLTYPES)
c = conn.cursor()

sql = "SELECT min(date), max(date) from data"
result =  c.execute(sql).fetchone()
lowest = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
highest = datetime.strptime(result[1], "%Y-%m-%d %H:%M:%S")



now = datetime.now() - timedelta(minutes = datetime.now().time().minute %5)
alldata = []


def getLiveData(start):
    sql = "SELECT * FROM data WHERE date < '{0}' GROUP BY node ORDER BY date DESC".format(str(start))
    return c.execute(sql)    
     
def mungeData(data, start):
    names = list(map(lambda x: x[0], data.description))
    summary = {}
    summary["date"] = start
    summary["temp"] = {}
    summary["battery"] = {}
    dataPresent = False
    for row in data.fetchall():
        node = row[names.index("node")]
        nodename = nodes[str(node)]
        dataPresent = True
        # we always have the battery indicator
        batt = row[names.index("batt")]
        summary["battery"][nodename] = batt
        
        if node != 3: # we always have temp, except for rain and wind.
            temp = row[names.index("temp")]
            summary["temp"][nodename] = temp
            
        if node == 2:
            # we also have  pressure, humidity
            for f in ["pressure", "humidity"]:
                summary[f] = row[names.index(f)]
        elif node >= 10 and node < 20:
            pass
        elif node == 21:
            # we also have the switch
            for f in ["switch"]:
                summary[f] = row[names.index(f)]
    
    if dataPresent:
	if "humidity" in summary and  "Outside" in summary["temp"]:
            dp = dew_point(summary["temp"]["Outside"], summary["humidity"])
            summary["dew_point"] = dp
            if "wind" in summary:
               ap_temp = apparent_temp(summary["temp"]["Outside"], summary["humidity"], summary["wind"])
               summary["feels_like"] = ap_temp
            else:
               ap_temp = apparent_temp(summary["temp"]["Outside"], summary["humidity"], 0)
               summary["feels_like"] = ap_temp

        alldata.append(summary)
    
    

def recent(start, span, spacingMins, outfile, title):
    global alldata
    alldata = []
    #start = now
    end = start - timedelta(minutes=spacingMins)
    finish = start - timedelta(minutes = span)
    fields = ["date", "node", "batt", "temp", "humidity", "wind_dir", "wind_avg", "wind_gust", "rain", "pressure", "switch"] 
    while(end >= finish):
        data = getLiveData(start)
        mungeData(data,start)
        start = end
        end = start - timedelta(minutes=spacingMins)
    
def livetweet(start, span, spacing, outfile):
    global alldata
    alldata = []
    data = getLiveData(start)
    mungeData(data, start)
    alldata = alldata[0]
    print alldata
    d = now - timedelta(seconds=now.second)
    d=d.strftime("%H:%M")

    with open(outfile, "w") as f:
	f.write("{0}: Temp:{1}oC; DP:{4}%; Humidity:{2}%; Pressure:{3}".format(d, alldata["temp"]["Outside"], alldata["humidity"], alldata["pressure"], alldata["dew_point"]))

 


def outputRecent(filename, title):
    with open(filename, "w") as f:
        f.write("<h3> {0}</h3>".format(title) + "\n")
        f.write('<table border="1" rules="rows" cellspacing="0" cellpadding="5"> ' + "\n")
        f.write('<col />' + "\n")
        f.write('<col /> ' + "\n")
        f.write('<col align="char" char="." /> ' + "\n")
        f.write('<col align="char" char="." /> ' + "\n")
        f.write('<col /> ' + "\n")
        f.write('<col /> ' + "\n")
        f.write('<col align="char" char="m" /> ' + "\n")
        f.write('<col align="char" char="m" /> ' + "\n")
        f.write('<col align="char" char="." /> ' + "\n")
        f.write('<col align="char" char="," />' + "\n")
        
        f.write('<tr>' + "\n")
        f.write('<th rowspan="2">Time</th>' + "\n")
        f.write('<th colspan="{0}">Temp <small>(&deg;C)</small></th>'.format(2 + len(nodes)) + "\n")
        f.write('<th colspan="1">Humidity <small>(%)</small></th>' + "\n")
        f.write('<th colspan="3">Wind <small>(km/h)</small></th>' + "\n")
        f.write('<th rowspan="2">Rain <small>(mm)</small></th>' + "\n")
        f.write('<th rowspan="2">Pressure <small>(hPa)</small></th>' + "\n")
        f.write('</tr>' + "\n")
        
        f.write('<tr>' + "\n")
        for n in sorted(nodes):
            f.write('<th>{0}</th>'.format(nodes[n]) + "\n")
        f.write('<th>DP</th>' + "\n")
        f.write('<th>Feels Like</th>' + "\n")
        f.write('<th>Outside</th>' + "\n")
        f.write('<th>dir</th>' + "\n")
        f.write('<th>ave</th>' + "\n")
        f.write('<th>gust</th>' + "\n")
        f.write('</tr>' + "\n")
        
        for row in alldata:
            f.write('<tr>' + "\n")
            timestamp = row["date"].strftime("%H:%M")
            f.write('<td>'+str(timestamp) + "</td>\n")
            for n in sorted(nodes):
                if nodes[n] in row["temp"]:
                    f.write('<th>{:.1f}</th>'.format(row["temp"][nodes[n]]) + "\n")
                else:
                    f.write('<th> </th>' + "\n")
            f.write('<th>{:.1f}</th>'.format(row["dew_point"]) + "\n")
            f.write('<th>{:.1f}</th>'.format(row["feels_like"]) + "\n")

            try:
                f.write('<th>{:.1f}</th>'.format(row["humidity"]) + "\n")
            except:
                f.write('<th></th>' + "\n")
            
            for entry in [["wind_dir", "-"], ["wind_avg", 0], ["wind_gust", 0], ["rain", 0], ["pressure", 999.0]]:
                try:
                    if entry[0] in row:
                        f.write('<th>{0}</th>'.format(row[entry[0]]) + "\n")
                    else:
                        f.write('<th></th>' + "\n")
                except Exception, e:
                    f.write('<th></th>' + "\n")

            f.write('</tr>' + "\n")
            
        f.write('</table>' + "\n")
        
def last24hours(now, filename, title):
    today = now.date()
    todayTime = now.time()
    yesterday = today-timedelta(days=1)
    fullstart = None
    fullend = None
    partstart = None
    partend = now
    if todayTime.hour < 21:
        daybefore = yesterday-timedelta(days=1)
        fullstart = datetime.combine(daybefore, time(21, 00))
    else:
        fullstart = datetime.combine(yesterday, time(21,00))
    fullend = fullstart + timedelta(days=1)
    partstart = fullend
    
    fulldayStart = fullstart + timedelta(hours=12)
    partdayStart = partstart + timedelta(hours = 12)           


    with open(filename, "w") as f:
        f.write("<center><h3> {0}</h3></center>".format(title) + "\n")
        f.write('<table border="1" rules="rows" cellspacing="0" cellpadding="5"> ' + "\n")
        f.write('<tr>' + "\n")
        f.write('<th colspan="2" class="left">' + "\n")
        
        f.write('24 hour period ending 21:00 on {0}'.format(fullend.date().strftime("%A, %d %B %Y")) + "\n")
        f.write('</th>' + "\n")
        f.write('<th colspan="2">Date &amp; time</th>' + "\n")
        f.write('</tr>' + "\n")

        # do the full day so first.
        for x in [["min(temp), date, node", fullstart, fulldayStart, "Night Min Temp", "&deg;C"],
                  ["max(temp), date, node", fullstart, fulldayStart, "Night Max Temp", "&deg;C"],
                  ["min(temp), date, node", fulldayStart, fullend,   "Day Min Temp", "&deg;C"],
                  ["max(temp), date", fulldayStart, fullend,   "Day Max Temp", "&deg;C"],
                  ["sum(rain)", fullstart, fullend,            "Total Rainfall","mm"],
                  ["avg(wind_avg)", fullstart, fullend,        "Avg Wind Speed", "km/h"],
                  ["max(wind_gust), date", fullstart, fullend, "Highest Gust Speed", "km/h"]
            ]:
            sql = "SELECT {0} from data where date >= '{1}' and date < '{2}' and node < 10".format(x[0], x[1], x[2])
            result  =  c.execute(sql).fetchone()
            res = result[0]
            instant = None
            if len(result) > 1 and result[1] is not None:
                instant = datetime.strptime(result[1], "%Y-%m-%d %H:%S:%M")

            f.write('<tr>' + "\n")
            f.write('<th align="right">{0}</th>'.format(x[3]) + "\n")
            f.write('<td>{0}<small>{1}</small></td>'.format(res, x[4]) + "\n")
            try:
              f.write('<td>{0}</td><td>{1}</td>'.format(instant.date(), instant.time()) + "\n")
            except:
              f.write('<td></td><td></td>' + "\n")  
            f.write('</tr>' + "\n")
        f.write('<tr><th colspan="4">&nbsp;</th></tr>  <tr>' + "\n")
        f.write('<th colspan="2" class="left">' + "\n")
        f.write('From 21:00 on {0} to {1}'.format(fullend.date().strftime("%d %b"), partend.strftime("%H:%M on %A, %d %B %Y")) + "\n")
        f.write('<th colspan="2">Date &amp; time</th>' + "\n")
        f.write('</tr>' + "\n")

        for x in [["min(temp), date, node", partstart, partdayStart, "Night Min Temp", "&deg;C"],
                  ["max(temp), date, node", partstart, partdayStart, "Night Max Temp", "&deg;C"],
                  ["min(temp), date", partdayStart, partend,   "Day Min Temp", "&deg;C"],
                  ["max(temp), date", partdayStart, partend,   "Day Max Temp", "&deg;C"],
                  ["sum(rain)", partstart, partend,            "Total Rainfall","mm"],
                  ["avg(wind_avg)", partstart, partend,        "Avg Wind Speed", "km/h"],
                  ["max(wind_gust), date", partstart, partend, "Highest Gust Speed", "km/h"]
            ]:
            sql = "SELECT {0} from data where date >= '{1}' and date < '{2}' and node < 10".format(x[0], x[1], x[2])
            result =  c.execute(sql).fetchone()
            #print sql, " = ", result
            
            res = result[0]
            if res is None:
                res = ""
            instant = None
            if len(result) > 1 and result[1] is not None:
                instant = datetime.strptime(result[1], "%Y-%m-%d %H:%S:%M")
            
            f.write('<tr>' + "\n")
            f.write('<th align="right">{0}</th>'.format(x[3]) + "\n")
            f.write('<td>{0}<small>{1}</small></td>'.format(res, x[4]) + "\n")
            try:
                f.write('<td>{0}</td><td>{1}</td>'.format(instant.date(), instant.time()) + "\n")
            except Exception, e:
              f.write('<td></td><td></td>' + "\n")  
            f.write('</tr>' + "\n")
        f.write("</table>\n")
        
        
def last7days(now, filename, title):
    today = now.date()
    todayTime = now.time()
    
    with open(filename, "w") as f:
        f.write("<center><h3> {0}</h3></center>".format(title) + "\n")
        f.write('<table border="1" rules="rows" cellspacing="0" cellpadding="3" style="line-height:20px;"> ' + "\n")
        f.write('<tr>' + "\n")
        f.write('<th rowspan="2">24 hour period ending</th>' + "\n")
        f.write('<th colspan="2">Temperature <small>&deg;C</small></th>' + "\n")
        f.write('<th colspan="1">Rain <small>mm</small></th>' + "\n")
        f.write('<th colspan="2">Wind <small>km/h</small></th>' + "\n")
        f.write('<th colspan="2">Humidity <small>%</small></th>' + "\n")
        f.write('<th colspan="2">Pressure <small>hPa</small></th>' + "\n")
        f.write('</tr>' + "\n")
        
        f.write('<tr>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('<th>Total</th>' + "\n")
        f.write('<th>Avg</th>' + "\n")
        f.write('<th>Max Gust</th>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('</tr>' + "\n")
        

        for x in range(1,7):
            start = datetime.combine(today-timedelta(days=x+1), time(21,00))
            startday = start + timedelta(hours=12)
            end = datetime.combine(today-timedelta(days=x), time(21,00))
            data = []
            realDataCount = 0
            for x in [["min(temp)", start, end,         "Min Temp", "&deg;C", "(select temp, date, node from data where temp between -30 and 35)"],
                      ["max(temp)", start, end,         "Max Temp", "&deg;C", "(select temp, date, node from data where temp between -30 and 35)"],
                      ["sum(rain)", start, end,         "Total Rainfall","mm", "(select rain, date, node from data where rain between 0 and 1)"],
                      ["avg(wind_avg)", start, end,     "Avg Wind Speed", "km/h", "(select wind_avg, date, node from data where wind_avg between 0 and 120)"],
                      ["max(wind_gust)", start, end,    "Highest Gust Speed", "km/h", "(select wind_gust, date, node from data where wind_gust between 0 and 120)"],
                      ["min(humidity)" , start, end,    "Lowest Humidity", "%", "(select humidity, date, node from data where humidity between 10 and 100)"],
                      ["max(humidity)" , start, end,    "Highest Humidity", "%", "(select humidity, date, node from data where humidity between 10 and 100)"],
                      ["min(pressure)" , start, end,    "Lowest Pressure", "hPa", "(select pressure, date, node from data where pressure between 950 and 1100)"],
                      ["max(pressure)" , start, end,    "Highest Pressure", "hPa", "(select pressure, date, node from data where pressure between 950 and 1100)"],
                ]:
                sql = "SELECT {0} from {3} where date >= '{1}' and date < '{2}' and node < 10 ".format(x[0], x[1], x[2], x[5])
                result =  c.execute(sql).fetchone()
                if result[0] is None or result[0] == " ": 
                    data.append("")
                else:
                    data.append(result[0])
                    realDataCount += 1
            if realDataCount > 0:
                f.write('<tr><td>{}</td><td>'.format(end))
                f.write("</td><td>".join(str(x) for x in data))
                f.write('</td></tr>')
                    
        f.write("</table>\n")       
        
def addMonth(thisMonth, months=1):
    y = thisMonth.year
    m = thisMonth.month + months
    if m > 12:
        m = 1
        y += 1
    return date(y, m, 1)
    
def subMonth(thisMonth, months = 1):
    y = thisMonth.year
    m = thisMonth.month - months
    if m < 0:
        m = 12
        y -= 1
    return date(y, m, 1)
        
def historic(now, filename, title):
    today = now.date()
    todayTime = now.time()
    
    low = date(lowest.year, lowest.month, 1)
    high = date(highest.year, highest.month, 1)
    start = high
    end = addMonth(start)
 
    
    with open(filename, "w") as f:
        f.write("<center><h3> {0}</h3></center>".format(title) + "\n")
        f.write("<center><h3> {0}</h3></center>".format("Monthly") + "\n")
        f.write('<table border="1" rules="rows" cellspacing="0" cellpadding="3" style="line-height:20px;"> ' + "\n")
        f.write('<tr>' + "\n")
        f.write('<th rowspan="2">Month</th>' + "\n")
        f.write('<th colspan="2">Temperature <small>&deg;C</small></th>' + "\n")
        f.write('<th colspan="1">Rain <small>mm</small></th>' + "\n")
        f.write('<th colspan="2">Wind <small>km/h</small></th>' + "\n")
        f.write('<th colspan="2">Humidity <small>%</small></th>' + "\n")
        f.write('<th colspan="2">Pressure <small>hPa</small></th>' + "\n")
        f.write('</tr>' + "\n")
        
        f.write('<tr>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('<th>Total</th>' + "\n")
        f.write('<th>Avg</th>' + "\n")
        f.write('<th>Max Gust</th>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('</tr>' + "\n")
        

        while start >= low:
            data = []
            realDataCount = 0
            for x in [["temp, date", start, end,         "Min Temp", "&deg;C", "(select date, temp from data where temp == (select min(temp) from data where node < 10 and temp between -30 and 35))"],
                  ["temp, date", start, end,         "Max Temp", "&deg;C", "(select date, temp from data where temp == (select max(temp) from data where node < 10 and temp between -30 and 35))"],
                  ["sum(rain), date", start, end,         "Total Rainfall","mm", "(select rain, date from data where rain between 0 and 1 and node < 10)"],
                  ["avg(wind_avg), date", start, end,     "Avg Wind Speed", "km/h", "(select wind_avg, date from data where wind_avg between 0 and 120 and node < 10 and wind_avg between 0 and 120)"],
                  ["wind_gust, date", start, end,    "Highest Gust Speed", "km/h", "(select wind_gust, date from data where wind_gust == (select min(wind_gust) from data where node < 10 and wind_avg between 0 and 120))"],
                  ["humidity, date" , start, end,    "Lowest Humidity", "%", "(select humidity, date from data where humidity == (select min(humidity) from data where node < 10 and humidity between 10 and 100))"],
                  ["humidity, date" , start, end,    "Highest Humidity", "%", "(select humidity, date from data where humidity == (select max(humidity) from data where node < 10 and humidity between 10 and 100))"],
                  ["pressure, date" , start, end,    "Lowest Pressure", "hPa", "(select pressure, date from data where pressure == (select min(pressure) from data where node < 10 and pressure between 950 and 1100))"],
                  ["pressure, date" , start, end,    "Highest Pressure", "hPa", "(select pressure, date from data where pressure == (select max(pressure) from data where node < 10 and pressure between 950 and 1100))"],
                 
                  
            ]:
                sql = "SELECT {0} from {3} where date >= '{1}' and date < '{2}'  ".format(x[0], x[1], x[2], x[5])
                result =  c.execute(sql).fetchone()
                if result is None or result[0] is None or result[0] == " ": 
                    data.append("")
                else:
                    data.append(result[0])
                    realDataCount += 1
            if realDataCount > 0:
                f.write('<tr><td>{}</td><td>'.format(start.strftime("%b %Y")))
                f.write("</td><td>".join(str(x) for x in data))
                f.write('</td></tr>')
                
            end = start    
            start = subMonth(start)
                    
        f.write("</table>\n")        
        ############################### YEARLY ############################# 
        
        
        f.write("<center><h3> {0}</h3></center>".format("Yearly") + "\n")
        f.write('<table border="1" rules="rows" cellspacing="0" cellpadding="3" style="line-height:20px;"> ' + "\n")
        f.write('<tr>' + "\n")
        f.write('<th rowspan="2">Year</th>' + "\n")
        f.write('<th colspan="2">Temperature <small>&deg;C</small></th>' + "\n")
        f.write('<th colspan="1">Rain <small>mm</small></th>' + "\n")
        f.write('<th colspan="2">Wind <small>km/h</small></th>' + "\n")
        f.write('<th colspan="2">Humidity <small>%</small></th>' + "\n")
        f.write('<th colspan="2">Pressure <small>hPa</small></th>' + "\n")
        f.write('</tr>' + "\n")
        
        f.write('<tr>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('<th>Total</th>' + "\n")
        f.write('<th>Avg</th>' + "\n")
        f.write('<th>Max Gust</th>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('<th>Min</th>' + "\n")
        f.write('<th>Max</th>' + "\n")
        f.write('</tr>' + "\n")
        
        low = date(lowest.year, 1, 1)
        high = date(highest.year, 1, 1)
        start = high
        end = addMonth(start, 12)
        

        while start >= low:
            data = []
            realDataCount = 0
            '''for x in [["min(temp)", start, end,         "Min Temp", "&deg;C", "(select temp, date, node from data where temp between -30 and 35)"],
                      ["max(temp)", start, end,         "Max Temp", "&deg;C", "(select temp, date, node from data where temp between -30 and 35)"],
                      ["sum(rain)", start, end,         "Total Rainfall","mm", "(select rain, date, node from data where rain between 0 and 1)"],
                      ["avg(wind_avg)", start, end,     "Avg Wind Speed", "km/h", "(select wind_avg, date, node from data where wind_avg between 0 and 120)"],
                      ["max(wind_gust)", start, end,    "Highest Gust Speed", "km/h", "(select wind_gust, date, node from data where wind_gust between 0 and 120)"],
                      ["min(humidity)" , start, end,    "Lowest Humidity", "%", "(select humidity, date, node from data where humidity between 10 and 100)"],
                      ["max(humidity)" , start, end,    "Highest Humidity", "%", "(select humidity, date, node from data where humidity between 10 and 100)"],
                      ["min(pressure)" , start, end,    "Lowest Pressure", "hPa", "(select pressure, date, node from data where pressure between 950 and 1100)"],
                      ["max(pressure)" , start, end,    "Highest Pressure", "hPa", "(select pressure, date, node from data where pressure between 950 and 1100)"],
                ]:'''
            for x in [["temp, date", start, end,         "Min Temp", "&deg;C", "(select date, temp from data where temp == (select min(temp) from data where node < 10 and temp between -30 and 35))"],
                  ["temp, date", start, end,         "Max Temp", "&deg;C", "(select date, temp from data where temp == (select max(temp) from data where node < 10 and temp between -30 and 35))"],
                  ["sum(rain), date", start, end,         "Total Rainfall","mm", "(select rain, date from data where rain between 0 and 1 and node < 10)"],
                  ["avg(wind_avg), date", start, end,     "Avg Wind Speed", "km/h", "(select wind_avg, date from data where wind_avg between 0 and 120 and node < 10 and wind_avg between 0 and 120)"],
                  ["wind_gust, date", start, end,    "Highest Gust Speed", "km/h", "(select wind_gust, date from data where wind_gust == (select min(wind_gust) from data where node < 10 and wind_avg between 0 and 120))"],
                  ["humidity, date" , start, end,    "Lowest Humidity", "%", "(select humidity, date from data where humidity == (select min(humidity) from data where node < 10 and humidity between 10 and 100))"],
                  ["humidity, date" , start, end,    "Highest Humidity", "%", "(select humidity, date from data where humidity == (select max(humidity) from data where node < 10 and humidity between 10 and 100))"],
                  ["pressure, date" , start, end,    "Lowest Pressure", "hPa", "(select pressure, date from data where pressure == (select min(pressure) from data where node < 10 and pressure between 950 and 1100))"],
                  ["pressure, date" , start, end,    "Highest Pressure", "hPa", "(select pressure, date from data where pressure == (select max(pressure) from data where node < 10 and pressure between 950 and 1100))"],
                 
                  
            ]:
                sql = "SELECT {0} from {3} where date >= '{1}' and date < '{2}'  ".format(x[0], x[1], x[2], x[5])
                result =  c.execute(sql).fetchone()
                if result[0] is None or result[0] == " ": 
                    data.append("")
                else:
                    data.append(result[0])
                    realDataCount += 1
            if realDataCount > 0:
                f.write('<tr><td>{}</td><td>'.format(start.strftime("%Y")))
                f.write("</td><td>".join(str(x) for x in data))
                f.write('</td></tr>')
                
            end = start    
            start = subMonth(start, 12)
                    
        f.write("</table>\n")

        ############################### ALL TIME ############################# 
        f.write("<center><h3> {0}</h3></center>".format("All Time") + "\n")
        f.write('<table border="1" rules="rows" cellspacing="0" cellpadding="3" style="line-height:20px;"> ' + "\n")
        f.write('<tr>' + "\n")
          
        low = date(lowest.year, 1, 1)
        high = date(highest.year, 1, 1)
        start = low
        end = addMonth(high, 12)
        
        for x in [["temp, date", start, end,         "Min Temp", "&deg;C", "(select date, temp from data where temp == (select min(temp) from data where node < 10))"],
                  ["temp, date", start, end,         "Max Temp", "&deg;C", "(select date, temp from data where temp == (select max(temp) from data where node < 10))"],
                  ["humidity, date" , start, end,    "Lowest Humidity", "%", "(select humidity, date from data where humidity == (select min(humidity) from data where node < 10 and humidity between 10 and 100))"],
                  ["humidity, date" , start, end,    "Highest Humidity", "%", "(select humidity, date from data where humidity == (select max(humidity) from data where node < 10 and humidity between 10 and 100))"],
                  ["pressure, date" , start, end,    "Lowest Pressure", "hPa", "(select pressure, date from data where pressure == (select min(pressure) from data where node < 10 and pressure between 950 and 1100))"],
                  ["pressure, date" , start, end,    "Highest Pressure", "hPa", "(select pressure, date from data where pressure == (select max(pressure) from data where node < 10 and pressure between 950 and 1100))"],
                  ["wind_gust, date", start, end,    "Highest Gust Speed", "km/h", "(select wind_gust, date from data where wind_gust == (select min(wind_gust) from data where node < 10))"],
                  ["avg(wind_avg)", start, end,     "Avg Wind Speed", "km/h", "(select wind_avg from data where wind_avg between 0 and 120 and node < 10)"],
                  ["sum(rain)", start, end,         "Total Rainfall","mm", "(select rain from data where rain between 0 and 1 and node < 10)"],
                  
            ]:
            sql = "SELECT {0} from {3}".format(x[0], x[1], x[2], x[5])
            result  =  c.execute(sql).fetchone()
            res = result[0]
            instant = None
            if len(result) > 1 and result[1] is not None:
                instant = datetime.strptime(result[1], "%Y-%m-%d %H:%S:%M")

            f.write('<tr>' + "\n")
            f.write('<th align="right">{0}: </th>'.format(x[3]) + "\n")
            f.write('<td>{0}<small>{1}</small></td>'.format(res, x[4]) + "\n")
            try:
              f.write('<td>{0}</td><td>{1}</td>'.format(instant.date(), instant.time()) + "\n")
            except:
              f.write('<td></td><td></td>' + "\n")  
            f.write('</tr>' + "\n")
                
                    
        f.write("</table>\n")
 
def genplot(indata, filename, title):
    tempLabels = []
    dateRange = []
    with open(filename+".dat", "w") as f:
        date = None
	for x in indata:
           date = str(x["date"])
           if len(dateRange) == 0:
              dateRange.append(date)
	   f.write("\""+str(x["date"]) + "\" ")
           for n in sorted(x["temp"]):
              if n not in tempLabels:
                   tempLabels.append(n)
   	      f.write(str(x["temp"][n]) + " ")
           f.write("\n")
        dateRange.append(date)

    with open(filename + ".plot", "w") as f:
      f.write('set title "{0}"'.format(title) + "\n")
      f.write('set xdata time' + "\n")
      f.write('set style data lines' + "\n")
      f.write('set term png' + "\n")
      f.write('set timefmt \'\"%Y-%m-%d %H:%M:%S\"\'' + "\n")
      f.write('set format x "%H:%M"' + "\n")
      f.write('set ylabel("Temp")' + "\n")
      f.write('set output "{0}"'.format(filename+".png") + "\n")
      f.write('set xrange [\'\"{0}\"\':\'\"{1}\"\']'.format(dateRange[1], dateRange[0]) + "\n")
      stri = []
      for xpos, x in enumerate(tempLabels):
        stri.append('\"{0}.dat\" u 1:{1} t \"{2}\"'.format(filename, xpos+2, x))
      f.write('plot ' + ",".join(stri))
	

 
def plotrecent(indata, filename, dateFormat, ticks=None):
    times = []
    temps = []
    tempLabels = []
    batts = []
    battLabels = []
    humidity = []
    pressure = []
    for x in indata:
        times.append(x["date"])
        t = []
        b = []
        for n in sorted(x["temp"]):
            if n not in tempLabels:
                tempLabels.append(n)
            t.append(x["temp"][n],)
        while len(t) < len(nodes):
            t.append(0)
        temps.append(t)
        
        for n in sorted(x["battery"]):
            if n not in battLabels:
                battLabels.append(n)
            b.append(x["battery"][n],)
        while len(b) < len(nodes):
            b.append(0)
        batts.append(b)
        
        
        try:
            humidity.append(x["humidity"])
        except:
            humidity.append(50)
        try:
            pressure.append(x["pressure"])
        except:
            pressure.append(950)
            
        
    f=figure()
    subplots_adjust(hspace=0.01)
    xfmt = md.DateFormatter(dateFormat)
    
    # do the temperatures
    ax1 = subplot(311)
    ax = ax1
    ax.plot(times, temps)
    ax.set_ylabel("Temp (oC)", color="b")
    ylim(min(min(tt) for tt in temps)-3, max(max(tt) for tt in temps)+3)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, # + box.height * 0.1,
                 box.width, box.height * 0.9])

    # Put a legend below current axis
    ax.legend(tempLabels, loc='upper center', bbox_to_anchor=(0.5,1.3),
          fancybox=True, shadow=True, ncol=5)
    

    tick_params(\
    axis='x',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    bottom='off',      # ticks along the bottom edge are off
    labelbottom='off') #
    
    # now the humidity
    ax2 = subplot(312, sharex=ax1)
    ax = ax2
    ax.plot(times, humidity, color="b")
    ax.set_ylabel("Humidity (%)", color="b")
    ylim(min(humidity)-5, max(humidity)+5)
    tick_params(\
    axis='x',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    bottom='off',      # ticks along the bottom edge are off
    labelbottom='off') #

    # and the pressure
    ax3 = subplot(313, sharex=ax1)
    ax = ax3
    ax.plot(times, pressure)
    ax.set_ylabel("Pressure (hPa)", color="b")
    
    '''
    # batteries
    ax4 = subplot(414, sharex=ax1)
    ax = ax4
    ax.plot(times, batts)
    ax.set_ylabel("Voltage (v)", color="b")
    ylim(min(min(tt) for tt in batts)-3, max(max(tt) for tt in batts)+3)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, # + box.height * 0.1,
                 box.width, box.height * 0.9])
             
    # Put a legend below current axis
    ax.legend(tempLabels, loc='upper center', bbox_to_anchor=(0.5,1.3),
          fancybox=True, shadow=True, ncol=5)
    '''
    
    ax.xaxis.set_major_formatter(xfmt)
    ylim(min(pressure)-5, max(pressure)+5)
    xticks(rotation = 45)
    if ticks == "day":
        loc = WeekdayLocator(byweekday=(MO,TU,WE,TH,FR,SA,SU))
        ax.xaxis.set_major_locator(loc)
    elif ticks == "hour":
        loc = HourLocator(byhour=range(24),interval=2)
        ax.xaxis.set_major_locator(loc)
    
    plt.savefig(filename)
    plt.cla()



#live
livetweet(highest, 5, 5, "output/tweet.txt")

import sys
# last hour
print "last hour"
recent(highest, 60, 5, "output/1hrs.txt", "Last Hour")
outputRecent("output/1hrs.txt", "Last Hour")

# last 12 hours
print "12 hours"
recent(highest, 60*12, 60, "output/12hrs.txt", "Last 12 Hours")
outputRecent("output/12hrs.txt", "Last 12 Hours" )
#plotrecent(alldata, "output/12hrs.png", "%H:%M", "hour")
genplot(alldata, "output/12hrs", "Last 12 Hours")

#last 24 hours 
print "24 hours"
recent(highest, 60*24, 60, "output/12hrs.txt", "Last 12 Hours")
#plotrecent(alldata, "output/24hrs.png", "%H:%M", "hour")
last24hours(highest, "output/24hrs.txt", "Last 24 Hours")
genplot(alldata, "output/24hrs", "Last 24 Hours")

# 7 days
print "7 days"
last7days(highest, "output/7days.txt", "Last 7 Days")
recent(highest, 60*24*7, 60, "output/12hrs.txt", "Last 12 Hours")
#plotrecent(alldata, "output/7days.png", "%a %d", "day")
genplot(alldata, "output/7days", "Last 7 days")


print "all history"
historic(highest, "output/allmonths.txt", "All historic data")


