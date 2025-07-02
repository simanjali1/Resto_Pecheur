import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';
import logo from '../assets/images/mainPicture/logo.png';

function HomePage() {
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('home');
  const [currentMediaIndex, setCurrentMediaIndex] = useState(0);
  const [isCarouselPlaying, setIsCarouselPlaying] = useState(true);

  // TEST with online vertical video first
  const mediaFiles = [
    { type: 'video', src: 'https://sample-videos.com/zip/10/mp4/480/mp4-sample_640x360_1mb.mp4', alt: 'Test video' }
    // { type: 'video', src: '/VIDEO1.mp4', alt: 'Restaurant video' }
  ];

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

  useEffect(() => {
    const handleScroll = () => {
      const sections = ['home', 'about'];
      const scrollPosition = window.scrollY + 200;

      for (let section of sections) {
        const element = document.getElementById(section);
        if (element) {
          const offsetTop = element.offsetTop;
          const offsetHeight = element.offsetHeight;
          
          if (scrollPosition >= offsetTop && scrollPosition < offsetTop + offsetHeight) {
            setActiveSection(section);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Simplified for testing
  useEffect(() => {
    console.log('🔍 Testing Vimeo embed');
  }, []);

  const handleNavClick = (section) => {
    setActiveSection(section);
    
    if (section === 'home' || section === 'about') {
      const element = document.getElementById(section);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  const goToNextMedia = () => {
    setCurrentMediaIndex((prevIndex) => (prevIndex + 1) % mediaFiles.length);
  };

  if (loading) {
    return <div className="loading">Chargement...</div>;
  }

  return (
    <div className="homepage">
      {/* Navigation Header */}
      <nav className="top-navigation">
        <div className="nav-container">
          <div className="nav-logo">
            <img src={logo} alt="Resto Pêcheur" />
          </div>
          
          <div className="nav-links">
            <a 
              href="#home" 
              className={`nav-link ${activeSection === 'home' ? 'active' : ''}`}
              onClick={(e) => {
                e.preventDefault();
                handleNavClick('home');
              }}
            >
              Accueil
            </a>
            <a 
              href="#about" 
              className={`nav-link ${activeSection === 'about' ? 'active' : ''}`}
              onClick={(e) => {
                e.preventDefault();
                handleNavClick('about');
              }}
            >
              À propos
            </a>
            <Link 
              to="/menu" 
              className={`nav-link ${activeSection === 'menu' ? 'active' : ''}`}
              onClick={() => handleNavClick('menu')}
            >
              Menu
            </Link>
            <Link 
              to="/reservation" 
              className={`nav-link nav-cta ${activeSection === 'reservation' ? 'active' : ''}`}
              onClick={() => handleNavClick('reservation')}
            >
              Réservation
            </Link>
          </div>
        </div>
      </nav>

      {/* Header */}
      <header id="home" className="hero-section">
        <div className="hero-background-wrapper">
          <div className="hero-background"></div>
        </div>
        <div className="hero-overlay">
          <div className="hero-content">
            <h1 className="restaurant-name">
              Resto Pêcheur
            </h1>
            
            <div className="main-hook">
              <h2 className="hook-text-fr">De l'océan à votre assiette</h2>
              <h3 className="hook-text-ar">من المحيط إلى طبقكم</h3>
            </div>
          </div>
        </div>
      </header>

      {/* Section Présentation - EXACTLY like your drawing */}
      <section id="about" className="about-section">
        <div className="container">
          <div className="about-content-new">
            
            {/* Left side - VIDEO */}
            <div className="about-left">
              <div className="video-container">
                <iframe 
                  width="100%" 
                  height="100%"
                  src="https://player.vimeo.com/video/1097934612?autoplay=1&muted=1&loop=1&autopause=0&background=1&controls=0&title=0&byline=0&portrait=0&dnt=1"
                  title="Resto Pêcheur - Restaurant Video"
                  frameBorder="0"
                  allow="autoplay; fullscreen; picture-in-picture"
                  allowFullScreen
                  style={{ 
                    borderRadius: '20px',
                    display: 'block',
                    width: '100%',
                    height: '100%'
                  }}
                />
              </div>
              <div style={{ textAlign: 'center', marginTop: '15px', color: '#666', fontSize: '14px' }}>
                Découvrez l'ambiance de notre restaurant
              </div>
            </div>

            {/* Right side - TEXT and INFO CARDS */}
            <div className="about-right">
              {/* Main text section */}
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

              {/* Info cards row under the text - NOW WITH BACKEND DATA */}
              <div className="info-cards-row">
                <div className="info-card-compact">
                  <h3>🕐 Horaires d'ouverture</h3>
                  <p>
                    <strong>Tous les jours</strong><br/>
                    {restaurant?.opening_time || "12h00"} - {restaurant?.closing_time || "23h00"}
                  </p>
                </div>
                
                <div className="info-card-compact">
                  <h3>📍 Adresse</h3>
                  <p>{restaurant?.address || 'M7RG+RJ3, Bd Mohamed Hafidi, Tiznit 85000'}</p>
                </div>
                
                <div className="info-card-compact">
                  <h3>📞 Contact</h3>
                  <p>
                    <strong>Téléphone:</strong> {restaurant?.phone || "0528 123 456"}<br/>
                    <strong>Email:</strong> {restaurant?.email || "contact@restopecheur.ma"}
                  </p>
                </div>
              </div>
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
              <p>Spécialités marocaines authentiques</p>
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