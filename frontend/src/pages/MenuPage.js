import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import menuData from '../Data/menu.json';
import './MenuPage.css';

// Import logo
import logo from '../assets/images/mainPicture/logo.png';

// Import all category images with correct lowercase .jpeg filenames
import boissonsImg from '../assets/images/Category_pics/boissons.jpeg';
import burgersImg from '../assets/images/Category_pics/burgers.jpeg';
import dessertsImg from '../assets/images/Category_pics/desserts.jpeg';
import entreesChaudesImg from '../assets/images/Category_pics/entrees-chaudes.jpeg';
import entreesFromdesImg from '../assets/images/Category_pics/entrees-froides.jpeg';
import jusImg from '../assets/images/Category_pics/jus.jpeg';
import jusBioImg from '../assets/images/Category_pics/jus-bio-naturelle.jpeg';
import lasagnesImg from '../assets/images/Category_pics/Lasagnes.jpeg';
import patesImg from '../assets/images/Category_pics/Les-Pates.jpeg';
import platsImg from '../assets/images/Category_pics/Les-Plats.jpeg';
import omelettesImg from '../assets/images/Category_pics/Omelettes.jpeg';
import paellaImg from '../assets/images/Category_pics/Paella.jpeg';
import paninisImg from '../assets/images/Category_pics/Paninis.jpeg';
import planchaImg from '../assets/images/Category_pics/Plancha.jpeg';
import platCremeImg from '../assets/images/Category_pics/plat-creme.jpeg';
import poissonFritureImg from '../assets/images/Category_pics/Poisson-Friture.jpeg';
import pouletImg from '../assets/images/Category_pics/Poulet-grille-au-four.jpeg';
import sandwichesImg from '../assets/images/Category_pics/Sandwiches.jpeg';
import tajinesImg from '../assets/images/Category_pics/Tajine-de-poisson.jpeg';

// Images et informations pour chaque catégorie - using imported images from src
const categoryImages = {
  'entrees-froides': {
    image: entreesFromdesImg,
    color: '#27ae60',
    nameFr: 'Entrées Froides',
    nameAr: 'المقبلات الباردة',
    description: 'Salades fraîches et entrées froides'
  },
  'entrees-chaudes': {
    image: entreesChaudesImg,
    color: '#e74c3c',
    nameFr: 'Entrées Chaudes',
    nameAr: 'المقبلات الساخنة',
    description: 'Soupes et entrées chaudes'
  },
  'pates': {
    image: patesImg,
    color: '#f39c12',
    nameFr: 'Les Pâtes',
    nameAr: 'المعكرونة',
    description: 'Spaghetti et tagliatelles'
  },
  'lasagnes': {
    image: lasagnesImg,
    color: '#d35400',
    nameFr: 'Lasagnes',
    nameAr: 'اللازانيا',
    description: 'Lasagnes au four'
  },
  'omelettes': {
    image: omelettesImg,
    color: '#f1c40f',
    nameFr: 'Omelettes',
    nameAr: 'العجة',
    description: 'Omelettes variées'
  },
  'sandwiches': {
    image: sandwichesImg,
    color: '#3498db',
    nameFr: 'Sandwiches',
    nameAr: 'السندويشات',
    description: 'Sandwiches et wraps'
  },
  'paninis': {
    image: paninisImg,
    color: '#95a5a6',
    nameFr: 'Paninis',
    nameAr: 'البانيني',
    description: 'Paninis grillés'
  },
  'burgers': {
    image: burgersImg,
    color: '#e67e22',
    nameFr: 'Burgers',
    nameAr: 'البرجر',
    description: 'Burgers et steaks'
  },
  'poulet': {
    image: pouletImg,
    color: '#f39c12',
    nameFr: 'Poulet',
    nameAr: 'الدجاج',
    description: 'Poulet grillé au four'
  },
  'plats': {
    image: platsImg,
    color: '#c0392b',
    nameFr: 'Les Plats',
    nameAr: 'الأطباق الرئيسية',
    description: 'Brochettes et plats chauds'
  },
  'poisson-friture': {
    image: poissonFritureImg,
    color: '#3498db',
    nameFr: 'Poisson Friture',
    nameAr: 'السمك المقلي',
    description: 'Poissons frits et fruits de mer'
  },
  'plancha': {
    image: planchaImg,
    color: '#16a085',
    nameFr: 'Plancha',
    nameAr: 'البلانشا',
    description: 'Grillades à la plancha'
  },
  'plat-creme': {
    image: platCremeImg,
    color: '#f8f9fa',
    nameFr: 'Plat Crème',
    nameAr: 'أطباق بالكريمة',
    description: 'Poissons à la crème'
  },
  'tajines': {
    image: tajinesImg,
    color: '#e74c3c',
    nameFr: 'Tajines',
    nameAr: 'الطاجين',
    description: 'Tajines traditionnels'
  },
  'paella': {
    image: paellaImg,
    color: '#f39c12',
    nameFr: 'Paëlla',
    nameAr: 'البايلا',
    description: 'Paëllas valenciennes'
  },
  'desserts': {
    image: dessertsImg,
    color: '#e91e63',
    nameFr: 'Desserts',
    nameAr: 'الحلويات',
    description: 'Desserts et sucreries'
  },
  'boissons': {
    image: boissonsImg,
    color: '#795548',
    nameFr: 'Boissons',
    nameAr: 'المشروبات',
    description: 'Thés, sodas et eau'
  },
  'jus': {
    image: jusImg,
    color: '#ff9800',
    nameFr: 'Jus',
    nameAr: 'العصائر',
    description: 'Jus de fruits frais'
  },
  'jus-bio': {
    image: jusBioImg,
    color: '#4caf50',
    nameFr: 'Jus Bio',
    nameAr: 'العصائر الطبيعية',
    description: 'Jus bio et naturels'
  }
};

function MenuPage() {
  const [selectedCategory, setSelectedCategory] = useState(null);

  const categories = Object.keys(menuData.categories);

  const handleCategoryClick = (categoryKey) => {
    setSelectedCategory(categoryKey);
  };

  const handleBackToCategories = () => {
    setSelectedCategory(null);
  };

  return (
    <div className="menu-page">
      {/* Header with Logo */}
      <header className="menu-header">
        <div className="container">
          <Link to="/" className="back-button">Retour</Link>
          <h1>Menu Digital</h1>
          <div className="menu-header-logo">
            <img src={logo} alt="Resto Pêcheur Logo" />
          </div>
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
                      style={{ 
                        borderColor: '#e74c3c',
                        backgroundImage: `linear-gradient(rgba(255, 255, 255, 0.4), rgba(255, 255, 255, 0.4)), url(${categoryInfo.image})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        backgroundRepeat: 'no-repeat'
                      }}
                    >
                      <h3 className="category-title-fr">{categoryInfo.nameFr}</h3>
                      <h4 className="category-title-ar">{categoryInfo.nameAr}</h4>
                      <div className="category-count">
                        {category.items.length} plat{category.items.length > 1 ? 's' : ''}
                      </div>
                      <p className="category-description">{categoryInfo.description}</p>
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
                  Retour aux catégories
                </button>
                <div className="category-info">
                  <span 
                    className="category-icon-large"
                    style={{ backgroundColor: categoryImages[selectedCategory].color }}
                  >
                    <img 
                      src={categoryImages[selectedCategory].image} 
                      alt={categoryImages[selectedCategory].nameFr}
                      className="category-image-large"
                    />
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
                    <div className="dish-header">
                      <h3 className="dish-name">{item.name}</h3>
                      <div className="dish-price">{item.price} DH</div>
                    </div>
                    
                    {/* Description/Ingredients */}
                    {item.description && (
                      <div className="dish-description">
                        <p className="ingredients">
                          {item.description}
                        </p>
                      </div>
                    )}
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
          <p>📍 Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc</p>
          <p>📞 0661-460593 | ✉️ contact@resto-pecheur.ma</p>
          <p>&copy; 2025 Resto Pêcheur - Tous les prix sont en Dirhams (DH) </p>
        </div>
      </footer>
    </div>
  );
}

export default MenuPage;