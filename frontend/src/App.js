import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import BookingPage from './pages/BookingPage';
import ConfirmationPage from './pages/ConfirmationPage';
import MenuPage from './pages/MenuPage';
import TestConnection from './components/TestConnection';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/reservation" element={<BookingPage />} />
          <Route path="/confirmation" element={<ConfirmationPage />} />
          <Route path="/menu" element={<MenuPage />} />
          {/* Route temporaire pour tester la connexion API */}
          <Route path="/test-connection" element={<TestConnection />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;