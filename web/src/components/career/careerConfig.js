import { Cpu, Users, Wrench } from "lucide-react";

export const PRIORITY_LABELS = {
  critical: "Crítica",
  recommended: "Recomendada",
  complementary: "Complementaria",
};

export const PRIORITY_COLORS = {
  critical: "#c96442",
  recommended: "#a66f2c",
  complementary: "#74766f",
};

export const SKILL_TYPES = [
  {
    key: "hard",
    label: "Habilidades hard",
    shortLabel: "Hard",
    subtitle: "Conocimientos técnicos y profesionales",
    icon: Wrench,
    color: "#c96442",
  },
  {
    key: "technology",
    label: "Tecnologías y herramientas",
    shortLabel: "Tecnologías",
    subtitle: "Software, plataformas, frameworks y herramientas concretas",
    icon: Cpu,
    color: "#3f6f82",
  },
  {
    key: "soft",
    label: "Habilidades soft",
    shortLabel: "Soft",
    subtitle: "Comportamientos y capacidades interpersonales",
    icon: Users,
    color: "#5c7052",
  },
];
