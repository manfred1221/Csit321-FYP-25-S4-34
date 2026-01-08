(() => {
  // --- Config ---
  const MAX_SIZE_MB = 5;

  const API_BASE =
    (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) ||
    (window.CONFIG && window.CONFIG.API_BASE_URL) ||
    "";

  const ENDPOINT_ENROLL_FACE = `${API_BASE}/api/staff/enroll-face`;

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

  // Camera elements
  const videoPreview = document.getElementById("videoPreview");
  const canvas = document.getElementById("canvas");
  const startCameraBtn = document.getElementById("startCameraBtn");
  const captureBtn = document.getElementById("captureBtn");
  const stopCameraBtn = document.getElementById("stopCameraBtn");

  let selectedFile = null;
  let staffId = null;
  let stream = null;

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
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function getStaffIdFromLocalStorage() {
    const raw = localStorage.getItem("user");
    if (!raw) throw new Error("No login data found. Please login again.");

    let user;
    try {
      user = JSON.parse(raw);
    } catch {
      throw new Error("Login data is corrupted. Please login again.");
    }

    if (!user || user.type !== "staff") {
      throw new Error("This page is for staff only.");
    }

    const sid = Number(user.staff_id || user.id);
    if (!sid) throw new Error("No staff_id found. Please login again.");

    return sid;
  }

  async function enrollFace() {
    if (!selectedFile) {
      setStatus("Please select an image first.", "error");
      return;
    }

    try {
      uploadBtn.disabled = true;
      chooseBtn.disabled = true;
      clearBtn.disabled = true;
      setStatus("Preparing image...", "");

      if (!staffId) {
        staffId = getStaffIdFromLocalStorage();
      }

      const base64DataUrl = await fileToBase64(selectedFile);

      setStatus("Uploading and processing...", "");

      const res = await fetch(ENDPOINT_ENROLL_FACE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          staff_id: staffId,
          image_data: base64DataUrl
        })
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Enrollment failed. Please try again.");
      }

      setStatus("Face enrolled successfully! ✓", "ok");
      
      // Optional: redirect after success
      setTimeout(() => {
        // window.location.href = "/staff/dashboard.html";
      }, 2000);
      
    } catch (err) {
      setStatus(err.message || "Something went wrong.", "error");
    } finally {
      uploadBtn.disabled = !selectedFile;
      clearBtn.disabled = !selectedFile;
      chooseBtn.disabled = false;
    }
  }

  // --- Camera Functions ---
  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: "user" } 
      });
      videoPreview.srcObject = stream;
      startCameraBtn.disabled = true;
      captureBtn.disabled = false;
      stopCameraBtn.disabled = false;
      setStatus("Camera ready. Position your face and click Capture.", "ok");
    } catch (err) {
      setStatus("Camera access denied or unavailable.", "error");
    }
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      videoPreview.srcObject = null;
      stream = null;
    }
    startCameraBtn.disabled = false;
    captureBtn.disabled = true;
    stopCameraBtn.disabled = true;
    setStatus("");
  }

  function capturePhoto() {
    const context = canvas.getContext("2d");
    canvas.width = videoPreview.videoWidth;
    canvas.height = videoPreview.videoHeight;
    context.drawImage(videoPreview, 0, 0);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], "captured-face.jpg", { type: "image/jpeg" });
        setFile(file);
        stopCamera();
      }
    }, "image/jpeg", 0.95);
  }

  // --- Events ---
  chooseBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  });
  clearBtn.addEventListener("click", resetUI);
  uploadBtn.addEventListener("click", enrollFace);

  startCameraBtn.addEventListener("click", startCamera);
  captureBtn.addEventListener("click", capturePhoto);
  stopCameraBtn.addEventListener("click", stopCamera);

  // Drag & drop
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

  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  dropzone.addEventListener("click", (e) => {
    const clickedButton = e.target.closest("button");
    if (!clickedButton) fileInput.click();
  });

  // Init
  resetUI();
})();