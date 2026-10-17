{
  "brand": {
    "name": "Perpustakaan SMA Negeri 1 Abung Tengah",
    "attributes": ["terang & bersih", "modern", "calm-academic", "high-contrast", "simple"],
    "constraints": {
      "css_only": true,
      "no_jsx_structure_changes": true,
      "id_card_design_must_not_change": true,
      "keep_semantic_status_colors": true,
      "no_transparent_bg_behind_text": true,
      "wcag_aa": true,
      "data_testid_required": true
    }
  },

  "design_tokens": {
    "fonts_google": {
      "keep": ["Outfit (headings)", "Inter (body)"]
    },
    "radius_px": {
      "sm": 8,
      "md": 10,
      "lg": 12,
      "xl": 14,
      "pill": 999
    },
    "shadow": {
      "sm": "0 1px 2px rgba(15,23,42,.06)",
      "md": "0 10px 24px -14px rgba(15,23,42,.22)",
      "lg": "0 22px 60px -28px rgba(15,23,42,.35)"
    },
    "palette": {
      "violet": {
        "50": "#f5f3ff",
        "100": "#ede9fe",
        "200": "#ddd6fe",
        "300": "#c4b5fd",
        "400": "#a78bfa",
        "500": "#8b5cf6",
        "600": "#7c3aed",
        "700": "#6d28d9",
        "800": "#5b21b6",
        "900": "#4c1d95"
      },
      "neutrals": {
        "bg": "#f7f7fb",
        "surface": "#ffffff",
        "surface_2": "#fbfbfe",
        "text": "#0f172a",
        "text_2": "#334155",
        "muted": "#64748b",
        "muted_2": "#94a3b8",
        "border": "#e6e8f2",
        "border_strong": "#d7dbea"
      },
      "semantic": {
        "success": {"bg": "#dcfce7", "fg": "#15803d"},
        "warning": {"bg": "#fef3c7", "fg": "#a16207"},
        "danger": {"bg": "#fee2e2", "fg": "#b91c1c"},
        "info": {"bg": "#e0e7ff", "fg": "#3730a3"}
      },
      "focus_ring": "#7c3aed"
    },
    "css_vars_to_define_in_override": {
      "--page": "#f7f7fb",
      "--line": "#e6e8f2",
      "--ink": "#0f172a",
      "--muted": "#64748b",
      "--navy": "#ffffff",
      "--blue": "#7c3aed",
      "--violet": "#7c3aed"
    }
  },

  "component_path": {
    "note": "Project has shadcn/ui available, but this task is CSS-only; do not refactor JSX. Use these only if later allowed.",
    "shadcn_ui": [
      "/app/frontend/src/components/ui/button.jsx",
      "/app/frontend/src/components/ui/input.jsx",
      "/app/frontend/src/components/ui/tabs.jsx",
      "/app/frontend/src/components/ui/dialog.jsx",
      "/app/frontend/src/components/ui/table.jsx",
      "/app/frontend/src/components/ui/sonner.jsx"
    ]
  },

  "instructions_to_main_agent": [
    "Create ONE new stylesheet loaded last (e.g., override.css) and only override existing classnames; do not change JSX structure.",
    "Also do a hex remap in existing CSS where requested (mapping table below). Keep ID card CSS untouched (Card.css / .id-card themes).",
    "Switch to a LIGHT sidebar (terang & bersih): white surface, subtle border, violet active indicator. Keep strong contrast for active state.",
    "Do not use transition: all. Only transition background, color, box-shadow, border-color, transform.",
    "Ensure focus-visible ring uses violet-600 and is clearly visible on white.",
    "All interactive/key info elements must have data-testid in JSX (buttons, inputs, tabs, nav items, modal actions, status text). If JSX edits are disallowed, at minimum add data-testid where already editable without structural changes."
  ],

  "concrete_css_rules": {
    "global": {
      "body": "background: var(--page); color: var(--ink);",
      "focus": "button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--violet); outline-offset:2px}"
    },

    "sidebar_light": {
      "target": ".sidebar, .side-brand, .side-label, .nav-item, .logout",
      "rules": [
        ".sidebar{background:#fff;color:var(--text_2,#334155);border-right:1px solid var(--line);box-shadow:none}",
        ".side-brand{color:var(--ink)} .side-brand small{color:var(--muted)}",
        ".side-label{color:var(--muted_2,#94a3b8)}",
        ".nav-item{color:var(--text_2,#334155);border:1px solid transparent}",
        ".nav-item:hover{background:var(--violet-50);color:var(--ink);border-color:var(--violet-100)}",
        ".nav-item.active{background:var(--violet-50);color:var(--ink);border-color:var(--violet-200);box-shadow:inset 3px 0 var(--violet)}",
        ".logout:hover{background:#f8fafc;color:var(--ink)}"
      ]
    },

    "topbar": {
      "target": ".topbar, .crumb, .icon-button, .avatar",
      "rules": [
        ".topbar{background:#fff;border-bottom:1px solid var(--line)}",
        ".icon-button:hover{background:var(--violet-50);color:var(--violet)}",
        ".avatar{background:var(--violet-100);color:var(--violet-800)}"
      ]
    },

    "hero_gradients": {
      "welcome_banner": "Use a mild 2-color gradient (<=20% viewport): linear-gradient(115deg, #ffffff, var(--violet-50)) with a thin violet border; keep text dark.",
      "student_hero": "Replace emerald hero with violet-tinted light hero: linear-gradient(135deg, #ffffff, var(--violet-50)); keep body text dark; use violet for CTA only.",
      "login_visual": "Keep photo, replace dark-blue overlay with violet ink overlay: linear-gradient(135deg, rgba(46,16,101,.92), rgba(124,58,237,.72)), url(...) center/cover; ensure text stays white."
    },

    "cards_panels": {
      "stat_cards": [
        ".stat-card,.panel{border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow-sm)}",
        ".stat-card:hover{box-shadow:var(--shadow-md);transform:translateY(-1px)}",
        ".stat-icon.blue{background:var(--violet-100);color:var(--violet-700)}",
        "Keep green/orange/red semantic icons as-is (only soften backgrounds if needed)."
      ],
      "panel_headers": ".panel-title h3{color:var(--ink)} .text-button{color:var(--violet)} .text-button:hover{color:var(--violet-700)}"
    },

    "buttons": {
      "primary": [
        ".primary{background:var(--violet);color:#fff;border-radius:10px;box-shadow:0 10px 18px -14px rgba(124,58,237,.55)}",
        ".primary:hover{background:var(--violet-700);transform:translateY(-1px);box-shadow:0 16px 26px -18px rgba(124,58,237,.55)}",
        ".primary:active{transform:translateY(0)}"
      ],
      "secondary": [
        ".secondary{background:#fff;border:1px solid var(--border_strong);color:var(--text_2);border-radius:10px}",
        ".secondary:hover{background:var(--violet-50);border-color:var(--violet-200);color:var(--ink)}"
      ]
    },

    "inputs_search": {
      "inputs": [
        "input,select{border:1px solid var(--border_strong);border-radius:10px}",
        "input:focus,select:focus{border-color:var(--violet-300)}",
        ".searchbox{border:1px solid var(--border_strong);border-radius:999px;background:#fff}",
        ".searchbox:focus-within{box-shadow:0 0 0 4px rgba(124,58,237,.14);border-color:var(--violet-300)}"
      ]
    },

    "tables": {
      "rules": [
        "th{color:var(--muted_2);border-bottom:1px solid var(--line)}",
        "td{border-bottom:1px solid #f1f2f8;color:var(--text_2)}",
        "tr:hover td{background:var(--violet-50)}"
      ]
    },

    "badges_status": {
      "soft_badge": ".soft-badge{background:var(--violet-50);color:var(--violet-700);border:1px solid var(--violet-100)}",
      "status": "Keep existing .status.{tersedia,dipinjam,hilang,habis} semantic colors; only adjust border-radius to pill if desired."
    },

    "tabs_segmented": {
      "report_tabs": [
        ".report-tabs{border-bottom:1px solid var(--line)}",
        ".report-tabs button{color:var(--muted);border-bottom-color:transparent}",
        ".report-tabs button:hover{color:var(--ink)}",
        ".report-tabs button.active{color:var(--violet);border-bottom-color:var(--violet)}"
      ],
      "mode_switch": [
        ".mode-switch{background:var(--violet-50);border:1px solid var(--violet-100)}",
        ".mode-switch button.selected{color:var(--violet);box-shadow:0 1px 2px rgba(15,23,42,.10)}"
      ]
    },

    "modals": {
      "rules": [
        ".modal-backdrop{background:rgba(15,23,42,.55)}",
        ".modal{border-radius:14px;border:1px solid var(--line);box-shadow:var(--shadow-lg)}",
        ".modal-head h3{color:var(--ink)}"
      ]
    },

    "micro_interactions": {
      "rules": [
        "Keep existing transitions but ensure they are limited to background,color,box-shadow,border-color,transform.",
        "Add hover lift only on cards/buttons (translateY(-1px)); never on tables/reading areas.",
        "Use reduced motion: @media (prefers-reduced-motion: reduce){*{scroll-behavior:auto} .primary,.secondary,.nav-item,.stat-card{transition:none;transform:none}}"
      ]
    }
  },

  "hex_remap_tables": {
    "blue_family_old_to_new_violet": [
      {"old":"#0284c7","new":"#7c3aed"},
      {"old":"#0369a1","new":"#6d28d9"},
      {"old":"#0f2745","new":"#ffffff"},
      {"old":"#14547c","new":"#ede9fe"},
      {"old":"#164167","new":"#f5f3ff"},
      {"old":"#193b5d","new":"#f5f3ff"},
      {"old":"#163754","new":"#ffffff"},
      {"old":"#1f4a6d","new":"#ddd6fe"},
      {"old":"#7dd3fc","new":"#a78bfa"},
      {"old":"#38bdf8","new":"#8b5cf6"},
      {"old":"#bae6fd","new":"#ddd6fe"},
      {"old":"#e0f2fe","new":"#ede9fe"},
      {"old":"#dbeafe","new":"#ede9fe"},
      {"old":"#eff6ff","new":"#f5f3ff"},
      {"old":"#f0f9ff","new":"#fbfbfe"},
      {"old":"#c7e5f5","new":"#c4b5fd"},
      {"old":"#075985","new":"#4c1d95"},
      {"old":"#7890ab","new":"#94a3b8"},
      {"old":"#9fb0c5","new":"#64748b"}
    ],
    "student_portal_emerald_family_old_to_violet_tint": [
      {"old":"#047857","new":"#4c1d95"},
      {"old":"#059669","new":"#6d28d9"},
      {"old":"#10b981","new":"#7c3aed"},
      {"old":"#34d399","new":"#a78bfa"},
      {"old":"#6ee7b7","new":"#ddd6fe"},
      {"old":"#d1fae5","new":"#f5f3ff"}
    ]
  },

  "image_urls": {
    "login_visual_photo_existing": {
      "category": "login",
      "description": "Keep existing Unsplash photo; only change overlay gradient.",
      "url": "https://images.unsplash.com/photo-1544185310-0b3cf501672b?auto=format&fit=crop&w=1400&q=80"
    }
  },

  "append_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>  \n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
