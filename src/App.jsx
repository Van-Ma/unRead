// src/index.jsx or src/main.jsx (your app entry)
import React from 'react';
import ReactDOM from 'react-dom/client';
import Main from './main';

function App() {
  return <Main />;
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);