// Initialize WebGazer
window.saveDataAcrossSessions = false;

// Global variables
let lastGaze = null;
let lastTime = null;
let gazeData = [];
let calibrationComplete = false;
let heatmapVisible = true;
let heatmapInstance;
let currentImageIndex = 0;
const uiImages = [
    "/static/ui_images/image1.png",
    "/static/ui_images/image2.png",
    "/static/ui_images/image3.png" 
];
const heatmaps = {};

// randomize the uiImages array 
uiImages.sort(() => Math.random() - 0.5);

// Debugging: Check if WebGazer is loaded
if (typeof webgazer === "undefined") {
    console.error("WebGazer.js is not loaded. Check the script tag in your HTML file.");
} else {
    console.log("WebGazer.js is loaded successfully.");
}

window.onload = function () {
    startTracking();
    const imgElement = document.getElementById("current-ui");
    imgElement.src = uiImages[0]; 
    document.getElementById("start-calibration").addEventListener("click", startCalibration);
    document.getElementById("toggle-heatmap").addEventListener("click", toggleHeatmap);
    document.getElementById("save-heatmap").addEventListener("click", saveHeatmapLocally);
};

// Start Calibration
function startCalibration() {
    document.getElementById("start-screen").style.display = "none";
    document.getElementById("calibration-screen").style.display = "flex";
    webgazer.showVideoPreview(true).showPredictionPoints(true);

    const dots = document.querySelectorAll(".dot");

    dots.forEach((dot) => {
        dot.addEventListener("click", () => {
            let clicks = parseInt(dot.getAttribute("data-clicks"));
            if (clicks === 0) {
                dot.classList.add("yellow");
                dot.setAttribute("data-clicks", "1");
            } else if (clicks === 1) {
                dot.classList.remove("yellow");
                dot.classList.add("green");
                dot.setAttribute("data-clicks", "2");
            }

            // Check if all dots are clicked twice
            if ([...dots].every(dot => dot.getAttribute("data-clicks") === "2")) {
                calibrationComplete = true;
                document.getElementById("calibration-screen").style.display = "none";
                document.getElementById("homepage").style.display = "flex";
                webgazer.showVideoPreview(false).showPredictionPoints(true);
            }
        });
    });
}

// Initialize Heatmap.js
function initializeHeatmap() {
    if (typeof h337 === "undefined") {
        console.error("Heatmap.js is not loaded properly.");
        return;
    }

    let container = document.getElementById("heatmap-container");
    if (!container) {
        console.error("Heatmap container (#homepage) not found.");
        return;
    }

    // Ensure the heatmap instance is not recreated multiple times
    if (!heatmapInstance) {
        heatmapInstance = h337.create({
            container: container,
            radius: 30,
            maxOpacity: 0.6,
            minOpacity: 0.1,
            blur: 0.75
        });
        console.log("Heatmap initialized successfully!", heatmapInstance);
    } else {
        console.log("Heatmap already initialized.");
    }
    // Set the height of the heatmap canvas dynamically
    const heatmapCanvas = container.querySelector("canvas");
    if (heatmapCanvas) {
        heatmapCanvas.style.height = '650px'; 
        heatmapCanvas.style.width = '1000px'; 
        heatmapCanvas.style.position = 'absolute';
        heatmapCanvas.style.top = '0';
        heatmapCanvas.style.left = '0';
    }
}


function startTracking() {
    initializeHeatmap();
    
    // Configure webgazer video feed
    webgazer.params.showVideoPreview = true;
    webgazer.applyKalmanFilter(true);
    webgazer.setRegression('ridge');
    
    // Updated gaze listener using eyeListener logic
    webgazer.setGazeListener((data, clock) => {
        if (data && document.getElementById("homepage").style.display === "flex") {
            const imgElement = document.getElementById("current-ui");
            const rect = imgElement.getBoundingClientRect();
            
            // Calculate relative coordinates within the image
            const x = data.x - rect.left;
            const y = data.y - rect.top;
            
            // Only record points within image bounds
            if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
                // Initialize lastTime if not set
                if (!lastTime) {
                    lastTime = clock;
                }

                // Track gaze duration
                if (lastGaze) {
                    const duration = clock - lastTime;
                    const point = {
                        x: Math.floor(x), // Use absolute coordinates
                        y: Math.floor(y), // Use absolute coordinates
                        value: duration / 1000 // Convert duration to seconds (or adjust as needed)
                    };
                    heatmapInstance.addData(point);
                }

                // Update lastGaze and lastTime
                lastGaze = { x, y };
                lastTime = clock;
            }
        }
    }).begin();
}

// 4. Add heatmap reset when changing images
function loadUIImage(index) {
    if (index < 0 || index >= uiImages.length) return;
    
    currentImageIndex = index;
    const imgElement = document.getElementById("current-ui");
    
    // Wait for image load before resetting heatmap
    imgElement.onload = () => {
        if (heatmapInstance) {
            heatmapInstance.setData({
                max: 1,
                data: []
            });
        }
        heatmaps[currentImageIndex] = [];
        lastGaze = null; 
        lastTime = null; 
    };
    imgElement.src = uiImages[currentImageIndex];
}

// Add event listeners for navigation
document.getElementById("next-ui").addEventListener("click", () => loadUIImage(currentImageIndex + 1));
document.getElementById("prev-ui").addEventListener("click", () => loadUIImage(currentImageIndex - 1));

// Toggle Heatmap Visibility
function toggleHeatmap() {
    const heatmapContainer = document.getElementById("heatmap-container");
    if (heatmapContainer) {
        heatmapVisible = !heatmapVisible; // Toggle the visibility state
        heatmapContainer.style.display = heatmapVisible ? "block" : "none"; // Show or hide the heatmap
    } else {
        console.error("Heatmap container not found.");
    }
}

// Save Heatmap Locally
function saveHeatmapLocally() {
    const heatmapCanvas = document.querySelector("#homepage canvas");
    if (!heatmapCanvas) {
        console.error("Heatmap canvas not found.");
        return;
    }

    if (heatmapCanvas.width === 0 || heatmapCanvas.height === 0) {
        console.error("Heatmap canvas is empty, cannot process.");
        return;
    }

    // Get the currently displayed UI image (assuming it's the active image)
    const imgElement = document.querySelector("#current-ui");  // Adjust if the image has a different ID or selector
    if (!imgElement) {
        console.error("UI image not found.");
        return;
    }

    // Convert the currently displayed UI image to a Blob
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    
    // Set canvas size to match the image size
    canvas.width = imgElement.naturalWidth;
    canvas.height = imgElement.naturalHeight;
    
    // Draw the image on the canvas
    context.drawImage(imgElement, 0, 0);

    // Convert canvas to Blob
    canvas.toBlob((blob) => {
        if (!blob) {
            console.error("Failed to create Blob from UI image.");
            return;
        }

        // Now you have imgBlob, so you can append both heatmap and UI image to the FormData
        const formData = new FormData();
        heatmapCanvas.toBlob((heatmapBlob) => {
            if (!heatmapBlob) {
                console.error("Failed to generate heatmap blob.");
                return;
            }

            // Append the heatmap and UI image Blob to FormData
            formData.append("heatmap", heatmapBlob, "heatmap.png");
            formData.append("ui_image", blob, `Dashboard${currentImageIndex + 1}.png`);

            // Send the FormData to the backend
            uploadHeatmap(formData);
        }, "image/png");
    }, "image/png");
}


// Upload Heatmap to Backend
function uploadHeatmap(formData) {
    fetch("http://127.0.0.1:5000/upload_heatmap", {
        method: "POST",
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Response from server:", data);
        if (data.error) {
            alert("Error: " + data.error);
        } else {
            alert("Heatmap saved successfully!");
        }
    })
    .catch(error => {
        console.error("Error uploading heatmap:", error);
        alert("Error: Unable to upload heatmap. Please try again later.");
    });
}
