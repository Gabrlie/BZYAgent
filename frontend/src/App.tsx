import { useState, useEffect } from 'react';
import LoginForm from './components/LoginForm';
import HomePage from './components/HomePage';
import { isAuthenticated } from './services/auth';
import './App.css';

function App() {
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    setAuthenticated(isAuthenticated());
  }, []);

  const handleLoginSuccess = () => {
    setAuthenticated(true);
  };

  const handleLogout = () => {
    setAuthenticated(false);
  };

  return (
    <>
      {authenticated ? (
        <HomePage onLogout={handleLogout} />
      ) : (
        <LoginForm onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  );
}

export default App;
