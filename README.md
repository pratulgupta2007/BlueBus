# BlueBus

BlueBus is a Django-based bus booking application with user authentication, route search, seat selection, booking verification, wallet/balance management, refunds, and booking history.

## Features

- Search buses by source, destination, and travel date
- View available routes and seats
- Book tickets with OTP-based verification
- Manage wallet balance and transaction history
- View bookings, profile details, and refund information
- Google login support via `django-allauth`
- PostgreSQL-backed persistence
- Dockerized local and production setups

## Tech Stack

- Django 5.x
- PostgreSQL 15
- `django-allauth` for authentication
- `django-import-export` for admin data workflows
- Gunicorn and Nginx for production deployment

## Project Structure

- `server/` contains the Django project, app code, templates, and Dockerfiles
- `nginx/` contains the reverse proxy configuration used in production
- `docker-compose.yml` starts the development stack
- `docker-compose.prod.yml` starts the production stack

## Prerequisites

- Docker and Docker Compose
- Or Python 3.11 with PostgreSQL if you want to run the app without Docker

## Environment Variables

Create the required environment file(s) before starting the app.

For local development, the app expects values such as:

- `SECRET_KEY`
- `DEBUG`
- `SQL_ENGINE`
- `SQL_DATABASE`
- `SQL_USER`
- `SQL_PASSWORD`
- `SQL_HOST`
- `SQL_PORT`
- `CLIENT_ID`
- `CLIENT_SECRET`
- `EMAIL_ID`
- `APP_PWD`

For production, use the variables referenced by `.env.prod` and `.env.prod.db`.

## Run With Docker

### Development

```bash
docker compose up --build
```

This starts the Django app on `http://localhost:8000` and PostgreSQL in a separate container.

### Production

```bash
docker compose -f docker-compose.prod.yml up --build
```

This starts Gunicorn behind Nginx and serves the app on `http://localhost:80`.

## Local Development Without Docker

If you prefer running Django directly, install the Python dependencies from `server/requirements.txt`, create a `.env` file with the required variables, then run:

```bash
cd server
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Main URLs

- `/home/` - landing page
- `/book/` - search form
- `/search/` - route results
- `/accounts/` - authentication and account pages
- `/admin/` - Django admin

## Notes

- The app uses PostgreSQL by default through Docker Compose.
- Email verification and Google sign-in require valid provider credentials.
- Static files are collected automatically in the production container startup flow.
