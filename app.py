import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
import os
from PIL import Image
import base64
import cv2
import numpy as np
from crewai import Agent, Task, Crew, LLM, Process
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from crew import UIEvalCrew
from openai import OpenAI
import litellm

app = Flask(__name__)
CORS(app)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Global variable to store analysis data for all images
analysis_data = {"reports": [], "images": []}

# Create heatmaps directory
HEATMAPS_DIR = Path("static/heatmaps")
HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def save_markdown_report(report: str) -> str:
    """Save the final report as a markdown file with a unique timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = OUTPUT_DIR / f"ui_analysis_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(report)
    return str(filename.absolute())


def save_heatmap(image: Image.Image) -> str:
    """Save blended image to heatmaps directory with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = HEATMAPS_DIR / f"heatmap_{timestamp}.png"
    image.save(filename)
    return str(filename.absolute())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload_heatmap", methods=["POST"])
def upload_heatmap():
    global analysis_data

    if "heatmap" not in request.files or "ui_image" not in request.files:
        return jsonify(error="No files uploaded"), 400

    try:
        # Process images
        ui_img = Image.open(request.files["ui_image"]).convert("RGBA")
        heatmap_img = Image.open(request.files["heatmap"]).convert("RGBA")

        # Image processing
        ui_np = np.array(ui_img)
        heatmap_np = np.array(heatmap_img)

        if ui_np.shape[:2] != heatmap_np.shape[:2]:
            heatmap_np = cv2.resize(heatmap_np, (ui_np.shape[1], ui_np.shape[0]))

        alpha = heatmap_np[..., 3] / 255.0
        alpha = np.expand_dims(alpha, axis=-1)

        ui_float = ui_np.astype(np.float32) / 255.0
        heatmap_float = heatmap_np.astype(np.float32) / 255.0

        blended = ui_float * (1 - alpha) + heatmap_float * alpha
        blended = (blended * 255).astype(np.uint8)
        combined_img = Image.fromarray(blended)

        # Save image and convert to base64
        heatmap_path = save_heatmap(combined_img)
        buffered = io.BytesIO()
        combined_img.save(buffered, format="PNG")
        combined_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Analyze the image using OpenAI's GPT-4
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this UI heatmap showing user gaze data. Identify areas of high and low attention."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{combined_base64}",
                        },
                    },
                ]
            }]
        )

        analysis_result = completion.choices[0].message.content

        # Store the analysis result and image for this heatmap
        analysis_data["reports"].append(analysis_result)
        analysis_data["images"].append(combined_base64)

        # If all 3 images have been processed, pass the results to the crew
        if len(analysis_data["reports"]) == 3:
            inputs = {
                "analysis_result": analysis_data["reports"]
            }
            results = UIEvalCrew().crew().kickoff(inputs=inputs)
            final_report = results.raw

            # Save the final report as a markdown file
            report_path = save_markdown_report(final_report)
            analysis_data["final_report"] = final_report

            # Reset the analysis data for the next set of images
            analysis_data["reports"] = []
            analysis_data["images"] = []

        return jsonify(message="Heatmap analyzed successfully")

    except Exception as e:
        print("Error processing heatmap:", str(e))
        return jsonify(error="Failed to analyze heatmap", details=str(e)), 500

# @app.route("/get_analysis", methods=["GET"])
# def get_analysis():
#     try:
#         # Safely wrap the multi-line string for JSON
#         final_report = analysis_data.get("final_report", "").strip()

#         return jsonify({
#             "final_report": final_report,
#             "images": analysis_data.get("images", [])
#         })
#     except Exception as e:
#         print("Error in /get_analysis:", str(e))
#         return jsonify(error="Failed to retrieve analysis", details=str(e)), 500

# @app.route("/analysis")
# def analysis():
#     return render_template("analysis.html")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
