import { useState, useEffect } from "react";
import "./CreateAgentPanel.css";
import api from "../services/api";
import { avatarOptions } from "../utils/avatarMap";

function CreateAgentPanel({ isOpen, onClose, onCreateAgent }) {
  const [agentName, setAgentName] = useState("");
  const [selectedAvatar, setSelectedAvatar] = useState(avatarOptions[0]);
  const [loading, setLoading] = useState(false);
  const [avatars, setAvatars] = useState([]);

  // Загружаем список доступных аватарок с бэкенда
  useEffect(() => {
    if (isOpen) {
      loadAvatars();
    }
  }, [isOpen]);

  const loadAvatars = async () => {
    try {
      const data = await api.getAvatars();
      if (data && data.length > 0) {
        setAvatars(data);
      } else {
        // Если бэкенд не вернул аватарки, используем локальные
        setAvatars(avatarOptions);
      }
    } catch (error) {
      console.error("Ошибка загрузки аватарок:", error);
      // В случае ошибки используем локальные
      setAvatars(avatarOptions);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!agentName.trim()) return;
    
    setLoading(true);
    try {
      const newAgent = {
        name: agentName,
        avatarFile: selectedAvatar.file, // отправляем только имя файла
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
              {avatars.map((avatar) => (
                <div
                  key={avatar.id}
                  className={`avatar-option ${selectedAvatar.id === avatar.id ? 'selected' : ''}`}
                  onClick={() => setSelectedAvatar(avatar)}
                  style={{ backgroundColor: avatar.color }}
                >
                  <img src={avatar.image} alt={avatar.name} className="avatar-image" />
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
                <img 
                  src={selectedAvatar.image} 
                  alt={selectedAvatar.name}
                  className="avatar-image preview-avatar-image"
                />
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