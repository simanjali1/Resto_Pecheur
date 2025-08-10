from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from .models import Reservation, Notification
from .utils.email_utils import (
    send_reservation_confirmation_email, 
    send_reservation_cancellation_email, 
    send_reservation_pending_email
)
import logging

logger = logging.getLogger(__name__)

# Global variable to store old status before save
_reservation_old_status = {}

@receiver(pre_save, sender=Reservation)
def capture_old_status(sender, instance, **kwargs):
    """Capture old status BEFORE save to detect changes"""
    if instance.pk:  # Only for existing reservations
        try:
            old_instance = Reservation.objects.get(pk=instance.pk)
            _reservation_old_status[instance.pk] = old_instance.status
            print(f"🔍 PRE_SAVE: Captured old status for {instance.customer_name}: {old_instance.status}")
        except Reservation.DoesNotExist:
            _reservation_old_status[instance.pk] = None

def mark_related_notifications_as_read(reservation):
    """Mark all notifications related to a reservation as read when status changes"""
    try:
        # Find all unread notifications for this reservation
        unread_notifications = Notification.objects.filter(
            related_reservation=reservation,
            is_read=False
        )
        
        count = unread_notifications.count()
        if count > 0:
            from django.utils import timezone
            unread_notifications.update(
                is_read=True,
                read_at=timezone.now()
            )
            print(f"✅ Marked {count} related notification(s) as read for {reservation.customer_name}")
        
    except Exception as e:
        logger.error(f"Error marking related notifications as read: {e}")

@receiver(post_save, sender=Reservation)
def create_simple_admin_message(sender, instance, created, **kwargs):
    """Create simple, clear messages for admin - ENHANCED WITH AUTO-READ"""
    
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            logger.warning("No admin user found for messages")
            return
        
        if created:
            # ✅ NEW RESERVATION
            print(f"🔍 POST_SAVE: New reservation created: {instance.customer_name}")
            handle_new_reservation_message(instance, admin_user)
        else:
            # ✅ RESERVATION UPDATE - Check for status change
            old_status = _reservation_old_status.get(instance.pk)
            current_status = instance.status
            
            print(f"🔍 POST_SAVE: Checking status change for {instance.customer_name}")
            print(f"🔍 OLD STATUS: {old_status}")
            print(f"🔍 NEW STATUS: {current_status}")
            
            if old_status and old_status != current_status:
                print(f"✅ STATUS CHANGED: {old_status} → {current_status}")
                
                # Mark all related notifications as read FIRST (user handled this reservation)
                mark_related_notifications_as_read(instance)
                
                # Then create new notification about the status change
                handle_status_change_message(instance, old_status, current_status, admin_user)
            else:
                print(f"ℹ️ No status change detected")
            
            # Clean up the stored old status
            if instance.pk in _reservation_old_status:
                del _reservation_old_status[instance.pk]
            
    except Exception as e:
        logger.error(f"Error creating admin message: {e}")
        print(f"❌ Erreur création message: {e}")
        import traceback
        traceback.print_exc()

def handle_new_reservation_message(reservation, admin_user):
    """Create message for new reservation - ALWAYS CREATE UNREAD"""
    try:
        print(f"📧 Processing new reservation for: {reservation.customer_name}")
        
        # Try to send email to customer
        email_status = "non fourni"
        email_sent = False
        priority = 'normal'
        
        if reservation.customer_email:
            try:
                print(f"📧 Sending pending email to: {reservation.customer_email}")
                email_sent = send_reservation_pending_email(reservation)
                email_status = "envoyé ✅" if email_sent else "ÉCHOUÉ ❌"
                print(f"📧 Email result: {email_sent}")
                
                if not email_sent:
                    priority = 'urgent'  # Set urgent if email failed
            except Exception as e:
                email_status = f"ERREUR ❌"
                priority = 'urgent'  # Set urgent on email error
                logger.error(f"Email error for {reservation.customer_name}: {e}")
                print(f"❌ Email error: {e}")
        
        # Create message based on email success/failure
        if email_sent:
            # ✅ SUCCESS - Normal priority, keep unread for review
            message = f"""📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
📧 Email envoyé à {reservation.customer_email}
📞 Tél: {reservation.customer_phone}

ℹ️ En attente de validation dans Réservations"""
            
            title = f"📨 Nouvelle réservation - {reservation.customer_name}"
            message_type = 'new_reservation'
            
        else:
            # ❌ EMAIL FAILED - Urgent priority, keep unread for immediate action
            message = f"""📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
📧 {reservation.customer_email or 'Aucun email'}
📞 {reservation.customer_phone} ← APPELER LE CLIENT

🚨 EMAIL N'A PAS ÉTÉ ENVOYÉ - Action immédiate requise"""
            
            title = f"🚨 EMAIL ÉCHOUÉ - {reservation.customer_name}"
            message_type = 'email_failed'
        
        # Create notification - ALWAYS UNREAD
        notification = Notification.objects.create(
            user=admin_user,
            title=title,
            message=message.strip(),
            message_type=message_type,
            priority=priority,
            related_reservation=reservation,
            is_read=False,  # Always create as unread
            read_at=None
        )
        
        print(f"✅ New reservation notification created (unread): {notification.title}")
        
    except Exception as e:
        logger.error(f"Error creating new reservation message: {e}")
        print(f"❌ Erreur message nouvelle réservation: {e}")

def handle_status_change_message(reservation, old_status, new_status, admin_user):
    """Create message for status changes - ALWAYS CREATE UNREAD"""
    try:
        email_sent = False
        priority = 'info'
        message_type = 'info'
        
        print(f"📧 Processing status change: {old_status} → {new_status}")
        print(f"📧 Customer email: {reservation.customer_email}")
        
        if new_status in ['Confirmée', 'confirmed']:
            # CONFIRMED
            print(f"✅ Processing CONFIRMATION for {reservation.customer_name}")
            
            if reservation.customer_email:
                try:
                    print(f"📧 Sending confirmation email to: {reservation.customer_email}")
                    email_sent = send_reservation_confirmation_email(reservation)
                    print(f"📧 Confirmation email result: {email_sent}")
                except Exception as e:
                    logger.error(f"Confirmation email error: {e}")
                    print(f"❌ Confirmation email error: {e}")
            else:
                print(f"⚠️ No email address for confirmation")
            
            if email_sent:
                message = f"""✅ Réservation CONFIRMÉE
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
📧 Email de confirmation envoyé à {reservation.customer_email}

Action effectuée avec succès"""
                
                title = f"✅ Confirmée - {reservation.customer_name}"
                priority = 'info'
                message_type = 'email_success'
                
            else:
                # Confirmation but email failed
                message = f"""✅ Réservation CONFIRMÉE (email échoué)
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
📞 {reservation.customer_phone} ← Peut nécessiter un appel

⚠️ Email de confirmation non envoyé"""
                
                title = f"⚠️ Confirmée (email échoué) - {reservation.customer_name}"
                priority = 'urgent'
                message_type = 'email_failed'
        
        elif new_status in ['Annulée', 'cancelled']:
            # CANCELLED
            print(f"❌ Processing CANCELLATION for {reservation.customer_name}")
            
            if reservation.customer_email:
                try:
                    print(f"📧 Sending cancellation email to: {reservation.customer_email}")
                    email_sent = send_reservation_cancellation_email(reservation)
                    print(f"📧 Cancellation email result: {email_sent}")
                except Exception as e:
                    logger.error(f"Cancellation email error: {e}")
                    print(f"❌ Cancellation email error: {e}")
            
            message = f"""❌ Réservation ANNULÉE
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
📧 Email d'annulation {'envoyé' if email_sent else 'NON ENVOYÉ'}

Annulation traitée"""
            
            title = f"❌ Annulée - {reservation.customer_name}"
            priority = 'normal' if email_sent else 'urgent'
            message_type = 'email_success' if email_sent else 'email_failed'
        
        elif new_status in ['Terminée', 'completed']:
            # COMPLETED
            message = f"""✅ Réservation TERMINÉE
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}

Service terminé avec succès"""
            
            title = f"✅ Terminée - {reservation.customer_name}"
            priority = 'info'
            message_type = 'info'
        
        else:
            # Other status changes
            print(f"ℹ️ Status change noted: {old_status} → {new_status}")
            message = f"""📝 Statut modifié: {old_status} → {new_status}
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}

Changement de statut enregistré"""
            
            title = f"📝 Status modifié - {reservation.customer_name}"
            priority = 'info'
            message_type = 'info'
        
        # Create the notification - ALWAYS UNREAD (will be marked read when viewed)
        notification = Notification.objects.create(
            user=admin_user,
            title=title,
            message=message.strip(),
            message_type=message_type,
            priority=priority,
            related_reservation=reservation,
            is_read=False,  # Always create as unread
            read_at=None
        )
        
        print(f"✅ Status change notification created (unread): {notification.title}")
        
    except Exception as e:
        logger.error(f"Error handling status change: {e}")
        print(f"❌ Erreur changement de statut: {e}")
        import traceback
        traceback.print_exc()

@receiver(post_delete, sender=Reservation)
def reservation_deleted_message(sender, instance, **kwargs):
    """Create message when reservation is deleted"""
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            return
        
        # Send cancellation email if possible
        email_sent = False
        if instance.customer_email:
            try:
                email_sent = send_reservation_cancellation_email(instance)
            except Exception as e:
                logger.error(f"Deletion email error: {e}")
        
        message = f"""🗑️ Réservation SUPPRIMÉE
📅 {instance.date.strftime('%d/%m/%Y')} à {instance.time.strftime('%H:%M')}
👥 {instance.number_of_guests} personne{'s' if instance.number_of_guests > 1 else ''}
📧 Email d'annulation {'envoyé' if email_sent else 'NON ENVOYÉ'}

Réservation définitivement supprimée du système"""
        
        Notification.objects.create(
            user=admin_user,
            title=f"🗑️ Supprimée - {instance.customer_name}",
            message=message.strip(),
            message_type='info',
            priority='normal',
            is_read=False,  # Create as unread
            read_at=None
        )
        
        print(f"✅ Message créé pour suppression: {instance.customer_name}")
        
    except Exception as e:
        logger.error(f"Error creating deletion message: {e}")
        print(f"❌ Erreur message suppression: {e}")

# Helper function to create custom messages
def create_custom_admin_message(title, message, priority='normal', message_type='info', reservation=None):
    """Create custom admin message"""
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            return None
        
        return Notification.objects.create(
            user=admin_user,
            title=title,
            message=message,
            message_type=message_type,
            priority=priority,
            related_reservation=reservation,
            is_read=False,  # Always create as unread
            read_at=None
        )
    except Exception as e:
        logger.error(f"Error creating custom message: {e}")
        return None

# Test function
def test_email_confirmation(reservation_id):
    """Test function to manually send confirmation email"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        print(f"🔍 Testing confirmation email for: {reservation.customer_name}")
        print(f"🔍 Email: {reservation.customer_email}")
        print(f"🔍 Status: {reservation.status}")
        
        result = send_reservation_confirmation_email(reservation)
        print(f"📧 Email result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Test email error: {e}")
        return False

# Cleanup function
def cleanup_old_notifications(days=30):
    """Clean up old read notifications"""
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        old_notifications = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_date
        )
        
        count = old_notifications.count()
        old_notifications.delete()
        
        logger.info(f"Cleaned up {count} old notifications")
        print(f"✅ {count} anciennes notifications supprimées")
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {e}")
        print(f"❌ Erreur nettoyage notifications: {e}")
        return 0