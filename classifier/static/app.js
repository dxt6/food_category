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

  var packageImage = document.getElementById("packageImage");
  var visionDropzone = document.getElementById("visionDropzone");
  var visionUploadCopy = document.getElementById("visionUploadCopy");
  var visionPreviewWrap = document.getElementById("visionPreviewWrap");
  var visionPreview = document.getElementById("visionPreview");
  var visionFileName = document.getElementById("visionFileName");
  var currentPreviewUrl = "";

  function showVisionPreview(file) {
    if (!file || !visionPreview || !visionPreviewWrap || !visionUploadCopy) return;
    if (currentPreviewUrl) URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = URL.createObjectURL(file);
    visionPreview.src = currentPreviewUrl;
    visionPreviewWrap.hidden = false;
    visionUploadCopy.hidden = true;
    if (visionFileName) visionFileName.textContent = file.name;
  }

  function assignVisionFile(file) {
    if (!packageImage || !file || !file.type.match(/^image\/(jpeg|png|webp)$/)) return false;
    var transfer = new DataTransfer();
    transfer.items.add(file);
    packageImage.files = transfer.files;
    showVisionPreview(file);
    return true;
  }

  if (packageImage) {
    packageImage.addEventListener("change", function () {
      var file = packageImage.files && packageImage.files[0];
      if (file) showVisionPreview(file);
    });
  }

  if (visionDropzone) {
    ["dragenter", "dragover"].forEach(function (eventName) {
      visionDropzone.addEventListener(eventName, function (event) {
        event.preventDefault();
        visionDropzone.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach(function (eventName) {
      visionDropzone.addEventListener(eventName, function (event) {
        event.preventDefault();
        visionDropzone.classList.remove("is-dragging");
      });
    });
    visionDropzone.addEventListener("drop", function (event) {
      var file = event.dataTransfer.files && event.dataTransfer.files[0];
      assignVisionFile(file);
    });
  }

  var cameraStart = document.getElementById("cameraStart");
  var cameraPanel = document.getElementById("cameraPanel");
  var cameraVideo = document.getElementById("cameraVideo");
  var cameraCanvas = document.getElementById("cameraCanvas");
  var cameraCapture = document.getElementById("cameraCapture");
  var cameraClose = document.getElementById("cameraClose");
  var cameraMessage = document.getElementById("cameraMessage");
  var cameraStream = null;

  function stopCamera() {
    if (cameraStream) cameraStream.getTracks().forEach(function (track) { track.stop(); });
    cameraStream = null;
    if (cameraVideo) cameraVideo.srcObject = null;
    if (cameraPanel) cameraPanel.hidden = true;
  }

  if (cameraStart) {
    cameraStart.addEventListener("click", function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (cameraMessage) cameraMessage.textContent = "当前浏览器不支持摄像头，请使用图片上传。";
        if (cameraPanel) cameraPanel.hidden = false;
        return;
      }
      navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false }).then(function (stream) {
        cameraStream = stream;
        cameraVideo.srcObject = stream;
        cameraPanel.hidden = false;
        if (cameraMessage) cameraMessage.textContent = "";
      }).catch(function () {
        cameraPanel.hidden = false;
        if (cameraMessage) cameraMessage.textContent = "无法访问摄像头，请检查浏览器权限或使用图片上传。";
      });
    });
  }

  if (cameraCapture) {
    cameraCapture.addEventListener("click", function () {
      if (!cameraVideo || !cameraCanvas || !cameraVideo.videoWidth) return;
      cameraCanvas.width = cameraVideo.videoWidth;
      cameraCanvas.height = cameraVideo.videoHeight;
      cameraCanvas.getContext("2d").drawImage(cameraVideo, 0, 0);
      cameraCanvas.toBlob(function (blob) {
        if (!blob) return;
        assignVisionFile(new File([blob], "camera-package.jpg", { type: "image/jpeg" }));
        stopCamera();
      }, "image/jpeg", 0.92);
    });
  }
  if (cameraClose) cameraClose.addEventListener("click", stopCamera);
  window.addEventListener("beforeunload", stopCamera);

  document.querySelectorAll("[data-copy-command]").forEach(function (button) {
    button.addEventListener("click", function () {
      var code = button.parentElement.querySelector("code");
      if (!code || !navigator.clipboard) return;
      navigator.clipboard.writeText(code.textContent).then(function () {
        button.innerHTML = '<i class="bi bi-check2"></i>';
        window.setTimeout(function () { button.innerHTML = '<i class="bi bi-copy"></i>'; }, 1500);
      });
    });
  });
})();
