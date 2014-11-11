#!/bin/bash

errorString=`python manager.py`
echo $errorString
if [ "$errorString" !=  "" ]; then
  print "emailing"
  echo $errorString | mutt -s "WeatherStation Failure" ken.mccullagh@gmail.com
fi

stillRunnin=`ps -eaf | grep tempreader | grep -v grep`
if [ "$stillRunnin" = "" ]; then
  echo "Temp Reader needs a restart" | mutt -s "Weather station down" ken.mccullagh@gmail.com
  pushd /home/python/weatherstation
  sudo python /home/python/weatherstation/tempreader.py &
  popd
fi
