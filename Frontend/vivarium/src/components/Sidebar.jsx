import { NavLink } from 'react-router-dom';
import './Sidebar.css';
import logo from '../img/logo.svg';
import user from '../img/user.svg';

function Sidebar() {
  return (
    <aside className="sidebar">
      <NavLink to="/" className="logo">
        <img src={logo} alt="Логотип" />
      </NavLink>

      <div className="container-buttons">
        <NavLink 
          to="/chat-bots" 
          className={({ isActive }) => isActive ? 'nav-btn active' : 'nav-btn'}
        >
          чат ботов
        </NavLink>
        
        <NavLink 
          to="/graph-relations" 
          className={({ isActive }) => isActive ? 'nav-btn active' : 'nav-btn'}
        >
          граф отношений
        </NavLink>
        
        <NavLink 
          to="/agent-inspector" 
          className={({ isActive }) => isActive ? 'nav-btn active' : 'nav-btn'}
        >
          инспектор агента
        </NavLink>
        
        <NavLink 
          to="/dashboard" 
          className={({ isActive }) => isActive ? 'nav-btn active' : 'nav-btn'}
        >
          панель управления
        </NavLink>

        <NavLink to="/profile" className="user">
          <img src={user} alt="Пользователь" />
        </NavLink>
      </div>
    </aside>
  );
}

export default Sidebar;