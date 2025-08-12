import './main-style.scss'; 
import React, { useState } from 'react';
import Dashboard from './Dashboard';

function Main() {
  const [activePage, setActivePage] = useState('landing');
  const [dashboardSection, setDashboardSection] = useState(null);

  // Add auth states
  const [token, setToken] = useState(null);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [authError, setAuthError] = useState(null);

  // Signup component inside Main
  const Signup = () => {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const handleSignup = async () => {
      setAuthError(null);
      if (password !== confirmPassword) {
        setAuthError("Passwords don't match");
        return;
      }
      try {
        const res = await fetch('/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, email, password, confirm_password: confirmPassword }),
        });
        const data = await res.json();
        if (res.ok) {
          setToken(data.token);
        } else {
          setAuthError(data.message || 'Signup failed');
        }
      } catch (e) {
        setAuthError('Network error');
      }
    };

    return (
      <div className="auth-form">
        <h2>Sign Up</h2>
        <input placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />
        <input placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
        <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <input placeholder="Confirm Password" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
        <button onClick={handleSignup}>Sign Up</button>
        {authError && <p style={{color: 'red'}}>{authError}</p>}
        <p>
          Already have an account?{' '}
          <button onClick={() => { setAuthMode('login'); setAuthError(null); }}>Log In</button>
        </p>
      </div>
    );
  };

  // Login component inside Main
  const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleLogin = async () => {
      setAuthError(null);
      try {
        const res = await fetch('/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (res.ok) {
          setToken(data.token);
        } else {
          setAuthError(data.message || 'Login failed');
        }
      } catch (e) {
        setAuthError('Network error');
      }
    };

    return (
      <div className="auth-form">
        <h2>Log In</h2>
        <input placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
        <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <button onClick={handleLogin}>Log In</button>
        {authError && <p style={{color: 'red'}}>{authError}</p>}
        <p>
          Don't have an account?{' '}
          <button onClick={() => { setAuthMode('signup'); setAuthError(null); }}>Sign Up</button>
        </p>
      </div>
    );
  };

  // If not logged in, show login/signup forms
  if (!token) {
    return authMode === 'login' ? <Login /> : <Signup />;
  }

  // If logged in, show your existing dashboard & project UI
  if (dashboardSection) {
    return (
      <Dashboard 
        section={dashboardSection} 
        onBack={() => setDashboardSection(null)} 
      />
    );
  }

  const renderContent = () => {
    switch (activePage) {
      case 'new':
        return (
          <div className="new-project-container">
            <div className="new-project-name">
              <label>Project Name: </label>
              <input />
            </div>
            <img id="monkey-icon" src="monkey.png" alt="monkey" />
            <div className="new-project-btns">
              <button id="back-btn" onClick={() => setActivePage('landing')}>back</button>
              <button onClick={() => setDashboardSection('new')}>Create</button>
            </div>
          </div>
        );

      case 'open':
        return (
          <div className="open-project-container">
            <div className="open-project-edit-btns">
              <button>Edit</button>
              <button style={{ display: 'none' }}>Delete</button>
            </div>
            <div className="project-directory">
              <h1>project names</h1>
            </div>
            <div className="open-project-btns">
              <button id="back-btn" onClick={() => setActivePage('landing')}>back</button>
              <button onClick={() => setDashboardSection('open')}>open</button>
            </div>
          </div>
        );

      case 'chat':
        return (
          <div className="just-chat-container">
            <div className="just-chat-output"></div>
            <div className="just-chat-controls">
              <input type="text" id="ai-input" placeholder="Ask AI anything..." />
              <button id="ai-send" aria-label="Send">
                <svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="#007bff"
                  className="bi bi-arrow-up-circle-fill" viewBox="0 0 16 16">
                  <path
                    d="M16 8A8 8 0 1 0 0 8a8 8 0 0 0 16 0m-7.5 3.5a.5.5 0 0 1-1 0V5.707L5.354 7.854a.5.5 0 1 1-.708-.708l3-3a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 5.707z" />
                </svg>
              </button>
            </div>
            <button id="back-btn" onClick={() => setActivePage('landing')}>back</button>
          </div>
        );

      default:
        return (
          <div className="landing-container">
            <div className="landing-info">
              <h1>unRead.Chat</h1>
              <p>peanut bobby peanut bobby</p>
              <div className="landing-buttons">
                <button onClick={() => setActivePage('new')}>New Project</button>
                <button onClick={() => setActivePage('open')}>Open Project</button>
                <button onClick={() => setActivePage('chat')}>Just Chat</button>
              </div>
            </div>
            <div className="landing-display">
              <img src="kitty.png" alt="landing visual" />
            </div>
          </div>
        );
    }
  };

  return (
    <div className="main-page">
      {renderContent()}
    </div>
  );
}

export default Main;
