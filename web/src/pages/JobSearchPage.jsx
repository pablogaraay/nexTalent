import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Search,
  Upload,
  FileText,
  MapPin,
  Building2,
  X,
  GitCompareArrows,
  Briefcase,
  ExternalLink,
  AlertCircle,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { jobsAPI } from "@/lib/api";

const OFFERS_PER_PAGE = 20;

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
  const [searchMode, setSearchMode] = useState("prompt");
  const [prompt, setPrompt] = useState("");
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
    setError("Solo se aceptan archivos PDF.");
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1
  });

  const handleSearch = async () => {
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

      const resultData = data.result || {};
      const offers = (resultData.results || []).map((offer, i) => ({
        id: offer.url || `offer-${i}`,
        title: offer.title || "Sin título",
        company: offer.company || "Empresa desconocida",
        location: offer.location || "",
        role: offer.role_raw || "",
        url: offer.url || "",
        matched_skills: offer.matched_skills || [],
        rank: i + 1
      }));

      const profile = resultData.profile || {};
      setResults({
        offers,
        total: resultData.total_candidates || offers.length,
        profile,
        query: prompt || "CV uploaded"
      });
      setSelectedOffers([]);
      setCompareMode(false);
      setCurrentPage(1);
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        err.response?.data?.details;
      setError(typeof detail === "string" ? detail : "Error en la búsqueda. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  const toggleOfferSelection = (offerId) => {
    setSelectedOffers((prev) =>
      prev.includes(offerId) ? prev.filter((id) => id !== offerId) : [...prev, offerId]
    );
  };

  const totalPages = results ? Math.max(1, Math.ceil(results.offers.length / OFFERS_PER_PAGE)) : 1;
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const pageStart = (safeCurrentPage - 1) * OFFERS_PER_PAGE;
  const pageEnd = pageStart + OFFERS_PER_PAGE;
  const paginatedOffers = results ? results.offers.slice(pageStart, pageEnd) : [];
  const visiblePageItems = getPaginationItems(safeCurrentPage, totalPages);

  const goToPage = (page) => {
    const nextPage = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(nextPage);
  };

  return (
    <div data-testid="job-search-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-10">
          <h1 className="font-serif mb-3" style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)", fontWeight: 500, lineHeight: 1.2, color: "var(--near-black)" }}>
            Búsqueda Avanzada de Empleo
          </h1>
          <p className="font-sans text-lg" style={{ color: "var(--olive-gray)", lineHeight: 1.6 }}>
            Encuentra las ofertas que mejor se ajustan a tu perfil.
          </p>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            data-testid="mode-prompt-btn"
            onClick={() => setSearchMode("prompt")}
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
            onClick={() => setSearchMode("cv")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-sans transition-all"
            style={{
              backgroundColor: searchMode === "cv" ? "var(--near-black)" : "var(--warm-sand)",
              color: searchMode === "cv" ? "var(--ivory)" : "var(--charcoal-warm)",
              fontWeight: 500
            }}
          >
            <Upload size={16} />
            Subir CV (PDF)
          </button>
        </div>

        <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)", boxShadow: "rgba(0,0,0,0.05) 0px 4px 24px" }}>
          {searchMode === "prompt" ? (
            <div>
              <label className="block text-sm font-sans mb-2" style={{ color: "var(--olive-gray)", fontWeight: 500 }}>
                Describe tu perfil, experiencia o lo que buscas
              </label>
              <textarea
                data-testid="search-prompt-input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ej: Desarrollador frontend con 3 años de experiencia en React y TypeScript, busco trabajo remoto en Madrid..."
                className="w-full rounded-xl p-4 text-sm font-sans resize-none focus:outline-none focus:ring-2"
                style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)", color: "var(--near-black)", minHeight: "120px", lineHeight: 1.6 }}
                rows={4}
              />
            </div>
          ) : (
            <div>
              <div
                {...getRootProps()}
                data-testid="cv-dropzone"
                className="rounded-xl p-8 text-center cursor-pointer transition-all"
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
                  <div className="flex items-center justify-center gap-3">
                    <FileText size={24} style={{ color: "var(--terracotta)" }} />
                    <span className="font-sans text-sm" style={{ color: "var(--near-black)", fontWeight: 500 }}>{cvFile.name}</span>
                    <button
                      data-testid="remove-cv-btn"
                      onClick={e => {
                        e.stopPropagation();
                        setCvFile(null);
                        setFileInputKey((k) => k + 1);
                        setError("");
                      }}
                      className="p-1 rounded-full"
                      style={{ backgroundColor: "var(--warm-sand)" }}
                    >
                      <X size={14} style={{ color: "var(--charcoal-warm)" }} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <Upload size={32} style={{ color: "var(--stone-gray)", margin: "0 auto 12px" }} />
                    <p className="font-sans text-sm" style={{ color: "var(--olive-gray)" }}>Arrastra tu CV aquí o haz clic para seleccionarlo</p>
                    <p className="font-sans text-xs mt-1" style={{ color: "var(--stone-gray)" }}>Solo PDF</p>
                  </div>
                )}
              </div>
              <div className="mt-4">
                <label className="block text-xs font-sans mb-1" style={{ color: "var(--stone-gray)" }}>
                  Opcional: añade un mensaje para refinar la búsqueda
                </label>
                <input
                  data-testid="cv-prompt-input"
                  type="text"
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="Ej: Busco trabajo remoto en Madrid"
                  className="w-full rounded-xl px-4 py-2.5 text-sm font-sans focus:outline-none"
                  style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)", color: "var(--near-black)" }}
                />
              </div>
            </div>
          )}

          {error && (
            <div data-testid="search-error" className="mt-3 flex items-center gap-2 p-3 rounded-lg text-sm font-sans" style={{ backgroundColor: "rgba(181,51,51,0.08)", color: "var(--error-crimson)" }}>
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <button
            data-testid="search-submit-btn"
            onClick={handleSearch}
            disabled={loading || (searchMode === "prompt" && !prompt.trim()) || (searchMode === "cv" && !cvFile && !prompt.trim())}
            className="mt-4 w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-base font-sans transition-all disabled:opacity-50"
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

        {results?.profile && results.profile.role && (
          <div data-testid="profile-summary" className="rounded-2xl p-5 mb-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <h3 className="font-serif mb-3" style={{ fontSize: "1.1rem", fontWeight: 500, color: "var(--near-black)" }}>
              Perfil Detectado
            </h3>
            <div className="flex flex-wrap gap-4 text-sm font-sans" style={{ color: "var(--olive-gray)" }}>
              {results.profile.role && <div><span style={{ color: "var(--stone-gray)" }}>Rol:</span> <strong style={{ color: "var(--near-black)" }}>{results.profile.role}</strong></div>}
              {results.profile.seniority_raw && results.profile.seniority_raw !== "unknown" && <div><span style={{ color: "var(--stone-gray)" }}>Nivel:</span> <strong style={{ color: "var(--near-black)" }}>{results.profile.seniority_raw}</strong></div>}
              {results.profile.location_query && <div><span style={{ color: "var(--stone-gray)" }}>Ubicación:</span> <strong style={{ color: "var(--near-black)" }}>{results.profile.location_query}</strong></div>}
            </div>
            {results.profile.skills?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {results.profile.skills.map(s => (
                  <span key={s} className="px-2.5 py-0.5 rounded-md text-xs font-sans" style={{ backgroundColor: "rgba(201,100,66,0.08)", color: "var(--terracotta)", fontWeight: 500 }}>{s}</span>
                ))}
              </div>
            )}
          </div>
        )}

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
                <div
                  key={offer.id}
                  data-testid={`offer-card-${offer.id}`}
                  className="rounded-2xl p-5 transition-all opacity-0 animate-fade-in-up"
                  style={{
                    backgroundColor: "var(--ivory)",
                    border: selectedOffers.includes(offer.id) ? "2px solid var(--terracotta)" : "1px solid var(--border-cream)",
                    boxShadow: "rgba(0,0,0,0.03) 0px 2px 12px",
                    animationDelay: `${i * 0.05}s`, animationFillMode: "forwards"
                  }}
                >
                  <div className="flex flex-col md:flex-row md:items-start gap-4">
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-serif" style={{ fontSize: "1.25rem", fontWeight: 500, color: "var(--near-black)", lineHeight: 1.2 }}>
                            {offer.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-3 mt-1.5">
                            <span className="flex items-center gap-1 text-sm font-sans" style={{ color: "var(--olive-gray)" }}>
                              <Building2 size={14} /> {offer.company}
                            </span>
                            {offer.location && (
                              <span className="flex items-center gap-1 text-sm font-sans" style={{ color: "var(--olive-gray)" }}>
                                <MapPin size={14} /> {offer.location}
                              </span>
                            )}
                            {offer.role && (
                              <span className="flex items-center gap-1 text-sm font-sans" style={{ color: "var(--olive-gray)" }}>
                                <Briefcase size={14} /> {offer.role}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="px-3 py-1 rounded-full text-sm font-sans" style={{ backgroundColor: "rgba(201,100,66,0.12)", color: "var(--terracotta)", fontWeight: 600 }}>
                            Top #{offer.rank}
                          </div>
                        </div>
                      </div>

                      <div className="w-full h-2 rounded-full mb-3" style={{ backgroundColor: "var(--border-cream)" }}>
                        <div className="h-2 rounded-full" style={{ width: `${Math.max(35, 100 - i * 7)}%`, backgroundColor: "var(--terracotta)" }} />
                      </div>

                      {offer.matched_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mb-3">
                          {offer.matched_skills.map(skill => (
                            <span key={skill} className="px-2.5 py-0.5 rounded-md text-xs font-sans" style={{ backgroundColor: "rgba(201,100,66,0.08)", color: "var(--terracotta)", fontWeight: 500 }}>
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col gap-2 self-start">
                      {offer.url && (
                        <a
                          href={offer.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          data-testid={`offer-link-${offer.id}`}
                          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-sans no-underline whitespace-nowrap"
                          style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)", fontWeight: 500 }}
                        >
                          <ExternalLink size={12} /> Ver oferta
                        </a>
                      )}
                      <button
                        data-testid={`select-offer-${offer.id}`}
                        onClick={() => toggleOfferSelection(offer.id)}
                        className="px-3 py-2 rounded-lg text-xs font-sans whitespace-nowrap transition-all"
                        style={{
                          backgroundColor: selectedOffers.includes(offer.id) ? "var(--near-black)" : "var(--warm-sand)",
                          color: selectedOffers.includes(offer.id) ? "var(--ivory)" : "var(--charcoal-warm)",
                          fontWeight: 500
                        }}
                      >
                        {selectedOffers.includes(offer.id) ? "Seleccionada" : "Comparar"}
                      </button>
                    </div>
                  </div>
                </div>
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
          <div data-testid="compare-view">
            <h2 className="font-serif mb-6" style={{ fontSize: "1.6rem", fontWeight: 500, color: "var(--near-black)" }}>
              Comparación de Ofertas
            </h2>
            <div className="overflow-x-auto">
              <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${selectedOffers.length}, minmax(280px, 1fr))` }}>
                {results.offers.filter(o => selectedOffers.includes(o.id)).map(offer => (
                  <div key={offer.id} data-testid={`compare-card-${offer.id}`} className="rounded-2xl p-5" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
                    <div className="px-3 py-1 rounded-full text-sm font-sans inline-block mb-3" style={{ backgroundColor: "rgba(201,100,66,0.12)", color: "var(--terracotta)", fontWeight: 600 }}>
                      Top #{offer.rank}
                    </div>
                    <h3 className="font-serif mb-1" style={{ fontSize: "1.1rem", fontWeight: 500, color: "var(--near-black)" }}>{offer.title}</h3>
                    <p className="font-sans text-sm mb-4" style={{ color: "var(--olive-gray)" }}>{offer.company}</p>
                    {[
                      { label: "Ubicación", value: offer.location || "N/A" },
                      { label: "Perfil", value: offer.role || "N/A" }
                    ].map(row => (
                      <div key={row.label} className="flex justify-between py-2 border-t" style={{ borderColor: "var(--border-cream)" }}>
                        <span className="text-xs font-sans" style={{ color: "var(--stone-gray)" }}>{row.label}</span>
                        <span className="text-xs font-sans" style={{ color: "var(--near-black)", fontWeight: 500 }}>{row.value}</span>
                      </div>
                    ))}
                    {offer.matched_skills.length > 0 && (
                      <div className="mt-3">
                        <span className="text-xs font-sans" style={{ color: "var(--stone-gray)" }}>Habilidades coincidentes</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {offer.matched_skills.map(s => (
                            <span key={s} className="px-2 py-0.5 rounded-md text-xs font-sans" style={{ backgroundColor: "rgba(201,100,66,0.08)", color: "var(--terracotta)" }}>{s}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {offer.url && (
                      <a href={offer.url} target="_blank" rel="noopener noreferrer" className="mt-3 flex items-center gap-1 text-xs font-sans no-underline" style={{ color: "var(--terracotta)", fontWeight: 500 }}>
                        <ExternalLink size={12} /> Ver oferta original
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
