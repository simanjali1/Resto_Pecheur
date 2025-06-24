# reservations/views.py - COMPLETE FILE with unified dashboard
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from .models import Restaurant, Reservation, TimeSlot, SpecialDate
from .serializers import ReservationSerializer, TimeSlotSerializer, RestaurantSerializer
import json

# ===== API VIEWS FOR FRONTEND (React) =====

class RestaurantDetailView(generics.RetrieveAPIView):
    """Get restaurant details"""
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    
    def get_object(self):
        # Return the first restaurant (assuming single restaurant)
        restaurant = Restaurant.objects.first()
        if not restaurant:
            # Create default restaurant if none exists
            restaurant = Restaurant.objects.create(
                name="Resto Pêcheur",
                address="Tangier, Morocco",
                phone="+212 XX XX XX XX",
                email="contact@restopecheur.com",
                capacity=50,
                number_of_tables=20,
                opening_time="12:00",
                closing_time="23:00"
            )
        return restaurant

class TimeSlotListView(generics.ListAPIView):
    """List all available time slots"""
    serializer_class = TimeSlotSerializer
    
    def get_queryset(self):
        queryset = TimeSlot.objects.filter(is_active=True).order_by('time')
        
        # If no time slots exist, create default ones
        if not queryset.exists():
            default_slots = [
                {'time': '12:00', 'max_reservations': 10},
                {'time': '13:00', 'max_reservations': 12},
                {'time': '14:00', 'max_reservations': 10},
                {'time': '19:00', 'max_reservations': 8},
                {'time': '20:00', 'max_reservations': 10},
                {'time': '21:00', 'max_reservations': 8},
            ]
            for slot_data in default_slots:
                TimeSlot.objects.create(
                    time=slot_data['time'],
                    max_reservations=slot_data['max_reservations'],
                    is_active=True
                )
            queryset = TimeSlot.objects.filter(is_active=True).order_by('time')
        
        return queryset

class ReservationCreateView(generics.CreateAPIView):
    """Create new reservation"""
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    
    def create(self, request, *args, **kwargs):
        try:
            # Validate data
            data = request.data
            required_fields = ['customer_name', 'customer_email', 'customer_phone', 'date', 'time', 'number_of_guests']
            
            for field in required_fields:
                if field not in data or not data[field]:
                    return Response(
                        {'error': f'{field} is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check availability before creating
            date_str = data['date']
            time_str = data['time']
            guests = int(data['number_of_guests'])
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                time_obj = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                return Response(
                    {'error': 'Invalid date or time format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if time slot exists and has capacity
            try:
                time_slot = TimeSlot.objects.get(time=time_obj, is_active=True)
            except TimeSlot.DoesNotExist:
                return Response(
                    {'error': 'Selected time slot is not available'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Count existing reservations
            existing_reservations = Reservation.objects.filter(
                date=date,
                time=time_obj,
                status__in=['pending', 'confirmed']
            ).count()
            
            if existing_reservations >= time_slot.max_reservations:
                return Response(
                    {'error': 'This time slot is fully booked'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the reservation
            reservation = Reservation.objects.create(
                customer_name=data['customer_name'],
                customer_email=data['customer_email'],
                customer_phone=data['customer_phone'],
                date=date,
                time=time_obj,
                number_of_guests=guests,
                special_requests=data.get('special_requests', ''),
                status='pending'
            )
            
            return Response({
                'id': reservation.id,
                'message': 'Reservation created successfully',
                'reservation': {
                    'id': reservation.id,
                    'customer_name': reservation.customer_name,
                    'date': reservation.date.strftime('%Y-%m-%d'),
                    'time': reservation.time.strftime('%H:%M'),
                    'number_of_guests': reservation.number_of_guests,
                    'status': reservation.status
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ===== NEW: AVAILABILITY ENDPOINT THAT YOUR FRONTEND NEEDS =====
@csrf_exempt
def check_availability_by_date(request):
    """Check availability for a specific date - This is what your frontend calls"""
    if request.method == 'GET':
        try:
            date_str = request.GET.get('date')
            if not date_str:
                return JsonResponse({'error': 'Date parameter required'}, status=400)
            
            # Parse the date
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
            
            # Get all active time slots
            time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
            
            # If no time slots exist, create default ones
            if not time_slots.exists():
                default_slots = [
                    {'time': '12:00', 'max_reservations': 10},
                    {'time': '13:00', 'max_reservations': 12},
                    {'time': '14:00', 'max_reservations': 10},
                    {'time': '19:00', 'max_reservations': 8},
                    {'time': '20:00', 'max_reservations': 10},
                    {'time': '21:00', 'max_reservations': 8},
                ]
                for slot_data in default_slots:
                    TimeSlot.objects.create(
                        time=slot_data['time'],
                        max_reservations=slot_data['max_reservations'],
                        is_active=True
                    )
                time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
            
            availability_data = []
            for slot in time_slots:
                # Count existing reservations for this date and time
                existing_reservations = Reservation.objects.filter(
                    date=date,
                    time=slot.time,
                    status__in=['pending', 'confirmed']
                ).count()
                
                available_spots = slot.max_reservations - existing_reservations
                is_available = available_spots > 0
                
                availability_data.append({
                    'time': slot.time.strftime('%H:%M'),
                    'time_id': slot.id,
                    'max_reservations': slot.max_reservations,
                    'existing_reservations': existing_reservations,
                    'available_spots': max(0, available_spots),
                    'is_available': is_available
                })
            
            return JsonResponse({
                'date': date_str,
                'availability': availability_data,
                'total_slots': len(availability_data)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'GET method required'}, status=405)

@api_view(['GET'])
def check_availability(request):
    """Check availability for a specific date and time - Legacy endpoint"""
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

# ===== TEST ENDPOINT =====
@csrf_exempt
def api_test(request):
    """Simple test endpoint to verify backend connection"""
    return JsonResponse({
        'status': 'success',
        'message': 'Backend connected successfully!',
        'timestamp': timezone.now().isoformat(),
        'method': request.method
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
        
        'peak_hour': get_peak_hour_today(today),
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
    
    # Chart data
    chart_data = {
        'weekly_reservations': get_weekly_chart_data(week_start),
        'daily_time_slots': get_daily_time_slots_data(today),
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

def get_peak_hour_today(date):
    """Find the busiest hour for today"""
    peak_hour = Reservation.objects.filter(
        date=date,
        status__in=['pending', 'confirmed']
    ).values('time').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    if peak_hour and peak_hour['count'] > 0:
        return peak_hour['time'].strftime('%H:%M')
    return None

def get_next_available_slot():
    """Find next available time slot"""
    now = timezone.localtime(timezone.now())
    current_date = now.date()
    current_time = now.time()
    
    # Look for available slots in the next 7 days
    for days_ahead in range(7):
        check_date = current_date + timedelta(days=days_ahead)
        
        # Get all time slots for this date
        time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
        
        for slot in time_slots:
            # If it's today, skip past time slots
            if days_ahead == 0:
                if slot.time <= current_time:
                    continue
            
            reservations_count = Reservation.objects.filter(
                date=check_date,
                time=slot.time,
                status__in=['confirmed', 'pending']
            ).count()
            
            # Check against slot max reservations
            if reservations_count < slot.max_reservations:
                if days_ahead == 0:
                    return f"Aujourd'hui {slot.time.strftime('%H:%M')}"
                elif days_ahead == 1:
                    return f"Demain {slot.time.strftime('%H:%M')}"
                else:
                    return f"{check_date.strftime('%d/%m')} à {slot.time.strftime('%H:%M')}"
    
    return "Aucun créneau disponible cette semaine"

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