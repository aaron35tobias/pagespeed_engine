import requests
from celery import shared_task
from django.conf import settings
from tracker.models import Website, PageSpeedReport

@shared_task
def run_audit_task(website_id, strategy):
    try:
        website = Website.objects.get(id=website_id)
    except Website.DoesNotExist:
        return False, "Website not found", None

    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        'url': website.url,
        'key': settings.GOOGLE_API_KEY,
        'strategy': strategy.upper(),
        'category': ['performance', 'accessibility', 'best-practices', 'seo']
    }

    import time
    time.sleep(5) # Prevent rate limiting 500 errors

    try:
        response = requests.get(api_url, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        
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

        f_fcp = field_fcp_raw / 1000.0 if field_fcp_raw else None
        f_lcp = field_lcp_raw / 1000.0 if field_lcp_raw else None
        f_cls = field_cls_raw / 100.0 if field_cls_raw else None
        f_inp = field_inp_raw if field_inp_raw else None
        f_ttfb = field_ttfb_raw / 1000.0 if field_ttfb_raw else None

        report = PageSpeedReport.objects.create(
            website=website,
            strategy=strategy,
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
            field_fcp=f_fcp,
            field_lcp=f_lcp,
            field_cls=f_cls,
            field_inp=f_inp,
            field_ttfb=f_ttfb,
            status='success'
        )
        return True, perf_score, report.id

    except requests.exceptions.RequestException as e:
        error_msg = str(e).replace(settings.GOOGLE_API_KEY, 'HIDDEN_API_KEY')
        report = PageSpeedReport.objects.create(
            website=website,
            strategy=strategy,
            status='failed',
            error_message=error_msg
        )
        return False, "Google PageSpeed API Error", report.id

@shared_task
def schedule_all_audits():
    websites = Website.objects.filter(is_active=True)
    for website in websites:
        run_audit_task.delay(website.id, 'desktop')
        run_audit_task.delay(website.id, 'mobile')
