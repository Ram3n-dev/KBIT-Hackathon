const API_URL = 'http://localhost:8000'; // замените на ваш URL бэкенда

class ApiService {
  // Агенты
  async getAgents() {
    const response = await fetch(`${API_URL}/agents`);
    return response.json();
  }

  async createAgent(agentData) {
    const response = await fetch(`${API_URL}/agents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(agentData),
    });
    return response.json();
  }

  async getAgentById(id) {
    const response = await fetch(`${API_URL}/agents/${id}`);
    return response.json();
  }

  // Отношения между агентами
  async getRelations() {
    const response = await fetch(`${API_URL}/relations`);
    return response.json();
  }

  async getAgentRelations(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/relations`);
    return response.json();
  }

  // Настроение агента
  async getAgentMood(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/mood`);
    return response.json();
  }

  // Планы и рефлексия
  async getAgentPlans(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/plans`);
    return response.json();
  }

  async getAgentReflection(agentId) {
    const response = await fetch(`${API_URL}/agents/${agentId}/reflection`);
    return response.json();
  }

  // События
  async createEvent(eventData) {
    const response = await fetch(`${API_URL}/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(eventData),
    });
    return response.json();
  }

  // Сообщения
  async sendMessage(messageData) {
    const response = await fetch(`${API_URL}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(messageData),
    });
    return response.json();
  }

  // Скорость времени
  async setTimeSpeed(speed) {
    const response = await fetch(`${API_URL}/time-speed`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ speed }),
    });
    return response.json();
  }

  async getTimeSpeed() {
    const response = await fetch(`${API_URL}/time-speed`);
    return response.json();
  }
}

export default new ApiService();