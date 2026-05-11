import { useState } from "react";
import { BarChart3, Menu, Search, TrendingUp, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

const navLinks = [
  { path: "/search", label: "Buscar Empleo", icon: Search },
  { path: "/skills", label: "Mercado", icon: BarChart3 }
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <nav
      data-testid="navbar"
      className="sticky top-0 z-50 border-b"
      style={{
        backgroundColor: "var(--ivory)",
        borderColor: "var(--border-cream)",
        backdropFilter: "blur(12px)"
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" data-testid="logo-link" className="flex items-center gap-2 no-underline">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--terracotta)" }}>
              <TrendingUp size={18} color="var(--ivory)" />
            </div>
            <span className="text-xl font-serif" style={{ color: "var(--near-black)", fontWeight: 500 }}>
              nexTalent
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {navLinks.map(({ path, label, icon: Icon }) => {
              const isActive = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm no-underline transition-colors"
                  style={{
                    color: isActive ? "var(--terracotta)" : "var(--olive-gray)",
                    backgroundColor: isActive ? "rgba(201,100,66,0.08)" : "transparent",
                    fontWeight: isActive ? 500 : 400
                  }}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </div>

          <button
            className="md:hidden p-2 rounded-lg"
            style={{ color: "var(--charcoal-warm)" }}
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {mobileOpen && (
          <div className="md:hidden pb-4 animate-fade-in">
            {navLinks.map(({ path, label, icon: Icon }) => {
              const isActive = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2 px-3 py-3 rounded-lg text-sm no-underline"
                  style={{
                    color: isActive ? "var(--terracotta)" : "var(--olive-gray)",
                    backgroundColor: isActive ? "rgba(201,100,66,0.08)" : "transparent"
                  }}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </nav>
  );
}
