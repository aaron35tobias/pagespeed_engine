# Project Status & Capabilities

What is currently implemented in the codebase, and what was intentionally left out for future iterations.

## What Is Implemented (100% Complete)
- **Automated Asynchronous Workers**: Celery is fully integrated. `fetch_pagespeed_data` is now an async task, meaning browser requests never block.
- **Robust Scheduling**: `django-celery-beat` is installed and migrated. Automated cron jobs can be configured directly from the DB.
- **Dual Strategy Capturing**: The system scans both Mobile and Desktop metrics for every URL concurrently.
- **Historical Charting & UI**: Dynamic search filters, responsive Light/Dark mode, and interactive Chart.js line graphs.
- **Debounced Alerting**: The logic to compare scores against thresholds and debounce via `AlertLog` is active.
- **Production SMTP Configuration**: `settings.py` is configured to use environment variables (`EMAIL_HOST`, etc.) when `DEBUG=False`.
- **Zero-Dependency Local Demo Mode**: We introduced `CELERY_TASK_ALWAYS_EAGER = True` for the local development environment to bypass the Redis broker. This allows a fully functional local demo on Windows machines without requiring a Dockerized Redis instance.

## What Is NOT There (And Why)

1. **MetricThreshold Table**
   - *Status*: Not implemented.
   - *Why*: The Technical Spec marked this as optional. Instead of a 4th database table, we hardcoded the industry-standard Google cutoffs directly in the UI logic (e.g., Performance >= 90 is good, 50-89 is needs improvement, <50 is poor). This keeps the database lightweight and removes the need for complex admin management of standard metrics.

2. **Django Rest Framework (DRF)**
   - *Status*: Not implemented.
   - *Why*: The frontend only needed basic JSON arrays for the charts and history search. Pulling in the entire DRF library was overkill. We utilized Django's built-in `JsonResponse` to serve the data instantly with zero bloat.

3. **External Email Providers Configured out-of-the-box**
   - *Status*: Code is ready, but credentials are empty.
   - *Why*: We configured `EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'`, but the company deploying this must create their own SendGrid, Mailgun, or Amazon SES account and inject those keys into the `.env` file. We cannot commit live SMTP credentials to a code repository.
