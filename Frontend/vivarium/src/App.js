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
    const savedUser = localStorage.getItem("user");
    
    if (token && savedUser) {
      // Сначала устанавливаем из localStorage для быстрого отображения
      setUser(JSON.parse(savedUser));
      setIsAuthenticated(true);
      
      // Затем проверяем валидность токена и получаем актуальные данные
      verifyAuth(token);
    }
  }, []);

  const verifyAuth = async (token) => {
    try {
      // Проверяем валидность токена и получаем профиль
      const profile = await api.getProfile();
      const userData = {
        id: profile.id,
        name: profile.username,
        email: profile.email,
        avatarUrl: profile.avatarUrl || null
      };
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
      setIsAuthenticated(true);
    } catch (error) {
      // Если токен невалидный - очищаем всё
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  // Загрузка агентов при авторизации
  useEffect(() => {
    if (isAuthenticated) {
      loadAgents();
    } else {
      setAgents([]);
    }
  }, [isAuthenticated]);

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
      setAgents(agents.filter((agent) => agent.id !== agentId));
      setIsDeletePanelOpen(false);
    } catch (error) {
      console.error("Ошибка удаления агента:", error);
    }
  };

  const handleLogin = async (username, password) => {
    try {
      const response = await api.login(username, password);
      // Данные уже сохраняются в api.js, но дублируем для надежности
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
      setUser(response.user);
      setIsAuthenticated(true);
      setIsAuthModalOpen(false);
    } catch (error) {
      console.error("Ошибка регистрации:", error);
      throw error;
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error("Ошибка при выходе:", error);
    } finally {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      api.token = null;
      setUser(null);
      setIsAuthenticated(false);
      setAgents([]);
    }
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
                <Dashboard 
                  agents={agents} 
                  isAuthenticated={isAuthenticated}
                  onLoginClick={() => setIsAuthModalOpen(true)}
                />
              }
            />
            <Route
              path="/chat-bots"
              element={
                <ChatBots 
                  agents={agents} 
                  isAuthenticated={isAuthenticated}
                  onLoginClick={() => setIsAuthModalOpen(true)}
                />
              }
            />
            <Route
              path="/graph-relations"
              element={
                <GraphRelations
                  agents={agents}
                  isAuthenticated={isAuthenticated}
                  onLoginClick={() => setIsAuthModalOpen(true)}
                />
              }
            />
            <Route
              path="/agent-inspector"
              element={
                <AgentInspector
                  agents={agents}
                  isAuthenticated={isAuthenticated}
                  onLoginClick={() => setIsAuthModalOpen(true)}
                />
              }
            />
            <Route
              path="/dashboard"
              element={
                <Dashboard 
                  agents={agents} 
                  isAuthenticated={isAuthenticated}
                  onLoginClick={() => setIsAuthModalOpen(true)}
                />
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