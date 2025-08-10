# reservations/admin.py - COMPLETE VERSION WITH CASABLANCA TIMEZONE - FIXED FOR is_open FIELD
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
    """Get dashboard metrics directly - CASABLANCA TIMEZONE VERSION"""
    # Get current time in Casablanca timezone
    casablanca_now = timezone.localtime(timezone.now())
    today = casablanca_now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    print(f"🔍 CASABLANCA DEBUG - Current time: {casablanca_now}")
    print(f"🔍 CASABLANCA DEBUG - Today date: {today}")
    
    # Get restaurant instance (single instance)
    restaurant = get_restaurant_info()
    
    # Calculate metrics - UPDATED WITH FRENCH STATUS AND CASABLANCA TIME
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
        'daily_time_slots': get_correct_daily_time_slots_data(today)
    }
    
    return metrics, chart_data

def get_correct_daily_time_slots_data(date):
    """Get reservation data by ACTUAL reservation times - CASABLANCA TIMEZONE VERSION"""
    from collections import defaultdict
    
    # Get current Casablanca time for debug
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 ADMIN CHART DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 ADMIN CHART DEBUG - Getting data for date: {date}")
    
    # Get all reservations for the specified date
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
    """Calculate available tables for given date - CASABLANCA TIMEZONE VERSION"""
    restaurant = get_restaurant_info()
    
    # Debug timezone info
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 TABLES DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 TABLES DEBUG - Checking availability for date: {date}")
    
    reservations_count = Reservation.objects.filter(
        date=date,
        status__in=['Confirmée', 'En attente']
    ).count()
    
    available = max(0, restaurant.number_of_tables - reservations_count)
    print(f"🔍 TABLES DEBUG - Total tables: {restaurant.number_of_tables}, Reserved: {reservations_count}, Available: {available}")
    
    return available

def get_peak_hour_today(date):
    """Find the busiest hour for today - CASABLANCA TIMEZONE VERSION"""
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 PEAK HOUR DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 PEAK HOUR DEBUG - Checking peak hour for date: {date}")
    
    peak_hour = Reservation.objects.filter(
        date=date,
        status__in=['En attente', 'Confirmée']
    ).values('time').annotate(
        total_guests=Sum('number_of_guests')
    ).order_by('-total_guests').first()
    
    if peak_hour and peak_hour['total_guests'] > 0:
        result = peak_hour['time'].strftime('%H:%M')
        print(f"🔍 PEAK HOUR DEBUG - Peak hour found: {result} with {peak_hour['total_guests']} guests")
        return result
    
    print(f"🔍 PEAK HOUR DEBUG - No peak hour found")
    return None

def get_next_available_slot():
    """Find next available time slot - CASABLANCA TIMEZONE VERSION"""
    try:
        # Use Casablanca timezone
        casablanca_now = timezone.localtime(timezone.now())
        current_date = casablanca_now.date()
        current_time = casablanca_now.time()
        
        print(f"🔍 NEXT SLOT DEBUG - Casablanca time: {casablanca_now}")
        print(f"🔍 NEXT SLOT DEBUG - Current date: {current_date}, Current time: {current_time}")
        
        # Look for available slots in the next 7 days
        for days_ahead in range(7):
            check_date = current_date + timedelta(days=days_ahead)
            time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
            
            for slot in time_slots:
                # If it's today, skip past time slots (with 30min buffer)
                if days_ahead == 0:
                    time_with_buffer = (datetime.combine(current_date, current_time) + timedelta(minutes=30)).time()
                    if slot.time <= time_with_buffer:
                        print(f"🔍 NEXT SLOT DEBUG - Skipping past slot: {slot.time}")
                        continue
                
                # Count current reservations for this slot
                reservations_count = Reservation.objects.filter(
                    date=check_date,
                    time=slot.time,
                    status__in=['Confirmée', 'En attente']
                ).count()
                
                print(f"🔍 NEXT SLOT DEBUG - Slot {slot.time} on {check_date}: {reservations_count}/{slot.max_reservations}")
                
                # Check if slot is available
                if reservations_count < slot.max_reservations:
                    if days_ahead == 0:
                        result = f"Aujourd'hui {slot.time.strftime('%H:%M')}"
                    elif days_ahead == 1:
                        result = f"Demain {slot.time.strftime('%H:%M')}"
                    else:
                        result = f"{check_date.strftime('%d/%m')} à {slot.time.strftime('%H:%M')}"
                    
                    print(f"🔍 NEXT SLOT DEBUG - Available slot found: {result}")
                    return result
        
        print(f"🔍 NEXT SLOT DEBUG - No available slots found")
        return "Aucun créneau disponible cette semaine"
        
    except Exception as e:
        print(f"🔍 NEXT SLOT DEBUG - Error: {e}")
        return "Vérification en cours..."

def get_weekly_stats(week_start):
    """Get reservation data for the current week - CASABLANCA TIMEZONE VERSION"""
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 WEEKLY STATS DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 WEEKLY STATS DEBUG - Week start: {week_start}")
    
    data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        count = Reservation.objects.filter(date=day).count()
        data.append(count)
        print(f"🔍 WEEKLY STATS DEBUG - Day {day}: {count} reservations")
    
    print(f"🔍 WEEKLY STATS DEBUG - Final weekly data: {data}")
    return data

def custom_admin_index(request, extra_context=None):
    """Custom admin index that shows unified dashboard with sidebar and CASABLANCA TIMEZONE"""
    try:
        # Get current Casablanca time
        casablanca_now = timezone.localtime(timezone.now())
        today = casablanca_now.date()
        
        print(f"🔍 DASHBOARD DEBUG - Casablanca time: {casablanca_now}")
        print(f"🔍 DASHBOARD DEBUG - Today date: {today}")
        
        # Get dashboard metrics
        metrics, chart_data = get_dashboard_metrics()
        
        # Recent reservations (last 24 hours) - use Casablanca timezone
        last_24h = casablanca_now - timedelta(hours=24)
        recent_reservations = Reservation.objects.filter(
            created_at__gte=last_24h
        ).order_by('-created_at')[:10]
        
        print(f"🔍 DASHBOARD DEBUG - Looking for reservations since: {last_24h}")
        print(f"🔍 DASHBOARD DEBUG - Found {recent_reservations.count()} recent reservations")
        
        # Recent notifications
        recent_notifications = Notification.objects.filter(
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Today's schedule
        todays_schedule = Reservation.objects.filter(
            date=today
        ).order_by('time')
        
        print(f"🔍 DASHBOARD DEBUG - Today's schedule has {todays_schedule.count()} reservations")
        
        # Get admin context
        app_list = admin.site.get_app_list(request)
        
        context = {
            'title': 'Administration - Resto Pêcheur',
            'app_list': app_list,
            'available_apps': app_list,
            'metrics': metrics,
            'chart_data': chart_data,
            'recent_reservations': recent_reservations,
            'recent_notifications': recent_notifications,
            'todays_schedule': todays_schedule,
            # Flatten the metrics for direct access
            'today_reservations': metrics['today_reservations'],
            'today_guests': metrics['today_guests'],
            'available_tables': metrics['available_tables'],
            'total_tables': metrics['total_tables'],
            'occupancy_rate': metrics['occupancy_rate'],
            'restaurant_name': metrics['restaurant_name'],
            'restaurant_capacity': metrics['restaurant_capacity'],
            'unread_notifications': metrics['unread_notifications'],
            # Add timezone info for frontend
            'casablanca_time': casablanca_now.isoformat(),
            'casablanca_date': today.isoformat(),
        }
        context.update(extra_context or {})
        
        return TemplateResponse(request, 'admin/unified_dashboard_with_sidebar.html', context)
    
    except Exception as e:
        print(f"🔍 DASHBOARD DEBUG - Error: {e}")
        # Fallback to default admin if there's an error
        from django.contrib.admin.sites import AdminSite
        return AdminSite().index(request, extra_context)
    
# Override the admin site index
admin.site.index = custom_admin_index

class NotificationAdmin(admin.ModelAdmin):
    """Simple, clean admin interface for notifications like a message center - CASABLANCA TIMEZONE"""
    
    list_display = [
        'priority_icon',
        'read_status', 
        'title_with_customer',
        'message_preview',
        'customer_contact',
        'time_display',
        'quick_actions'
    ]
    
    list_filter = [
        'priority',
        'message_type', 
        'is_read',
        'created_at',
    ]
    
    search_fields = [
        'title',
        'message',
        'related_reservation__customer_name',
        'related_reservation__customer_email',
        'related_reservation__customer_phone'
    ]
    
    readonly_fields = [
        'user',
        'created_at',
        'read_at',
        'reservation_details'
    ]
    
    ordering = ['-created_at']
    list_per_page = 20
    
    # Simplified fields for form
    fields = [
        'title',
        'message',
        'message_type',
        'priority',
        'related_reservation',
        'is_read',
        'user',
        'created_at',
        'read_at',
        'reservation_details'
    ]
    
    # Custom display methods
    def priority_icon(self, obj):
        """Show priority with colored icon"""
        if obj.priority == 'urgent':
            return format_html('<span style="font-size: 16px; color: #dc3545;">🚨</span>')
        elif obj.priority == 'normal':
            return format_html('<span style="font-size: 16px; color: #ffc107;">📨</span>')
        else:
            return format_html('<span style="font-size: 16px; color: #28a745;">ℹ️</span>')
    priority_icon.short_description = "Priorité"
    
    def read_status(self, obj):
        """Show read status"""
        if obj.is_read:
            return format_html('<span style="color: #6c757d;">✓ Lu</span>')
        else:
            return format_html('<span style="color: #333354d0; font-weight: bold;">● Non lu</span>')
    read_status.short_description = "Statut"
    
    def title_with_customer(self, obj):
        """Show title with customer name highlighted"""
        if obj.related_reservation:
            customer = obj.related_reservation.customer_name
            return format_html('<strong>{}</strong><br><small style="color: #6c757d;">{}</small>',
                             obj.title, customer)
        return format_html('<strong>{}</strong>', obj.title)
    title_with_customer.short_description = "Message"
    
    def message_preview(self, obj):
        """Show message preview"""
        preview = obj.message[:150] + "..." if len(obj.message) > 150 else obj.message
        return format_html('<div style="max-width: 350px; white-space: pre-line; font-size: 12px; line-height: 1.4;">{}</div>', 
                          preview)
    message_preview.short_description = "Contenu"
    
    def customer_contact(self, obj):
        """Show customer contact info"""
        if obj.related_reservation:
            res = obj.related_reservation
            contact_parts = []
            
            if res.customer_phone:
                phone_display = res.customer_phone[:12] + "..." if len(res.customer_phone) > 12 else res.customer_phone
                contact_parts.append(f'<a href="tel:{res.customer_phone}" style="color: #333354d0; text-decoration: none;">📞 {phone_display}</a>')
            
            if res.customer_email:
                email_display = res.customer_email[:20] + "..." if len(res.customer_email) > 20 else res.customer_email
                contact_parts.append(f'<a href="mailto:{res.customer_email}" style="color: #333354d0; text-decoration: none;">📧 {email_display}</a>')
            
            if contact_parts:
                return format_html('<br>'.join(contact_parts))
            else:
                return format_html('<span style="color: #dc3545;">❌ Pas de contact</span>')
        return "-"
    customer_contact.short_description = "Contact"
    
    def time_display(self, obj):
        """Show time in readable format - CASABLANCA TIMEZONE VERSION"""
        from django.utils import timezone
        
        # Convert to Casablanca timezone
        created_local = timezone.localtime(obj.created_at)
        casablanca_now = timezone.localtime(timezone.now())
        
        print(f"🔍 NOTIFICATION TIME DEBUG - Created local: {created_local}")
        print(f"🔍 NOTIFICATION TIME DEBUG - Current local: {casablanca_now}")
        
        return format_html('<small style="color: #6c757d;">{}<br>{}</small>',
                        created_local.strftime('%d/%m %H:%M'),
                        obj.time_ago)
    time_display.short_description = "Quand"
    
    def quick_actions(self, obj):
        """Show quick action buttons"""
        if obj.related_reservation:
            from django.urls import reverse
            try:
                res_url = reverse('admin:reservations_reservation_change', args=[obj.related_reservation.pk])
                return format_html(
                    '<a href="{}" class="button" style="background: #333354d0; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">📋 Voir</a>',
                    res_url
                )
            except:
                return "-"
        return "-"
    quick_actions.short_description = "Actions"
    
    def reservation_details(self, obj):
        """Show full reservation details in form"""
        if obj.related_reservation:
            from django.urls import reverse
            res = obj.related_reservation
            try:
                res_url = reverse('admin:reservations_reservation_change', args=[res.pk])
                return format_html("""
                    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e8e8f0 100%); padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #333354d0;">
                        <h3 style="color: #333354; margin-top: 0;">📋 Détails de la réservation</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                            <div>
                                <p style="margin: 8px 0;"><strong>👤 Client:</strong> {}</p>
                                <p style="margin: 8px 0;"><strong>📅 Date:</strong> {}</p>
                                <p style="margin: 8px 0;"><strong>⏰ Heure:</strong> {}</p>
                                <p style="margin: 8px 0;"><strong>👥 Personnes:</strong> {}</p>
                            </div>
                            <div>
                                <p style="margin: 8px 0;"><strong>📞 Téléphone:</strong> <a href="tel:{}" style="color: #333354d0;">{}</a></p>
                                <p style="margin: 8px 0;"><strong>📧 Email:</strong> <a href="mailto:{}" style="color: #333354d0;">{}</a></p>
                                <p style="margin: 8px 0;"><strong>📊 Statut:</strong> <span style="background: #333354d0; color: white; padding: 3px 10px; border-radius: 15px; font-size: 12px;">{}</span></p>
                                {}
                            </div>
                        </div>
                        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                        <div style="text-align: center;">
                            <a href="{}" class="button" style="background: linear-gradient(45deg, #333354d0, #333354); color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">
                                🔗 Gérer cette réservation
                            </a>
                        </div>
                    </div>
                """,
                    res.customer_name,
                    res.date.strftime('%d/%m/%Y'),
                    res.time.strftime('%H:%M'),
                    res.number_of_guests,
                    res.customer_phone or 'Non fourni',
                    res.customer_phone or 'Non fourni',
                    res.customer_email or 'Non fourni',
                    res.customer_email or 'Non fourni',
                    res.get_status_display(),
                    f'<p style="margin: 8px 0;"><strong>🪑 Table:</strong> {res.table_number}</p>' if res.table_number else '',
                    res_url
                )
            except Exception as e:
                return format_html('<div style="color: #dc3545;">Erreur: {}</div>', str(e))
        return format_html('<div style="text-align: center; color: #6c757d; padding: 20px;">Aucune réservation liée</div>')
    reservation_details.short_description = "Réservation Liée"
    
    # Custom actions
    actions = ['mark_as_read', 'mark_as_unread', 'delete_read_messages']
    
    def mark_as_read(self, request, queryset):
        """Mark selected messages as read - CASABLANCA TIMEZONE VERSION"""
        casablanca_now = timezone.localtime(timezone.now())
        count = queryset.filter(is_read=False).update(is_read=True, read_at=casablanca_now)
        self.message_user(request, f"✅ {count} message(s) marqué(s) comme lu(s).")
    mark_as_read.short_description = "✓ Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        """Mark selected messages as unread"""
        count = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f"📩 {count} message(s) marqué(s) comme non lu(s).")
    mark_as_unread.short_description = "● Marquer comme non lu"
    
    def delete_read_messages(self, request, queryset):
        """Delete only read messages"""
        read_messages = queryset.filter(is_read=True)
        count = read_messages.count()
        read_messages.delete()
        self.message_user(request, f"🗑️ {count} message(s) lu(s) supprimé(s).")
    delete_read_messages.short_description = "🗑️ Supprimer les messages lus"
    
    # Auto-mark as read when viewing details
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Auto-mark message as read when viewing details"""
        obj = self.get_object(request, object_id)
        if obj and not obj.is_read:
            obj.mark_as_read()
            self.message_user(request, f"✅ Notification marquée comme lue: {obj.title}")
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    # Mark as read when user clicks on notification in list
    def response_change(self, request, obj):
        """Mark as read when user clicks on notification in list"""
        if obj and not obj.is_read:
            obj.mark_as_read()
            self.message_user(request, f"✅ Notification marquée comme lue")
        
        return super().response_change(request, obj)
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user', 'related_reservation').order_by('-created_at')

class RestaurantInfoAdmin(admin.ModelAdmin):
    """Admin for single restaurant configuration - CASABLANCA TIMEZONE VERSION"""
    
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
    """Admin for reservations - CASABLANCA TIMEZONE VERSION"""
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
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
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
        updated = queryset.update(status='Confirmée')
        self.message_user(request, f'{updated} réservations marquées comme confirmées.')
    mark_as_confirmed.short_description = "Marquer comme confirmées"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='Annulée')
        self.message_user(request, f'{updated} réservations annulées.')
    mark_as_cancelled.short_description = "Annuler les réservations"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='Terminée')
        self.message_user(request, f'{updated} réservations marquées comme terminées.')
    mark_as_completed.short_description = "Marquer comme terminées"

class TimeSlotAdmin(admin.ModelAdmin):
    """Admin for time slots - CASABLANCA TIMEZONE VERSION"""
    list_display = ['time', 'max_reservations', 'is_active', 'current_reservations', 'availability_status']
    list_filter = ['is_active']
    ordering = ['time']
    list_editable = ['max_reservations', 'is_active']
    
    def current_reservations(self, obj):
        # Use Casablanca timezone
        casablanca_now = timezone.localtime(timezone.now())
        today = casablanca_now.date()
        
        print(f"🔍 TIMESLOT DEBUG - Casablanca time: {casablanca_now}")
        print(f"🔍 TIMESLOT DEBUG - Today: {today}")
        
        # Support both French and English statuses
        count = Reservation.objects.filter(
            time=obj.time,
            date=today,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']
        ).count()
        
        print(f"🔍 TIMESLOT DEBUG - Slot {obj.time}: {count}/{obj.max_reservations}")
        return f"{count}/{obj.max_reservations}"
    current_reservations.short_description = 'Réservations Aujourd\'hui'
    
    def availability_status(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
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
        except Exception as e:
            print(f"🔍 TIMESLOT ERROR - {e}")
            return format_html('<span style="color: #999;">N/A</span>')
    availability_status.short_description = 'Disponibilité'

# ✅ FIXED: SpecialDateAdmin with corrected field names for is_open
class SpecialDateAdmin(admin.ModelAdmin):
    """Admin for special dates - CASABLANCA TIMEZONE VERSION - FIXED FOR is_open FIELD"""
    list_display = ['date', 'reason', 'is_open_colored', 'is_upcoming_date', 'days_until_date']
    list_filter = ['is_open', 'date']  # ✅ FIXED: Changed from 'is_closed' to 'is_open'
    date_hierarchy = 'date'
    ordering = ['-date']
    
    fieldsets = (
        ('Date et Raison', {
            'fields': ('date', 'reason', 'is_open')  # ✅ FIXED: Changed from 'is_closed' to 'is_open'
        }),
        ('Horaires Spéciaux', {
            'fields': ('special_opening_time', 'special_closing_time'),
            'classes': ('collapse',),
            'description': 'Laisser vide si fermé ou pour garder les horaires normaux'
        }),
    )
    
    def is_open_colored(self, obj):
        """Show open/closed status with colors - FIXED FOR is_open FIELD"""
        if obj.is_open:
            return format_html('<span style="color: #4caf50; font-weight: bold;">✅ Ouvert</span>')
        else:
            return format_html('<span style="color: #f44336; font-weight: bold;">❌ Fermé</span>')
    is_open_colored.short_description = 'Statut'
    
    def is_upcoming_date(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
            print(f"🔍 SPECIAL DATE DEBUG - Casablanca time: {casablanca_now}")
            print(f"🔍 SPECIAL DATE DEBUG - Today: {today}, Special date: {obj.date}")
            
            if obj.date == today:
                return format_html('<span style="color: #f44336; font-weight: bold;">Aujourd\'hui</span>')
            elif obj.date > today:
                return format_html('<span style="color: #ff9800; font-weight: bold;">À venir</span>')
            else:
                return format_html('<span style="color: #666;">Passée</span>')
        except Exception as e:
            print(f"🔍 SPECIAL DATE ERROR - {e}")
            return format_html('<span style="color: #999;">N/A</span>')
    is_upcoming_date.short_description = 'Statut'
    
    def days_until_date(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
            if obj.date == today:
                return "Aujourd'hui"
            elif obj.date > today:
                days = (obj.date - today).days
                return f"Dans {days} jour{'s' if days > 1 else ''}"
            else:
                return "-"
        except Exception as e:
            print(f"🔍 SPECIAL DATE DAYS ERROR - {e}")
            return "-"
    days_until_date.short_description = 'Échéance'
    
    def get_queryset(self, request):
        """Filter to show only recent and upcoming dates - CASABLANCA TIMEZONE VERSION"""
        qs = super().get_queryset(request)
        # Use Casablanca timezone
        casablanca_now = timezone.localtime(timezone.now())
        thirty_days_ago = casablanca_now.date() - timedelta(days=30)
        
        print(f"🔍 SPECIAL DATE QUERYSET DEBUG - Filtering from: {thirty_days_ago}")
        return qs.filter(date__gte=thirty_days_ago)

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