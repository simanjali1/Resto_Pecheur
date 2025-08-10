# reservations/views.py - COMPLETE VERSION WITH SPECIAL DATES INTEGRATION
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from .models import RestaurantInfo, Reservation, TimeSlot, SpecialDate, get_restaurant_info
from .serializers import ReservationSerializer, TimeSlotSerializer, RestaurantSerializer
import json
import logging
import re

# EMAIL VERIFICATION IMPORTS
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    print("⚠️ WARNING: dnspython not installed. Email verification will be limited.")

logger = logging.getLogger(__name__)

# ===== EMAIL VERIFICATION ENDPOINT =====

@csrf_exempt
@require_http_methods(["POST"])
def verify_email_exists(request):
    """
    Comprehensive email verification: Format + Domain + Typos + Disposable blocking
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({
                'exists': False,
                'error': 'Email is required'
            })
        
        # Step 1: Basic format validation
        if '@' not in email:
            return JsonResponse({
                'exists': False,
                'error': 'Email must contain @'
            })
        
        parts = email.split('@')
        if len(parts) != 2:
            return JsonResponse({
                'exists': False,
                'error': 'Invalid email format'
            })
        
        username, domain = parts
        
        # Step 2: Username validation
        if not username or len(username) < 1:
            return JsonResponse({
                'exists': False,
                'error': 'Username cannot be empty'
            })
        
        if len(username) > 64:
            return JsonResponse({
                'exists': False,
                'error': 'Username too long (max 64 characters)'
            })
        
        # Check for valid characters in username
        if not re.match(r'^[a-zA-Z0-9._+-]+$', username):
            return JsonResponse({
                'exists': False,
                'error': 'Username contains invalid characters'
            })
        
        # Check for consecutive dots or starting/ending dots
        if '..' in username or username.startswith('.') or username.endswith('.'):
            return JsonResponse({
                'exists': False,
                'error': 'Invalid username format'
            })
        
        # Step 3: Domain validation
        if not domain or len(domain) < 3:
            return JsonResponse({
                'exists': False,
                'error': 'Domain too short'
            })
        
        if len(domain) > 255:
            return JsonResponse({
                'exists': False,
                'error': 'Domain too long'
            })
        
        if '.' not in domain:
            return JsonResponse({
                'exists': False,
                'error': 'Domain must contain at least one dot'
            })
        
        # Check for valid characters in domain
        if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
            return JsonResponse({
                'exists': False,
                'error': 'Domain contains invalid characters'
            })
        
        # Check domain parts
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return JsonResponse({
                'exists': False,
                'error': 'Invalid domain format'
            })
        
        # Check TLD (last part)
        tld = domain_parts[-1]
        if len(tld) < 2:
            return JsonResponse({
                'exists': False,
                'error': 'Invalid top-level domain'
            })
        
        # Step 4: Typo detection and correction
        typo_corrections = {
            'gmial.com': 'gmail.com',
            'gmai.com': 'gmail.com',
            'gmail.co': 'gmail.com',
            'gmil.com': 'gmail.com',
            'hotmial.com': 'hotmail.com',
            'hotmai.com': 'hotmail.com',
            'hotmeil.com': 'hotmail.com',
            'yahooo.com': 'yahoo.com',
            'yaho.com': 'yahoo.com',
            'yahoo.co': 'yahoo.com',
            'outloook.com': 'outlook.com',
            'outlok.com': 'outlook.com',
            'outlook.co': 'outlook.com',
            'orage.fr': 'orange.fr',
            'ornage.fr': 'orange.fr',
            'fre.fr': 'free.fr',
            'free.f': 'free.fr',
            'sfr.f': 'sfr.fr',
            'lapost.net': 'laposte.net',
            'laposte.ne': 'laposte.net',
            'wanadoo.f': 'wanadoo.fr',
            'live.co': 'live.com',
            'iclou.com': 'icloud.com',
            'icloud.co': 'icloud.com'
        }
        
        if domain in typo_corrections:
            suggested_email = f"{username}@{typo_corrections[domain]}"
            return JsonResponse({
                'exists': False,
                'error': f'Possible typo detected. Did you mean: {suggested_email}?'
            })
        
        # Step 5: Disposable email blocking
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com', 'mailinator.com',
            'throwaway.email', 'temp-mail.org', 'getairmail.com', 'yopmail.com',
            'maildrop.cc', 'sharklasers.com', 'grr.la', 'guerrillamailblock.com',
            'tempmail.net', 'tempail.com', 'temp-mail.io', 'disposablemail.com',
            'fakeinbox.com', 'spamgourmet.com', 'mohmal.com', 'emailondeck.com',
            'getnada.com', 'tempinbox.com', 'tempr.email', 'temporaryemail.net'
        ]
        
        if domain in disposable_domains:
            return JsonResponse({
                'exists': False,
                'error': 'Temporary/disposable email addresses are not allowed'
            })
        
        # Step 6: Domain MX record validation
        if not DNS_AVAILABLE:
            return JsonResponse({
                'exists': True,
                'message': 'Email format is valid (DNS verification unavailable)'
            })
        
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            
            # Domain has MX records, email format is valid
            return JsonResponse({
                'exists': True,
                'message': 'Email format is valid and domain accepts emails'
            })
            
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return JsonResponse({
                'exists': False,
                'error': 'Domain does not exist or cannot receive emails'
            })
        except Exception as e:
            logger.error(f"DNS verification error for {domain}: {e}")
            # If DNS fails, but format is valid, still allow it
            return JsonResponse({
                'exists': True,
                'message': 'Email format is valid (domain verification failed)'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'exists': False,
            'error': 'Invalid request format'
        }, status=400)
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        return JsonResponse({
            'exists': False,
            'error': 'Email verification service temporarily unavailable'
        }, status=500)

# Alternative lightweight verification (less accurate but faster)
@csrf_exempt
@require_http_methods(["POST"])
def verify_email_lightweight(request):
    """
    Lightweight email verification - only checks domain validity
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            return JsonResponse({
                'exists': False,
                'error': 'Invalid email format'
            })
        
        domain = email.split('@')[1]
        
        if not DNS_AVAILABLE:
            return JsonResponse({
                'exists': None,
                'error': 'DNS verification not available'
            })
        
        # Check if domain has MX record
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return JsonResponse({
                'exists': True,
                'message': 'Domain can receive emails',
                'verification_type': 'domain_only'
            })
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return JsonResponse({
                'exists': False,
                'error': 'Domain does not accept emails'
            })
        except Exception as e:
            logger.error(f"Domain verification error: {e}")
            return JsonResponse({
                'exists': None,
                'error': 'Verification service unavailable'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'exists': None,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        return JsonResponse({
            'exists': None,
            'error': 'Verification service temporarily unavailable'
        }, status=500)

# For bulk email verification (if needed)
@csrf_exempt
@require_http_methods(["POST"])
def verify_emails_bulk(request):
    """
    Verify multiple emails at once
    """
    try:
        data = json.loads(request.body)
        emails = data.get('emails', [])
        
        if not emails or len(emails) > 50:  # Limit to 50 emails per request
            return JsonResponse({
                'error': 'Invalid email list (max 50 emails)'
            }, status=400)
        
        results = []
        for email in emails:
            # Use the main verification function
            mock_request = type('MockRequest', (), {
                'method': 'POST',
                'body': json.dumps({'email': email}).encode()
            })()
            
            # Get verification result
            result = verify_email_exists(mock_request)
            result_data = json.loads(result.content)
            
            results.append({
                'email': email,
                'exists': result_data.get('exists'),
                'message': result_data.get('message', result_data.get('error', ''))
            })
        
        return JsonResponse({
            'results': results,
            'total': len(emails),
            'valid': len([r for r in results if r['exists'] is True]),
            'invalid': len([r for r in results if r['exists'] is False]),
            'unknown': len([r for r in results if r['exists'] is None])
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Bulk email verification error: {e}")
        return JsonResponse({
            'error': 'Verification service temporarily unavailable'
        }, status=500)

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
    """Create new reservation with special dates check"""
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
                # Parse date without timezone conversion
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                time_obj = datetime.strptime(time_str, '%H:%M').time()
                
            except ValueError as e:
                return Response(
                    {'error': f'Invalid date or time format: {e}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ✅ NEW: Check if date is a special date (closed)
            special_date = SpecialDate.objects.filter(date=date).first()
            if special_date and not special_date.is_open:
                return Response(
                    {'error': 'Restaurant fermé ce jour-là'}, 
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
                status__in=['En attente', 'Confirmée']
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
                status='En attente'
            )

            return Response({
                'id': reservation.id,
                'message': 'Reservation created successfully',
                'customer_name': reservation.customer_name,
                'customer_email': reservation.customer_email,
                'customer_phone': reservation.customer_phone,
                'date': reservation.date.strftime('%Y-%m-%d'),
                'time': reservation.time.strftime('%H:%M'),
                'number_of_guests': reservation.number_of_guests,
                'special_requests': reservation.special_requests,
                'status': reservation.status,
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

# ===== SPECIAL DATES API ENDPOINT =====
@api_view(['GET'])
def special_dates_list(request):
    """Get all special dates for frontend calendar"""
    try:
        # Get future special dates only
        special_dates = SpecialDate.objects.filter(
            date__gte=timezone.now().date()
        ).values('date', 'is_open', 'reason', 'special_hours')
        
        return JsonResponse({
            'special_dates': list(special_dates)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

# ===== AVAILABILITY ENDPOINT WITH SPECIAL DATES =====
@csrf_exempt
def check_availability_by_date(request):
    """Check availability for a specific date with special dates integration"""
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
            
            # ✅ NEW: Check if date is a special date
            special_date = SpecialDate.objects.filter(date=date).first()
            if special_date and not special_date.is_open:
                return JsonResponse({
                    'date': date_str,
                    'availability': [],
                    'message': 'Restaurant fermé ce jour',
                    'is_special_date': True,
                    'reason': special_date.reason,
                    'total_slots': 0
                })
            
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
                    status__in=['En attente', 'Confirmée']
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
            
            response_data = {
                'date': date_str,
                'availability': availability_data,
                'total_slots': len(availability_data),
                'is_special_date': False
            }
            
            # Add special date info if it exists but is open
            if special_date and special_date.is_open:
                response_data.update({
                    'is_special_date': True,
                    'reason': special_date.reason,
                    'special_hours': special_date.special_hours
                })
            
            return JsonResponse(response_data)
            
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
    
    # Check if date is a special date (closed)
    special_date = SpecialDate.objects.filter(date=date).first()
    if special_date and not special_date.is_open:
        return Response({
            'available': False, 
            'message': 'Restaurant fermé ce jour'
        }, status=status.HTTP_200_OK)
    
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
        'method': request.method,
        'email_verification_available': DNS_AVAILABLE
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
    restaurant = get_restaurant_info()
    
    stats = {
        'restaurant_name': restaurant.name,
        'restaurant_capacity': restaurant.capacity,
        'restaurant_tables': restaurant.number_of_tables,
        'total_reservations': Reservation.objects.count(),
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'pending_reservations': Reservation.objects.filter(status='En attente').count(),
        'confirmed_reservations': Reservation.objects.filter(status='Confirmée').count(),
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        'available_tables': restaurant.get_available_tables_today(),
    }
    
    return JsonResponse(stats)

@api_view(['POST'])
@staff_member_required
def update_reservation_status(request, reservation_id):
    """Update reservation status"""
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
        'email_verification_available': DNS_AVAILABLE,
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
        },
        'email_verification_available': DNS_AVAILABLE,
        'dns_library_status': 'Available' if DNS_AVAILABLE else 'Not installed - run: pip install dnspython'
    })

# ===== HELPER FUNCTIONS FOR DASHBOARD =====

def get_available_tables_count(date, time):
    """Calculate available tables for given date and time"""
    restaurant = get_restaurant_info()
    
    # Count reservations for today
    reservations_count = Reservation.objects.filter(
        date=date,
        status__in=['Confirmée', 'En attente']
    ).count()
    
    return max(0, restaurant.number_of_tables - reservations_count)

def get_peak_hour_today(date):
    """Find the busiest hour for today"""
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
    """Find next available time slot with special dates check"""
    now = timezone.localtime(timezone.now())
    current_date = now.date()
    current_time = now.time()
    
    # Look for available slots in the next 7 days
    for days_ahead in range(7):
        check_date = current_date + timedelta(days=days_ahead)
        
        # Check if date is a special date (closed)
        special_date = SpecialDate.objects.filter(date=check_date).first()
        if special_date and not special_date.is_open:
            continue
        
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

# ===== DASHBOARD VIEWS (if needed) =====

@staff_member_required
def dashboard_view(request):
    """Main unified dashboard view with all functionalities"""
    today = timezone.now().date()
    now = timezone.now()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Get restaurant instance (single instance)
    restaurant = get_restaurant_info()
    
    # Basic metrics
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
    
    context = {
        'metrics': metrics,
        'recent_reservations': recent_reservations,
        'todays_schedule': todays_schedule,
        'restaurant': restaurant,
        'email_verification_available': DNS_AVAILABLE,
    }
    
    return render(request, 'admin/unified_dashboard_with_sidebar.html', context)

# API endpoints for AJAX updates
@staff_member_required
def dashboard_api_metrics(request):
    """API endpoint for real-time metrics"""
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
        'pending_reservations': Reservation.objects.filter(
            date=today, 
            status='En attente'
        ).count(),
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        'total_capacity': restaurant.capacity,
        'total_tables': restaurant.number_of_tables,
        'email_verification_available': DNS_AVAILABLE,
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