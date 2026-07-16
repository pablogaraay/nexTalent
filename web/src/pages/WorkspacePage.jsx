import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bell,
  Bookmark,
  BriefcaseBusiness,
  CheckCircle2,
  Compass,
  ExternalLink,
  FileUser,
  MapPin,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";

import { useWorkspace } from "@/context/WorkspaceContext";

const APPLICATION_STATUS = {
  preparing: "Preparando candidatura",
  applied: "Candidatura enviada",
  interview: "Entrevista",
  offer: "Oferta recibida",
  rejected: "Proceso cerrado",
};

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

export default function WorkspacePage() {
  const {
    workspace,
    toggleSavedOffer,
    updateApplication,
    addAlert,
    updateAlert,
    removeAlert,
    clearWorkspace,
  } = useWorkspace();
  const [alertRole, setAlertRole] = useState("");
  const [alertLocation, setAlertLocation] = useState("");

  const profile = workspace.profile.parsed || {};
  const profileSkills = profile.skills || [];
  const stats = [
    { label: "Ofertas guardadas", value: workspace.savedOffers.length, icon: Bookmark },
    { label: "Planes activos", value: workspace.careerPlans.length, icon: Compass },
    { label: "Candidaturas", value: workspace.applications.length, icon: BriefcaseBusiness },
    { label: "Alertas activas", value: workspace.alerts.filter((item) => item.active).length, icon: Bell },
  ];

  const planProgress = useMemo(() => workspace.careerPlans.map((plan) => {
    const actions = (plan.plan?.tracks || []).flatMap((track) =>
      (track.phases || []).flatMap((phase) => phase.actions || []),
    );
    const completed = Object.values(workspace.planProgress[plan.id] || {}).filter(Boolean).length;
    return { plan, total: actions.length, completed };
  }), [workspace.careerPlans, workspace.planProgress]);

  const handleAddAlert = (event) => {
    event.preventDefault();
    if (!alertRole.trim()) return;
    addAlert({ role: alertRole.trim(), location: alertLocation.trim() });
    setAlertRole("");
    setAlertLocation("");
  };

  const handleClear = () => {
    if (window.confirm("¿Eliminar todo tu espacio personal de este dispositivo? Esta acción no se puede deshacer.")) {
      clearWorkspace();
    }
  };

  return (
    <div data-testid="workspace-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5 mb-9">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs mb-4" style={{ color: "var(--terracotta)", backgroundColor: "rgba(201,100,66,0.08)", fontWeight: 600 }}>
              <UserRound size={14} /> Datos guardados en este dispositivo
            </div>
            <h1 className="font-serif mb-2" style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)", color: "var(--near-black)", fontWeight: 500 }}>Mi espacio profesional</h1>
            <p className="text-base" style={{ color: "var(--olive-gray)" }}>Tu perfil, oportunidades, planes y candidaturas en un único lugar.</p>
          </div>
          <Link to="/privacy" className="inline-flex items-center gap-2 text-sm" style={{ color: "var(--terracotta)", fontWeight: 600 }}><ShieldCheck size={16} /> Privacidad y datos</Link>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          {stats.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-xl p-4" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
              <Icon size={17} style={{ color: "var(--terracotta)" }} />
              <div className="font-serif text-2xl mt-2" style={{ color: "var(--near-black)" }}>{value}</div>
              <div className="text-xs" style={{ color: "var(--stone-gray)" }}>{label}</div>
            </div>
          ))}
        </div>

        <section className="rounded-2xl p-6 mb-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
            <div className="flex items-center gap-3"><FileUser size={20} style={{ color: "var(--terracotta)" }} /><div><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Perfil profesional</h2><p className="text-xs" style={{ color: "var(--stone-gray)" }}>{workspace.profile.updatedAt ? `Actualizado ${formatDate(workspace.profile.updatedAt)}` : "Todavía no has analizado tu perfil"}</p></div></div>
            <Link to="/search" className="px-3 py-2 rounded-lg text-sm" style={{ backgroundColor: "var(--warm-sand)", color: "var(--near-black)", fontWeight: 600 }}>{workspace.profile.updatedAt ? "Actualizar perfil" : "Crear perfil"}</Link>
          </div>
          {workspace.profile.updatedAt ? (
            <div className="grid md:grid-cols-3 gap-4">
              <div><span className="text-xs uppercase" style={{ color: "var(--stone-gray)" }}>Rol principal</span><p className="mt-1" style={{ color: "var(--near-black)", fontWeight: 600 }}>{profile.role || "No identificado"}</p></div>
              <div><span className="text-xs uppercase" style={{ color: "var(--stone-gray)" }}>Ubicación</span><p className="mt-1 flex items-center gap-1" style={{ color: "var(--near-black)", fontWeight: 600 }}><MapPin size={14} />{profile.location_query || "Sin preferencia"}</p></div>
              <div><span className="text-xs uppercase" style={{ color: "var(--stone-gray)" }}>Origen</span><p className="mt-1" style={{ color: "var(--near-black)", fontWeight: 600 }}>{workspace.profile.cvName || "Descripción de perfil"}</p></div>
              <div className="md:col-span-3 flex flex-wrap gap-2">{profileSkills.map((skill) => <span key={skill} className="px-2.5 py-1 rounded-full text-xs" style={{ backgroundColor: "rgba(201,100,66,0.08)", color: "var(--terracotta)" }}>{skill}</span>)}</div>
            </div>
          ) : <p className="text-sm" style={{ color: "var(--olive-gray)" }}>Analiza una descripción o CV una sola vez y nexTalent reutilizará el perfil en el resto de herramientas.</p>}
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
          <section className="rounded-2xl p-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <div className="flex items-center justify-between mb-5"><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Ofertas guardadas</h2><Link to="/search" className="text-sm" style={{ color: "var(--terracotta)", fontWeight: 600 }}>Descubrir</Link></div>
            {workspace.savedOffers.length ? <div className="space-y-3">{workspace.savedOffers.slice(0, 6).map((offer) => (
              <article key={offer.id} className="rounded-xl p-4" style={{ backgroundColor: "var(--parchment)" }}>
                <div className="flex items-start justify-between gap-3"><div><h3 className="font-serif text-lg" style={{ color: "var(--near-black)" }}>{offer.title}</h3><p className="text-xs" style={{ color: "var(--olive-gray)" }}>{offer.company}{offer.location ? ` · ${offer.location}` : ""}</p></div><button onClick={() => toggleSavedOffer(offer)} aria-label={`Quitar ${offer.title} de guardadas`}><Trash2 size={15} style={{ color: "var(--stone-gray)" }} /></button></div>
                <div className="flex flex-wrap gap-3 mt-3"><Link to={`/application?offerId=${encodeURIComponent(offer.id)}`} className="text-xs" style={{ color: "var(--terracotta)", fontWeight: 600 }}>Preparar candidatura</Link><Link to={`/career?targetRole=${encodeURIComponent(offer.role || offer.title)}`} className="text-xs" style={{ color: "var(--olive-gray)", fontWeight: 600 }}>Analizar brecha</Link>{offer.url && <a href={offer.url} target="_blank" rel="noopener noreferrer" className="text-xs inline-flex items-center gap-1" style={{ color: "var(--olive-gray)" }}>Original <ExternalLink size={11} /></a>}</div>
              </article>
            ))}</div> : <p className="text-sm" style={{ color: "var(--olive-gray)" }}>Guarda oportunidades desde la búsqueda para compararlas y preparar candidaturas.</p>}
          </section>

          <section className="rounded-2xl p-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <div className="flex items-center justify-between mb-5"><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Planes de carrera</h2><Link to="/career" className="text-sm" style={{ color: "var(--terracotta)", fontWeight: 600 }}>Nuevo plan</Link></div>
            {planProgress.length ? <div className="space-y-4">{planProgress.map(({ plan, completed, total }) => {
              const pct = total ? Math.round((completed / total) * 100) : 0;
              return <article key={plan.id}><div className="flex justify-between gap-3 mb-2"><div><Link to={`/career?targetRole=${encodeURIComponent(plan.target_role)}`} className="font-serif text-lg" style={{ color: "var(--near-black)" }}>{plan.target_role}</Link><p className="text-xs" style={{ color: "var(--stone-gray)" }}>Preparación inicial: {plan.readiness?.score || 0}%</p></div><span className="text-sm" style={{ color: "var(--terracotta)", fontWeight: 600 }}>{pct}%</span></div><div className="h-2 rounded-full" style={{ backgroundColor: "var(--warm-sand)" }}><div className="h-2 rounded-full" style={{ width: `${pct}%`, backgroundColor: "var(--terracotta)" }} /></div></article>;
            })}</div> : <p className="text-sm" style={{ color: "var(--olive-gray)" }}>Los planes generados se guardarán aquí junto con su progreso.</p>}
          </section>
        </div>

        <section className="rounded-2xl p-6 mb-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <div className="flex items-center justify-between mb-5"><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Candidaturas</h2><Link to="/search" className="text-sm" style={{ color: "var(--terracotta)", fontWeight: 600 }}>Añadir desde una oferta</Link></div>
          {workspace.applications.length ? <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">{workspace.applications.map((application) => (
            <article key={application.id} className="rounded-xl p-4" style={{ backgroundColor: "var(--parchment)" }}>
              <h3 className="font-serif text-lg" style={{ color: "var(--near-black)" }}>{application.offer?.title}</h3><p className="text-xs mb-3" style={{ color: "var(--olive-gray)" }}>{application.offer?.company}</p>
              <select value={application.status} onChange={(event) => updateApplication(application.id, { status: event.target.value })} className="w-full rounded-lg px-3 py-2 text-xs" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>{Object.entries(APPLICATION_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
              <Link to={`/application?offerId=${encodeURIComponent(application.offer?.id || "")}`} className="inline-flex items-center gap-1 mt-3 text-xs" style={{ color: "var(--terracotta)", fontWeight: 600 }}>Abrir kit de candidatura</Link>
            </article>
          ))}</div> : <p className="text-sm" style={{ color: "var(--olive-gray)" }}>Aún no has iniciado ninguna candidatura.</p>}
        </section>

        <section className="rounded-2xl p-6 mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <h2 className="font-serif text-2xl mb-2" style={{ color: "var(--near-black)" }}>Alertas de oportunidades</h2><p className="text-sm mb-5" style={{ color: "var(--olive-gray)" }}>Guarda criterios para reutilizarlos. Las notificaciones externas requerirán conectar posteriormente un canal de correo o mensajería.</p>
          <form onSubmit={handleAddAlert} className="grid sm:grid-cols-[1fr_1fr_auto] gap-3 mb-4"><input aria-label="Rol de la alerta" value={alertRole} onChange={(event) => setAlertRole(event.target.value)} placeholder="Rol, por ejemplo Data Engineer" className="rounded-lg px-3 py-2 text-sm" style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)" }} /><input aria-label="Ubicación de la alerta" value={alertLocation} onChange={(event) => setAlertLocation(event.target.value)} placeholder="Ubicación opcional" className="rounded-lg px-3 py-2 text-sm" style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)" }} /><button type="submit" className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm" style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)", fontWeight: 600 }}><Plus size={15} /> Crear</button></form>
          <div className="space-y-2">{workspace.alerts.map((alert) => <div key={alert.id} className="flex items-center gap-3 rounded-lg px-3 py-2" style={{ backgroundColor: "var(--parchment)" }}><input type="checkbox" checked={alert.active} onChange={(event) => updateAlert(alert.id, { active: event.target.checked })} aria-label={`Activar alerta ${alert.role}`} /><div className="flex-1"><span className="text-sm" style={{ color: "var(--near-black)", fontWeight: 600 }}>{alert.role}</span>{alert.location && <span className="text-xs ml-2" style={{ color: "var(--stone-gray)" }}>{alert.location}</span>}{alert.lastCheckedAt && <p className="text-xs" style={{ color: "var(--stone-gray)" }}>{alert.lastMatchCount || 0} coincidencias en la última búsqueda · {formatDate(alert.lastCheckedAt)}</p>}</div><button onClick={() => removeAlert(alert.id)} aria-label={`Eliminar alerta ${alert.role}`}><Trash2 size={14} style={{ color: "var(--stone-gray)" }} /></button></div>)}</div>
        </section>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl p-5" style={{ backgroundColor: "rgba(181,51,51,0.05)", border: "1px solid rgba(181,51,51,0.12)" }}><div className="flex items-start gap-3"><CheckCircle2 size={18} style={{ color: "var(--olive-gray)" }} /><div><p className="text-sm" style={{ color: "var(--near-black)", fontWeight: 600 }}>Control de tus datos</p><p className="text-xs" style={{ color: "var(--olive-gray)" }}>Esta versión guarda el espacio personal únicamente en el almacenamiento local del navegador.</p></div></div><button onClick={handleClear} className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm" style={{ color: "var(--error-crimson)", border: "1px solid rgba(181,51,51,0.2)" }}><Trash2 size={14} /> Eliminar mis datos</button></div>
      </div>
    </div>
  );
}
