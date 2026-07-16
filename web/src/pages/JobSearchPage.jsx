import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Search,
  Upload,
  FileText,
  X,
  GitCompareArrows,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { OfferCard } from "@/components/jobs/OfferCard";
import { OfferComparison } from "@/components/jobs/OfferComparison";
import { ProfileSummary } from "@/components/jobs/ProfileSummary";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { jobsAPI } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

const OFFERS_PER_PAGE = 20;

function uniqueItems(items) {
  return [...new Set((items || []).filter(Boolean))];
}

function getPaginationItems(currentPage, totalPages) {
  if (totalPages <= 8) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  if (currentPage <= 5) {
    return [1, 2, 3, 4, 5, 6, "end-ellipsis", totalPages];
  }

  if (currentPage >= totalPages - 4) {
    return [1, "start-ellipsis", ...Array.from({ length: 6 }, (_, i) => totalPages - 5 + i)];
  }

  return [1, "start-ellipsis", currentPage - 1, currentPage, currentPage + 1, "end-ellipsis", totalPages];
}

export default function JobSearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const {
    workspace,
    saveProfile,
    toggleSavedOffer,
    ensureSavedOffer,
    setOfferFeedback,
    upsertApplication,
    acceptPrivacy,
    updateAlert,
  } = useWorkspace();
  const [searchMode, setSearchMode] = useState("prompt");
  const [prompt, setPrompt] = useState(() => {
    const requestedRole = searchParams.get("role");
    return requestedRole ? `Busco oportunidades como ${requestedRole}. ${workspace.profile.text || ""}`.trim() : workspace.profile.text || "";
  });
  const [cvFile, setCvFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedOffers, setSelectedOffers] = useState([]);
  const [compareMode, setCompareMode] = useState(false);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setCvFile(acceptedFiles[0]);
      setError("");
    }
  }, []);

  const onDropRejected = useCallback(() => {
    setCvFile(null);
    setError("Solo se aceptan archivos PDF o DOCX.");
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"]
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  const handleSearch = async () => {
    if (searchMode === "cv" && !workspace.privacyAcceptedAt) {
      setError("Acepta el procesamiento temporal del CV antes de continuar.");
      return;
    }
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const formData = new FormData();
      if (searchMode === "cv" && cvFile) {
        formData.append("cv", cvFile);
      }
      if (prompt.trim()) {
        formData.append("profileText", prompt);
      }
      const { data } = await jobsAPI.search(formData);
      if (data.error) {
        throw new Error(data.error);
      }

      const resultData = data.result || {};
      const offers = (resultData.results || []).map((offer, i) => ({
        id: offer.url || `offer-${i}`,
        title: offer.title || "Sin título",
        company: offer.company || "Empresa desconocida",
        location: offer.location || "",
        role: offer.role_raw || "",
        url: offer.url || "",
        matched_skills: offer.matched_skills || [],
        match_score: Number(offer.match_score || offer.vector_score || 0),
        why_match: offer.why_match || "",
        rank: i + 1
      }));
      const feedbackWeight = (offer) => {
        const value = workspace.offerFeedback[offer.id]?.value;
        return value === "positive" ? 1 : value === "negative" ? -1 : 0;
      };
      offers.sort((a, b) => feedbackWeight(b) - feedbackWeight(a) || b.match_score - a.match_score);
      offers.forEach((offer, index) => { offer.rank = index + 1; });
      workspace.alerts.filter((alert) => alert.active).forEach((alert) => {
        const roleNeedle = alert.role.toLocaleLowerCase("es");
        const locationNeedle = (alert.location || "").toLocaleLowerCase("es");
        const count = offers.filter((offer) => {
          const roleHaystack = `${offer.title} ${offer.role}`.toLocaleLowerCase("es");
          const locationHaystack = offer.location.toLocaleLowerCase("es");
          return roleHaystack.includes(roleNeedle) && (!locationNeedle || locationHaystack.includes(locationNeedle));
        }).length;
        updateAlert(alert.id, { lastMatchCount: count, lastCheckedAt: new Date().toISOString() });
      });

      const profile = resultData.profile || {};
      setResults({
        offers,
        total: resultData.total_candidates || offers.length,
        profile,
        query: prompt || "CV subido"
      });
      setSelectedOffers([]);
      setCompareMode(false);
      setCurrentPage(1);
      saveProfile({
        text: prompt,
        parsed: profile,
        cvName: cvFile?.name || "",
      });
    } catch (err) {
      const detail =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message;
      setError(typeof detail === "string" ? detail : "Error en la búsqueda. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  const handleModeChange = (nextMode) => {
    if (nextMode === searchMode) {
      return;
    }

    setSearchMode(nextMode);
    setPrompt(nextMode === "prompt" ? workspace.profile.text || "" : "");
    setCvFile(null);
    setResults(null);
    setError("");
    setSelectedOffers([]);
    setCompareMode(false);
    setCurrentPage(1);
    setFileInputKey((key) => key + 1);
  };

  const toggleOfferSelection = (offerId) => {
    setSelectedOffers((prev) =>
      prev.includes(offerId) ? prev.filter((id) => id !== offerId) : [...prev, offerId]
    );
  };

  const startCareerPlan = (offer) => {
    ensureSavedOffer(offer);
    navigate(`/career?targetRole=${encodeURIComponent(offer.role || offer.title)}`);
  };

  const prepareApplication = (offer) => {
    ensureSavedOffer(offer);
    upsertApplication(offer);
    navigate(`/application?offerId=${encodeURIComponent(offer.id)}`);
  };

  const totalPages = results ? Math.max(1, Math.ceil(results.offers.length / OFFERS_PER_PAGE)) : 1;
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const pageStart = (safeCurrentPage - 1) * OFFERS_PER_PAGE;
  const pageEnd = pageStart + OFFERS_PER_PAGE;
  const paginatedOffers = results ? results.offers.slice(pageStart, pageEnd) : [];
  const visiblePageItems = getPaginationItems(safeCurrentPage, totalPages);
  const hasResults = Boolean(results);
  const detectedProfile = results?.profile || {};
  const performedRoles = uniqueItems([
    ...(detectedProfile.performed_roles || []),
    ...(!detectedProfile.performed_roles?.length && detectedProfile.role ? [detectedProfile.role] : [])
  ]);
  const normalizedRoleGroups = (detectedProfile.normalized_roles || []).reduce((groups, role) => {
    const occupation = role?.occupation;
    if (!occupation) {
      return groups;
    }

    const existing = groups.find(group => group.occupation === occupation);
    const sourceRoles = uniqueItems(role.source_roles || []);
    if (existing) {
      existing.source_roles = uniqueItems([...existing.source_roles, ...sourceRoles]);
      return groups;
    }

    return [...groups, { occupation, source_roles: sourceRoles }];
  }, []);
  const roleExperienceRows = (detectedProfile.role_experiences || [])
    .map((experience) => ({
      role: experience?.role || "",
      seniority: experience?.seniority_raw && experience.seniority_raw !== "unknown" ? experience.seniority_raw : "",
      location: experience?.location || "",
      normalized: experience?.normalized_occupation || ""
    }))
    .filter(experience => experience.role);
  const fallbackRoleExperienceRows = roleExperienceRows.length > 0
    ? roleExperienceRows
    : performedRoles.map(role => {
      const normalizedGroup = normalizedRoleGroups.find(group => group.source_roles.includes(role));
      return {
        role,
        seniority: detectedProfile.seniority_raw && detectedProfile.seniority_raw !== "unknown" ? detectedProfile.seniority_raw : "",
        location: detectedProfile.location_query || "",
        normalized: normalizedGroup?.occupation || ""
      };
    });
  const goToPage = (page) => {
    const nextPage = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(nextPage);
  };

  return (
    <div data-testid="job-search-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <PageHeader
          title="Búsqueda avanzada de empleo"
          description="Encuentra oportunidades alineadas con tu experiencia y entiende por qué encajan contigo."
        />

        <div className="flex gap-2 mb-6">
          <button
            data-testid="mode-prompt-btn"
            onClick={() => handleModeChange("prompt")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-sans transition-all"
            style={{
              backgroundColor: searchMode === "prompt" ? "var(--near-black)" : "var(--warm-sand)",
              color: searchMode === "prompt" ? "var(--ivory)" : "var(--charcoal-warm)",
              fontWeight: 500
            }}
          >
            <Search size={16} />
            Describir perfil
          </button>
          <button
            data-testid="mode-cv-btn"
            onClick={() => handleModeChange("cv")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-sans transition-all"
            style={{
              backgroundColor: searchMode === "cv" ? "var(--near-black)" : "var(--warm-sand)",
              color: searchMode === "cv" ? "var(--ivory)" : "var(--charcoal-warm)",
              fontWeight: 500
            }}
          >
            <Upload size={16} />
            Subir CV
          </button>
        </div>

        <div
          className={hasResults ? "rounded-xl p-4 mb-5" : "rounded-2xl p-6 mb-8"}
          style={{
            backgroundColor: "var(--ivory)",
            border: "1px solid var(--border-cream)",
            boxShadow: hasResults ? "rgba(0,0,0,0.03) 0px 2px 14px" : "rgba(0,0,0,0.05) 0px 4px 24px"
          }}
        >
          {searchMode === "prompt" ? (
            <div>
              <label htmlFor="search-profile-text" className="block text-sm font-sans mb-2" style={{ color: "var(--olive-gray)", fontWeight: 500 }}>
                Describe tu perfil, experiencia o lo que buscas
              </label>
              <textarea
                data-testid="search-prompt-input"
                id="search-profile-text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ej: Desarrollador frontend con 3 años de experiencia en React y TypeScript, busco trabajo remoto en Madrid..."
                className="w-full rounded-xl p-4 text-sm font-sans resize-none focus:outline-none focus:ring-2"
                style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)", color: "var(--near-black)", minHeight: hasResults ? "72px" : "120px", lineHeight: 1.6 }}
                rows={hasResults ? 2 : 4}
              />
            </div>
          ) : (
            <div>
              <div
                {...getRootProps()}
                data-testid="cv-dropzone"
                className={hasResults ? "rounded-lg p-3 text-center cursor-pointer transition-all" : "rounded-xl p-8 text-center cursor-pointer transition-all"}
                style={{
                  backgroundColor: isDragActive ? "rgba(201,100,66,0.05)" : "var(--parchment)",
                  border: `2px dashed ${isDragActive ? "var(--terracotta)" : "var(--border-warm)"}`
                }}
              >
                <input
                  key={fileInputKey}
                  {...getInputProps({
                    onClick: (event) => {
                      // Allow selecting the same file repeatedly.
                      event.target.value = null;
                    }
                  })}
                />
                {cvFile ? (
                  <div className="flex items-center justify-center gap-2 min-w-0">
                    <FileText size={hasResults ? 18 : 24} style={{ color: "var(--terracotta)", flex: "0 0 auto" }} />
                    <span className="font-sans text-sm truncate" style={{ color: "var(--near-black)", fontWeight: 500 }}>{cvFile.name}</span>
                    <button
                      data-testid="remove-cv-btn"
                      onClick={e => {
                        e.stopPropagation();
                        setCvFile(null);
                        setFileInputKey((k) => k + 1);
                        setError("");
                      }}
                      className="p-1 rounded-full flex-shrink-0"
                      style={{ backgroundColor: "var(--warm-sand)" }}
                    >
                      <X size={14} style={{ color: "var(--charcoal-warm)" }} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <Upload size={hasResults ? 22 : 32} style={{ color: "var(--stone-gray)", margin: hasResults ? "0 auto 6px" : "0 auto 12px" }} />
                    <p className="font-sans text-sm" style={{ color: "var(--olive-gray)" }}>Arrastra tu CV aquí o haz clic para seleccionarlo</p>
                    {!hasResults && <p className="font-sans text-xs mt-1" style={{ color: "var(--stone-gray)" }}>PDF o DOCX</p>}
                  </div>
                )}
              </div>
            </div>
          )}

          {searchMode === "cv" && (
            <label className="flex items-start gap-2 mt-3 text-xs" style={{ color: "var(--olive-gray)" }}>
              <input type="checkbox" checked={Boolean(workspace.privacyAcceptedAt)} onChange={(event) => event.target.checked && acceptPrivacy()} className="mt-0.5" />
              <span>Acepto el procesamiento temporal del CV y confirmo que tengo derecho a utilizarlo. <Link to="/privacy" style={{ color: "var(--terracotta)" }}>Privacidad</Link>.</span>
            </label>
          )}

          {error && (
            <div data-testid="search-error" className="mt-3"><StatusMessage tone="error">{error}</StatusMessage></div>
          )}

          <button
            data-testid="search-submit-btn"
            onClick={handleSearch}
            disabled={loading || (searchMode === "prompt" && !prompt.trim()) || (searchMode === "cv" && !cvFile)}
            className={hasResults ? "mt-3 w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-sans transition-all disabled:opacity-50" : "mt-4 w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-base font-sans transition-all disabled:opacity-50"}
            style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)", fontWeight: 500 }}
          >
            {loading ? (
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Analizando perfil con IA...</span>
              </div>
            ) : (
              <><Search size={18} /> Buscar Ofertas</>
            )}
          </button>
        </div>

        <ProfileSummary
          profile={detectedProfile}
          roleExperiences={fallbackRoleExperienceRows}
          normalizedRoles={normalizedRoleGroups}
        />
        {selectedOffers.length >= 2 && (
          <div data-testid="compare-bar" className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-6 py-3 rounded-2xl animate-fade-in-up" style={{ backgroundColor: "var(--near-black)", boxShadow: "rgba(0,0,0,0.2) 0px 8px 32px" }}>
            <GitCompareArrows size={18} style={{ color: "var(--coral)" }} />
            <span className="font-sans text-sm" style={{ color: "var(--ivory)" }}>{selectedOffers.length} ofertas seleccionadas</span>
            <button data-testid="compare-toggle-btn" onClick={() => setCompareMode(!compareMode)} className="px-4 py-1.5 rounded-lg text-sm font-sans" style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)", fontWeight: 500 }}>
              {compareMode ? "Volver a lista" : "Comparar"}
            </button>
          </div>
        )}

        {results && !compareMode && (
          <div data-testid="search-results">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
              <div>
                <h2 className="font-serif" style={{ fontSize: "1.6rem", fontWeight: 500, color: "var(--near-black)" }}>
                  {results.offers.length} ofertas encontradas
                </h2>
                {results.offers.length > 0 && (
                  <p className="font-sans text-sm mt-1" style={{ color: "var(--stone-gray)" }}>
                    Mostrando {pageStart + 1}-{Math.min(pageEnd, results.offers.length)} de {results.offers.length}
                  </p>
                )}
              </div>
            </div>
            <div className="grid gap-4">
              {paginatedOffers.map((offer, i) => (
                <OfferCard
                  key={offer.id}
                  offer={offer}
                  animationDelay={i * 0.05}
                  isSelected={selectedOffers.includes(offer.id)}
                  isSaved={workspace.savedOffers.some((item) => item.id === offer.id)}
                  feedback={workspace.offerFeedback[offer.id]?.value}
                  onSave={() => toggleSavedOffer(offer)}
                  onSelect={() => toggleOfferSelection(offer.id)}
                  onCareerPlan={() => startCareerPlan(offer)}
                  onApplication={() => prepareApplication(offer)}
                  onFeedback={(value) => setOfferFeedback(offer.id, { value })}
                />
              ))}
            </div>
            {totalPages > 1 && (
              <nav data-testid="search-pagination" className="flex items-center justify-center gap-1.5 mt-8 overflow-x-auto whitespace-nowrap" aria-label="Paginación de ofertas">
                <button
                  data-testid="pagination-prev"
                  onClick={() => goToPage(safeCurrentPage - 1)}
                  disabled={safeCurrentPage === 1}
                  className="h-9 min-w-9 inline-flex items-center justify-center rounded-md transition-all disabled:opacity-40"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}
                  aria-label="Página anterior"
                >
                  <ChevronLeft size={16} />
                </button>
                {visiblePageItems.map(item => {
                  if (typeof item !== "number") {
                    return (
                      <span
                        key={item}
                        className="h-9 min-w-7 inline-flex items-center justify-center text-sm font-sans"
                        style={{ color: "var(--stone-gray)", fontWeight: 600 }}
                      >
                        ...
                      </span>
                    );
                  }

                  return (
                    <button
                      key={item}
                      data-testid={`pagination-page-${item}`}
                      onClick={() => goToPage(item)}
                      className="h-9 min-w-9 px-3 inline-flex items-center justify-center rounded-md text-sm font-sans transition-all"
                      style={{
                        backgroundColor: item === safeCurrentPage ? "var(--near-black)" : "transparent",
                        color: item === safeCurrentPage ? "var(--ivory)" : "var(--charcoal-warm)",
                        border: item === safeCurrentPage ? "1px solid var(--near-black)" : "1px solid var(--border-cream)",
                        fontWeight: 600
                      }}
                      aria-current={item === safeCurrentPage ? "page" : undefined}
                    >
                      {item}
                    </button>
                  );
                })}
                <button
                  data-testid="pagination-next"
                  onClick={() => goToPage(safeCurrentPage + 1)}
                  disabled={safeCurrentPage === totalPages}
                  className="h-9 min-w-9 inline-flex items-center justify-center rounded-md transition-all disabled:opacity-40"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}
                  aria-label="Página siguiente"
                >
                  <ChevronRight size={16} />
                </button>
              </nav>
            )}
          </div>
        )}

        {compareMode && selectedOffers.length >= 2 && results && (
          <OfferComparison offers={results.offers.filter((offer) => selectedOffers.includes(offer.id))} />
        )}
      </div>
    </div>
  );
}
