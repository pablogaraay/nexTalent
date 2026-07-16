import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Check, ClipboardList, FileText, MessageSquareText, Printer, Send, Sparkles } from "lucide-react";

import { useWorkspace } from "@/context/WorkspaceContext";

function buildCoverLetter(offer, profile) {
  const role = profile?.role || "mi experiencia profesional";
  const skills = (offer?.matched_skills || []).slice(0, 4);
  const skillText = skills.length ? ` Destacaría especialmente mi experiencia verificable en ${skills.join(", ")}.` : "";
  return `Estimado equipo de ${offer?.company || "selección"}:\n\nMe gustaría presentar mi candidatura para la posición de ${offer?.title || "la vacante publicada"}. Mi trayectoria como ${role} guarda relación con las responsabilidades del puesto.${skillText}\n\nAntes de enviar esta carta, sustituye este párrafo por un logro concreto y medible que puedas acreditar y que sea relevante para la oferta.\n\nQuedo a su disposición para ampliar cualquier información.\n\nUn saludo.`;
}

export default function ApplicationKitPage() {
  const [searchParams] = useSearchParams();
  const offerId = searchParams.get("offerId") || "";
  const { workspace, upsertApplication, updateApplication } = useWorkspace();
  const offer = workspace.savedOffers.find((item) => item.id === offerId)
    || workspace.applications.find((item) => item.offer?.id === offerId)?.offer;
  const existingApplication = workspace.applications.find((item) => item.offer?.id === offerId);
  const profile = workspace.profile.parsed || {};
  const [coverLetter, setCoverLetter] = useState(() => existingApplication?.coverLetter || (offer ? buildCoverLetter(offer, profile) : ""));
  const [saved, setSaved] = useState(false);

  const questions = useMemo(() => {
    if (!offer) return [];
    const skills = (offer.matched_skills || []).slice(0, 3);
    return [
      `¿Por qué te interesa el puesto de ${offer.title} en ${offer.company}?`,
      `Describe una situación real en la que resolviste un problema relevante para ${offer.role || offer.title}.`,
      ...skills.map((skill) => `Explica un proyecto en el que utilizaste ${skill}, tus decisiones y el resultado.`),
      "¿Qué habilidad necesitas reforzar para desempeñar mejor este puesto y cómo lo estás haciendo?",
      "¿Qué preguntas harías al equipo para valorar si esta oportunidad encaja contigo?",
    ].slice(0, 7);
  }, [offer]);

  if (!offer) {
    return <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: "var(--parchment)" }}><div className="max-w-lg text-center"><FileText size={32} style={{ color: "var(--terracotta)", margin: "0 auto 16px" }} /><h1 className="font-serif text-3xl mb-3" style={{ color: "var(--near-black)" }}>Selecciona primero una oferta</h1><p className="text-sm mb-5" style={{ color: "var(--olive-gray)" }}>Guarda una oportunidad desde la búsqueda para preparar una candidatura específica.</p><Link to="/search" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg" style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)" }}>Ir a búsqueda</Link></div></div>;
  }

  const handleSave = () => {
    upsertApplication(offer, { coverLetter, status: existingApplication?.status || "preparing" });
    if (existingApplication?.id) updateApplication(existingApplication.id, { coverLetter });
    setSaved(true);
  };

  return (
    <div data-testid="application-kit-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Link to="/workspace" className="inline-flex items-center gap-2 text-sm mb-6" style={{ color: "var(--olive-gray)" }}><ArrowLeft size={15} /> Volver a mi espacio</Link>
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-8"><div><div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs mb-3" style={{ backgroundColor: "rgba(201,100,66,0.08)", color: "var(--terracotta)", fontWeight: 600 }}><Sparkles size={14} /> Kit basado únicamente en datos verificados</div><h1 className="font-serif text-4xl mb-2" style={{ color: "var(--near-black)" }}>{offer.title}</h1><p style={{ color: "var(--olive-gray)" }}>{offer.company}{offer.location ? ` · ${offer.location}` : ""}</p></div><div className="flex gap-2"><button onClick={() => window.print()} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm" style={{ backgroundColor: "var(--warm-sand)", color: "var(--near-black)" }}><Printer size={15} /> Imprimir</button><button onClick={handleSave} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm" style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)", fontWeight: 600 }}>{saved ? <Check size={15} /> : <Send size={15} />}{saved ? "Guardado" : "Guardar candidatura"}</button></div></div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="rounded-2xl p-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}><div className="flex items-center gap-2 mb-4"><ClipboardList size={18} style={{ color: "var(--terracotta)" }} /><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Adaptación segura del CV</h2></div><p className="text-sm mb-5" style={{ color: "var(--olive-gray)" }}>No se inventa experiencia. Utiliza solo hechos que puedas demostrar.</p><ol className="space-y-3 text-sm" style={{ color: "var(--charcoal-warm)" }}><li className="flex gap-2"><Check size={15} style={{ color: "#5c7052", flex: "0 0 auto", marginTop: 3 }} />Adapta el título profesional al contexto de “{offer.role || offer.title}” sin cambiar tu cargo real.</li>{(offer.matched_skills || []).map((skill) => <li key={skill} className="flex gap-2"><Check size={15} style={{ color: "#5c7052", flex: "0 0 auto", marginTop: 3 }} />Incluye una evidencia o resultado verificable relacionado con {skill}.</li>)}<li className="flex gap-2"><Check size={15} style={{ color: "#5c7052", flex: "0 0 auto", marginTop: 3 }} />Prioriza resultados medibles y elimina contenido que no aporte a esta candidatura.</li><li className="flex gap-2"><Check size={15} style={{ color: "#5c7052", flex: "0 0 auto", marginTop: 3 }} />Revisa fechas, enlaces y datos de contacto antes de exportar.</li></ol></section>

          <section className="rounded-2xl p-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}><div className="flex items-center gap-2 mb-4"><MessageSquareText size={18} style={{ color: "var(--terracotta)" }} /><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Preparación de entrevista</h2></div><div className="space-y-3">{questions.map((question, index) => <details key={question} className="rounded-xl p-3" style={{ backgroundColor: "var(--parchment)" }}><summary className="cursor-pointer text-sm" style={{ color: "var(--near-black)", fontWeight: 600 }}>{index + 1}. {question}</summary><p className="text-xs mt-3" style={{ color: "var(--olive-gray)" }}>Prepara una respuesta con contexto, acción concreta, resultado y aprendizaje. No memorices texto completo.</p></details>)}</div></section>

          <section className="lg:col-span-2 rounded-2xl p-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}><div className="flex items-center justify-between gap-3 mb-3"><div><h2 className="font-serif text-2xl" style={{ color: "var(--near-black)" }}>Borrador de carta</h2><p className="text-xs" style={{ color: "var(--stone-gray)" }}>Revisa y personaliza el párrafo de logros antes de utilizarla.</p></div></div><label htmlFor="cover-letter" className="sr-only">Borrador editable de carta de presentación</label><textarea id="cover-letter" value={coverLetter} onChange={(event) => { setCoverLetter(event.target.value); setSaved(false); }} rows={13} className="w-full rounded-xl p-4 text-sm" style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)", color: "var(--near-black)", lineHeight: 1.7 }} /></section>
        </div>
      </div>
    </div>
  );
}
