# Database Schema & Models
The engine relies on three essential tables. We opted for a normalized structure to ensure history is preserved efficiently over time.

## 1. Website (The Parent Record)
Holds the URL and configuration for alerting.
- **Why a separate table?** We don't want to store configuration settings (like `alert_cooldown_minutes` or `performance_threshold`) on every single audit run. The Website table acts as the single source of truth for a monitored target.

## 2. PageSpeedReport (The Ledger)
One row is created for every audit run. It stores the Core Web Vitals (FCP, LCP, CLS, etc.) and the top-level scores (Performance, SEO, Best Practices, Accessibility).
- **Why save everything?** By storing each run chronologically with a `fetched_at` timestamp, we can plot historical trend graphs using Chart.js. We separate `strategy` (mobile vs desktop) so we can filter and compare device-specific performance.

## 3. AlertLog (The Debouncer)
Records every alert email that gets sent out.
- **Why is this needed?** If a website's score drops to 40, and we audit it hourly, the owner will receive 24 emails a day. The `AlertLog` checks the `alert_cooldown_minutes` and "debounces" the emails, ensuring the team is notified once per incident window.

## MySQL vs SQLite
- **Why MySQL?** SQLite locks the entire database during writes. Because Celery might have multiple workers running audits concurrently and writing to the database at the exact same time, SQLite would result in "Database is locked" errors. MySQL handles concurrent connections and writes smoothly.
