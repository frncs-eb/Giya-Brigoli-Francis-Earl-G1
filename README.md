# Giya

A full-stack Django project (backend and frontend via Django templates).

## Structure

```
Giya/            Project config (settings, urls, wsgi/asgi)
accounts/        Accounts app
dashboard/       Dashboard app
templates/       Project-wide templates
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
