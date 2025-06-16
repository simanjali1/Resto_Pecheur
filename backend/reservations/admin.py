from django.contrib import admin
from .models import Reservation, TimeSlot, SpecialDate

# Restaurant model is intentionally not registered to hide it from admin

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'date', 'time', 'number_of_guests', 
        'status', 'customer_phone', 'created_at'
    ]
    list_filter = ['status', 'date', 'number_of_guests', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email']
    list_editable = ['status']  # Permet de changer le statut directement depuis la liste
    date_hierarchy = 'date'  # Navigation par date
    
    fieldsets = (
        ('Informations client', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Détails réservation', {
            'fields': ('date', 'time', 'number_of_guests', 'status')
        }),
        ('Notes', {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        })
    )
    
    # Actions personnalisées
    actions = ['mark_as_confirmed', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} réservation(s) confirmée(s).')
    mark_as_confirmed.short_description = "Marquer comme confirmées"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} réservation(s) annulée(s).')
    mark_as_cancelled.short_description = "Marquer comme annulées"

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['time', 'max_reservations', 'is_active']
    list_filter = ['is_active']
    list_editable = ['max_reservations', 'is_active']
    ordering = ['time']

@admin.register(SpecialDate)
class SpecialDateAdmin(admin.ModelAdmin):
    list_display = ['date', 'is_closed', 'reason', 'special_opening_time', 'special_closing_time']
    list_filter = ['is_closed', 'date']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Date et statut', {
            'fields': ('date', 'is_closed', 'reason')
        }),
        ('Horaires modifiés', {
            'fields': ('special_opening_time', 'special_closing_time'),
            'description': 'Laissez vide si les horaires normaux s\'appliquent'
        })
    )

# Configuration générale de l'admin
admin.site.site_header = "Administration Resto Pêcheur"
admin.site.site_title = "Resto Pêcheur"
admin.site.index_title = "Gestion des réservations"