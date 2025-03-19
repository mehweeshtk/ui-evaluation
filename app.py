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
from pydantic import Field, BaseModel
from typing import List

app = Flask(__name__)
CORS(app)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Global variable to store analysis data for all images
analysis_data = {"reports": [], "images": []}

# Create heatmaps directory
HEATMAPS_DIR = Path("output/heatmaps")
HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def save_markdown_report(report: str, images: List[str]) -> str:
    """Save the final report as a markdown file with a unique timestamp and embedded images."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = OUTPUT_DIR / f"ui_analysis_{timestamp}.md"
    
    # Split the report into sections for each image
    sections = report.split("---")
    
    # Create the markdown content with embedded images
    markdown_content = ""
    for i, section in enumerate(sections):
        markdown_content += section.strip() + "\n\n"
        if i < len(images):
            # Replace backslashes with forward slashes in the image path
            image_path = f"heatmaps/{Path(images[i]).name}"
            markdown_content += f"![Image {i+1}]({image_path})\n\n"
    
    # Write the markdown content to the file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(markdown_content)
    
    return str(filename.absolute())


def save_heatmap(image: Image.Image) -> str:
    """Save blended image to heatmaps directory with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = HEATMAPS_DIR / f"heatmap_{timestamp}.png"
    image.save(filename)
    return str(filename.relative_to(HEATMAPS_DIR.parent))


# Define nested models for each dictionary field
class VisualClarityWeakness(BaseModel):
    issue: str = Field(
        description="""
        A detailed description of an issue in the user interface in accordance with established UI and usability conventions, standards, and heuristics.
        Explain why it is a weakness in terms of visual clarity and usability.
        """
    )
    location: str = Field(
        description="The location of the issue in the UI (e.g., 'bottom-right corner')."
    )
    severity: str = Field(
        description="""
        The severity of the issue (e.g., 'high', 'medium', 'low').
        Justify the severity level by explaining:
        - The impact of the issue on the user experience.
        - The likelihood of users encountering the issue.
        """
    )
    impact: str = Field(
        description="""
        How the issue impacts user behavior and experience.
        """
    )
    heatmap_correlation: str = Field(
        description="""
        Explain how the heatmap data supports the identified weakness. Include:
        - Specific heatmap observations (e.g., 'Users ignored the "Add to Basket" button, which aligns with its low contrast and poor placement').
        - Whether the heatmap data confirms the weakness (e.g., 'Low fixation on the button supports the issue of poor visibility').
        """
    )

class PrimaryFixationArea(BaseModel):
    area: str = Field(
        description="The specific UI element (e.g., 'product image', 'product name and price')."
    )
    reason: str = Field(
        description="""
        The reason for high attention (e.g., 'Large size and central placement align with the F-pattern').
        Include how it aligns with established UI and usability conventions, standards, and heuristics.
        """
    )
    alignment_with_goals: str = Field(
        description="""
        How this area aligns with or deviates from usability principles (e.g., Fitts Law, Gestalt principles, Hick’s Law).
        Provide specific examples of alignment or deviation.
        """
    )
    heatmap_correlation: str = Field(
        description="""
        Explain how the heatmap data supports the identified strength. Include:
        - Specific heatmap observations (e.g., 'Users focused heavily on the product image, which aligns with its prominent placement').
        - Whether the heatmap data confirms the strength (e.g., 'High fixation on the product image supports its effectiveness in capturing user attention').
        """
    )

class IgnoredArea(BaseModel):
    area: str = Field(
        description="The specific UI element (e.g., 'navigation bar', 'footer links')."
    )
    reason: str = Field(
        description="""
        The reason for low attention (e.g., 'Low contrast and poor placement outside the natural gaze path').
        Include how it deviates from established UI and usability conventions, standards, and heuristics.
        """
    )
    critical_to_task: str = Field(
        description="""
        Whether this area is critical to the user’s task (e.g., 'CTA buttons', 'navigation links').
        Provide a detailed explanation of why this area is or isn't critical.
        """
    )

class AccessibilityIssue(BaseModel):
    issue: str = Field(
        description="""
        The specific issue (e.g., 'Text contrast ratio for some elements is 3:1, which does not meet the required 4.5:1 for normal text').
        Include how it deviates from WCAG 2.1 standards.
        """
    )
    location: str = Field(
        description="The location of the issue in the UI (e.g., 'product description')."
    )
    severity: str = Field(
        description="""
        The severity of the issue (e.g., 'high', 'medium', 'low').
        Justify the severity level by explaining:
        - The impact of the issue on the user experience.
        - The likelihood of users encountering the issue.
        """
    )
    impact: str = Field(
        description="""
        How this issue impacts user behavior (e.g., 'Reduced readability leads to user frustration').
        Include specific examples of how the issue affects user interactions.
        """
    )

class APIAnalysis(BaseModel):
    # Visual Clarity & Usability
    visual_clarity_strengths: List[PrimaryFixationArea] = Field(
        title="Visual Clarity & Usability Strengths", 
        description="""
        Identify 3-4 elements of the user interface that align well with established UI and usability conventions, standards, and heuristics.
        For each strength, provide:
        - The specific UI element.
        - The reason for high attention.
        - How this area aligns with usability principles.
        - How the heatmap data supports the strength.
        """, 
        default_factory=list
    )

    visual_clarity_weaknesses: List[VisualClarityWeakness] = Field(
        title="Visual Clarity & Usability Weaknesses", 
        description="""
        Identify 3-4 elements of the user interface that contribute to poor usability and aesthetics.
        For each weakness, provide:
        - A detailed description of the issue.
        - The location of the issue in the UI.
        - The severity of the issue.
        - How the issue impacts user behavior.
        - How the heatmap data supports the weakness.
        - Detailed recommendations to address the weakness.
        """, 
        default_factory=list
    )

    # Heatmap Analysis
    primary_fixation_areas: List[PrimaryFixationArea] = Field(
        title="Primary Fixation Areas", 
        description="""
        Identify the areas of the UI that received the highest user attention based on heatmap data.
        For each area, provide:
        - The specific UI element.
        - The reason for high attention.
        - How this area aligns with or deviates from usability principles.
        - How the heatmap data supports the strength.
        """, 
        default_factory=list
    )
    
    ignored_areas: List[IgnoredArea] = Field(
        title="Ignored Areas", 
        description="""
        Identify UI elements that received minimal attention in the heatmap.
        For each area, provide:
        - The specific UI element.
        - The reason for low attention.
        - Whether this area is critical to the user’s task.
        - The impact of this lack of attention on user behavior.
        - Detailed recommendations to address the weakness.
        """, 
        default_factory=list
    )

    # Accessibility & Contrast (WCAG)
    overall_wcag_standards: str = Field(
        title="Overall WCAG Standards", 
        description="""
        Evaluate whether the UI meets WCAG 2.1 standards and specify the conformance level (A, AA, or AAA).
        Provide a detailed explanation of the reasoning behind the compliance level, including:
        - Specific elements that meet or do not meet WCAG guidelines.
        - Recommendations to improve accessibility where needed.
        """
    )

    accessibility: List[AccessibilityIssue] = Field(
        description="""
        Cross-reference heatmap data with WCAG compliance issues.
        For each issue, provide:
        - The specific issue.
        - The location of the issue in the UI.
        - The severity of the issue.
        - How this issue impacts user behavior.
        - Detailed recommendations to address the issue.
        """,
        default_factory=list
    )

    ui_standards: List[str] = Field(
        title="Reference Standards", 
        description="""
        List the UI/UX principles, guidelines, and heuristics used in this analysis.
        Provide specific examples (e.g., 'Nielsen's 10 Usability Heuristics', 'Gestalt principles', 'WCAG 2.1 guidelines').
        """, 
        default_factory=list
    )

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
        analysis_data["images"].append(heatmap_path)
        buffered = io.BytesIO()
        combined_img.save(buffered, format="PNG")
        combined_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Analyze the image using OpenAI's GPT-4
        client = OpenAI()
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this UI heatmap showing user gaze data for its visual clarity and whether it meets WCAG standards. Identify areas of high and low attention. All points should be explained in detail and justified by standard UI/UX principles, practices, heuristics and existing research."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{combined_base64}",
                        },
                    },
                ]
            }],
            response_format=APIAnalysis
        )

        analysis_result = completion.choices[0].message.content

        # Store the analysis result and image for this heatmap
        analysis_data["reports"].append(analysis_result)

        # If all 3 images have been processed, pass the results to the crew
        if len(analysis_data["reports"]) == 3:
            inputs = {
                "analysis_result": analysis_data["reports"]
            }
            results = UIEvalCrew().crew().kickoff(inputs=inputs)
            final_report = results.raw

            # Save the final report as a markdown file
            report_path = save_markdown_report(final_report, analysis_data["images"])
            analysis_data["final_report"] = final_report

            # Reset the analysis data for the next set of images
            analysis_data["reports"] = []
            analysis_data["images"] = []

        return jsonify(message="Heatmap analyzed successfully")

    except Exception as e:
        print("Error processing heatmap:", str(e))
        return jsonify(error="Failed to analyze heatmap", details=str(e)), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
