import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from .models import Website, PageSpeedReport

def run_audit_view(request):
    if request.method == 'POST':
        target_url = request.POST.get('url', '').strip()
        if target_url and not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
            
        strategy = request.POST.get('strategy', 'desktop')
        
        # Get or Create the Website parent record
        website, created = Website.objects.get_or_create(
            url=target_url,
            defaults={'name': target_url} # Default name if it's new
        )
        
        # Setup the API Call (Note the multiple 'category' params)
        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            'url': target_url,
            'key': settings.GOOGLE_API_KEY,
            'strategy': strategy.upper(), # Google expects 'DESKTOP' or 'MOBILE'
            'category': ['performance', 'accessibility', 'best-practices', 'seo']
        }
        
        try:
            # Ping the API
            response = requests.get(api_url, params=params)
            response.raise_for_status() # Raise exception for bad status codes
            data = response.json()
            
            # Parse the nested JSON payload [LAB DATA (Lighthouse)]
            lighthouse = data.get('lighthouseResult', {})
            categories = lighthouse.get('categories', {})
            audits = lighthouse.get('audits', {})
            
            # Extract main scores (API returns 0.0 to 1.0, so multiply by 100 to get out of 100%)
            perf_score = int(categories.get('performance', {}).get('score', 0) * 100)
            access_score = int(categories.get('accessibility', {}).get('score', 0) * 100)
            bp_score = int(categories.get('best-practices', {}).get('score', 0) * 100)
            seo_score = int(categories.get('seo', {}).get('score', 0) * 100)
            
            # Extract Core Web Vitals (Converting ms to seconds where appropriate for DB schema)
            fcp = audits.get('first-contentful-paint', {}).get('numericValue', 0) / 1000.0 # divide by 1000 to make it in sec 
            lcp = audits.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000.0 # make it sec
            tbt = audits.get('total-blocking-time', {}).get('numericValue', 0) # Keep in ms
            cls = audits.get('cumulative-layout-shift', {}).get('numericValue', 0) # Unitless
            speed_idx = audits.get('speed-index', {}).get('numericValue', 0) / 1000.0 # sec
            inp = audits.get('interaction-to-next-paint', {}).get('numericValue', 0) # ms
            ttfb = audits.get('server-response-time', {}).get('numericValue', 0) / 1000.0 #sec
            
            # Parse FIELD DATA (CrUX)
            loading_experience = data.get('loadingExperience', {})
            field_metrics = loading_experience.get('metrics', {})

            field_fcp_raw = field_metrics.get('FIRST_CONTENTFUL_PAINT_MS', {}).get('percentile')
            field_lcp_raw = field_metrics.get('LARGEST_CONTENTFUL_PAINT_MS', {}).get('percentile')
            field_cls_raw = field_metrics.get('CUMULATIVE_LAYOUT_SHIFT_SCORE', {}).get('percentile')
            field_inp_raw = field_metrics.get('INTERACTION_TO_NEXT_PAINT_MS', {}).get('percentile')
            field_ttfb_raw = field_metrics.get('EXPERIMENTAL_TIME_TO_FIRST_BYTE', {}).get('percentile')

            # Safely convert units only if the data exists
            f_fcp = field_fcp_raw / 1000.0 if field_fcp_raw else None
            f_lcp = field_lcp_raw / 1000.0 if field_lcp_raw else None
            f_cls = field_cls_raw / 100.0 if field_cls_raw else None
            f_inp = field_inp_raw if field_inp_raw else None
            f_ttfb = field_ttfb_raw / 1000.0 if field_ttfb_raw else None

            # 5. Save to MySQL via Django ORM
            report = PageSpeedReport.objects.create(
                website=website,
                strategy=strategy,
                performance_score=perf_score,
                accessibility_score=access_score,
                best_practices_score=bp_score,
                seo_score=seo_score,
                # Lab Data
                first_contentful_paint=fcp,
                largest_contentful_paint=lcp,
                total_blocking_time=tbt,
                cumulative_layout_shift=cls,
                speed_index=speed_idx,
                interaction_to_next_paint=inp,
                time_to_first_byte=ttfb,
                # Field Data
                field_fcp=f_fcp,
                field_lcp=f_lcp,
                field_cls=f_cls,
                field_inp=f_inp,
                field_ttfb=f_ttfb,
                status='success'
            )
            
            messages.success(request, f"Audit complete for {target_url}! Performance: {perf_score}, SEO: {seo_score}. Saved to MySQL.")
            
        except requests.exceptions.RequestException as e:
            # Handle API errors cleanly and log to database
            PageSpeedReport.objects.create(
                website=website,
                strategy=strategy,
                status='failed',
                error_message=str(e)
            )
            messages.error(request, f"Audit failed: {str(e)}")

        # Redirect back to the form
        return redirect('run_audit')
        
    # GET request just renders the blank form
    return render(request, 'dashboard.html')