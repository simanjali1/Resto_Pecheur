import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './MenuPage.css';

function MenuPage() {
  const [activeCategory, setActiveCategory] = useState('entrees-froides');

  const menuData = {
    'entrees-froides': {
      title: 'Entrées Froides',
      items: [
        { name: 'Salade Mexicaine', price: 17 },
        { name: 'Salade Marocaine', price: 17 },
        { name: 'Salade Niçoise', price: 22 },
        { name: 'Salade de thon', price: 20 },
        { name: 'Salade Tropicale', price: 25 },
        { name: 'Salade Pêcheur', price: 30 },
        { name: 'Salade Crevette avocat', price: 30 },
        { name: 'Salade cocktail', price: 30 },
        { name: 'Salade tomate mozzarella', price: 30 },
        { name: 'Salade de Chef', price: 40 }
      ]
    },
    'entrees-chaudes': {
      title: 'Entrées Chaudes',
      items: [
        { name: 'Soupe de poisson', price: 20 },
        { name: 'Fruits de mer pilpil', price: 35 },
        { name: 'Crevette pilpil', price: 30 },
        { name: 'Fruits de mer au provençal', price: 40 },
        { name: 'Gratin de fruits de mer', price: 40 }
      ]
    },
    'pates': {
      title: 'Les Pâtes',
      items: [
        { name: 'Spaghetti / Tagliatelle Bolognaise', price: 40 },
        { name: 'Spaghetti / Tagliatelle Napolitaine', price: 35 },
        { name: 'Spaghetti / Tagliatelle Pistou', price: 35 },
        { name: 'Spaghetti / Tagliatelle Carbonara', price: 40 },
        { name: 'Spaghetti / Tagliatelle Pêcheur', price: 45 }
      ]
    },
    'lasagnes': {
      title: 'Lasagnes',
      items: [
        { name: 'Lasagnes fruits de mer', price: 40 },
        { name: 'Lasagnes bolognaise', price: 40 }
      ]
    },
    'omelettes': {
      title: 'Omelettes',
      items: [
        { name: 'Omelette Nature (sandwich)', price: 20 },
        { name: 'Omelette aux champignons (sandwich)', price: 22 },
        { name: 'Omelette au fromage (sandwich)', price: 22 },
        { name: 'Omelette au crevette (sandwich)', price: 25 }
      ]
    },
    'sandwiches': {
      title: 'Sandwiches',
      items: [
        { name: 'Sandwich Thon', price: 18 },
        { name: 'Sandwich Fromage', price: 18 },
        { name: 'Sandwich Dinde', price: 20 },
        { name: 'Sandwich Viande hachée', price: 20 },
        { name: 'Sandwich merguez', price: 20 },
        { name: 'Sandwich spécialité maison', price: 26 },
        { name: 'Sandwich Calamar', price: 27 },
        { name: 'Sandwich Crevette', price: 27 },
        { name: 'Sandwich Mixte (dinde+merguez)', price: 25 },
        { name: 'Sandwich fruits de mer', price: 30 }
      ]
    },
    'paninis': {
      title: 'Paninis',
      items: [
        { name: 'Panini Thon', price: 20 },
        { name: 'Panini au Fromage', price: 22 },
        { name: 'Panini Viande hachée', price: 22 },
        { name: 'Panini merguez', price: 22 },
        { name: 'Panini Dinde', price: 22 },
        { name: 'Panini Crevette', price: 30 },
        { name: 'Panini Calamar', price: 30 },
        { name: 'Panini Mixte (dinde+merguez)', price: 30 },
        { name: 'Panini Fruits de mer', price: 30 }
      ]
    },
    'burgers': {
      title: 'Burgers',
      items: [
        { name: 'Hamburger', price: 22 },
        { name: 'Chicken Burger', price: 22 },
        { name: 'Cheese Burger', price: 24 },
        { name: 'Eggs Burger', price: 24 },
        { name: 'Double Chicken', price: 30 },
        { name: 'Double Burger', price: 30 },
        { name: 'Double Cheese', price: 33 }
      ]
    },
    'poulet': {
      title: 'Poulet grillé au four',
      items: [
        { name: 'Poulet Grillé 1/4', price: 27 },
        { name: 'Poulet Grillé 1/2', price: 55 },
        { name: 'Poulet Entier', price: 100 }
      ]
    },
    'plats': {
      title: 'Les Plats',
      items: [
        { name: 'Brochette dinde', price: 30 },
        { name: 'Brochette Viande hachée', price: 30 },
        { name: 'Brochette de bœuf garnie', price: 35 },
        { name: 'Brochette Mixte grillé', price: 40 },
        { name: 'Émincé de dinde à la crème', price: 40 },
        { name: 'Escalope de dinde', price: 35 },
        { name: 'Émincé de bœuf au champignon', price: 50 },
        { name: 'Entre côte au choix', price: 60 }
      ]
    },
    'poisson-friture': {
      title: 'Spécialités Poisson Friture',
      items: [
        { name: 'Plat à la sauce', price: 25 },
        { name: 'Friture de poisson 1 pax', price: 45 },
        { name: 'Friture extra maison 1 pax', price: 70 },
        { name: 'Friture de poisson 2 pax', price: 80 },
        { name: 'Friture de crevettes décortiquées', price: 50 },
        { name: 'Friture de calamar', price: 80 },
        { name: 'Friture de poisson Resto Pêcheur', price: 100 },
        { name: 'Friture Royale', price: 130 }
      ]
    },
    'plancha': {
      title: 'Plancha',
      items: [
        { name: 'Pageot grillé garnie', price: 50 },
        { name: 'Filet de lotte à la plancha', price: 50 },
        { name: 'Brochette d\'ambrine', price: 50 },
        { name: 'Bochette de lotte marinée', price: 50 },
        { name: 'Bochette de lotte', price: 50 },
        { name: 'Sole grillé garnie', price: 50 },
        { name: 'Mixte grillé', price: 75 },
        { name: 'Calamar grillé', price: 80 },
        { name: 'Plancha Royale', price: 130 }
      ]
    },
    'plat-creme': {
      title: 'Plat à la crème',
      items: [
        { name: 'Filet de poisson aux champignons', price: 45 },
        { name: 'Filet de merlan', price: 45 },
        { name: 'Filet de poisson aux fruits de mer', price: 55 },
        { name: 'Filet de saint pierre à la sauce blanche', price: 70 }
      ]
    },
    'tajines': {
      title: 'Tajine de poisson',
      items: [
        { name: 'Tajine des moules (bourrouogue)', price: 25 },
        { name: 'Tajine kefta', price: 30 },
        { name: 'Tajine poulet au citron 1/4', price: 30 },
        { name: 'Tajine de lotte (1 pax)', price: 50 },
        { name: 'Tajine d\'ambrine (1 pax)', price: 50 },
        { name: 'Tajine de poulpe (1 pax)', price: 50 },
        { name: 'Tajine d\'ambrine (2pax)', price: 90 },
        { name: 'Tajine de fruits de mer', price: 50 },
        { name: 'Tajine kefta', price: 30 }
      ]
    },
    'paella': {
      title: 'Paëlla',
      items: [
        { name: 'Paëlla valencienne 1 pax', price: 45 },
        { name: 'Paëlla valencienne 2 pax', price: 100 },
        { name: 'Paëlla Royale', price: 130 }
      ]
    },
    'desserts': {
      title: 'Desserts',
      items: [
        { name: 'Crème caramel', price: 20 },
        { name: 'Salade fruits', price: 20 },
        { name: 'Orange à la cannelle', price: 15 },
        { name: 'Banana split', price: 25 },
        { name: 'Coupe de glace', price: 25 },
        { name: 'Mega glacé', price: 20 }
      ]
    }
  };

  const categories = Object.keys(menuData);

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
                  {menuData[categoryKey].title}
                </button>
              ))}
            </div>
          </nav>

          {/* Contenu du menu */}
          <div className="menu-content">
            <div className="category-section">
              <h2 className="category-title">
                {menuData[activeCategory].title}
              </h2>
              
              <div className="menu-items">
                {menuData[activeCategory].items.map((item, index) => (
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
          <p>📞 +212 661 46 05 93 | 📍 M7RG+RJ3, Bd Mohamed Hafidi, Tiznit</p>
          <p>&copy; 2025 Resto Pêcheur - Tous les prix sont en Dirhams (DH)</p>
        </div>
      </footer>
    </div>
  );
}

export default MenuPage;