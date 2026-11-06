/* =====================================================================
   NumLock Light 1.0.3 — settings UI logic
   Fixes:
   - CRITICAL: wait for the pywebview API to be *populated*, not merely
     truthy. pywebview injects `window.pywebview = {api:{}, ...}` first and
     only fills `api` (firing `pywebviewready`) in a SECOND script; the old
     `window.pywebview && window.pywebview.api` check passed during that
     gap, so `BRIDGE.get_manifest()` threw "not a function", the async
     boot() died and NO event handlers were ever bound — a rendered but
     completely dead settings window.
   - boot() is now fault-tolerant: every await has its own fallback, nav
     binding happens first, and a failed bridge retries instead of killing
     the UI. When running on mock data a visible warning toast is shown.
   - Bridge calls resolve dynamically on EVERY call: real API when present,
     mock otherwise (a late-arriving bridge is picked up automatically).
   - Quit button in the sidebar footer so the app is always controllable
     even when the tray icon is unavailable.
   ===================================================================== */
"use strict";

/* ---------------------------------- i18n ---------------------------- */
const STR = {
  fa: {
    sec_general: "عمومی", sec_general_sub: "وضعیت برنامه و گزینه‌های پایه",
    sec_keys: "کلیدها", sec_keys_sub: "کلیدهای زیر نظر و رنگ‌های هر کدام — با کلیک روی کاشی بالای صفحه هم می‌توانید وضعیت کلید را عوض کنید",
    sec_appearance: "ظاهر و آیکون", sec_appearance_sub: "تم، مدل آیکون نشانگر و اندازه آن",
    sec_osd: "اعلان روی صفحه (OSD)", sec_osd_sub: "نمایش اعلان هنگام روشن یا خاموش شدن کلیدها",
    sec_sound: "صدا", sec_sound_sub: "افکت صوتی هنگام روشن یا خاموش شدن کلیدها",
    sec_about: "درباره",
    language: "زبان برنامه", language_hint: "زبان رابط کاربری؛ چیدمان به‌صورت خودکار راست‌چین یا چپ‌چین می‌شود",
    indicator_enabled: "فعال بودن نشانگر", indicator_enabled_hint: "آیکون وضعیت در نوار وظیفه ویندوز",
    startup: "اجرای خودکار با شروع ویندوز", startup_hint: "افزودن برنامه به فهرست Startup کاربر",
    balloon: "اعلان ویندوزی هنگام تغییر وضعیت", balloon_hint: "نمایش اعلان بالون در کنار آیکون برنامه",
    tray_mode: "آیکون در نوار وظیفه", tray_mode_hint: "جدا برای هر کلید، یا یک آیکون ترکیبی",
    tray_per_key: "جدا برای هر کلید", tray_single: "یک آیکون ترکیبی",
    state_text: "نمایش متن وضعیت در راهنمای آیکون", state_text_hint: "هنگام نگه‌داشتن ماوس روی آیکون",
    poll: "سرعت بررسی وضعیت", poll_hint: "مثلاً ۱۵۰ میلی‌ثانیه — عدد کوچک‌تر یعنی واکنش سریع‌تر",
    ms: "میلی‌ثانیه",
    theme: "تم برنامه", theme_dark: "تاریک", theme_light: "روشن",
    icon_style: "مدل آیکون نشانگر", icon_style_hint: "پیش‌نمایش واقعی هر مدل با وضعیت روشن",
    icon_size: "اندازه آیکون نشانگر",
    size_sm: "کوچک", size_md: "متوسط", size_lg: "بزرگ",
    live_preview: "پیش‌نمایش زنده نوار وظیفه", live_preview_hint: "دقیقاً همان چیزی که الان کنار ساعت می‌بینید",
    osd_enabled: "نمایش اعلان هنگام تغییر وضعیت", osd_enabled_hint: "یک کارت شیشه‌ای کنار صفحه نمایش",
    osd_duration: "مدت نمایش", osd_duration_hint: "چقدر روی صفحه بماند",
    osd_seconds: "ثانیه",
    osd_scale: "بزرگی نمایش", osd_scale_hint: "اندازه کارت اعلان",
    osd_position: "محل نمایش",
    osd_arrange: "جابه‌جایی با کشیدن ماوس",
    osd_arrange_hint: "اعلان روی صفحه ظاهر می‌شود؛ با ماوس آن را بکشید و هرجا خواستید رها کنید — دابل‌کلیک یا Enter برای ذخیره، Esc برای لغو",
    osd_preview: "پیش‌نمایش اعلان",
    sound_enabled: "پخش صدا هنگام تغییر وضعیت", sound_enabled_hint: "صدای جدا برای روشن و خاموش شدن",
    ui_click: "صدای کلیک برای دکمه‌های برنامه", ui_click_hint: "افکت ظریف هنگام کار با تنظیمات",
    volume: "میزان صدا", volume_hint: "میزان بلندی افکت‌های صوتی برنامه",
    sound_on: "صدای روشن شدن", sound_off: "صدای خاموش شدن",
    monitor_key: "پایش این کلید", show_off: "نمایش آیکون در حالت خاموش",
    show_off_hint: "اگر خاموش باشد، آیکون قرمز دیده می‌شود",
    color_on: "رنگ حالت روشن", color_off: "رنگ حالت خاموش",
    on: "روشن", off: "خاموش", monitoring_off: "پایش خاموش",
    reset: "بازنشانی تنظیمات",
    saved: "ذخیره شد", reset_done: "تنظیمات به حالت پیش‌فرض برگشت",
    startup_failed: "تنظیم اجرای خودکار انجام نشد",
    about_app: "نشانگر هوشمند کلیدهای کیبورد برای ویندوز",
    app_name_fa: "نام‌لاک لایت",
    developer: "طراح و توسعه‌دهنده", website: "وب‌سایت",
    open_github: "صفحه پروژه در گیت‌هاب",
    credits: "اعتبارات و منابع آزاد",
    credit_sounds: "افکت‌های صوتی", credit_icons: "آیکون‌ها",
    license_note: "این برنامه با مجوز MIT منتشر شده است.",
    click_tile_hint: "برای تغییر وضعیت کلیک کنید",
    none: "بدون صدا", play: "پخش",
    quit: "خروج از برنامه",
    bridge_dead: "ارتباط با برنامه برقرار نشد — نمایش داده‌ها آزمایشی است",
  },
  en: {
    sec_general: "General", sec_general_sub: "Program status and basic options",
    sec_keys: "Keys", sec_keys_sub: "Monitored keys and their colors — you can also click the tiles at the top to toggle a key",
    sec_appearance: "Appearance", sec_appearance_sub: "Theme, indicator icon style and size",
    sec_osd: "On-screen display", sec_osd_sub: "Notification shown when a key turns on or off",
    sec_sound: "Sound", sec_sound_sub: "Sound effects on key state changes",
    sec_about: "About",
    language: "UI language", language_hint: "Layout flips to RTL or LTR automatically",
    indicator_enabled: "Indicator enabled", indicator_enabled_hint: "Status icon in the Windows taskbar",
    startup: "Start with Windows", startup_hint: "Adds the program to the user Startup list",
    balloon: "Windows notification on change", balloon_hint: "Balloon tip next to the tray icon",
    tray_mode: "Taskbar icon", tray_mode_hint: "One icon per key, or a single combined icon",
    tray_per_key: "Per key", tray_single: "Single combined",
    state_text: "Show state text in icon tooltip", state_text_hint: "When hovering the icon",
    poll: "Poll rate", poll_hint: "e.g. 150 ms — smaller means faster reaction",
    ms: "ms",
    theme: "Theme", theme_dark: "Dark", theme_light: "Light",
    icon_style: "Indicator icon style", icon_style_hint: "Real preview of every style in the ON state",
    icon_size: "Indicator icon size",
    size_sm: "Small", size_md: "Medium", size_lg: "Large",
    live_preview: "Live taskbar preview", live_preview_hint: "Exactly what you see next to the clock right now",
    osd_enabled: "Show notification on change", osd_enabled_hint: "A glass card at the edge of the screen",
    osd_duration: "Duration", osd_duration_hint: "How long it stays on screen",
    osd_seconds: "s",
    osd_scale: "Size", osd_scale_hint: "Scale of the notification card",
    osd_position: "Position",
    osd_arrange: "Drag to place",
    osd_arrange_hint: "The notification appears on screen; drag it anywhere with the mouse — double-click or Enter to save, Esc to cancel",
    osd_preview: "Preview notification",
    sound_enabled: "Play sound on change", sound_enabled_hint: "Separate sounds for on and off",
    ui_click: "Click sound for app buttons", ui_click_hint: "Subtle effect while using settings",
    volume: "Volume", volume_hint: "Loudness of the app sound effects",
    sound_on: "Turn-on sound", sound_off: "Turn-off sound",
    monitor_key: "Monitor this key", show_off: "Show icon when off",
    show_off_hint: "When off, the icon shows in red",
    color_on: "ON color", color_off: "OFF color",
    on: "ON", off: "OFF", monitoring_off: "not monitored",
    reset: "Reset settings",
    saved: "Saved", reset_done: "Settings restored to defaults",
    startup_failed: "Could not change startup",
    about_app: "Smart keyboard lock-key indicator for Windows",
    app_name_fa: "نام‌لاک لایت",
    developer: "Designed & developed by", website: "Website",
    open_github: "Project on GitHub",
    credits: "Credits & free resources",
    credit_sounds: "Sound effects", credit_icons: "Icons",
    license_note: "Released under the MIT license.",
    click_tile_hint: "Click to toggle",
    none: "No sound", play: "Play",
    quit: "Quit application",
    bridge_dead: "Cannot reach the app — showing sample data",
  },
};

/* ---------------------------------- mock ---------------------------- */
const MOCK = {
  manifest: {
    version: "1.1.0", author: "sadri1993", website: "https://100ri.ir",
    github: "https://github.com/100ri-ir/NumLockLight",
    system: "Windows 11",
    keys: {
      num:    { keycap: "Num",   name: "نام لاک",   hint: "قفل صفحه اعداد سمت راست کیبورد" },
      caps:   { keycap: "Caps",  name: "کپس لاک",  hint: "قفل حروف بزرگ انگلیسی" },
      scroll: { keycap: "ScrLk", name: "اسکرول لاک",hint: "قفل اسکرول (در بعضی کیبوردها)" },
      insert: { keycap: "Ins",   name: "اینسرت",     hint: "حالت درج/بازنویسی هنگام تایپ" },
    },
    styles: {
      badge:  { fa: "نشان حرفی", en: "Letter badge" },
      keycap: { fa: "کلید کیبورد", en: "Keycap" },
      led:    { fa: "کلاسیک (LED)", en: "Classic LED" },
      ring:   { fa: "حلقه", en: "Ring" },
      glow:   { fa: "مهتابی", en: "Orb" },
      icon:   { fa: "آیکون کیبورد", en: "Keyboard icon" },
    },
    sounds_on: ["chime", "glass", "rise", "select", "none"],
    sounds_off: ["fall", "tick", "soft", "none"],
    webview2: true,
    font_css: "",
  },
  settings: {
    language: "fa", enabled: true, startup: false, balloon: false, poll_ms: 150,
    theme: "dark",
    keys: {
      num:    { enabled: true,  color_on: "#22c55e", color_off: "#ef4444", show_off: true },
      caps:   { enabled: true,  color_on: "#22c55e", color_off: "#ef4444", show_off: true },
      scroll: { enabled: false, color_on: "#22c55e", color_off: "#ef4444", show_off: true },
      insert: { enabled: false, color_on: "#22c55e", color_off: "#ef4444", show_off: true },
    },
    tray: { mode: "per_key", style: "badge", size: "md", state_text: true },
    osd: { enabled: true, position: "bottom_center", custom_x: 0.5, custom_y: 0.92, duration_ms: 1200, scale: 1.0 },
    sound: { enabled: false, on_sound: "chime", off_sound: "tick", volume: 70, ui_click: false },
  },
  states: { num: true, caps: false, scroll: false, insert: false },
  startup: false,
};

function getBridge() {
  if (window.pywebview && window.pywebview.api) {
    return window.pywebview.api;
  }
  return new Proxy({}, { get: (_t, prop) => (...args) => mockCall(prop, args) });
}

/* Resolve EVERY call dynamically: use the real bridge when the method
   exists, fall back to the mock otherwise. This survives the injection
   race, late bridges and partial API exposure. */
const BRIDGE = new Proxy({}, {
  get: (_t, prop) => (...args) => {
    const api = (window.pywebview && window.pywebview.api) || null;
    if (api && typeof api[prop] === "function") {
      try {
        return api[prop](...args);
      } catch (e) {
        return mockCall(prop, args);
      }
    }
    return mockCall(prop, args);
  }
});

/* True only when the pywebview API has actually been populated.
   (api is `{}` — truthy — between the first and second injected script.) */
function bridgeReady() {
  try {
    return !!(
      window.pywebview &&
      window.pywebview.api &&
      Object.keys(window.pywebview.api).length > 0
    );
  } catch (e) {
    return false;
  }
}

function mockCall(fn, args) {
  const s = MOCK.settings;
  switch (fn) {
    case "get_manifest": return Promise.resolve(MOCK.manifest);
    case "get_settings": return Promise.resolve(s);
    case "get_states": return Promise.resolve({ ...MOCK.states });
    case "get_startup": return Promise.resolve(MOCK.startup);
    case "set_setting": {
      const [path, value] = args;
      setDeep(MOCK.settings, path, value);
      return Promise.resolve({ ok: true });
    }
    case "toggle_key": {
      const kid = args[0];
      MOCK.states[kid] = !MOCK.states[kid];
      return Promise.resolve({ ...MOCK.states });
    }
    case "set_startup": MOCK.startup = args[0]; return Promise.resolve({ ok: true, error: "" });
    case "set_language": s.language = args[0]; return Promise.resolve({ ok: true });
    case "get_icon_previews": {
      const out = {};
      for (const st of Object.keys(MOCK.manifest.styles)) {
        out[st] = "data:image/svg+xml;utf8," + encodeURIComponent(
          `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72"><rect x="8" y="8" width="56" height="56" rx="17" fill="#22c55e"/><text x="36" y="47" font-family="Vazirmatn,Arial" font-weight="bold" font-size="28" fill="#fff" text-anchor="middle">N</text></svg>`
        );
      }
      return Promise.resolve(out);
    }
    case "get_tray_preview": {
      const kids = ["num", "caps"];
      return Promise.resolve(kids.map((k) =>
        "data:image/svg+xml;utf8," + encodeURIComponent(
          `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><rect x="5" y="5" width="38" height="38" rx="11" fill="${MOCK.states[k] ? "#22c55e" : "#4b5563"}"/><text x="24" y="32" font-family="Vazirmatn,Arial" font-weight="bold" font-size="19" fill="#fff" text-anchor="middle">${k[0].toUpperCase()}</text></svg>`)));
    }
    default: return Promise.resolve({ ok: true });
  }
}

function setDeep(obj, path, value) {
  const parts = path.split(".");
  let o = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    if (o[parts[i]] === undefined) o[parts[i]] = {};
    o = o[parts[i]];
  }
  o[parts[parts.length - 1]] = value;
}

/* ---------------------------------- helpers ------------------------- */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

let LANG = "fa";
let M = null;          // manifest
let S = null;          // settings
let STATES = {};
let STYLE_PREVIEWS = {};
let slidersBound = false;
let trayPreviewTimer = null;
let onMockData = false;   // true when boot() fell back to MOCK data
let uiActivated = false;  // true once handlers are bound

const PD = ["۰","۱","۲","۳","۴","۵","۶","۷","۸","۹"];
function toFa(n) { return String(n).replace(/\d/g, (d) => PD[+d]); }
function num(n, lang) { return (lang || LANG) === "fa" ? toFa(n) : String(n); }
function t(key) {
  const d = STR[LANG] || STR.fa;
  return d[key] !== undefined ? d[key] : (STR.fa[key] !== undefined ? STR.fa[key] : key);
}

function injectFonts(cssText) {
  if (!cssText) return;
  let styleEl = document.getElementById("vazir-embedded-fonts");
  if (!styleEl) {
    styleEl = document.createElement("style");
    styleEl.id = "vazir-embedded-fonts";
    document.head.insertBefore(styleEl, document.head.firstChild);
  }
  styleEl.textContent = cssText;
}

function toast(msg) {
  const container = $("#toasts");
  if (!container) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span class="tdot"></span><span></span>`;
  el.lastElementChild.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 260);
  }, 1800);
}

function uiClick() { BRIDGE.ui_click().catch(() => {}); }

function statesEqual(a, b) {
  if (!a || !b) return false;
  const keys = ["num", "caps", "scroll", "insert"];
  for (const k of keys) {
    if (Boolean(a[k]) !== Boolean(b[k])) return false;
  }
  return true;
}

/* ---------------------------------- i18n apply ---------------------- */
function applyLanguage() {
  document.documentElement.lang = LANG;
  document.documentElement.dir = LANG === "fa" ? "rtl" : "ltr";
  $$("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = t(key);
    if (val !== undefined) el.textContent = val;
  });
}

/* ---------------------------------- key strip ----------------------- */
function renderKeyStrip() {
  const strip = $("#keystrip");
  strip.innerHTML = "";
  for (const [kid, meta] of Object.entries(M.keys)) {
    const k = S.keys[kid];
    const on = !!STATES[kid];
    const tile = document.createElement("button");
    tile.className = "ktile " + (k.enabled ? (on ? "on" : "off") : "disabled");
    tile.dataset.kid = kid;
    tile.title = k.enabled ? t("click_tile_hint") : t("monitoring_off");
    tile.innerHTML = `
      <span class="kcap">${meta.keycap}</span>
      <span class="kmeta">
        <span class="kname"></span>
        <span class="kstate"><span class="kdot"></span><span class="kst-txt"></span></span>
      </span>`;
    tile.querySelector(".kname").textContent = meta.name;
    tile.querySelector(".kst-txt").textContent =
      k.enabled ? (on ? t("on") : t("off")) : t("monitoring_off");
    tile.addEventListener("click", () => {
      if (!S.keys[kid].enabled) return;
      uiClick();
      BRIDGE.toggle_key(kid).then((st) => {
        if (st) {
          STATES = st;
          refreshStates(true);
        }
      }).catch(() => {});
    });
    strip.appendChild(tile);
  }
}

function refreshStates(animate) {
  $$(".ktile").forEach((tile) => {
    const kid = tile.dataset.kid;
    const k = S.keys[kid];
    const on = !!STATES[kid];
    const was = tile.classList.contains("on");
    tile.className = "ktile " + (k.enabled ? (on ? "on" : "off") : "disabled");
    tile.querySelector(".kst-txt").textContent =
      k.enabled ? (on ? t("on") : t("off")) : t("monitoring_off");
    if (animate && k.enabled && was !== on) {
      tile.classList.add("flash");
      setTimeout(() => tile.classList.remove("flash"), 500);
    }
  });
  $$(".keycard").forEach((card) => {
    const kid = card.dataset.kid;
    const k = S.keys[kid];
    const on = !!STATES[kid];
    card.classList.toggle("lit", k.enabled && on);
    card.classList.toggle("muted", !k.enabled);
    const live = card.querySelector(".kc-live");
    if (live) {
      live.className = "kc-live " + (k.enabled ? (on ? "on" : "off") : "off");
      live.textContent = k.enabled ? (on ? t("on") : t("off")) : t("monitoring_off");
    }
  });
  scheduleTrayPreview();
}

/* ---------------------------------- key cards ----------------------- */
const PRESETS = ["#22c55e", "#38bdf8", "#f59e0b", "#a78bfa", "#f43f5e", "#ef4444"];

function renderKeyCards() {
  const wrap = $("#keycards");
  wrap.innerHTML = "";
  for (const [kid, meta] of Object.entries(M.keys)) {
    const k = S.keys[kid];
    const card = document.createElement("div");
    card.className = "keycard";
    card.dataset.kid = kid;
    card.innerHTML = `
      <div class="kc-head">
        <span class="kc-cap">${meta.keycap}</span>
        <div class="kc-titles">
          <div class="kc-name">${meta.name}</div>
          <div class="kc-hint">${meta.hint}</div>
        </div>
        <span class="kc-live"></span>
      </div>
      <div class="kc-rows">
        <div class="kc-row">
          <span class="kc-label">${t("monitor_key")}</span>
          <label class="switch"><input type="checkbox" data-set="keys.${kid}.enabled" ${k.enabled ? "checked" : ""}><span class="knob"></span></label>
        </div>
        <div class="kc-row">
          <span class="kc-label">${t("color_on")}</span>
          <div class="colorline">
            <div class="presets">${PRESETS.map((c) => `<span class="preset" data-target="keys.${kid}.color_on" style="background:${c}"></span>`).join("")}</div>
            <span class="colorswatch" style="background:${k.color_on}"><input type="color" value="${k.color_on}" data-set="keys.${kid}.color_on"></span>
            <span class="hexcode">${k.color_on}</span>
          </div>
        </div>
        <div class="kc-row">
          <span class="kc-label">${t("color_off")}</span>
          <div class="colorline">
            <div class="presets">${PRESETS.map((c) => `<span class="preset" data-target="keys.${kid}.color_off" style="background:${c}"></span>`).join("")}</div>
            <span class="colorswatch" style="background:${k.color_off}"><input type="color" value="${k.color_off}" data-set="keys.${kid}.color_off"></span>
            <span class="hexcode">${k.color_off}</span>
          </div>
        </div>
        <div class="kc-row">
          <span class="kc-label">${t("show_off")}<small>${t("show_off_hint")}</small></span>
          <label class="switch"><input type="checkbox" data-set="keys.${kid}.show_off" ${k.show_off ? "checked" : ""}><span class="knob"></span></label>
        </div>
      </div>`;
    wrap.appendChild(card);
  }
  bindControls(wrap);
}

/* ---------------------------------- appearance ---------------------- */
function renderStyleGrid() {
  const grid = $("#stylegrid");
  grid.innerHTML = "";
  for (const [sid, meta] of Object.entries(M.styles)) {
    const el = document.createElement("button");
    el.className = "stylecard" + (S.tray.style === sid ? " selected" : "");
    el.dataset.style = sid;
    const img = STYLE_PREVIEWS[sid] || "";
    el.innerHTML = `<img src="${img}" alt=""><span class="sc-name"></span><span class="sc-desc"></span>`;
    el.querySelector(".sc-name").textContent = meta[LANG] || meta.fa;
    if (meta.desc) {
      el.querySelector(".sc-desc").textContent = meta.desc;
    }
    el.addEventListener("click", () => {
      S.tray.style = sid;
      BRIDGE.set_setting("tray.style", sid).catch(() => {});
      $$(".stylecard").forEach((c) => c.classList.toggle("selected", c.dataset.style === sid));
      scheduleTrayPreview();
      uiClick();
    });
    grid.appendChild(el);
  }
}

function scheduleTrayPreview() {
  clearTimeout(trayPreviewTimer);
  trayPreviewTimer = setTimeout(renderTrayPreview, 60);
}

async function renderTrayPreview() {
  try {
    const icons = await BRIDGE.get_tray_preview(S.tray.style, S.tray.size);
    const box = $("#traymock-icons");
    if (!box) return;
    box.innerHTML = "";
    if (Array.isArray(icons)) {
      icons.forEach((src) => {
        const img = document.createElement("img");
        img.src = src;
        img.alt = "";
        box.appendChild(img);
      });
    }
  } catch (e) { /* noop */ }
}

/* ---------------------------------- OSD ----------------------------- */
function renderPosGrid() {
  const grid = $("#posgrid");
  grid.innerHTML = "";
  const POS = [
    ["top_left", "p4 p1"], ["top_center", "p1"], ["top_right", "p1 p5"],
    ["middle_left", "p4 p2"], ["center", "p2"], ["middle_right", "p2 p5"],
    ["bottom_left", "p4 p3"], ["bottom_center", "p3"], ["bottom_right", "p3 p5"],
  ];
  for (const [pos, cls] of POS) {
    const b = document.createElement("button");
    b.className = "posbtn " + cls + (S.osd.position === pos ? " active" : "");
    b.dataset.pos = pos;
    b.title = pos.replace(/_/g, " ");
    b.addEventListener("click", () => {
      S.osd.position = pos;
      BRIDGE.set_setting("osd.position", pos).catch(() => {});
      $$(".posbtn").forEach((x) => x.classList.toggle("active", x.dataset.pos === pos));
      uiClick();
    });
    grid.appendChild(b);
  }
}

/* ---------------------------------- sound --------------------------- */
function renderSoundGrids() {
  const mk = (wrapId, list, settingKey) => {
    const wrap = $(wrapId);
    wrap.innerHTML = "";
    const labels = {
      chime: LANG === "fa" ? "چایم تأیید" : "Confirm chime",
      glass: LANG === "fa" ? "زنگ شیشه‌ای" : "Glass ring",
      rise: LANG === "fa" ? "ملایم صعودی" : "Soft rise",
      select: LANG === "fa" ? "انتخاب" : "Select",
      fall: LANG === "fa" ? "ملایم نزولی" : "Soft fall",
      tick: LANG === "fa" ? "تیک کوتاه" : "Short tick",
      soft: LANG === "fa" ? "نرم شیشه‌ای" : "Glass soft",
      none: t("none"),
    };
    for (const name of list) {
      const card = document.createElement("div");
      card.className = "soundcard" + (S.sound[settingKey] === name ? " selected" : "");
      card.dataset.name = name;
      card.innerHTML = `
        <span class="sd-name">${labels[name] || name}</span>
        <button class="playbtn" title="${t("play")}" ${name === "none" ? "style='visibility:hidden'" : ""}>
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        </button>`;
      card.querySelector(".playbtn").addEventListener("click", (ev) => {
        ev.stopPropagation();
        BRIDGE.play_sound(name, S.sound.volume).catch(() => {});
      });
      card.addEventListener("click", () => {
        S.sound[settingKey] = name;
        BRIDGE.set_setting("sound." + settingKey, name).catch(() => {});
        $$(wrapId + " .soundcard").forEach((c) => c.classList.toggle("selected", c.dataset.name === name));
        if (name !== "none") BRIDGE.play_sound(name, S.sound.volume).catch(() => {});
        uiClick();
      });
      wrap.appendChild(card);
    }
  };
  mk("#soundgrid-on", M.sounds_on, "on_sound");
  mk("#soundgrid-off", M.sounds_off, "off_sound");
}

/* ---------------------------------- segmented ----------------------- */
function bindSegments() {
  const segLang = $("#seg-language");
  segLang.querySelectorAll("button").forEach((b) => {
    b.classList.toggle("active", S.language === b.dataset.val);
    b.addEventListener("click", async () => {
      LANG = b.dataset.val;
      S.language = b.dataset.val;
      await BRIDGE.set_language(b.dataset.val).catch(() => {});
      M = await BRIDGE.get_manifest().catch(() => M);
      segLang.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
      applyLanguage();
      renderAll();
      toast(t("saved"));
    });
  });

  const bindSeg = (id, path, cb) => {
    const seg = $(id);
    if (!seg) return;
    seg.querySelectorAll("button").forEach((b) => {
      b.addEventListener("click", () => {
        const v = b.dataset.val;
        setDeep(S, path, v);
        BRIDGE.set_setting(path, v).catch(() => {});
        seg.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
        if (cb) cb(v);
        uiClick();
      });
    });
  };
  bindSeg("#seg-traymode", "tray.mode", () => scheduleTrayPreview());
  bindSeg("#seg-theme", "theme", (v) => document.body.dataset.theme = v);
  bindSeg("#seg-iconsize", "tray.size", () => scheduleTrayPreview());
}

function refreshSegments() {
  const mark = (id, val) => {
    const seg = $(id);
    if (seg) seg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.val === val));
  };
  mark("#seg-language", S.language);
  mark("#seg-traymode", S.tray.mode);
  mark("#seg-theme", S.theme);
  mark("#seg-iconsize", S.tray.size);
  document.body.dataset.theme = S.theme;
}

/* ---------------------------------- sliders ------------------------- */
function fillRange(input) {
  const min = +input.min, max = +input.max, val = +input.value;
  input.style.setProperty("--fill", ((val - min) / (max - min) * 100) + "%");
}

function updateSlidersUI() {
  const rgPoll = $("#rg-poll");
  const rgDur = $("#rg-duration");
  const rgScale = $("#rg-scale");
  const rgVol = $("#rg-volume");
  if (!rgPoll) return;

  rgPoll.value = S.poll_ms;
  rgDur.value = Math.round(S.osd.duration_ms / 100);
  rgScale.value = Math.round(S.osd.scale * 100);
  rgVol.value = S.sound.volume;

  [rgPoll, rgDur, rgScale, rgVol].forEach(fillRange);
}

function bindSlidersOnce() {
  if (slidersBound) {
    updateSlidersUI();
    return;
  }
  slidersBound = true;

  const rgPoll = $("#rg-poll");
  rgPoll.addEventListener("input", () => {
    fillRange(rgPoll);
    $("#poll-chip").textContent = num(rgPoll.value);
    S.poll_ms = +rgPoll.value;
  });
  rgPoll.addEventListener("change", () => {
    BRIDGE.set_setting("poll_ms", +rgPoll.value).catch(() => {});
    uiClick();
  });

  const rgDur = $("#rg-duration");
  rgDur.addEventListener("input", () => {
    fillRange(rgDur);
    const secs = (rgDur.value / 10).toFixed(1);
    $("#dur-chip").textContent = num(secs).replace(".", LANG === "fa" ? "٫" : ".");
  });
  rgDur.addEventListener("change", () => {
    S.osd.duration_ms = rgDur.value * 100;
    BRIDGE.set_setting("osd.duration_ms", S.osd.duration_ms).catch(() => {});
    uiClick();
  });

  const rgScale = $("#rg-scale");
  rgScale.addEventListener("input", () => {
    fillRange(rgScale);
    $("#scale-chip").textContent = num(rgScale.value) + (LANG === "fa" ? "٪" : "%");
  });
  rgScale.addEventListener("change", () => {
    S.osd.scale = rgScale.value / 100;
    BRIDGE.set_setting("osd.scale", S.osd.scale).catch(() => {});
    uiClick();
  });

  const rgVol = $("#rg-volume");
  rgVol.addEventListener("input", () => {
    fillRange(rgVol);
    $("#vol-chip").textContent = num(rgVol.value) + (LANG === "fa" ? "٪" : "%");
  });
  rgVol.addEventListener("change", () => {
    S.sound.volume = +rgVol.value;
    BRIDGE.set_setting("sound.volume", S.sound.volume).catch(() => {});
    BRIDGE.play_sound(S.sound.on_sound === "none" ? "select" : S.sound.on_sound, S.sound.volume).catch(() => {});
  });

  updateSlidersUI();
}

/* ---------------------------------- generic controls ---------------- */
function bindControls(root) {
  root.querySelectorAll("input[type=checkbox][data-set]").forEach((chk) => {
    if (chk.dataset.bound === "1") return;
    chk.dataset.bound = "1";
    const path = chk.dataset.set;
    // Sync initial state from S
    const parts = path.split(".");
    let cur = S;
    for (const p of parts) { if (cur !== undefined) cur = cur[p]; }
    if (typeof cur === "boolean") chk.checked = cur;

    chk.addEventListener("change", () => {
      setDeep(S, path, chk.checked);
      BRIDGE.set_setting(path, chk.checked).catch(() => {});
      if (path.startsWith("keys.")) refreshStates(false);
      uiClick();
    });
  });

  root.querySelectorAll("input[type=color][data-set]").forEach((inp) => {
    if (inp.dataset.bound === "1") return;
    inp.dataset.bound = "1";
    inp.addEventListener("input", () => {
      const path = inp.dataset.set;
      setDeep(S, path, inp.value);
      const swatch = inp.closest(".colorline").querySelector(".colorswatch");
      const hex = inp.closest(".colorline").querySelector(".hexcode");
      if (swatch) swatch.style.background = inp.value;
      if (hex) hex.textContent = inp.value;
    });
    inp.addEventListener("change", () => {
      const path = inp.dataset.set;
      setDeep(S, path, inp.value);
      BRIDGE.set_setting(path, inp.value).then(() => {
        if (path === "keys.num.color_on") {
          BRIDGE.get_icon_previews().then((pr) => {
            if (pr) { STYLE_PREVIEWS = pr; renderStyleGrid(); }
          }).catch(() => {});
        }
        scheduleTrayPreview();
      }).catch(() => {});
      uiClick();
    });
  });

  root.querySelectorAll(".preset").forEach((p) => {
    if (p.dataset.bound === "1") return;
    p.dataset.bound = "1";
    p.addEventListener("click", () => {
      const target = p.dataset.target;
      const color = p.style.background;
      const inp = p.closest(".colorline").querySelector("input[type=color]");
      const hex = rgbToHex(color);
      if (inp) {
        inp.value = hex;
        inp.dispatchEvent(new Event("input"));
        inp.dispatchEvent(new Event("change"));
      }
      setDeep(S, target, hex);
    });
  });
}

function rgbToHex(rgb) {
  if (rgb.startsWith("#")) return rgb;
  const m = rgb.match(/\d+/g);
  if (!m) return rgb;
  return "#" + m.slice(0, 3).map((x) => (+x).toString(16).padStart(2, "0")).join("");
}

/* ---------------------------------- nav / titlebar ------------------ */
function bindNav() {
  $$(".navitem").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".navitem").forEach((b) => b.classList.toggle("active", b === btn));
      $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + btn.dataset.section));
      uiClick();
    });
  });
  $("#btn-minimize").addEventListener("click", () => {
    BRIDGE.minimize_window().catch(() => {});
  });
  $("#btn-close").addEventListener("click", () => {
    BRIDGE.close_window().catch(() => window.close());
  });
  $("#btn-reset").addEventListener("click", async () => {
    const fresh = await BRIDGE.reset_settings().catch(() => null);
    if (fresh) {
      S = fresh;
      LANG = S.language === "en" ? "en" : "fa";
      M = await BRIDGE.get_manifest().catch(() => M);
      renderAll();
      toast(t("reset_done"));
    }
  });
  $("#btn-osd-preview").addEventListener("click", () => {
    BRIDGE.osd_preview().catch(() => {});
    uiClick();
  });
  $("#btn-arrange").addEventListener("click", () => {
    BRIDGE.osd_arrange().catch(() => {});
    uiClick();
  });
  $("#lnk-website").addEventListener("click", () => BRIDGE.open_url(M.website).catch(() => {}));
  $("#lnk-github").addEventListener("click", () => BRIDGE.open_url(M.github).catch(() => {}));

  const btnQuit = $("#btn-quit");
  if (btnQuit) {
    btnQuit.addEventListener("click", () => {
      try {
        BRIDGE.quit_app().catch(() => {});
      } catch (e) { /* noop */ }
      // Safety net: if the bridge is dead, try closing the window itself.
      setTimeout(() => { try { window.close(); } catch (e) { /* noop */ } }, 800);
    });
  }

  const chkStartup = $("#chk-startup");
  chkStartup.addEventListener("change", async () => {
    const res = await BRIDGE.set_startup(chkStartup.checked).catch(() => ({ ok: false, error: "x" }));
    if (!res || res.ok === false) {
      chkStartup.checked = !chkStartup.checked;
      toast(t("startup_failed"));
    } else {
      S.startup = chkStartup.checked;
    }
    uiClick();
  });
}

/* ---------------------------------- clock --------------------------- */
function tickClock() {
  const el = $("#traymock-clock");
  if (!el) return;
  const d = new Date();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  el.textContent = hh + ":" + mm;
}

/* ---------------------------------- boot ---------------------------- */
function renderAll() {
  if (!M || !S) return;
  applyLanguage();
  renderKeyStrip();
  renderKeyCards();
  renderStyleGrid();
  renderPosGrid();
  renderSoundGrids();
  refreshSegments();
  bindSlidersOnce();
  refreshStates(false);
  $("#verchip").textContent = "v" + M.version;
  $("#about-ver").textContent = "v" + M.version;
  $("#about-sys").textContent = M.system || "";
  $("#poll-chip").textContent = num(S.poll_ms);
  $("#dur-chip").textContent = num((S.osd.duration_ms / 1000).toFixed(1)).replace(".", LANG === "fa" ? "٫" : ".");
  $("#scale-chip").textContent = num(Math.round(S.osd.scale * 100)) + (LANG === "fa" ? "٪" : "%");
  $("#vol-chip").textContent = num(S.sound.volume) + (LANG === "fa" ? "٪" : "%");
}

/* Bind the window chrome FIRST so the settings window is always usable
   (navigable, closable, quittable) even if data loading fails. */
function activateUI() {
  if (uiActivated) return;
  uiActivated = true;
  bindNav();
  bindSegments();
  bindControls(document);
  tickClock();
  setInterval(tickClock, 15000);
}

let pollTimerStarted = false;

async function boot(isRetry) {
  // --- data acquisition, each step with its own fallback -------------
  let failed = false;
  try { M = await BRIDGE.get_manifest(); } catch (e) { M = MOCK.manifest; failed = true; }
  if (M && M.font_css) injectFonts(M.font_css);
  try { S = await BRIDGE.get_settings(); } catch (e) { S = MOCK.settings; failed = true; }
  try { STATES = await BRIDGE.get_states(); } catch (e) { STATES = { ...MOCK.states }; failed = true; }
  try { STYLE_PREVIEWS = await BRIDGE.get_icon_previews(); } catch (e) { STYLE_PREVIEWS = {}; }
  let st = false;
  try { st = await BRIDGE.get_startup(); } catch (e) { st = false; }

  onMockData = failed || !bridgeReady();
  LANG = S && S.language === "en" ? "en" : "fa";
  const chk = $("#chk-startup");
  if (chk) chk.checked = !!st;
  if (S) S.startup = !!st;

  activateUI();
  renderAll();

  if (onMockData) {
    toast(t("bridge_dead"));
    // The bridge may still be initializing — retry once it arrives.
    if (!isRetry) scheduleBridgeRetry();
  }

  // Lightweight state check: only re-render when a key state actually changes
  if (!pollTimerStarted) {
    pollTimerStarted = true;
    setInterval(async () => {
      if (document.hidden) return;
      try {
        const stt = await BRIDGE.get_states();
        if (stt && !statesEqual(stt, STATES)) {
          STATES = stt;
          refreshStates(true);
        }
      } catch (e) { /* ignore */ }
    }, 600);
  }
}

/* If we booted on mock data, re-boot as soon as the real bridge appears. */
function scheduleBridgeRetry() {
  const timer = setInterval(() => {
    if (!onMockData) { clearInterval(timer); return; }
    if (bridgeReady()) {
      clearInterval(timer);
      boot(true);
    }
  }, 250);
  // stop checking after 30 s
  setTimeout(() => clearInterval(timer), 30000);
}

let bootTries = 0;
let bootStarted = false;
function waitForBridge() {
  if (bootStarted) return;
  if (bridgeReady()) { bootStarted = true; boot(false); return; }
  // Boot on mock data after ~1.5 s instead of leaving an inert skeleton;
  // when the real bridge arrives later, boot() re-runs with real data
  // (pywebviewready listener + scheduleBridgeRetry).
  if (bootTries++ > 30) { bootStarted = true; boot(false); return; }
  setTimeout(waitForBridge, 50);
}

/* The official signal: pywebview dispatches this after populating the API. */
window.addEventListener("pywebviewready", () => {
  if (!bootStarted) {
    bootStarted = true;
    boot(false);
  } else if (onMockData) {
    boot(true);
  }
});
waitForBridge();

// Let Python push state updates instantly
window.__push = function (payload) {
  try {
    const data = typeof payload === "string" ? JSON.parse(payload) : payload;
    if (data && data.states) {
      STATES = data.states;
      refreshStates(true);
    }
  } catch (e) { /* noop */ }
};

// Settings saved callback from Python
window.__saved = function (_payload) {
  // Handled silently; explicit actions show toast if needed
};