import { useState, useEffect } from "react";
import "./Pages.css";
import "./page_agentinspector.css";
import api from "../services/api";

function AgentInspector() {
  const [selectedAgent, setSelectedAgent] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [agents, setAgents] = useState([]);
  const [relations, setRelations] = useState([]);
  const [mood, setMood] = useState(null);
  const [plans, setPlans] = useState([]);
  const [reflection, setReflection] = useState("");
  const [loading, setLoading] = useState(false);

  // Загрузка списка агентов
  useEffect(() => {
    loadAgents();
  }, []);

  // Загрузка данных агента при выборе
  useEffect(() => {
    if (selectedAgent) {
      loadAgentData(selectedAgent);
    }
  }, [selectedAgent]);

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

  const selectedAgentData = agents.find(a => a.id === parseInt(selectedAgent));

  return (
    <div className="content-page inspector-page">
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
              <h3>{selectedAgentData?.name}</h3>
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