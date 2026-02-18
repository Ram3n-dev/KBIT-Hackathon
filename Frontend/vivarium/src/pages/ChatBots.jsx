import { useState, useEffect, useRef } from "react";
import "./Pages.css";
import "./ChatBots.css";
import api from "../services/api";
import { getAvatarByFile } from "../utils/avatarMap";

function ChatBots({ isAuthenticated, onLoginClick }) {
  const [messages, setMessages] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const messagesContainerRef = useRef(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  
  const [lastMessageId, setLastMessageId] = useState(null);
  const updateIntervalRef = useRef(null);
  const isInitialLoad = useRef(true);
  const scrollPositionRef = useRef(0);
  const prevMessagesLengthRef = useRef(0);
  const messageIdsRef = useRef(new Set());

  // Загрузка данных только если авторизован
  useEffect(() => {
    if (isAuthenticated) {
      loadData();
      
      updateIntervalRef.current = setInterval(() => {
        checkForNewMessages();
      }, 3000);

      return () => {
        if (updateIntervalRef.current) {
          clearInterval(updateIntervalRef.current);
        }
      };
    } else {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const checkForNewMessages = async () => {
    try {
      const newMessages = await api.getNewChatMessages(lastMessageId);
      
      if (newMessages && newMessages.length > 0) {
        const uniqueNewMessages = newMessages.filter(msg => !messageIdsRef.current.has(msg.id));
        
        if (uniqueNewMessages.length > 0) {
          const container = messagesContainerRef.current;
          if (container) {
            scrollPositionRef.current = container.scrollTop;
          }
          
          uniqueNewMessages.forEach(msg => messageIdsRef.current.add(msg.id));
          
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages, ...uniqueNewMessages];
            if (uniqueNewMessages.length > 0) {
              setLastMessageId(uniqueNewMessages[uniqueNewMessages.length - 1].id);
            }
            return updatedMessages;
          });
        }
      }
    } catch (error) {
      console.error("Ошибка проверки новых сообщений:", error);
    }
  };

  // Восстанавливаем позицию скролла после добавления сообщений
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container && !isInitialLoad.current) {
      if (messages.length > prevMessagesLengthRef.current) {
        if (!shouldAutoScroll) {
          requestAnimationFrame(() => {
            if (container) {
              container.scrollTop = scrollPositionRef.current;
            }
          });
        }
      }
    }
    prevMessagesLengthRef.current = messages.length;
  }, [messages, shouldAutoScroll]);

  useEffect(() => {
    if (!loading && messages.length > 0) {
      if (isInitialLoad.current) {
        const savedScrollPosition = sessionStorage.getItem('chatScrollPosition');
        if (savedScrollPosition) {
          const container = messagesContainerRef.current;
          if (container) {
            requestAnimationFrame(() => {
              if (container) {
                container.scrollTop = parseInt(savedScrollPosition);
                const { scrollTop, scrollHeight, clientHeight } = container;
                const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
                setShouldAutoScroll(isAtBottom);
              }
            });
          }
        }
        isInitialLoad.current = false;
      }
    }
  }, [loading, messages]);

  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (container) {
      const { scrollTop, scrollHeight, clientHeight } = container;
      
      sessionStorage.setItem('chatScrollPosition', scrollTop.toString());
      scrollPositionRef.current = scrollTop;
      
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShouldAutoScroll(isAtBottom);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [agentsData, messagesData] = await Promise.all([
        api.getAgents(),
        api.getChatMessages()
      ]);
      
      setAgents(agentsData);
      
      messageIdsRef.current.clear();
      messagesData.forEach(msg => messageIdsRef.current.add(msg.id));
      
      setMessages(messagesData);
      
      if (messagesData.length > 0) {
        setLastMessageId(messagesData[messagesData.length - 1].id);
      }
      prevMessagesLengthRef.current = messagesData.length;
    } catch (error) {
      console.error("Ошибка загрузки данных:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = async () => {
    try {
      await api.clearChat();
      setMessages([]);
      setLastMessageId(null);
      messageIdsRef.current.clear();
      setShowClearConfirm(false);
      sessionStorage.removeItem('chatScrollPosition');
      setShouldAutoScroll(true);
      scrollPositionRef.current = 0;
      prevMessagesLengthRef.current = 0;
    } catch (error) {
      console.error("Ошибка очистки чата:", error);
    }
  };

  // Автоскролл при новых сообщениях
  useEffect(() => {
    if (shouldAutoScroll && messagesContainerRef.current) {
      requestAnimationFrame(() => {
        if (messagesContainerRef.current) {
          messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
      });
    }
  }, [messages, shouldAutoScroll]);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
  };

  const getAgent = (agentId) => {
    return agents.find(a => a.id === agentId);
  };

  const getMessageType = (message) => {
    // Если есть явно указанный тип, используем его
    if (message.type) {
      if (message.type === 'system') return 'system';
      if (message.type === 'event') return 'event';
      if (message.type === 'agent') return 'agent';
    }
    
    // Если нет типа, но есть agentId - это сообщение агента
    if (message.agentId) return 'agent';
    
    // Иначе это системное сообщение
    return 'system';
  };

  // Заглушка для неавторизованных пользователей
  if (!isAuthenticated) {
    return (
      <div className="content-page chat-bots-page">
        <h1>Чат ботов</h1>
        <div className="auth-required">
          <div className="auth-required-icon">💬</div>
          <h2>Доступ ограничен</h2>
          <p>Пожалуйста, авторизуйтесь, чтобы увидеть диалоги ботов</p>
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

  if (loading) {
    return <div className="content-page">Загрузка чата...</div>;
  }

  return (
    <div className="content-page chat-bots-page">
      <div className="chat-header">
        <h1>Чат ботов</h1>
        <button 
          className="clear-chat-btn"
          onClick={() => setShowClearConfirm(true)}
          title="Очистить диалог"
        >
          🗑️ Очистить чат
        </button>
      </div>
      
      <div className="chat-container">
        <div 
          className="chat-messages"
          ref={messagesContainerRef}
          onScroll={handleScroll}
        >
          {messages.length === 0 ? (
            <div className="empty-chat-message">
              <p>Чат пуст. Начните общение!</p>
            </div>
          ) : (
            messages.map((message) => {
              const messageType = getMessageType(message);
              const agent = messageType === 'agent' ? getAgent(message.agentId) : null;
              
              const index = messages.findIndex(m => m.id === message.id);
              const showAvatar = messageType === 'agent' && (index === 0 || 
                messages[index - 1]?.agentId !== message.agentId);
              
              // Системные сообщения и события (голос свыше)
              if (messageType === 'system' || messageType === 'event') {
                return (
                  <div key={message.id} className="system-message-wrapper">
                    <div className={`system-message ${messageType === 'event' ? 'event-message' : ''}`}>
                      <span className="system-icon">
                        {messageType === 'event' ? '📢' : '⚙️'}
                      </span>
                      <p>{message.text}</p>
                      <span className="system-time">{formatTime(message.timestamp)}</span>
                    </div>
                  </div>
                );
              }
              
              // Сообщения от агентов
              return (
                <div 
                  key={message.id} 
                  className={`message-wrapper ${showAvatar ? 'with-avatar' : 'without-avatar'}`}
                >
                  {showAvatar && (
                    <div 
                      className="message-avatar"
                      style={{ backgroundColor: agent?.avatarColor || "#5d6939" }}
                    >
                      <img 
                        src={getAvatarByFile(agent?.avatarFile)} 
                        alt={agent?.name}
                        className="avatar-image"
                      />
                    </div>
                  )}
                  
                  <div className="message-block">
                    {showAvatar && (
                      <div className="message-author">
                        {agent?.name || "Агент"}
                      </div>
                    )}
                    
                    <div className="message-bubble">
                      <p>{message.text}</p>
                    </div>
                  </div>

                  <div className="message-time">
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {!shouldAutoScroll && messages.length > 0 && (
          <div 
            className="new-messages-indicator"
            onClick={() => {
              const container = messagesContainerRef.current;
              if (container) {
                container.scrollTop = container.scrollHeight;
                setShouldAutoScroll(true);
              }
            }}
          >
            ↓ Новые сообщения
          </div>
        )}
      </div>

      {showClearConfirm && (
        <div className="clear-confirm-overlay">
          <div className="clear-confirm-modal">
            <h3>Очистить диалог?</h3>
            <p>Все сообщения будут безвозвратно удалены.</p>
            <div className="confirm-actions">
              <button className="confirm-cancel-btn" onClick={() => setShowClearConfirm(false)}>
                Отмена
              </button>
              <button className="confirm-clear-btn" onClick={handleClearChat}>
                Очистить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatBots;