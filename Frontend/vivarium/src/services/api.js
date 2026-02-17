const API_URL = "http://192.168.0.74:8000";

class ApiService {
  constructor() {
    this.token = localStorage.getItem("token");
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem("token", token);
  }

  getHeaders() {
    const headers = {
      "Content-Type": "application/json",
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  // Авторизация
  async login(username, password) {
    const response = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (response.ok) {
      this.setToken(data.token);
    }
    return data;
  }

  async register(username, email, password) {
    const response = await fetch(`${API_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await response.json();
    if (response.ok) {
      this.setToken(data.token);
    }
    return data;
  }

  async checkAuth(token) {
    const response = await fetch(`${API_URL}/check-auth`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.json();
  }

  // Агенты (требуют авторизацию)
  async getAgents() {
    const response = await fetch(`${API_URL}/agents`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  async createAgent(agentData) {
    const response = await fetch(`${API_URL}/agents`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(agentData),
    });
    return response.json();
  }

  async deleteAgent(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return response.json();
  }

  // В классе ApiService добавьте:

  // Отношения между агентами
  async getRelations() {
    const response = await fetch(`${API_URL}/relations`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  async getAgentRelations(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/relations`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  // Настроение агента
  async getAgentMood(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/mood`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  // Планы и рефлексия
  async getAgentPlans(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/plans`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  async getAgentReflection(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/reflection`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  // События
  async createEvent(eventData) {
    const response = await fetch(`${API_URL}/events`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(eventData),
    });
    return response.json();
  }

  // Сообщения
  async sendMessage(messageData) {
    const response = await fetch(`${API_URL}/messages`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(messageData),
    });
    return response.json();
  }

  // Скорость времени
  async setTimeSpeed(speed) {
    const response = await fetch(`${API_URL}/time-speed`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ speed }),
    });
    return response.json();
  }

  async getTimeSpeed() {
    const response = await fetch(`${API_URL}/time-speed`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  // Получение агента по ID
  async getAgentById(id) {
    const response = await fetch(`${API_URL}/agents/${id}`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }
  async fetchWithError(url, options = {}) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        if (response.status === 401) {
          // Неавторизован - очищаем токен
          localStorage.removeItem("token");
          this.token = null;
          window.location.reload(); // перезагружаем страницу
        }
        const error = await response.json();
        throw new Error(error.message || "Ошибка запроса");
      }
      return await response.json();
    } catch (error) {
      console.error("API Error:", error);
      throw error;
    }
  }

  // Теперь каждый метод используйте так:
  async getAgents() {
    return this.fetchWithError(`${API_URL}/agents`, {
      headers: this.getHeaders(),
    });
  }
  // В классе ApiService добавьте:

  // Чаты
  async getChats() {
    return this.fetchWithError(`${API_URL}/chats`, {
      headers: this.getHeaders(),
    });
  }

  async getChatMessages(chatId) {
    return this.fetchWithError(`${API_URL}/chats/${chatId}/messages`, {
      headers: this.getHeaders(),
    });
  }

  async sendChatMessage(messageData) {
    return this.fetchWithError(`${API_URL}/chats/messages`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(messageData),
    });
  }

  async createChat(agentId, partnerName) {
    return this.fetchWithError(`${API_URL}/chats`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ agentId, partnerName }),
    });
  }
  // В классе ApiService добавьте или обновите:

  // Получение всех сообщений чата
  async getChatMessages() {
    return this.fetchWithError(`${API_URL}/chat/messages`, {
      headers: this.getHeaders(),
    });
  }

  // Отправка сообщения в общий чат
  async sendChatMessage(messageData) {
    return this.fetchWithError(`${API_URL}/chat/messages`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(messageData),
    });
  }
}

export default new ApiService();
