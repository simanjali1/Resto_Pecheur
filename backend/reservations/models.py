from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta, date
from collections import defaultdict


# NEW: Notification Model for Integration
class Notification(models.Model):
    """Système de notifications pour le restaurant"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=50, default='general')
    
    # Optional: Link to related reservation
    related_reservation = models.ForeignKey(
        'Reservation', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Réservation liée"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save()


class RestaurantInfo(models.Model):
    """Informations du restaurant Resto Pêcheur (Singleton)"""
    name = models.CharField(max_length=100, default="Resto Pêcheur", editable=False)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(default=50)  # Nombre total de couverts
    number_of_tables = models.IntegerField(default=20, verbose_name="Nombre de tables")
    
    # Horaires d'ouverture
    opening_time = models.TimeField(default="11:00")
    closing_time = models.TimeField(default="22:00")
    
    # Jours de fermeture (optionnel)
    closed_on_monday = models.BooleanField(default=False)
    closed_on_tuesday = models.BooleanField(default=False)
    closed_on_wednesday = models.BooleanField(default=False)
    closed_on_thursday = models.BooleanField(default=False)
    closed_on_friday = models.BooleanField(default=False)
    closed_on_saturday = models.BooleanField(default=False)
    closed_on_sunday = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Assure qu'il n'y a qu'une seule instance"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Empêche la suppression"""
        pass
    
    @classmethod
    def load(cls):
        """Charge ou crée l'instance unique du restaurant"""
        obj, created = cls.objects.get_or_create(pk=1, defaults={
            'name': 'Resto Pêcheur',
            'address': 'Tangier, Morocco',
            'phone': '0661-460593',
            'email': 'contact@resto-pecheur.ma',
            'capacity': 50,
            'number_of_tables': 20,
        })
        return obj
    
    def is_closed_on_day(self, weekday):
        """Vérifie si le restaurant est fermé un jour donné (0=lundi, 6=dimanche)"""
        closed_days = [
            self.closed_on_monday,
            self.closed_on_tuesday,
            self.closed_on_wednesday,
            self.closed_on_thursday,
            self.closed_on_friday,
            self.closed_on_saturday,
            self.closed_on_sunday,
        ]
        return closed_days[weekday]
    
    def get_occupancy_rate_today(self):
        """Calcule le taux d'occupation pour aujourd'hui - UPDATED WITH FRENCH STATUS SUPPORT"""
        today = timezone.now().date()
        total_guests_today = Reservation.objects.filter(
            date=today,
            status__in=['confirmed', 'pending', 'Confirmée', 'En attente']  # Support both English and French
        ).aggregate(total=Sum('number_of_guests'))['total'] or 0
        
        return round((total_guests_today / self.capacity) * 100, 1) if self.capacity > 0 else 0
    
    def get_available_tables_today(self):
        """Retourne le nombre de tables disponibles aujourd'hui - UPDATED WITH FRENCH STATUS SUPPORT"""
        today = timezone.now().date()
        reserved_tables = Reservation.objects.filter(
            date=today,
            status__in=['confirmed', 'pending', 'Confirmée', 'En attente']  # Support both English and French
        ).count()
        
        return max(0, self.number_of_tables - reserved_tables)
    
    class Meta:
        verbose_name = "Configuration Restaurant"
        verbose_name_plural = "Configuration Restaurant"


class ReservationManager(models.Manager):
    """Manager personnalisé pour les réservations - UPDATED WITH FRENCH STATUS SUPPORT"""
    
    def today(self):
        """Réservations d'aujourd'hui"""
        return self.filter(date=timezone.now().date())
    
    def this_week(self):
        """Réservations de cette semaine"""
        today = timezone.now().date()
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        return self.filter(date__range=[start_week, end_week])
    
    def pending(self):
        """Réservations en attente - SUPPORT BOTH LANGUAGES"""
        return self.filter(status__in=['pending', 'En attente'])
    
    def confirmed(self):
        """Réservations confirmées - SUPPORT BOTH LANGUAGES"""
        return self.filter(status__in=['confirmed', 'Confirmée'])
    
    def active(self):
        """Réservations actives (pending + confirmed) - SUPPORT BOTH LANGUAGES"""
        return self.filter(status__in=['pending', 'confirmed', 'En attente', 'Confirmée'])
    
    def get_weekly_stats(self):
        """Statistiques par jour de la semaine"""
        today = timezone.now().date()
        start_week = today - timedelta(days=today.weekday())
        
        weekly_data = []
        for i in range(7):
            day = start_week + timedelta(days=i)
            count = self.filter(
                date=day,
                status__in=['pending', 'confirmed', 'En attente', 'Confirmée']  # Support both
            ).count()
            weekly_data.append(count)
        
        return weekly_data
    
    def get_hourly_stats_today(self):
        """Statistiques par heure pour aujourd'hui"""
        today = timezone.now().date()
        reservations = self.filter(
            date=today,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']  # Support both
        ).values('time').annotate(count=Count('id'))
        
        hourly_data = defaultdict(int)
        for res in reservations:
            hour = res['time'].strftime('%H:00')
            hourly_data[hour] = res['count']
        
        # Créneaux standards
        standard_hours = ['12:00', '13:00', '14:00', '19:00', '20:00', '21:00']
        result = []
        for hour in standard_hours:
            result.append(hourly_data.get(hour, 0))
        
        return result
    
    def get_peak_hour_today(self):
        """Retourne l'heure de pointe d'aujourd'hui - COUNT GUESTS NOT RESERVATIONS"""
        today = timezone.now().date()
        peak_hour = self.filter(
            date=today,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']
        ).values('time').annotate(
            total_guests=Sum('number_of_guests')  # Count guests, not reservations
        ).order_by('-total_guests').first()
        
        if peak_hour and peak_hour['total_guests'] > 0:
            return peak_hour['time'].strftime('%H:%M')
        return None


class Reservation(models.Model):
    """Réservations des clients - UPDATED WITH FRENCH STATUS AND AUTO-MIGRATION"""
    STATUS_CHOICES = [
        # French statuses (primary)
        ('En attente', 'En attente'),
        ('Confirmée', 'Confirmée'),
        ('Annulée', 'Annulée'),
        ('Terminée', 'Terminée'),
    ]
    
    # Informations client
    customer_name = models.CharField(max_length=100, verbose_name="Nom du client")
    customer_email = models.EmailField(blank=True, null=True, verbose_name="Email")
    customer_phone = models.CharField(max_length=20, verbose_name="Téléphone")
    
    # Détails de la réservation
    date = models.DateField(verbose_name="Date")
    time = models.TimeField(verbose_name="Heure")
    number_of_guests = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name="Nombre de personnes"
    )
    
    # Statut et notes
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='En attente',  # Changed default to French
        verbose_name="Statut"
    )
    special_requests = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Demandes spéciales"
    )
    
    # Champs additionnels pour le dashboard
    table_number = models.IntegerField(blank=True, null=True, verbose_name="Numéro de table")
    confirmed_at = models.DateTimeField(blank=True, null=True, verbose_name="Confirmé le")
    cancelled_at = models.DateTimeField(blank=True, null=True, verbose_name="Annulé le")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    objects = ReservationManager()
    
    def __str__(self):
        return f"{self.customer_name} - {self.date} {self.time} ({self.number_of_guests} pers.)"
    
    def save(self, *args, **kwargs):
        """Override save pour auto-migration des status et timestamps - UPDATED WITH AUTO-MIGRATION"""
        
        # AUTO-MIGRATION DES STATUS ANGLAIS VERS FRANÇAIS
        status_migration = {
            'pending': 'En attente',
            'confirmed': 'Confirmée',
            'cancelled': 'Annulée',
            'completed': 'Terminée'
        }
        
        # Auto-migration si nécessaire
        if self.status in status_migration:
            print(f"🔄 Auto-migration: {self.status} → {status_migration[self.status]} for {self.customer_name}")
            self.status = status_migration[self.status]
        
        # Gestion des timestamps de statut (code existant amélioré)
        if self.pk:
            try:
                old_instance = Reservation.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    if self.status in ['confirmed', 'Confirmée'] and not self.confirmed_at:
                        self.confirmed_at = timezone.now()
                    elif self.status in ['cancelled', 'Annulée'] and not self.cancelled_at:
                        self.cancelled_at = timezone.now()
            except Reservation.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-date', '-time']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['date', 'time']),
            models.Index(fields=['status']),
        ]
    
    @property
    def is_today(self):
        """Vérifie si la réservation est pour aujourd'hui"""
        return self.date == timezone.now().date()
    
    @property
    def is_past(self):
        """Vérifie si la réservation est passée"""
        now = timezone.now()
        reservation_datetime = timezone.datetime.combine(self.date, self.time)
        reservation_datetime = timezone.make_aware(reservation_datetime)
        return reservation_datetime < now
    
    @property
    def is_upcoming(self):
        """Vérifie si la réservation est à venir (dans les 2 prochaines heures)"""
        if not self.is_today:
            return False
        
        now = timezone.now()
        reservation_datetime = timezone.datetime.combine(self.date, self.time)
        reservation_datetime = timezone.make_aware(reservation_datetime)
        
        return reservation_datetime > now and reservation_datetime <= now + timedelta(hours=2)
    
    @property
    def status_badge_class(self):
        """Retourne la classe CSS pour le badge de statut - UPDATED WITH FRENCH STATUS"""
        status_classes = {
            # English statuses
            'pending': 'status-pending',
            'confirmed': 'status-confirmed',
            'cancelled': 'status-cancelled',
            'completed': 'status-confirmed',
            # French statuses
            'En attente': 'status-pending',
            'Confirmée': 'status-confirmed',
            'Annulée': 'status-cancelled',
            'Terminée': 'status-confirmed'
        }
        return status_classes.get(self.status, 'status-pending')
    
    def get_time_until_reservation(self):
        """Retourne le temps jusqu'à la réservation"""
        if not self.is_today:
            return None
        
        now = timezone.now()
        reservation_datetime = timezone.datetime.combine(self.date, self.time)
        reservation_datetime = timezone.make_aware(reservation_datetime)
        
        if reservation_datetime < now:
            return "Passée"
        
        diff = reservation_datetime - now
        hours = diff.total_seconds() // 3600
        minutes = (diff.total_seconds() % 3600) // 60
        
        if hours > 0:
            return f"Dans {int(hours)}h {int(minutes)}min"
        else:
            return f"Dans {int(minutes)}min"


class TimeSlotManager(models.Manager):
    """Manager pour les créneaux horaires"""
    
    def active(self):
        """Créneaux actifs seulement"""
        return self.filter(is_active=True)
    
    def get_next_available(self, date=None):
        """Trouve le prochain créneau disponible"""
        if date is None:
            date = timezone.now().date()
        
        for slot in self.active().order_by('time'):
            if slot.is_available(date):
                return slot
        return None


class TimeSlot(models.Model):
    """Créneaux horaires disponibles"""
    time = models.TimeField(verbose_name="Heure")
    max_reservations = models.IntegerField(
        default=10, 
        verbose_name="Nombre max de réservations"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    objects = TimeSlotManager()
    
    def __str__(self):
        return f"{self.time.strftime('%H:%M')}"
    
    class Meta:
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"
        ordering = ['time']
    
    def available_slots(self, date):
        """Retourne le nombre de créneaux disponibles pour une date donnée - UPDATED WITH FRENCH STATUS"""
        reservations_count = Reservation.objects.filter(
            date=date,
            time=self.time,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']  # Support both
        ).count()
        return max(0, self.max_reservations - reservations_count)
    
    def is_available(self, date):
        """Vérifie si ce créneau est disponible pour une date donnée"""
        return self.available_slots(date) > 0
    
    def get_reservations_for_date(self, date):
        """Retourne les réservations pour ce créneau à une date donnée - UPDATED WITH FRENCH STATUS"""
        return Reservation.objects.filter(
            date=date,
            time=self.time,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']  # Support both
        ).select_related()


class SpecialDateManager(models.Manager):
    """Manager pour les dates spéciales"""
    
    def upcoming(self):
        """Dates spéciales à venir"""
        return self.filter(date__gte=timezone.now().date())
    
    def closures(self):
        """Fermetures seulement"""
        return self.filter(is_closed=True)
    
    def upcoming_events(self):
        """Événements à venir (non fermetures)"""
        return self.upcoming().filter(is_closed=False)
    
    def get_closure_count(self):
        """Nombre de fermetures à venir"""
        return self.upcoming().closures().count()


class SpecialDate(models.Model):
    """Dates spéciales (fermetures exceptionnelles, horaires modifiés)"""
    date = models.DateField(verbose_name="Date")
    is_closed = models.BooleanField(default=False, verbose_name="Fermé")
    special_opening_time = models.TimeField(blank=True, null=True, verbose_name="Ouverture spéciale")
    special_closing_time = models.TimeField(blank=True, null=True, verbose_name="Fermeture spéciale")
    reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="Raison")
    
    objects = SpecialDateManager()
    
    def __str__(self):
        if self.is_closed:
            return f"Fermé le {self.date} - {self.reason or 'Pas de raison'}"
        return f"Horaires modifiés le {self.date}"
    
    class Meta:
        verbose_name = "Date spéciale"
        verbose_name_plural = "Dates spéciales"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['date', 'is_closed']),
        ]
    
    @property
    def is_today(self):
        """Vérifie si c'est aujourd'hui"""
        return self.date == timezone.now().date()
    
    @property
    def is_upcoming(self):
        """Vérifie si c'est à venir"""
        return self.date > timezone.now().date()
    
    @property
    def days_until(self):
        """Nombre de jours jusqu'à cette date"""
        if not self.is_upcoming:
            return 0
        return (self.date - timezone.now().date()).days


# SIGNALS FOR NOTIFICATION INTEGRATION
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Reservation)
def reservation_saved(sender, instance, created, **kwargs):
    """Signal quand une réservation est sauvegardée - ENHANCED WITH NOTIFICATIONS"""
    if created:
        # Nouvelle réservation - créer notification pour le staff
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                Notification.objects.create(
                    user=admin_user,
                    title="🍽️ Nouvelle Réservation!",
                    message=f"Nouvelle réservation de {instance.customer_name} pour {instance.number_of_guests} personnes le {instance.date.strftime('%d/%m/%Y')} à {instance.time.strftime('%H:%M')}.",
                    notification_type="new_reservation",
                    related_reservation=instance
                )
                print(f"📝 Nouvelle réservation créée: {instance.customer_name} ({instance.status})")
        except Exception as e:
            print(f"❌ Erreur création notification: {e}")
    
    elif instance.status in ['Confirmée', 'confirmed']:
        # Réservation confirmée - créer notification
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                Notification.objects.create(
                    user=admin_user,
                    title="✅ Réservation Confirmée",
                    message=f"Réservation de {instance.customer_name} confirmée pour le {instance.date.strftime('%d/%m/%Y')} à {instance.time.strftime('%H:%M')}.",
                    notification_type="reservation_confirmed",
                    related_reservation=instance
                )
                print(f"✅ Réservation confirmée: {instance.customer_name}")
        except Exception as e:
            print(f"❌ Erreur création notification: {e}")


# Utility function to get restaurant info
def get_restaurant_info():
    """Helper function to get the single restaurant instance"""
    return RestaurantInfo.load()


# UTILITY FUNCTIONS FOR STATUS MIGRATION
def migrate_all_reservations_to_french():
    """Utility function to migrate all reservations to French status"""
    status_mapping = {
        'pending': 'En attente',
        'confirmed': 'Confirmée',
        'cancelled': 'Annulée',
        'completed': 'Terminée'
    }
    
    total_migrated = 0
    
    for old_status, new_status in status_mapping.items():
        count = Reservation.objects.filter(status=old_status).update(status=new_status)
        if count > 0:
            print(f"✅ Migré {count} réservations: {old_status} → {new_status}")
            total_migrated += count
    
    print(f"🎉 Migration terminée ! Total: {total_migrated} réservations")
    return total_migrated


def get_status_distribution():
    """Get current status distribution for debugging"""
    print("📊 Distribution actuelle des status:")
    
    # All unique statuses
    all_statuses = Reservation.objects.values_list('status', flat=True).distinct()
    
    for status in all_statuses:
        count = Reservation.objects.filter(status=status).count()
        print(f"  '{status}': {count} réservations")
    
    return dict([(status, Reservation.objects.filter(status=status).count()) for status in all_statuses])