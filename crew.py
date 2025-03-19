from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import Field, BaseModel
from typing import Dict, List
import yaml
import os
from openai import OpenAI
import base64

from pydantic import BaseModel, Field
from typing import List

class StrengthAnalysis(BaseModel):
    strength: str = Field(
        title="Strength",
        description="""
        The specific strength noticed in the user interface.
        Provide a detailed explanation of the strength, including:
        - How it aligns with established UI and usability conventions, standards, and heuristics (e.g., Nielsen's 10 Usability Heuristics, Gestalt principles).
        - Specific examples from the UI (e.g., 'The product image is prominently placed and aligns with the F-pattern, capturing user attention effectively').
        """,
    )
    heatmap_correlation: str = Field(
        title="Heatmap Correlation",
        description="""
        Explain how the heatmap data supports the identified strength. Include:
        - Specific heatmap observations (e.g., 'Users focused heavily on the product image, which aligns with its prominent placement').
        - Whether the heatmap data confirms the strength (e.g., 'High fixation on the product image supports its effectiveness in capturing user attention').
        """,
    )

class WeaknessAnalysis(BaseModel):
    weakness: str = Field(
        title="Weakness",
        description="""
        The specific weakness noticed in the user interface.
        Provide a detailed explanation of the weakness, including:
        - How this element deviates from established UI and usability conventions, standards, and heuristics (e.g., Nielsen's 10 Usability Heuristics, WCAG guidelines).
        - Specific examples from the UI (e.g., 'The "Add to Basket" button has low contrast with the background').
        """,
    )
    reason: str = Field(
        title="Reason",
        description="""
        Explain why the weakness is problematic in accordance with UI guidelines.
        Include:
        - The specific UI guideline or heuristic violated (e.g., 'Nielsen's Visibility of System Status heuristic').
        - Why this issue negatively impacts the user experience (e.g., 'Low contrast makes the button difficult to notice, leading to missed conversions').
        """,
    )
    heatmap_correlation: str = Field(
        title="Heatmap Correlation",
        description="""
        Explain how the heatmap data supports the identified weakness. Include:
        - Specific heatmap observations (e.g., 'Users ignored the "Add to Basket" button, which aligns with its low contrast and poor placement').
        - Whether the heatmap data confirms the weakness (e.g., 'Low fixation on the button supports the issue of poor visibility').
        """,
    )
    severity: str = Field(
        title="Severity",
        description="""
        Specify the severity of the weakness (e.g., 'High', 'Medium', 'Low').
        Justify the severity level by explaining:
        - The impact of the weakness on the user experience (e.g., 'High severity because the issue directly impacts conversion rates').
        - The likelihood of users encountering the issue (e.g., 'All users will struggle to notice the button due to its low contrast').
        """,
    )
    impact: str = Field(
        title="Impact",
        description="""
        Explain the impact of the weakness on user behavior and experience. Include:
        - How the weakness affects user interactions (e.g., 'Users are less likely to add items to the cart due to the button's poor visibility').
        """,
    )
    recommendations: str = Field(
        title="Recommendations",
        description="""
        Provide detailed recommendations to address the identified weakness. Include:
        - Specific actions to take (e.g., 'Increase the button's contrast to 4.5:1 and reposition it to the top-right corner').
        - How the recommendation aligns with UI/UX best practices (e.g., 'This aligns with Nielsen's Visibility of System Status heuristic').
        - The expected impact of implementing the recommendation (e.g., 'Increased button visibility will lead to higher conversion rates').
        """,
    )

class ImageRecommendations(BaseModel):

    image_number: int = Field(..., title="Image Number", description="Unique identifier for each image")

    strengths: List[StrengthAnalysis] = Field(
        title="Strengths Analysis",
        description="""
        List of 3-4 strengths identified in the user interface.
        Each strength should include:
        - A detailed description of the strength.
        - How the heatmap data supports the strength.
        """,
        default_factory=list
    )
    weaknesses: List[WeaknessAnalysis] = Field(
        title="Weaknesses Analysis",
        description="""
        List of 3-4 weaknesses identified in the user interface.
        Each weakness should include:
        - A detailed description of the weakness.
        - The reason why it's problematic.
        - How the heatmap data supports the weakness.
        - The severity and impact of the weakness.
        - Detailed recommendations to address the weakness.
        """,
        default_factory=list
    )
    wcag_standards: str = Field(
        title="WCAG Standards",
        description="""
        Evaluate whether the UI meets WCAG 2.1 standards and specify the conformance level (A, AA, or AAA).
        Provide a detailed explanation of the reasoning behind the compliance level, including:
        - Specific elements that meet or do not meet WCAG guidelines (e.g., 'Text contrast ratio for some elements is 3:1, which does not meet the required 4.5:1 for normal text').
        - Recommendations to improve accessibility where needed (e.g., 'Increase text contrast to 4.5:1 for all elements').
        """,
    )
    separator: str = Field(
        default="---",
        description="Horizontal rule separator between sections.",
    )


# class Recommendations(BaseModel):
#     images: List[ImageRecommendations] = Field(
#         title="Image Analysis and Recommendations",
#         description="List of analysis and recommendations for each user interface image.",
#         default_factory=list
#     )

# class ReportFormat(BaseModel):
#     title: str = Field(title="Usability Analysis Report")
#     overview: str = Field(title="Overview", description="A brief overview of the use case and the usability analysis report.")
#     images: List[Dict] = Field(
#         title="Image Analysis and Recommendations",
#         description="Analysis and recommendations for each user interface image.",
#         default_factory=list
#     )
#     summary: str = Field(title="Summary", description="A summary of the usability analysis report.")

@CrewBase
class UIEvalCrew():
    agents_config_path = 'config/agents.yaml'
    tasks_config_path = 'config/tasks.yaml'

    os.environ["OPENAI_MODEL_NAME"] = "gpt-4o"

    def load_agents_config(self):
        with open(self.agents_config_path, 'r') as file:
            return yaml.safe_load(file)

    def load_tasks_config(self):
        with open(self.tasks_config_path, 'r') as file:
            return yaml.safe_load(file)

    # @agent
    # def image_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['image_analyzer'],
    #         tools=[],
    #         output_json = ImageAnalysis
    #     )

    @agent
    def ui_recommender(self) -> Agent:
        return Agent(
            config=self.agents_config['ui_recommender'],
            tools=[],
        )

    @agent
    def report_compiler(self) -> Agent:
        return Agent(
            config=self.agents_config['report_compiler'],
            tools=[]
        )


    # @task
    # def analyze_image_base64(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['analyze_image_base64'],
    #         tools=[]
    #     )

    @task
    def generate_ui_recommendations(self) -> Task:
        return Task(
            config=self.tasks_config['generate_ui_recommendations'],
            tools=[],
            output_pydantic = ImageRecommendations
        )

    @task
    def compile_report(self) -> Task:
        return Task(
            config=self.tasks_config['compile_report'],
            tools=[]
            # output_pydantic=Recommendations
        )


    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
