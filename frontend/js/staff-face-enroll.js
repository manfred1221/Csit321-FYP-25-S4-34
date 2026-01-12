document.addEventListener('DOMContentLoaded', async () => {
    // ==========================================
    // 1. AUTHENTICATION & SIDEBAR LOGIC
    // ==========================================
    let currentUser = null;

    // Try using the global checkAuth if available (from config.js)
    if (typeof checkAuth === 'function') {
        currentUser = await checkAuth();
    } else {
        // Fallback: Check localStorage manually
        const userString = localStorage.getItem('user');
        if (userString) {
            currentUser = JSON.parse(userString);
        }
    }

    // Redirect if not logged in or wrong role
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }

    const allowedRoles = ['Internal_Staff', 'Staff', 'Security', 'internal_staff'];
    if (currentUser.role && !allowedRoles.includes(currentUser.role) && currentUser.type !== 'staff') {
        window.location.href = '/login';
        return;
    }

    // ✅ POPULATE SIDEBAR (Targeting your new IDs)
    const nameEl = document.getElementById('staffNameSidebar'); // Matches your HTML change
    const posEl = document.getElementById('staffPosition');
    
    if (nameEl) nameEl.textContent = currentUser.full_name || currentUser.username;
    if (posEl) posEl.textContent = (currentUser.role || 'Staff Member').replace('_', ' ');

    // Handle Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                localStorage.removeItem('user');
                try { await fetch('/api/auth/logout', { method: 'POST' }); } catch (e) {}
                window.location.href = '/login';
            }
        });
    }

    // ==========================================
    // 2. FACE ENROLLMENT LOGIC
    // ==========================================
    initFaceEnrollment(currentUser);
});

function initFaceEnrollment(user) {
    // --- Config ---
    const MAX_SIZE_MB = 5;
    const ENDPOINT_ENROLL_FACE = `/api/staff/enroll-face`; // Using relative path for consistency

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
    let stream = null;

    function setStatus(text, type = "") {
        if (!statusMsg) return;
        statusMsg.textContent = text || "";
        statusMsg.className = "status" + (type ? " " + type : "");
        statusMsg.style.display = text ? "block" : "none";
    }

    function bytesToSize(bytes) {
        const sizes = ["Bytes", "KB", "MB", "GB"];
        if (bytes === 0) return "0 Bytes";
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + " " + sizes[i];
    }

    function resetUI() {
        selectedFile = null;
        if (fileInput) fileInput.value = "";
        if (previewImg) {
            previewImg.src = "";
            previewImg.style.display = "none";
        }
        if (previewPlaceholder) previewPlaceholder.style.display = "block";
        if (uploadBtn) uploadBtn.disabled = true;
        if (clearBtn) clearBtn.disabled = true;
        if (fileMeta) {
            fileMeta.style.display = "none";
            fileMeta.textContent = "";
        }
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
            if (previewImg) {
                previewImg.src = e.target.result;
                previewImg.style.display = "block";
            }
            if (previewPlaceholder) previewPlaceholder.style.display = "none";
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

        if (fileMeta) {
            fileMeta.textContent = `${file.name} • ${bytesToSize(file.size)}`;
            fileMeta.style.display = "block";
        }

        if (uploadBtn) uploadBtn.disabled = false;
        if (clearBtn) clearBtn.disabled = false;
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

    async function enrollFace() {
        if (!selectedFile) {
            setStatus("Please select an image first.", "error");
            return;
        }

        try {
            uploadBtn.disabled = true;
            if (chooseBtn) chooseBtn.disabled = true;
            clearBtn.disabled = true;
            setStatus("Preparing image...", "processing");

            // Use ID from the authenticated user object
            const staffId = user.staff_id || user.user_id || user.id;

            const base64DataUrl = await fileToBase64(selectedFile);

            setStatus("Uploading and processing...", "processing");

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

        } catch (err) {
            setStatus(err.message || "Something went wrong.", "error");
        } finally {
            uploadBtn.disabled = !selectedFile;
            clearBtn.disabled = !selectedFile;
            if (chooseBtn) chooseBtn.disabled = false;
        }
    }

    // --- Camera Functions ---
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user" }
            });
            if (videoPreview) videoPreview.srcObject = stream;
            if (startCameraBtn) startCameraBtn.disabled = true;
            if (captureBtn) captureBtn.disabled = false;
            if (stopCameraBtn) stopCameraBtn.disabled = false;
            setStatus("Camera ready. Position your face and click Capture.", "ok");
        } catch (err) {
            setStatus("Camera access denied or unavailable.", "error");
        }
    }

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            if (videoPreview) videoPreview.srcObject = null;
            stream = null;
        }
        if (startCameraBtn) startCameraBtn.disabled = false;
        if (captureBtn) captureBtn.disabled = true;
        if (stopCameraBtn) stopCameraBtn.disabled = true;
        setStatus("");
    }

    function capturePhoto() {
        if (!canvas || !videoPreview) return;
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
    if (chooseBtn && fileInput) {
        chooseBtn.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
        });
    }

    if (clearBtn) clearBtn.addEventListener("click", resetUI);
    if (uploadBtn) uploadBtn.addEventListener("click", enrollFace);

    if (startCameraBtn) startCameraBtn.addEventListener("click", startCamera);
    if (captureBtn) captureBtn.addEventListener("click", capturePhoto);
    if (stopCameraBtn) stopCameraBtn.addEventListener("click", stopCamera);

    // Drag & drop logic
    if (dropzone) {
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

        dropzone.addEventListener("click", (e) => {
            // Only trigger if not clicking a button inside
            const clickedButton = e.target.closest("button");
            if (!clickedButton && fileInput) fileInput.click();
        });
    }

    // Initialize
    resetUI();
}