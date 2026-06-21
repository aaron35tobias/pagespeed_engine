# To do

## Phase 1: Core Foundation (Completed)
- [x] **Environment Setup**: Isolate Python virtual environment and lock dependencies (`requirements.txt`).
- [x] **Secrets Management**: Abstract API keys and database credentials into `.env` (secured via `.gitignore`).
- [x] **Database Pivot**: Transition from PostgreSQL to MySQL (`mysqlclient`) and initialize `pagespeed_db`.
- [x] **Schema Definition**: Build and migrate `Website` and `PageSpeedReport` tables.
- [x] **API Integration**: Expand standard API payload to capture Accessibility, Best Practices, and SEO scores alongside Performance.
- [x] **Synchronous Engine**: Implement Django view to handle URL submission, trigger Google PSI REST API, parse nested JSON, and write to MySQL.
- [x] **Dual Strategy Support**: Added logic to capture BOTH desktop and mobile data on every manual submit.
- [x] **Code Refactoring**: Extracted synchronous PSI API execution logic into `tracker/services.py` to prepare for Celery worker transition.
- [x] **Admin & Documentation**: Create superuser for raw data verification and draft `README.md` for team onboarding.

## Phase 2: Frontend & Alerts (Completed)
- [x] **Frontend Spec Handoff**: Deliver UI/UX specifications (dark-mode dashboard, Core Web Vitals grid) to the frontend developer based on API JSON structure.
- [x] **Dashboard Views**: Update `views.py` to query the MySQL database and render historical reports on `dashboard.html`.
- [x] **Data Visualization**: Implement `Chart.js` on the frontend to render line graphs of performance trends over time.
- [x] **Schema Expansion**: Add missing fields from Technical Design Spec (e.g., `owner`, `notification_email`, `alert_enabled`).
- [x] **Alert Logistics**: Define and migrate the `AlertLog` table to debounce duplicate email warnings.
- [x] **Email Logic Integration**: Complete the threshold evaluation logic by triggering a `send_mail` function when `performance_score < performance_threshold`.

## Phase 3: Automation & Scale (Completed)
- [x] **Asynchronous Workers**: Migrate the newly extracted `fetch_pagespeed_data` logic to a Celery worker to prevent browser blocking.
- [x] **Audit Automation**: Wire up `django-celery-beat` to schedule and execute recurring API pings (hourly/daily) for all active websites.
- [x] **Production SMTP**: Swap Django's console email backend for a production provider (e.g., SendGrid, Mailgun, Amazon SES).

