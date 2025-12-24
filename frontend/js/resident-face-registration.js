(() => {
  // --- Config ---
  const MAX_SIZE_MB = 5;

  // If your config.js defines API_BASE_URL, we use it. Otherwise fallback.
  const API_BASE =
    (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) ||
    (window.CONFIG && window.CONFIG.API_BASE_URL) ||
    "";

  // Your backend route is /api/resident/register-face
  const ENDPOINT_REGISTER_FACE = `${API_BASE}/api/resident/register-face`;

  // --- Elements ---
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const chooseBtn = document.getElementById("chooseBtn");
  const clearBtn = document.getElementById("clearBtn");
  const uploadBtn = document.getElementById("uploadBtn");
  const statusMsg = document.getElementById("statusMsg");
  const previewImg = document.getElementById("previewImg");
  const previewPlaceholder = document.getElementById("previewPlaceholder");
  const fileMeta = document.getElementById("fileMeta");

  let selectedFile = null;
  let residentId = null;

  function setStatus(text, type = "") {
    statusMsg.textContent = text || "";
    statusMsg.className = "status" + (type ? " " + type : "");
  }

  function bytesToSize(bytes) {
    const sizes = ["Bytes", "KB", "MB", "GB"];
    if (bytes === 0) return "0 Bytes";
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + " " + sizes[i];
  }

  function resetUI() {
    selectedFile = null;
    fileInput.value = "";
    previewImg.src = "";
    previewImg.style.display = "none";
    previewPlaceholder.style.display = "block";
    uploadBtn.disabled = true;
    clearBtn.disabled = true;
    fileMeta.style.display = "none";
    fileMeta.textContent = "";
    setStatus("");
  }

  function validateFile(file) {
    if (!file) return "No file selected.";
    if (!file.type.startsWith("image/")) return "Please upload an image (JPG/PNG).";
    const maxBytes = MAX_SIZE_MB * 1024 * 1024;
    if (file.size > maxBytes) return `File too large. Max is ${MAX_SIZE_MB}MB.`;
    return null;
  }

  function showPreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewPlaceholder.style.display = "none";
      previewImg.style.display = "block";
    };
    reader.readAsDataURL(file);
  }

  function setFile(file) {
    const err = validateFile(file);
    if (err) {
      resetUI();
      setStatus(err, "error");
      return;
    }

    selectedFile = file;
    showPreview(file);

    fileMeta.textContent = `${file.name} • ${bytesToSize(file.size)}`;
    fileMeta.style.display = "block";

    uploadBtn.disabled = false;
    clearBtn.disabled = false;
    setStatus("Ready to upload.", "ok");
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result); // data:image/...;base64,xxxx
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  // ✅ FIX: read resident_id from localStorage("user") (this matches your login.js)
  function getResidentIdFromLocalStorage() {
    const raw = localStorage.getItem("user");
    if (!raw) throw new Error("No login data found. Please login again.");

    let user;
    try {
      user = JSON.parse(raw);
    } catch {
      throw new Error("Login data is corrupted. Please login again.");
    }

    if (!user || user.type !== "resident") {
      throw new Error("This page is for residents only.");
    }

    // login.js stores resident_id and also sets id = resident_id
    const rid = Number(user.resident_id || user.id);
    if (!rid) throw new Error("No resident_id found. Please login again.");

    return rid;
  }

  async function registerFace() {
    if (!selectedFile) {
      setStatus("Please select an image first.", "error");
      return;
    }

    try {
      uploadBtn.disabled = true;
      chooseBtn.disabled = true;
      clearBtn.disabled = true;
      setStatus("Preparing image...", "");

      // Ensure we have resident_id
      if (!residentId) {
        residentId = getResidentIdFromLocalStorage();
      }

      // Convert image -> base64 data URL (matches your backend expecting image_data)
      const base64DataUrl = await fileToBase64(selectedFile);

      setStatus("Uploading...", "");

      const res = await fetch(ENDPOINT_REGISTER_FACE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resident_id: residentId,
          image_data: base64DataUrl
        })
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Upload failed. Please try again.");
      }

      setStatus("Face registered successfully.", "ok");
      // Optional redirect:
      // window.location.href = "/resident/dashboard";
    } catch (err) {
      setStatus(err.message || "Something went wrong.", "error");
    } finally {
      // Re-enable buttons so user can retry or clear
      uploadBtn.disabled = !selectedFile;
      clearBtn.disabled = !selectedFile;
      chooseBtn.disabled = false;
    }
  }

  // --- Events ---
  chooseBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  });

  clearBtn.addEventListener("click", resetUI);

  uploadBtn.addEventListener("click", registerFace);

  // Drag & drop styling
  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) setFile(file);
  });

  // Keyboard access
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  // Click dropzone (but not buttons)
  dropzone.addEventListener("click", (e) => {
    const clickedButton = e.target.closest("button");
    if (!clickedButton) fileInput.click();
  });

  // Init
  resetUI();
})();
