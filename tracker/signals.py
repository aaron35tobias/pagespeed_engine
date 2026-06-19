from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import PageSpeedReport, AlertLog

# This decorator tells Django: "Listen for whenever a PageSpeedReport is saved"
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