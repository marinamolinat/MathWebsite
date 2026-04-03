# Math Club website

An interactive website for my school's Math Club where organizers can assign problems and students can complete them (with a leaderboard and score system). Also, an excuse to finally learn backend with Flask!

<a href="https://marina281.pythonanywhere.com/adminDashboard"> Live here.</a>
Note: This site is mostly for my school's, so only access if you must  (i.e. you are a HCTG reviewer)


## How it works 

In the website, users can have two roles: either they are students or organizers. Organizers can assign new problems and grade problems, while students can submit answers to problems. Both can view a leaderboard of students. 

It's a simple Flask application. The /database directory includes the database, and a python module (dbUtils.py) that has classes (Student and Problem) that manage queries to the database. I'm aware that using OOP was kinda extra, but oh well, it works ig. 

### Some illustrations of how the database works 
<img src="https://cdn.hackclub.com/019d50a1-c2c1-7f93-9950-44f0da1b0f41/image.png" width="600">

<img src="https://cdn.hackclub.com/019d50a2-a2be-73d6-96d4-663cdc45559a/image.png" width="600">

### Example of how problems are added by organizers
See the video <a href="https://user-cdn.hackclub-assets.com/019d5091-dfb5-7ab4-abd9-aa46cec7b720/screen_recording_2026-04-02_at_6.24.12___pm.mp4" target="_blank"> here </a>


