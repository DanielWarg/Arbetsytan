import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Folder, Sun, Moon } from 'lucide-react'
import './Sidebar.css'

function Sidebar({ darkMode, toggleTheme }) {
  const location = useLocation()

  const NavItem = ({ to, icon: Icon, label }) => {
    const isActive = location.pathname === to || (to === '/projects' && location.pathname.startsWith('/projects'))
    return (
      <Link
        to={to}
        className={`nav-item ${isActive ? 'active' : ''}`}
      >
        <Icon size={16} strokeWidth={2} />
        <span>{label}</span>
      </Link>
    )
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-dot"></div>
          <span>ARBETSYTAN</span>
        </div>
        <div className="sidebar-subtitle">REDAKTIONELLT STÖD</div>
      </div>
      
      <div className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-label">Navigation</div>
          <NavItem to="/" icon={LayoutDashboard} label="Dashboard" />
          <NavItem to="/projects" icon={Folder} label="Arbetsytan" />
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">JD</div>
          <div className="user-name">Redaktör</div>
        </div>
        <button 
          onClick={toggleTheme}
          className="theme-toggle-btn"
          aria-label="Toggle theme"
        >
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </aside>
  )
}

export default Sidebar

