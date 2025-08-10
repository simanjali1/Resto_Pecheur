# restaurant_booking/urls.py - COMPLETE VERSION WITH ALL FEATURES
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from reservations import views

def redirect_to_admin(request):
    return redirect('/admin/')

urlpatterns = [
    # Simple Django admin at /admin/
    path('admin/', admin.site.urls),
    
    # Core API endpoints
    path('api/test/', views.api_test, name='api-test'),
    path('api/restaurant/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('api/restaurant/info/', views.restaurant_info, name='restaurant-info'),
    path('api/timeslots/', views.TimeSlotListView.as_view(), name='timeslot-list'),
    
    # Reservation endpoints
    path('api/reservations/', views.ReservationListView.as_view(), name='reservation-list'),
    path('api/reservations/create/', views.ReservationCreateView.as_view(), name='reservation-create'),
    path('api/reservations/<int:pk>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    path('api/reservations/<int:reservation_id>/update-status/', views.update_reservation_status, name='update-reservation-status'),
    
    # Availability checking endpoints
    path('api/availability/', views.check_availability_by_date, name='check-availability-by-date'),
    path('api/check-availability/', views.check_availability, name='check-availability'),
    
    # ✅ SPECIAL DATES API - MISSING FROM YOUR CONFIG
    path('api/special-dates/', views.special_dates_list, name='special-dates-list'),
    
    # Email verification endpoints
    path('api/verify-email-exists/', views.verify_email_exists, name='verify-email-exists'),
    path('api/verify-email-lightweight/', views.verify_email_lightweight, name='verify-email-lightweight'),
    path('api/verify-emails-bulk/', views.verify_emails_bulk, name='verify-emails-bulk'),
    
    # Dashboard API endpoints
    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/api/metrics/', views.dashboard_api_metrics, name='dashboard_api_metrics'),
    path('dashboard/api/recent/', views.dashboard_api_recent, name='dashboard_api_recent'),
    
    # Debug endpoints
    path('api/timezone-debug/', views.timezone_debug, name='timezone-debug'),
    
    # Dashboard redirects to admin
    path('dashboard/', redirect_to_admin),
    path('tableau-de-bord/', redirect_to_admin),
    path('', redirect_to_admin),
]