import { Link } from "react-router-dom";
import { Search, BarChart3, ArrowRight, Sparkles } from "lucide-react";

const features = [
  {
    icon: Search,
    title: "Búsqueda Avanzada",
    description: "Encuentra las ofertas que mejor encajan con tu perfil. Sube tu CV o describe tu experiencia.",
    path: "/search",
    color: "var(--terracotta)"
  },
  {
    icon: BarChart3,
    title: "Skills Demandadas",
    description: "Identifica las competencias y jobs más buscados por las empresas con datos reales.",
    path: "/skills",
    color: "var(--terracotta)"
  }
];

export default function HomePage() {
  return (
    <div data-testid="home-page">
      <section className="relative overflow-hidden" style={{ backgroundColor: "var(--parchment)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <div
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-sans mb-6 opacity-0 animate-fade-in-up"
              style={{
                backgroundColor: "rgba(201,100,66,0.08)",
                color: "var(--terracotta)",
                fontWeight: 500,
                letterSpacing: "0.12px"
              }}
            >
              <Sparkles size={14} />
              Inteligencia laboral impulsada por IA
            </div>
            <h1
              className="font-serif opacity-0 animate-fade-in-up stagger-1"
              style={{
                fontSize: "clamp(2.5rem, 5vw, 4rem)",
                fontWeight: 500,
                lineHeight: 1.1,
                color: "var(--near-black)",
                marginBottom: "1.5rem"
              }}
            >
              Tu brújula en el mercado laboral
            </h1>
            <p
              className="font-sans opacity-0 animate-fade-in-up stagger-2"
              style={{
                fontSize: "1.25rem",
                lineHeight: 1.6,
                color: "var(--olive-gray)",
                maxWidth: "560px",
                margin: "0 auto 2.5rem"
              }}
            >
              Descubre tendencias, compara ofertas y toma decisiones con información estructurada del mercado.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center opacity-0 animate-fade-in-up stagger-3">
              <Link
                to="/search"
                data-testid="hero-search-btn"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-base no-underline font-sans"
                style={{
                  backgroundColor: "var(--terracotta)",
                  color: "var(--ivory)",
                  fontWeight: 500,
                  boxShadow: "0px 0px 0px 1px var(--terracotta)"
                }}
              >
                <Search size={18} />
                Buscar Empleo
              </Link>
              <Link
                to="/skills"
                data-testid="hero-skills-btn"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-base no-underline font-sans"
                style={{
                  backgroundColor: "var(--warm-sand)",
                  color: "var(--charcoal-warm)",
                  fontWeight: 500,
                  boxShadow: "0px 0px 0px 1px var(--ring-warm)"
                }}
              >
                <BarChart3 size={18} />
                Explorar Tendencias
              </Link>
            </div>
          </div>
        </div>
        <div className="absolute top-0 right-0 w-64 h-64 rounded-full opacity-[0.04]" style={{ background: "var(--terracotta)", filter: "blur(80px)" }} />
        <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full opacity-[0.03]" style={{ background: "var(--terracotta)", filter: "blur(60px)" }} />
      </section>

      <section style={{ backgroundColor: "var(--near-black)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-28">
          <div className="text-center mb-16">
            <h2
              className="font-serif mb-4"
              style={{ fontSize: "clamp(1.75rem, 3.5vw, 3.25rem)", fontWeight: 500, lineHeight: 1.2, color: "var(--ivory)" }}
            >
              Herramientas para decisiones informadas
            </h2>
            <p className="font-sans text-base max-w-lg mx-auto" style={{ color: "var(--warm-silver)", lineHeight: 1.6 }}>
              Dos perspectivas clave del mercado laboral en una sola plataforma.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {features.map((feature, i) => (
              <Link
                key={feature.title}
                to={feature.path}
                data-testid={`feature-card-${i}`}
                className="group block p-6 rounded-2xl no-underline transition-all duration-300 opacity-0 animate-fade-in-up"
                style={{
                  backgroundColor: "var(--dark-surface)",
                  border: "1px solid var(--border-dark)",
                  animationDelay: `${i * 0.1}s`,
                  animationFillMode: "forwards"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(201,100,66,0.3)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-dark)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                  style={{ backgroundColor: "rgba(201,100,66,0.12)" }}
                >
                  <feature.icon size={20} style={{ color: "var(--coral)" }} />
                </div>
                <h3 className="font-serif mb-2" style={{ fontSize: "1.3rem", fontWeight: 500, color: "var(--ivory)", lineHeight: 1.2 }}>
                  {feature.title}
                </h3>
                <p className="font-sans text-sm mb-4" style={{ color: "var(--warm-silver)", lineHeight: 1.6 }}>
                  {feature.description}
                </p>
                <span className="inline-flex items-center gap-1 text-sm font-sans" style={{ color: "var(--coral)", fontWeight: 500 }}>
                  Explorar <ArrowRight size={14} />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section style={{ backgroundColor: "var(--parchment)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "619", label: "Ofertas analizadas" },
              { value: "10", label: "Top resultados" },
              { value: "2", label: "Casos de uso activos" },
              { value: "24/7", label: "Datos disponibles" }
            ].map((stat, i) => (
              <div key={stat.label} data-testid={`stat-${i}`} className="text-center">
                <div className="font-serif mb-1" style={{ fontSize: "clamp(2rem, 3vw, 2.5rem)", fontWeight: 500, color: "var(--terracotta)", lineHeight: 1.1 }}>
                  {stat.value}
                </div>
                <div className="font-sans text-sm" style={{ color: "var(--stone-gray)" }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
