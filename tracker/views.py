import requests
from datetime import timedelta 
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Website, PageSpeedReport, AlertLog
from .tasks import run_audit_task


# run audit and save to MySQL
def run_audit_view(request):
    if request.method == 'POST':
        target_url = request.POST.get('url', '').strip()
        #auto correct missing protocols to prevent api errors
        if target_url and not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
            
        # Remove trailing slash to prevent duplicates (e.g. example.com vs example.com/)
        if target_url.endswith('/'):
            target_url = target_url[:-1]

        # fetch existing website or create new parent record
        website, created = Website.objects.get_or_create(
            url=target_url,
            defaults={'name': target_url}
        )

        # Dispatch background tasks
        run_audit_task.delay(website.id, 'desktop')
        run_audit_task.delay(website.id, 'mobile')

        selected_strategy = request.POST.get('strategy', 'desktop')
        
        # Remove the 'Audit queued' message because tasks now run synchronously for local demo
        return redirect(f"/?url={target_url}&strategy={selected_strategy}")

    # GET REQUEST: RENDER DASHBOARD & LATEST DATA
    context = {}
    
    # Provide all websites for the frontend dropdown menu
    context['websites'] = Website.objects.all()
    # Provide all reports for the exact history lookup dropdown
    context['all_reports'] = PageSpeedReport.objects.select_related('website').order_by('-fetched_at')[:100]
    
    # If a user is viewing a specific site (e.g., ?url=https://example.com)
    selected_url = request.GET.get('url')
    # Use the strategy requested by the UI, default to desktop
    view_strategy = request.GET.get('strategy', 'desktop')
    # Use report_id if a specific history item was selected
    report_id = request.GET.get('report_id')

    if report_id:
        try:
            latest_report = PageSpeedReport.objects.get(id=report_id)
            website = latest_report.website
            view_strategy = latest_report.strategy
            
            context['latest_report'] = latest_report
            context['selected_website'] = website
            context['current_strategy'] = view_strategy
            # Pre-build ordered score list for the template ring loop
            context['score_items'] = [
                ('Performance', latest_report.performance_score),
                ('Accessibility', latest_report.accessibility_score),
                ('Best Practices', latest_report.best_practices_score),
                ('SEO', latest_report.seo_score),
            ]
            
            history = PageSpeedReport.objects.filter(
                website=website, 
                strategy=view_strategy
            ).order_by('-fetched_at')[:20]
            context['history'] = history
        except PageSpeedReport.DoesNotExist:
            context['error'] = "Specific report not found."
            
    elif selected_url:
        try:
            website = Website.objects.get(url=selected_url)
            
            # Check for the absolute newest report for this website/strategy, regardless of success
            try:
                latest_run = PageSpeedReport.objects.filter(website=website, strategy=view_strategy).latest('fetched_at')
                
                if latest_run.status == 'success':
                    context['latest_report'] = latest_run
                    context['selected_website'] = website
                    context['view_strategy'] = view_strategy
                    # Pre-build ordered score list for the template ring loop
                    context['score_items'] = [
                        ('Performance', latest_run.performance_score),
                        ('Accessibility', latest_run.accessibility_score),
                        ('Best Practices', latest_run.best_practices_score),
                        ('SEO', latest_run.seo_score),
                    ]
                else:
                    context['error'] = f"The analysis for {view_strategy} failed. Please try again."
                    context['selected_website'] = website
                    context['view_strategy'] = view_strategy
                    
            except PageSpeedReport.DoesNotExist:
                context['error'] = f"No {view_strategy} audits found for this URL yet."
                context['selected_website'] = website
                context['view_strategy'] = view_strategy

            # Pull historical reports for the table
            history = PageSpeedReport.objects.filter(
                website=website, 
                strategy=view_strategy
            ).order_by('-fetched_at')[:20]
            context['history'] = history
            
        except Website.DoesNotExist:
            context['error'] = "Website not found in the database."

    return render(request, 'dashboard.html', context)



# JSON API ENDPOINT FOR THE FRONTEND "RECENTLY VISITED" LIST
def api_recent_websites(request):
    """
    Returns the list of websites from MySQL, newest-audited first.
    Optional date range via query params: ?start=YYYY-MM-DD&end=YYYY-MM-DD
    Each website appears once, using its most recent successful audit in range.
    """
    start = request.GET.get('start')  # e.g. "2026-06-01" (optional)
    end = request.GET.get('end')      # e.g. "2026-06-17" (optional)

    # Start with every successful audit
    reports = PageSpeedReport.objects.filter(status='success')

    # Narrow to the requested date range if the frontend sent one
    try:
        if start:
            reports = reports.filter(fetched_at__date__gte=start)
        if end:
            reports = reports.filter(fetched_at__date__lte=end)
    except (ValueError, ValidationError):
        return JsonResponse({'error': 'Dates must look like YYYY-MM-DD'}, status=400)

    # Walk newest -> oldest; the first time we see a website is its latest audit.
    # select_related pulls the Website in the same query (avoids extra DB hits).
    seen = {}
    for report in reports.select_related('website').order_by('-fetched_at'):
        wid = report.website_id
        if wid not in seen:
            seen[wid] = {
                'id': report.website.id,
                'url': report.website.url,
                'name': report.website.name or report.website.url,
                'last_visited': report.fetched_at.strftime('%b %d, %Y %H:%M'),
                'latest_score': report.performance_score,
            }

    return JsonResponse({
        'count': len(seen),
        'websites': list(seen.values()),  # already in newest-first order
    })


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
            data['labels'].append(report.fetched_at.strftime('%b %d, %H:%M'))
            data['scores'].append(report.performance_score)
            
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# JSON API for the history search bar — returns matching reports by URL
def api_reports_search(request):
    q = request.GET.get('q', '').strip()
    reports = PageSpeedReport.objects.select_related('website').order_by('-fetched_at')
    if q:
        reports = reports.filter(website__url__icontains=q)
    reports = reports[:60]
    results = []
    for r in reports:
        results.append({
            'id': r.id,
            'website_id': r.website_id,
            'url': r.website.url,
            'strategy': r.strategy,
            'performance_score': r.performance_score,
            'status': r.status,
            'fetched_at': r.fetched_at.strftime('%b %d, %Y, %I:%M:%S %p'),
        })
    return JsonResponse({'results': results})


# DELETE A WEBSITE AND ITS ENTIRE AUDIT HISTORY (from the History Log delete button)
@require_POST
def delete_website(request, website_id):
    """
    Permanently delete one website and ALL of its audit reports from MySQL.
    Deleting the Website cascades to its PageSpeedReports and AlertLogs, so the
    URL also disappears from the History Log and the History Search dropdown.
    POST-only so it can't be triggered by accident (e.g. a stray GET/link).
    """
    try:
        website = Website.objects.get(id=website_id)
    except Website.DoesNotExist:
        messages.error(request, "That site was already removed.")
        return redirect('run_audit')

    url = website.url
    website.delete()  # CASCADE removes its reports + alerts too
    messages.success(request, f"Deleted {url} and all of its audit history.")
    return redirect('run_audit')


# Renders the dedicated full-page history explorer
def history_page(request):
    return render(request, 'history.html', {})


# Full history search API: filter by URL text, date range, and strategy
def api_history_search(request):
    q        = request.GET.get('q', '').strip()
    start    = request.GET.get('start', '').strip()
    end      = request.GET.get('end', '').strip()
    strategy = request.GET.get('strategy', '').strip().lower()

    reports = PageSpeedReport.objects.select_related('website').order_by('-fetched_at')

    if q:
        reports = reports.filter(website__url__icontains=q)
    if strategy in ('desktop', 'mobile'):
        reports = reports.filter(strategy=strategy)
    try:
        if start:
            reports = reports.filter(fetched_at__date__gte=start)
        if end:
            reports = reports.filter(fetched_at__date__lte=end)
    except (ValueError, ValidationError):
        return JsonResponse({'error': 'Dates must be YYYY-MM-DD'}, status=400)

    reports = reports[:200]
    results = []
    for r in reports:
        results.append({
            'id':             r.id,
            'url':            r.website.url,
            'strategy':       r.strategy,
            'performance':    r.performance_score,
            'accessibility':  r.accessibility_score,
            'best_practices': r.best_practices_score,
            'seo':            r.seo_score,
            'status':         r.status,
            'fetched_at':     r.fetched_at.strftime('%b %d, %Y, %I:%M:%S %p'),
        })
    return JsonResponse({'count': len(results), 'results': results})


# DELETE a single PageSpeedReport from the DB
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_history_delete(request, report_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed. Use DELETE.'}, status=405)
    try:
        report = PageSpeedReport.objects.get(id=report_id)
        report.delete()
        return JsonResponse({'deleted': True, 'id': report_id})
    except PageSpeedReport.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
