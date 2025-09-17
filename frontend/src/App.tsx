import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout/Layout'
import Dashboard from '@/pages/Dashboard/Dashboard'
import Agents from '@/pages/Agents/Agents'
import Tasks from '@/pages/Tasks/Tasks'
import Chat from '@/pages/Chat/Chat'
import Settings from '@/pages/Settings/Settings'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
