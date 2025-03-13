from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import Field, BaseModel
import yaml
import os
from openai import OpenAI
import base64

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

    @agent
    def image_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['image_analyzer'],
            tools=[]
        )

    @agent
    def ui_recommender(self) -> Agent:
        return Agent(
            config=self.agents_config['ui_recommender'],
            tools=[]
        )

    @agent
    def report_compiler(self) -> Agent:
        return Agent(
            config=self.agents_config['report_compiler'],
            tools=[]
        )


    @task
    def analyze_image_base64(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_image_base64'],
            tools=[]
        )

    @task
    def generate_ui_recommendations(self) -> Task:
        return Task(
            config=self.tasks_config['generate_ui_recommendations'],
            tools=[]
        )

    @task
    def compile_report(self) -> Task:
        return Task(
            config=self.tasks_config['compile_report'],
            tools=[]
        )


    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
