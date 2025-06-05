import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import menuData from '../Data/menu.json';
import './MenuPage.css';

function MenuPage() {
  const [selectedCategory, setSelectedCategory] = useState(null);

  const categories = Object.keys(menuData.categories);

  // Images et icônes pour chaque catégorie
  const categoryImages = {
    'entrees-froides': {
      icon: '🥗',
      color: '#27ae60',
      description: 'Salades fraîches et entrées froides'
    },
    'entrees-chaudes': {
      icon: '🍲',
      color: '#e74c3c',
      description: 'Soupes et entrées chaudes'
    },
    'pates': {
      icon: '🍝',
      color: '#f39c12',
      description: 'Spaghetti et tagliatelles'
    },
    'lasagnes': {
      icon: '🧀',
      color: '#d35400',
      description: 'Lasagnes au four'
    },
    'omelettes': {
      icon: '🥚',
      color: '#f1c40f',
      description: 'Omelettes variées'
    },
    'sandwiches': {
      icon: '🥪',
      color: '#3498db',
      description: 'Sandwiches et wraps'
    },
    'paninis': {
      icon: '🍞',
      color: '#95a5a6',
      description: 'Paninis grillés'
    },
    'burgers': {
      icon: '🍔',
      color: '#e67e22',
      description: 'Burgers et steaks'
    },
    'poulet': {
      icon: '🍗',
      color: '#f39c12',
      description: 'Poulet grillé au four'
    },
    'plats': {
      icon: '🍖',
      color: '#c0392b',
      description: 'Brochettes et plats chauds'
    },
    'poisson-friture': {
      icon: '🍤',
      color: '#3498db',
      description: 'Poissons frits et fruits de mer'
    },
    'plancha': {
      icon: '🐟',
      color: '#16a085',
      description: 'Grillades à la plancha'
    },
    'plat-creme': {
      icon: '🐠',
      color: '#f8f9fa',
      description: 'Poissons à la crème'
    },
    'tajines': {
      icon: '🥘',
      color: '#e74c3c',
      description: 'Tajines traditionnels'
    },
    'paella': {
      icon: '🥙',
      color: '#f39c12',
      description: 'Paëllas valenciennes'
    },
    'desserts': {
      icon: '🍰',
      color: '#e91e63',
      description: 'Desserts et sucreries'
    },
    'boissons': {
      icon: '☕',
      color: '#795548',
      description: 'Thés, sodas et eau'
    },
    'jus': {
      icon: '🧃',
      color: '#ff9800',
      description: 'Jus de fruits frais'
    },
    'jus-bio': {
      icon: '🥕',
      color: '#4caf50',
      description: 'Jus bio et naturels'
    }
  };

  const handleCategoryClick = (categoryKey) => {
    setSelectedCategory(categoryKey);
  };

  const handleBackToCategories = () => {
    setSelectedCategory(null);
  };

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
          {!selectedCategory ? (
            // Vue des catégories
            <div className="categories-view">
              <h2 className="page-title">Découvrez notre menu</h2>
              <p className="page-subtitle">Cliquez sur une catégorie pour voir nos plats</p>
              
              <div className="categories-grid">
                {categories.map(categoryKey => {
                  const categoryInfo = categoryImages[categoryKey];
                  const category = menuData.categories[categoryKey];
                  
                  return (
                    <div
                      key={categoryKey}
                      className="category-card"
                      onClick={() => handleCategoryClick(categoryKey)}
                      style={{ borderColor: categoryInfo.color }}
                    >
                      <div 
                        className="category-icon"
                        style={{ backgroundColor: categoryInfo.color }}
                      >
                        {categoryInfo.icon}
                      </div>
                      <h3 className="category-title">{category.title}</h3>
                      <p className="category-description">{categoryInfo.description}</p>
                      <div className="category-count">
                        {category.items.length} plat{category.items.length > 1 ? 's' : ''}
                      </div>
                      <div className="category-price-range">
                        {Math.min(...category.items.map(item => item.price))} - {Math.max(...category.items.map(item => item.price))} DH
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            // Vue des plats d'une catégorie
            <div className="category-details">
              <div className="category-header">
                <button className="back-btn" onClick={handleBackToCategories}>
                  ← Retour aux catégories
                </button>
                <div className="category-info">
                  <span 
                    className="category-icon-large"
                    style={{ backgroundColor: categoryImages[selectedCategory].color }}
                  >
                    {categoryImages[selectedCategory].icon}
                  </span>
                  <div>
                    <h2>{menuData.categories[selectedCategory].title}</h2>
                    <p>{categoryImages[selectedCategory].description}</p>
                  </div>
                </div>
              </div>

              <div className="dishes-grid">
                {menuData.categories[selectedCategory].items.map((item, index) => (
                  <div key={index} className="dish-card">
                    <div className="dish-info">
                      <h3 className="dish-name">{item.name}</h3>
                      <div className="dish-price">{item.price} DH</div>
                    </div>
                    <div className="dish-actions">
                      <span className="dish-category">{menuData.categories[selectedCategory].title}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Call to action */}
          {!selectedCategory && (
            <div className="menu-cta">
              <h3>Envie de commander ?</h3>
              <p>Réservez votre table pour déguster nos spécialités</p>
              <Link to="/reservation" className="cta-button">
                Réserver une table
              </Link>
            </div>
          )}
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