// Check authentication
let user = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verify user via Flask session
    user = await checkAuth(); 
    
    if (!user) return; 

    if (user.role !== 'Resident') {
        window.location.href = '/login';
        return;
    }

    // 2. Initialize UI (Sidebar)
    document.getElementById('userName').textContent = user.full_name || user.username;
    const emailEl = document.getElementById('userEmail');
    if (emailEl) emailEl.textContent = user.email || (user.username + '@condo.com');

    // 3. Setup Face Registration UI
    initFaceRegistration();
});

function initFaceRegistration() {
    const fileInput = document.getElementById("fileInput");
    const chooseBtn = document.getElementById("chooseBtn");
    const clearBtn = document.getElementById("clearBtn");
    const uploadBtn = document.getElementById("uploadBtn");
    const statusMsg = document.getElementById("statusMsg");
    const previewImg = document.getElementById("previewImg");
    const previewPlaceholder = document.getElementById("previewPlaceholder");
    const fileMeta = document.getElementById("fileMeta");

    let selectedFile = null;

    function setStatus(text, type = "") {
        statusMsg.textContent = text || "";
        statusMsg.className = "status" + (type ? " " + type : "");
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
        setStatus("");
    }

    // File selection logic
    chooseBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
            selectedFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImg.src = e.target.result;
                previewPlaceholder.style.display = "none";
                previewImg.style.display = "block";
            };
            reader.readAsDataURL(file);
            fileMeta.textContent = `${file.name}`;
            fileMeta.style.display = "block";
            uploadBtn.disabled = false;
            clearBtn.disabled = false;
            setStatus("Ready to upload.", "ok");
        }
    });

    clearBtn.addEventListener("click", resetUI);

    // Upload Logic
    uploadBtn.addEventListener("click", async () => {
        if (!selectedFile) return;

        try {
            uploadBtn.disabled = true;
            setStatus("Uploading...", "");

            // ⭐ GET ID FROM SESSION USER
            const residentId = user.resident_id || user.user_id;

            const reader = new FileReader();
            reader.readAsDataURL(selectedFile);
            reader.onload = async () => {
                const base64Data = reader.result;
                
                // Use API_CONFIG from config.js
                const res = await fetch(API_CONFIG.ENDPOINTS.RESIDENT.REGISTER_FACE, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        resident_id: residentId,
                        image_data: base64Data
                    })
                });

                const data = await res.json();
                if (data.success) {
                    setStatus("Face registered successfully!", "ok");
                } else {
                    throw new Error(data.error);
                }
            };
        } catch (err) {
            setStatus(err.message, "error");
            uploadBtn.disabled = false;
        }
    });
}