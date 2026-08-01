import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "../hooks/useTheme.jsx";

const ICONS = { light: Sun, dark: Moon, system: Monitor };
const LABELS = { light: "Light", dark: "Dark", system: "System" };

export default function ThemeToggle() {
  const { mode, cycle } = useTheme();
  const Icon = ICONS[mode];

  return (
    <button className="theme-toggle" onClick={cycle} title={`Theme: ${LABELS[mode]} (click to cycle)`}>
      <Icon size={15} />
      <span style={{ fontSize: 11.5, fontWeight: 600 }}>{LABELS[mode]}</span>
    </button>
  );
}
