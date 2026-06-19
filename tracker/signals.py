from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import PageSpeedReport, AlertLog

# Minimum point drop between two consecutive scans to trigger a significant-drop alert
SIGNIFICANT_DROP_THRESHOLD = 30

# ── Alert 1: absolute threshold breach ──────────────────────────────────────
# Fires when score < website.performance_threshold (e.g. below 80)
@receiver(post_save, sender=PageSpeedReport)
def trigger_performance_alert(sender, instance, created, **kwargs):
    # 'created' ensures this only runs when a NEW report is added, not if we edit an old one
    if created and instance.status == 'success':
        website = instance.website

        # Check if alerts are enabled
        if not website.alert_enabled:
            return

        # Check if the score dropped below the threshold
        if instance.performance_score < website.performance_threshold:

            # Debounce Engine: Check for recent alerts based on cooldown
            recent_alert = AlertLog.objects.filter(
                website=website,
                alert_type='threshold_breach',
                created_at__gte=timezone.now() - timedelta(minutes=website.alert_cooldown_minutes)
            ).exists()

            if not recent_alert:
                subject = f'ALERT: {instance.strategy.upper()} PageSpeed dropped to {instance.performance_score} for {website.name}'
                message = f'Automated System: The {instance.strategy.upper()} score for {website.url} has dropped to {instance.performance_score}.'

                recipient = website.notification_email if website.notification_email else settings.DEFAULT_FROM_EMAIL

                # Send the email
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient]
                )

                # Log it to start the cooldown
                AlertLog.objects.create(
                    website=website,
                    report=instance,
                    alert_type='threshold_breach',
                    score_at_alert=instance.performance_score,
                    sent_to=recipient,
                    subject=subject,
                    delivered=True
                )


# ── Alert 2: significant relative drop ──────────────────────────────────────
# Fires when score drops 30+ points vs the previous scan for the same URL+strategy.
# Example: 98 → 68 = drop of 30 → ALERT  |  70 → 60 = drop of 10 → no alert
@receiver(post_save, sender=PageSpeedReport)
def trigger_significant_drop_alert(sender, instance, created, **kwargs):
    # Only process new successful reports that have a score
    if not (created and instance.status == 'success' and instance.performance_score is not None):
        return

    website = instance.website
    if not website.alert_enabled:
        return

    # Find the most recent PREVIOUS successful scan for this exact URL + strategy
    previous = (
        PageSpeedReport.objects
        .filter(
            website=website,
            strategy=instance.strategy,
            status='success',
            performance_score__isnull=False,
        )
        .exclude(id=instance.id)
        .order_by('-fetched_at')
        .first()
    )

    # No previous scan to compare against — skip (first run for this URL)
    if previous is None:
        return

    drop = previous.performance_score - instance.performance_score

    # Only fire if the drop meets or exceeds 30 points
    if drop < SIGNIFICANT_DROP_THRESHOLD:
        return

    # Debounce: don't re-alert for the same site within the cooldown window
    recent_alert = AlertLog.objects.filter(
        website=website,
        alert_type='significant_drop',
        created_at__gte=timezone.now() - timedelta(minutes=website.alert_cooldown_minutes),
    ).exists()

    if recent_alert:
        return

    subject = (
        f'ALERT: {instance.strategy.upper()} score dropped {drop} points '
        f'for {website.name or website.url}'
    )
    message = (
        f'Significant performance drop detected!\n\n'
        f'URL:            {website.url}\n'
        f'Strategy:       {instance.strategy.upper()}\n'
        f'Previous score: {previous.performance_score}  '
        f'(scanned {previous.fetched_at.strftime("%b %d, %Y %H:%M")})\n'
        f'Current score:  {instance.performance_score}  '
        f'(scanned {instance.fetched_at.strftime("%b %d, %Y %H:%M")})\n'
        f'Drop:           -{drop} points\n\n'
        f'This alert fires when a score falls {SIGNIFICANT_DROP_THRESHOLD}+ points '
        f'between consecutive scans for the same URL and strategy.'
    )

    recipient = website.notification_email if website.notification_email else settings.DEFAULT_FROM_EMAIL

    # Console log so the trigger is visible during dev before SMTP is wired up
    print(
        f'[SignificantDrop] {website.url} ({instance.strategy.upper()}) | '
        f'{previous.performance_score} → {instance.performance_score} (drop: -{drop})'
    )

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)

    # Log the alert to start the debounce cooldown window
    AlertLog.objects.create(
        website=website,
        report=instance,
        alert_type='significant_drop',
        score_at_alert=instance.performance_score,
        sent_to=recipient,
        subject=subject,
        delivered=True,
    )