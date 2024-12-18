from typing import Optional
from openai import OpenAI
from models import ReflectionAnalysis, ReportAnalysis
from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def analyze_reflection(question: str, answer: str, language: str = "en") -> Optional[ReflectionAnalysis]:
    # Instructions for the LLM
    instructions = {
        "en": """Extract information from the reflection and provide a detailed analysis.
                The analysis will include a list of general topics that the answer talks about.
                It will include the sentiment of the answer from positive to negative.
                It will include a list of beliefs or blind spots that the answer assumes or contradicts.
                The list of beliefs should be between 1 and 3 beliefs.
                Each belief will have a challenge question that will help the user to understand the belief better and explore it deeper.
                Create open questions and avoid yes or no questions, use questions that are practical and useful.""",
        "es": """Extrae información de la reflexión y proporciona un análisis detallado en español.
                El análisis incluirá una lista de temas generales de los que habla la respuesta.
                Incluirá el sentimiento de la respuesta de positivo a negativo.
                Incluirá una lista de creencias o puntos ciegos que la respuesta asume o contradice.
                La lista de creencias debe tener entre 1 y 3 creencias.
                Cada creencia tendrá una pregunta de desafío que ayudará al usuario a comprender mejor la creencia y explorarla más profundamente.
                Crea preguntas abiertas y evita preguntas de sí o no, usa preguntas prácticas y útiles.
                Asegúrate de que todo el análisis esté en español."""
    }
    content = {
        "en": f"Question: {question}\nAnswer: {answer}\n",
        "es": f"Pregunta: {question}\nRespuesta: {answer}\n"
    }
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instructions.get(language, instructions["en"])},
                {"role": "user", "content": content.get(language, content["en"])},
            ],
            response_format=ReflectionAnalysis,
            temperature=0.0,
            max_tokens=2000
        )
    except Exception as e:
        print(e)
        return None
    return completion.choices[0].message.parsed


def analyze_report(report: str, language: str = "en") -> Optional[ReportAnalysis]:
    instructions = {
        "en": """You will analyze a report of questions and answers from a reflection journal.
                The main question will be the question that the report is related to.
                The answer summary will be an overall answer of the main question of the report with the main points.
                The insights will be a list of insights on the core beliefs and assumptions that the report provides.
                The themes will be a list of themes that the insight talks about.
                The goal will be a short description of the goal that the report is related to based on the insights.
                The tasks will be a long a detail list of tasks from start to finish that I can do to archive the goal in the shortest time possible.
                The importance of the tasks will be a rating of the tasks from high to low based on the insights.""",
        "es": """Analizarás un informe de preguntas y respuestas de un diario de reflexión. Proporciona todo el análisis en español.
                La pregunta principal será la pregunta a la que se refiere el informe.
                El resumen de la respuesta será una respuesta general de la pregunta principal del informe con los puntos principales.
                Las percepciones serán una lista de ideas sobre las creencias y suposiciones fundamentales que proporciona el informe.
                Los temas serán una lista de temas que las percepciones abordan.
                El objetivo será una breve descripción de la meta a la que se refiere el informe basada en las percepciones.
                Las tareas serán una lista larga y detallada de tareas de principio a fin que puedo hacer para alcanzar el objetivo en el menor tiempo posible.
                La importancia de las tareas será una calificación de las tareas de alta a baja basada en las percepciones.
                Asegúrate de que todas las respuestas estén en español."""
    }
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instructions.get(language, instructions["en"])},
                {"role": "user", "content": report},
            ],
            response_format=ReportAnalysis,
            temperature=0.0,
            max_tokens=5000
        )
    except Exception as e:
        print(e)
        return None
    return completion.choices[0].message.parsed
