import json
import random
import logging
from typing import Optional, Dict, List, Union
from backend.models import ReflectionEntry, QuestionEntry, Languages
from backend.routers.llm import analyze_reflection

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
    
    def get_language_by_id(self, reflection_id: str) -> Languages:
        if reflection_id in self.reflection_entries:
            return self.reflection_entries[reflection_id].language
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