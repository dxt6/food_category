(function () {
  "use strict";

  var root = document.documentElement;
  var themeKey = "food-classify-theme";
  var toggle = document.getElementById("themeToggle");

  function preferredTheme() {
    var saved = localStorage.getItem(themeKey);
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    if (!toggle) return;
    var dark = theme === "dark";
    toggle.setAttribute("aria-pressed", String(dark));
    toggle.setAttribute("aria-label", dark ? "切换到浅色主题" : "切换到深色主题");
    toggle.innerHTML = '<i class="bi ' + (dark ? "bi-sun" : "bi-moon-stars") + '" aria-hidden="true"></i>';
  }

  setTheme(preferredTheme());
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      localStorage.setItem(themeKey, next);
      setTheme(next);
    });
  }

  var textArea = document.getElementById("foodText");
  var charCount = document.getElementById("charCount");
  function updateCount() {
    if (textArea && charCount) charCount.textContent = textArea.value.length + " / 2000";
  }
  if (textArea) {
    updateCount();
    textArea.addEventListener("input", updateCount);
    document.querySelectorAll("[data-prompt]").forEach(function (button) {
      button.addEventListener("click", function () {
        textArea.value = button.getAttribute("data-prompt") || "";
        updateCount();
        textArea.focus();
      });
    });
  }

  var foodFile = document.getElementById("foodFile");
  var fileName = document.getElementById("fileName");
  if (foodFile) {
    foodFile.addEventListener("change", function () {
      var file = foodFile.files && foodFile.files[0];
      if (!file) {
        if (fileName) fileName.textContent = "";
        return;
      }
      if (fileName) fileName.textContent = "已选择：" + file.name;
      if (file.size <= 2 * 1024 * 1024 && /\.(txt|csv|md)$/i.test(file.name) && textArea) {
        var reader = new FileReader();
        reader.addEventListener("load", function () {
          textArea.value = String(reader.result || "").slice(0, 2000);
          updateCount();
        });
        reader.readAsText(file, "UTF-8");
      }
    });
  }

  document.querySelectorAll("[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var message = form.getAttribute("data-confirm") || "确认执行此操作？";
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-loading-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (event.defaultPrevented) return;
      var button = form.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;
      var label = form.getAttribute("data-loading-text") || "处理中…";
      button.disabled = true;
      button.dataset.originalHtml = button.innerHTML;
      button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>' + label + "</span>";
    });
  });

  var levelSelect = document.querySelector('[name="level"]');
  var parentSelect = document.querySelector('[name="parent_code"]');
  function syncParentOptions() {
    if (!levelSelect || !parentSelect) return;
    var level = Number(levelSelect.value);
    Array.prototype.forEach.call(parentSelect.options, function (option) {
      if (!option.value) return;
      var optionLevel = Number(option.getAttribute("data-level"));
      option.hidden = level === 1 || optionLevel !== level - 1;
      option.disabled = option.hidden;
    });
    if (level === 1 || (parentSelect.selectedOptions[0] && parentSelect.selectedOptions[0].hidden)) parentSelect.value = "";
    parentSelect.disabled = level === 1;
  }
  if (levelSelect && parentSelect) {
    syncParentOptions();
    levelSelect.addEventListener("change", syncParentOptions);
  }
})();
