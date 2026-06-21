# Core Logic Flow
This document outlines how data moves through the application.

## 1. On-Demand Audit Flow
1. User submits a URL on the dashboard.
2. The view extracts the URL, formats it, and ensures a `Website` record exists.
3. The view dispatches two async tasks: `run_audit_task.delay(id, 'desktop')` and `run_audit_task.delay(id, 'mobile')`.
4. The UI instantly redirects the user with a success message: "Audit queued."
5. In the background, the Celery worker reaches out to the `https://www.googleapis.com/pagespeedonline/v5/runPagespeed` endpoint.
6. The JSON response is parsed. Core Web Vitals (which are buried deep in `lighthouseResult.audits`) are extracted and converted into seconds or milliseconds depending on the metric.
7. A `PageSpeedReport` is saved to the database.

## 2. The Alert System (Post-Save)
The key business value of this tool is the automated alerting.

When a `PageSpeedReport` is saved:
- The system checks if `report.performance_score < website.performance_threshold`.
- If true, it checks the `AlertLog` table to see if an email was already sent recently (based on `website.alert_cooldown_minutes`).
- If no recent alert exists, Django's `send_mail` utility is triggered to notify the `notification_email`.
- An `AlertLog` record is created so the cooldown timer begins.

## 3. History Search & Trend Graphing
- When a user views a specific site, a JSON API endpoint (`/api/history/...`) serves the last 30 runs.
- Chart.js plots the `fetched_at` dates on the X-axis and the `performance_score` on the Y-axis.
