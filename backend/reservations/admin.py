# reservations/admin.py - COMPLETE VERSION WITH NOTIFICATIONS
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from .models import RestaurantInfo, Reservation, TimeSlot, SpecialDate, Notification, get_restaurant_info

# IMPORTANT: Clear any existing registrations to prevent duplicates
from django.contrib.admin.sites import site

# Unregister all models first to avoid conflicts
for model in [RestaurantInfo, Reservation, TimeSlot, SpecialDate, Notification]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass

def get_dashboard_metrics():
    """Get dashboard metrics directly - FIXED VERSION WITH CORRECT CHART DATA AND FRENCH STATUS"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Get restaurant instance (single instance)
    restaurant = get_restaurant_info()
    
    # Calculate metrics - UPDATED WITH FRENCH STATUS
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
        'available_tables': get_available_tables_count(today),
        
        'peak_hour': get_peak_hour_today(today),
        'next_available_slot': get_next_available_slot(),
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        'daily_average': round(Reservation.objects.filter(date__gte=month_start).count() / max(1, (today - month_start).days + 1), 1),
        
        # Restaurant info for display
        'restaurant_name': restaurant.name,
        'restaurant_phone': restaurant.phone,
        'restaurant_email': restaurant.email,
        'restaurant_address': restaurant.address,
        'restaurant_capacity': restaurant.capacity,
        
        # Notification metrics
        'unread_notifications': Notification.objects.filter(is_read=False).count(),
        'today_notifications': Notification.objects.filter(created_at__date=today).count(),
    }
    
    # Chart data - FIXED: Use actual reservation times
    chart_data = {
        'weekly_reservations': {
            'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'data': get_weekly_stats(week_start)
        },
        'daily_time_slots': get_correct_daily_time_slots_data(today)  # ← NOUVELLE FONCTION CORRIGÉE
    }
    
    return metrics, chart_data

def get_correct_daily_time_slots_data(date):
    """Get reservation data by ACTUAL reservation times - CORRECT VERSION FOR ADMIN"""
    from collections import defaultdict
    
    print(f"🔍 ADMIN CHART DEBUG - Getting data for date: {date}")
    
    # Get all reservations for today
    todays_reservations = Reservation.objects.filter(date=date).order_by('time')
    
    print(f"🔍 ADMIN CHART DEBUG - Found {todays_reservations.count()} reservations")
    
    if not todays_reservations.exists():
        print("🔍 ADMIN CHART DEBUG - No reservations, returning empty data")
        return {
            'labels': [],
            'data': []
        }
    
    # Count reservations by actual time - ONLY use actual reservation times
    time_counts = defaultdict(int)
    
    for reservation in todays_reservations:
        time_str = reservation.time.strftime('%H:%M')
        time_counts[time_str] += 1
        print(f"🔍 ADMIN CHART DEBUG - Reservation: {reservation.customer_name} at {time_str} (status: {reservation.status})")
    
    # Sort times and prepare data - CRITICAL: Only include times that have reservations
    sorted_times = sorted(time_counts.keys())
    labels = sorted_times
    data = [time_counts[time] for time in sorted_times]
    
    print(f"🔍 ADMIN CHART DEBUG - Final labels: {labels}")
    print(f"🔍 ADMIN CHART DEBUG - Final data: {data}")
    print(f"🔍 ADMIN CHART DEBUG - Time counts: {dict(time_counts)}")
    
    return {
        'labels': labels,
        'data': data
    }

def get_available_tables_count(date):
    """Calculate available tables for given date - UPDATED WITH FRENCH STATUS"""
    restaurant = get_restaurant_info()
    
    reservations_count = Reservation.objects.filter(
        date=date,
        status__in=['Confirmée', 'En attente']  # Changed from ['confirmed', 'pending']
    ).count()
    
    return max(0, restaurant.number_of_tables - reservations_count)

def get_peak_hour_today(date):
    """Find the busiest hour for today - UPDATED TO COUNT GUESTS, NOT RESERVATIONS"""
    peak_hour = Reservation.objects.filter(
        date=date,
        status__in=['En attente', 'Confirmée']  # French status
    ).values('time').annotate(
        total_guests=Sum('number_of_guests')  # ← CHANGEMENT ICI: Sum au lieu de Count
    ).order_by('-total_guests').first()  # ← ET ICI: order by total_guests
    
    if peak_hour and peak_hour['total_guests'] > 0:
        return peak_hour['time'].strftime('%H:%M')
    return None

def get_next_available_slot():
    """Find next available time slot - UPDATED WITH FRENCH STATUS"""
    try:
        now = timezone.localtime(timezone.now())
        current_date = now.date()
        current_time = now.time()
        
        # Look for available slots in the next 7 days
        for days_ahead in range(7):
            check_date = current_date + timedelta(days=days_ahead)
            time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
            
            for slot in time_slots:
                # If it's today, skip past time slots (with 30min buffer)
                if days_ahead == 0:
                    time_with_buffer = (datetime.combine(current_date, current_time) + timedelta(minutes=30)).time()
                    if slot.time <= time_with_buffer:
                        continue
                
                # Count current reservations for this slot - UPDATED WITH FRENCH STATUS
                reservations_count = Reservation.objects.filter(
                    date=check_date,
                    time=slot.time,
                    status__in=['Confirmée', 'En attente']  # Changed from ['confirmed', 'pending']
                ).count()
                
                # Check if slot is available
                if reservations_count < slot.max_reservations:
                    if days_ahead == 0:
                        return f"Aujourd'hui {slot.time.strftime('%H:%M')}"
                    elif days_ahead == 1:
                        return f"Demain {slot.time.strftime('%H:%M')}"
                    else:
                        return f"{check_date.strftime('%d/%m')} à {slot.time.strftime('%H:%M')}"
        
        return "Aucun créneau disponible cette semaine"
        
    except Exception as e:
        return "Vérification en cours..."

def get_weekly_stats(week_start):
    """Get reservation data for the current week"""
    data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        count = Reservation.objects.filter(date=day).count()
        data.append(count)
    return data

def get_hourly_stats_today(date):
    """Get reservation data by time slots for today - DEPRECATED, USE get_correct_daily_time_slots_data INSTEAD"""
    # This function is kept for backward compatibility but should not be used
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
    data = []
    
    for slot in time_slots:
        count = Reservation.objects.filter(
            date=date,
            time=slot.time
        ).count()
        data.append(count)
    
    # If no time slots, return default data
    if not data:
        data = [0, 0, 0, 0, 0, 0]
    
    return data

def custom_admin_index(request, extra_context=None):
    """Custom admin index that shows unified dashboard with sidebar and REAL DATA"""
    try:
        # Get dashboard metrics
        metrics, chart_data = get_dashboard_metrics()
        
        # Recent reservations (last 24 hours)
        now = timezone.now()
        recent_reservations = Reservation.objects.filter(
            created_at__gte=now - timedelta(hours=24)
        ).order_by('-created_at')[:10]
        
        # Recent notifications
        recent_notifications = Notification.objects.filter(
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Today's schedule
        today = timezone.now().date()
        todays_schedule = Reservation.objects.filter(
            date=today
        ).order_by('time')
        
        # Get admin context
        app_list = admin.site.get_app_list(request)
        
        context = {
            'title': 'Administration - Resto Pêcheur',
            'app_list': app_list,
            'available_apps': app_list,
            'metrics': metrics,  # Keep this for nested access
            'chart_data': chart_data,
            'recent_reservations': recent_reservations,
            'recent_notifications': recent_notifications,
            'todays_schedule': todays_schedule,
            # ADD THESE LINES - Flatten the metrics for direct access
            'today_reservations': metrics['today_reservations'],
            'today_guests': metrics['today_guests'],
            'available_tables': metrics['available_tables'],
            'total_tables': metrics['total_tables'],
            'occupancy_rate': metrics['occupancy_rate'],
            'restaurant_name': metrics['restaurant_name'],
            'restaurant_capacity': metrics['restaurant_capacity'],
            'unread_notifications': metrics['unread_notifications'],
        }
        context.update(extra_context or {})
        
        return TemplateResponse(request, 'admin/unified_dashboard_with_sidebar.html', context)
    
    except Exception as e:
        # Fallback to default admin if there's an error
        from django.contrib.admin.sites import AdminSite
        return AdminSite().index(request, extra_context)
    
# Override the admin site index
admin.site.index = custom_admin_index

class NotificationAdmin(admin.ModelAdmin):
    """Admin for notifications"""
    list_display = ['user', 'title', 'notification_type', 'is_read', 'related_reservation', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message', 'related_reservation__customer_name']
    readonly_fields = ['created_at', 'related_reservation']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Détails de la Notification', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('Statut', {
            'fields': ('is_read',)
        }),
        ('Liens', {
            'fields': ('related_reservation',),
            'classes': ('collapse',)
        }),
        ('Horodatage', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marquées comme lues.')
    mark_as_read.short_description = "Marquer comme lues"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notifications marquées comme non lues.')
    mark_as_unread.short_description = "Marquer comme non lues"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'related_reservation')

class RestaurantInfoAdmin(admin.ModelAdmin):
    """Admin for single restaurant configuration - FIXED VERSION"""
    
    fieldsets = (
        ('Restaurant Resto Pêcheur', {
            'fields': ('address', 'phone', 'email', 'description'),
            'description': 'Informations de contact pour Resto Pêcheur'
        }),
        ('Capacité et Tables', {
            'fields': ('capacity', 'number_of_tables'),
            'description': 'Configuration de la capacité du restaurant'
        }),
        ('Horaires d\'Ouverture', {
            'fields': ('opening_time', 'closing_time'),
            'description': 'Horaires d\'ouverture standard'
        }),
        ('Fermetures Hebdomadaires', {
            'fields': (
                'closed_on_monday', 'closed_on_tuesday', 'closed_on_wednesday',
                'closed_on_thursday', 'closed_on_friday', 'closed_on_saturday', 'closed_on_sunday'
            ),
            'classes': ('collapse',),
            'description': 'Jours de fermeture hebdomadaire réguliers'
        }),
    )
    
    # FIXED: Prevent multiple restaurants
    def has_add_permission(self, request):
        """Allow add only if no restaurant exists"""
        return False  # Always prevent adding since we use singleton
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of restaurant info"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Always redirect to single restaurant edit"""
        restaurant = get_restaurant_info()  # This will create if doesn't exist
        return redirect(f'/admin/reservations/restaurantinfo/{restaurant.pk}/change/')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Ensure we're always editing the single restaurant"""
        restaurant = get_restaurant_info()
        if str(object_id) != str(restaurant.pk):
            return redirect(f'/admin/reservations/restaurantinfo/{restaurant.pk}/change/')
        
        extra_context = extra_context or {}
        extra_context['title'] = 'Configuration Restaurant - Resto Pêcheur'
        return super().change_view(request, object_id, form_url, extra_context)

class ReservationAdmin(admin.ModelAdmin):
    """Admin for reservations - UPDATED WITH FRENCH STATUS SUPPORT"""
    list_display = [
        'customer_name', 'customer_phone', 'date', 'time', 
        'number_of_guests', 'status', 'colored_status', 'created_at', 'is_today_reservation'
    ]
    list_filter = ['status', 'date', 'number_of_guests', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email']
    list_editable = ['status']
    date_hierarchy = 'date'
    ordering = ['-date', '-time']
    actions = ['mark_as_confirmed', 'mark_as_cancelled', 'mark_as_completed']
    
    fieldsets = (
        ('Information Client', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Détails Réservation', {
            'fields': ('date', 'time', 'number_of_guests', 'status', 'table_number')
        }),
        ('Informations Supplémentaires', {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        }),
        ('Historique', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
            'classes': ('collapse',),
            'description': 'Ces champs sont automatiquement mis à jour'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at', 'cancelled_at']
    
    def colored_status(self, obj):
        # Support both French and English status values
        colors = {
            # English statuses
            'pending': '#ff8f00',
            'confirmed': '#4caf50',
            'cancelled': '#f44336',
            'completed': '#2196f3',
            # French statuses
            'En attente': '#ff8f00',
            'Confirmée': '#4caf50',
            'Annulée': '#f44336',
            'Terminée': '#2196f3',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">●</span>',
            colors.get(obj.status, '#666')
        )
    colored_status.short_description = 'État'
    
    def is_today_reservation(self, obj):
        try:
            today = timezone.now().date()
            if obj.date == today:
                return format_html('<span style="color: #4caf50; font-weight: bold;">Aujourd\'hui</span>')
            elif obj.date > today:
                return format_html('<span style="color: #ff9800; font-weight: bold;">À venir</span>')
            else:
                return format_html('<span style="color: #666;">Passée</span>')
        except:
            return '-'
    is_today_reservation.short_description = 'Timing'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related().order_by('-date', '-time')
    
    def mark_as_confirmed(self, request, queryset):
        # Support both English and French - use French by default
        updated = queryset.update(status='Confirmée')
        self.message_user(request, f'{updated} réservations marquées comme confirmées.')
    mark_as_confirmed.short_description = "Marquer comme confirmées"
    
    def mark_as_cancelled(self, request, queryset):
        # Support both English and French - use French by default
        updated = queryset.update(status='Annulée')
        self.message_user(request, f'{updated} réservations annulées.')
    mark_as_cancelled.short_description = "Annuler les réservations"
    
    def mark_as_completed(self, request, queryset):
        # Support both English and French - use French by default
        updated = queryset.update(status='Terminée')
        self.message_user(request, f'{updated} réservations marquées comme terminées.')
    mark_as_completed.short_description = "Marquer comme terminées"

class TimeSlotAdmin(admin.ModelAdmin):
    """Admin for time slots - UPDATED WITH FRENCH STATUS SUPPORT"""
    list_display = ['time', 'max_reservations', 'is_active', 'current_reservations', 'availability_status']
    list_filter = ['is_active']
    ordering = ['time']
    list_editable = ['max_reservations', 'is_active']
    
    def current_reservations(self, obj):
        today = timezone.now().date()
        # Support both French and English statuses
        count = Reservation.objects.filter(
            time=obj.time,
            date=today,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']
        ).count()
        return f"{count}/{obj.max_reservations}"
    current_reservations.short_description = 'Réservations Aujourd\'hui'
    
    def availability_status(self, obj):
        try:
            today = timezone.now().date()
            # Support both French and English statuses
            reservations_count = Reservation.objects.filter(
                time=obj.time,
                date=today,
                status__in=['pending', 'confirmed', 'En attente', 'Confirmée']
            ).count()
            available = obj.max_reservations - reservations_count
            
            if available <= 0:
                color = '#f44336'
                status = 'Complet'
            elif available <= 2:
                color = '#ff9800'
                status = 'Presque complet'
            else:
                color = '#4caf50'
                status = 'Disponible'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span> ({} places)',
                color, status, available
            )
        except:
            return format_html('<span style="color: #999;">N/A</span>')
    availability_status.short_description = 'Disponibilité'

class SpecialDateAdmin(admin.ModelAdmin):
    list_display = ['date', 'reason', 'is_closed', 'is_upcoming_date', 'days_until_date']
    list_filter = ['is_closed', 'date']
    date_hierarchy = 'date'
    ordering = ['-date']
    
    fieldsets = (
        ('Date et Raison', {
            'fields': ('date', 'reason', 'is_closed')
        }),
        ('Horaires Spéciaux', {
            'fields': ('special_opening_time', 'special_closing_time'),
            'classes': ('collapse',),
            'description': 'Laisser vide si fermé ou pour garder les horaires normaux'
        }),
    )
    
    def is_upcoming_date(self, obj):
        try:
            today = timezone.now().date()
            if obj.date == today:
                return format_html('<span style="color: #f44336; font-weight: bold;">Aujourd\'hui</span>')
            elif obj.date > today:
                return format_html('<span style="color: #ff9800; font-weight: bold;">À venir</span>')
            else:
                return format_html('<span style="color: #666;">Passée</span>')
        except:
            return format_html('<span style="color: #999;">N/A</span>')
    is_upcoming_date.short_description = 'Statut'
    
    def days_until_date(self, obj):
        try:
            today = timezone.now().date()
            if obj.date == today:
                return "Aujourd'hui"
            elif obj.date > today:
                days = (obj.date - today).days
                return f"Dans {days} jour{'s' if days > 1 else ''}"
            else:
                return "-"
        except:
            return "-"
    days_until_date.short_description = 'Échéance'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(date__gte=timezone.now().date() - timedelta(days=30))

# FIXED: Register models only once to prevent duplicates
admin.site.register(Notification, NotificationAdmin)
admin.site.register(RestaurantInfo, RestaurantInfoAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(SpecialDate, SpecialDateAdmin)

# Customize admin site - REMOVE ALL BRANDING
admin.site.site_header = ""
admin.site.site_title = ""
admin.site.index_title = ""