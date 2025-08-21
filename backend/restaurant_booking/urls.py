# restaurant_booking/urls.py 
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from reservations import views

def redirect_to_admin(request):
    return redirect('/admin/')

urlpatterns = [
    # Simple Django admin at /admin/
    path('admin/', admin.site.urls),
    
    # ===== CORE API ENDPOINTS =====
    path('api/test/', views.api_test, name='api-test'),
    path('api/restaurant/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('api/restaurant/info/', views.restaurant_info, name='restaurant-info'),
    path('api/timeslots/', views.TimeSlotListView.as_view(), name='timeslot-list'),
    
    # ===== RESERVATION ENDPOINTS =====
    path('api/reservations/', views.ReservationListView.as_view(), name='reservation-list'),
    path('api/reservations/create/', views.ReservationCreateView.as_view(), name='reservation-create'),
    path('api/reservations/<int:pk>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    path('api/reservations/<int:reservation_id>/update-status/', views.update_reservation_status, name='update-reservation-status'),
    
    # ===== AVAILABILITY CHECKING ENDPOINTS =====
    path('api/availability/', views.check_availability_by_date, name='check-availability-by-date'),
    path('api/check-availability/', views.check_availability, name='check-availability'),
    
    # ===== SPECIAL DATES API =====
    path('api/special-dates/', views.special_dates_list, name='special-dates-list'),
    
    # ===== EMAIL VERIFICATION ENDPOINTS =====
    path('api/verify-email-exists/', views.verify_email_exists, name='verify-email-exists'),
    path('api/verify-email-lightweight/', views.verify_email_lightweight, name='verify-email-lightweight'),
    path('api/verify-emails-bulk/', views.verify_emails_bulk, name='verify-emails-bulk'),
    
    # ===== 🆕 EMAIL TRACKING ENDPOINTS =====
    path('track/<uuid:token>/', views.email_tracking_view, name='email_tracking'),
    path('track/<uuid:token>/<str:action>/', views.email_tracking_view, name='email_tracking_action'),
    path('api/email-stats/', views.email_tracking_stats, name='email_tracking_stats'),
    
    # ===== 🆕 NOTIFICATION MANAGEMENT ENDPOINTS =====
    path('api/notifications/', views.notification_list, name='notification_list'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # ===== 🆕 EMAIL ANALYTICS ENDPOINTS =====
    path('api/email-analytics/', views.email_analytics_summary, name='email_analytics_summary'),
    path('api/email-tracking/<int:notification_id>/', views.email_tracking_details, name='email_tracking_details'),
    
    # ===== DASHBOARD API ENDPOINTS =====
    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/api/metrics/', views.dashboard_api_metrics, name='dashboard_api_metrics'),
    path('dashboard/api/recent/', views.dashboard_api_recent, name='dashboard_api_recent'),
    
    # ===== 🆕 UTILITY ENDPOINTS =====
    path('api/test-email/', views.test_email_tracking, name='test_email_tracking'),
    path('api/cleanup/', views.cleanup_old_data, name='cleanup_old_data'),
    
    # ===== 🆕 EMAIL DEBUG ENDPOINTS =====
    path('api/debug/gmail-basic/', views.test_gmail_basic, name='test_gmail_basic'),
    path('api/debug/email-utils/', views.test_email_utils_function, name='test_email_utils'),
    path('api/debug/tracking-url/', views.test_tracking_url_generation, name='test_tracking_url'),
    path('api/debug/full-flow/', views.test_full_email_flow, name='test_full_email_flow'),
    path('api/debug/settings/', views.debug_email_settings, name='debug_email_settings'),
    path('api/debug/failed-emails/', views.check_notifications_with_failed_emails, name='check_failed_emails'),
    path('api/debug/quick-gmail/', views.quick_gmail_test, name='quick_gmail_test'),
    
    # ===== DEBUG ENDPOINTS =====
    path('api/timezone-debug/', views.timezone_debug, name='timezone-debug'),
    
    # ===== DASHBOARD REDIRECTS =====
    path('dashboard/', redirect_to_admin),
    path('tableau-de-bord/', redirect_to_admin),
    path('', redirect_to_admin),
]