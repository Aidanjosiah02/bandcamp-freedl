# Bandcamp-free-dl
A Python script for downloading free albums and tracks with their metadata in the highest quality available. No Selenium or Scrapy; uses Requests. Also works around albums/tracks that require emails automatically by using a temporary email service (thanks to ['1secMail'](https://www.1secmail.com/api/) for their API!). For albums and tracks that require payment, this script can grab the 128kbps mp3 files as higher quality copies are not available without purchase.

* Script waiting with every request?  
This is an attempt to act somewhat similar to someone using a browser and to fit in with the rest of the traffic in order to be respectful to Bandcamp. If you want to turn this off, change the `WAITS` constant at the top of "bandcampfreedl.py" to `False`.

# Use in other projects
This project is not actively maintained, though I may update it once in a while if it stops working or if I improve it on my own time. 
It is written in a somewhat naive manner and is thus not suitable for use in other projects. For this case think of it as a reference for understanding how Bandcamp's download process works.

# Install and run
Ensure you have [Python](https://www.python.org/) installed first and included in your system PATH.  
Look in the top-right of this Github page for a green dropdown box that says \[ <> Code \], then click "Download ZIP". Extract the files wherever you like.  
Inside you should also see a "batch.txt" file in there. This is where you will put links to Bandcamp artists/tracks/albums for downloading. I have included one in there purely for example and testing purposes.  
Once you've populated the batch file with what you want, run the "run.bat" file to install the [Beautifulsoup](https://pypi.org/project/beautifulsoup4/) Python library (it will skip if it's already installed), as well as to make it run.

# File and directory structure
The script will create files named "archive.txt" and "checkpoint.txt", directories named "publishers" and "metadata".

The archive file keeps track of all IDs for successful downloads so that the script can automatically skip these if found at a later time. IDs are used instead of URLs in case a publisher removes a track/album and re-lists it with the same URL, but the content is potentially modified. 
The checkpoint file keeps track of all URLs for tracks/albums that were downloaded successfully and/or require payment, so that if the script crashes or fails it will automatically start where it left off rather than check each track/album again. You may delete this file after a successful run. 
The "publishers" directory is where all the music is stored, seperated by publisher. 
The "metadata" directory is where relevant metadata is stored for posterity and easy cataloguing; descriptions, release dates, covers, etc..
