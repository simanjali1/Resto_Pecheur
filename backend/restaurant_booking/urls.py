# restaurant_booking/urls.py - COMPLETE WITH MISSING ENDPOINT
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from reservations import views

def redirect_to_admin_dashboard(request):
    """Redirect everything to admin with sidebar"""
    return redirect('/admin/')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Redirect ALL dashboard access to admin with sidebar
    path('dashboard/', redirect_to_admin_dashboard),
    path('tableau-de-bord/', redirect_to_admin_dashboard),
    
    # ===== API ENDPOINTS FOR FRONTEND =====
    # Test endpoint
    path('api/test/', views.api_test, name='api-test'),
    
    # Core endpoints that your frontend calls
    path('api/restaurant/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('api/timeslots/', views.TimeSlotListView.as_view(), name='timeslot-list'),
    path('api/reservations/', views.ReservationListView.as_view(), name='reservation-list'),
    path('api/reservations/create/', views.ReservationCreateView.as_view(), name='reservation-create'),
    path('api/reservations/<int:pk>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    
    # ===== CRITICAL: ADD THIS MISSING ENDPOINT =====
    path('api/availability/', views.check_availability_by_date, name='check-availability-by-date'),
    
    # Legacy endpoints
    path('api/check-availability/', views.check_availability, name='check-availability'),
    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('api/reservations/<int:reservation_id>/update-status/', views.update_reservation_status, name='update-reservation-status'),
    
    # Dashboard API for metrics (keep this for AJAX calls)
    path('dashboard/api/metrics/', views.dashboard_api_metrics, name='dashboard_api_metrics'),
    path('dashboard/api/recent/', views.dashboard_api_recent, name='dashboard_api_recent'),
    
    # Root redirect to admin dashboard
    path('', redirect_to_admin_dashboard),
]