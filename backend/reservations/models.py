from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Restaurant(models.Model):
    """Informations du restaurant"""
    name = models.CharField(max_length=100, default="Resto Pêcheur")
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(default=50)  # Nombre total de couverts
    
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
    
    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"


class Reservation(models.Model):
    """Réservations des clients"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
        ('completed', 'Terminée'),
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
        default='pending',
        verbose_name="Statut"
    )
    special_requests = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Demandes spéciales"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    def __str__(self):
        return f"{self.customer_name} - {self.date} {self.time} ({self.number_of_guests} pers.)"
    
    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-date', '-time']  # Tri par date et heure décroissantes
    
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


class TimeSlot(models.Model):
    """Créneaux horaires disponibles"""
    time = models.TimeField(verbose_name="Heure")
    max_reservations = models.IntegerField(
        default=10, 
        verbose_name="Nombre max de réservations"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    def __str__(self):
        return f"{self.time.strftime('%H:%M')}"
    
    class Meta:
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"
        ordering = ['time']
    
    def available_slots(self, date):
        """Retourne le nombre de créneaux disponibles pour une date donnée"""
        reservations_count = Reservation.objects.filter(
            date=date,
            time=self.time,
            status__in=['pending', 'confirmed']
        ).count()
        return max(0, self.max_reservations - reservations_count)
    
    def is_available(self, date):
        """Vérifie si ce créneau est disponible pour une date donnée"""
        return self.available_slots(date) > 0


class SpecialDate(models.Model):
    """Dates spéciales (fermetures exceptionnelles, horaires modifiés)"""
    date = models.DateField(verbose_name="Date")
    is_closed = models.BooleanField(default=False, verbose_name="Fermé")
    special_opening_time = models.TimeField(blank=True, null=True, verbose_name="Ouverture spéciale")
    special_closing_time = models.TimeField(blank=True, null=True, verbose_name="Fermeture spéciale")
    reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="Raison")
    
    def __str__(self):
        if self.is_closed:
            return f"Fermé le {self.date} - {self.reason or 'Pas de raison'}"
        return f"Horaires modifiés le {self.date}"
    
    class Meta:
        verbose_name = "Date spéciale"
        verbose_name_plural = "Dates spéciales"
        ordering = ['-date']