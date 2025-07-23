from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Reservation, Notification
from .utils.email_utils import (
    send_reservation_confirmation_email, 
    send_reservation_cancellation_email, 
    send_reservation_pending_email
)

@receiver(post_save, sender=Reservation)
def reservation_notification_and_email(sender, instance, created, **kwargs):
    """
    Handle reservation creation and updates with notifications + emails
    """
    if created:
        # New reservation created
        try:
            # 1. Send pending email to customer
            if instance.customer_email:
                send_reservation_pending_email(instance)
            
            # 2. Create notification for restaurant staff
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                Notification.objects.create(
                    user=admin_user,
                    title="🍽️ Nouvelle Réservation!",
                    message=f"Nouvelle réservation de {instance.customer_name} pour {instance.number_of_guests} personnes le {instance.date.strftime('%d/%m/%Y')} à {instance.time.strftime('%H:%M')}. Email: {instance.customer_email or 'Non fourni'}",
                    notification_type="new_reservation",
                    related_reservation=instance
                )
                print(f"✅ Notification admin créée pour nouvelle réservation: {instance.customer_name}")
                
        except Exception as e:
            print(f"❌ Erreur dans le gestionnaire de nouvelle réservation: {e}")
    
    else:
        # Reservation updated - check if status changed
        try:
            # Send appropriate email based on status
            if instance.status in ['Confirmée', 'confirmed']:
                if instance.customer_email:
                    send_reservation_confirmation_email(instance)
                notification_title = "✅ Réservation Confirmée"
                notification_message = f"Réservation de {instance.customer_name} CONFIRMÉE pour le {instance.date.strftime('%d/%m/%Y')} à {instance.time.strftime('%H:%M')}. Email de confirmation envoyé."
                
            elif instance.status in ['Annulée', 'cancelled']:
                if instance.customer_email:
                    send_reservation_cancellation_email(instance)
                notification_title = "❌ Réservation Annulée"
                notification_message = f"Réservation de {instance.customer_name} ANNULÉE. Email d'annulation envoyé."
                
            elif instance.status in ['Terminée', 'completed']:
                notification_title = "✅ Réservation Terminée"
                notification_message = f"Réservation de {instance.customer_name} marquée comme terminée."
                
            else:  # En attente or other status
                notification_title = "📝 Réservation Mise à Jour"
                notification_message = f"Réservation de {instance.customer_name} mise à jour: {instance.get_status_display()}"
            
            # Create staff notification
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                Notification.objects.create(
                    user=admin_user,
                    title=notification_title,
                    message=notification_message,
                    notification_type="reservation_update",
                    related_reservation=instance
                )
                print(f"✅ Notification admin créée pour mise à jour réservation: {instance.customer_name}")
                
        except Exception as e:
            print(f"❌ Erreur dans la mise à jour de réservation: {e}")

@receiver(post_delete, sender=Reservation)
def reservation_deleted_notification(sender, instance, **kwargs):
    """
    Handle reservation deletion
    """
    try:
        # Send cancellation email to customer
        if instance.customer_email:
            send_reservation_cancellation_email(instance)
        
        # Create admin notification
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            Notification.objects.create(
                user=admin_user,
                title="🗑️ Réservation Supprimée",
                message=f"Réservation de {instance.customer_name} ({instance.number_of_guests} personnes) supprimée pour le {instance.date.strftime('%d/%m/%Y')}. Email d'annulation envoyé.",
                notification_type="reservation_deleted"
            )
            print(f"✅ Notification admin créée pour réservation supprimée: {instance.customer_name}")
            
    except Exception as e:
        print(f"❌ Erreur dans la suppression de réservation: {e}")

# Additional signal for table assignment
@receiver(post_save, sender=Reservation)
def table_assignment_notification(sender, instance, created, **kwargs):
    """
    Notify when a table is assigned to a reservation
    """
    if not created and instance.table_number:
        try:
            # Check if table was just assigned
            if hasattr(instance, '_state') and instance._state.adding is False:
                old_instance = Reservation.objects.get(pk=instance.pk)
                if old_instance.table_number != instance.table_number:
                    admin_user = User.objects.filter(is_superuser=True).first()
                    if admin_user:
                        Notification.objects.create(
                            user=admin_user,
                            title="🪑 Table Assignée",
                            message=f"Table {instance.table_number} assignée à la réservation de {instance.customer_name} pour le {instance.date.strftime('%d/%m/%Y')}.",
                            notification_type="table_assigned",
                            related_reservation=instance
                        )
                        print(f"✅ Notification table assignée: {instance.customer_name} → Table {instance.table_number}")
        except Exception as e:
            print(f"❌ Erreur notification assignment table: {e}")