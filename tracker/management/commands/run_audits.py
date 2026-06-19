import requests
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import Website, PageSpeedReport

class Command(BaseCommand):
    help = 'Loops through all active websites and runs both Desktop and Mobile PageSpeed audits.'

    def handle(self, *args, **kwargs):
        # Only scan websites that are marked active
        websites = Website.objects.filter(is_active=True)
        
        if not websites:
            self.stdout.write(self.style.WARNING("No websites found in the database. Exiting."))
            return

        self.stdout.write(self.style.NOTICE(f"Starting automated audits for {websites.count()} websites..."))

        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

        for website in websites:
            self.stdout.write(f"\nTarget: {website.url}")
            
            # Using 'loop_strategy' to guarantee no variable overwriting occurs
            for loop_strategy in ['desktop', 'mobile']:
                self.stdout.write(f" -> Running {loop_strategy.upper()} audit...")
                
                params = {
                    'url': website.url,
                    'key': settings.GOOGLE_API_KEY,
                    'strategy': loop_strategy.upper(),
                    'category': ['performance', 'accessibility', 'best-practices', 'seo']
                }

                try:
                    response = requests.get(api_url, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    # EXTRACT DATA
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
                        strategy=loop_strategy, # Safely saves exactly what the loop is on
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

                    self.stdout.write(self.style.SUCCESS(f"    [OK] {loop_strategy.upper()} score: {perf_score}"))
                    # Alert signals fire automatically via post_save in signals.py

                except requests.exceptions.RequestException as e:
                    PageSpeedReport.objects.create(website=website, strategy=loop_strategy, status='failed', error_message=str(e))
                    self.stdout.write(self.style.ERROR(f"    [X] FAILED API Call: {str(e)}"))

                time.sleep(1.5)

        self.stdout.write(self.style.SUCCESS("\nAll automated audits completed successfully!"))