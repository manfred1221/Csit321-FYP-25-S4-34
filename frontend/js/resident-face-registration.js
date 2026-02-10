let user = null;
let stream = null;
let selectedDataUrl = null;

document.addEventListener("DOMContentLoaded", async () => {
  // 1) Verify session user
  user = await checkAuth();
  if (!user) return;

  if (user.role !== "Resident") {
    window.location.href = "/login";
    return;
  }

  // 2) Sidebar name
  const residentNameEl = document.getElementById("residentName");
  if (residentNameEl) {
    residentNameEl.textContent = user.full_name || user.username || "Resident";
  }

  // 3) Wire up UI
  setupUploadOption();
  setupCameraOption();
  setupSubmitAndClear();

  // initial preview state
  setPreview(null);
});

function setStatus(text, type) {
  const statusMsg = document.getElementById("statusMsg");
  if (!statusMsg) return;

  statusMsg.textContent = text || "";
  statusMsg.style.display = text ? "block" : "none";
  statusMsg.className = "status-message" + (type ? " " + type : "");
}

function setPreview(dataUrl) {
  selectedDataUrl = dataUrl;

  const img = document.getElementById("previewImg");
  const empty = document.getElementById("previewEmpty");
  const uploadBtn = document.getElementById("uploadBtn");
  const clearBtn = document.getElementById("clearBtn");

  if (dataUrl) {
    img.src = dataUrl;
    img.style.display = "block";
    empty.style.display = "none";
    uploadBtn.disabled = false;
    clearBtn.disabled = false;
  } else {
    img.src = "";
    img.style.display = "none";
    empty.style.display = "block";
    uploadBtn.disabled = true;
    clearBtn.disabled = true;
  }
}

/* =========================
   Option 1: Upload Photo
   ========================= */
function setupUploadOption() {
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("dropZone");
  const btnSelectFile = document.getElementById("btnSelectFile");

  function handleFile(file) {
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setStatus("Please upload an image file (JPG/PNG).", "error");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setStatus("File too large. Max 5MB.", "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setPreview(reader.result);
      setStatus("Photo loaded. You can now click Upload & Register.", "success");
    };
    reader.onerror = () => setStatus("Failed to read image file.", "error");
    reader.readAsDataURL(file);
  }

  btnSelectFile.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener("click", (e) => {
    // allow clicking anywhere except button (button already handled)
    if (e.target && e.target.id === "btnSelectFile") return;
    fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    handleFile(file);
    fileInput.value = "";
  });

  // Drag & drop
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("is-dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("is-dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("is-dragover");
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    handleFile(file);
  });
}

/* =========================
   Option 2: Use Camera
   ========================= */
function setupCameraOption() {
  const webcam = document.getElementById("webcam");
  const canvas = document.getElementById("canvas");

  const startBtn = document.getElementById("startBtn");
  const stopBtn = document.getElementById("stopBtn");
  const captureBtn = document.getElementById("captureBtn");
  const cameraHint = document.getElementById("cameraHint");

  async function startCamera() {
    try {
      setStatus("Requesting camera permission...", "processing");

      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });

      webcam.srcObject = stream;
      await webcam.play();

      startBtn.disabled = true;
      stopBtn.disabled = false;
      captureBtn.disabled = false;
      cameraHint.style.display = "none";

      setStatus("Camera ready. Click Capture when you're ready.", "success");
    } catch (err) {
      console.error(err);
      stream = null;
      webcam.srcObject = null;

      startBtn.disabled = false;
      stopBtn.disabled = true;
      captureBtn.disabled = true;
      cameraHint.style.display = "block";

      setStatus(
        "Could not access camera. Please allow camera permission in the browser settings.",
        "error"
      );
    }
  }

  function stopCamera() {
    try {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    } catch (_) {}

    stream = null;
    webcam.srcObject = null;

    startBtn.disabled = false;
    stopBtn.disabled = true;
    captureBtn.disabled = true;
    cameraHint.style.display = "block";

    setStatus("Camera stopped.", "");
  }

  function captureFrame() {
    if (!stream) return;

    const w = webcam.videoWidth || 640;
    const h = webcam.videoHeight || 480;

    canvas.width = w;
    canvas.height = h;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(webcam, 0, 0, w, h);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    setPreview(dataUrl);

    setStatus("Captured. If it looks good, click Upload & Register.", "success");
  }

  startBtn.addEventListener("click", startCamera);
  stopBtn.addEventListener("click", stopCamera);
  captureBtn.addEventListener("click", captureFrame);

  // Safety: stop camera when leaving page
  window.addEventListener("beforeunload", () => stopCamera());
}

/* =========================
   Submit + Clear (shared)
   ========================= */
function setupSubmitAndClear() {
  const uploadBtn = document.getElementById("uploadBtn");
  const clearBtn = document.getElementById("clearBtn");

  clearBtn.addEventListener("click", () => {
    setPreview(null);
    setStatus("", "");
  });

  uploadBtn.addEventListener("click", async () => {
    if (!selectedDataUrl) {
      setStatus("Please select or capture an image first.", "error");
      return;
    }

    try {
      uploadBtn.disabled = true;
      clearBtn.disabled = true;

      setStatus("Uploading face registration...", "processing");

      const residentId = user.resident_id || user.user_id;
      if (!residentId) throw new Error("Could not find resident_id/user_id from session.");

      const res = await fetch(API_CONFIG.ENDPOINTS.RESIDENT.REGISTER_FACE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          resident_id: residentId,
          image_data: selectedDataUrl,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Face registration failed.");
      }

      setStatus("Face registered successfully!", "success");
    } catch (err) {
      console.error(err);
      setStatus(err.message || "Upload failed.", "error");
    } finally {
      // re-enable based on whether we still have an image selected
      uploadBtn.disabled = !selectedDataUrl;
      clearBtn.disabled = !selectedDataUrl;
    }
  });
}
