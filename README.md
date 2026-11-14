# Giya

**Giya: Integrated Management for Academic and Clinical Excellence** is a project for IT317 - G1. It is intended to help allied health students manage the demands of classes, clinical duties, and personal budgets in one place.

The project charter identifies nursing, pharmacy, and medical technology students as the primary users. The goal is to reduce schedule conflicts, missed duties, and disorganized routines by bringing the students' academic and clinical workflows together.

## Project goals

The planned application brings together:

- Account registration and secure sign-in
- Class schedule and calendar management
- Task planning and reminders
- Clinical duty hours, case, and rotation logging
- Personal expense tracking and budget summaries
- A central dashboard

The charter excludes advanced financial and banking services, as well as clinical verification and collaboration workflows. The current codebase is an early Django foundation: account registration, login/logout, and a protected starter dashboard are implemented; the other planned modules are not yet available.

## Technology

- Python 3.10 or later
- Django 5.1 or later, but earlier than 6.0
- Supabase PostgreSQL for the shared application database
- SQLite fallback for local checks and automated tests when `DATABASE_URL` is unset
- Django templates for the web pages

## Project structure

```text
Giya/                 Django project configuration and root URL routes
accounts/             Account registration, authentication routes, and tests
dashboard/            Protected dashboard and tests
templates/
  accounts/           Login and registration pages
  dashboard/          Dashboard page
  base.html            Shared page layout and navigation
.env.example          Template for local environment configuration
manage.py             Django command-line utility
requirements.txt      Python dependencies
```

## Run the project on Windows

Run these commands in **PowerShell** from the project directory—the folder that contains `manage.py`.

1. **Install Python.** Install Python 3.10 or later and make sure the Python launcher is available. Verify it in PowerShell:

   ```powershell
   py --version
   ```

2. **Create a Supabase project.** In the Supabase dashboard, create a project and set its database password. Open **Connect** and copy the PostgreSQL connection URI for your project. Keep the password private; do not paste it into source files or commit it to Git.

3. **Open the project directory.** In VS Code, open the `Giya-Brigoli-Francis-Earl-G1` folder, then select **Terminal > New Terminal**. Confirm that the terminal is in the folder containing `manage.py`:

   ```powershell
   Get-ChildItem manage.py
   ```

4. **Create a virtual environment** to keep the project dependencies separate:

   ```powershell
   py -m venv .venv
   ```

5. **Activate the environment:**

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   After activation, PowerShell should show `(.venv)` at the start of the prompt.

6. **Install the dependencies:**

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. **Configure the Supabase connection.** Copy the example environment file and open `.env`:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Set `DATABASE_URL` to the PostgreSQL connection URI you copied from Supabase. Ensure the URI uses SSL (`sslmode=require`) if Supabase has not already included an SSL mode. Save the file. `.env` is excluded from Git, so your database credentials stay local.

8. **Create or update the database tables:**

   ```powershell
   python manage.py migrate
   ```

   This applies Django's migrations to the configured Supabase database. The first run may take a short time.

9. **Start the development server:**

   ```powershell
   python manage.py runserver
   ```

10. **Open Giya** at [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Use the links in the page header or visit:

   - `/register/` to create an account
   - `/login/` to sign in
   - `/dashboard/` to open the dashboard (requires sign-in)
   - `/admin/` for the Django admin site

   To stop the server, focus the terminal and press **Ctrl+C**.

### Optional: create an admin account

To sign in to `/admin/`, stop the server if needed, then run:

```powershell
python manage.py createsuperuser
```

Follow the prompts to create an administrator in the configured database, then start the server again with `python manage.py runserver`.

### If PowerShell blocks environment activation

You can run the virtual environment's Python directly without activating it. For example:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Make sure `.env` is configured before running migrations or starting the server.

## Run tests

With the virtual environment activated, run the account and dashboard tests:

```powershell
python manage.py test accounts dashboard
```
