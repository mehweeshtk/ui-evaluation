from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
from PIL import Image
import base64
from google import genai  

app = Flask(__name__)
CORS(app)

# Set up the Gemini client using API key
client = genai.Client(api_key="API key")

# Store analysis result in memory
analysis_result = None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload_heatmap", methods=["POST"])
def upload_heatmap():
    global analysis_result

    if "heatmap" not in request.files:
        return jsonify(error="No file uploaded"), 400

    try:
        # Convert uploaded file to PIL Image
        heatmap_file = request.files["heatmap"]
        image = Image.open(io.BytesIO(heatmap_file.read())).convert("RGB")

        # Resize image to reduce memory usage
        image = image.resize((224, 224))  # Adjust resolution as needed

        # Convert image to base64 for Gemini API
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Prepare content for Gemini API request
        contents = "This is a heatmap showing user gaze data. Analyze the heatmap and describe the areas where users looked the most and the least.."

        # Call the Gemini API to analyze the heatmap
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # Using the correct model for analysis
            contents=[image_base64, contents]
        )

        # Extract analysis from Gemini API response
        analysis_result = response.text  # Assuming the response contains text as the analysis result

        return jsonify(message="Heatmap uploaded and analyzed successfully")
    except Exception as e:
        print("Error processing heatmap:", str(e))
        return jsonify(error="Failed to analyze heatmap", details=str(e)), 500

@app.route("/get_analysis", methods=["GET"])
def get_analysis():
    global analysis_result
    if analysis_result:
        return jsonify(analysis=analysis_result)
    else:
        return jsonify(error="No analysis available"), 404

@app.route("/analysis")
def analysis():
    return render_template("analysis.html")

if __name__ == "__main__":
    app.run(port=5000, debug=False)  # Disable debug for production
