from django.db import models
from django.contrib.auth.models import User

class Website(models.Model):
    name = models.CharField(max_length=120, blank=True)
    url = models.URLField(unique=True)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    notification_email = models.EmailField(null=True, blank=True)
    alert_enabled = models.BooleanField(default=True)
    alert_cooldown_minutes = models.PositiveIntegerField(default=1440)
    performance_threshold = models.PositiveSmallIntegerField(default=80)
    
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.url

class PageSpeedReport(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='reports')
    strategy = models.CharField(max_length=10) # 'desktop' or 'mobile'
    

    
    # Core Scores (0-100)
    performance_score = models.PositiveSmallIntegerField(null=True, blank=True)
    accessibility_score = models.PositiveSmallIntegerField(null=True, blank=True)
    best_practices_score = models.PositiveSmallIntegerField(null=True, blank=True)
    seo_score = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # LAB DATA (Simulated Lighthouse Metrics)
    first_contentful_paint = models.FloatField(null=True, blank=True) # Seconds
    largest_contentful_paint = models.FloatField(null=True, blank=True) # Seconds
    total_blocking_time = models.FloatField(null=True, blank=True) # ms
    cumulative_layout_shift = models.FloatField(null=True, blank=True) # Unitless
    speed_index = models.FloatField(null=True, blank=True) # Seconds
    interaction_to_next_paint = models.FloatField(null=True, blank=True) # ms
    time_to_first_byte = models.FloatField(null=True, blank=True) # Seconds

    # FIELD DATA (Real-World CrUX 28-day averages)
    field_fcp = models.FloatField(null=True, blank=True) # Seconds
    field_lcp = models.FloatField(null=True, blank=True) # Seconds
    field_cls = models.FloatField(null=True, blank=True) # Unitless
    field_inp = models.FloatField(null=True, blank=True) # ms
    field_ttfb = models.FloatField(null=True, blank=True) # Seconds
    
    # Audit Meta
    status = models.CharField(max_length=20, default='success') # 'success' or 'failed'
    error_message = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)


class AlertLog(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='alerts')
    report = models.ForeignKey(PageSpeedReport, on_delete=models.SET_NULL, null=True)
    alert_type = models.CharField(max_length=50)
    score_at_alert = models.PositiveSmallIntegerField(null=True, blank=True)
    sent_to = models.EmailField()
    subject = models.CharField(max_length=200)
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert_type} for {self.website.url} on {self.created_at.strftime('%Y-%m-%d')}"
