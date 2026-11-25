import { font, radius } from "../tokens";
import { useT } from "../context/ThemeContext";


export default function Sidebar({ profiles = [], onDemo, onLogout }) {
  const T = useT();
  return (
    <aside style={{
      width: 260,
      flexShrink: 0,
      borderRight: `1px solid ${T.border}`,
      background: T.bgSidebar,
      padding: "18px 14px",
      display: "flex",
      flexDirection: "column",
      gap: 16,
      overflowY: "auto",
    }}>
      <div>
        <div style={{
          fontSize: font.size.xxs,
          fontWeight: 700,
          textTransform: "uppercase",
          color: T.textFaint,
          marginBottom: 8,
        }}>
          Configured profiles
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {profiles.map(profile => (
            <div key={profile.id} style={{
              padding: "9px 10px",
              border: `1px solid ${T.borderSub}`,
              borderRadius: radius.md,
              background: T.bgCard,
            }}>
              <div style={{ fontSize: font.size.sm, fontWeight: 700, color: T.text }}>{profile.label}</div>
              <div style={{ marginTop: 3, fontSize: font.size.xs, color: T.textFaint }}>
                {profile.source} · {profile.methodology}
              </div>
            </div>
          ))}
          {profiles.length === 0 && (
            <div style={{ fontSize: font.size.xs, color: T.textFaint }}>No server profiles configured</div>
          )}
        </div>
      </div>

      <div style={{ flex: 1 }} />

      <button type="button" onClick={onDemo} style={{
        height: 34,
        borderRadius: radius.md,
        border: `1px solid ${T.border}`,
        background: T.bgCard,
        color: T.textSec,
        fontWeight: 600,
        cursor: "pointer",
      }}>
        Load demo data
      </button>
      <button type="button" onClick={onLogout} style={{
        height: 34,
        borderRadius: radius.md,
        border: `1px solid ${T.border}`,
        background: "transparent",
        color: T.textMuted,
        fontWeight: 600,
        cursor: "pointer",
      }}>
        Sign out
      </button>
    </aside>
  );
}
