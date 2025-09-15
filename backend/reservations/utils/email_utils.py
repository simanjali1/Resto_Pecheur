from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import logging
import re

logger = logging.getLogger(__name__)

def check_email_blacklist(email):
    """Check if email is in a blacklist of known non-existent patterns"""
    blacklist_patterns = [
        r'^.*aaaaa.*@gmail\.com$',  # Multiple 'a's like fatimaaaaaa
        r'^.*test.*@test\..*$',
        r'^.*fake.*@fake\..*$',
        r'^admin@example\.com$',
        r'^test@test\.com$',
        r'^.*noreply.*@.*\.com$',
        r'^fatimazah@gmail\.com$',  # The exact problematic email
    ]
    
    email_lower = email.lower()
    
    for pattern in blacklist_patterns:
        if re.match(pattern, email_lower):
            return True, "Email address not accepted"
    
    return False, "Email not in blacklist"

def validate_email_address_properly(email):
    """Simplified email validation without SMTP checking"""
    try:
        if not email or not email.strip():
            return False, "No email address provided"
        
        email = email.strip()
        
        if len(email) > 254:
            return False, "Email address too long"
        
        if email.count('@') != 1:
            return False, "Invalid email format - multiple @ symbols"
        
        local, domain = email.split('@')
        if len(local) > 64:
            return False, "Email local part too long"
        
        try:
            validate_email(email)
        except ValidationError as e:
            return False, f"Invalid email format: {str(e)}"
        
        is_blacklisted, blacklist_msg = check_email_blacklist(email)
        if is_blacklisted:
            return False, blacklist_msg
        
        return True, "Email format valid"
        
    except Exception as e:
        return False, f"Email validation error: {str(e)}"

def send_mail_with_proper_error_handling(subject, message, from_email, recipient_list):
    """Send mail with basic validation only"""
    try:
        # Basic validation for all recipients
        for email in recipient_list:
            try:
                validate_email(email)
                is_blacklisted, _ = check_email_blacklist(email)
                if is_blacklisted:
                    return False, f"Email address not accepted: {email}"
            except ValidationError:
                return False, f"Invalid email format: {email}"
        
        # Send the email
        result = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        if result == len(recipient_list):
            return True, "Email sent successfully"
        else:
            return False, f"Email sending failed. Only {result} of {len(recipient_list)} emails sent"
    
    except Exception as e:
        logger.error(f"Email sending error: {e}")
        return False, f"Email sending failed: {str(e)}"

def generate_tracking_url(notification, action_type="view"):
    """Generate tracking URL for email"""
    try:
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
       
        if action_type == "view":
            try:
                tracking_url = reverse('email_tracking', kwargs={
                    'token': notification.tracking_token
                })
            except:
                tracking_url = f"/track/{notification.tracking_token}/"
        else:
            try:
                tracking_url = reverse('email_tracking_action', kwargs={
                    'token': notification.tracking_token,
                    'action': action_type
                })
            except:
                tracking_url = f"/track/{notification.tracking_token}/{action_type}/"
       
        return f"{base_url}{tracking_url}"
       
    except Exception as e:
        logger.error(f"Error generating tracking URL: {e}")
        return "#"

def send_reservation_pending_email(reservation, notification=None):
    """Send pending notification email"""
    try:
        if not reservation.customer_email:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        
        if not is_valid:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
        
        subject = f"Demande de Réservation Reçue - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Merci pour votre demande de réservation au Resto Pêcheur!

Détails de votre demande:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date demandée: {reservation.date.strftime('%d %B %Y')}
• Heure demandée: {reservation.time.strftime('%H:%M')}
• Statut: En cours de traitement

Suivre votre demande: {view_url}

Votre demande est actuellement en cours d'examen. Nous vous notifierons dès qu'elle sera confirmée.

Cordialement,
L'équipe Resto Pêcheur
Adresse: Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc
Téléphone: 0661-460593
Site web: www.restopecheur.ma
        """
        
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        if notification:
            if success:
                notification.mark_email_as_sent()
            else:
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.save(update_fields=['email_sent', 'email_opened_by_client'])
        
        return success
        
    except Exception as e:
        logger.error(f"Pending email error: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False

def send_reservation_confirmation_email(reservation, notification=None):
    """Send confirmation email"""
    try:
        if not reservation.customer_email:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        
        if not is_valid:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
        
        subject = f"Réservation Confirmée - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Excellente nouvelle! Votre réservation a été CONFIRMÉE.

Détails de la réservation:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: {reservation.date.strftime('%d %B %Y')}
• Heure: {reservation.time.strftime('%H:%M')}
• Statut: Confirmée

Voir les détails de votre réservation: {view_url}

En cas de problème, contactez-nous au 0661-460593.

Nous avons hâte de vous accueillir au Resto Pêcheur!

Cordialement,
L'équipe Resto Pêcheur
Adresse: Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc
Téléphone: 0661-460593
Site web: www.restopecheur.ma
        """
        
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        if notification:
            if success:
                notification.mark_email_as_sent()
            else:
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.save(update_fields=['email_sent', 'email_opened_by_client'])
        
        return success
        
    except Exception as e:
        logger.error(f"Confirmation email error: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False

def send_reservation_cancellation_email(reservation, notification=None):
    """Send cancellation email"""
    try:
        if not reservation.customer_email:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        
        if not is_valid:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
        
        subject = f"Réservation Annulée - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Nous regrettons de vous informer que votre réservation a été annulée.

Détails de la réservation annulée:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: {reservation.date.strftime('%d %B %Y')}
• Heure: {reservation.time.strftime('%H:%M')}

Voir les détails: {view_url}

Si vous avez des questions, n'hésitez pas à nous contacter au 0661-460593.

Nous espérons vous accueillir prochainement!

Cordialement,
L'équipe Resto Pêcheur
        """
        
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        if notification:
            if success:
                notification.mark_email_as_sent()
            else:
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.save(update_fields=['email_sent', 'email_opened_by_client'])
        
        return success
        
    except Exception as e:
        logger.error(f"Cancellation email error: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False

def send_reservation_reminder_email(reservation, notification=None):
    """Send reminder email"""
    try:
        if not reservation.customer_email:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        if not is_valid:
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
       
        subject = f"Rappel - Votre réservation aujourd'hui - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},
 
Nous vous rappelons votre réservation aujourd'hui au Resto Pêcheur.
 
Détails de votre réservation:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: Aujourd'hui ({reservation.date.strftime('%d %B %Y')})
• Heure: {reservation.time.strftime('%H:%M')}
 
Voir votre réservation: {view_url}
 
Nous vous attendons avec plaisir!
 
En cas d'imprévu, merci de nous contacter au 0661-460593.
 
À bientôt,
L'équipe Resto Pêcheur
Adresse: Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc
        """
       
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        if notification:
            if success:
                notification.mark_email_as_sent()
            else:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
        
        return success
       
    except Exception as e:
        logger.error(f"Reminder email error: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False