import React, { useState, useEffect } from 'react';
import { restaurantAPI } from '../services/api';

function TestConnection() {
  const [restaurant, setRestaurant] = useState(null);
  const [timeSlots, setTimeSlots] = useState([]);
  const [availability, setAvailability] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    testAPIConnection();
  }, []);

  const testAPIConnection = async () => {
    try {
      setLoading(true);
      setError(null);

      // Test 1: Récupérer infos restaurant
      console.log('🏪 Test: Récupération restaurant...');
      const restaurantResponse = await restaurantAPI.getRestaurant();
      setRestaurant(restaurantResponse.data);
      console.log('✅ Restaurant récupéré:', restaurantResponse.data);

      // Test 2: Récupérer créneaux horaires
      console.log('⏰ Test: Récupération créneaux...');
      const timeSlotsResponse = await restaurantAPI.getTimeSlots();
      setTimeSlots(timeSlotsResponse.data);
      console.log('✅ Créneaux récupérés:', timeSlotsResponse.data);

      // Test 3: Vérifier disponibilité pour aujourd'hui
      const today = new Date().toISOString().split('T')[0];
      console.log('📅 Test: Vérification disponibilité pour', today);
      const availabilityResponse = await restaurantAPI.checkAvailability(today);
      setAvailability(availabilityResponse.data);
      console.log('✅ Disponibilité récupérée:', availabilityResponse.data);

    } catch (err) {
      console.error('❌ Erreur lors du test API:', err);
      setError(err.message || 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>🔄 Test de connexion API en cours...</h2>
        <p>Vérification de la connexion avec le backend Django</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', backgroundColor: '#ffebee', border: '1px solid #f44336', borderRadius: '8px' }}>
        <h2 style={{ color: '#d32f2f' }}>❌ Erreur de connexion</h2>
        <p><strong>Erreur:</strong> {error}</p>
        <div style={{ marginTop: '15px' }}>
          <h3>🔧 Vérifications à faire :</h3>
          <ul style={{ textAlign: 'left' }}>
            <li>✅ Backend Django lancé sur http://localhost:8000</li>
            <li>✅ Frontend React lancé sur http://localhost:3000</li>
            <li>✅ CORS configuré dans Django settings.py</li>
            <li>✅ API accessible : <a href="http://localhost:8000/api/restaurant/" target="_blank" rel="noopener noreferrer">Tester l'API</a></li>
          </ul>
        </div>
        <button 
          onClick={testAPIConnection}
          style={{ marginTop: '10px', padding: '10px 20px', backgroundColor: '#2196F3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          🔄 Réessayer
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', backgroundColor: '#e8f5e8', border: '1px solid #4caf50', borderRadius: '8px' }}>
      <h2 style={{ color: '#2e7d32' }}>🎉 Connexion API réussie !</h2>
      
      {restaurant && (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: 'white', borderRadius: '8px' }}>
          <h3>🏪 Restaurant connecté :</h3>
          <p><strong>Nom:</strong> {restaurant.name}</p>
          <p><strong>Adresse:</strong> {restaurant.address}</p>
          <p><strong>Téléphone:</strong> {restaurant.phone}</p>
          <p><strong>Capacité:</strong> {restaurant.capacity} personnes</p>
          <p><strong>Horaires:</strong> {restaurant.opening_time} - {restaurant.closing_time}</p>
        </div>
      )}

      {timeSlots.length > 0 && (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: 'white', borderRadius: '8px' }}>
          <h3>⏰ Créneaux horaires disponibles :</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
            {timeSlots.map(slot => (
              <div key={slot.id} style={{ padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                <strong>{slot.time}</strong> - Max {slot.max_reservations} réservations
                {slot.is_active ? ' ✅' : ' ❌'}
              </div>
            ))}
          </div>
        </div>
      )}

      {availability && (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: 'white', borderRadius: '8px' }}>
          <h3>📅 Disponibilité d'aujourd'hui :</h3>
          <p>Créneaux disponibles trouvés !</p>
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: '20px' }}>
        <p style={{ color: '#2e7d32', fontWeight: 'bold' }}>
          ✅ Backend et Frontend sont maintenant connectés !
        </p>
        <p>Vous pouvez maintenant utiliser l'API dans vos composants de réservation.</p>
      </div>
    </div>
  );
}

export default TestConnection;