import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import menuData from '../Data/menu.json';
import './MenuPage.css';

function MenuPage() {
  const [activeCategory, setActiveCategory] = useState('entrees-froides');

  const categories = Object.keys(menuData.categories);

  return (
    <div className="menu-page">
      {/* Header */}
      <header className="menu-header">
        <div className="container">
          <Link to="/" className="back-button">← Retour</Link>
          <h1>Menu Digital</h1>
          <h2>Resto Pêcheur - Tiznit</h2>
        </div>
      </header>

      <div className="menu-container">
        <div className="container">
          {/* Navigation des catégories */}
          <nav className="menu-nav">
            <div className="menu-categories">
              {categories.map(categoryKey => (
                <button
                  key={categoryKey}
                  className={`category-btn ${activeCategory === categoryKey ? 'active' : ''}`}
                  onClick={() => setActiveCategory(categoryKey)}
                >
                  {menuData.categories[categoryKey].title}
                </button>
              ))}
            </div>
          </nav>

          {/* Contenu du menu */}
          <div className="menu-content">
            <div className="category-section">
              <h2 className="category-title">
                {menuData.categories[activeCategory].title}
              </h2>
              
              <div className="menu-items">
                {menuData.categories[activeCategory].items.map((item, index) => (
                  <div key={index} className="menu-item">
                    <div className="item-info">
                      <h3 className="item-name">{item.name}</h3>
                    </div>
                    <div className="item-price">
                      {item.price} DH
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Call to action */}
          <div className="menu-cta">
            <h3>Envie de commander ?</h3>
            <p>Réservez votre table pour déguster nos spécialités</p>
            <Link to="/reservation" className="cta-button">
              Réserver une table
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="menu-footer">
        <div className="container">
          <p>📞 +212 528 86 25 47 | 📍 M7RG+RJ3, Bd Mohamed Hafidi, Tiznit</p>
          <p>&copy; 2025 Resto Pêcheur - Tous les prix sont en Dirhams (DH)</p>
        </div>
      </footer>
    </div>
  );
}

export default MenuPage;