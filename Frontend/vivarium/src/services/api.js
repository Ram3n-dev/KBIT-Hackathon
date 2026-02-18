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

  async fetchWithError(url, options = {}) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          this.token = null;
          window.location.reload();
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

  // ============= АВАТАРКИ =============
  async getAvatars() {
    return this.fetchWithError(`${API_URL}/avatars`, {
      headers: this.getHeaders(),
    });
  }

  // ============= АВТОРИЗАЦИЯ =============

  async login(username, password) {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (response.ok) {
      this.setToken(data.access_token);
      const userData = {
        id: data.user.id,
        name: data.user.username,
        email: data.user.email,
        avatarUrl: data.user.avatarUrl || null,
      };
      localStorage.setItem("user", JSON.stringify(userData));
      return {
        token: data.access_token,
        user: userData,
      };
    }
    throw new Error(data.message || "Ошибка входа");
  }

  async register(username, email, password) {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await response.json();
    if (response.ok) {
      this.setToken(data.access_token);
      const userData = {
        id: data.user.id,
        name: data.user.username,
        email: data.user.email,
        avatarUrl: data.user.avatarUrl || null,
      };
      localStorage.setItem("user", JSON.stringify(userData));
      return {
        token: data.access_token,
        user: userData,
      };
    }
    throw new Error(data.message || "Ошибка регистрации");
  }

  async getProfile() {
    return this.fetchWithError(`${API_URL}/auth/profile`, {
      headers: this.getHeaders(),
    });
  }

  async logout() {
    return this.fetchWithError(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: this.getHeaders(),
    });
  }

  // ============= АГЕНТЫ =============

  async getAgents() {
    return this.fetchWithError(`${API_URL}/agents`, {
      headers: this.getHeaders(),
    });
  }

  async getAgentById(id) {
    return this.fetchWithError(`${API_URL}/agents/${id}`, {
      headers: this.getHeaders(),
    });
  }

  async createAgent(agentData) {
    return this.fetchWithError(`${API_URL}/agents`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(agentData),
    });
  }

  async updateAgent(id, agentData) {
    return this.fetchWithError(`${API_URL}/agents/${id}`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(agentData),
    });
  }

  async deleteAgent(agentId) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
  }

  // ============= ОТНОШЕНИЯ =============

  async getRelations() {
    return this.fetchWithError(`${API_URL}/relations`, {
      headers: this.getHeaders(),
    });
  }

  async getAgentRelations(agentId) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/relations`, {
      headers: this.getHeaders(),
    });
  }

  async createRelation(relationData) {
    return this.fetchWithError(`${API_URL}/relations`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(relationData),
    });
  }

  async updateRelation(id, relationData) {
    return this.fetchWithError(`${API_URL}/relations/${id}`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(relationData),
    });
  }

  async deleteRelation(id) {
    return this.fetchWithError(`${API_URL}/relations/${id}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
  }

  // ============= НАСТРОЕНИЕ =============

  async getAgentMood(agentId) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/mood`, {
      headers: this.getHeaders(),
    });
  }

  async updateAgentMood(agentId, moodData) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/mood`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(moodData),
    });
  }

  // ============= ПЛАНЫ И РЕФЛЕКСИЯ =============

  async getAgentPlans(agentId) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/plans`, {
      headers: this.getHeaders(),
    });
  }

  async createAgentPlan(agentId, planData) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/plans`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(planData),
    });
  }

  async getAgentReflection(agentId) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/reflection`, {
      headers: this.getHeaders(),
    });
  }

  async updateAgentReflection(agentId, reflectionData) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/reflection`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(reflectionData),
    });
  }

  // ============= СОБЫТИЯ =============

  async getEvents() {
    return this.fetchWithError(`${API_URL}/events`, {
      headers: this.getHeaders(),
    });
  }

  async createEvent(eventData) {
    return this.fetchWithError(`${API_URL}/events`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        text: eventData.text,
        type: 'event' // Явно указываем тип 'event'
      }),
    });
  }

  // ============= СООБЩЕНИЯ =============

  async sendMessage(messageData) {
    return this.fetchWithError(`${API_URL}/messages`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(messageData),
    });
  }

  async getMessages(agentId) {
    return this.fetchWithError(`${API_URL}/agents/${agentId}/messages`, {
      headers: this.getHeaders(),
    });
  }

  // ============= ЧАТ (ОБЩИЙ) =============

  async getChatMessages(limit = 50) {
    const data = await this.fetchWithError(`${API_URL}/chat/messages?limit=${limit}`, {
      headers: this.getHeaders(),
    });
    
    // Добавляем поле type, если его нет
    return data.map(msg => ({
      ...msg,
      type: msg.type || (msg.agentId ? 'agent' : 'system')
    }));
  }

  async sendChatMessage(messageData) {
    return this.fetchWithError(`${API_URL}/chat/messages`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(messageData),
    });
  }

  async clearChat() {
    return this.fetchWithError(`${API_URL}/chat/clear`, {
      method: "POST",
      headers: this.getHeaders(),
    });
  }

  async getNewChatMessages(lastMessageId) {
    const url = lastMessageId
      ? `${API_URL}/chat/messages?after=${lastMessageId}`
      : `${API_URL}/chat/messages`;

    const data = await this.fetchWithError(url, {
      headers: this.getHeaders(),
    });
    
    // Добавляем поле type, если его нет
    return data.map(msg => ({
      ...msg,
      type: msg.type || (msg.agentId ? 'agent' : 'system')
    }));
  }

  // ============= СКОРОСТЬ ВРЕМЕНИ =============

  async getTimeSpeed() {
    return this.fetchWithError(`${API_URL}/time-speed`, {
      headers: this.getHeaders(),
    });
  }

  async setTimeSpeed(speed) {
    return this.fetchWithError(`${API_URL}/time-speed`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify({ speed }),
    });
  }
}

export default new ApiService();