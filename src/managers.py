import os
import json
import random
from typing import Optional, Literal, Dict, List
from datetime import datetime
from uuid import uuid4
from llm import analyze_reflection, analyze_report
from models import ReflectionEntry
from config import directory_initializer


class QuestionManager:
    def __init__(self):
        # Initialize the question manager
        self.period_to_frequency = {"daily": 365, "weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}
        self.frequency_to_period = {365: "daily", 52: "weekly", 12: "monthly", 4: "quarterly", 1: "yearly"}
        self.questions = self._load_questions()

    def _load_questions(self) -> Dict[str, int]:
        # Load the questions from the JSONL file
        with open("../data/questions.jsonl", "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f]
        if not data:
            return dict()

        # Get all questions and their frequency
        questions = {}
        for item in data:
            if item["question"] not in questions:
                questions[item["question"]] = self.period_to_frequency[item["period"]]
        return questions


    def get_random_question(self) -> str:
        return random.choices(list(self.questions.keys()), weights=list(self.questions.values()), k=1)[0]

    def add_question(self, question: str, period: Literal["daily", "weekly", "monthly", "quarterly", "yearly"] = "weekly") -> bool:
        if period not in self.period_to_frequency:
            return False
        self.questions[question] = self.period_to_frequency[period]
        self.save_questions()
        return True

    def save_questions(self) -> None:
        # Write to JSONL file
        with open("../data/questions.jsonl", "w+", encoding="utf-8") as f:
            for question, frequency in self.questions.items():
                record = {
                    "question": question,
                    "period": self.frequency_to_period[frequency]
                }
                f.write(json.dumps(record) + "\n")


class JournalManager:
    def __init__(self):
        self.uuid_str = uuid4().hex
        self.original_entry_id = None
        self.entries = {}

    def add_entry(self, question: str, answer: Optional[str] = None) -> ReflectionEntry:
        entry = ReflectionEntry(question=question, answer=answer)
        self.upsert_entry(entry)
        return entry

    def upsert_entry(self, entry: ReflectionEntry) -> None:
        if not self.original_entry_id:
            self.original_entry_id = entry.id
        self.entries[entry.id] = entry

    def get_entry(self, entry_id: str) -> Optional[ReflectionEntry]:
        return self.entries.get(entry_id)
    
    def get_unanswered_entry(self) -> Optional[ReflectionEntry]:
        for entry in self.entries.values():
            if not entry.answer:
                return entry
        return None

    def get_children(self, parent_id: str) -> List[ReflectionEntry]:
        children = []
        for child_id in self.entries[parent_id].children_ids:
            children.append(self.entries[child_id])
        return children
    
    def get_parent(self, child_id: str) -> Optional[ReflectionEntry]:
        return self.get_entry(self.entries[child_id].parent_id)

    def delete_entry(self, entry_id: str) -> bool:
        if entry_id in self.entries:
            parent = self.get_parent(entry_id)
            if parent:
                parent.children_ids.remove(entry_id)
            children = self.get_children(entry_id)
            for child in children:
                if parent:
                    child.parent_id = parent.id
                else:
                    self.delete_entry(child.id)
            del self.entries[entry_id]
            return True
        return False

    def get_stats(self) -> tuple[int, int]:
        analyzed_entries = len([entry for entry in self.entries.values() if entry.themes])
        return analyzed_entries, len(self.entries)

    def get_report(self, entry_id: str, prefix: str = "# ") -> str:
        # Get the entry and check if it exists and has an answer
        entry = self.get_entry(entry_id)
        if not entry or not entry.answer:
            return ""
        
        # Generate the string
        text = f"{prefix}{entry.question}\n\n"
        if entry.context:
            text += f"**{entry.context_type}**: {entry.context}\n\n"
        text += f"{entry.answer}\n\n"

        # Recursively get the children strings
        for child in self.get_children(entry_id):
            text += self.get_report(child.id, f"#{prefix} ")
        return text

    def analyze_entry(self, entry_id: str) -> bool:
        # Get the entry and check if it exists
        entry = self.get_entry(entry_id)
        if not entry or not entry.answer:
            print("Entry not found or answer not set")
            return False

        # Analyze the reflection
        analysis = analyze_reflection(entry.question, entry.answer)
        if not analysis:
            print("Analysis not generated")
            return False
        
        # Set the themes and sentiment
        entry.themes = analysis.themes
        entry.sentiment = analysis.sentiment

        # Create the children entries
        for belief in analysis.beliefs:
            new_entry = ReflectionEntry(
                question=belief.challenge_question, 
                context=belief.statement, 
                context_type=belief.belief_type,
                parent_id=entry.id
            )
            self.upsert_entry(new_entry)
            entry.children_ids.append(new_entry.id)
        return True

    def analyze_entries_and_save(self) -> Optional[str]:
        # Check if the original entry exists
        if not self.original_entry_id:
            return None
        
        # Get the report and analyze it
        report = self.get_report(self.original_entry_id)
        if not report:
            return None
        
        # Get the current date and prefixes for the directories and files
        now = datetime.now()
        dir_date_str = now.strftime("%Y_%m")
        file_date_str = now.strftime("%Y_%m_%d")

        # Save all the entries
        reflections_dir = f"../data/reflections/{dir_date_str}"
        directory_initializer.ensure_dir(reflections_dir)
        jsonl_file_path = f"{reflections_dir}/{file_date_str}_{self.uuid_str}.jsonl"
        if not os.path.exists(jsonl_file_path):
            with open(jsonl_file_path, "w+", encoding="utf-8") as f:
                for entry in self.entries.values():
                    f.write(entry.model_dump_json() + "\n")

        # Analyze the report and save it
        insights_dir = f"../data/insights/{dir_date_str}"
        directory_initializer.ensure_dir(insights_dir)
        insights_file_path = f"{insights_dir}/{file_date_str}_{self.uuid_str}.json"
        if os.path.exists(insights_file_path):
            with open(insights_file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Save the insights if they don't exist
        analysis = analyze_report(report)
        if not analysis:
            return None
        analysis_str = analysis.model_dump_json(indent=2)
        with open(insights_file_path, "w+", encoding="utf-8") as f:
            f.write(analysis_str)
        return analysis_str
