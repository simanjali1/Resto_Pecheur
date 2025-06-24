# reservations/admin.py - COMPLETE OPTIMIZED VERSION
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from .models import Restaurant, Reservation, TimeSlot, SpecialDate

# First, unregister all models to avoid conflicts
try:
    admin.site.unregister(Restaurant)
    admin.site.unregister(Reservation)
    admin.site.unregister(TimeSlot)
    admin.site.unregister(SpecialDate)
except admin.sites.NotRegistered:
    pass

def get_dashboard_metrics():
    """Get dashboard metrics directly - OPTIMIZED VERSION"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Get restaurant instance
    restaurant = Restaurant.objects.first()
    
    # Calculate metrics
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
        'available_tables': get_available_tables_count(today),
        
        'peak_hour': get_peak_hour_today(today),
        'next_available_slot': get_next_available_slot(),
        'occupancy_rate': restaurant.get_occupancy_rate_today() if restaurant else 0,
        'daily_average': round(Reservation.objects.filter(date__gte=month_start).count() / max(1, (today - month_start).days + 1), 1),
    }
    
    # Chart data
    chart_data = {
        'weekly_reservations': {
            'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'data': get_weekly_stats(week_start)
        },
        'daily_time_slots': {
            'labels': ['12:00', '13:00', '14:00', '19:00', '20:00', '21:00'],
            'data': get_hourly_stats_today(today)
        },
    }
    
    return metrics, chart_data

def get_available_tables_count(date):
    """Calculate available tables for given date"""
    restaurant = Restaurant.objects.first()
    if not restaurant:
        return 20
    
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
    """Find next available time slot - OPTIMIZED VERSION WITHOUT DEBUG PRINTS"""
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
                
                # Count current reservations for this slot
                reservations_count = Reservation.objects.filter(
                    date=check_date,
                    time=slot.time,
                    status__in=['confirmed', 'pending']
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
        # Return a safe default if there's any error
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
    """Get reservation data by time slots for today"""
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
        
        # Today's schedule
        today = timezone.now().date()
        todays_schedule = Reservation.objects.filter(
            date=today
        ).order_by('time')
        
        # Get admin context
        app_list = admin.site.get_app_list(request)
        
        context = {
            'title': 'Tableau de Bord Unifié - Resto Pêcheur',
            'app_list': app_list,
            'available_apps': app_list,
            'metrics': metrics,
            'chart_data': chart_data,
            'recent_reservations': recent_reservations,
            'todays_schedule': todays_schedule,
        }
        context.update(extra_context or {})
        
        return TemplateResponse(request, 'admin/unified_dashboard_with_sidebar.html', context)
    
    except Exception as e:
        # Fallback to default admin if there's an error
        from django.contrib.admin.sites import AdminSite
        return AdminSite().index(request, extra_context)

# Override the admin site index
admin.site.index = custom_admin_index

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'capacity', 'number_of_tables', 'get_occupancy_rate']
    fieldsets = (
        ('Informations Générales', {
            'fields': ('name', 'address', 'phone', 'email', 'description')
        }),
        ('Capacité', {
            'fields': ('capacity', 'number_of_tables')
        }),
        ('Horaires', {
            'fields': ('opening_time', 'closing_time')
        }),
        ('Jours de Fermeture', {
            'fields': (
                'closed_on_monday', 'closed_on_tuesday', 'closed_on_wednesday',
                'closed_on_thursday', 'closed_on_friday', 'closed_on_saturday', 'closed_on_sunday'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_occupancy_rate(self, obj):
        try:
            rate = obj.get_occupancy_rate_today()
            color = '#4caf50' if rate < 70 else '#ff9800' if rate < 90 else '#f44336'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, rate
            )
        except:
            return format_html('<span style="color: #999;">N/A</span>')
    get_occupancy_rate.short_description = 'Taux Occupation Aujourd\'hui'
    
    def has_add_permission(self, request):
        return not Restaurant.objects.exists()

class ReservationAdmin(admin.ModelAdmin):
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
            'fields': ('date', 'time', 'number_of_guests', 'status')
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
        colors = {
            'pending': '#ff8f00',
            'confirmed': '#4caf50',
            'cancelled': '#f44336',
            'completed': '#2196f3',
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
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} réservations marquées comme confirmées.')
    mark_as_confirmed.short_description = "Marquer comme confirmées"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} réservations annulées.')
    mark_as_cancelled.short_description = "Annuler les réservations"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} réservations marquées comme terminées.')
    mark_as_completed.short_description = "Marquer comme terminées"

class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['time', 'max_reservations', 'is_active', 'current_reservations', 'availability_status']
    list_filter = ['is_active']
    ordering = ['time']
    list_editable = ['max_reservations', 'is_active']
    
    def current_reservations(self, obj):
        today = timezone.now().date()
        count = Reservation.objects.filter(
            time=obj.time,
            date=today,
            status__in=['pending', 'confirmed']
        ).count()
        return f"{count}/{obj.max_reservations}"
    current_reservations.short_description = 'Réservations Aujourd\'hui'
    
    def availability_status(self, obj):
        try:
            today = timezone.now().date()
            reservations_count = Reservation.objects.filter(
                time=obj.time,
                date=today,
                status__in=['pending', 'confirmed']
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

# Register all models
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(SpecialDate, SpecialDateAdmin)

# Customize admin site
admin.site.site_header = "🦐 Resto Pêcheur - Administration"
admin.site.site_title = "Resto Pêcheur Admin"
admin.site.index_title = "Tableau de Bord Unifié"