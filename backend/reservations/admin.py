# reservations/admin.py - KEEP SIDEBAR, REPLACE ONLY MAIN CONTENT
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from datetime import timedelta
from .models import Restaurant, Reservation, TimeSlot, SpecialDate

# First, unregister all models to avoid conflicts
try:
    admin.site.unregister(Restaurant)
    admin.site.unregister(Reservation)
    admin.site.unregister(TimeSlot)
    admin.site.unregister(SpecialDate)
except admin.sites.NotRegistered:
    pass

# Custom admin site class to override only the index content
class CustomAdminSite(admin.AdminSite):
    def index(self, request, extra_context=None):
        """
        Override admin index to show unified dashboard while keeping sidebar
        """
        from . import views
        # Get the dashboard context
        dashboard_context = views.dashboard_view(request).context_data if hasattr(views.dashboard_view(request), 'context_data') else {}
        
        # Use the unified dashboard template but with admin base
        context = {
            'title': 'Tableau de Bord Unifié',
            'app_list': self.get_app_list(request),
            'available_apps': self.get_app_list(request),
            **dashboard_context,
        }
        context.update(extra_context or {})
        
        return TemplateResponse(request, 'admin/unified_dashboard_with_sidebar.html', context)

# Don't override the entire admin site, just patch the index method
original_index = admin.site.index

def custom_admin_index(request, extra_context=None):
    """Custom admin index that shows unified dashboard with sidebar"""
    # Import here to avoid circular imports
    from . import views
    
    # Get dashboard data
    try:
        dashboard_response = views.dashboard_view(request)
        if hasattr(dashboard_response, 'context_data'):
            dashboard_context = dashboard_response.context_data
        else:
            dashboard_context = {}
    except:
        dashboard_context = {}
    
    # Get admin context
    app_list = admin.site.get_app_list(request)
    
    context = {
        'title': 'Tableau de Bord Unifié - Resto Pêcheur',
        'app_list': app_list,
        'available_apps': app_list,
        **dashboard_context,
    }
    context.update(extra_context or {})
    
    return TemplateResponse(request, 'admin/unified_dashboard_with_sidebar.html', context)

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
        rate = obj.get_occupancy_rate_today()
        color = '#4caf50' if rate < 70 else '#ff9800' if rate < 90 else '#f44336'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    get_occupancy_rate.short_description = 'Taux Occupation Aujourd\'hui'
    
    def has_add_permission(self, request):
        # Only allow one restaurant
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
        if obj.is_today:
            return format_html('<span style="color: #4caf50; font-weight: bold;">Aujourd\'hui</span>')
        elif obj.is_upcoming:
            return format_html('<span style="color: #ff9800; font-weight: bold;">Bientôt</span>')
        elif obj.is_past:
            return format_html('<span style="color: #666;">Passée</span>')
        return '-'
    is_today_reservation.short_description = 'Timing'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related().order_by('-date', '-time')
    
    # Custom actions
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
        today = timezone.now().date()
        available = obj.available_slots(today)
        total = obj.max_reservations
        
        if available == 0:
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
        if obj.is_today:
            return format_html('<span style="color: #f44336; font-weight: bold;">Aujourd\'hui</span>')
        elif obj.is_upcoming:
            return format_html('<span style="color: #ff9800; font-weight: bold;">À venir</span>')
        else:
            return format_html('<span style="color: #666;">Passée</span>')
    is_upcoming_date.short_description = 'Statut'
    
    def days_until_date(self, obj):
        if obj.is_today:
            return "Aujourd'hui"
        elif obj.is_upcoming:
            days = obj.days_until
            return f"Dans {days} jour{'s' if days > 1 else ''}"
        else:
            return "-"
    days_until_date.short_description = 'Échéance'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Show upcoming dates first, then recent past dates
        return qs.filter(date__gte=timezone.now().date() - timedelta(days=30))

# Register all models - ONLY ONCE
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(SpecialDate, SpecialDateAdmin)

# Customize admin site
admin.site.site_header = "🦐 Resto Pêcheur - Administration"
admin.site.site_title = "Resto Pêcheur Admin"
admin.site.index_title = "Tableau de Bord Unifié"