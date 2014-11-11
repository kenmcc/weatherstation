#!/bin/bash
cd /data
python lasthour.py >>loader.log
gnuplot output/*.plot
python Upload.py output output/1hrs.txt output/12hrs.txt output/24hrs.txt output/7days.txt output/allmonths.txt output/24hrs.png output/12hrs.png output/7days.png >> loader.log
python ToTwitter.py output/ output/tweet.txt

echo "Uploaded" >> loader.log
rm output/*.png
rm output/*.dat
rm output/*.plot
rm output/tweet.txt
