import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

function HomePage() {
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Récupérer les infos du restaurant depuis l'API Django
    fetch('http://127.0.0.1:8000/api/restaurant/')
      .then(response => response.json())
      .then(data => {
        setRestaurant(data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Erreur:', error);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading">Chargement...</div>;
  }

  return (
    <div className="homepage">
      {/* Header */}
      <header className="hero-section">
        <div className="hero-overlay">
          <div className="hero-content">
            <h1 className="restaurant-name">
              {restaurant?.name || 'Resto Pêcheur'}
            </h1>
            <p className="restaurant-tagline">
              Restaurant de poissons et fruits de mer frais
            </p>
            <p className="restaurant-location">
              Boulevard Mohamed Hafidi, Tiznit • Cuisine authentique
            </p>
            <div className="hero-buttons">
              <Link to="/reservation" className="cta-button">
                Réserver une table
              </Link>
              <Link to="/menu" className="cta-button secondary">
                Voir le menu
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Section Présentation */}
      <section className="about-section">
        <div className="container">
          <div className="about-content">
            <div className="about-text">
              <h2>Bienvenue au Resto Pêcheur</h2>
              <p>
                {restaurant?.description || 
                 "Découvrez notre restaurant familial situé au cœur de Tiznit. Nous vous proposons les meilleurs poissons et fruits de mer de la région, ainsi que des spécialités marocaines authentiques préparées avec des produits frais locaux."}
              </p>
              <p>
                Notre chef vous prépare des plats traditionnels dans une ambiance chaleureuse 
                au cœur de la ville historique de Tiznit.
              </p>
            </div>
            <div className="about-image">
              <div className="image-placeholder">
                <span>🐟 Photo du restaurant</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section Horaires et Contact */}
      <section className="info-section">
        <div className="container">
          <div className="info-grid">
            <div className="info-card">
              <h3>🕐 Horaires d'ouverture</h3>
              <p>
                <strong>Tous les jours</strong><br/>
                {restaurant?.opening_time} - {restaurant?.closing_time}
              </p>
            </div>
            
            <div className="info-card">
              <h3>📍 Adresse</h3>
              <p>{restaurant?.address || 'M7RG+RJ3, Bd Mohamed Hafidi, Tiznit 85000'}</p>
            </div>
            
            <div className="info-card">
              <h3>📞 Contact</h3>
              <p>
                <strong>Téléphone:</strong> {restaurant?.phone}<br/>
                <strong>Email:</strong> {restaurant?.email}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section Spécialités */}
      <section className="specialties-section">
        <div className="container">
          <h2>Nos Spécialités</h2>
          <div className="specialties-grid">
            <div className="specialty-card">
              <span className="specialty-icon">🐟</span>
              <h3>Poissons frais</h3>
              <p>Dorade, sole, loup de mer pêchés quotidiennement</p>
            </div>
            
            <div className="specialty-card">
              <span className="specialty-icon">🦐</span>
              <h3>Fruits de mer</h3>
              <p>Crevettes, langoustes, crabes de nos côtes</p>
            </div>
            
            <div className="specialty-card">
              <span className="specialty-icon">🥘</span>
              <h3>Tagines de poisson</h3>
              <p>Spécialités marocaines aux saveurs authentiques</p>
            </div>
            
            <div className="specialty-card">
              <span className="specialty-icon">🌊</span>
              <h3>Ambiance authentique</h3>
              <p>Restaurant au cœur de la ville historique de Tiznit</p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="cta-section">
        <div className="container">
          <h2>Prêt à nous rendre visite ?</h2>
          <p>Découvrez notre menu ou réservez votre table dès maintenant</p>
          <div className="cta-buttons">
            <Link to="/menu" className="cta-button secondary large">
              📋 Découvrir le menu
            </Link>
            <Link to="/reservation" className="cta-button large">
              Réserver maintenant
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <p>&copy; 2025 Resto Pêcheur - Tiznit. Tous droits réservés.</p>
        </div>
      </footer>
    </div>
  );
}

export default HomePage;