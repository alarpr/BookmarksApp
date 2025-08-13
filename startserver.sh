lsof -nP -iTCP:8055 -sTCP:LISTEN -t | xargs -r kill -9
source /Users/alar/Documents/Projektid/BookmarksApp/.venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8055 --reload
