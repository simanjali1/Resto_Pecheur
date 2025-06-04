import React, { useState } from 'react';
import menuData from '../Data/menu.json';
import './MenuSelector.css';

function MenuSelector({ selectedDishes, onDishUpdate, onClose }) {
  const [activeCategory, setActiveCategory] = useState('entrees-froides');

  const categories = Object.keys(menuData.categories);

  const handleDishSelection = (dish, category) => {
    const dishId = `${category}_${dish.name}`;
    const existingDish = selectedDishes.find(d => d.id === dishId);
    
    if (existingDish) {
      // Supprimer le plat
      onDishUpdate(selectedDishes.filter(d => d.id !== dishId));
    } else {
      // Ajouter le nouveau plat
      onDishUpdate([...selectedDishes, {
        id: dishId,
        category: menuData.categories[category].title,
        name: dish.name,
        price: dish.price,
        quantity: 1
      }]);
    }
  };

  const updateQuantity = (dishId, newQuantity) => {
    if (newQuantity === 0) {
      onDishUpdate(selectedDishes.filter(d => d.id !== dishId));
    } else {
      onDishUpdate(selectedDishes.map(d => 
        d.id === dishId ? { ...d, quantity: newQuantity } : d
      ));
    }
  };

  const getTotalPrice = () => {
    return selectedDishes.reduce((total, dish) => total + (dish.price * dish.quantity), 0);
  };

  return (
    <div className="menu-selector-overlay">
      <div className="menu-selector">
        {/* Header */}
        <div className="menu-selector-header">
          <h2>Sélectionnez vos plats</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="menu-selector-content">
          {/* Navigation des catégories */}
          <nav className="menu-categories-nav">
            {categories.map(categoryKey => (
              <button
                key={categoryKey}
                className={`category-btn ${activeCategory === categoryKey ? 'active' : ''}`}
                onClick={() => setActiveCategory(categoryKey)}
              >
                {menuData.categories[categoryKey].title}
              </button>
            ))}
          </nav>

          {/* Contenu du menu */}
          <div className="menu-content">
            <h3 className="category-title">{menuData.categories[activeCategory].title}</h3>
            
            <div className="menu-items">
              {menuData.categories[activeCategory].items.map((item, index) => {
                const dishId = `${activeCategory}_${item.name}`;
                const selectedDish = selectedDishes.find(d => d.id === dishId);
                const isSelected = !!selectedDish;
                
                return (
                  <div key={index} className={`menu-item ${isSelected ? 'selected' : ''}`}>
                    <div className="item-header">
                      <label className="item-checkbox">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleDishSelection(item, activeCategory)}
                        />
                        <div className="item-info">
                          <h4 className="item-name">{item.name}</h4>
                          <span className="item-price">{item.price} DH</span>
                        </div>
                      </label>
                    </div>
                    
                    {isSelected && (
                      <div className="quantity-section">
                        <div className="quantity-controls">
                          <button
                            type="button"
                            className="qty-btn"
                            onClick={() => updateQuantity(dishId, selectedDish.quantity - 1)}
                          >
                            -
                          </button>
                          <span className="quantity">{selectedDish.quantity}</span>
                          <button
                            type="button"
                            className="qty-btn"
                            onClick={() => updateQuantity(dishId, selectedDish.quantity + 1)}
                          >
                            +
                          </button>
                        </div>
                        <div className="subtotal">
                          Sous-total: {selectedDish.price * selectedDish.quantity} DH
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer avec résumé */}
        {selectedDishes.length > 0 && (
          <div className="menu-selector-footer">
            <div className="order-summary">
              <div className="summary-header">
                <h4>Votre sélection ({selectedDishes.length} plat{selectedDishes.length > 1 ? 's' : ''})</h4>
                <div className="total-price">Total: {getTotalPrice()} DH</div>
              </div>
              <div className="selected-items-list">
                {selectedDishes.map(dish => (
                  <div key={dish.id} className="summary-item">
                    <span>{dish.name} x{dish.quantity}</span>
                    <span>{dish.price * dish.quantity} DH</span>
                  </div>
                ))}
              </div>
            </div>
            <button className="confirm-selection-btn" onClick={onClose}>
              Confirmer la sélection
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default MenuSelector;