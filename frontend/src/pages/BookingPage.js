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
  const [availability, setAvailability] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedDate, setSelectedDate] = useState(null);
  const [showMenuSelector, setShowMenuSelector] = useState(false);

  // Récupérer les créneaux horaires
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/timeslots/')
      .then(response => response.json())
      .then(data => setTimeSlots(data))
      .catch(error => console.error('Erreur créneaux:', error));
  }, []);

  // Vérifier la disponibilité quand la date change
  useEffect(() => {
    if (formData.date) {
      const dateString = formData.date.toISOString().split('T')[0];
      fetch(`http://127.0.0.1:8000/api/availability/?date=${dateString}`)
        .then(response => response.json())
        .then(data => {
          if (data.is_closed) {
            setAvailability([]);
            setError('Le restaurant est fermé ce jour-là.');
          } else {
            setAvailability(data.available_slots);
            setError('');
          }
        })
        .catch(error => {
          console.error('Erreur disponibilité:', error);
          setError('Erreur lors de la vérification de la disponibilité.');
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Préparer les données avec la date au format string
      const reservationData = {
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        customer_phone: formData.customer_phone,
        date: formData.date.toISOString().split('T')[0],
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
        // Rediriger vers la page de confirmation avec les données
        navigate('/confirmation', { 
          state: { 
            reservation: reservation,
            message: 'Votre réservation a été créée avec succès !' 
          } 
        });
      } else {
        const errorData = await response.json();
        setError(errorData.message || 'Erreur lors de la réservation');
      }
    } catch (error) {
      setError('Erreur de connexion. Veuillez réessayer.');
      console.error('Erreur:', error);
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
                      {availability.length > 0 ? (
                        availability.map(slot => (
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
                              {!slot.is_available && ' (Complet)'}
                              {slot.is_available && ` (${slot.available_count} places)`}
                            </span>
                          </label>
                        ))
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