# reservations/views.py - SINGLE RESTAURANT VERSION WITH TIMEZONE FIX
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
from .models import RestaurantInfo, Reservation, TimeSlot, SpecialDate, get_restaurant_info
from .serializers import ReservationSerializer, TimeSlotSerializer, RestaurantSerializer
import json

# ===== API VIEWS FOR FRONTEND (React) =====

class RestaurantDetailView(generics.RetrieveAPIView):
    """Get restaurant details - Single Restaurant"""
    serializer_class = RestaurantSerializer
    
    def get_object(self):
        # Always return the single restaurant instance
        return get_restaurant_info()

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
    """Create new reservation - FIXED TIMEZONE HANDLING"""
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
            
            # TIMEZONE FIX: Debug and proper date handling
            print(f"🔍 DEBUG - Original date from frontend: {date_str}")
            print(f"🔍 DEBUG - Original time from frontend: {time_str}")
            print(f"🔍 DEBUG - Current Django timezone: {timezone.get_current_timezone()}")
            print(f"🔍 DEBUG - Current Django date: {timezone.now().date()}")
            
            try:
                # Parse date without timezone conversion
                # This should preserve the date as-is without timezone adjustment
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                time_obj = datetime.strptime(time_str, '%H:%M').time()
                
                print(f"🔍 DEBUG - Parsed date: {date}")
                print(f"🔍 DEBUG - Parsed time: {time_obj}")
                
            except ValueError as e:
                print(f"❌ ERROR - Date/time parsing failed: {e}")
                return Response(
                    {'error': f'Invalid date or time format: {e}'}, 
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
            
            # Count existing reservations - FIXED: Use French status values
            existing_reservations = Reservation.objects.filter(
                date=date,
                time=time_obj,
                status__in=['En attente', 'Confirmée']
            ).count()
            
            print(f"🔍 DEBUG - Existing reservations for {date} at {time_obj}: {existing_reservations}")
            
            if existing_reservations >= time_slot.max_reservations:
                return Response(
                    {'error': 'This time slot is fully booked'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the reservation - FIXED: Use French status value
            reservation = Reservation.objects.create(
                customer_name=data['customer_name'],
                customer_email=data['customer_email'],
                customer_phone=data['customer_phone'],
                date=date,
                time=time_obj,
                number_of_guests=guests,
                special_requests=data.get('special_requests', ''),
                status='En attente'  # Changed from 'pending'
            )
            
            # Debug: Check what was actually saved
            print(f"✅ SUCCESS - Reservation created with date: {reservation.date}")
            print(f"✅ SUCCESS - Reservation ID: {reservation.id}")
            
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
            print(f"❌ ERROR in reservation creation: {e}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ===== AVAILABILITY ENDPOINT =====
@csrf_exempt
def check_availability_by_date(request):
    """Check availability for a specific date - FIXED TIMEZONE HANDLING"""
    if request.method == 'GET':
        try:
            date_str = request.GET.get('date')
            if not date_str:
                return JsonResponse({'error': 'Date parameter required'}, status=400)
            
            print(f"🔍 DEBUG - Availability check for date: {date_str}")
            
            # Parse the date
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                print(f"🔍 DEBUG - Parsed availability date: {date}")
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
                # Count existing reservations for this date and time - FIXED: Use French status values
                existing_reservations = Reservation.objects.filter(
                    date=date,
                    time=slot.time,
                    status__in=['En attente', 'Confirmée']
                ).count()
                
                available_spots = slot.max_reservations - existing_reservations
                is_available = available_spots > 0
                
                print(f"🔍 DEBUG - Slot {slot.time}: {existing_reservations}/{slot.max_reservations} reservations")
                
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
            print(f"❌ ERROR in availability check: {e}")
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
    
    # Check reservations for this date and time - FIXED: Use French status values
    existing_reservations = Reservation.objects.filter(
        date=date,
        time=time,
        status__in=['En attente', 'Confirmée']
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
    restaurant = get_restaurant_info()
    current_tz = timezone.get_current_timezone()
    current_time = timezone.now()
    
    return JsonResponse({
        'status': 'success',
        'message': 'Backend connected successfully!',
        'restaurant': restaurant.name,
        'timestamp': current_time.isoformat(),
        'timezone': str(current_tz),
        'local_date': current_time.date().strftime('%Y-%m-%d'),
        'local_time': current_time.time().strftime('%H:%M:%S'),
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
    """Basic dashboard statistics API - FIXED: French status values"""
    today = timezone.now().date()
    restaurant = get_restaurant_info()
    
    stats = {
        'restaurant_name': restaurant.name,
        'restaurant_capacity': restaurant.capacity,
        'restaurant_tables': restaurant.number_of_tables,
        'total_reservations': Reservation.objects.count(),
        'today_reservations': Reservation.objects.filter(date=today).count(),
        
        # FIXED: Use French status values
        'pending_reservations': Reservation.objects.filter(status='En attente').count(),
        'confirmed_reservations': Reservation.objects.filter(status='Confirmée').count(),
        
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        'available_tables': restaurant.get_available_tables_today(),
    }
    
    return JsonResponse(stats)

@api_view(['POST'])
@staff_member_required
def update_reservation_status(request, reservation_id):
    """Update reservation status - FIXED: Accept French status values"""
    try:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        new_status = request.data.get('status')
        
        # Accept both English and French status values for flexibility
        if new_status in ['pending', 'confirmed', 'cancelled', 'completed', 'En attente', 'Confirmée', 'Annulée', 'Terminée']:
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
    
    # Get restaurant instance (single instance)
    restaurant = get_restaurant_info()
    
    # ADD THIS DEBUG BLOCK:
    print(f"🔥 DASHBOARD DEBUG - Today's date: {today}")
    today_reservations_debug = Reservation.objects.filter(date=today).order_by('time')
    print(f"🔥 DASHBOARD DEBUG - Found {today_reservations_debug.count()} reservations")
    for res in today_reservations_debug:
        print(f"🔥 DASHBOARD DEBUG - Reservation: {res.customer_name} at {res.time} (status: {res.status})")
    
    # Basic metrics - FIXED: Use French status values
    metrics = {
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'today_confirmed': Reservation.objects.filter(date=today, status='Confirmée').count(),
        'today_pending': Reservation.objects.filter(date=today, status='En attente').count(),
        'today_guests': Reservation.objects.filter(date=today).aggregate(
            total=Sum('number_of_guests')
        )['total'] or 0,
        
        'week_reservations': Reservation.objects.filter(date__gte=week_start).count(),
        'month_reservations': Reservation.objects.filter(date__gte=month_start).count(),
        
        'total_tables': restaurant.number_of_tables,
        'available_tables': get_available_tables_count(today, now.time()),
        
        'peak_hour': get_peak_hour_today(today),
        'next_available_slot': get_next_available_slot(),
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        
        # Restaurant info
        'restaurant_name': restaurant.name,
        'restaurant_capacity': restaurant.capacity,
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
    
    # Chart data - ADD DEBUG HERE TOO:
    print(f"🔥 DASHBOARD DEBUG - About to call get_daily_time_slots_data")
    daily_slots_data = get_daily_time_slots_data(today)
    print(f"🔥 DASHBOARD DEBUG - Chart data returned: {daily_slots_data}")
    
    chart_data = {
        'weekly_reservations': get_weekly_chart_data(week_start),
        'daily_time_slots': daily_slots_data,
    }
    
    context = {
        'metrics': metrics,
        'recent_reservations': recent_reservations,
        'todays_schedule': todays_schedule,
        'alerts': alerts,
        'chart_data': chart_data,
        'restaurant': restaurant,
    }
    
    return render(request, 'admin/unified_dashboard_with_sidebar.html', context)

def get_available_tables_count(date, time):
    """Calculate available tables for given date and time - FIXED: French status values"""
    restaurant = get_restaurant_info()
    
    # Count reservations for today
    reservations_count = Reservation.objects.filter(
        date=date,
        status__in=['Confirmée', 'En attente']
    ).count()
    
    return max(0, restaurant.number_of_tables - reservations_count)

def get_peak_hour_today(date):
    """Find the busiest hour for today - FIXED: French status values"""
    peak_hour = Reservation.objects.filter(
        date=date,
        status__in=['En attente', 'Confirmée']
    ).values('time').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    if peak_hour and peak_hour['count'] > 0:
        return peak_hour['time'].strftime('%H:%M')
    return None

def get_next_available_slot():
    """Find next available time slot - FIXED: French status values"""
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
                status__in=['Confirmée', 'En attente']
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
    """Generate dashboard alerts - FIXED: French status values"""
    alerts = []
    
    # Check for overbookings
    time_slots = TimeSlot.objects.filter(is_active=True)
    for slot in time_slots:
        reservations_count = Reservation.objects.filter(
            date=date,
            time=slot.time,
            status__in=['Confirmée', 'En attente']
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
    """Get reservation data by ACTUAL reservation times for today - CORRECTED VERSION"""
    from collections import defaultdict
    
    print(f"🔍 CHART DEBUG - Getting data for date: {date}")
    
    # Get all reservations for today
    todays_reservations = Reservation.objects.filter(date=date).order_by('time')
    
    print(f"🔍 CHART DEBUG - Found {todays_reservations.count()} reservations")
    
    if not todays_reservations.exists():
        print("🔍 CHART DEBUG - No reservations, returning empty data")
        return {
            'labels': [],
            'data': []
        }
    
    # Count reservations by actual time - ONLY use actual reservation times
    time_counts = defaultdict(int)
    
    for reservation in todays_reservations:
        time_str = reservation.time.strftime('%H:%M')
        time_counts[time_str] += 1
        print(f"🔍 CHART DEBUG - Reservation: {reservation.customer_name} at {time_str} (status: {reservation.status})")
    
    # Sort times and prepare data - CRITICAL: Only include times that have reservations
    sorted_times = sorted(time_counts.keys())
    labels = sorted_times
    data = [time_counts[time] for time in sorted_times]
    
    print(f"🔍 CHART DEBUG - Final labels: {labels}")
    print(f"🔍 CHART DEBUG - Final data: {data}")
    print(f"🔍 CHART DEBUG - Time counts: {dict(time_counts)}")
    
    return {
        'labels': labels,
        'data': data
    }

# ALTERNATIVE VERSION - If you want to show ALL time slots (including empty ones)
def get_daily_time_slots_data_with_empty_slots(date):
    """Show ALL configured time slots, even empty ones"""
    from collections import defaultdict
    
    print(f"🔍 CHART DEBUG - Getting data with empty slots for date: {date}")
    
    # Get all active time slots
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
    
    if not time_slots.exists():
        print("🔍 CHART DEBUG - No time slots configured")
        return {'labels': [], 'data': []}
    
    # Initialize all time slots with 0
    time_counts = {}
    for slot in time_slots:
        time_str = slot.time.strftime('%H:%M')
        time_counts[time_str] = 0
        print(f"🔍 CHART DEBUG - Initialized slot: {time_str}")
    
    # Count actual reservations
    todays_reservations = Reservation.objects.filter(date=date)
    for reservation in todays_reservations:
        time_str = reservation.time.strftime('%H:%M')
        if time_str in time_counts:  # Only count if it's a valid time slot
            time_counts[time_str] += 1
            print(f"🔍 CHART DEBUG - Added reservation: {reservation.customer_name} at {time_str}")
    
    # Sort and return
    sorted_times = sorted(time_counts.keys())
    labels = sorted_times
    data = [time_counts[time] for time in sorted_times]
    
    print(f"🔍 CHART DEBUG - All slots - Labels: {labels}")
    print(f"🔍 CHART DEBUG - All slots - Data: {data}")
    
    return {
        'labels': labels,
        'data': data
    }

def get_daily_time_slots_data_with_all_slots(date):
    """Get reservation data showing ALL time slots (including empty ones)"""
    
    # Get all active time slots
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
    
    # Also get any actual reservation times that might not be in TimeSlot model
    actual_reservation_times = Reservation.objects.filter(
        date=date
    ).values_list('time', flat=True).distinct().order_by('time')
    
    # Combine all times
    all_times = set()
    
    # Add time slots
    for slot in time_slots:
        all_times.add(slot.time)
    
    # Add actual reservation times
    for res_time in actual_reservation_times:
        all_times.add(res_time)
    
    # Sort all times
    sorted_times = sorted(all_times)
    
    labels = []
    data = []
    
    for time_obj in sorted_times:
        time_str = time_obj.strftime('%H:%M')
        labels.append(time_str)
        
        # Count actual reservations for this time
        count = Reservation.objects.filter(
            date=date,
            time=time_obj
        ).count()
        data.append(count)
        
        print(f"🔍 DEBUG - Time slot {time_str}: {count} reservations")
    
    print(f"🔍 DEBUG - Final chart labels: {labels}")
    print(f"🔍 DEBUG - Final chart data: {data}")
    
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
    """API endpoint for real-time metrics - FIXED: French status values"""
    today = timezone.now().date()
    now = timezone.now()
    restaurant = get_restaurant_info()
    
    metrics = {
        'restaurant_name': restaurant.name,
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'today_guests': Reservation.objects.filter(date=today).aggregate(
            total=Sum('number_of_guests')
        )['total'] or 0,
        'available_tables': get_available_tables_count(today, now.time()),
        
        # FIXED: Use French status values
        'pending_reservations': Reservation.objects.filter(
            date=today, 
            status='En attente'
        ).count(),
        
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        'total_capacity': restaurant.capacity,
        'total_tables': restaurant.number_of_tables,
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

# ===== RESTAURANT INFO API =====
@api_view(['GET'])
def restaurant_info(request):
    """Get restaurant information"""
    restaurant = get_restaurant_info()
    
    return JsonResponse({
        'name': restaurant.name,
        'address': restaurant.address,
        'phone': restaurant.phone,
        'email': restaurant.email,
        'description': restaurant.description,
        'capacity': restaurant.capacity,
        'number_of_tables': restaurant.number_of_tables,
        'opening_time': restaurant.opening_time.strftime('%H:%M'),
        'closing_time': restaurant.closing_time.strftime('%H:%M'),
        'occupancy_rate_today': restaurant.get_occupancy_rate_today(),
        'available_tables_today': restaurant.get_available_tables_today(),
    })

# ===== TIMEZONE DEBUG ENDPOINT =====
@csrf_exempt
def timezone_debug(request):
    """Debug endpoint to check timezone handling"""
    now_utc = timezone.now()
    now_local = timezone.localtime(now_utc)
    
    return JsonResponse({
        'server_timezone': str(timezone.get_current_timezone()),
        'utc_time': now_utc.isoformat(),
        'local_time': now_local.isoformat(),
        'utc_date': now_utc.date().strftime('%Y-%m-%d'),
        'local_date': now_local.date().strftime('%Y-%m-%d'),
        'django_settings': {
            'USE_TZ': True,  # Should be True
            'TIME_ZONE': 'Africa/Casablanca'
        },
        'test_date_parsing': {
            'input': '2025-07-18',
            'parsed': datetime.strptime('2025-07-18', '%Y-%m-%d').date().strftime('%Y-%m-%d')
        }
    })