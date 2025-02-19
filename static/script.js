// Initialize WebGazer
window.saveDataAcrossSessions = true;

// Global variables
let gazeData = [];
let calibrationComplete = false;
let heatmapVisible = true;
let heatmapInstance;

// Debugging: Check if WebGazer is loaded
if (typeof webgazer === "undefined") {
    console.error("WebGazer.js is not loaded. Check the script tag in your HTML file.");
} else {
    console.log("WebGazer.js is loaded successfully.");
}

// Wait for DOM to load
window.onload = function () {
    startTracking();
    document.getElementById("start-calibration").addEventListener("click", startCalibration);
    document.getElementById("toggle-heatmap").addEventListener("click", toggleHeatmap);
    document.getElementById("save-heatmap").addEventListener("click", saveHeatmapLocally);
};

// Start Calibration
function startCalibration() {
    document.getElementById("start-screen").style.display = "none";
    document.getElementById("calibration-screen").style.display = "flex";

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

    let container = document.getElementById("homepage");
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
}


// Start Tracking
function startTracking() {
    initializeHeatmap();

    webgazer.setGazeListener((data) => {
        if (data && document.getElementById("homepage").style.display === "flex") {
            const x = data.x;
            const y = data.y;
            gazeData.push({ x, y, value: 1 });

            heatmapInstance.addData({
                x: x,
                y: y,
                value: 1
            });
        }
    }).begin();
}

// Toggle Heatmap Visibility
function toggleHeatmap() {
    heatmapVisible = !heatmapVisible;
    document.getElementById("heatmap-container").style.display = heatmapVisible ? "block" : "none";
}

// // Save Heatmap Locally
// function saveHeatmapLocally() {
//     const heatmapCanvas = document.querySelector("#heatmap-container canvas");
//     if (!heatmapCanvas) {
//         console.error("Heatmap canvas not found.");
//         return;
//     }

//     const heatmapDataURL = heatmapCanvas.toDataURL("image/png");
//     const downloadLink = document.createElement("a");
//     downloadLink.href = heatmapDataURL;
//     downloadLink.download = `heatmap_${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
//     downloadLink.click();
// }

// function checkModelStatusAndUpload(formData) {
//     fetch("http://127.0.0.1:5000/model_status") // API to check if model is ready
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === "loading") {
//                 console.log(`Model is still loading, retrying in 10 seconds...`);
//                 setTimeout(() => checkModelStatusAndUpload(formData), 10000); // Retry after 10 seconds
//             } else if (data.status === "ready") {
//                 console.log("Model is ready! Uploading heatmap...");
//                 uploadHeatmap(formData);
//             }
//         })
//         .catch(error => {
//             console.error("Error checking model status:", error);
//             alert("Error: Unable to check model status. Please try again later.");
//         });
// }

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

    // Convert canvas to Blob
    heatmapCanvas.toBlob((blob) => {
        if (!blob) {
            console.error("Failed to generate heatmap blob.");
            return;
        }

        // Create FormData object and append the heatmap image
        const formData = new FormData();
        formData.append("heatmap", blob, "heatmap.png");

        // Send the heatmap to the backend
        uploadHeatmap(formData);
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

// Show Analysis
function showAnalysis() {
    fetch("http://127.0.0.1:5000/get_analysis")
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                alert("Error: " + data.error);
            } else {
                // Redirect to the analysis page
                window.location.href = "/analysis";
            }
        })
        .catch(error => {
            console.error("Error fetching analysis:", error);
            alert("Error: Unable to fetch analysis. Please try again later.");
        });
}

// Add event listener for "Show Analysis" button
document.getElementById("show-analysis").addEventListener("click", showAnalysis);


