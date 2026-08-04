# Academic Audit Analytics Tool

A lightweight Streamlit application for managing student marks and viewing role-based analytics.

## What this project includes

- Streamlit login screen with role-based routing
- Registrar workflow for Excel upload and manual mark entry
- Admin analytics dashboard with charts and recommendations
- SQLite-backed storage using the built-in sqlite3 module

## Requirements

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

## Default test accounts

- Registrar: username `registrar`, password `registrar123`
- Admin: username `admin`, password `admin123`

## Notes

- The database file is created automatically as `academic_audit.db` when the app starts.
- The SQLite schema is initialized in `db.py` on startup.
