import requests
import time 
from datetime import timedelta 
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail 
from django.utils import timezone 
from .models import Website, PageSpeedReport, AlertLog 


# run audit and save to MySQL
def run_audit_view(request):
    if request.method == 'POST':
        target_url = request.POST.get('url', '').strip()
        #auto correct missing protocols to prevent api errors
        if target_url and not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        # default to desktop if the frontend form doesn't send a strategy    
        strategy = request.POST.get('strategy', 'desktop')
        
        # fetch exisiting website or create new parent record
        website, created = Website.objects.get_or_create(
            url=target_url,
            defaults={'name': target_url} # Default name if it's new
        )
        
        # configure google pagespeed api request parameters
        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        # We will track if at least one audit succeeded to show a success message
        success_count = 0

        # Loop to capture BOTH Desktop and Mobile data on every manual submit
        for strategy in ['desktop', 'mobile']:
            params = {
                'url': target_url,
                'key': settings.GOOGLE_API_KEY,
                'strategy': strategy.upper(), 
                'category': ['performance', 'accessibility', 'best-practices', 'seo']
            }
        
            # FIX: Everything from here down is now indented inside the loop!
            try:
                # execute synchronous HTTP request to google
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

                # Save to MySQL via Django ORM
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
                
                success_count += 1

                # ALERT ENGINE LOGIC
                if report.performance_score < website.performance_threshold:
                    # Check for recent alerts in last 24hrs to prevent spamming
                    recent_alert = AlertLog.objects.filter(
                        website=website,
                        alert_type='threshold_breach',
                        created_at__gte=timezone.now() - timedelta(minutes=1440) # 24 hours cooldown
                    ).exists()

                    # dispatch email only if 24hrs cooldown has passed
                    if not recent_alert:
                        subject = f'{strategy.upper()} PageSpeed dropped to {report.performance_score} for {website.name}'
                        message = f'The {strategy.upper()} performance score for {website.url} has dropped to {report.performance_score}.'
                        from_email = settings.DEFAULT_FROM_EMAIL
                        recipient_list = ['your_team_email@example.com'] # Replace with your notification email

                        send_mail(subject, message, from_email, recipient_list)
                        # Log the alert to start the 24-hour cooldown timer
                        AlertLog.objects.create(
                            website=website,
                            report=report,
                            alert_type='threshold_breach',
                            score_at_alert=report.performance_score,
                            sent_to=recipient_list[0],
                            subject=subject,
                            delivered=True # Assuming successful delivery for now
                        )
                
                messages.success(request, f"{strategy.upper()} Audit complete for {target_url}! Performance: {perf_score}. Saved to MySQL.")
                
            except requests.exceptions.RequestException as e:
                # Log the API failure securely without crashing the server
                PageSpeedReport.objects.create(
                    website=website,
                    strategy=strategy,
                    status='failed',
                    error_message=str(e)
                )
                messages.error(request, f"{strategy.upper()} Audit failed: {str(e)}")

            # Pause briefly between the Desktop and Mobile API calls to avoid rate limits
            time.sleep(1.5)

        # Redirect to the specific URL's dashboard after the loop finishes
        if success_count > 0:
             return redirect(f"/?url={target_url}")
        else:
             return redirect('run_audit') 


    # GET REQUEST: RENDER DASHBOARD & LATEST DATA
    context = {}
    
    # Provide all websites for the frontend dropdown menu
    context['websites'] = Website.objects.all()
    
    # If a user is viewing a specific site (e.g., ?url=https://example.com)
    # If a user is viewing a specific site (e.g., ?url=https://example.com)
    selected_url = request.GET.get('url')
    # Use the strategy requested by the UI, default to desktop
    view_strategy = request.GET.get('strategy', 'desktop')

    if selected_url:
        try:
            website = Website.objects.get(url=selected_url)
            # Pull the absolute newest successful report for this specific website AND strategy
            latest_report = PageSpeedReport.objects.filter(
                website=website, 
                strategy=view_strategy,
                status='success'
            ).latest('fetched_at')
            
            context['latest_report'] = latest_report
            context['selected_website'] = website
            context['current_strategy'] = view_strategy
            
        except Website.DoesNotExist:
            context['error'] = "Website not found in the database."
        except PageSpeedReport.DoesNotExist:
            context['error'] = f"No successful {view_strategy} audits found for this URL yet."
            # Still pass the website so the frontend knows what was searched
            context['selected_website'] = Website.objects.get(url=selected_url) 

    return render(request, 'dashboard.html', context)



# JSON API ENDPOINT FOR CHART.JS
def api_website_history(request, website_id):
    """
    Returns a JSON array of the last 30 performance scores for Chart.js
    """
    # Accept the strategy from the frontend request, default to desktop
    strategy = request.GET.get('strategy', 'desktop')
    
    try:
        # Grab the last 30 successful reports for this specific website AND strategy
        reports = PageSpeedReport.objects.filter(
            website_id=website_id, 
            strategy=strategy,
            status='success'
        ).order_by('-fetched_at')[:30]
        
        # Reverse the list so it is chronological (oldest to newest) for the chart
        reports = reversed(list(reports))

        data = {
            'labels': [], # X-axis (Dates) strings (e.g., "Jun 16, 14:30")
            'scores': []  # Y-axis (Performance Scores) integers
        }
        
        for report in reports:
            # Prefix the label with PC or Mob to indicate strategy on the graph lines
            label_prefix = "PC" if report.strategy == "desktop" else "Mob"
            data['labels'].append(f"{label_prefix} - {report.fetched_at.strftime('%b %d, %H:%M')}")
            data['scores'].append(report.performance_score)
            
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)