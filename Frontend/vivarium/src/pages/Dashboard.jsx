import { useState, useEffect } from "react";
import "./Pages.css";
import "./DashBoard.css";
import api from "../services/api";

function Dashboard({ isAuthenticated, onLoginClick }) {
  const [eventText, setEventText] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("");
  const [messageText, setMessageText] = useState("");
  const [speed, setSpeed] = useState(1);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);

  // Загрузка агентов при монтировании
  useEffect(() => {
    if (isAuthenticated) {
      loadAgents();
      loadTimeSpeed();
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

  const loadTimeSpeed = async () => {
    try {
      const data = await api.getTimeSpeed();
      setSpeed(data.speed);
    } catch (error) {
      console.error("Ошибка загрузки скорости:", error);
    }
  };

  const handleAddEvent = async () => {
    if (!eventText.trim()) return;
    
    setLoading(true);
    try {
      await api.createEvent({ text: eventText });
      setEventText("");
      console.log("Событие добавлено");
    } catch (error) {
      console.error("Ошибка добавления события:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!selectedAgent || !messageText.trim()) return;
    
    setLoading(true);
    try {
      await api.sendMessage({
        agentId: selectedAgent,
        text: messageText
      });
      setMessageText("");
      console.log("Сообщение отправлено");
    } catch (error) {
      console.error("Ошибка отправки сообщения:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSpeedChange = async (newSpeed) => {
    setSpeed(newSpeed);
    try {
      await api.setTimeSpeed(newSpeed);
    } catch (error) {
      console.error("Ошибка изменения скорости:", error);
    }
  };

  // Заглушка для неавторизованных пользователей
  if (!isAuthenticated) {
    return (
      <div className="content-page dashboard-page">
        <h1>Панель управления</h1>
        <div className="auth-required">
          <div className="auth-required-icon">⚙️</div>
          <h2>Доступ ограничен</h2>
          <p>Пожалуйста, авторизуйтесь, чтобы управлять событиями и агентами</p>
          <button 
            className="auth-required-btn" 
            onClick={onLoginClick}
          >
            Перейти к авторизации
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="content-page dashboard-page">
      <div className="dashboard-top-row">
        {/* Блок 1: добавление события */}
        <div className="event-panel">
          <h2>напишите событие, которое вы хотите добавить</h2>
          <div className="input-wrapper">
            <textarea
              className="event-input"
              value={eventText}
              onChange={(e) => setEventText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !loading) {
                  e.preventDefault();
                  handleAddEvent();
                }
              }}
              placeholder="Введите событие..."
              disabled={loading}
            />
          </div>
        </div>

        {/* Блок 2: сообщение агенту */}
        <div className="message-panel">
          <h2>напишите личное сообщение агенту</h2>

          <div className="input-wrapper">
            <select
              className="agent-select"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              disabled={loading}
            >
              <option value="">Выберите агента</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </div>

          <div className="input-wrapper">
            <input
              type="text"
              className="message-input"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && selectedAgent && messageText.trim() && !loading) {
                  handleSendMessage();
                }
              }}
              placeholder="Введите сообщение..."
              disabled={!selectedAgent || loading}
            />
          </div>
        </div>

        {/* Блок 3: скорость времени */}
        <div className="time-speed-panel">
          <div className="speed-header">
            <h2>скорость времени</h2>
            <div className="speed-controls">
              <div className="speed-value">{speed}x</div>
              <input
                type="range"
                className="speed-slider"
                min="0"
                max="2"
                step="0.1"
                value={speed}
                onChange={(e) => handleSpeedChange(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Карточки панели управления */}
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <h3>Всего агентов</h3>
          <div className="card-value">{agents.length}</div>
        </div>
        {/* Другие карточки */}
      </div>
    </div>
  );
}

export default Dashboard;