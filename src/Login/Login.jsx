import { useState } from 'react';   
import './login.scss';

function AuthHeader({ type, onMinimize, onMaximize, isMinimized }) {
  return (
    <header className={`login-header ${isMinimized ? 'minimized-header' : ''}`}>
      <h2>{type === 'login' ? 'Sign in' : 'Sign up'}</h2>
      <div className="login-header-btns">
        <button onClick={onMinimize} disabled={isMinimized}>
          <img src="minimize.png" alt="Minimize" />
        </button>
        <button onClick={onMaximize} disabled={!isMinimized}>
          <img src="maximize.png" alt="Maximize" />
        </button>
      </div>
    </header>
  );
}

function AuthForm({ type, onSwitch, isMinimized, onMinimize, onMaximize }) {
  return (
    <div className={`${type}-form auth-form ${isMinimized ? 'minimized' : ''}`}>
      <AuthHeader
        type={type}
        onMinimize={onMinimize}
        onMaximize={onMaximize}
        isMinimized={isMinimized}
      />

      {!isMinimized && (
        <>
          {type === 'login' && (
            <div className="social-media-login">
              <button
                id="login-google-btn"
                onClick={() => { window.location.href = "http://localhost:5000/login/google"; }}
              >
                <img src="google.png" alt="Google" /> Sign in with Google
              </button>
            </div>
          )}

          {/* Input with icon container */}
          <div className="input-with-icon">
            <img src={type === 'login' ? 'mail.png' : 'avatar.png'} alt="Icon" />
            <input
              placeholder={type === 'login' ? 'Sign in with Email' : 'Username'}
              type={type === 'login' ? 'email' : 'text'}
            />
          </div>

          {type === 'signup' && (
            <div className="input-with-icon">
              <img src="mail.png" alt="Email Icon" />
              <input placeholder="Email" type="email" />
            </div>
          )}

          <div className="login-no-account">
            <p>{type === 'login' ? "Don't have an account?" : "Already have an account?"}</p>
            <button onClick={onSwitch}>{type === 'login' ? 'Sign Up' : 'Log In'}</button>
          </div>
        </>
      )}
    </div>
  );
}

function Login() {
  const [activePage, setActivePage] = useState('login');
  const [isMinimized, setIsMinimized] = useState(false);

  return (
    <div className="user-authentication-page">
      {/* Persistent landing background */}
      <div className="landing-page">
        <div className="landing-container">
          <img src="brain2.png" alt="Logo" />
          <h1>unRead.</h1>
        </div>
      </div>

      {/* Render auth form with minimize/maximize */}
      <AuthForm
        type={activePage}
        isMinimized={isMinimized}
        onMinimize={() => setIsMinimized(true)}
        onMaximize={() => setIsMinimized(false)}
        onSwitch={() => setActivePage(activePage === 'login' ? 'signup' : 'login')}
      />
    </div>
  );
}

export default Login;
