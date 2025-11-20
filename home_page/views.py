from django.shortcuts import render
from issues.models import Issue

def home_view(request):
    issues_in_progress = Issue.objects.filter(status=Issue.STATUS_IN_PROGRESS).count()

    issues_resolved = Issue.objects.filter(status=Issue.STATUS_RESOLVED).count()
    
    context = {
        'issues_in_progress': issues_in_progress,
        'issues_resolved': issues_resolved,
    }
    
    return render(request, 'home_page/home.html', context)

def about_site(request):
    return render(request, 'about_site.html')