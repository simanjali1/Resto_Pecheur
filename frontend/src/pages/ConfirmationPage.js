import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import './ConfirmationPage.css';

function ConfirmationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Récupérer les données de la réservation depuis la navigation
  const { reservation } = location.state || {};

  // Si pas de données, rediriger vers l'accueil
  if (!reservation) {
    return (
      <div className="confirmation-page">
        <div className="container">
          <div className="confirmation-card">
            <div className="error-content">
              <h2>Aucune réservation trouvée</h2>
              <p>Il semble que vous ayez accédé à cette page directement.</p>
              <Link to="/" className="btn btn-primary">
                Retour à l'accueil
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Date non disponible';
    const options = { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    };
    try {
      return new Date(dateString).toLocaleDateString('fr-FR', options);
    } catch (error) {
      return dateString;
    }
  };

  const formatTime = (timeString) => {
    if (!timeString) return 'Heure non disponible';
    // Handle different time formats
    if (typeof timeString === 'string') {
      // If it's already in HH:MM format, return as is
      if (timeString.includes(':') && timeString.length >= 5) {
        return timeString.slice(0, 5); // Format HH:MM
      }
      // If it's just the time string, return it
      return timeString;
    }
    return 'Heure non disponible';
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'pending': { text: 'En attente', class: 'status-pending' },
      'confirmed': { text: 'Confirmée', class: 'status-confirmed' },
      'cancelled': { text: 'Annulée', class: 'status-cancelled' }
    };
    
    const config = statusConfig[status] || statusConfig['pending'];
    
    return (
      <span className={`status-badge ${config.class}`}>
        {config.text}
      </span>
    );
  };

  // Since users have no accounts, they only see this page once after booking (always pending)
  const headerContent = {
    icon: '⏳',
    title: 'Demande de réservation envoyée !',
    message: 'Votre demande a bien été reçue. Vous recevrez une réponse par email sous peu. Nous avons hâte de vous accueillir !',
    headerClass: 'confirmation-header pending'
  };

  // Debug: log the reservation data
  console.log('Reservation data in ConfirmationPage:', reservation);
  console.log('Phone number specifically:', reservation.customer_phone);
  console.log('All reservation keys:', Object.keys(reservation || {}));
  console.log('Full reservation object:', JSON.stringify(reservation, null, 2));

  return (
    <div className="confirmation-page">
      <div className="container">
        <div className="confirmation-card">
          {/* Header de confirmation */}
          <div className={headerContent.headerClass}>
            <div className="success-icon">{headerContent.icon}</div>
            <h1>{headerContent.title}</h1>
            <p className="confirmation-message">
              {headerContent.message}
            </p>
          </div>

          {/* Détails de la réservation */}
          <div className="reservation-details">
            <h2>Détails de votre réservation</h2>
            
            {/* First row - 4 items */}
            <div className="details-row">
              <div className="detail-item">
                <span className="detail-label">Statut</span>
                <span className="detail-value">
                  {getStatusBadge(reservation.status)}
                </span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Nom</span>
                <span className="detail-value">{reservation.customer_name || 'Non spécifié'}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Téléphone</span>
                <span className="detail-value">
                  {reservation.customer_phone || 'Non spécifié'}
                </span>
              </div>

              {reservation.customer_email && (
                <div className="detail-item">
                  <span className="detail-label">Email</span>
                  <span className="detail-value">{reservation.customer_email}</span>
                </div>
              )}
            </div>

            {/* Second row - 3 items centered */}
            <div className="details-row centered-three">
              <div className="detail-item highlight">
                <span className="detail-label">Date</span>
                <span className="detail-value">{formatDate(reservation.date)}</span>
              </div>

              <div className="detail-item highlight">
                <span className="detail-label">Heure</span>
                <span className="detail-value">{formatTime(reservation.time)}</span>
              </div>

              <div className="detail-item highlight">
                <span className="detail-label">Nombre de personnes</span>
                <span className="detail-value">
                  {reservation.number_of_guests || 1} personne{(reservation.number_of_guests || 1) > 1 ? 's' : ''}
                </span>
              </div>
            </div>

            {/* Special requests if any */}
            {reservation.special_requests && (
              <div className="details-row">
                <div className="detail-item special-requests">
                  <span className="detail-label">Demandes spéciales</span>
                  <span className="detail-value">{reservation.special_requests}</span>
                </div>
              </div>
            )}
          </div>

          {/* Informations importantes */}
          <div className="important-info">
            <h3>📋 Informations importantes</h3>
            <ul>
              <li>
                <strong>Confirmation :</strong> Votre réservation est en attente de confirmation. 
                Nous vous contacterons par téléphone et email dans les plus brefs délais.
              </li>
              <li>
                <strong>Notifications :</strong> Vous recevrez un email de confirmation dès que votre réservation sera validée par notre équipe.
              </li>
              <li>
                <strong>Arrivée :</strong> Merci de vous présenter 15 minutes avant l'heure de votre réservation.
              </li>
              <li>
                <strong>Annulation :</strong> Pour annuler ou modifier votre réservation, 
                contactez-nous par téléphone.
              </li>
              <li>
                <strong>Contact :</strong> +212 661 46 05 93
              </li>
            </ul>
          </div>

          {/* Informations du restaurant */}
          <div className="restaurant-info">
            <h3>📍 Resto Pêcheur</h3>
            <p>
              <strong>Adresse :</strong> Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc<br/>
              <strong>Téléphone :</strong> +212 661 46 05 93<br/>
              <strong>Email :</strong> contact@resto-pecheur.ma
            </p>
          </div>

          {/* Actions */}
          <div className="confirmation-actions">
            <button 
              onClick={() => window.print()} 
              className="btn btn-secondary"
            >
              📄 Imprimer
            </button>
            
            <button 
              onClick={() => navigate('/reservation')} 
              className="btn btn-outline"
            >
              Nouvelle réservation
            </button>
            
            <Link to="/" className="btn btn-primary">
              Retour à l'accueil
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationPage;