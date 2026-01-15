let user = null;
let stream = null;
let capturedDataUrl = null;

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

  // 3) Init camera UI
  initCameraFaceRegistration();
});

function initCameraFaceRegistration() {
  const webcam = document.getElementById("webcam");
  const capturedImg = document.getElementById("capturedImg");
  const placeholder = document.getElementById("cameraPlaceholder");
  const canvas = document.getElementById("canvas");

  const startBtn = document.getElementById("startBtn");
  const captureBtn = document.getElementById("captureBtn");
  const retakeBtn = document.getElementById("retakeBtn");
  const uploadBtn = document.getElementById("uploadBtn");

  const statusMsg = document.getElementById("statusMsg");

  function setStatus(text, type) {
    if (!statusMsg) return;
    statusMsg.textContent = text || "";
    statusMsg.style.display = text ? "block" : "none";
    statusMsg.className = "status-message" + (type ? " " + type : "");
  }

  function showVideo() {
    webcam.style.display = "block";
    capturedImg.style.display = "none";
    if (placeholder) placeholder.style.display = "none";
  }

  function showPlaceholder(msg) {
    webcam.style.display = "none";
    capturedImg.style.display = "none";
    if (placeholder) {
      placeholder.textContent = msg || "Camera is off";
      placeholder.style.display = "block";
    }
  }

  function showCaptured(dataUrl) {
    capturedImg.src = dataUrl;
    capturedImg.style.display = "block";
    webcam.style.display = "none";
    if (placeholder) placeholder.style.display = "none";
  }

  function resetCapturedState() {
    capturedDataUrl = null;
    retakeBtn.disabled = true;
    uploadBtn.disabled = true;
    captureBtn.disabled = !stream; // enabled only if camera started
    if (stream) showVideo();
    else showPlaceholder("Camera is off");
  }

  async function startCamera() {
    try {
      setStatus("Requesting camera permission...", "processing");

      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });

      webcam.srcObject = stream;
      await webcam.play();

      showVideo();
      captureBtn.disabled = false;
      startBtn.textContent = "Stop Camera";
      setStatus("Camera ready. Click Capture when you're ready.", "success");
    } catch (err) {
      console.error(err);
      stream = null;
      showPlaceholder("Camera unavailable");
      setStatus(
        "Could not access camera. Please allow camera permission in the browser settings.",
        "error"
      );
    }
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    webcam.srcObject = null;
    startBtn.textContent = "Start Camera";
    captureBtn.disabled = true;
    resetCapturedState();
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

    capturedDataUrl = canvas.toDataURL("image/jpeg", 0.92);
    showCaptured(capturedDataUrl);

    captureBtn.disabled = true;
    retakeBtn.disabled = false;
    uploadBtn.disabled = false;

    setStatus("Captured. If it looks good, click Upload & Register.", "success");
  }

  async function uploadCapture() {
    if (!capturedDataUrl) return;

    try {
      uploadBtn.disabled = true;
      retakeBtn.disabled = true;
      setStatus("Uploading face registration...", "processing");

      const residentId = user.resident_id || user.user_id;
      if (!residentId) {
        throw new Error("Could not find resident_id/user_id from session.");
      }

      const res = await fetch(API_CONFIG.ENDPOINTS.RESIDENT.REGISTER_FACE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          resident_id: residentId,
          image_data: capturedDataUrl,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Face registration failed.");
      }

      setStatus("Face registered successfully!", "success");

      // Optional: stop camera after successful upload
      // stopCamera();

    } catch (err) {
      console.error(err);
      setStatus(err.message || "Upload failed.", "error");
      uploadBtn.disabled = false;
      retakeBtn.disabled = false;
    }
  }

  // Button wiring
  startBtn.addEventListener("click", async () => {
    if (!stream) await startCamera();
    else stopCamera();
  });

  captureBtn.addEventListener("click", captureFrame);

  retakeBtn.addEventListener("click", () => {
    setStatus("Retake: position your face and capture again.", "success");
    resetCapturedState();
  });

  uploadBtn.addEventListener("click", uploadCapture);

  // Start in clean state
  showPlaceholder("Camera is off");
  resetCapturedState();
}
