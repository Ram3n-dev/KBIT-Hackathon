import { NavLink } from "react-router-dom";
import "./Sidebar.css";
import logo from "../img/logo.svg";
import create from "../img/create.svg";
import deleteIcon from "../img/delete.svg";

function Sidebar({
  onAddAgentClick,
  onDeleteAgentClick,
  onLoginClick,
  onLogout,
  isAuthenticated,
  userData,
}) {
  // Функция для обрезки длинного имени
  const truncateName = (name, maxLength = 15) => {
    if (!name) return "Пользователь";
    return name.length > maxLength ? name.slice(0, maxLength) + "..." : name;
  };

  return (
    <aside className="sidebar">
      <NavLink to="/" className="logo">
        <img src={logo} alt="Логотип" />
      </NavLink>

      <div className="container-buttons">
        <NavLink
          to="/graph-relations"
          className={({ isActive }) =>
            isActive ? "nav-btn active" : "nav-btn"
          }
        >
          граф отношений
        </NavLink>
        <NavLink
          to="/chat-bots"
          className={({ isActive }) =>
            isActive ? "nav-btn active" : "nav-btn"
          }
        >
          чат ботов
        </NavLink>

        <NavLink
          to="/agent-inspector"
          className={({ isActive }) =>
            isActive ? "nav-btn active" : "nav-btn"
          }
        >
          инспектор агента
        </NavLink>

        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            isActive ? "nav-btn active" : "nav-btn"
          }
        >
          панель управления
        </NavLink>

        {/* Блок с кнопками создания и удаления в grid */}
        <div className="agent-actions-grid">
          <div
            className="action-btn create"
            onClick={onAddAgentClick}
            title="Создать агента"
          >
            <img src={create} alt="Создать" />
            <span>Создать агента</span>
          </div>

          <div
            className="action-btn delete"
            onClick={onDeleteAgentClick}
            title="Удалить агента"
          >
            <img src={deleteIcon} alt="Удалить" />
            <span>Удалить агента</span>
          </div>
        </div>
      </div>

      {/* Блок пользователя внизу */}
      <div className="user-section">
        {isAuthenticated ? (
          <div className="user-info">
            <div className="user-avatar">{userData?.avatar || "👤"}</div>
            <div className="user-details">
              <span className="user-name" title={userData?.name}>
                {truncateName(userData?.name)}
              </span>
              <span className="user-email" title={userData?.email}>
                {truncateName(userData?.email, 20)}
              </span>
            </div>
            <button className="logout-btn" onClick={onLogout}>
              Выйти
            </button>
          </div>
        ) : (
          <div className="login-prompt" onClick={onLoginClick}>
            <div className="login-icon">🔐</div>
            <div className="login-text">
              <span>Войти в аккаунт</span>
              <small>для использования функционала</small>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;