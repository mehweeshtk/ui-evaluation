from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
from PIL import Image
import base64
from google import genai  
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key="API_key") 

# analysis_result = None

analysis_data = {"text": None, "image": None}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload_heatmap", methods=["POST"])
def upload_heatmap():
    global analysis_data

    if "heatmap" not in request.files or "ui_image" not in request.files:
        return jsonify(error="No files uploaded"), 400

    try:
        # Get both files from request
        heatmap_file = request.files["heatmap"]
        ui_file = request.files["ui_image"]
        
        # Read and process images
        ui_img = Image.open(ui_file).convert("RGBA")
        heatmap_img = Image.open(heatmap_file).convert("RGBA")

        # Convert to numpy arrays
        ui_np = np.array(ui_img)
        heatmap_np = np.array(heatmap_img)

        # Resize heatmap to match UI image dimensions
        if ui_np.shape[:2] != heatmap_np.shape[:2]:
            heatmap_np = cv2.resize(heatmap_np, (ui_np.shape[1], ui_np.shape[0]))

        # Normalize alpha channel to 0-1 range
        alpha = heatmap_np[..., 3] / 255.0
        alpha = np.expand_dims(alpha, axis=-1)  # Add channel dimension

        # Convert images to float for calculations
        ui_float = ui_np.astype(np.float32) / 255.0
        heatmap_float = heatmap_np.astype(np.float32) / 255.0

        # Perform alpha blending
        blended = ui_float * (1 - alpha) + heatmap_float * alpha

        # Convert back to 8-bit format
        blended = (blended * 255).astype(np.uint8)
        combined_img = Image.fromarray(blended)

        # Prepare for Gemini API
        buffered = io.BytesIO()
        combined_img.save(buffered, format="PNG")
        combined_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = "This is a heatmap showing user gaze data. Analyze the heatmap and describe the areas where users looked the most and the least."

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": combined_base64}}
                ]
            }]
        )
        
        # analysis_result = response.text
        analysis_data = {
            "text": response.text,
            "image": combined_base64  
        }
        return jsonify(message="Heatmap uploaded and analyzed successfully")

    except Exception as e:
        print("Error processing heatmap:", str(e))
        return jsonify(error="Failed to analyze heatmap", details=str(e)), 500

@app.route("/get_analysis", methods=["GET"])
def get_analysis():
    if analysis_data["text"]:
        return jsonify({
            "analysis": analysis_data["text"],
            "image": analysis_data["image"]
        })
    else:
        return jsonify(error="No analysis available"), 404

@app.route("/analysis")
def analysis():
    return render_template("analysis.html")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
