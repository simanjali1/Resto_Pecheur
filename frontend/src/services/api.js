import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Configuration axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 secondes timeout
});

// Intercepteur pour gérer les erreurs
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Erreur API:', error);
    return Promise.reject(error);
  }
);

export const restaurantAPI = {
  // Récupérer infos du restaurant
  getRestaurant: () => apiClient.get('/restaurant/'),
  
  // Récupérer tous les créneaux horaires
  getTimeSlots: () => apiClient.get('/timeslots/'),
  
  // Vérifier disponibilité pour une date spécifique
  checkAvailability: (date) => apiClient.get(`/availability/?date=${date}`),
  
  // Créer une réservation
  createReservation: (reservationData) => apiClient.post('/reservations/create/', reservationData),
};

export default restaurantAPI;