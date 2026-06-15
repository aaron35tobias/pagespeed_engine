import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from .models import Website, PageSpeedReport

def run_audit_view(request):
    if request.method == 'POST':
        target_url = request.POST.get('url')
        strategy = request.POST.get('strategy', 'desktop')
        
        # 1. Get or Create the Website parent record
        website, created = Website.objects.get_or_create(
            url=target_url,
            defaults={'name': target_url} # Default name if it's new
        )
        
        # 2. Setup the API Call (Note the multiple 'category' params)
        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            'url': target_url,
            'key': settings.GOOGLE_API_KEY,
            'strategy': strategy.upper(), # Google expects 'DESKTOP' or 'MOBILE'
            'category': ['performance', 'accessibility', 'best-practices', 'seo']
        }
        
        try:
            # 3. Ping the API
            response = requests.get(api_url, params=params)
            response.raise_for_status() # Raise exception for bad status codes
            data = response.json()
            
            # 4. Parse the nested JSON payload
            lighthouse = data.get('lighthouseResult', {})
            categories = lighthouse.get('categories', {})
            audits = lighthouse.get('audits', {})
            
            # Extract main scores (API returns 0.0 to 1.0, so multiply by 100)
            perf_score = int(categories.get('performance', {}).get('score', 0) * 100)
            access_score = int(categories.get('accessibility', {}).get('score', 0) * 100)
            bp_score = int(categories.get('best-practices', {}).get('score', 0) * 100)
            seo_score = int(categories.get('seo', {}).get('score', 0) * 100)
            
            # Extract Core Web Vitals (Converting ms to seconds where appropriate for your DB schema)
            # FCP and LCP usually come in milliseconds, so we divide by 1000
            fcp = audits.get('first-contentful-paint', {}).get('numericValue', 0) / 1000.0
            lcp = audits.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000.0
            tbt = audits.get('total-blocking-time', {}).get('numericValue', 0) # Keep in ms
            cls = audits.get('cumulative-layout-shift', {}).get('numericValue', 0) # Unitless
            speed_idx = audits.get('speed-index', {}).get('numericValue', 0) / 1000.0
            inp = audits.get('interaction-to-next-paint', {}).get('numericValue', 0) # ms
            
            # 5. Save to MySQL via Django ORM
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