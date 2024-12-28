# %%
import json
import random
from typing import Optional, List, Dict, Union
from datetime import datetime
from uuid import uuid4
from llm import analyze_reflection, analyze_report
from models import Languages, QuestionEntry, ReflectionEntry, Insight
import logging


class QuestionManager:
    file_path: str
    question_entries: Dict[str, QuestionEntry]

    def __init__(self, file_path: str):
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
    user_id: str
    original_entry_id: Optional[str]
    reflection_entries: Dict[str, ReflectionEntry]

    def __init__(self, user_id: str):
        self.user_id = user_id
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

            # Remove the reflection from the original entry
            if self.original_entry_id == reflection_id:
                self.original_entry_id = None
                self.reflection_entries = {}

            return True
        return False

    def delete_all_reflections_without_answer(self) -> None:
        ids_without_answer = [reflection.id for reflection in self.reflection_entries.values() if not reflection.answer]
        for id in ids_without_answer:
            self.delete_reflection_by_id(id)

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

    def save_journal_entry(self, directory_path: str) -> bool:
        if not self._generate_journal_entry():
            logging.error("Journal entry not generated")
            return False
        
        now = datetime.now()
        # TODO: develop in typeDB, Save reflections
        # TODO: develop in typeDB, Save summary
        # TODO: develop in typeDB, Save insights
        # TODO: save tags
        return True

# %%
