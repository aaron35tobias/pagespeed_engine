from django.db import models

class Website(models.Model):
    name = models.CharField(max_length=120, blank=True)
    url = models.URLField(unique=True)
    performance_threshold = models.PositiveSmallIntegerField(default=80)
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

    def __str__(self):
        return f"{self.website.url} - {self.strategy} - {self.fetched_at.strftime('%Y-%m-%d %H:%M')}"