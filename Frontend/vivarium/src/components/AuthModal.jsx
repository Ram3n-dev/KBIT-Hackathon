import { useState } from "react";
import "./AuthModal.css";

function AuthModal({ isOpen, onClose, onLogin, onRegister }) {
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: ""
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLoginMode) {
        // Вход
        await onLogin(formData.username, formData.password);
      } else {
        // Регистрация
        if (formData.password !== formData.confirmPassword) {
          alert("Пароли не совпадают");
          return;
        }
        await onRegister(formData.username, formData.email, formData.password);
      }
      onClose();
    } catch (error) {
      console.error("Ошибка авторизации:", error);
      alert("Ошибка при входе");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="auth-overlay">
      <div className="auth-modal">
        <div className="auth-header">
          <h2>{isLoginMode ? "Вход" : "Регистрация"}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Имя пользователя</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Введите имя"
              required
              disabled={loading}
            />
          </div>

          {!isLoginMode && (
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Введите email"
                required
                disabled={loading}
              />
            </div>
          )}

          <div className="form-group">
            <label>Пароль</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Введите пароль"
              required
              disabled={loading}
            />
          </div>

          {!isLoginMode && (
            <div className="form-group">
              <label>Подтверждение пароля</label>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Повторите пароль"
                required
                disabled={loading}
              />
            </div>
          )}

          <button 
            type="submit" 
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? "Загрузка..." : (isLoginMode ? "Войти" : "Зарегистрироваться")}
          </button>
        </form>

        <div className="auth-switch">
          {isLoginMode ? (
            <p>
              Нет аккаунта?{" "}
              <button onClick={() => setIsLoginMode(false)}>
                Зарегистрироваться
              </button>
            </p>
          ) : (
            <p>
              Уже есть аккаунт?{" "}
              <button onClick={() => setIsLoginMode(true)}>
                Войти
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthModal;