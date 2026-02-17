import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import ChatBots from "./pages/ChatBots";
import GraphRelations from "./pages/GraphRelations";
import AgentInspector from "./pages/AgentInspector";
import Dashboard from "./pages/Dashboard";
import CreateAgentPanel from "./pages/CreateAgentPanel";
import DeleteAgentPanel from "./pages/DeleteAgentPanel";
import AuthModal from "./components/AuthModal";
import "./App.css";
import api from "./services/api";

function App() {
  const [isCreatePanelOpen, setIsCreatePanelOpen] = useState(false);
  const [isDeletePanelOpen, setIsDeletePanelOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [agents, setAgents] = useState([]);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Проверка авторизации при загрузке
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      checkAuth(token);
    }
  }, []);

  // Загрузка агентов при авторизации
  useEffect(() => {
    if (isAuthenticated) {
      loadAgents();
    }
  }, [isAuthenticated]);

  const checkAuth = async (token) => {
    try {
      const userData = await api.checkAuth(token);
      setUser(userData);
      setIsAuthenticated(true);
    } catch (error) {
      localStorage.removeItem("token");
    }
  };

  const loadAgents = async () => {
    try {
      const data = await api.getAgents();
      setAgents(data);
    } catch (error) {
      console.error("Ошибка загрузки агентов:", error);
    }
  };

  const handleAddAgent = async (newAgent) => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      const createdAgent = await api.createAgent(newAgent);
      setAgents([...agents, createdAgent]);
      setIsCreatePanelOpen(false);
    } catch (error) {
      console.error("Ошибка создания агента:", error);
    }
  };

  const handleDeleteAgent = async (agentId) => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      await api.deleteAgent(agentId);
      // Обновляем список после удаления
      setAgents(agents.filter((agent) => agent.id !== agentId));
      setIsDeletePanelOpen(false);
    } catch (error) {
      console.error("Ошибка удаления агента:", error);
    }
  };

  const handleLogin = async (username, password) => {
    try {
      const response = await api.login(username, password);
      localStorage.setItem("token", response.token);
      setUser(response.user);
      setIsAuthenticated(true);
      setIsAuthModalOpen(false);
    } catch (error) {
      console.error("Ошибка входа:", error);
      throw error;
    }
  };

  const handleRegister = async (username, email, password) => {
    try {
      const response = await api.register(username, email, password);
      localStorage.setItem("token", response.token);
      setUser(response.user);
      setIsAuthenticated(true);
      setIsAuthModalOpen(false);
    } catch (error) {
      console.error("Ошибка регистрации:", error);
      throw error;
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    api.token = null;
    setUser(null);
    setIsAuthenticated(false);
    setAgents([]); // Очищаем список агентов при выходе
  };

  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar
          onAddAgentClick={() => {
            if (!isAuthenticated) {
              setIsAuthModalOpen(true);
            } else {
              setIsCreatePanelOpen(true);
            }
          }}
          onDeleteAgentClick={() => {
            if (!isAuthenticated) {
              setIsAuthModalOpen(true);
            } else {
              setIsDeletePanelOpen(true);
            }
          }}
          onLoginClick={() => setIsAuthModalOpen(true)}
          onLogout={handleLogout}
          isAuthenticated={isAuthenticated}
          userData={user}
        />
        <main className="main-content">
          <Routes>
            <Route
              path="/"
              element={
                <Dashboard agents={agents} isAuthenticated={isAuthenticated} />
              }
            />
            <Route
              path="/chat-bots"
              element={
                <ChatBots agents={agents} isAuthenticated={isAuthenticated} />
              }
            />
            <Route
              path="/graph-relations"
              element={
                <GraphRelations
                  agents={agents}
                  isAuthenticated={isAuthenticated}
                />
              }
            />
            <Route
              path="/agent-inspector"
              element={
                <AgentInspector
                  agents={agents}
                  isAuthenticated={isAuthenticated}
                />
              }
            />
            <Route
              path="/dashboard"
              element={
                <Dashboard agents={agents} isAuthenticated={isAuthenticated} />
              }
            />
          </Routes>
        </main>

        <CreateAgentPanel
          isOpen={isCreatePanelOpen}
          onClose={() => setIsCreatePanelOpen(false)}
          onCreateAgent={handleAddAgent}
        />

        <DeleteAgentPanel
          isOpen={isDeletePanelOpen}
          onClose={() => setIsDeletePanelOpen(false)}
          onDeleteAgent={handleDeleteAgent}
          agents={agents}
        />

        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          onLogin={handleLogin}
          onRegister={handleRegister}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;