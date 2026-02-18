import { useState, useEffect } from "react";
import "./Pages.css";
import "./AgentInspector.css";
import api from "../services/api";
import { avatarOptions, getAvatarByFile } from "../utils/avatarMap";

function AgentInspector({ isAuthenticated, onLoginClick }) {
  const [selectedAgent, setSelectedAgent] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [agents, setAgents] = useState([]);
  const [relations, setRelations] = useState([]);
  const [mood, setMood] = useState(null);
  const [plans, setPlans] = useState([]);
  const [reflection, setReflection] = useState("");
  const [loading, setLoading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedName, setEditedName] = useState("");
  const [selectedAvatar, setSelectedAvatar] = useState(null);

  // Загрузка списка агентов
  useEffect(() => {
    if (isAuthenticated) {
      loadAgents();
    }
  }, [isAuthenticated]);

  // Загрузка данных агента при выборе
  useEffect(() => {
    if (selectedAgent && agents.length > 0) {
      loadAgentData(selectedAgent);
      const agent = agents.find(a => a.id === parseInt(selectedAgent));
      if (agent) {
        setEditedName(agent.name);
        // Находим соответствующий аватар по имени файла
        const avatar = avatarOptions.find(a => a.file === agent.avatarFile);
        setSelectedAvatar(avatar || avatarOptions[0]);
      }
    }
  }, [selectedAgent, agents]);

  const loadAgents = async () => {
    try {
      const data = await api.getAgents();
      setAgents(data);
    } catch (error) {
      console.error("Ошибка загрузки агентов:", error);
    }
  };

  const loadAgentData = async (agentId) => {
    setLoading(true);
    try {
      const [relationsData, moodData, plansData, reflectionData] = await Promise.all([
        api.getAgentRelations(agentId),
        api.getAgentMood(agentId),
        api.getAgentPlans(agentId),
        api.getAgentReflection(agentId)
      ]);
      
      setRelations(relationsData);
      setMood(moodData);
      setPlans(plansData);
      setReflection(reflectionData);
    } catch (error) {
      console.error("Ошибка загрузки данных агента:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setIsEditMode(true);
  };

  const handleSave = async () => {
    try {
      await api.updateAgent(parseInt(selectedAgent), {
        name: editedName,
        avatarFile: selectedAvatar.file,
        avatarColor: selectedAvatar.color
      });
      setIsEditMode(false);
      loadAgents();
    } catch (error) {
      console.error("Ошибка сохранения:", error);
    }
  };

  const handleCancel = () => {
    setIsEditMode(false);
    const agent = agents.find(a => a.id === parseInt(selectedAgent));
    if (agent) {
      setEditedName(agent.name);
      const avatar = avatarOptions.find(a => a.file === agent.avatarFile);
      setSelectedAvatar(avatar || avatarOptions[0]);
    }
  };

  const selectedAgentData = agents.find(a => a.id === parseInt(selectedAgent));

  // Заглушка для неавторизованных пользователей
  if (!isAuthenticated) {
    return (
      <div className="content-page inspector-page">
        <h1>Инспектор агента</h1>
        <div className="auth-required">
          <div className="auth-required-icon">🔍</div>
          <h2>Доступ ограничен</h2>
          <p>Пожалуйста, авторизуйтесь, чтобы инспектировать агентов</p>
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
    <div className="content-page inspector-page">
      <h1>Инспектор агента</h1>
      <div className="inspector-container">
        {/* Выпадающий список агентов */}
        <div className="inspector-select-section">
          <h2>выберите агента для инспекции</h2>
          
          <div className="custom-select">
            <div 
              className="select-selected"
              onClick={() => setIsOpen(!isOpen)}
            >
              {selectedAgentData ? selectedAgentData.name : 'Выберите агента'}
            </div>
            
            {isOpen && (
              <div className="select-items">
                {agents.map((agent) => (
                  <div
                    key={agent.id}
                    className={`select-item ${selectedAgent === agent.id.toString() ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedAgent(agent.id.toString());
                      setIsOpen(false);
                    }}
                  >
                    {agent.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Информация об агенте */}
        {selectedAgent && !loading && (
          <div className="agent-info-panel">
            <div className="agent-name-header">
              {isEditMode ? (
                <div className="edit-mode">
                  <input
                    type="text"
                    className="edit-name-input"
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    placeholder="Имя агента"
                  />
                  
                  <div className="avatar-selector">
                    <h4>Выберите аватар:</h4>
                    <div className="avatar-grid-small">
                      {avatarOptions.map((avatar) => (
                        <div
                          key={avatar.id}
                          className={`avatar-option-small ${selectedAvatar?.id === avatar.id ? 'selected' : ''}`}
                          onClick={() => setSelectedAvatar(avatar)}
                          style={{ backgroundColor: avatar.color }}
                        >
                          <img 
                            src={avatar.image} 
                            alt={avatar.name}
                            className="avatar-option-image"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="edit-actions">
                    <button className="save-btn" onClick={handleSave}>Сохранить</button>
                    <button className="cancel-btn" onClick={handleCancel}>Отмена</button>
                  </div>
                </div>
              ) : (
                <div className="view-mode">
                  {/* Аватарка слева от имени */}
                  <div 
                    className="agent-header-avatar"
                    style={{ backgroundColor: selectedAgentData?.avatarColor || "#5d6939" }}
                  >
                    <img 
                      src={getAvatarByFile(selectedAgentData?.avatarFile)} 
                      alt={selectedAgentData?.name}
                      className="avatar-image"
                    />
                  </div>
                  <h3>{selectedAgentData?.name}</h3>
                  <button className="edit-agent-btn" onClick={handleEdit} title="Редактировать агента">
                    ✎
                  </button>
                </div>
              )}
            </div>

            {/* Отношения к другим агентам */}
            <div className="relationships-section">
              <h4>Отношения к другим агентам:</h4>
              <div className="relationships-list">
                {relations.map(rel => (
                  <div key={rel.id} className="relationship-item">
                    <span className="agent-name">{rel.target_name}</span>
                    <span 
                      className="relationship-type"
                      style={{ 
                        backgroundColor: rel.color,
                        color: "#454135"
                      }}
                    >
                      {rel.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Настроение агента */}
            {mood && (
              <div className="mood-section">
                <h4>Настроение:</h4>
                <div className="mood-display">
                  <span className="mood-emoji">{mood.emoji}</span>
                  <span 
                    className="mood-text"
                    style={{ color: mood.color }}
                  >
                    {mood.text}
                  </span>
                </div>
              </div>
            )}

            {/* Планы на будущее */}
            <div className="future-plans-section">
              <h4>Планы на будущее:</h4>
              <ul className="plans-list">
                {plans.map((plan, index) => (
                  <li key={index} className="plan-item">{plan.text}</li>
                ))}
              </ul>
            </div>

            {/* Рефлексия */}
            {reflection && (
              <div className="reflection-section">
                <h4>Рефлексия:</h4>
                <div className="thought-bubble">
                  <p>{reflection}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {loading && <div className="loading">Загрузка...</div>}
      </div>
    </div>
  );
}

export default AgentInspector;