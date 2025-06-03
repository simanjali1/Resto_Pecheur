from rest_framework import serializers
from .models import Restaurant, Reservation, TimeSlot, SpecialDate


class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer pour les informations du restaurant"""
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'address', 'phone', 'email', 'description',
            'capacity', 'opening_time', 'closing_time',
            'closed_on_monday', 'closed_on_tuesday', 'closed_on_wednesday',
            'closed_on_thursday', 'closed_on_friday', 'closed_on_saturday', 'closed_on_sunday'
        ]


class TimeSlotSerializer(serializers.ModelSerializer):
    """Serializer pour les créneaux horaires"""
    available_slots = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeSlot
        fields = ['id', 'time', 'max_reservations', 'is_active', 'available_slots']
    
    def get_available_slots(self, obj):
        """Retourne le nombre de créneaux disponibles pour une date donnée"""
        # Par défaut, on retourne max_reservations
        # Dans une vraie app, on calculerait selon la date demandée
        request = self.context.get('request')
        if request and 'date' in request.GET:
            date = request.GET.get('date')
            return obj.available_slots(date)
        return obj.max_reservations


class ReservationSerializer(serializers.ModelSerializer):
    """Serializer pour les réservations"""
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'customer_name', 'customer_email', 'customer_phone',
            'date', 'time', 'number_of_guests', 'status', 'special_requests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validation personnalisée pour les réservations"""
        # Vérifier que la date n'est pas dans le passé
        from django.utils import timezone
        if data['date'] < timezone.now().date():
            raise serializers.ValidationError("Impossible de réserver dans le passé.")
        
        # Vérifier la disponibilité du créneau
        try:
            time_slot = TimeSlot.objects.get(time=data['time'], is_active=True)
            if not time_slot.is_available(data['date']):
                raise serializers.ValidationError("Ce créneau n'est plus disponible.")
        except TimeSlot.DoesNotExist:
            raise serializers.ValidationError("Créneau horaire non disponible.")
        
        return data


class ReservationCreateSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour créer une réservation depuis le frontend"""
    
    class Meta:
        model = Reservation
        fields = [
            'customer_name', 'customer_email', 'customer_phone',
            'date', 'time', 'number_of_guests', 'special_requests'
        ]
    
    def create(self, validated_data):
        """Créer une réservation avec statut 'pending' par défaut"""
        validated_data['status'] = 'pending'
        return super().create(validated_data)


class SpecialDateSerializer(serializers.ModelSerializer):
    """Serializer pour les dates spéciales"""
    
    class Meta:
        model = SpecialDate
        fields = [
            'id', 'date', 'is_closed', 'special_opening_time', 
            'special_closing_time', 'reason'
        ]


class AvailabilitySerializer(serializers.Serializer):
    """Serializer pour vérifier la disponibilité d'une date"""
    date = serializers.DateField()
    available_slots = serializers.ListField(child=serializers.DictField())
    is_closed = serializers.BooleanField()
    special_hours = serializers.DictField(required=False)