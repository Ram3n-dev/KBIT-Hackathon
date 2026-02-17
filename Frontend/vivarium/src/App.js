import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatBots from './pages/ChatBots';
import GraphRelations from './pages/GraphRelations';
import AgentInspector from './pages/AgentInspector';
import Dashboard from './pages/Dashboard';
import CreateAgentPanel from './pages/CreateAgentPanel';
import './App.css';

function App() {
  const [isCreatePanelOpen, setIsCreatePanelOpen] = useState(false);
  const [agents, setAgents] = useState([]);

  const handleAddAgent = (newAgent) => {
    setAgents([...agents, { ...newAgent, id: Date.now() }]);
    setIsCreatePanelOpen(false);
  };

  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar onAddAgentClick={() => setIsCreatePanelOpen(true)} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard agents={agents} />} />
            <Route path="/chat-bots" element={<ChatBots agents={agents} />} />
            <Route path="/graph-relations" element={<GraphRelations agents={agents} />} />
            <Route path="/agent-inspector" element={<AgentInspector agents={agents} />} />
            <Route path="/dashboard" element={<Dashboard agents={agents} />} />
          </Routes>
        </main>
        
        {/* Панель создания агента */}
        <CreateAgentPanel 
          isOpen={isCreatePanelOpen}
          onClose={() => setIsCreatePanelOpen(false)}
          onCreateAgent={handleAddAgent}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;