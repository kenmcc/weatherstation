#!/bin/bash
cd /data

echo "weather data" | mutt -s "weather data" ken.mccullagh@gmail.com -a /data/weather.db 
