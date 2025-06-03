from django.urls import path
from . import views

urlpatterns = [
    # APIs pour les clients (Frontend React)
    path('restaurant/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('timeslots/', views.TimeSlotListView.as_view(), name='timeslot-list'),
    path('reservations/create/', views.ReservationCreateView.as_view(), name='reservation-create'),
    path('availability/', views.check_availability, name='check-availability'),
    
    # APIs pour l'admin
    path('admin/reservations/', views.ReservationListView.as_view(), name='admin-reservation-list'),
    path('admin/reservations/<int:pk>/', views.ReservationDetailView.as_view(), name='admin-reservation-detail'),
    path('admin/dashboard/', views.dashboard_stats, name='admin-dashboard'),
    path('admin/reservations/<int:reservation_id>/status/', views.update_reservation_status, name='update-reservation-status'),
]