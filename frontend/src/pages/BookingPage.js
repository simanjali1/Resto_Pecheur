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
    date: null,
    time: '',
    number_of_guests: 2,
    special_requests: '',
    wants_preorder: false,
    selected_dishes: []
  });
  
  const [timeSlots, setTimeSlots] = useState([]);
  const [availability, setAvailability] = useState([]); // Initialize as empty array
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedDate, setSelectedDate] = useState(null);
  const [showMenuSelector, setShowMenuSelector] = useState(false);

  // FIXED: Date formatting function to avoid timezone issues
  const formatDateForAPI = (date) => {
    if (!date) return null;
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

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

  // FIXED: Vérifier la disponibilité quand la date change
  useEffect(() => {
    if (formData.date) {
      const dateString = formatDateForAPI(formData.date);
      console.log('🔍 DEBUG - Checking availability for date:', dateString);
      console.log('🔍 DEBUG - Selected date object:', formData.date);
      
      fetch(`http://127.0.0.1:8000/api/availability/?date=${dateString}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
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
  }, [formData.date]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDateChange = (date) => {
    console.log('🔍 DEBUG - Date selected from calendar:', date);
    console.log('🔍 DEBUG - Date will be formatted as:', formatDateForAPI(date));
    
    setSelectedDate(date);
    setFormData(prev => ({
      ...prev,
      date: date,
      time: '' // Reset time when date changes
    }));
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

  // FIXED: Handle submit with proper date formatting
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // FIXED: Préparer les données avec la date au format string sans timezone
      const formattedDate = formatDateForAPI(formData.date);
      
      console.log('🔍 DEBUG - Original date object:', formData.date);
      console.log('🔍 DEBUG - Formatted date for API:', formattedDate);
      console.log('🔍 DEBUG - Selected time:', formData.time);

      const reservationData = {
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        customer_phone: formData.customer_phone,
        date: formattedDate, // FIXED: Use proper date formatting
        time: formData.time,
        number_of_guests: formData.number_of_guests,
        special_requests: formData.wants_preorder 
          ? `${formData.special_requests}\n\nPré-commande:\n${formData.selected_dishes.map(d => `${d.name} x${d.quantity} (${d.price * d.quantity} DH)`).join('\n')}`
          : formData.special_requests
      };

      console.log('🔍 DEBUG - Complete reservation data being sent:', reservationData);

      const response = await fetch('http://127.0.0.1:8000/api/reservations/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(reservationData)
      });

      if (response.ok) {
        const reservation = await response.json();
        
        console.log('✅ SUCCESS - Reservation created:', reservation);
        
        // Make sure we have all the data needed for confirmation
        const confirmationData = {
          ...reservation,
          // Ensure we have the formatted data that ConfirmationPage expects
          customer_name: reservation.customer_name || formData.customer_name,
          customer_email: reservation.customer_email || formData.customer_email,
          customer_phone: reservation.customer_phone || formData.customer_phone,
          date: reservation.date || formattedDate, // Use the formatted date
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
        console.error('❌ ERROR - Reservation failed:', errorData);
        setError(errorData.message || errorData.error || 'Erreur lors de la réservation');
      }
    } catch (error) {
      console.error('❌ ERROR - Network or other error:', error);
      setError('Erreur de connexion. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  };

  // Date minimum = aujourd'hui
  const today = new Date();
  const maxDate = new Date();
  maxDate.setMonth(maxDate.getMonth() + 3); // 3 mois à l'avance

  // Fonction pour désactiver les dates passées
  const tileDisabled = ({ date, view }) => {
    if (view === 'month') {
      // Désactiver les dates passées
      return date < today.setHours(0, 0, 0, 0);
    }
    return false;
  };

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
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="customer_phone">Téléphone *</label>
                    <input
                      type="tel"
                      id="customer_phone"
                      name="customer_phone"
                      value={formData.customer_phone}
                      onChange={handleInputChange}
                      required
                      placeholder="+212 6XX XXX XXX"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="customer_email">Email</label>
                    <input
                      type="email"
                      id="customer_email"
                      name="customer_email"
                      value={formData.customer_email}
                      onChange={handleInputChange}
                      placeholder="votre@email.com"
                    />
                  </div>
                </div>
              </div>

              {/* Détails de la réservation */}
              <div className="form-section">
                <h3>Détails de votre réservation</h3>
                
                {/* Calendrier */}
                <div className="form-group">
                  <label>Choisissez une date *</label>
                  <div className="calendar-container">
                    <Calendar
                      onChange={handleDateChange}
                      value={selectedDate}
                      minDate={today}
                      maxDate={maxDate}
                      tileDisabled={tileDisabled}
                      locale="fr-FR"
                      className="booking-calendar"
                    />
                  </div>
                  {selectedDate && (
                    <p className="selected-date">
                      Date sélectionnée : {selectedDate.toLocaleDateString('fr-FR', { 
                        weekday: 'long', 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric' 
                      })}
                      <br />
                      <small style={{color: '#666'}}>
                        Envoyé à l'API comme : {formatDateForAPI(selectedDate)}
                      </small>
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
                  >
                    {[1,2,3,4,5,6,7,8,9,10].map(num => (
                      <option key={num} value={num}>
                        {num} personne{num > 1 ? 's' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Créneaux horaires */}
                {formData.date && (
                  <div className="form-group">
                    <label>Heure *</label>
                    <div className="time-slots">
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
                                onChange={handleInputChange}
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
                  />
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
                  disabled={loading || !formData.date || !formData.time}
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