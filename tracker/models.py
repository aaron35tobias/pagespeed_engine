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
    
    # Core Web Vitals
    first_contentful_paint = models.FloatField(null=True, blank=True) # Seconds
    largest_contentful_paint = models.FloatField(null=True, blank=True) # Seconds
    total_blocking_time = models.FloatField(null=True, blank=True) # ms
    cumulative_layout_shift = models.FloatField(null=True, blank=True) # Unitless
    speed_index = models.FloatField(null=True, blank=True) # Seconds
    interaction_to_next_paint = models.FloatField(null=True, blank=True) # ms
    
    # Audit Meta
    status = models.CharField(max_length=20, default='success') # 'success' or 'failed'
    error_message = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.website.url} - {self.strategy} - {self.fetched_at.strftime('%Y-%m-%d %H:%M')}"