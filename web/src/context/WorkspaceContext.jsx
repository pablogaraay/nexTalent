import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "nextalent.workspace.v1";

const EMPTY_WORKSPACE = {
  version: 1,
  profile: {
    text: "",
    parsed: null,
    cvName: "",
    updatedAt: "",
  },
  savedOffers: [],
  offerFeedback: {},
  careerPlans: [],
  planProgress: {},
  applications: [],
  alerts: [],
  privacyAcceptedAt: "",
};

function readWorkspace() {
  if (typeof window === "undefined") return EMPTY_WORKSPACE;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
    if (!parsed || typeof parsed !== "object") return EMPTY_WORKSPACE;
    return {
      ...EMPTY_WORKSPACE,
      ...parsed,
      profile: { ...EMPTY_WORKSPACE.profile, ...(parsed.profile || {}) },
      offerFeedback: parsed.offerFeedback || {},
      savedOffers: Array.isArray(parsed.savedOffers) ? parsed.savedOffers : [],
      careerPlans: Array.isArray(parsed.careerPlans) ? parsed.careerPlans : [],
      planProgress: parsed.planProgress && typeof parsed.planProgress === "object" ? parsed.planProgress : {},
      applications: Array.isArray(parsed.applications) ? parsed.applications : [],
      alerts: Array.isArray(parsed.alerts) ? parsed.alerts : [],
    };
  } catch {
    return EMPTY_WORKSPACE;
  }
}

function makeId(prefix = "item") {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [workspace, setWorkspace] = useState(readWorkspace);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
    } catch {
      // The UI remains usable when storage is unavailable or its quota is exhausted.
    }
  }, [workspace]);

  const updateWorkspace = useCallback((updater) => {
    setWorkspace((current) => {
      const next = typeof updater === "function" ? updater(current) : updater;
      return { ...next, version: 1 };
    });
  }, []);

  const saveProfile = useCallback(({ text = "", parsed = null, cvName = "" }) => {
    updateWorkspace((current) => ({
      ...current,
      profile: {
        text: text || current.profile.text,
        parsed: parsed || current.profile.parsed,
        cvName: cvName || current.profile.cvName,
        updatedAt: new Date().toISOString(),
      },
    }));
  }, [updateWorkspace]);

  const toggleSavedOffer = useCallback((offer) => {
    updateWorkspace((current) => {
      const exists = current.savedOffers.some((item) => item.id === offer.id);
      return {
        ...current,
        savedOffers: exists
          ? current.savedOffers.filter((item) => item.id !== offer.id)
          : [{ ...offer, savedAt: new Date().toISOString() }, ...current.savedOffers],
      };
    });
  }, [updateWorkspace]);

  const ensureSavedOffer = useCallback((offer) => {
    updateWorkspace((current) => {
      if (current.savedOffers.some((item) => item.id === offer.id)) return current;
      return {
        ...current,
        savedOffers: [{ ...offer, savedAt: new Date().toISOString() }, ...current.savedOffers],
      };
    });
  }, [updateWorkspace]);

  const setOfferFeedback = useCallback((offerId, feedback) => {
    updateWorkspace((current) => ({
      ...current,
      offerFeedback: {
        ...current.offerFeedback,
        [offerId]: { ...feedback, updatedAt: new Date().toISOString() },
      },
    }));
  }, [updateWorkspace]);

  const saveCareerPlan = useCallback((result) => {
    if (!result?.target_role) return;
    updateWorkspace((current) => {
      const plan = {
        ...result,
        id: result.id || makeId("plan"),
        savedAt: new Date().toISOString(),
      };
      const otherPlans = current.careerPlans.filter(
        (item) => item.target_role?.toLowerCase() !== result.target_role.toLowerCase(),
      );
      return { ...current, careerPlans: [plan, ...otherPlans].slice(0, 10) };
    });
  }, [updateWorkspace]);

  const setPlanActionComplete = useCallback((planId, actionKey, completed) => {
    updateWorkspace((current) => ({
      ...current,
      planProgress: {
        ...current.planProgress,
        [planId]: {
          ...(current.planProgress[planId] || {}),
          [actionKey]: Boolean(completed),
        },
      },
    }));
  }, [updateWorkspace]);

  const upsertApplication = useCallback((offer, patch = {}) => {
    updateWorkspace((current) => {
      const existing = current.applications.find((item) => item.offer?.id === offer.id);
      const applicationId = existing?.id || makeId("application");
      const application = {
        status: "preparing",
        notes: "",
        coverLetter: "",
        createdAt: existing?.createdAt || new Date().toISOString(),
        ...existing,
        ...patch,
        id: applicationId,
        offer,
        updatedAt: new Date().toISOString(),
      };
      return {
        ...current,
        applications: [
          application,
          ...current.applications.filter((item) => item.id !== applicationId),
        ],
      };
    });
  }, [updateWorkspace]);

  const updateApplication = useCallback((applicationId, patch) => {
    updateWorkspace((current) => ({
      ...current,
      applications: current.applications.map((item) =>
        item.id === applicationId
          ? { ...item, ...patch, updatedAt: new Date().toISOString() }
          : item,
      ),
    }));
  }, [updateWorkspace]);

  const addAlert = useCallback((alert) => {
    updateWorkspace((current) => ({
      ...current,
      alerts: [{ id: makeId("alert"), active: true, createdAt: new Date().toISOString(), ...alert }, ...current.alerts],
    }));
  }, [updateWorkspace]);

  const updateAlert = useCallback((alertId, patch) => {
    updateWorkspace((current) => ({
      ...current,
      alerts: current.alerts.map((item) => item.id === alertId ? { ...item, ...patch } : item),
    }));
  }, [updateWorkspace]);

  const removeAlert = useCallback((alertId) => {
    updateWorkspace((current) => ({ ...current, alerts: current.alerts.filter((item) => item.id !== alertId) }));
  }, [updateWorkspace]);

  const acceptPrivacy = useCallback(() => {
    updateWorkspace((current) => ({ ...current, privacyAcceptedAt: new Date().toISOString() }));
  }, [updateWorkspace]);

  const clearWorkspace = useCallback(() => {
    setWorkspace({ ...EMPTY_WORKSPACE, profile: { ...EMPTY_WORKSPACE.profile } });
    window.localStorage.removeItem(STORAGE_KEY);
  }, []);

  const value = useMemo(() => ({
    workspace,
    saveProfile,
    toggleSavedOffer,
    ensureSavedOffer,
    setOfferFeedback,
    saveCareerPlan,
    setPlanActionComplete,
    upsertApplication,
    updateApplication,
    addAlert,
    updateAlert,
    removeAlert,
    acceptPrivacy,
    clearWorkspace,
  }), [
    workspace,
    saveProfile,
    toggleSavedOffer,
    ensureSavedOffer,
    setOfferFeedback,
    saveCareerPlan,
    setPlanActionComplete,
    upsertApplication,
    updateApplication,
    addAlert,
    updateAlert,
    removeAlert,
    acceptPrivacy,
    clearWorkspace,
  ]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace debe utilizarse dentro de WorkspaceProvider.");
  return value;
}
