import { useState, useEffect, useRef } from "react";
import "./Pages.css";
import "./ChatBots.css";
import api from "../services/api";

function ChatBots() {
  const [messages, setMessages] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef(null);

  // Загрузка данных
  useEffect(() => {
    loadData();
  }, []);

  // Автоскролл к новым сообщениям
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [agentsData, messagesData] = await Promise.all([
        api.getAgents(),
        api.getChatMessages() // Получаем все сообщения чата
      ]);
      setAgents(agentsData);
      setMessages(messagesData);
    } catch (error) {
      console.error("Ошибка загрузки данных:", error);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Форматирование времени
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
  };

  // Получение агента по ID
  const getAgent = (agentId) => {
    return agents.find(a => a.id === agentId);
  };

  if (loading) {
    return <div className="content-page">Загрузка чата...</div>;
  }

  return (
    <div className="content-page chat-bots-page">
      <h1>Чат ботов</h1>
      
      <div className="chat-container">
        {/* Область сообщений */}
        <div className="chat-messages">
          {messages.map((message, index) => {
            const agent = getAgent(message.agentId);
            const showAvatar = index === 0 || 
              messages[index - 1].agentId !== message.agentId;
            
            return (
              <div 
                key={message.id} 
                className={`message-wrapper ${showAvatar ? 'with-avatar' : 'without-avatar'}`}
              >
                {/* Аватар (показываем только для первого сообщения подряд от того же агента) */}
                {showAvatar && (
                  <div 
                    className="message-avatar"
                    style={{ backgroundColor: agent?.avatarColor || "#5d6939" }}
                  >
                    <span>{agent?.avatar || "🤖"}</span>
                  </div>
                )}
                
                {/* Блок сообщения */}
                <div className="message-block">
                  {/* Имя агента (только если показываем аватар) */}
                  {showAvatar && (
                    <div className="message-author">
                      {agent?.name || "Агент"}
                    </div>
                  )}
                  
                  {/* Текст сообщения (автоматически расширяется по высоте) */}
                  <div className="message-bubble">
                    <p>{message.text}</p>
                  </div>
                </div>

                {/* Время сообщения (всегда справа) */}
                <div className="message-time">
                  {formatTime(message.timestamp)}
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  );
}

export default ChatBots;