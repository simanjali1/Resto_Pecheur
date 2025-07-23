from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_reservation_confirmation_email(reservation):
    """Send confirmation email to customer for Resto Pêcheur"""
    try:
        subject = f"✅ Réservation Confirmée - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Excellente nouvelle! Votre réservation a été CONFIRMÉE.

Détails de la réservation:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: {reservation.date.strftime('%d %B %Y')}
• Heure: {reservation.time.strftime('%H:%M')}
• Statut: Confirmée

Nous avons hâte de vous accueillir au Resto Pêcheur!

Cordialement,
L'équipe Resto Pêcheur
📍 Adresse: Tangier, Morocco
📞 Téléphone: 0661-460593
🌐 Site web: www.restopecheur.ma
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email],
            fail_silently=False,
        )
        
        print(f"✅ Email de confirmation envoyé à {reservation.customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur envoi email confirmation: {e}")
        print(f"❌ Erreur envoi email confirmation: {e}")
        return False

def send_reservation_cancellation_email(reservation):
    """Send cancellation email to customer"""
    try:
        subject = f"❌ Réservation Annulée - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Nous regrettons de vous informer que votre réservation a été annulée.

Détails de la réservation annulée:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: {reservation.date.strftime('%d %B %Y')}
• Heure: {reservation.time.strftime('%H:%M')}

Si vous avez des questions, n'hésitez pas à nous contacter au 0661-460593.

Nous espérons vous accueillir prochainement!

Cordialement,
L'équipe Resto Pêcheur
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email],
            fail_silently=False,
        )
        
        print(f"✅ Email d'annulation envoyé à {reservation.customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur envoi email annulation: {e}")
        print(f"❌ Erreur envoi email annulation: {e}")
        return False

def send_reservation_pending_email(reservation):
    """Send pending notification email to customer"""
    try:
        subject = f"⏳ Demande de Réservation Reçue - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Merci pour votre demande de réservation au Resto Pêcheur!

Détails de votre demande:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date demandée: {reservation.date.strftime('%d %B %Y')}
• Heure demandée: {reservation.time.strftime('%H:%M')}
• Statut: En cours de traitement

Votre demande est actuellement en cours d'examen. Nous vous notifierons dès qu'elle sera confirmée.

Cordialement,
L'équipe Resto Pêcheur
📍 Adresse: Tangier, Morocco
📞 Téléphone: 0661-460593
🌐 Site web: www.restopecheur.ma
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email],
            fail_silently=False,
        )
        
        print(f"✅ Email en attente envoyé à {reservation.customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur envoi email en attente: {e}")
        print(f"❌ Erreur envoi email en attente: {e}")
        return False

def send_reservation_reminder_email(reservation):
    """Send reminder email for upcoming reservations"""
    try:
        subject = f"🔔 Rappel - Votre réservation aujourd'hui - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Nous vous rappelons votre réservation aujourd'hui au Resto Pêcheur.

Détails de votre réservation:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: Aujourd'hui ({reservation.date.strftime('%d %B %Y')})
• Heure: {reservation.time.strftime('%H:%M')}

Nous vous attendons avec plaisir!

En cas d'imprévu, merci de nous contacter au 0661-460593.

À bientôt,
L'équipe Resto Pêcheur
📍 Adresse: Tangier, Morocco
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email],
            fail_silently=False,
        )
        
        print(f"✅ Email de rappel envoyé à {reservation.customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur envoi email rappel: {e}")
        print(f"❌ Erreur envoi email rappel: {e}")
        return False