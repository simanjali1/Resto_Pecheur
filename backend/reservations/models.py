from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta, date
from collections import defaultdict
import uuid


# ENHANCED NOTIFICATION MODEL WITH EMAIL TRACKING

class Notification(models.Model):
    """Admin notification system with email tracking capabilities"""
    
    MESSAGE_TYPES = [
        ('new_reservation', '📨 Nouvelle Réservation'),
        ('email_failed', '❌ Email Échoué'), 
        ('email_success', '✅ Email Envoyé'),
        ('reservation_confirmed', '✅ Confirmée'),
        ('reservation_cancelled', '❌ Annulée'),
        ('info', 'ℹ️ Information'),
    ]
    
    PRIORITY_LEVELS = [
        ('urgent', '🔴 Urgent'),     # Email failed, needs phone call
        ('normal', '🟡 Normal'),     # New reservation, confirmation
        ('info', '🟢 Info'),         # General information
    ]
    
    # Core message info
    title = models.CharField(max_length=200, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    message_type = models.CharField(
        max_length=30, 
        choices=MESSAGE_TYPES, 
        default='info',
        verbose_name="Type"
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_LEVELS, 
        default='normal',
        verbose_name="Priorité"
    )
    
    # Related reservation (optional)
    related_reservation = models.ForeignKey(
        'Reservation', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Réservation liée"
    )
    
    # Admin read status
    is_read = models.BooleanField(default=False, verbose_name="Lu par admin")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lu par admin le")
    
    # ✅ EMAIL TRACKING FIELDS
    email_sent = models.BooleanField(default=False, verbose_name="Email envoyé")
    email_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Email envoyé le")
    
    # Client email tracking
    email_opened_by_client = models.BooleanField(default=False, verbose_name="Email ouvert par client")
    email_opened_at = models.DateTimeField(null=True, blank=True, verbose_name="Email ouvert le")
    client_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP du client")
    client_user_agent = models.TextField(null=True, blank=True, verbose_name="Navigateur client")
    
    # Tracking token for email links
    tracking_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name="Token de suivi")
    
    # Admin user (usually superuser)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_read']),
            models.Index(fields=['priority', 'is_read']),
            # Email tracking indexes
            models.Index(fields=['tracking_token']),
            models.Index(fields=['email_opened_by_client']),
            models.Index(fields=['is_read', 'email_opened_by_client']),
        ]
    
    def __str__(self):
        """Enhanced __str__ method showing CLIENT email tracking status"""
        priority_icon = "🔴" if self.priority == 'urgent' else "🟡" if self.priority == 'normal' else "🟢"
        
        # ✅ EMAIL TRACKING STATUS (what client did with the email)
        if not self.email_sent:
            read_status = "●"     # ● Red dot = Email failed to send
        elif self.email_sent and self.email_opened_by_client:
            read_status = "✓✓"   # ✓✓ Double checkmarks = Client opened/seen the email
        elif self.email_sent and not self.email_opened_by_client:
            read_status = "✓"    # ✓ Single checkmark = Email sent but client hasn't seen it yet
        else:
            read_status = "●"     # Default fallback
            
        return f"{priority_icon} {read_status} {self.title}"
    
    @property
    def admin_read_display(self):
        """Separate property for admin read status"""
        return "Lu" if self.is_read else "Non lu"

    @property 
    def email_tracking_display(self):
        """Detailed email tracking status for admin interface"""
        if not self.email_sent:
            return "❌ Email non envoyé"
        elif self.email_opened_by_client:
            return f"👁️ Email ouvert {self.time_since_opened}"
        else:
            return f"📤 Email envoyé {self.time_since_sent}"
    
    def mark_as_read(self):
        """Mark message as read by admin"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    # ✅ EMAIL TRACKING METHODS
    def mark_email_as_opened(self, request=None):
        """Mark email as opened by client"""
        if not self.email_opened_by_client:
            self.email_opened_by_client = True
            self.email_opened_at = timezone.now()
            
            # Capture client info if request provided
            if request:
                self.client_ip = self.get_client_ip(request)
                self.client_user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            self.save(update_fields=[
                'email_opened_by_client', 
                'email_opened_at', 
                'client_ip', 
                'client_user_agent'
            ])
            
            print(f"📧 Email opened by client for: {self.title}")
    
    def mark_email_as_sent(self):
        """Mark email as successfully sent"""
        self.email_sent = True
        self.email_sent_at = timezone.now()
        self.save(update_fields=['email_sent', 'email_sent_at'])
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    # ✅ EMAIL STATUS PROPERTIES
    @property
    def email_status_display(self):
        """Display email status for admin"""
        if not self.email_sent:
            return "❌ Non envoyé"
        elif self.email_opened_by_client:
            return f"👁️ Ouvert {self.time_since_opened}"
        else:
            return f"📤 Envoyé {self.time_since_sent}"
    
    @property
    def time_since_opened(self):
        """Time since email was opened"""
        if not self.email_opened_at:
            return ""
        
        diff = timezone.now() - self.email_opened_at
        if diff.days > 0:
            return f"il y a {diff.days}j"
        elif diff.seconds > 3600:
            return f"il y a {diff.seconds // 3600}h"
        else:
            return f"il y a {diff.seconds // 60}min"
    
    @property
    def time_since_sent(self):
        """Time since email was sent"""
        if not self.email_sent_at:
            return ""
        
        diff = timezone.now() - self.email_sent_at
        if diff.days > 0:
            return f"il y a {diff.days}j"
        elif diff.seconds > 3600:
            return f"il y a {diff.seconds // 3600}h"
        else:
            return f"il y a {diff.seconds // 60}min"
    
    # ✅ ENHANCED: Add email tracking summary property for admin display
    @property
    def admin_summary(self):
        """Summary for admin with email tracking info"""
        if not self.related_reservation:
            return self.message[:100] + "..." if len(self.message) > 100 else self.message
        
        # Base reservation info
        summary = f"📅 {self.reservation_date} à {self.reservation_time} | 👥 {self.related_reservation.number_of_guests} pers."
        
        # Add email tracking info
        if self.email_sent:
            if self.email_opened_by_client:
                summary += f" | {self.email_status_display}"
            else:
                summary += f" | 📧 Envoyé (non ouvert)"
        else:
            summary += f" | ❌ Email non envoyé"
        
        return summary
    
    # ✅ EMAIL TRACKING METHODS
    def get_tracking_url(self):
        """Get the tracking URL for this notification"""
        from django.conf import settings
        from django.urls import reverse
        
        try:
            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            tracking_url = reverse('email_tracking', kwargs={'token': self.tracking_token})
            return f"{base_url}{tracking_url}"
        except:
            return None
    
    def refresh_email_status(self):
        """Refresh the notification message with current email tracking status"""
        if not self.email_sent or not self.related_reservation:
            return False
        
        # Update any static tracking status with dynamic status
        old_message = self.message
        
        # Replace old tracking patterns with current status
        import re
        
        # Pattern 1: "📊 Tracking: Email non ouvert" or "📊 Tracking: Email ouvert"
        pattern1 = r"📊 Tracking: Email (non )?ouvert"
        replacement1 = f"📊 Status: {self.email_status_display}"
        
        # Pattern 2: Any line starting with "📊 Status:" (update it)
        pattern2 = r"📊 Status: .*"
        replacement2 = f"📊 Status: {self.email_status_display}"
        
        new_message = re.sub(pattern1, replacement1, old_message)
        new_message = re.sub(pattern2, replacement2, new_message)
        
        if new_message != old_message:
            self.message = new_message
            self.save(update_fields=['message'])
            return True
        
        return False
    
    # ✅ EXISTING: Properties (unchanged)
    @property
    def is_urgent(self):
        """Check if message is urgent"""
        return self.priority == 'urgent'
    
    @property
    def customer_name(self):
        """Get customer name from related reservation"""
        return self.related_reservation.customer_name if self.related_reservation else "N/A"
    
    @property
    def customer_phone(self):
        """Get customer phone from related reservation"""  
        return self.related_reservation.customer_phone if self.related_reservation else "N/A"
    
    @property
    def customer_email(self):
        """Get customer email from related reservation"""
        return self.related_reservation.customer_email if self.related_reservation else "N/A"
    
    @property
    def reservation_date(self):
        """Get reservation date"""
        if self.related_reservation:
            return self.related_reservation.date.strftime('%d/%m/%Y')
        return "N/A"
    
    @property
    def reservation_time(self):
        """Get reservation time"""
        if self.related_reservation:
            return self.related_reservation.time.strftime('%H:%M')
        return "N/A"
    
    @property
    def time_ago(self):
        """Human readable time since creation - USING DJANGO TIMEZONE ONLY"""
        from django.utils import timezone
        
        # Use Django's timezone-aware datetime
        # This respects the TIME_ZONE setting in settings.py (Africa/Casablanca)
        now = timezone.localtime(timezone.now())
        created_local = timezone.localtime(self.created_at)
        
        # Calculate difference
        diff = now - created_local
        
        if diff.days > 0:
            return f"Il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"Il y a {hours}h"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"Il y a {minutes}min"
        else:
            return "À l'instant"
    
    # ✅ CLASS METHODS
    @classmethod
    def create_simple_message(cls, title, message, message_type='info', priority='normal', reservation=None):
        """Helper method to create simple messages"""
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            return None
        
        return cls.objects.create(
            user=admin_user,
            title=title,
            message=message,
            message_type=message_type,
            priority=priority,
            related_reservation=reservation
        )
    
    @classmethod
    def mark_all_as_read(cls):
        """Mark all unread messages as read"""
        return cls.objects.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @classmethod
    def get_unread_count(cls):
        """Get count of unread messages"""
        return cls.objects.filter(is_read=False).count()
    
    @classmethod
    def get_urgent_count(cls):
        """Get count of urgent unread messages"""
        return cls.objects.filter(is_read=False, priority='urgent').count()
    
    @classmethod
    def cleanup_old_messages(cls, days=30):
        """Clean up old read messages"""
        cutoff_date = timezone.now() - timedelta(days=days)
        return cls.objects.filter(is_read=True, read_at__lt=cutoff_date).delete()
    
    # ✅ EMAIL TRACKING CLASS METHODS
    @classmethod
    def get_email_stats(cls, days=30):
        """Get email tracking statistics"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        notifications = cls.objects.filter(
            created_at__gte=cutoff_date,
            email_sent=True
        )
        
        total_sent = notifications.count()
        total_opened = notifications.filter(email_opened_by_client=True).count()
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        
        return {
            'total_sent': total_sent,
            'total_opened': total_opened,
            'open_rate': round(open_rate, 1),
            'period_days': days
        }


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
            'address': 'Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc',
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
    """Manager pour les dates spéciales - UPDATED FOR is_open FIELD"""
    
    def upcoming(self):
        """Dates spéciales à venir"""
        return self.filter(date__gte=timezone.now().date())
    
    def closures(self):
        """Fermetures seulement - UPDATED FOR is_open FIELD"""
        return self.filter(is_open=False)  # ✅ FIXED: Changed from is_closed=True
    
    def upcoming_events(self):
        """Événements à venir (non fermetures) - UPDATED FOR is_open FIELD"""
        return self.upcoming().filter(is_open=True)  # ✅ FIXED: Changed from is_closed=False
    
    def get_closure_count(self):
        """Nombre de fermetures à venir - UPDATED FOR is_open FIELD"""
        return self.upcoming().closures().count()


class SpecialDate(models.Model):
    """Dates spéciales (fermetures exceptionnelles, horaires modifiés) - FIXED WITH is_open FIELD"""
    date = models.DateField(verbose_name="Date")
    
    # ✅ FIXED: Changed from is_closed to is_open to match views.py
    is_open = models.BooleanField(default=True, verbose_name="Ouvert")
    
    special_opening_time = models.TimeField(blank=True, null=True, verbose_name="Ouverture spéciale")
    special_closing_time = models.TimeField(blank=True, null=True, verbose_name="Fermeture spéciale")
    reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="Raison")
    
    objects = SpecialDateManager()
    
    # ✅ ADDED: Add special_hours property for API compatibility
    @property
    def special_hours(self):
        """Format special hours for API response"""
        if self.special_opening_time and self.special_closing_time:
            return f"{self.special_opening_time.strftime('%H:%M')} - {self.special_closing_time.strftime('%H:%M')}"
        return None
    
    def __str__(self):
        if not self.is_open:  # ✅ FIXED: Changed from is_closed to not is_open
            return f"Fermé le {self.date} - {self.reason or 'Pas de raison'}"
        return f"Horaires modifiés le {self.date}"
    
    class Meta:
        verbose_name = "Date spéciale"
        verbose_name_plural = "Dates spéciales"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['date', 'is_open']),  # ✅ FIXED: Changed from is_closed
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


# ✅ NO MORE DUPLICATE SIGNALS HERE - All notification logic is in signals.py
# This prevents duplicate notifications when reservations are created/updated

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


# ✅ NEW: Utility functions for email tracking management
def refresh_all_notification_tracking():
    """Refresh all notification messages with current email tracking status"""
    try:
        notifications_with_emails = Notification.objects.filter(
            email_sent=True,
            related_reservation__isnull=False
        )
        
        updated_count = 0
        
        for notification in notifications_with_emails:
            if notification.refresh_email_status():
                updated_count += 1
        
        print(f"✅ Updated {updated_count} notifications with current tracking status")
        return updated_count
        
    except Exception as e:
        print(f"❌ Error refreshing notification tracking: {e}")
        return 0


def get_email_tracking_summary():
    """Get comprehensive email tracking summary"""
    try:
        # Get basic stats
        total_notifications = Notification.objects.filter(email_sent=True).count()
        opened_notifications = Notification.objects.filter(
            email_sent=True, 
            email_opened_by_client=True
        ).count()
        
        # Calculate open rate
        open_rate = (opened_notifications / total_notifications * 100) if total_notifications > 0 else 0
        
        # Get recent activity (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_notifications = Notification.objects.filter(
            email_sent=True,
            email_sent_at__gte=seven_days_ago
        )
        
        recent_opened = recent_notifications.filter(email_opened_by_client=True).count()
        recent_total = recent_notifications.count()
        recent_open_rate = (recent_opened / recent_total * 100) if recent_total > 0 else 0
        
        # Get customers who haven't opened emails
        unread_notifications = Notification.objects.filter(
            email_sent=True,
            email_opened_by_client=False,
            email_sent_at__gte=seven_days_ago
        ).select_related('related_reservation')
        
        summary = {
            'total_emails_sent': total_notifications,
            'total_emails_opened': opened_notifications,
            'overall_open_rate': round(open_rate, 1),
            'recent_emails_sent': recent_total,
            'recent_emails_opened': recent_opened,
            'recent_open_rate': round(recent_open_rate, 1),
            'unread_emails_count': unread_notifications.count(),
            'customers_need_followup': [
                {
                    'customer_name': n.customer_name,
                    'customer_email': n.customer_email,
                    'sent_at': n.email_sent_at.strftime('%d/%m/%Y %H:%M'),
                    'days_ago': (timezone.now() - n.email_sent_at).days
                }
                for n in unread_notifications[:10]  # Limit to 10
            ]
        }
        
        return summary
        
    except Exception as e:
        print(f"❌ Error getting email tracking summary: {e}")
        return None


def cleanup_old_email_tracking_data(days=90):
    """Clean up old email tracking data while preserving important statistics"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Only clean up very old, read notifications with no recent email activity
        old_notifications = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_date,
            email_sent_at__lt=cutoff_date
        ).exclude(
            # Keep notifications that were recently opened
            email_opened_at__gte=timezone.now() - timedelta(days=30)
        )
        
        # Log some stats before deletion
        tracking_stats = []
        for notification in old_notifications[:20]:  # Sample first 20
            if notification.email_sent:
                tracking_stats.append({
                    'customer': notification.customer_name,
                    'sent': notification.email_sent_at.strftime('%d/%m/%Y') if notification.email_sent_at else 'N/A',
                    'opened': notification.email_opened_by_client,
                    'opened_at': notification.email_opened_at.strftime('%d/%m/%Y') if notification.email_opened_at else 'N/A'
                })
        
        count = old_notifications.count()
        
        if count > 0:
            print(f"📊 Sample email tracking data before cleanup:")
            for stat in tracking_stats[:5]:
                status = "Opened" if stat['opened'] else "Not opened"
                print(f"  - {stat['customer']}: Sent {stat['sent']}, {status}")
            
            # Delete old notifications
            old_notifications.delete()
            print(f"✅ Cleaned up {count} old email tracking records")
        else:
            print("ℹ️ No old email tracking data to clean up")
        
        return count
        
    except Exception as e:
        print(f"❌ Error cleaning up email tracking data: {e}")
        return 0