import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Calendar from 'react-calendar';
import MenuSelector from '../components/MenuSelector';
import 'react-calendar/dist/Calendar.css';
import './BookingPage.css';

function BookingPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    country_code: '+212', // Default to Morocco
    date: null,
    time: '',
    number_of_guests: 2,
    special_requests: '',
    wants_preorder: false,
    selected_dishes: []
  });
  
  const [timeSlots, setTimeSlots] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [specialDates, setSpecialDates] = useState([]); // ✅ NEW: Special dates state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedDate, setSelectedDate] = useState(null);
  const [showMenuSelector, setShowMenuSelector] = useState(false);
  const [emailVerificationStatus, setEmailVerificationStatus] = useState({
    isVerifying: false,
    isValid: null,
    message: ''
  });
  
  // New state for field-specific errors
  const [fieldErrors, setFieldErrors] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    country_code: '',
    date: '',
    time: '',
    number_of_guests: ''
  });

  // Countries with their phone number patterns
  const countries = [
    { code: '+212', name: '🇲🇦 Maroc', pattern: /^\d{9}$/, placeholder: 'XXX XXX XXX', example: '6XX XXX XXX' },
    { code: '+33', name: '🇫🇷 France', pattern: /^\d{9}$/, placeholder: 'X XX XX XX XX', example: '6 12 34 56 78' },
    { code: '+1', name: '🇺🇸 États-Unis', pattern: /^\d{10}$/, placeholder: 'XXX XXX XXXX', example: '555 123 4567' },
    { code: '+44', name: '🇬🇧 Royaume-Uni', pattern: /^\d{10}$/, placeholder: 'XXXX XXX XXX', example: '7700 123456' },
    { code: '+49', name: '🇩🇪 Allemagne', pattern: /^\d{10,11}$/, placeholder: 'XXX XXXXXXX', example: '176 12345678' },
    { code: '+34', name: '🇪🇸 Espagne', pattern: /^\d{9}$/, placeholder: 'XXX XXX XXX', example: '612 345 678' },
    { code: '+39', name: '🇮🇹 Italie', pattern: /^\d{9,10}$/, placeholder: 'XXX XXX XXXX', example: '333 1234567' },
    { code: '+31', name: '🇳🇱 Pays-Bas', pattern: /^\d{9}$/, placeholder: 'X XXXX XXXX', example: '6 1234 5678' },
    { code: '+32', name: '🇧🇪 Belgique', pattern: /^\d{8,9}$/, placeholder: 'XXX XX XX XX', example: '471 12 34 56' },
    { code: '+41', name: '🇨🇭 Suisse', pattern: /^\d{9}$/, placeholder: 'XX XXX XX XX', example: '78 123 45 67' },
    { code: '+351', name: '🇵🇹 Portugal', pattern: /^\d{9}$/, placeholder: 'XXX XXX XXX', example: '912 345 678' },
    { code: '+7', name: '🇷🇺 Russie', pattern: /^\d{10}$/, placeholder: 'XXX XXX XXXX', example: '912 345 6789' },
    { code: '+86', name: '🇨🇳 Chine', pattern: /^\d{11}$/, placeholder: 'XXX XXXX XXXX', example: '138 0013 8000' },
    { code: '+81', name: '🇯🇵 Japon', pattern: /^\d{10,11}$/, placeholder: 'XX XXXX XXXX', example: '90 1234 5678' },
    { code: '+91', name: '🇮🇳 Inde', pattern: /^\d{10}$/, placeholder: 'XXXXX XXXXX', example: '98765 43210' },
    { code: '+971', name: '🇦🇪 Émirats arabes unis', pattern: /^\d{8,9}$/, placeholder: 'XX XXX XXXX', example: '50 123 4567' },
    { code: '+966', name: '🇸🇦 Arabie saoudite', pattern: /^\d{8,9}$/, placeholder: 'XX XXX XXXX', example: '50 123 4567' },
    { code: '+213', name: '🇩🇿 Algérie', pattern: /^\d{9}$/, placeholder: 'XXX XXX XXX', example: '551 234 567' },
    { code: '+216', name: '🇹🇳 Tunisie', pattern: /^\d{8}$/, placeholder: 'XX XXX XXX', example: '20 123 456' },
    { code: '+20', name: '🇪🇬 Égypte', pattern: /^\d{9,10}$/, placeholder: 'XXX XXX XXXX', example: '100 123 4567' }
  ];

  // Validation functions
  const validateName = (name) => {
    if (!name.trim()) {
      return 'Le nom est requis';
    }
    if (name.trim().length < 2) {
      return 'Le nom doit contenir au moins 2 caractères';
    }
    // Check for numbers in name
    if (/\d/.test(name)) {
      return 'Le nom ne doit pas contenir de chiffres';
    }
    // Check for excessive special characters
    if (!/^[a-zA-ZÀ-ÿ\s\-'\.]+$/.test(name)) {
      return 'Le nom contient des caractères non valides';
    }
    // Check for reasonable length
    if (name.trim().length > 50) {
      return 'Le nom est trop long (maximum 50 caractères)';
    }
    return '';
  };

  const validatePhone = (phone, countryCode = formData.country_code) => {
    if (!phone.trim()) {
      return 'Le numéro de téléphone est requis';
    }
    
    // Remove all spaces, dashes, and parentheses for validation
    const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');
    
    // Check if it contains only numbers
    if (!/^\d+$/.test(cleanPhone)) {
      return 'Le numéro de téléphone ne doit contenir que des chiffres';
    }
    
    // Find the country configuration
    const country = countries.find(c => c.code === countryCode);
    if (!country) {
      return 'Code pays non supporté';
    }
    
    // Validate against country-specific pattern
    if (!country.pattern.test(cleanPhone)) {
      return `Format invalide pour ${country.name.split(' ')[1]}. Exemple: ${country.example}`;
    }
    
    return '';
  };

  const validateEmail = (email) => {
    if (!email.trim()) {
      return ''; // Email is optional
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return 'Format d\'email invalide';
    }
    
    if (email.length > 100) {
      return 'L\'email est trop long (maximum 100 caractères)';
    }
    
    return '';
  };

  // Advanced email verification functions
  const checkDisposableEmail = (email) => {
    const disposableDomains = [
      '10minutemail.com', 'tempmail.org', 'guerrillamail.com', 'mailinator.com',
      'throwaway.email', 'temp-mail.org', 'getairmail.com', 'yopmail.com',
      'maildrop.cc', 'sharklasers.com', 'grr.la', 'guerrillamailblock.com'
    ];
    
    const domain = email.split('@')[1]?.toLowerCase();
    return disposableDomains.includes(domain);
  };

  const checkEmailTypos = (email) => {
    const commonDomains = {
      'gmial.com': 'gmail.com',
      'gmai.com': 'gmail.com',
      'gmail.co': 'gmail.com',
      'hotmial.com': 'hotmail.com',
      'hotmai.com': 'hotmail.com',
      'yahooo.com': 'yahoo.com',
      'yaho.com': 'yahoo.com',
      'outloook.com': 'outlook.com',
      'outlok.com': 'outlook.com'
    };
    
    const domain = email.split('@')[1]?.toLowerCase();
    return commonDomains[domain] || null;
  };

  // Real-time email verification (client-side only)
  const verifyEmailRealTime = async (email) => {
    if (!email || !email.includes('@')) return;
    
    setEmailVerificationStatus({
      isVerifying: true,
      isValid: null,
      message: 'Vérification du format...'
    });

    try {
      // Check for disposable email
      if (checkDisposableEmail(email)) {
        setEmailVerificationStatus({
          isVerifying: false,
          isValid: false,
          message: 'Les adresses email temporaires ne sont pas autorisées'
        });
        return false;
      }

      // Check for common typos
      const suggestion = checkEmailTypos(email);
      if (suggestion) {
        setEmailVerificationStatus({
          isVerifying: false,
          isValid: false,
          message: `Vouliez-vous dire: ${email.split('@')[0]}@${suggestion} ?`
        });
        return false;
      }

      // Basic format validation
      const formatError = validateEmail(email);
      if (formatError) {
        setEmailVerificationStatus({
          isVerifying: false,
          isValid: false,
          message: formatError
        });
        return false;
      }

      // Email format is valid
      setEmailVerificationStatus({
        isVerifying: false,
        isValid: true,
        message: 'Format d\'email valide ✓'
      });
      return true;

    } catch (error) {
      console.error('Email verification error:', error);
      setEmailVerificationStatus({
        isVerifying: false,
        isValid: null,
        message: 'Format valide'
      });
      return true;
    }
  };

  // Clear field error when user starts typing
  const clearFieldError = (fieldName) => {
    if (fieldErrors[fieldName]) {
      setFieldErrors(prev => ({
        ...prev,
        [fieldName]: ''
      }));
    }
  };

  // Real-time validation as user types
  const validateField = (name, value) => {
    let error = '';
    
    switch (name) {
      case 'customer_name':
        error = validateName(value);
        break;
      case 'customer_phone':
        error = validatePhone(value, formData.country_code);
        break;
      case 'customer_email':
        error = validateEmail(value);
        break;
      case 'country_code':
        // Re-validate phone when country changes
        if (formData.customer_phone) {
          const phoneError = validatePhone(formData.customer_phone, value);
          setFieldErrors(prev => ({
            ...prev,
            customer_phone: phoneError
          }));
        }
        break;
      default:
        break;
    }
    
    setFieldErrors(prev => ({
      ...prev,
      [name]: error
    }));
    
    return error === '';
  };

  // Validate all fields before submission
  const validateAllFields = () => {
    const errors = {
      customer_name: validateName(formData.customer_name),
      customer_phone: validatePhone(formData.customer_phone, formData.country_code),
      customer_email: validateEmail(formData.customer_email),
      country_code: !formData.country_code ? 'Veuillez sélectionner un pays' : '',
      date: !formData.date ? 'Veuillez sélectionner une date' : '',
      time: !formData.time ? 'Veuillez sélectionner un créneau horaire' : '',
      number_of_guests: formData.number_of_guests < 1 ? 'Le nombre de personnes doit être au moins 1' : ''
    };
    
    setFieldErrors(errors);
    
    // Return true if no errors
    return Object.values(errors).every(error => error === '');
  };

  // Date formatting function to avoid timezone issues
  const formatDateForAPI = (date) => {
    if (!date) return null;
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // ✅ NEW: Helper function to check if a date is a special closed date
  const isSpecialClosedDate = (date) => {
    if (!date || !specialDates.length) return false;
    
    const dateString = formatDateForAPI(date);
    const specialDate = specialDates.find(sd => sd.date === dateString);
    
    return specialDate && !specialDate.is_open;
  };

  // ✅ UPDATED: Enhanced tileDisabled function
  const tileDisabled = ({ date, view }) => {
    if (view === 'month') {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      // Disable past dates
      if (date < today) {
        return true;
      }
      
      // Disable special closed dates
      if (isSpecialClosedDate(date)) {
        return true;
      }
    }
    return false;
  };

  // ✅ NEW: Fetch special dates on component mount
  useEffect(() => {
    const fetchSpecialDates = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/special-dates/');
        if (response.ok) {
          const data = await response.json();
          setSpecialDates(data.special_dates || []);
          console.log('✅ Special dates loaded:', data.special_dates);
        } else {
          console.warn('⚠️ Failed to fetch special dates, continuing without them');
          setSpecialDates([]);
        }
      } catch (error) {
        console.error('❌ Error fetching special dates:', error);
        setSpecialDates([]); // Continue without special dates
      }
    };

    fetchSpecialDates();
  }, []);

  // Récupérer les créneaux horaires
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/timeslots/')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setTimeSlots(data);
      })
      .catch(error => {
        console.error('Erreur créneaux:', error);
        // Mock data for development
        setTimeSlots([
          { id: 1, time: '12:00', type: 'lunch' },
          { id: 2, time: '12:30', type: 'lunch' },
          { id: 3, time: '13:00', type: 'lunch' },
          { id: 4, time: '19:00', type: 'dinner' },
          { id: 5, time: '19:30', type: 'dinner' },
          { id: 6, time: '20:00', type: 'dinner' },
          { id: 7, time: '20:30', type: 'dinner' }
        ]);
      });
  }, []);

  // ✅ ENHANCED: Availability check with special dates handling
  useEffect(() => {
    if (formData.date) {
      const dateString = formatDateForAPI(formData.date);
      
      // ✅ Check if this is a special closed date first
      if (isSpecialClosedDate(formData.date)) {
        setAvailability([]);
        setError('Restaurant fermé ce jour-là');
        return;
      }
      
      fetch(`http://127.0.0.1:8000/api/availability/?date=${dateString}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          // ✅ Handle special date response from API
          if (data.is_special_date && !data.availability.length) {
            setAvailability([]);
            setError(data.message || 'Restaurant fermé ce jour-là');
            return;
          }
          
          // Handle the actual API response format
          if (data.availability && Array.isArray(data.availability)) {
            const selectedDate = formData.date;
            const today = new Date();
            const isToday = selectedDate.toDateString() === today.toDateString();
            const currentHour = today.getHours();
            const currentMinute = today.getMinutes();
            
            // Transform the API data to match what the component expects
            const transformedSlots = data.availability.map(slot => {
              let isAvailable = slot.is_available;
              
              // If it's today, check if the time has already passed
              if (isToday) {
                const [slotHour, slotMinute] = slot.time.split(':').map(Number);
                const slotTimeInMinutes = slotHour * 60 + slotMinute;
                const currentTimeInMinutes = currentHour * 60 + currentMinute;
                
                // Add 30 minutes buffer - can't book within 30 minutes
                if (slotTimeInMinutes <= currentTimeInMinutes + 30) {
                  isAvailable = false;
                }
              }
              
              return {
                id: slot.time_id,
                time: slot.time,
                is_available: isAvailable,
                available_count: isAvailable ? slot.available_spots : 0
              };
            });
            
            setAvailability(transformedSlots);
            setError('');
            
            // ✅ Show special date info if it's a special open date
            if (data.is_special_date && data.reason) {
              console.log(`ℹ️ Special date: ${data.reason}`);
            }
          } else {
            setAvailability([]);
            setError('Aucun créneau disponible pour cette date.');
          }
        })
        .catch(error => {
          console.error('Erreur disponibilité:', error);
          // Mock availability data for development
          setAvailability([
            { id: 1, time: '12:00', is_available: true, available_count: 5 },
            { id: 2, time: '12:30', is_available: true, available_count: 3 },
            { id: 3, time: '13:00', is_available: false, available_count: 0 },
            { id: 4, time: '19:00', is_available: true, available_count: 8 },
            { id: 5, time: '19:30', is_available: true, available_count: 6 },
            { id: 6, time: '20:00', is_available: true, available_count: 4 },
            { id: 7, time: '20:30', is_available: true, available_count: 2 }
          ]);
          setError('');
        });
    }
  }, [formData.date, specialDates]); // ✅ Added specialDates dependency

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    // Clear the general error when user starts typing
    if (error) {
      setError('');
    }
    
    // Clear field-specific error
    clearFieldError(name);
    
    // For name field, prevent numbers from being typed
    if (name === 'customer_name') {
      // Remove any numbers that might have been pasted
      const cleanValue = value.replace(/[0-9]/g, '');
      setFormData(prev => ({
        ...prev,
        [name]: cleanValue
      }));
      
      // Validate on blur or after a short delay
      setTimeout(() => validateField(name, cleanValue), 500);
    } else if (name === 'customer_phone') {
      // Allow only numbers, spaces, dashes, parentheses for phone
      const cleanValue = value.replace(/[^0-9\s\-\(\)]/g, '');
      setFormData(prev => ({
        ...prev,
        [name]: cleanValue
      }));
      
      // Validate phone after user stops typing
      setTimeout(() => validateField(name, cleanValue), 500);
    } else if (name === 'country_code') {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
      
      // Re-validate phone when country changes
      setTimeout(() => validateField(name, value), 100);
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
      
      // Validate email if it's the email field
      if (name === 'customer_email') {
        setTimeout(() => {
          validateField(name, value);
          if (value && validateEmail(value) === '') {
            verifyEmailRealTime(value);
          } else {
            setEmailVerificationStatus({
              isVerifying: false,
              isValid: null,
              message: ''
            });
          }
        }, 1000); // Longer delay for email verification
      }
    }
  };

  const handleDateChange = (date) => {
    // Clear date error
    clearFieldError('date');
    
    setSelectedDate(date);
    setFormData(prev => ({
      ...prev,
      date: date,
      time: '' // Reset time when date changes
    }));
    
    // Clear time error since time was reset
    clearFieldError('time');
  };

  const handlePreorderChange = (checked) => {
    setFormData(prev => ({
      ...prev,
      wants_preorder: checked,
      selected_dishes: checked ? prev.selected_dishes : []
    }));
    
    if (checked) {
      setShowMenuSelector(true);
    }
  };

  const handleMenuUpdate = (newSelectedDishes) => {
    setFormData(prev => ({
      ...prev,
      selected_dishes: newSelectedDishes
    }));
  };

  const handleMenuClose = () => {
    setShowMenuSelector(false);
  };

  const openMenuSelector = () => {
    setShowMenuSelector(true);
  };

  // Handle submit with proper date formatting and validation
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate all fields before submission
    if (!validateAllFields()) {
      setError('Veuillez corriger les erreurs dans le formulaire');
      // Scroll to first error
      const firstErrorField = Object.keys(fieldErrors).find(key => fieldErrors[key]);
      if (firstErrorField) {
        const errorElement = document.getElementById(firstErrorField) || document.querySelector(`[name="${firstErrorField}"]`);
        if (errorElement) {
          errorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
          errorElement.focus();
        }
      }
      return;
    }
    
    // ✅ Additional check: Make sure selected date is not a special closed date
    if (isSpecialClosedDate(formData.date)) {
      setError('Impossible de réserver : le restaurant est fermé ce jour-là');
      return;
    }
    
    setLoading(true);
    setError('');

    try {
      // Préparer les données avec la date au format string sans timezone
      const formattedDate = formatDateForAPI(formData.date);

      const reservationData = {
        customer_name: formData.customer_name.trim(),
        customer_email: formData.customer_email.trim(),
        customer_phone: `${formData.country_code}${formData.customer_phone.replace(/[\s\-\(\)]/g, '')}`, // Full international number
        date: formattedDate,
        time: formData.time,
        number_of_guests: formData.number_of_guests,
        special_requests: formData.wants_preorder 
          ? `${formData.special_requests}\n\nPré-commande:\n${formData.selected_dishes.map(d => `${d.name} x${d.quantity} (${d.price * d.quantity} DH)`).join('\n')}`
          : formData.special_requests
      };

      const response = await fetch('http://127.0.0.1:8000/api/reservations/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(reservationData)
      });

      if (response.ok) {
        const reservation = await response.json();
        
        // Make sure we have all the data needed for confirmation
        const confirmationData = {
          ...reservation,
          // Ensure we have the formatted data that ConfirmationPage expects
          customer_name: reservation.customer_name || formData.customer_name,
          customer_email: reservation.customer_email || formData.customer_email,
          customer_phone: reservation.customer_phone || formData.customer_phone,
          date: reservation.date || formattedDate,
          time: reservation.time || formData.time,
          number_of_guests: reservation.number_of_guests || formData.number_of_guests,
          special_requests: reservation.special_requests || formData.special_requests
        };
        
        // Rediriger vers la page de confirmation avec les données
        navigate('/confirmation', { 
          state: { 
            reservation: confirmationData,
            message: 'Votre réservation a été créée avec succès !' 
          } 
        });
      } else {
        const errorData = await response.json();
        
        // ✅ Handle special date error from backend
        if (errorData.error === 'Restaurant fermé ce jour-là') {
          setError('Impossible de réserver : le restaurant est fermé ce jour-là');
          return;
        }
        
        // Handle specific API errors
        if (errorData.field_errors) {
          setFieldErrors(prev => ({
            ...prev,
            ...errorData.field_errors
          }));
          setError('Veuillez corriger les erreurs dans le formulaire');
        } else {
          setError(errorData.message || errorData.error || 'Erreur lors de la réservation');
        }
      }
    } catch (error) {
      setError('Erreur de connexion. Veuillez vérifier votre connexion internet et réessayer.');
    } finally {
      setLoading(false);
    }
  };

  // Date minimum = aujourd'hui
  const today = new Date();
  const maxDate = new Date();
  maxDate.setMonth(maxDate.getMonth() + 3); // 3 mois à l'avance

  return (
    <div className="booking-page">
      <header className="booking-header">
        <div className="container">
          <h1>Réserver une table</h1>
          <p>Resto Pêcheur - Tiznit</p>
        </div>
      </header>

      <div className="booking-container">
        <div className="container">
          <div className="booking-form-wrapper">
            <form onSubmit={handleSubmit} className="booking-form">
              <h2>Informations de réservation</h2>
              
              {error && <div className="error-message">{error}</div>}

              {/* Informations personnelles */}
              <div className="form-section">
                <h3>Vos informations</h3>
                
                <div className="form-group">
                  <label htmlFor="customer_name">Nom complet *</label>
                  <input
                    type="text"
                    id="customer_name"
                    name="customer_name"
                    value={formData.customer_name}
                    onChange={handleInputChange}
                    required
                    placeholder="Votre nom et prénom"
                    className={fieldErrors.customer_name ? 'error' : ''}
                  />
                  {fieldErrors.customer_name && (
                    <div className="field-error">{fieldErrors.customer_name}</div>
                  )}
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="country_code">Pays *</label>
                    <select
                      id="country_code"
                      name="country_code"
                      value={formData.country_code}
                      onChange={handleInputChange}
                      required
                      className={fieldErrors.country_code ? 'error' : ''}
                    >
                      {countries.map(country => (
                        <option key={country.code} value={country.code}>
                          {country.name}
                        </option>
                      ))}
                    </select>
                    {fieldErrors.country_code && (
                      <div className="field-error">{fieldErrors.country_code}</div>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="customer_phone">Téléphone *</label>
                    <div className="phone-input-container">
                      <span className="country-code-display">{formData.country_code}</span>
                      <input
                        type="tel"
                        id="customer_phone"
                        name="customer_phone"
                        value={formData.customer_phone}
                        onChange={handleInputChange}
                        required
                        placeholder={countries.find(c => c.code === formData.country_code)?.placeholder}
                        className={fieldErrors.customer_phone ? 'error' : ''}
                      />
                    </div>
                    {fieldErrors.customer_phone && (
                      <div className="field-error">{fieldErrors.customer_phone}</div>
                    )}
                    <small className="phone-example">
                      Exemple: {countries.find(c => c.code === formData.country_code)?.example}
                    </small>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="customer_email">Email</label>
                  <div className="email-input-container">
                    <input
                      type="email"
                      id="customer_email"
                      name="customer_email"
                      value={formData.customer_email}
                      onChange={handleInputChange}
                      placeholder="votre@email.com"
                      className={fieldErrors.customer_email ? 'error' : ''}
                    />
                    {emailVerificationStatus.isVerifying && (
                      <div className="email-verification-spinner">
                        <div className="spinner"></div>
                      </div>
                    )}
                    {!emailVerificationStatus.isVerifying && emailVerificationStatus.isValid === true && (
                      <div className="email-verification-success">✓</div>
                    )}
                    {!emailVerificationStatus.isVerifying && emailVerificationStatus.isValid === false && (
                      <div className="email-verification-error">✗</div>
                    )}
                    {!emailVerificationStatus.isVerifying && emailVerificationStatus.isValid === null && formData.customer_email && (
                      <div className="email-verification-neutral">?</div>
                    )}
                  </div>
                  {fieldErrors.customer_email && (
                    <div className="field-error">{fieldErrors.customer_email}</div>
                  )}
                  {emailVerificationStatus.message && (
                    <div className={`email-verification-message ${
                      emailVerificationStatus.isValid === true ? 'success' : 
                      emailVerificationStatus.isValid === false ? 'warning' : 'neutral'
                    }`}>
                      {emailVerificationStatus.message}
                    </div>
                  )}
                </div>
              </div>

              {/* Détails de la réservation */}
              <div className="form-section">
                <h3>Détails de votre réservation</h3>
                
                {/* Calendrier */}
                <div className="form-group">
                  <label>Choisissez une date *</label>
                  {specialDates.length > 0 && (
                    <div className="special-dates-info">
                      <small>ℹ️ Les dates grisées correspondent aux jours de fermeture</small>
                    </div>
                  )}
                  <div className={`calendar-container ${fieldErrors.date ? 'error' : ''}`}>
                    <Calendar
                      onChange={handleDateChange}
                      value={selectedDate}
                      minDate={today}
                      maxDate={maxDate}
                      tileDisabled={tileDisabled}
                      locale="fr-FR"
                      className="booking-calendar"
                      tileClassName={({ date, view }) => {
                        if (view === 'month' && isSpecialClosedDate(date)) {
                          return 'special-closed-date';
                        }
                        return null;
                      }}
                    />
                  </div>
                  {fieldErrors.date && (
                    <div className="field-error">{fieldErrors.date}</div>
                  )}
                  {selectedDate && (
                    <p className="selected-date">
                      Date sélectionnée : {selectedDate.toLocaleDateString('fr-FR', { 
                        weekday: 'long', 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric' 
                      })}
                      {isSpecialClosedDate(selectedDate) && (
                        <span className="closed-date-warning"> ⚠️ (Restaurant fermé)</span>
                      )}
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="number_of_guests">Nombre de personnes *</label>
                  <select
                    id="number_of_guests"
                    name="number_of_guests"
                    value={formData.number_of_guests}
                    onChange={handleInputChange}
                    required
                    className={fieldErrors.number_of_guests ? 'error' : ''}
                  >
                    {[1,2,3,4,5,6,7,8,9,10].map(num => (
                      <option key={num} value={num}>
                        {num} personne{num > 1 ? 's' : ''}
                      </option>
                    ))}
                  </select>
                  {fieldErrors.number_of_guests && (
                    <div className="field-error">{fieldErrors.number_of_guests}</div>
                  )}
                </div>

                {/* Créneaux horaires */}
                {formData.date && (
                  <div className="form-group">
                    <label>Heure *</label>
                    {isSpecialClosedDate(formData.date) ? (
                      <div className="closed-date-message">
                        <p>🚫 Restaurant fermé ce jour-là</p>
                        <small>Veuillez sélectionner une autre date</small>
                      </div>
                    ) : (
                      <div className={`time-slots ${fieldErrors.time ? 'error' : ''}`}>
                        {availability && availability.length > 0 ? (
                          availability.map(slot => {
                            const isToday = formData.date && formData.date.toDateString() === new Date().toDateString();
                            const isPastTime = isToday && (() => {
                              const [slotHour, slotMinute] = slot.time.split(':').map(Number);
                              const now = new Date();
                              const slotTimeInMinutes = slotHour * 60 + slotMinute;
                              const currentTimeInMinutes = now.getHours() * 60 + now.getMinutes();
                              return slotTimeInMinutes <= currentTimeInMinutes + 30;
                            })();
                            
                            return (
                              <label key={slot.id} className="time-slot">
                                <input
                                  type="radio"
                                  name="time"
                                  value={slot.time}
                                  onChange={(e) => {
                                    handleInputChange(e);
                                    clearFieldError('time');
                                  }}
                                  disabled={!slot.is_available}
                                  required
                                />
                                <span className={!slot.is_available ? 'unavailable' : ''}>
                                  {slot.time}
                                  {!slot.is_available && isPastTime && ' (Passé)'}
                                  {!slot.is_available && !isPastTime && ' (Complet)'}
                                  {slot.is_available && ` (${slot.available_count} places)`}
                                </span>
                              </label>
                            );
                          })
                        ) : (
                          <p className="no-slots">
                            {error || 'Aucun créneau disponible pour cette date.'}
                          </p>
                        )}
                      </div>
                    )}
                    {fieldErrors.time && (
                      <div className="field-error">{fieldErrors.time}</div>
                    )}
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="special_requests">Demandes spéciales</label>
                  <textarea
                    id="special_requests"
                    name="special_requests"
                    value={formData.special_requests}
                    onChange={handleInputChange}
                    rows="3"
                    placeholder="Allergies, occasion spéciale, préférences de table..."
                    maxLength="500"
                  />
                  <small className="character-count">
                    {formData.special_requests.length}/500 caractères
                  </small>
                </div>

                {/* Pré-commande optionnelle */}
                <div className="form-group">
                  <div className="preorder-section">
                    <label className="preorder-checkbox">
                      <input
                        type="checkbox"
                        checked={formData.wants_preorder}
                        onChange={(e) => handlePreorderChange(e.target.checked)}
                      />
                      <span className="checkmark"></span>
                      <span className="preorder-text">
                        <strong>Je veux pré-commander mes plats</strong>
                        <small>Gagnez du temps ! Vos plats seront prêts à votre arrivée</small>
                      </span>
                    </label>
                  </div>

                  {formData.wants_preorder && (
                    <div className="preorder-summary">
                      <div className="preorder-actions">
                        <button 
                          type="button"
                          className="select-dishes-btn"
                          onClick={openMenuSelector}
                        >
                          📋 Sélectionner des plats
                        </button>
                      </div>

                      {formData.selected_dishes.length > 0 && (
                        <div className="selected-dishes-summary">
                          <h5>Plats sélectionnés :</h5>
                          <div className="dishes-list">
                            {formData.selected_dishes.map(dish => (
                              <div key={dish.id} className="selected-dish">
                                <span className="dish-details">
                                  {dish.name} x{dish.quantity}
                                </span>
                                <span className="dish-total">
                                  {dish.price * dish.quantity} DH
                                </span>
                              </div>
                            ))}
                          </div>
                          <div className="total-summary">
                            <strong>
                              Total estimé : {formData.selected_dishes.reduce((total, dish) => total + (dish.price * dish.quantity), 0)} DH
                            </strong>
                          </div>
                          <button 
                            type="button"
                            className="modify-dishes-btn"
                            onClick={openMenuSelector}
                          >
                            Modifier la sélection
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={() => navigate('/')}
                  className="btn btn-secondary"
                >
                  Retour
                </button>
                <button 
                  type="submit" 
                  disabled={loading || !formData.date || !formData.time || isSpecialClosedDate(formData.date)}
                  className="btn btn-primary"
                >
                  {loading ? 'Réservation en cours...' : 'Confirmer la réservation'}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* MenuSelector Modal */}
        {showMenuSelector && (
          <MenuSelector
            selectedDishes={formData.selected_dishes}
            onDishUpdate={handleMenuUpdate}
            onClose={handleMenuClose}
          />
        )}
      </div>
    </div>
  );
}

export default BookingPage;