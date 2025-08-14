from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Reservation, Notification
from .utils.email_utils import (
    send_reservation_confirmation_email, 
    send_reservation_cancellation_email, 
    send_reservation_pending_email
)
import logging
import re

logger = logging.getLogger(__name__)

# Global variable to store old status before save
_reservation_old_status = {}

def validate_email_address_properly(email):
    """Properly validate email address format"""
    try:
        if not email or not email.strip():
            return False, "No email address provided"
        
        email = email.strip()
        
        # Use Django's built-in email validator
        validate_email(email)
        
        # Additional basic checks
        if len(email) > 254:  # RFC 5321 limit
            return False, "Email address too long"
        
        if email.count('@') != 1:
            return False, "Invalid email format - multiple @ symbols"
        
        local, domain = email.split('@')
        if len(local) > 64:  # RFC 5321 limit
            return False, "Email local part too long"
        
        return True, "Email format is valid"
        
    except ValidationError as e:
        return False, f"Invalid email format: {str(e)}"
    except Exception as e:
        return False, f"Email validation error: {str(e)}"

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
    """Create simple, clear messages for admin with email tracking - ENHANCED"""
    
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
    """Create message for new reservation with PROPER email validation and failure tracking"""
    try:
        print(f"📧 Processing new reservation for: {reservation.customer_name}")
        
        # ✅ CREATE NOTIFICATION FIRST to get tracking token
        notification = Notification.objects.create(
            user=admin_user,
            title=f"📨 Nouvelle réservation - {reservation.customer_name}",
            message="En cours de traitement...",  # Temporary message
            message_type='new_reservation',
            priority='normal',
            related_reservation=reservation,
            is_read=False,
            read_at=None,
            # ✅ CRITICAL: Start with email_sent=False
            email_sent=False,
            email_opened_by_client=False
        )
        
        # ✅ VALIDATE EMAIL ADDRESS FIRST
        email_sent = False
        priority = 'normal'
        error_reason = ""
        
        print(f"📧 Customer email: '{reservation.customer_email}'")
        
        if reservation.customer_email and reservation.customer_email.strip():
            # ✅ PROPER EMAIL VALIDATION
            is_valid, validation_message = validate_email_address_properly(reservation.customer_email)
            
            print(f"📧 Email validation result: {is_valid} - {validation_message}")
            
            if is_valid:
                try:
                    print(f"📧 Email validation passed, attempting to send to: {reservation.customer_email}")
                    
                    # ✅ TRY TO SEND EMAIL - This will now properly detect failures
                    email_sent = send_reservation_pending_email(reservation, notification)
                    
                    print(f"📧 Email function returned: {email_sent}")
                    
                    # ✅ DOUBLE-CHECK: Reload notification to see actual email_sent status
                    notification.refresh_from_db()
                    actual_email_sent = notification.email_sent
                    
                    print(f"📧 Notification email_sent field: {actual_email_sent}")
                    
                    if email_sent and actual_email_sent:
                        print(f"✅ Email sent successfully to {reservation.customer_email}")
                        priority = 'normal'
                    else:
                        print(f"❌ Email failed to send to {reservation.customer_email}")
                        # ✅ ENSURE notification reflects failure
                        notification.email_sent = False
                        notification.email_opened_by_client = False
                        notification.save(update_fields=['email_sent', 'email_opened_by_client'])
                        priority = 'urgent'
                        email_sent = False
                        error_reason = "Échec d'envoi"
                        
                except Exception as e:
                    print(f"❌ Email exception for {reservation.customer_email}: {e}")
                    # ✅ EMAIL EXCEPTION - mark as failed
                    email_sent = False
                    notification.email_sent = False
                    notification.email_opened_by_client = False
                    notification.save(update_fields=['email_sent', 'email_opened_by_client'])
                    priority = 'urgent'
                    error_reason = f"Erreur d'envoi: {str(e)}"
                    logger.error(f"Email error for {reservation.customer_name}: {e}")
            else:
                print(f"❌ Email validation failed: {validation_message}")
                priority = 'urgent'
                email_sent = False
                error_reason = f"Email invalide: {validation_message}"
                # Mark notification as failed
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
        else:
            print(f"❌ No email address provided")
            priority = 'urgent'
            email_sent = False
            error_reason = "Aucun email fourni"
        
        # ✅ FINAL CHECK: Use the actual database state
        notification.refresh_from_db()
        final_email_status = notification.email_sent
        
        print(f"📧 Final email status check: {final_email_status}")
        
        # ✅ UPDATE MESSAGE BASED ON ACTUAL RESULT
        if final_email_status and email_sent:
            # SUCCESS - Email actually sent
            message = f"""📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
✅ Email avec tracking envoyé à {reservation.customer_email}
📞 Tél: {reservation.customer_phone}

⏳ En attente de validation dans Réservations
📊 Status: Email envoyé avec succès"""
            
            title = f"📨 Nouvelle réservation - {reservation.customer_name}"
            message_type = 'email_success'
            priority = 'normal'
            
        else:
            # ❌ EMAIL FAILED - Show specific reason
            email_display = reservation.customer_email if reservation.customer_email else "Non fourni"
            
            message = f"""📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
❌ EMAIL NON ENVOYÉ: {error_reason}
📧 Email: {email_display}
📞 {reservation.customer_phone} ← APPELER LE CLIENT IMMÉDIATEMENT

🚨 AUCUN EMAIL ENVOYÉ - Action immédiate requise
⚠️ Client n'a reçu aucune confirmation"""
            
            title = f"🚨 EMAIL ÉCHOUÉ - {reservation.customer_name}"
            message_type = 'email_failed'
            priority = 'urgent'
        
        # Update the notification with final content
        notification.title = title
        notification.message = message.strip()
        notification.priority = priority
        notification.message_type = message_type
        notification.save(update_fields=['title', 'message', 'priority', 'message_type'])
        
        print(f"✅ New reservation notification created: {notification.title}")
        print(f"📊 Final tracking status: email_sent={notification.email_sent}")
        
    except Exception as e:
        logger.error(f"Error creating new reservation message: {e}")
        print(f"❌ Erreur message nouvelle réservation: {e}")

def handle_status_change_message(reservation, old_status, new_status, admin_user):
    """Create message for status changes with PROPER email validation and failure tracking"""
    try:
        # ✅ CREATE NOTIFICATION FIRST to get tracking token
        notification = Notification.objects.create(
            user=admin_user,
            title=f"📝 Status change - {reservation.customer_name}",
            message="Processing status change...",  # Temporary message
            message_type='info',
            priority='info',
            related_reservation=reservation,
            is_read=False,
            read_at=None,
            # ✅ CRITICAL: Start with email_sent=False
            email_sent=False,
            email_opened_by_client=False
        )
        
        email_sent = False
        priority = 'info'
        message_type = 'info'
        
        print(f"📧 Processing status change: {old_status} → {new_status}")
        print(f"📧 Customer email: {reservation.customer_email}")
        
        if new_status in ['Confirmée', 'confirmed']:
            # CONFIRMED
            print(f"✅ Processing CONFIRMATION for {reservation.customer_name}")
            
            if reservation.customer_email and reservation.customer_email.strip():
                # ✅ VALIDATE EMAIL FIRST
                is_valid, validation_message = validate_email_address_properly(reservation.customer_email)
                
                if is_valid:
                    try:
                        print(f"📧 Attempting to send confirmation email to: {reservation.customer_email}")
                        # ✅ TRY TO SEND EMAIL
                        email_sent = send_reservation_confirmation_email(reservation, notification)
                        
                        # ✅ DOUBLE-CHECK actual status
                        notification.refresh_from_db()
                        actual_email_sent = notification.email_sent
                        
                        if not (email_sent and actual_email_sent):
                            print(f"❌ Confirmation email failed")
                            notification.email_sent = False
                            notification.email_opened_by_client = False
                            notification.save(update_fields=['email_sent', 'email_opened_by_client'])
                            email_sent = False
                        
                    except Exception as e:
                        logger.error(f"Confirmation email error: {e}")
                        print(f"❌ Confirmation email error: {e}")
                        email_sent = False
                        notification.email_sent = False
                        notification.save(update_fields=['email_sent'])
                else:
                    print(f"❌ Email validation failed for confirmation: {validation_message}")
                    email_sent = False
                    notification.email_sent = False
                    notification.save(update_fields=['email_sent'])
            else:
                print(f"⚠️ No email address for confirmation")
                email_sent = False
            
            # ✅ CHECK FINAL STATUS
            notification.refresh_from_db()
            final_email_status = notification.email_sent
            
            if final_email_status:
                message = f"""✅ Réservation CONFIRMÉE
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
✅ Email de confirmation avec tracking envoyé à {reservation.customer_email}
📊 Status: Email envoyé avec succès

Action effectuée avec succès"""
                
                title = f"✅ Confirmée - {reservation.customer_name}"
                priority = 'info'
                message_type = 'email_success'
                
            else:
                # Confirmation but email failed
                email_display = reservation.customer_email if reservation.customer_email else "Non fourni"
                message = f"""✅ Réservation CONFIRMÉE (email échoué)
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
❌ EMAIL DE CONFIRMATION ÉCHOUÉ
📧 Email: {email_display}
📞 {reservation.customer_phone} ← APPELER LE CLIENT

⚠️ Email de confirmation non envoyé - Action requise"""
                
                title = f"⚠️ Confirmée (email échoué) - {reservation.customer_name}"
                priority = 'urgent'
                message_type = 'email_failed'
        
        elif new_status in ['Annulée', 'cancelled']:
            # CANCELLED
            print(f"❌ Processing CANCELLATION for {reservation.customer_name}")
            
            if reservation.customer_email and reservation.customer_email.strip():
                # ✅ VALIDATE EMAIL FIRST
                is_valid, validation_message = validate_email_address_properly(reservation.customer_email)
                
                if is_valid:
                    try:
                        print(f"📧 Attempting to send cancellation email to: {reservation.customer_email}")
                        email_sent = send_reservation_cancellation_email(reservation, notification)
                        
                        # ✅ DOUBLE-CHECK actual status
                        notification.refresh_from_db()
                        actual_email_sent = notification.email_sent
                        
                        if not (email_sent and actual_email_sent):
                            print(f"❌ Cancellation email failed")
                            notification.email_sent = False
                            notification.save(update_fields=['email_sent'])
                            email_sent = False
                            
                    except Exception as e:
                        logger.error(f"Cancellation email error: {e}")
                        print(f"❌ Cancellation email error: {e}")
                        email_sent = False
                        notification.email_sent = False
                        notification.save(update_fields=['email_sent'])
                else:
                    print(f"❌ Email validation failed for cancellation: {validation_message}")
                    email_sent = False
                    notification.email_sent = False
                    notification.save(update_fields=['email_sent'])
            else:
                print(f"⚠️ No email address for cancellation")
                email_sent = False
            
            # ✅ CHECK FINAL STATUS
            notification.refresh_from_db()
            final_email_status = notification.email_sent
            
            message = f"""❌ Réservation ANNULÉE
📅 {reservation.date.strftime('%d/%m/%Y')} à {reservation.time.strftime('%H:%M')}
👥 {reservation.number_of_guests} personne{'s' if reservation.number_of_guests > 1 else ''}
{'✅ Email d\'annulation avec tracking envoyé' if final_email_status else '❌ EMAIL D\'ANNULATION ÉCHOUÉ'}
📊 Status: {'Email envoyé avec succès' if final_email_status else 'Email non envoyé'}

Annulation traitée"""
            
            title = f"❌ Annulée - {reservation.customer_name}"
            priority = 'normal' if final_email_status else 'urgent'
            message_type = 'email_success' if final_email_status else 'email_failed'
        
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
        
        # Update the notification with final content
        notification.title = title
        notification.message = message.strip()
        notification.priority = priority
        notification.message_type = message_type
        notification.save(update_fields=['title', 'message', 'priority', 'message_type'])
        
        print(f"✅ Status change notification created: {notification.title}")
        print(f"📊 Final tracking status: email_sent={notification.email_sent}")
        
    except Exception as e:
        logger.error(f"Error handling status change: {e}")
        print(f"❌ Erreur changement de statut: {e}")
        import traceback
        traceback.print_exc()

@receiver(post_delete, sender=Reservation)
def reservation_deleted_message(sender, instance, **kwargs):
    """Create message when reservation is deleted with email tracking"""
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            return
        
        # ✅ CREATE NOTIFICATION FIRST to get tracking token
        notification = Notification.objects.create(
            user=admin_user,
            title=f"🗑️ Supprimée - {instance.customer_name}",
            message="Processing deletion...",
            message_type='info',
            priority='normal',
            is_read=False,
            read_at=None,
            # ✅ CRITICAL: Start with email_sent=False
            email_sent=False,
            email_opened_by_client=False
        )
        
        # Send cancellation email if possible
        email_sent = False
        if instance.customer_email and instance.customer_email.strip():
            # ✅ VALIDATE EMAIL FIRST
            is_valid, validation_message = validate_email_address_properly(instance.customer_email)
            
            if is_valid:
                try:
                    email_sent = send_reservation_cancellation_email(instance, notification)
                    
                    # ✅ DOUBLE-CHECK actual status
                    notification.refresh_from_db()
                    if not (email_sent and notification.email_sent):
                        notification.email_sent = False
                        notification.save(update_fields=['email_sent'])
                        email_sent = False
                        
                except Exception as e:
                    logger.error(f"Deletion email error: {e}")
                    email_sent = False
                    notification.email_sent = False
                    notification.save(update_fields=['email_sent'])
            else:
                print(f"❌ Email validation failed for deletion: {validation_message}")
                email_sent = False
        
        # ✅ CHECK FINAL STATUS
        notification.refresh_from_db()
        final_email_status = notification.email_sent
        
        message = f"""🗑️ Réservation SUPPRIMÉE
📅 {instance.date.strftime('%d/%m/%Y')} à {instance.time.strftime('%H:%M')}
👥 {instance.number_of_guests} personne{'s' if instance.number_of_guests > 1 else ''}
{'✅ Email d\'annulation avec tracking envoyé' if final_email_status else '❌ EMAIL D\'ANNULATION ÉCHOUÉ'}
📊 Status: {'Email envoyé avec succès' if final_email_status else 'Email non envoyé'}

Réservation définitivement supprimée du système"""
        
        # Update notification with final message
        notification.message = message.strip()
        notification.save(update_fields=['message'])
        
        print(f"✅ Message avec tracking créé pour suppression: {instance.customer_name}")
        print(f"📊 Final tracking status: email_sent={notification.email_sent}")
        
    except Exception as e:
        logger.error(f"Error creating deletion message: {e}")
        print(f"❌ Erreur message suppression: {e}")

# Helper function to create custom messages with tracking
def create_custom_admin_message(title, message, priority='normal', message_type='info', reservation=None, send_email=False):
    """Create custom admin message with optional email tracking"""
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            return None
        
        notification = Notification.objects.create(
            user=admin_user,
            title=title,
            message=message,
            message_type=message_type,
            priority=priority,
            related_reservation=reservation,
            is_read=False,
            read_at=None,
            # ✅ Start with email_sent=False
            email_sent=False,
            email_opened_by_client=False
        )
        
        # Optional: Send email with tracking (with validation)
        if send_email and reservation and reservation.customer_email:
            # ✅ VALIDATE EMAIL FIRST
            is_valid, validation_message = validate_email_address_properly(reservation.customer_email)
            
            if is_valid:
                try:
                    if message_type == 'reservation_confirmed':
                        send_reservation_confirmation_email(reservation, notification)
                    elif message_type == 'reservation_cancelled':
                        send_reservation_cancellation_email(reservation, notification)
                    else:
                        send_reservation_pending_email(reservation, notification)
                except Exception as e:
                    logger.error(f"Error sending custom email: {e}")
            else:
                print(f"❌ Custom email not sent - validation failed: {validation_message}")
        
        return notification
        
    except Exception as e:
        logger.error(f"Error creating custom message: {e}")
        return None

# ✅ EMAIL TRACKING UTILITY FUNCTIONS
def get_email_tracking_stats():
    """Get email tracking statistics"""
    from datetime import timedelta
    from django.utils import timezone
    
    try:
        # Last 30 days stats
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        notifications = Notification.objects.filter(
            created_at__gte=thirty_days_ago,
            email_sent=True
        )
        
        total_sent = notifications.count()
        total_opened = notifications.filter(email_opened_by_client=True).count()
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        
        # Recent openings
        recent_openings = notifications.filter(
            email_opened_by_client=True
        ).order_by('-email_opened_at')[:5]
        
        stats = {
            'total_sent': total_sent,
            'total_opened': total_opened,
            'open_rate': round(open_rate, 1),
            'recent_openings': [
                {
                    'customer_name': n.related_reservation.customer_name if n.related_reservation else 'N/A',
                    'opened_at': n.email_opened_at.strftime('%d/%m/%Y %H:%M') if n.email_opened_at else 'N/A',
                    'title': n.title
                }
                for n in recent_openings
            ]
        }
        
        print(f"📊 Email tracking stats: {total_sent} sent, {total_opened} opened ({open_rate}%)")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting email tracking stats: {e}")
        return {
            'total_sent': 0,
            'total_opened': 0,
            'open_rate': 0,
            'recent_openings': []
        }

def mark_notification_email_opened(tracking_token, request=None):
    """Mark a notification's email as opened by client"""
    try:
        notification = Notification.objects.get(tracking_token=tracking_token)
        
        if not notification.email_opened_by_client:
            notification.mark_email_as_opened(request)
            
            print(f"📧 Email opened for notification: {notification.title}")
            return True
            
        return False
        
    except Notification.DoesNotExist:
        logger.error(f"Notification not found for tracking token: {tracking_token}")
        return False
    except Exception as e:
        logger.error(f"Error marking email as opened: {e}")
        return False

# Test function with tracking
def test_email_confirmation_with_tracking(reservation_id):
    """Test function to manually send confirmation email with tracking"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        print(f"🔍 Testing confirmation email with tracking for: {reservation.customer_name}")
        print(f"🔍 Email: {reservation.customer_email}")
        print(f"🔍 Status: {reservation.status}")
        
        # ✅ VALIDATE EMAIL FIRST
        if reservation.customer_email:
            is_valid, validation_message = validate_email_address_properly(reservation.customer_email)
            print(f"🔍 Email validation: {is_valid} - {validation_message}")
            
            if not is_valid:
                print(f"❌ Cannot test - email validation failed")
                return False
        else:
            print(f"❌ Cannot test - no email address")
            return False
        
        # Create test notification
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("❌ No admin user found")
            return False
        
        notification = Notification.objects.create(
            user=admin_user,
            title=f"🧪 Test - {reservation.customer_name}",
            message="Test email with tracking",
            message_type='reservation_confirmed',
            priority='info',
            related_reservation=reservation,
            is_read=False,
            # ✅ Start with email_sent=False
            email_sent=False,
            email_opened_by_client=False
        )
        
        result = send_reservation_confirmation_email(reservation, notification)
        
        # Check final status
        notification.refresh_from_db()
        print(f"📧 Email result: {result}")
        print(f"📊 Tracking token: {notification.tracking_token}")
        print(f"📊 Final email_sent status: {notification.email_sent}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test email error: {e}")
        return False

# ✅ ENHANCED TEST FUNCTIONS
def test_email_validation_signals():
    """Test email validation in signals"""
    print("🧪 Testing email validation in signals...")
    
    test_emails = [
        "fatimzah@gmail.com",        # Should work
        "invalid-email",             # Should fail - no @
        "test@nonexistent.fake",     # Should fail format-wise but pass basic validation
        "",                          # Should fail - empty
        None,                        # Should fail - None
        "test@",                     # Should fail - incomplete
        "@domain.com",               # Should fail - no local part
        "very.long.email.address.that.exceeds.the.maximum.length.allowed.by.rfc.standards@example.com",  # Should fail - too long
    ]
    
    for email in test_emails:
        print(f"\n📧 Testing email: '{email}'")
        is_valid, message = validate_email_address_properly(email)
        print(f"   ✅ Valid: {is_valid}")
        print(f"   📝 Message: {message}")
    
    return True

def test_reservation_with_invalid_email():
    """Test creating a reservation with invalid email to verify proper handling"""
    try:
        print("🧪 Testing reservation creation with invalid email...")
        
        # You would need to create a test reservation here
        # This is just a template - adjust based on your Reservation model
        
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        # Create test reservation with invalid email
        test_reservation_data = {
            'customer_name': 'Test Customer',
            'customer_email': 'invalid-email-format',  # Invalid email
            'customer_phone': '0612345678',
            'date': timezone.now().date() + timedelta(days=1),
            'time': datetime.now().time(),
            'number_of_guests': 2,
            'status': 'En attente'
        }
        
        print(f"📧 Would create reservation with email: {test_reservation_data['customer_email']}")
        
        # Validate the email first
        is_valid, message = validate_email_address_properly(test_reservation_data['customer_email'])
        print(f"📧 Email validation result: {is_valid} - {message}")
        
        if not is_valid:
            print("✅ Test passed - invalid email correctly detected")
            return True
        else:
            print("❌ Test failed - invalid email not detected")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_reservation_with_valid_email():
    """Test creating a reservation with valid email"""
    try:
        print("🧪 Testing reservation creation with valid email...")
        
        test_email = "fatimzah@gmail.com"  # Your valid email
        
        # Validate the email
        is_valid, message = validate_email_address_properly(test_email)
        print(f"📧 Email validation result for {test_email}: {is_valid} - {message}")
        
        if is_valid:
            print("✅ Test passed - valid email correctly detected")
            return True
        else:
            print("❌ Test failed - valid email incorrectly rejected")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

# Cleanup function with tracking info
def cleanup_old_notifications(days=30):
    """Clean up old read notifications (preserves tracking data for recent notifications)"""
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Only delete notifications that are read AND old AND have no recent email activity
        old_notifications = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_date
        ).exclude(
            # Keep notifications with recent email tracking activity
            email_opened_at__gte=timezone.now() - timedelta(days=7)
        )
        
        count = old_notifications.count()
        
        # Log some stats before deletion
        email_tracking_stats = []
        for notification in old_notifications[:10]:  # Sample first 10
            if notification.email_sent:
                email_tracking_stats.append({
                    'title': notification.title,
                    'sent': notification.email_sent,
                    'opened': notification.email_opened_by_client,
                    'customer': getattr(notification.related_reservation, 'customer_name', 'N/A') if notification.related_reservation else 'N/A'
                })
        
        # Delete old notifications
        old_notifications.delete()
        
        logger.info(f"Cleaned up {count} old notifications")
        print(f"✅ {count} anciennes notifications supprimées")
        
        if email_tracking_stats:
            print("📊 Sample email tracking data from deleted notifications:")
            for stat in email_tracking_stats:
                print(f"  - {stat['customer']}: Email {'opened' if stat['opened'] else 'not opened'}")
        
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {e}")
        print(f"❌ Erreur nettoyage notifications: {e}")
        return 0

# Periodic task to update email tracking stats (can be called from management command)
def update_email_tracking_summary():
    """Update email tracking summary for reporting"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        stats = get_email_tracking_stats()
        
        # You could save these stats to a separate model for reporting
        # For now, just log them
        logger.info(f"Email tracking summary: {stats}")
        
        # Identify customers who haven't opened emails for follow-up
        unread_notifications = Notification.objects.filter(
            email_sent=True,
            email_opened_by_client=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('related_reservation')
        
        if unread_notifications.exists():
            print(f"⚠️ {unread_notifications.count()} emails sent but not opened in last 7 days:")
            for notification in unread_notifications[:5]:  # Show first 5
                customer_name = notification.related_reservation.customer_name if notification.related_reservation else 'N/A'
                print(f"  - {customer_name}: {notification.title}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error updating email tracking summary: {e}")
        return None

# ✅ FUNCTION TO REFRESH NOTIFICATION MESSAGES WITH CURRENT TRACKING STATUS
def refresh_notification_tracking_display():
    """Refresh all notification messages to show current email tracking status"""
    try:
        # Get all notifications with email tracking
        notifications_with_emails = Notification.objects.filter(
            email_sent=True,
            related_reservation__isnull=False
        )
        
        updated_count = 0
        
        for notification in notifications_with_emails:
            old_message = notification.message
            
            # Replace old tracking status with current status
            if "📊 Tracking: Email non ouvert" in old_message:
                if notification.email_opened_by_client:
                    # Check if notification has email_status_display method/property
                    try:
                        status_display = notification.email_status_display
                    except AttributeError:
                        status_display = "Email ouvert" if notification.email_opened_by_client else "Email non ouvert"
                    
                    new_message = old_message.replace(
                        "📊 Tracking: Email non ouvert",
                        f"📊 Status: {status_display}"
                    )
                    notification.message = new_message
                    notification.save(update_fields=['message'])
                    updated_count += 1
            elif "📊 Tracking:" in old_message and "📊 Status:" not in old_message:
                # Update any old tracking format to new status format
                import re
                try:
                    status_display = notification.email_status_display
                except AttributeError:
                    status_display = "Email ouvert" if notification.email_opened_by_client else "Email non ouvert"
                
                new_message = re.sub(
                    r"📊 Tracking:.*",
                    f"📊 Status: {status_display}",
                    old_message
                )
                if new_message != old_message:
                    notification.message = new_message
                    notification.save(update_fields=['message'])
                    updated_count += 1
        
        print(f"✅ Updated {updated_count} notifications with current tracking status")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error refreshing notification tracking display: {e}")
        print(f"❌ Error refreshing tracking display: {e}")
        return 0

# ✅ DEBUGGING FUNCTIONS
def debug_email_sending(reservation_id):
    """Debug email sending for a specific reservation"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        
        print(f"🔍 DEBUGGING EMAIL for reservation ID: {reservation_id}")
        print(f"🔍 Customer: {reservation.customer_name}")
        print(f"🔍 Email: '{reservation.customer_email}'")
        print(f"🔍 Phone: {reservation.customer_phone}")
        print(f"🔍 Status: {reservation.status}")
        
        # Step 1: Validate email
        if reservation.customer_email:
            is_valid, validation_message = validate_email_address_properly(reservation.customer_email)
            print(f"📧 Email validation: {is_valid}")
            print(f"📧 Validation message: {validation_message}")
            
            if is_valid:
                print("✅ Email validation passed - email format is correct")
                
                # Step 2: Test email sending
                print("📧 Testing email sending...")
                
                # Create a test notification
                admin_user = User.objects.filter(is_superuser=True).first()
                if admin_user:
                    test_notification = Notification.objects.create(
                        user=admin_user,
                        title=f"🧪 DEBUG TEST - {reservation.customer_name}",
                        message="Testing email sending",
                        message_type='test',
                        priority='info',
                        related_reservation=reservation,
                        is_read=False,
                        email_sent=False,
                        email_opened_by_client=False
                    )
                    
                    # Try to send
                    result = send_reservation_pending_email(reservation, test_notification)
                    
                    # Check results
                    test_notification.refresh_from_db()
                    
                    print(f"📧 Send function returned: {result}")
                    print(f"📧 Notification email_sent: {test_notification.email_sent}")
                    
                    if result and test_notification.email_sent:
                        print("✅ EMAIL SENDING SUCCESSFUL")
                    else:
                        print("❌ EMAIL SENDING FAILED")
                        
                    # Clean up test notification
                    test_notification.delete()
                    
                else:
                    print("❌ No admin user found for testing")
            else:
                print(f"❌ Email validation failed: {validation_message}")
        else:
            print("❌ No email address provided")
            
    except Reservation.DoesNotExist:
        print(f"❌ Reservation with ID {reservation_id} not found")
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

def get_notification_summary():
    """Get summary of recent notifications and their email status"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Get recent notifications (last 7 days)
        recent_notifications = Notification.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')[:20]
        
        print("📊 RECENT NOTIFICATIONS SUMMARY (Last 7 days)")
        print("=" * 60)
        
        for notification in recent_notifications:
            customer_name = notification.related_reservation.customer_name if notification.related_reservation else 'N/A'
            email = notification.related_reservation.customer_email if notification.related_reservation else 'N/A'
            
            email_status = "✅ Sent" if notification.email_sent else "❌ Failed"
            if notification.email_sent and notification.email_opened_by_client:
                email_status += " & Opened"
            elif notification.email_sent:
                email_status += " (Not opened)"
            
            print(f"📨 {notification.title}")
            print(f"   👤 Customer: {customer_name}")
            print(f"   📧 Email: {email}")
            print(f"   📊 Status: {email_status}")
            print(f"   🕐 Created: {notification.created_at.strftime('%d/%m/%Y %H:%M')}")
            print(f"   🔗 Type: {notification.message_type}")
            print("-" * 40)
        
        # Summary stats
        total_with_email = recent_notifications.filter(
            related_reservation__customer_email__isnull=False
        ).exclude(related_reservation__customer_email='').count()
        
        emails_sent = recent_notifications.filter(email_sent=True).count()
        emails_opened = recent_notifications.filter(
            email_sent=True, 
            email_opened_by_client=True
        ).count()
        
        print(f"📊 SUMMARY:")
        print(f"   Total notifications: {recent_notifications.count()}")
        print(f"   With email address: {total_with_email}")
        print(f"   Emails sent: {emails_sent}")
        print(f"   Emails opened: {emails_opened}")
        
        if emails_sent > 0:
            open_rate = (emails_opened / emails_sent) * 100
            print(f"   Open rate: {open_rate:.1f}%")
        
        return {
            'total': recent_notifications.count(),
            'with_email': total_with_email,
            'sent': emails_sent,
            'opened': emails_opened
        }
        
    except Exception as e:
        print(f"❌ Error getting notification summary: {e}")
        return None

# ✅ FINAL TEST FUNCTION TO RUN ALL TESTS
def run_all_email_tests():
    """Run all email validation and sending tests"""
    print("🧪 RUNNING ALL EMAIL TESTS")
    print("=" * 50)
    
    try:
        # Test 1: Email validation
        print("\n1️⃣ Testing email validation...")
        test_email_validation_signals()
        
        # Test 2: Valid email test
        print("\n2️⃣ Testing valid email...")
        test_reservation_with_valid_email()
        
        # Test 3: Invalid email test
        print("\n3️⃣ Testing invalid email...")
        test_reservation_with_invalid_email()
        
        # Test 4: Get notification summary
        print("\n4️⃣ Getting notification summary...")
        get_notification_summary()
        
        # Test 5: Email tracking stats
        print("\n5️⃣ Getting email tracking stats...")
        get_email_tracking_stats()
        
        print("\n✅ ALL TESTS COMPLETED")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()

# ✅ UTILITY TO CHECK EXISTING RESERVATIONS
def check_existing_reservations_emails():
    """Check email addresses in existing reservations"""
    try:
        print("🔍 CHECKING EXISTING RESERVATIONS EMAIL ADDRESSES")
        print("=" * 60)
        
        # Get recent reservations
        reservations = Reservation.objects.all().order_by('-id')[:10]
        
        valid_count = 0
        invalid_count = 0
        no_email_count = 0
        
        for reservation in reservations:
            print(f"\n📋 Reservation ID: {reservation.id}")
            print(f"   👤 Customer: {reservation.customer_name}")
            print(f"   📧 Email: '{reservation.customer_email}'")
            
            if reservation.customer_email and reservation.customer_email.strip():
                is_valid, message = validate_email_address_properly(reservation.customer_email)
                if is_valid:
                    print(f"   ✅ Valid email")
                    valid_count += 1
                else:
                    print(f"   ❌ Invalid email: {message}")
                    invalid_count += 1
            else:
                print(f"   ⚠️ No email address")
                no_email_count += 1
        
        print(f"\n📊 SUMMARY:")
        print(f"   Valid emails: {valid_count}")
        print(f"   Invalid emails: {invalid_count}")
        print(f"   No email: {no_email_count}")
        print(f"   Total checked: {len(reservations)}")
        
        return {
            'valid': valid_count,
            'invalid': invalid_count,
            'no_email': no_email_count,
            'total': len(reservations)
        }
        
    except Exception as e:
        print(f"❌ Error checking existing reservations: {e}")
        return None