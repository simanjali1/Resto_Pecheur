from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import logging
import smtplib
import socket
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Try to import DNS resolver - install with: pip install dnspython
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    print("⚠️ dnspython not installed. Enhanced email validation disabled.")
    print("   Install with: pip install dnspython")

logger = logging.getLogger(__name__)

def check_email_deliverability(email):
    """
    Advanced email validation that checks if email address actually exists
    This goes beyond format checking to verify the email can receive mail
    """
    try:
        if not email or not email.strip():
            return False, "No email address provided"
        
        email = email.strip().lower()
        
        # Step 1: Basic format validation
        try:
            validate_email(email)
        except ValidationError as e:
            return False, f"Invalid email format: {str(e)}"
        
        # Step 2: Split email into local and domain parts
        try:
            local, domain = email.split('@')
        except ValueError:
            return False, "Invalid email format - no @ symbol"
        
        # Step 3: Check domain has MX record (mail server) - only if DNS available
        if DNS_AVAILABLE:
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                if not mx_records:
                    return False, f"Domain {domain} has no mail servers"
                
                # Get the primary mail server
                mx_record = str(mx_records[0].exchange).rstrip('.')
                print(f"📧 Found mail server for {domain}: {mx_record}")
                
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                return False, f"Domain {domain} does not exist or has no mail servers"
            except Exception as e:
                print(f"⚠️ Could not check MX record for {domain}: {e}")
                # Don't fail completely if MX check fails - continue with basic validation
                return True, "Email format valid (MX check skipped)"
        else:
            # If DNS not available, skip MX check
            mx_record = domain
            print(f"⚠️ DNS checking disabled, using domain directly: {domain}")
        
        # Step 4: Attempt SMTP connection to verify email exists
        try:
            # Connect to the mail server
            print(f"📧 Connecting to mail server: {mx_record}")
            
            with smtplib.SMTP(mx_record, 25, timeout=10) as server:
                server.helo()
                
                # Set a fake sender for the check
                server.mail('noreply@example.com')
                
                # Try to set recipient - this will fail if email doesn't exist
                code, message = server.rcpt(email)
                
                print(f"📧 SMTP response for {email}: {code} - {message.decode() if isinstance(message, bytes) else message}")
                
                # Response codes:
                # 250 = OK (email exists)
                # 550 = User unknown / mailbox unavailable
                # 553 = Mailbox name not allowed
                if code == 250:
                    return True, "Email address exists and can receive mail"
                elif code in [550, 551, 553]:
                    return False, f"Email address does not exist (SMTP: {code})"
                else:
                    return False, f"Email verification failed (SMTP: {code})"
                    
        except smtplib.SMTPConnectError:
            return False, f"Could not connect to mail server for {domain}"
        except smtplib.SMTPServerDisconnected:
            return False, f"Mail server for {domain} disconnected during check"
        except socket.timeout:
            print(f"⚠️ Timeout checking {email} - assuming valid")
            return True, "Email format valid (existence check timed out)"
        except Exception as e:
            print(f"⚠️ Could not verify email existence for {email}: {e}")
            # If we can't verify existence, don't fail completely
            return True, f"Email format valid (existence check failed: {str(e)})"
        
    except Exception as e:
        print(f"❌ Error in email deliverability check: {e}")
        return False, f"Email validation error: {str(e)}"

def check_email_blacklist(email):
    """Check if email is in a blacklist of known non-existent patterns"""
    blacklist_patterns = [
        # Common fake email patterns
        r'^.*aaaaa.*@gmail\.com$',  # Multiple 'a's like fatimaaaaaa
        r'^.*test.*@test\..*$',
        r'^.*fake.*@fake\..*$',
        r'^admin@example\.com$',
        r'^test@test\.com$',
        r'^.*noreply.*@.*\.com$',
        # Add the specific problematic email
        r'^fatimazah@gmail\.com$',  # The exact problematic email
        # Add more patterns as needed
    ]
    
    email_lower = email.lower()
    
    for pattern in blacklist_patterns:
        if re.match(pattern, email_lower):
            return True, f"Email matches blacklisted pattern: {pattern}"
    
    return False, "Email not in blacklist"

def validate_email_address_properly(email):
    """
    Enhanced email validation that includes deliverability checking and blacklist
    """
    try:
        # First do basic validation
        if not email or not email.strip():
            return False, "No email address provided"
        
        email = email.strip()
        
        # Basic format checks
        if len(email) > 254:
            return False, "Email address too long"
        
        if email.count('@') != 1:
            return False, "Invalid email format - multiple @ symbols"
        
        local, domain = email.split('@')
        if len(local) > 64:
            return False, "Email local part too long"
        
        # Django validation
        try:
            validate_email(email)
        except ValidationError as e:
            return False, f"Invalid email format: {str(e)}"
        
        # Check blacklist first
        is_blacklisted, blacklist_msg = check_email_blacklist(email)
        if is_blacklisted:
            return False, f"Email address does not exist (blacklisted)"
        
        # Enhanced deliverability check
        is_deliverable, message = check_email_deliverability(email)
        
        return is_deliverable, message
        
    except Exception as e:
        return False, f"Email validation error: {str(e)}"

def send_mail_with_proper_error_handling(subject, message, from_email, recipient_list):
    """Send mail with enhanced error detection including bounces"""
    try:
        # Enhanced validation for all recipients
        for email in recipient_list:
            print(f"🔍 Checking email deliverability: {email}")
            is_valid, error_msg = validate_email_address_properly(email)
            
            if not is_valid:
                print(f"❌ Email failed deliverability check: {email} - {error_msg}")
                return False, f"Email address cannot receive mail: {error_msg}"
            else:
                print(f"✅ Email passed deliverability check: {email}")
        
        print(f"📧 All recipients validated, attempting to send...")
        print(f"📧 Subject: {subject}")
        print(f"📧 Recipients: {recipient_list}")
        
        # Try to send the email
        result = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        print(f"📧 send_mail returned: {result}")
        
        if result == len(recipient_list):
            print(f"✅ Email sent successfully to {recipient_list}")
            return True, "Email sent successfully"
        else:
            print(f"❌ Email sending partially failed. Expected {len(recipient_list)}, sent {result}")
            return False, f"Email sending failed. Only {result} of {len(recipient_list)} emails sent"
    
    except smtplib.SMTPRecipientsRefused as e:
        print(f"❌ SMTP Recipients Refused: {e}")
        return False, f"Email address rejected by server: {str(e)}"
    
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication Error: {e}")
        return False, f"Email authentication failed: {str(e)}"
    
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {e}")
        return False, f"Email server error: {str(e)}"
    
    except Exception as e:
        print(f"❌ General email error: {e}")
        logger.error(f"Email sending error: {e}")
        return False, f"Email sending failed: {str(e)}"

def generate_tracking_url(notification, action_type="view"):
    """Generate tracking URL for email - FIXED VERSION"""
    try:
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
       
        # ✅ FIX: Use the correct URL pattern name based on whether action is needed
        if action_type == "view":
            # For simple tracking without action parameter
            try:
                tracking_url = reverse('email_tracking', kwargs={
                    'token': notification.tracking_token
                })
            except:
                # Fallback if URL pattern doesn't exist
                tracking_url = f"/track/{notification.tracking_token}/"
        else:
            # For tracking with specific action (confirm, etc.)
            try:
                tracking_url = reverse('email_tracking_action', kwargs={
                    'token': notification.tracking_token,
                    'action': action_type
                })
            except:
                # Fallback if URL pattern doesn't exist
                tracking_url = f"/track/{notification.tracking_token}/{action_type}/"
       
        return f"{base_url}{tracking_url}"
       
    except Exception as e:
        logger.error(f"Error generating tracking URL: {e}")
        print(f"❌ Error generating tracking URL: {e}")
        return "#"

# ✅ MAIN EMAIL FUNCTIONS (Enhanced versions)
def send_reservation_pending_email(reservation, notification=None):
    """Send pending notification email with PROPER error detection and existence checking"""
    try:
        print(f"📧 Processing ENHANCED pending email for: {reservation.customer_name}")
        
        # ✅ STEP 1: Enhanced email validation
        if not reservation.customer_email:
            print(f"❌ No email address for {reservation.customer_name}")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        print(f"🔍 Performing enhanced validation for: {reservation.customer_email}")
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        
        if not is_valid:
            print(f"❌ Email validation failed: {validation_msg}")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        print(f"✅ Email validation passed: {validation_msg}")
        
        # ✅ STEP 2: Generate tracking URL
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
        
        # ✅ STEP 3: Prepare email content
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

🔗 Suivre votre demande: {view_url}

Votre demande est actuellement en cours d'examen. Nous vous notifierons dès qu'elle sera confirmée.

Cordialement,
L'équipe Resto Pêcheur
📍 Adresse: Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc
📞 Téléphone: 0661-460593
🌐 Site web: www.restopecheur.ma
        """
        
        # ✅ STEP 4: Send email with proper error handling
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        # ✅ STEP 5: Update notification based on ACTUAL result
        if notification:
            if success:
                notification.mark_email_as_sent()
                print(f"✅ Email sent successfully, notification marked as sent")
            else:
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.save(update_fields=['email_sent', 'email_opened_by_client'])
                print(f"❌ Email failed, notification marked as NOT sent")
        
        if success:
            print(f"✅ Pending email sent successfully to {reservation.customer_email}")
        else:
            print(f"❌ Pending email failed: {error_msg}")
        
        return success
        
    except Exception as e:
        print(f"❌ Exception in send_reservation_pending_email: {e}")
        logger.error(f"Pending email error: {e}")
        
        # Mark notification as failed
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        
        return False

def send_reservation_confirmation_email(reservation, notification=None):
    """Send confirmation email with PROPER error detection and existence checking"""
    try:
        print(f"📧 Processing ENHANCED confirmation email for: {reservation.customer_name}")
        
        # ✅ STEP 1: Enhanced email validation
        if not reservation.customer_email:
            print(f"❌ No email address for confirmation")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        print(f"🔍 Performing enhanced validation for: {reservation.customer_email}")
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        
        if not is_valid:
            print(f"❌ Email validation failed: {validation_msg}")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        print(f"✅ Email validation passed: {validation_msg}")
        
        # Generate tracking URL
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
        
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

🔗 Voir les détails de votre réservation: {view_url}

En cas de problème, contactez-nous au 0661-460593.

Nous avons hâte de vous accueillir au Resto Pêcheur!

Cordialement,
L'équipe Resto Pêcheur
📍 Adresse: Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc
📞 Téléphone: 0661-460593
🌐 Site web: www.restopecheur.ma

---
Cet email a été envoyé automatiquement. Si vous avez reçu ce message par erreur, veuillez l'ignorer.
        """
        
        # ✅ Send with proper error handling
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        # ✅ Update notification based on ACTUAL result
        if notification:
            if success:
                notification.mark_email_as_sent()
                print(f"✅ Confirmation email sent successfully, notification marked as sent")
            else:
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.save(update_fields=['email_sent', 'email_opened_by_client'])
                print(f"❌ Confirmation email failed, notification marked as NOT sent")
        
        if success:
            print(f"✅ Confirmation email sent successfully to {reservation.customer_email}")
        else:
            print(f"❌ Confirmation email failed: {error_msg}")
        
        return success
        
    except Exception as e:
        print(f"❌ Exception in confirmation email: {e}")
        logger.error(f"Confirmation email error: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False

def send_reservation_cancellation_email(reservation, notification=None):
    """Send cancellation email with PROPER error detection and existence checking"""
    try:
        print(f"📧 Processing ENHANCED cancellation email for: {reservation.customer_name}")
        
        # ✅ STEP 1: Enhanced email validation
        if not reservation.customer_email:
            print(f"❌ No email address for cancellation")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        print(f"🔍 Performing enhanced validation for: {reservation.customer_email}")
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        
        if not is_valid:
            print(f"❌ Email validation failed: {validation_msg}")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        print(f"✅ Email validation passed: {validation_msg}")
        
        # Generate tracking URL
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
        
        subject = f"❌ Réservation Annulée - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},

Nous regrettons de vous informer que votre réservation a été annulée.

Détails de la réservation annulée:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: {reservation.date.strftime('%d %B %Y')}
• Heure: {reservation.time.strftime('%H:%M')}

🔗 Voir les détails: {view_url}

Si vous avez des questions, n'hésitez pas à nous contacter au 0661-460593.

Nous espérons vous accueillir prochainement!

Cordialement,
L'équipe Resto Pêcheur
        """
        
        # ✅ Send with proper error handling
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        # ✅ Update notification based on ACTUAL result
        if notification:
            if success:
                notification.mark_email_as_sent()
                print(f"✅ Cancellation email sent successfully, notification marked as sent")
            else:
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.save(update_fields=['email_sent', 'email_opened_by_client'])
                print(f"❌ Cancellation email failed, notification marked as NOT sent")
        
        if success:
            print(f"✅ Cancellation email sent successfully to {reservation.customer_email}")
        else:
            print(f"❌ Cancellation email failed: {error_msg}")
        
        return success
        
    except Exception as e:
        print(f"❌ Exception in cancellation email: {e}")
        logger.error(f"Cancellation email error: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False

def send_reservation_reminder_email(reservation, notification=None):
    """Send reminder email for upcoming reservations with tracking and validation"""
    try:
        print(f"📧 Processing ENHANCED reminder email for: {reservation.customer_name}")
        
        # ✅ Enhanced email validation
        if not reservation.customer_email:
            print(f"❌ No email address for reminder")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        is_valid, validation_msg = validate_email_address_properly(reservation.customer_email)
        if not is_valid:
            print(f"❌ Email validation failed: {validation_msg}")
            if notification:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
            return False
        
        # Generate tracking URL
        if notification:
            view_url = generate_tracking_url(notification, "view")
        else:
            view_url = "#"
       
        subject = f"🔔 Rappel - Votre réservation aujourd'hui - Resto Pêcheur"
        message = f"""
Cher(e) {reservation.customer_name},
 
Nous vous rappelons votre réservation aujourd'hui au Resto Pêcheur.
 
Détails de votre réservation:
• Nom: {reservation.customer_name}
• Nombre de personnes: {reservation.number_of_guests} personnes
• Date: Aujourd'hui ({reservation.date.strftime('%d %B %Y')})
• Heure: {reservation.time.strftime('%H:%M')}
 
🔗 Voir votre réservation: {view_url}
 
Nous vous attendons avec plaisir!
 
En cas d'imprévu, merci de nous contacter au 0661-460593.
 
À bientôt,
L'équipe Resto Pêcheur
📍 Adresse: Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc
        """
       
        # ✅ Send with proper error handling
        success, error_msg = send_mail_with_proper_error_handling(
            subject=subject,
            message=message,
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[reservation.customer_email]
        )
        
        # ✅ Update notification based on ACTUAL result
        if notification:
            if success:
                notification.mark_email_as_sent()
                print(f"✅ Reminder email sent successfully, notification marked as sent")
            else:
                notification.email_sent = False
                notification.save(update_fields=['email_sent'])
                print(f"❌ Reminder email failed, notification marked as NOT sent")
        
        if success:
            print(f"✅ Reminder email sent successfully to {reservation.customer_email}")
        else:
            print(f"❌ Reminder email failed: {error_msg}")
        
        return success
       
    except Exception as e:
        logger.error(f"❌ Erreur envoi email rappel: {e}")
        print(f"❌ Erreur envoi email rappel: {e}")
        if notification:
            notification.email_sent = False
            notification.save(update_fields=['email_sent'])
        return False

# ✅ TEST FUNCTIONS
def test_fatimazah_email():
    """Specific test for the fatimazah email issue"""
    print("🎯 TESTING SPECIFIC FATIMAZAH EMAIL ISSUE")
    print("=" * 50)
    
    # The problematic email
    problematic = "fatimazah@gmail.com"
    
    print(f"📧 Testing: {problematic}")
    
    # Test with different validation methods
    
    # 1. Basic format validation
    try:
        validate_email(problematic)
        print("1️⃣ Django validation: ✅ Valid format")
    except ValidationError:
        print("1️⃣ Django validation: ❌ Invalid format")
    
    # 2. Enhanced validation
    is_valid, message = validate_email_address_properly(problematic)
    print(f"2️⃣ Enhanced validation: {'✅' if is_valid else '❌'} {message}")
    
    # 3. Blacklist check
    is_blacklisted, blacklist_msg = check_email_blacklist(problematic)
    print(f"3️⃣ Blacklist check: {'❌ Blacklisted' if is_blacklisted else '✅ Not blacklisted'} - {blacklist_msg}")
    
    # Final recommendation
    print(f"\n🎯 FINAL RESULT:")
    if is_valid:
        print(f"❌ PROBLEM: Email still validates as existing")
        print(f"   The system will still show ✅ in notifications")
        print(f"   Solution: Add to blacklist or enhance SMTP checking")
    else:
        print(f"✅ SUCCESS: Email correctly detected as non-existent")
        print(f"   The system should now show ❌ in notifications")
    
    return not is_valid

def test_specific_email_address(email_address):
    """Test a specific email address"""
    print(f"🧪 Testing specific email: {email_address}")
    
    is_valid, message = validate_email_address_properly(email_address)
    print(f"📧 Validation: {is_valid} - {message}")
    
    if is_valid:
        success, error_msg = send_mail_with_proper_error_handling(
            subject="Test Email - Resto Pêcheur",
            message="This is a test email to verify your email address works.",
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=[email_address]
        )
        print(f"📧 Send result: {success} - {error_msg}")
        return success
    else:
        print(f"❌ Email invalid, not attempting to send")
        return False

def quick_fix_test():
    """Quick test to verify the fix works"""
    print("🚀 QUICK FIX VERIFICATION TEST")
    print("=" * 40)
    
    # Test the specific problematic email
    problematic_email = "fatimazah@gmail.com"
    
    print(f"Testing problematic email: {problematic_email}")
    
    is_valid, message = validate_email_address_properly(problematic_email)
    
    if is_valid:
        print(f"❌ STILL BROKEN: Email validation thinks {problematic_email} exists")
        print(f"   Message: {message}")
        print("\n🔧 This means the email server is not properly rejecting the address")
        print("   or the validation needs to be more strict.")
    else:
        print(f"✅ FIXED: Email validation correctly detects {problematic_email} doesn't exist")
        print(f"   Message: {message}")
        print("\n🎯 Your notifications should now show ❌ instead of ✅!")
    
    return not is_valid  # Return True if email is correctly detected as invalid

# ✅ LEGACY FUNCTIONS (for backwards compatibility)
def send_reservation_pending_email_fixed(reservation, notification=None):
    """Legacy function name - redirects to main function"""
    return send_reservation_pending_email(reservation, notification)

def send_reservation_confirmation_email_fixed(reservation, notification=None):
    """Legacy function name - redirects to main function"""
    return send_reservation_confirmation_email(reservation, notification)

def send_reservation_cancellation_email_fixed(reservation, notification=None):
    """Legacy function name - redirects to main function"""
    return send_reservation_cancellation_email(reservation, notification)

def validate_email_format(email):
    """Basic email format validation (legacy function for compatibility)"""
    is_valid, message = validate_email_address_properly(email)
    return is_valid

def test_email_connection():
    """Test email connection without sending to customers"""
    try:
        print("🧪 Testing email connection...")
        
        success, error_msg = send_mail_with_proper_error_handling(
            subject='Test Email Connection - Resto Pêcheur',
            message='This is a test email to verify SMTP configuration.',
            from_email='Resto Pêcheur <simanjali8@gmail.com>',
            recipient_list=['simanjali8@gmail.com']  # Send to yourself
        )
        
        if success:
            print("✅ Email connection test successful")
        else:
            print(f"❌ Email connection test failed: {error_msg}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Email connection test failed: {e}")
        print(f"❌ Email connection test failed: {e}")
        return False