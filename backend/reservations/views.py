from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime
from .models import Restaurant, Reservation, TimeSlot, SpecialDate
from .serializers import (
    RestaurantSerializer, ReservationSerializer, ReservationCreateSerializer,
    TimeSlotSerializer, SpecialDateSerializer, AvailabilitySerializer
)


class RestaurantDetailView(generics.RetrieveAPIView):
    """API pour récupérer les informations du restaurant"""
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    
    def get_object(self):
        # Retourne le premier restaurant (on n'en a qu'un)
        return Restaurant.objects.first()


class TimeSlotListView(generics.ListAPIView):
    """API pour récupérer tous les créneaux horaires actifs"""
    queryset = TimeSlot.objects.filter(is_active=True).order_by('time')
    serializer_class = TimeSlotSerializer


class ReservationCreateView(generics.CreateAPIView):
    """API pour créer une nouvelle réservation"""
    queryset = Reservation.objects.all()
    serializer_class = ReservationCreateSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            reservation = serializer.save()
            # Retourner les détails de la réservation créée
            response_serializer = ReservationSerializer(reservation)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReservationListView(generics.ListAPIView):
    """API pour lister les réservations (pour l'admin)"""
    queryset = Reservation.objects.all().order_by('-created_at')
    serializer_class = ReservationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrer par date si spécifié
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(date=date)
        # Filtrer par statut si spécifié
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class ReservationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API pour récupérer, modifier ou supprimer une réservation"""
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer


@api_view(['GET'])
def check_availability(request):
    """
    API pour vérifier la disponibilité d'une date donnée
    Usage: GET /api/availability/?date=2025-06-15
    """
    date_str = request.GET.get('date')
    if not date_str:
        return Response(
            {'error': 'Paramètre date requis (format: YYYY-MM-DD)'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Format de date invalide (format: YYYY-MM-DD)'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier si c'est une date spéciale
    special_date = SpecialDate.objects.filter(date=check_date).first()
    is_closed = False
    special_hours = {}
    
    if special_date:
        is_closed = special_date.is_closed
        if special_date.special_opening_time and special_date.special_closing_time:
            special_hours = {
                'opening_time': special_date.special_opening_time.strftime('%H:%M'),
                'closing_time': special_date.special_closing_time.strftime('%H:%M')
            }
    
    # Si fermé, retourner l'info
    if is_closed:
        return Response({
            'date': check_date,
            'is_closed': True,
            'available_slots': [],
            'special_hours': special_hours
        })
    
    # Récupérer tous les créneaux actifs
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
    available_slots = []
    
    for slot in time_slots:
        available_count = slot.available_slots(check_date)
        available_slots.append({
            'id': slot.id,
            'time': slot.time.strftime('%H:%M'),
            'max_reservations': slot.max_reservations,
            'available_count': available_count,
            'is_available': available_count > 0
        })
    
    return Response({
        'date': check_date,
        'is_closed': False,
        'available_slots': available_slots,
        'special_hours': special_hours
    })


@api_view(['GET'])
def dashboard_stats(request):
    """
    API pour les statistiques du tableau de bord admin
    """
    today = timezone.now().date()
    
    # Réservations d'aujourd'hui
    today_reservations = Reservation.objects.filter(date=today)
    
    # Statistiques
    stats = {
        'today': {
            'total_reservations': today_reservations.count(),
            'confirmed': today_reservations.filter(status='confirmed').count(),
            'pending': today_reservations.filter(status='pending').count(),
            'cancelled': today_reservations.filter(status='cancelled').count(),
            'total_guests': sum(r.number_of_guests for r in today_reservations if r.status in ['confirmed', 'pending'])
        },
        'this_week': {
            'total_reservations': Reservation.objects.filter(
                date__gte=today,
                date__lt=today.replace(day=today.day + 7)
            ).count()
        }
    }
    
    # Prochaines réservations (aujourd'hui)
    upcoming_reservations = today_reservations.filter(
        status__in=['confirmed', 'pending']
    ).order_by('time')[:5]
    
    stats['upcoming_reservations'] = ReservationSerializer(
        upcoming_reservations, many=True
    ).data
    
    return Response(stats)


@api_view(['POST'])
def update_reservation_status(request, reservation_id):
    """
    API pour changer le statut d'une réservation
    """
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response(
            {'error': 'Réservation non trouvée'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    new_status = request.data.get('status')
    if new_status not in ['pending', 'confirmed', 'cancelled', 'completed']:
        return Response(
            {'error': 'Statut invalide'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    reservation.status = new_status
    reservation.save()
    
    serializer = ReservationSerializer(reservation)
    return Response(serializer.data)