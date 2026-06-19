from django.contrib import admin
from .models import Website, PageSpeedReport, AlertLog

@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'performance_threshold', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'url')

@admin.register(PageSpeedReport)
class PageSpeedReportAdmin(admin.ModelAdmin):
    list_display = ('website', 'strategy', 'performance_score', 'status', 'fetched_at')
    list_filter = ('strategy', 'status', 'fetched_at')

@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ('website', 'alert_type', 'score_at_alert', 'sent_to', 'created_at')