import React from 'react';
import ReactDOM from 'react-dom/client';
import Main from './main';
import "./App.scss";

function App() {
  return <Main />;
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);