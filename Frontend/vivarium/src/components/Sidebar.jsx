import { NavLink } from "react-router-dom";  // убрали useState
import "./Sidebar.css";
import logo from "../img/logo.svg";
import user from "../img/user.svg";

function Sidebar({ onAddAgentClick }) {
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

        {/* Кругляшок для создания агентов */}
        <div className="user" onClick={onAddAgentClick}>
          <img src={user} alt="Создать агента" />ававава
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;