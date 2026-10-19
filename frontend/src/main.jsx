import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth'
import { TournamentProvider } from './tournament'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <TournamentProvider>
          <App />
        </TournamentProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
