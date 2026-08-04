/* 食品类别分类系统 · emilkowalski 风交互
   - 主题切换（localStorage 记忆，默认跟随系统）
   - 卡片入场 reveal（交错延迟）
   - 轻量 Toast 替代 Django alert
*/
(function () {
  "use strict";

  /* ---------- 主题 ---------- */
  var root = document.documentElement;
  var KEY = "ek-theme";
  function apply(theme) {
    if (theme === "dark" || theme === "light") {
      root.setAttribute("data-theme", theme);
    } else {
      root.removeAttribute("data-theme");
    }
    var btn = document.getElementById("ekThemeBtn");
    if (btn) {
      var isDark = root.getAttribute("data-theme") === "dark" ||
        (!root.getAttribute("data-theme") &&
          window.matchMedia("(prefers-color-scheme: dark)").matches);
      btn.textContent = isDark ? "☀" : "☾";
      btn.setAttribute("aria-label", isDark ? "切换到浅色" : "切换到暗色");
    }
  }
  var saved = localStorage.getItem(KEY);
  apply(saved || "auto");

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("#ekThemeBtn");
    if (!btn) return;
    var cur = root.getAttribute("data-theme");
    var sysDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    var nowDark = cur === "dark" || (!cur && sysDark);
    var next = nowDark ? "light" : "dark";
    localStorage.setItem(KEY, next);
    apply(next);
  });

  // 系统主题变化时（仅当用户未手动设定）自动跟随
  if (!saved) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
      apply("auto");
    });
  }

  /* ---------- 入场 reveal（交错） ---------- */
  function revealAll() {
    var cards = document.querySelectorAll(".reveal");
    cards.forEach(function (el, i) {
      el.style.animationDelay = Math.min(i * 60, 360) + "ms";
    });
  }
  if (document.readyState !== "loading") revealAll();
  else document.addEventListener("DOMContentLoaded", revealAll);

  /* ---------- Toast ---------- */
  function toast(msg, type) {
    type = type || "ok";
    var wrap = document.querySelector(".ek-toast-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "ek-toast-wrap";
      document.body.appendChild(wrap);
    }
    var t = document.createElement("div");
    t.className = "ek-toast " + type;
    t.innerHTML = '<span class="ek-dot"></span><span></span>';
    t.lastChild.textContent = msg;
    wrap.appendChild(t);
    setTimeout(function () {
      t.classList.add("ek-out");
      setTimeout(function () { t.remove(); }, 320);
    }, 3200);
  }
  window.ekToast = toast;

  /* ---------- 表单提交中状态（Spec §4.3/§6：禁用+进行中） ---------- */
  document.addEventListener("submit", function (e) {
    var btn = e.target.querySelector && e.target.querySelector("button[type=submit], button:not([type=button])");
    if (!btn || btn.dataset.loading === "1") return;
    var old = btn.textContent;
    btn.dataset.loading = "1";
    btn.disabled = true;
    btn.textContent = (btn.dataset.loadingText || "处理中…");
    // 若 6s 内未跳转（同步请求），恢复可点，避免卡死
    setTimeout(function () {
      if (btn && document.body.contains(btn)) {
        btn.disabled = false;
        btn.textContent = old;
        btn.dataset.loading = "";
      }
    }, 6000);
  });

  // 把页面里的 Django alert 也包一层淡入（保持可读，不破坏功能）
  document.querySelectorAll(".alert").forEach(function (el) {
    el.style.opacity = "0";
    el.style.transform = "translateY(6px)";
    el.style.transition = "opacity .4s cubic-bezier(.16,1,.3,1), transform .4s cubic-bezier(.16,1,.3,1)";
    requestAnimationFrame(function () {
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    });
  });
})();
