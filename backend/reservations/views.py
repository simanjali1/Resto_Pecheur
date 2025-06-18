# reservations/views.py - COMPLETE FILE with unified dashboard
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Restaurant, Reservation, TimeSlot, SpecialDate
from .serializers import ReservationSerializer, TimeSlotSerializer, RestaurantSerializer

# ===== API VIEWS FOR FRONTEND (React) =====

class RestaurantDetailView(generics.RetrieveAPIView):
    """Get restaurant details"""
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    
    def get_object(self):
        # Return the first restaurant (assuming single restaurant)
        return Restaurant.objects.first()

class TimeSlotListView(generics.ListAPIView):
    """List all available time slots"""
    queryset = TimeSlot.objects.filter(is_active=True)
    serializer_class = TimeSlotSerializer

class ReservationCreateView(generics.CreateAPIView):
    """Create new reservation"""
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

@api_view(['GET'])
def check_availability(request):
    """Check availability for a specific date and time"""
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    
    if not date_str or not time_str:
        return Response(
            {'error': 'Date and time parameters required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        time = datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        return Response(
            {'error': 'Invalid date or time format'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get time slot
    try:
        time_slot = TimeSlot.objects.get(time=time, is_active=True)
    except TimeSlot.DoesNotExist:
        return Response(
            {'available': False, 'message': 'Time slot not available'}, 
            status=status.HTTP_200_OK
        )
    
    # Check reservations for this date and time
    existing_reservations = Reservation.objects.filter(
        date=date,
        time=time,
        status__in=['pending', 'confirmed']
    ).count()
    
    available_spots = max(0, time_slot.max_reservations - existing_reservations)
    
    return Response({
        'available': available_spots > 0,
        'available_spots': available_spots,
        'max_reservations': time_slot.max_reservations
    })

# ===== ADMIN API VIEWS =====

class ReservationListView(generics.ListAPIView):
    """List all reservations for admin"""
    queryset = Reservation.objects.all().order_by('-date', '-time')
    serializer_class = ReservationSerializer

class ReservationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete specific reservation"""
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

@api_view(['GET'])
@staff_member_required
def dashboard_stats(request):
    """Basic dashboard statistics API"""
    today = timezone.now().date()
    
    stats = {
        'total_reservations': Reservation.objects.count(),
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
        'confirmed_reservations': Reservation.objects.filter(status='confirmed').count(),
    }
    
    return JsonResponse(stats)

@api_view(['POST'])
@staff_member_required
def update_reservation_status(request, reservation_id):
    """Update reservation status"""
    try:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        new_status = request.data.get('status')
        
        if new_status in ['pending', 'confirmed', 'cancelled', 'completed']:
            reservation.status = new_status
            reservation.save()
            return JsonResponse({'success': True, 'status': new_status})
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===== UNIFIED DASHBOARD VIEWS =====

@staff_member_required
def dashboard_view(request):
    """Main unified dashboard view with all functionalities"""
    today = timezone.now().date()
    now = timezone.now()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Get restaurant instance
    restaurant = Restaurant.objects.first()
    
    # Basic metrics
    metrics = {
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'today_confirmed': Reservation.objects.filter(date=today, status='confirmed').count(),
        'today_pending': Reservation.objects.filter(date=today, status='pending').count(),
        'today_guests': Reservation.objects.filter(date=today).aggregate(
            total=Sum('number_of_guests')
        )['total'] or 0,
        
        'week_reservations': Reservation.objects.filter(date__gte=week_start).count(),
        'month_reservations': Reservation.objects.filter(date__gte=month_start).count(),
        
        'total_tables': restaurant.number_of_tables if restaurant else 20,
        'available_tables': get_available_tables_count(today, now.time()),
        
        'peak_hour': Reservation.objects.get_peak_hour_today(),
        'next_available_slot': get_next_available_slot(),
    }
    
    # Recent reservations (last 24 hours)
    recent_reservations = Reservation.objects.filter(
        created_at__gte=now - timedelta(hours=24)
    ).order_by('-created_at')[:10]
    
    # Today's schedule
    todays_schedule = Reservation.objects.filter(
        date=today
    ).order_by('time')
    
    # Alerts
    alerts = get_dashboard_alerts(today)
    
    # Chart data using manager methods
    chart_data = {
        'weekly_reservations': {
            'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'data': Reservation.objects.get_weekly_stats()
        },
        'daily_time_slots': {
            'labels': ['12:00', '13:00', '14:00', '19:00', '20:00', '21:00'],
            'data': Reservation.objects.get_hourly_stats_today()
        },
    }
    
    context = {
        'metrics': metrics,
        'recent_reservations': recent_reservations,
        'todays_schedule': todays_schedule,
        'alerts': alerts,
        'chart_data': chart_data,
    }
    
    return render(request, 'admin/unified_dashboard.html', context)

def get_available_tables_count(date, time):
    """Calculate available tables for given date and time"""
    restaurant = Restaurant.objects.first()
    if not restaurant:
        return 20
    
    # Count reservations for today
    reservations_count = Reservation.objects.filter(
        date=date,
        status__in=['confirmed', 'pending']
    ).count()
    
    return max(0, restaurant.number_of_tables - reservations_count)

def get_next_available_slot():
    """Find next available time slot"""
    now = timezone.now()
    
    # Look for available slots in the next 7 days
    for days_ahead in range(7):
        check_date = now.date() + timedelta(days=days_ahead)
        
        # Get all time slots for this date
        time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
        
        for slot in time_slots:
            reservations_count = Reservation.objects.filter(
                date=check_date,
                time=slot.time,
                status__in=['confirmed', 'pending']
            ).count()
            
            # Check against slot max reservations
            if reservations_count < slot.max_reservations:
                if days_ahead == 0:
                    return f"Aujourd'hui {slot.time.strftime('%H:%M')}"
                else:
                    return f"{check_date.strftime('%d/%m')} à {slot.time.strftime('%H:%M')}"
    
    return "Complet"

def get_dashboard_alerts(date):
    """Generate dashboard alerts"""
    alerts = []
    
    # Check for overbookings
    time_slots = TimeSlot.objects.filter(is_active=True)
    for slot in time_slots:
        reservations_count = Reservation.objects.filter(
            date=date,
            time=slot.time,
            status__in=['confirmed', 'pending']
        ).count()
        
        if reservations_count > slot.max_reservations:
            alerts.append({
                'type': 'danger',
                'icon': '🚨',
                'message': f"Surbooking à {slot.time.strftime('%H:%M')} - {reservations_count} réservations",
                'time': slot.time
            })
        elif reservations_count > (slot.max_reservations - 2):  # Near capacity
            alerts.append({
                'type': 'warning',
                'icon': '⚠️',
                'message': f"Presque complet à {slot.time.strftime('%H:%M')} - {reservations_count}/{slot.max_reservations}",
                'time': slot.time
            })
    
    # Check for large parties
    large_parties = Reservation.objects.filter(
        date=date,
        number_of_guests__gte=8
    )
    
    for party in large_parties:
        alerts.append({
            'type': 'info',
            'icon': '👥',
            'message': f"Groupe important: {party.customer_name} - {party.number_of_guests} personnes à {party.time.strftime('%H:%M')}",
            'time': party.time
        })
    
    # Check for special requests
    special_reservations = Reservation.objects.filter(
        date=date,
        special_requests__isnull=False
    ).exclude(special_requests='')
    
    for reservation in special_reservations:
        alerts.append({
            'type': 'success',
            'icon': '📝',
            'message': f"Demande spéciale: {reservation.customer_name} - {reservation.special_requests[:50]}...",
            'time': reservation.time
        })
    
    # Check for upcoming special dates
    special_dates = SpecialDate.objects.filter(
        date=date
    )
    
    for special_date in special_dates:
        if special_date.is_closed:
            alerts.append({
                'type': 'danger',
                'icon': '🚫',
                'message': f"Fermeture exceptionnelle: {special_date.reason or 'Pas de raison'}",
                'time': None
            })
        else:
            alerts.append({
                'type': 'info',
                'icon': '⏰',
                'message': f"Horaires modifiés: {special_date.reason or 'Voir détails'}",
                'time': None
            })
    
    # Sort alerts by time (put non-time alerts at the end)
    alerts.sort(key=lambda x: x.get('time') or timezone.now().time())
    
    return alerts

def get_weekly_chart_data(week_start):
    """Get reservation data for the current week"""
    data = []
    labels = []
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        count = Reservation.objects.filter(date=day).count()
        data.append(count)
        labels.append(day.strftime('%a %d'))
    
    return {
        'labels': labels,
        'data': data
    }

def get_daily_time_slots_data(date):
    """Get reservation data by time slots for today"""
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
    data = []
    labels = []
    
    for slot in time_slots:
        count = Reservation.objects.filter(
            date=date,
            time=slot.time
        ).count()
        data.append(count)
        labels.append(slot.time.strftime('%H:%M'))
    
    return {
        'labels': labels,
        'data': data
    }

def get_monthly_trends_data():
    """Get monthly reservation trends"""
    today = timezone.now().date()
    data = []
    labels = []
    
    # Get last 6 months
    for i in range(6):
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = Reservation.objects.filter(
            date__gte=month_start,
            date__lte=month_end
        ).count()
        
        data.insert(0, count)
        labels.insert(0, month_start.strftime('%b %Y'))
    
    return {
        'labels': labels,
        'data': data
    }

# API endpoints for AJAX updates
@staff_member_required
def dashboard_api_metrics(request):
    """API endpoint for real-time metrics"""
    today = timezone.now().date()
    now = timezone.now()
    
    metrics = {
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'today_guests': Reservation.objects.filter(date=today).aggregate(
            total=Sum('number_of_guests')
        )['total'] or 0,
        'available_tables': get_available_tables_count(today, now.time()),
        'pending_reservations': Reservation.objects.filter(
            date=today, 
            status='pending'
        ).count(),
    }
    
    return JsonResponse(metrics)

@staff_member_required
def dashboard_api_recent(request):
    """API endpoint for recent reservations"""
    now = timezone.now()
    recent = Reservation.objects.filter(
        created_at__gte=now - timedelta(hours=1)
    ).order_by('-created_at')[:5]
    
    data = []
    for reservation in recent:
        data.append({
            'customer_name': reservation.customer_name,
            'party_size': reservation.number_of_guests,
            'time': reservation.created_at.strftime('%H:%M'),
            'status': reservation.status
        })
    
    return JsonResponse({'recent_reservations': data})