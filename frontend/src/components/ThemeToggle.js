import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/theme";

// Tombol mode gelap/terang. variant: "icon" (di topbar) atau "floating" (pojok layar login/pemilih portal).
export function ThemeToggle({ variant = "icon", testId = "theme-toggle-button" }) {
  const [theme, toggle] = useTheme();
  const dark = theme === "dark";
  const label = dark ? "Ganti ke mode terang" : "Ganti ke mode gelap";
  return (
    <button
      type="button"
      className={`theme-toggle ${variant}`}
      data-testid={testId}
      data-theme-state={theme}
      aria-label={label}
      aria-pressed={dark}
      title={label}
      onClick={toggle}
    >
      <span className="theme-toggle-icon" key={theme}>{dark ? <Sun size={18} /> : <Moon size={18} />}</span>
      {variant === "floating" && <span className="theme-toggle-text">{dark ? "Mode terang" : "Mode gelap"}</span>}
    </button>
  );
}
