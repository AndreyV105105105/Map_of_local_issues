from django.shortcuts import render

def home_view(request):
    return render(request, 'home_page/home.html')
def about_site(request):
    return render(request, 'about_site.html')