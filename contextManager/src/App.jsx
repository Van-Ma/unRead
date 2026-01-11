import { useState } from 'react'
import './App.css'
import ChatManager from './components/ChatManager';

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="app-page">
      <ChatManager/>
    </div>
  )
}

export default App
