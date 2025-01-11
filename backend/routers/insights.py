import logging
from uuid import uuid4
from datetime import datetime
from typing import Optional, List
from backend.routers.reflections import ReflectionManager
from backend.models import Insight, ReflectionEntry
from backend.routers.llm import analyze_report, analyze_reflection


class InsightsManager:
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

    def _generate_insights(self) -> bool:
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
        
        now = datetime.now()
        # TODO: develop in sqllite, Save reflections
        # TODO: develop in sqllite, Save summary
        # TODO: develop in sqllite, Save insights
        # TODO: develop in sqllite, Save tags?
        return True