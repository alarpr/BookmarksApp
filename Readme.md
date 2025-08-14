
BookmarksApp - Estonian Bookmark Organizer
Overview
BookmarksApp is a FastAPI-based web application that allows you to manage and organize website bookmarks in a hierarchical folder structure. The application supports multiple import/export formats and provides a user-friendly interface for organizing bookmarks.

Key Features
📚 Bookmark Management

Hierarchical structure: Create folders and subfolders to organize bookmarks

Drag & Drop: Drag bookmarks between folders

Search: Search bookmarks by title or URL

Preview: View pages directly in the application (YouTube, GitHub README support)

📥 Import/Export

HTML: Import Safari/Netscape bookmark files

CSV: Import/export data in a table format

JSON: Import/export structured data

SQLite: Database backup and restore

🎛️ User Interface

Resizable columns: Change the width of the sidebar and preview with dragging

Double-click: Quick solutions for column widths

Dark theme: A modern, eye-friendly design

Responsive: Works on different screen sizes

🔍 Additional options

Link checking: Automatic check to see if links are working

Favicon: Shows page icons

Bulk actions: Delete/move multiple bookmarks at once

Technical Information
Backend

FastAPI: Modern Python web framework

SQLAlchemy: ORM for database management

SQLite: Database (file-based)

Jinja2: Template engine for HTML

Frontend

Vanilla JavaScript: Without a framework

CSS Grid: Modern layout

HTML5: Semantic markup

Dependencies

fastapi==0.114.2
uvicorn[standard]==0.30.6
jinja2==3.1.4
sqlalchemy==2.0.32
pydantic==2.8.2
python-multipart==0.0.9
beautifulsoup4==4.12.3
httpx==0.27.2
Installation
1. Clone the project

Bash
git clone <repository-url>
cd BookmarksApp
2. Create a virtual environment

Bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
3. Install dependencies

Bash
pip install -r requirements.txt
4. Start the server

Bash
# HTTP (for development)
./start_server.sh

# or HTTPS (local)
./start_server_https.sh
5. Open in browser

HTTP: http://localhost:8000

HTTPS: https://localhost:8444 (local certificate)

Usage
Adding bookmarks

Select the folder where you want to add a bookmark

Enter the title and URL

Click "Add link"

Managing folders

Add folder: Enter the folder name and click "Add"

Rename: Click "Tools" → enter a new name

Delete: Click "Delete" (the root folder cannot be deleted)

Importing

Select "Manage Resources" → Import from the menu

Select the file (HTML/CSV/JSON)

Click "Upload"

View the results (imported/skipped)

Exporting

HTML: Netscape format, compatible with most browsers

CSV: Table format, can be opened in Excel

JSON: Structured data, for programming

Changing column width

Dragging: Move the mouse over the separator bar and drag

Double-click: Quick solutions for preset widths

Saving: The widths are remembered even when the page is reopened

Database structure
Tables

topics: Folder hierarchy (id, name, parent_id)

bookmarks: Bookmark data (id, title, url, topic_id)

Relationships

A folder can contain subfolders and bookmarks

A bookmark always belongs to one folder

Root folder: "My collections"

Development
Project structure

BookmarksApp/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy models
│   ├── db.py           # Database connection
│   ├── parse_bookmarks.py  # HTML parsing
│   ├── templates/       # HTML templates
│   └── static/         # CSS, JavaScript
├── requirements.txt
├── start_server.sh      # HTTP server
└── start_server_https.sh # HTTPS server
Adding new features

Add an endpoint to main.py

If necessary, update models.py

Add the user interface to the templates/ or static/ folder

Test the functionality

Database changes

Bash
# Viewing the SQLite database
sqlite3 bookmarks.sqlite3
.tables
.schema topics
.schema bookmarks
Troubleshooting
Import not working

Check the file format (HTML should be in Netscape format)

Check the server logs for error messages

Try with a smaller file

Server not starting

Check if the port is free: lsof -i :8000

Stop the existing process: pkill -f uvicorn

Check the virtual environment: which python

HTTPS issues

Self-signed certificates can cause warnings

Use HTTP for development

Use Let's Encrypt for a production environment

Future features
[ ] Drag & Drop import

[ ] Duplicate merging

[ ] Additional filtering options

[ ] Mobile user interface

[ ] API documentation

[ ] User management

[ ] Synchronization

License
MIT License - free to use and modify.

Contact
For questions or suggestions, create an issue on GitHub or contact the developer.

Note: This application is created for Estonian-speaking users, but the code is in English to follow standards.