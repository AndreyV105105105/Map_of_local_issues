from django.urls import path

from . import views

app_name = 'issues'

urlpatterns = [
    path('api/geocode/', views.GeocodeAPIView.as_view(), name='geocode_api'),
    path('api/search-address/', views.SearchAddressAPIView.as_view(), name='search_address_api'),
    path('api/reverse-geocode/', views.ReverseGeocodeAPIView.as_view(), name='reverse_geocode_api'),
    path('map/', views.map_view, name='map'),
    path('map/geojson/', views.get_issues_geojson, name='map_geojson'),
    path('create/', views.create_issue, name='create_issue'),
    path('update-status/<int:issue_id>/', views.update_issue_status, name='update_issue_status'),
    path('<int:issue_id>/delete/', views.delete_issue, name='delete_issue'),
    path('<int:pk>/', views.issue_detail, name='issue_detail'),
    path('<int:issue_id>/vote/', views.vote_issue, name='vote_issue'),
    path('issues/<int:pk>/', views.issue_detail, name='issue_detail'),
]
