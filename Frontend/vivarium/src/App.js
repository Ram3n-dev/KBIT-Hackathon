import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatBots from './pages/ChatBots';
import GraphRelations from './pages/GraphRelations';
import AgentInspector from './pages/AgentInspector';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat-bots" element={<ChatBots />} />
            <Route path="/graph-relations" element={<GraphRelations />} />
            <Route path="/agent-inspector" element={<AgentInspector />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;