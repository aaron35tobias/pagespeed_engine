import requests
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from tracker.models import Website, PageSpeedReport, AlertLog

class Command(BaseCommand):
    help = 'Loops through all active websites in the database and runs a background PageSpeed audit.'

    def handle(self, *args, **kwargs):
        # Grab every website currently stored in your MySQL database
        websites = Website.objects.all()
        
        if not websites:
            self.stdout.write(self.style.WARNING("No websites found in the database. Exiting."))
            return

        self.stdout.write(self.style.NOTICE(f"Starting automated audits for {websites.count()} websites..."))

        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

        for website in websites:
            self.stdout.write(f"Auditing: {website.url}...")
            
            # We will run the automated daemon in 'mobile' strategy as it catches more performance issues
            strategy = 'MOBILE'
            
            params = {
                'url': website.url,
                'key': settings.GOOGLE_API_KEY,
                'strategy': strategy,
                'category': ['performance', 'accessibility', 'best-practices', 'seo']
            }

            try:
                response = requests.get(api_url, params=params)
                response.raise_for_status()
                data = response.json()

                # --- EXTRACT DATA (Same logic as your views.py) ---
                lighthouse = data.get('lighthouseResult', {})
                categories = lighthouse.get('categories', {})
                audits = lighthouse.get('audits', {})

                perf_score = int(categories.get('performance', {}).get('score', 0) * 100)
                access_score = int(categories.get('accessibility', {}).get('score', 0) * 100)
                bp_score = int(categories.get('best-practices', {}).get('score', 0) * 100)
                seo_score = int(categories.get('seo', {}).get('score', 0) * 100)

                fcp = audits.get('first-contentful-paint', {}).get('numericValue', 0) / 1000.0
                lcp = audits.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000.0
                tbt = audits.get('total-blocking-time', {}).get('numericValue', 0)
                cls = audits.get('cumulative-layout-shift', {}).get('numericValue', 0)
                speed_idx = audits.get('speed-index', {}).get('numericValue', 0) / 1000.0
                inp = audits.get('interaction-to-next-paint', {}).get('numericValue', 0)
                ttfb = audits.get('server-response-time', {}).get('numericValue', 0) / 1000.0

                loading_experience = data.get('loadingExperience', {})
                field_metrics = loading_experience.get('metrics', {})

                field_fcp_raw = field_metrics.get('FIRST_CONTENTFUL_PAINT_MS', {}).get('percentile')
                field_lcp_raw = field_metrics.get('LARGEST_CONTENTFUL_PAINT_MS', {}).get('percentile')
                field_cls_raw = field_metrics.get('CUMULATIVE_LAYOUT_SHIFT_SCORE', {}).get('percentile')
                field_inp_raw = field_metrics.get('INTERACTION_TO_NEXT_PAINT_MS', {}).get('percentile')
                field_ttfb_raw = field_metrics.get('EXPERIMENTAL_TIME_TO_FIRST_BYTE', {}).get('percentile')

                report = PageSpeedReport.objects.create(
                    website=website,
                    strategy=strategy.lower(),
                    performance_score=perf_score,
                    accessibility_score=access_score,
                    best_practices_score=bp_score,
                    seo_score=seo_score,
                    first_contentful_paint=fcp,
                    largest_contentful_paint=lcp,
                    total_blocking_time=tbt,
                    cumulative_layout_shift=cls,
                    speed_index=speed_idx,
                    interaction_to_next_paint=inp,
                    time_to_first_byte=ttfb,
                    field_fcp=field_fcp_raw / 1000.0 if field_fcp_raw else None,
                    field_lcp=field_lcp_raw / 1000.0 if field_lcp_raw else None,
                    field_cls=field_cls_raw / 100.0 if field_cls_raw else None,
                    field_inp=field_inp_raw if field_inp_raw else None,
                    field_ttfb=field_ttfb_raw / 1000.0 if field_ttfb_raw else None,
                    status='success'
                )

                self.stdout.write(self.style.SUCCESS(f"  -> Success! Performance: {perf_score}"))

                # --- ALERT ENGINE ---
                if report.performance_score < website.performance_threshold:
                    recent_alert = AlertLog.objects.filter(
                        website=website,
                        alert_type='threshold_breach',
                        created_at__gte=timezone.now() - timedelta(minutes=1440)
                    ).exists()

                    if not recent_alert:
                        subject = f'ALERT: PageSpeed dropped to {report.performance_score} for {website.name}'
                        message = f'Automated Audit: The score for {website.url} has dropped to {report.performance_score}.'
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['your_team_email@example.com'])
                        
                        AlertLog.objects.create(
                            website=website, report=report, alert_type='threshold_breach',
                            score_at_alert=report.performance_score, sent_to='your_team_email@example.com',
                            subject=subject, delivered=True
                        )
                        self.stdout.write(self.style.WARNING(f"  -> WARNING EMAIL DISPATCHED for {website.url}"))

            except requests.exceptions.RequestException as e:
                PageSpeedReport.objects.create(website=website, strategy=strategy.lower(), status='failed', error_message=str(e))
                self.stdout.write(self.style.ERROR(f"  -> FAILED API Call: {str(e)}"))

            # Be a good citizen to Google's API: sleep for 1.5 seconds between audits so you don't get rate-limited
            time.sleep(1.5)

        self.stdout.write(self.style.SUCCESS("\nAll automated audits completed successfully!"))