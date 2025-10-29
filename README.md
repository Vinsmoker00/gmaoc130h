# GMAO C-130H Demo Dataset

The application now bootstraps a complete demo dataset so you can explore each mini-app immediately after cloning the repository.

## First run

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies: `pip install -r requirements.txt`.
3. Launch the development server: `flask --app gmao run`.

When the Flask app starts it will automatically create the database (SQLite by default) and load the curated demo data if no aircraft or material records exist yet. You should see the aircraft fleet, 100 material references, 100 personnel profiles, and 100 scheduled visits populated on first load.

## Refreshing the dataset

If you want to reset the database and reload the demo content at any time, run:

```bash
flask --app gmao seed-demo
```

The command drops the existing schema, recreates it, and repopulates the curated dataset.

## Git Bash helper

Developers using Git Bash on Windows can run `./scripts/gitbash_workflow.sh` to automate pulling the latest code, syncing the virtual environment, and reseeding the demo database.
