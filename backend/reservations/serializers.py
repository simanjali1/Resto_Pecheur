from rest_framework import serializers
from .models import RestaurantInfo, Reservation, TimeSlot, SpecialDate


class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer pour les informations du restaurant - Single Restaurant Version"""
    occupancy_rate_today = serializers.SerializerMethodField()
    available_tables_today = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantInfo
        fields = [
            'id', 'name', 'address', 'phone', 'email', 'description',
            'capacity', 'number_of_tables', 'opening_time', 'closing_time',
            'closed_on_monday', 'closed_on_tuesday', 'closed_on_wednesday',
            'closed_on_thursday', 'closed_on_friday', 'closed_on_saturday', 'closed_on_sunday',
            'occupancy_rate_today', 'available_tables_today'
        ]
        read_only_fields = ['name']  # Name is fixed to "Resto Pêcheur"
    
    def get_occupancy_rate_today(self, obj):
        """Retourne le taux d'occupation pour aujourd'hui"""
        return obj.get_occupancy_rate_today()
    
    def get_available_tables_today(self, obj):
        """Retourne le nombre de tables disponibles aujourd'hui"""
        return obj.get_available_tables_today()


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
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                return obj.available_slots(date_obj)
            except (ValueError, TypeError):
                return obj.max_reservations
        return obj.max_reservations


class ReservationSerializer(serializers.ModelSerializer):
    """Serializer pour les réservations"""
    is_today = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    time_until_reservation = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'customer_name', 'customer_email', 'customer_phone',
            'date', 'time', 'number_of_guests', 'status', 'special_requests',
            'table_number', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at',
            'is_today', 'is_upcoming', 'time_until_reservation'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at']
    
    def get_is_today(self, obj):
        """Vérifie si la réservation est pour aujourd'hui"""
        return obj.is_today
    
    def get_is_upcoming(self, obj):
        """Vérifie si la réservation est à venir"""
        return obj.is_upcoming
    
    def get_time_until_reservation(self, obj):
        """Retourne le temps jusqu'à la réservation"""
        return obj.get_time_until_reservation()
    
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
    
    def validate(self, data):
        """Validation pour la création de réservation"""
        # Vérifier que la date n'est pas dans le passé
        from django.utils import timezone
        if data['date'] < timezone.now().date():
            raise serializers.ValidationError({
                'date': "Impossible de réserver dans le passé."
            })
        
        # Vérifier la disponibilité du créneau
        try:
            time_slot = TimeSlot.objects.get(time=data['time'], is_active=True)
            if not time_slot.is_available(data['date']):
                raise serializers.ValidationError({
                    'time': "Ce créneau n'est plus disponible pour cette date."
                })
        except TimeSlot.DoesNotExist:
            raise serializers.ValidationError({
                'time': "Créneau horaire non disponible."
            })
        
        # Vérifier que le restaurant n'est pas fermé ce jour-là
        from .models import get_restaurant_info
        restaurant = get_restaurant_info()
        weekday = data['date'].weekday()  # 0=Monday, 6=Sunday
        
        if restaurant.is_closed_on_day(weekday):
            days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
            raise serializers.ValidationError({
                'date': f"Le restaurant est fermé le {days[weekday]}."
            })
        
        # Vérifier les dates spéciales
        special_date = SpecialDate.objects.filter(date=data['date']).first()
        if special_date and special_date.is_closed:
            raise serializers.ValidationError({
                'date': f"Le restaurant est fermé ce jour: {special_date.reason or 'Fermeture exceptionnelle'}"
            })
        
        return data


class SpecialDateSerializer(serializers.ModelSerializer):
    """Serializer pour les dates spéciales"""
    is_today = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    days_until = serializers.SerializerMethodField()
    
    class Meta:
        model = SpecialDate
        fields = [
            'id', 'date', 'is_closed', 'special_opening_time', 
            'special_closing_time', 'reason', 'is_today', 'is_upcoming', 'days_until'
        ]
    
    def get_is_today(self, obj):
        """Vérifie si c'est aujourd'hui"""
        return obj.is_today
    
    def get_is_upcoming(self, obj):
        """Vérifie si c'est à venir"""
        return obj.is_upcoming
    
    def get_days_until(self, obj):
        """Nombre de jours jusqu'à cette date"""
        return obj.days_until


class AvailabilitySerializer(serializers.Serializer):
    """Serializer pour vérifier la disponibilité d'une date"""
    date = serializers.DateField()
    available_slots = serializers.ListField(child=serializers.DictField())
    is_closed = serializers.BooleanField()
    special_hours = serializers.DictField(required=False)
    restaurant_name = serializers.CharField(default="Resto Pêcheur")
    total_capacity = serializers.IntegerField(required=False)


class RestaurantInfoSerializer(serializers.ModelSerializer):
    """Serializer complet pour les informations du restaurant avec métriques"""
    occupancy_rate_today = serializers.SerializerMethodField()
    available_tables_today = serializers.SerializerMethodField()
    total_reservations_today = serializers.SerializerMethodField()
    pending_reservations_today = serializers.SerializerMethodField()
    confirmed_reservations_today = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantInfo
        fields = [
            'id', 'name', 'address', 'phone', 'email', 'description',
            'capacity', 'number_of_tables', 'opening_time', 'closing_time',
            'closed_on_monday', 'closed_on_tuesday', 'closed_on_wednesday',
            'closed_on_thursday', 'closed_on_friday', 'closed_on_saturday', 'closed_on_sunday',
            'created_at', 'updated_at',
            'occupancy_rate_today', 'available_tables_today', 'total_reservations_today',
            'pending_reservations_today', 'confirmed_reservations_today'
        ]
        read_only_fields = ['name', 'created_at', 'updated_at']
    
    def get_occupancy_rate_today(self, obj):
        """Retourne le taux d'occupation pour aujourd'hui"""
        return obj.get_occupancy_rate_today()
    
    def get_available_tables_today(self, obj):
        """Retourne le nombre de tables disponibles aujourd'hui"""
        return obj.get_available_tables_today()
    
    def get_total_reservations_today(self, obj):
        """Retourne le nombre total de réservations aujourd'hui"""
        from django.utils import timezone
        today = timezone.now().date()
        return Reservation.objects.filter(date=today).count()
    
    def get_pending_reservations_today(self, obj):
        """Retourne le nombre de réservations en attente aujourd'hui"""
        from django.utils import timezone
        today = timezone.now().date()
        return Reservation.objects.filter(date=today, status='pending').count()
    
    def get_confirmed_reservations_today(self, obj):
        """Retourne le nombre de réservations confirmées aujourd'hui"""
        from django.utils import timezone
        today = timezone.now().date()
        return Reservation.objects.filter(date=today, status='confirmed').count()


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    restaurant_name = serializers.CharField()
    restaurant_capacity = serializers.IntegerField()
    restaurant_tables = serializers.IntegerField()
    
    # Statistiques de base
    total_reservations = serializers.IntegerField()
    today_reservations = serializers.IntegerField()
    pending_reservations = serializers.IntegerField()
    confirmed_reservations = serializers.IntegerField()
    
    # Métriques temps réel
    occupancy_rate = serializers.FloatField()
    available_tables = serializers.IntegerField()
    
    # Données temporelles
    week_reservations = serializers.IntegerField(required=False)
    month_reservations = serializers.IntegerField(required=False)
    peak_hour = serializers.CharField(required=False, allow_null=True)
    next_available_slot = serializers.CharField(required=False)