import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import './ConfirmationPage.css';

function ConfirmationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Récupérer les données de la réservation depuis la navigation
  const { reservation, message } = location.state || {};

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
    const options = { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    };
    return new Date(dateString).toLocaleDateString('fr-FR', options);
  };

  const formatTime = (timeString) => {
    return timeString.slice(0, 5); // Format HH:MM
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

  return (
    <div className="confirmation-page">
      <div className="container">
        <div className="confirmation-card">
          {/* Header de confirmation */}
          <div className="confirmation-header">
            <div className="success-icon">✅</div>
            <h1>Réservation confirmée !</h1>
            <p className="confirmation-message">
              {message || 'Votre demande de réservation a été enregistrée avec succès.'}
            </p>
          </div>

          {/* Détails de la réservation */}
          <div className="reservation-details">
            <h2>Détails de votre réservation</h2>
            
            <div className="details-grid">
              <div className="detail-item">
                <span className="detail-label">Numéro de réservation</span>
                <span className="detail-value">#{reservation.id}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Statut</span>
                <span className="detail-value">
                  {getStatusBadge(reservation.status)}
                </span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Nom</span>
                <span className="detail-value">{reservation.customer_name}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Téléphone</span>
                <span className="detail-value">{reservation.customer_phone}</span>
              </div>

              {reservation.customer_email && (
                <div className="detail-item">
                  <span className="detail-label">Email</span>
                  <span className="detail-value">{reservation.customer_email}</span>
                </div>
              )}

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
                  {reservation.number_of_guests} personne{reservation.number_of_guests > 1 ? 's' : ''}
                </span>
              </div>

              {reservation.special_requests && (
                <div className="detail-item full-width">
                  <span className="detail-label">Demandes spéciales</span>
                  <span className="detail-value">{reservation.special_requests}</span>
                </div>
              )}
            </div>
          </div>

          {/* Informations importantes */}
          <div className="important-info">
            <h3>📋 Informations importantes</h3>
            <ul>
              <li>
                <strong>Confirmation :</strong> Votre réservation est en attente de confirmation. 
                Nous vous contacterons dans les plus brefs délais.
              </li>
              <li>
                <strong>Arrivée :</strong> Merci de vous présenter 15 minutes avant l'heure de votre réservation.
              </li>
              <li>
                <strong>Annulation :</strong> Pour annuler ou modifier votre réservation, 
                contactez-nous par téléphone.
              </li>
              <li>
                <strong>Contact :</strong> +212 528 86 25 47
              </li>
            </ul>
          </div>

          {/* Informations du restaurant */}
          <div className="restaurant-info">
            <h3>📍 Resto Pêcheur</h3>
            <p>
              <strong>Adresse :</strong> M7RG+RJ3, Bd Mohamed Hafidi, Tiznit 85000<br/>
              <strong>Téléphone :</strong> +212 528 86 25 47<br/>
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