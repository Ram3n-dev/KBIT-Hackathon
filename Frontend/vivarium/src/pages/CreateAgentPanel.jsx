import { useState } from "react";
import "./CreateAgentPanel.css";
import api from "../services/api";

const avatarOptions = [
  { id: 1, svg: "🤖", color: "#4CAF50", name: "Робот" },
  { id: 2, svg: "👤", color: "#FFC107", name: "Человек" },
  { id: 3, svg: "🐱", color: "#F44336", name: "Кот" },
  { id: 4, svg: "🐶", color: "#5d6939", name: "Собака" },
  { id: 5, svg: "🦊", color: "#aab97e", name: "Лиса" },
  { id: 6, svg: "🦉", color: "#8b8b7a", name: "Сова" },
  { id: 7, svg: "⭐", color: "#FFD700", name: "Звезда" },
  { id: 8, svg: "🌈", color: "#4CAF50", name: "Радуга" },
];

function CreateAgentPanel({ isOpen, onClose, onCreateAgent }) {
  const [agentName, setAgentName] = useState("");
  const [selectedAvatar, setSelectedAvatar] = useState(avatarOptions[0]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!agentName.trim()) return;
    
    setLoading(true);
    try {
      const newAgent = {
        name: agentName,
        avatar: selectedAvatar.svg,
        avatarColor: selectedAvatar.color,
        avatarName: selectedAvatar.name
      };
      
      const createdAgent = await api.createAgent(newAgent);
      onCreateAgent(createdAgent);
      setAgentName("");
    } catch (error) {
      console.error("Ошибка создания агента:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="create-agent-overlay">
      <div className="create-agent-panel">
        <div className="panel-header">
          <h2>Создание агента</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="avatar-section">
            <h3>Выберите аватар</h3>
            <div className="avatar-grid">
              {avatarOptions.map((avatar) => (
                <div
                  key={avatar.id}
                  className={`avatar-option ${selectedAvatar.id === avatar.id ? 'selected' : ''}`}
                  onClick={() => setSelectedAvatar(avatar)}
                  style={{ backgroundColor: avatar.color }}
                >
                  <span className="avatar-emoji">{avatar.svg}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="name-section">
            <h3>Имя агента</h3>
            <input
              type="text"
              className="agent-name-input"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="Введите имя агента..."
              autoFocus
              disabled={loading}
            />
          </div>

          <div className="preview-section">
            <h3>Предпросмотр</h3>
            <div className="agent-preview">
              <div 
                className="preview-avatar"
                style={{ backgroundColor: selectedAvatar.color }}
              >
                <span className="preview-emoji">{selectedAvatar.svg}</span>
              </div>
              <span className="preview-name">
                {agentName || "Имя агента"}
              </span>
            </div>
          </div>

          <div className="panel-actions">
            <button type="button" className="cancel-btn" onClick={onClose} disabled={loading}>
              Отмена
            </button>
            <button 
              type="submit" 
              className="create-btn"
              disabled={!agentName.trim() || loading}
            >
              {loading ? "Создание..." : "Создать агента"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateAgentPanel;