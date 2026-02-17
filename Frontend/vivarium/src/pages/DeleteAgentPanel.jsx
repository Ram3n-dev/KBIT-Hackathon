import { useState } from "react";
import "./DeleteAgentPanel.css";
import api from "../services/api";

function DeleteAgentPanel({ isOpen, onClose, onDeleteAgent, agents }) {
  const [selectedAgent, setSelectedAgent] = useState("");
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!selectedAgent) return;
    
    setLoading(true);
    try {
      await onDeleteAgent(selectedAgent);
    } catch (error) {
      console.error("Ошибка удаления:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="delete-agent-overlay">
      <div className="delete-agent-panel">
        <div className="panel-header">
          <h2>Удаление агента</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="delete-content">
          <p>Выберите агента для удаления:</p>
          
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

          {selectedAgent && (
            <div className="warning-message">
              <p>⚠️ Внимание! Удаление агента приведет к потере всех данных о нем.</p>
            </div>
          )}

          <div className="panel-actions">
            <button type="button" className="cancel-btn" onClick={onClose} disabled={loading}>
              Отмена
            </button>
            <button 
              type="button" 
              className="delete-btn"
              onClick={handleDelete}
              disabled={!selectedAgent || loading}
            >
              {loading ? "Удаление..." : "Удалить агента"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DeleteAgentPanel;