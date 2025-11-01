# GMAO C-130H Setup

The application now starts with a clean database so you can explore the new maintenance layouts without legacy demo content getting in the way.

## First run

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies: `pip install -r requirements.txt`.
3. Launch the development server: `flask --app gmao run`.

The first launch creates the database (SQLite by default), applies pending schema upgrades, and seeds the core reference data (roles, default workshops, and an administrator account).

## Optional: load the curated demo dataset

If you still want the full demo dataset for exploration, trigger it manually:

```bash
flask --app gmao seed-demo
```

The command drops the existing schema, recreates it, and repopulates the curated dataset.

## Git Bash helper

Developers using Git Bash on Windows can run `./scripts/gitbash_workflow.sh` to automate pulling the latest code, syncing the virtual environment, and reseeding the demo database when desired.
