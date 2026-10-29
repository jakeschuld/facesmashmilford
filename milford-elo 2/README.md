# Milford Elo Ranking

A 1v1 face-off ranking site for the group. Python (Flask) + SQLite. The 22 players and their photos are loaded automatically on first run. Everyone starts at 0.

## Run it on your computer
1. Install Python 3.10 or newer.
2. In this folder, run:
       pip install -r requirements.txt
       python app.py
3. Open http://localhost:5000

To let friends on the same Wi-Fi vote, have them open http://YOUR-COMPUTER-IP:5000

## Put it online with your own domain
1. Push this folder to a GitHub repo.
2. Create a web service on Render (render.com) or Railway from that repo.
   - Start command: gunicorn app:app
   - Add a persistent disk and set the env var DB_PATH to a file on that disk
     (for example /data/elo.db), or votes reset when the server restarts.
     Uploaded photos go in static/uploads, so mount the disk there too or
     add photos in the repo under static/photos.
3. Buy a domain (Namecheap, Cloudflare, Porkbun) and add it under the
   service's Custom Domains settings. Follow the DNS records it shows you.

## How ratings work
Every vote is stored. The page replays all votes in order to compute ratings
(Elo, K = 32), so deleting a vote recalculates everything.

## Files
- app.py: server and API
- templates/index.html: the whole site (face-off, standings, analytics)
- static/photos/: starting headshots
- static/uploads/: photos added from the site
- elo.db: created on first run

## Heads-up
There are no logins. Anyone with the link can vote, add players, change photos,
and delete votes. Share the link only with the group.
