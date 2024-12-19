# %%
import json
import random
from typing import Optional, List, Dict, Union
from datetime import datetime
from uuid import uuid4
from llm import analyze_reflection, analyze_report
from models import Languages
from models import QuestionEntry, ReflectionEntry, Insight
from config import DirectoryInitializer
import logging


class QuestionManager:
    file_path: str
    question_entries: Dict[str, QuestionEntry]

    def __init__(self, file_path: str = "../data/questions.jsonl"):
        self.file_path = file_path
        self.question_entries = {}
        self._load_questions()

    def _add_question(self, question_entry: QuestionEntry) -> bool:
        if question_entry.question not in self.question_entries:
            self.question_entries[question_entry.question] = question_entry
            return True
        return False

    def _load_questions(self) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        current_question = QuestionEntry(**data)
                    except Exception as e:
                        logging.error(e)
                        continue
                    self._add_question(current_question)
        except FileNotFoundError:
            logging.warning(f"Questions file not found at {self.file_path}")
        except Exception as e:
            logging.error(f"Error loading questions: {e}")

    def _save_questions(self) -> None:
        try:
            with open(self.file_path, "w+", encoding="utf-8") as f:
                for question in self.question_entries.values():
                    f.write(question.model_dump_json() + "\n")
        except Exception as e:
            logging.error(f"Error saving questions: {e}")

    def get_random_question_entry(self) -> QuestionEntry:
        weights = [question.weight for question in self.question_entries.values()]
        return random.choices(list(self.question_entries.values()), weights=weights, k=1)[0]

    def add_question_entry(self, question_entry: QuestionEntry) -> bool:
        question_entry = QuestionEntry(**question_entry.model_dump())
        if self._add_question(question_entry):
            self._save_questions()
            return True
        return False
    
    def delete_question(self, question: str) -> bool:
        if question in self.question_entries:
            del self.question_entries[question]
            self._save_questions()
            return True
        return False


class ReflectionManager:
    original_entry_id: Optional[str]
    reflection_entries: Dict[str, ReflectionEntry]

    def __init__(self):
        self.original_entry_id = None
        self.reflection_entries = {}

    def upsert_reflection(self, reflection_entry: Union[ReflectionEntry, QuestionEntry]) -> str:
        if isinstance(reflection_entry, QuestionEntry):
            reflection_entry = ReflectionEntry(**reflection_entry.model_dump())
        if not self.original_entry_id:
            self.original_entry_id = reflection_entry.id
        self.reflection_entries[reflection_entry.id] = reflection_entry
        return reflection_entry.id
    
    def load_reflections(self, file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    current_entry = ReflectionEntry(**data)
                except Exception as e:
                    logging.error(e)
                    continue
                self.upsert_reflection(current_entry)

    def save_reflections(self, file_path: str) -> None:
        with open(file_path, "w+", encoding="utf-8") as f:
            for entry in self.reflection_entries.values():
                f.write(entry.model_dump_json() + "\n")

    def get_reflection_by_id(self, reflection_id: str) -> Optional[ReflectionEntry]:
        return self.reflection_entries.get(reflection_id)
    
    def get_parent_by_id(self, reflection_id: str) -> Optional[ReflectionEntry]:
        if reflection_id in self.reflection_entries:
            parent_id = self.reflection_entries[reflection_id].parent_id
            if parent_id:
                return self.get_reflection_by_id(parent_id)
        return None

    def get_children_by_id(self, reflection_id: str) -> List[ReflectionEntry]:
        children = []
        for child_id in self.reflection_entries[reflection_id].children_ids:
            children.append(self.reflection_entries[child_id])
        return children
    
    def get_unanswered_reflection_entry(self) -> Optional[ReflectionEntry]:
        unanswered_entries = [entry for entry in self.reflection_entries.values() if not entry.answer]
        if unanswered_entries:
            return random.choice(unanswered_entries)
        return None
    
    def get_language(self) -> Languages:
        for entry in self.reflection_entries.values():
            if entry.language:
                return entry.language
        return Languages.EN

    def delete_reflection_by_id(self, reflection_id: str) -> bool:
        if reflection_id in self.reflection_entries:
            # Remove the reflection from the parent
            parent = self.get_parent_by_id(reflection_id)
            if parent:
                parent.children_ids.remove(reflection_id)
            
            # Remove the reflection from the children
            children = self.get_children_by_id(reflection_id)
            for child in children:
                if parent:
                    child.parent_id = parent.id
                    parent.children_ids.append(child.id)
                else:
                    self.delete_reflection_by_id(child.id)

            # Remove the reflection from the entries
            del self.reflection_entries[reflection_id]
            return True
        return False

    def delete_all_reflections_without_answer(self) -> None:
        for reflection in self.reflection_entries.values():
            if not reflection.answer:
                self.delete_reflection_by_id(reflection.id)

    def analyze_reflection_by_id(self, reflection_id: str) -> bool:
        # Get the entry and check if it exists
        reflection = self.get_reflection_by_id(reflection_id)
        if not reflection or not reflection.answer:
            logging.warning("Reflection not found or answer not set")
            return False
        
        # Skip if already analyzed
        if reflection.themes and reflection.sentiment:
            return True

        # Analyze the reflection
        analysis = analyze_reflection(reflection.question, reflection.answer, reflection.language.value)
        if not analysis:
            logging.warning("Analysis not generated")
            return False
        
        # Set the themes and sentiment
        reflection.themes = analysis.themes
        reflection.sentiment = analysis.sentiment

        # Create the children entries
        for belief in analysis.beliefs:
            new_reflection = ReflectionEntry(
                question=belief.challenge_question, 
                context=belief.statement, 
                context_type=belief.belief_type,
                parent_id=reflection.id,
                language=reflection.language
            )
            self.upsert_reflection(new_reflection)
            reflection.children_ids.append(new_reflection.id)
        return True

    def analyze_all_reflections(self) -> None:
        for reflection in self.reflection_entries.values():
            self.analyze_reflection_by_id(reflection.id)

    def _get_recursive_report(self, entry_id: str, prefix: str = "# ") -> str:
        # Get the entry and check if it exists and has an answer
        entry = self.get_reflection_by_id(entry_id)
        if not entry or not entry.answer:
            return ""
        
        # Generate the string
        text = f"{prefix}{entry.question}\n\n"
        if entry.context:
            text += f"**{entry.context_type}**: {entry.context}\n\n"
        text += f"{entry.answer}\n\n"

        # Recursively get the children strings
        for child in self.get_children_by_id(entry_id):
            text += self._get_recursive_report(child.id, f"#{prefix} ")
        return text
    
    def get_report(self) -> str:
        if not self.original_entry_id:
            return ""
        return self._get_recursive_report(self.original_entry_id)
    
    def get_statistics(self) -> tuple[int, int]:
        analyzed_entries = len([entry for entry in self.reflection_entries.values() if entry.themes])
        return analyzed_entries, len(self.reflection_entries)


class JournalManager:
    uuid_str: str
    reflection_manager: ReflectionManager
    summary_entry: Optional[ReflectionEntry]
    insights: List[Insight]

    def __init__(self, reflection_manager: ReflectionManager):
        self.uuid_str = uuid4().hex
        self.reflection_manager = reflection_manager
        self.insights = []
        self.summary_entry = None
    
    def get_summary_entry(self) -> Optional[ReflectionEntry]:
        return self.summary_entry
    
    def get_insights(self) -> List[Insight]:
        return self.insights

    def _generate_journal_entry(self) -> bool:
        # Get the report
        report = self.reflection_manager.get_report()
        if not report:
            return False
        
        # Analyze the report
        language = self.reflection_manager.get_language()
        analysis = analyze_report(report, language.value)
        if not analysis:
            return False
        
        # Create the summary entry and insights
        reflection_analysis = analyze_reflection(analysis.main_question, analysis.answer_summary, language.value)
        if not reflection_analysis:
            return False
        self.summary_entry = ReflectionEntry(
            question=analysis.main_question,
            answer=analysis.answer_summary,
            language=language,
            themes=reflection_analysis.themes,
            sentiment=reflection_analysis.sentiment,
            context='\n'.join([belief.belief_type + ': ' + belief.statement for belief in reflection_analysis.beliefs]),
        )
        self.insights = analysis.insights
        return True

    def save_journal_entry(self) -> bool:
        if not self._generate_journal_entry():
            logging.error("Journal entry not generated")
            return False
        
        # Get the current date and strings
        now = datetime.now()
        month_str = now.strftime("%Y_%m")
        day_str = now.strftime("%Y_%m_%d")

        # Create directories
        directory_initializer = DirectoryInitializer()
        reflections_month_dir = f"{directory_initializer.reflections_dir}/{month_str}"
        reflection_summaries_month_dir = f"{directory_initializer.reflection_summaries_dir}/{month_str}"
        reflection_insights_month_dir = f"{directory_initializer.reflection_insights_dir}/{month_str}"
        directory_initializer.ensure_dir(reflections_month_dir)
        directory_initializer.ensure_dir(reflection_summaries_month_dir)
        directory_initializer.ensure_dir(reflection_insights_month_dir)

        # Save the reflections
        self.reflection_manager.save_reflections(f"{reflections_month_dir}/{day_str}_{self.uuid_str}.jsonl")

        # Save the insights
        if self.insights:
            with open(f"{reflection_insights_month_dir}/{day_str}_{self.uuid_str}.jsonl", "w+", encoding="utf-8") as f:
                for insight in self.insights:
                    f.write(insight.model_dump_json() + "\n")

        # Save the summary
        if self.summary_entry:
            with open(f"{reflection_summaries_month_dir}/{day_str}_{self.uuid_str}.json", "w+", encoding="utf-8") as f:
                f.write(self.summary_entry.model_dump_json(indent=2))
        
        return True

# %%
