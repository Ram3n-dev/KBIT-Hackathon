import { useState, useRef, useEffect } from "react";
import "./Pages.css";
import "./page_GraphRelations.css";
import api from "../services/api";

function GraphRelations() {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [hoveredRelation, setHoveredRelation] = useState(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [agents, setAgents] = useState([]);
  const [relations, setRelations] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const graphRef = useRef(null);

  // Загрузка данных
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [agentsData, relationsData] = await Promise.all([
        api.getAgents(),
        api.getRelations()
      ]);
      
      // Преобразуем координаты для отображения
      const positionedAgents = agentsData.map((agent, index) => ({
        ...agent,
        x: 150 + (index % 3) * 200,
        y: 100 + Math.floor(index / 3) * 150
      }));
      
      setAgents(positionedAgents);
      setRelations(relationsData);
    } catch (error) {
      console.error("Ошибка загрузки данных:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.2, 3));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.2, 0.5));
  };

  const handleReset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e) => {
    if (e.button === 0) {
      e.preventDefault();
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      e.preventDefault();
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = (e) => {
    if (e.button === 0) {
      setIsDragging(false);
    }
  };

  const getRelationColor = (value) => {
    if (value >= 0.7) return "#4CAF50";
    if (value >= 0.4) return "#FFC107";
    return "#F44336";
  };

  const getStrokeWidth = (value) => {
    return 2 + value * 3;
  };

  if (loading) {
    return <div className="content-page">Загрузка графа...</div>;
  }

  return (
    <div className="content-page graph-page">
      <h1>Граф отношений</h1>
      
      <div className="graph-container">
        <div 
          className="graph-wrapper"
          ref={graphRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={() => setIsDragging(false)}
          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
        >
          <div 
            className="graph-zoom-container"
            style={{
              transform: `scale(${scale}) translate(${position.x / scale}px, ${position.y / scale}px)`,
              transformOrigin: 'center',
              transition: isDragging ? 'none' : 'transform 0.1s ease'
            }}
          >
            <svg 
              className="relations-graph" 
              viewBox="0 0 600 650"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Рисуем ребра */}
              {relations.map((rel, index) => {
                const fromAgent = agents.find(a => a.id === rel.from);
                const toAgent = agents.find(a => a.id === rel.to);
                if (!fromAgent || !toAgent) return null;
                
                const isHovered = hoveredRelation === index;
                const color = getRelationColor(rel.value);
                
                return (
                  <g key={index}>
                    <line
                      x1={fromAgent.x}
                      y1={fromAgent.y}
                      x2={toAgent.x}
                      y2={toAgent.y}
                      stroke={color}
                      strokeWidth={isHovered ? getStrokeWidth(rel.value) + 2 : getStrokeWidth(rel.value)}
                      opacity={isHovered ? 1 : 0.8}
                      className="relation-line"
                      onMouseEnter={() => setHoveredRelation(index)}
                      onMouseLeave={() => setHoveredRelation(null)}
                    />
                    
                    {isHovered && (
                      <text
                        x={(fromAgent.x + toAgent.x) / 2}
                        y={(fromAgent.y + toAgent.y) / 2 - 10}
                        textAnchor="middle"
                        className="relation-value"
                      >
                        {Math.round(rel.value * 100)}%
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Рисуем узлы */}
              {agents.map(agent => (
                <g key={agent.id}>
                  <circle
                    cx={agent.x}
                    cy={agent.y}
                    r={selectedAgent === agent.id ? 25 : 20}
                    fill="#5d6939"
                    stroke="#f1e8c7"
                    strokeWidth={selectedAgent === agent.id ? 4 : 2}
                    className="agent-node"
                    onMouseEnter={() => setSelectedAgent(agent.id)}
                    onMouseLeave={() => setSelectedAgent(null)}
                  />
                  
                  <text
                    x={agent.x}
                    y={agent.y + 30}
                    textAnchor="middle"
                    className="agent-label"
                    fill="#454135"
                  >
                    {agent.name}
                  </text>
                </g>
              ))}
            </svg>
          </div>

          <div className="zoom-controls">
            <button onClick={handleZoomIn} className="zoom-btn">+</button>
            <button onClick={handleZoomOut} className="zoom-btn">−</button>
            <button onClick={handleReset} className="zoom-btn reset">⟲</button>
          </div>
        </div>

        <div className="graph-legend">
          <h3>Легенда</h3>
          
          <div className="legend-items">
            <div className="legend-item">
              <div className="legend-color" style={{ background: "#4CAF50" }}></div>
              <div className="legend-text">
                <span className="legend-title">Эмпатия</span>
                <span className="legend-percent">70-100%</span>
              </div>
            </div>

            <div className="legend-item">
              <div className="legend-color" style={{ background: "#FFC107" }}></div>
              <div className="legend-text">
                <span className="legend-title">Нейтралитет</span>
                <span className="legend-percent">40-69%</span>
              </div>
            </div>

            <div className="legend-item">
              <div className="legend-color" style={{ background: "#F44336" }}></div>
              <div className="legend-text">
                <span className="legend-title">Антипатия</span>
                <span className="legend-percent">0-39%</span>
              </div>
            </div>
          </div>

          <div className="legend-note">
            <p>• Толщина линии = сила симпатии</p>
            <p>• Наведите на линию для процента</p>
            <p>• Зажмите ЛКМ для перемещения</p>
            <p>• Кнопки +/– для масштабирования</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GraphRelations;