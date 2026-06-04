import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# Pydantic-моделі для структурованої відповіді ШІ
# ============================================================

class ActionItem(BaseModel):
    task: str = Field(..., description="Конкретне завдання, яке потрібно виконати")
    assignee: str = Field("Не визначено", description="Ім'я або роль особи, яка відповідає за виконання завдання")
    due_date: str = Field("Не визначено", description="Термін виконання або дедлайн")

class KeyTopic(BaseModel):
    topic: str = Field(..., description="Назва теми або питання, що обговорювалося")
    key_points: list[str] = Field(..., description="Основні тези, аргументи або деталі обговорення цієї теми")

class MeetingSummary(BaseModel):
    summary: str = Field(..., description="Короткий огляд (TL;DR) всієї зустрічі, її основна мета та результат")
    topics: list[KeyTopic] = Field(..., description="Список ключових обговорених тем")
    decisions: list[str] = Field(..., description="Список усіх прийнятих на зустрічі рішень та домовленостей")
    action_items: list[ActionItem] = Field(..., description="Список конкретних доручень та завдань за результатами зустрічі")


class AIService:
    """Сервіс для інтелектуального аналізу транскрипту зустрічі за допомогою Llama 3.3."""

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key.get_secret_value())
        self.model = "llama-3.3-70b-versatile"

    async def summarize_meeting(self, transcript: str) -> MeetingSummary:
        """
        Аналізує транскрипт зустрічі та повертає структуровану модель MeetingSummary.
        """
        logger.info("Відправляємо транскрипт в LLM для аналізу...")

        system_prompt = (
            "Ти — професійний AI-секретар та аналітик зустрічей. Твоє завдання — проаналізувати надану стенограму зустрічі "
            "та виділити з неї ключову інформацію у строгому JSON форматі.\n\n"
            "Зверни увагу на такі правила:\n"
            "1. Заповни всі поля моделі MeetingSummary.\n"
            "2. Визнач ключові теми (topics) та головні тези для кожної теми.\n"
            "3. Знайди всі прийняті рішення (decisions).\n"
            "4. Знайди всі доручення та завдання (action_items). Для кожного завдання чітко вкажи: суть завдання, "
            "хто відповідальний (assignee), і який дедлайн (due_date) було озвучено.\n"
            "5. Якщо відповідального або дедлайн не було озвучено, запиши 'Не визначено'.\n"
            "6. Мова відповіді повинна бути такою ж, якою велася зустріч (пріоритет — українська мова).\n"
            "7. Твоя відповідь має містити виключно валідний JSON, де поля лежать на найвищому рівні. Наприклад:\n"
            "{\n"
            "  \"summary\": \"Короткий огляд...\",\n"
            "  \"topics\": [{\"topic\": \"Тема\", \"key_points\": [\"Теза 1\"]\}],\n"
            "  \"decisions\": [\"Рішення 1\"],\n"
            "  \"action_items\": [{\"task\": \"Завдання\", \"assignee\": \"Ім'я\", \"due_date\": \"Дедлайн\"\}]\n"
            "}"
        )

        user_content = f"Стенограма зустрічі для аналізу:\n\n{transcript}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                # Активуємо JSON mode для гарантованого отримання валідного JSON
                response_format={"type": "json_object"},
                temperature=0.2
            )

            response_content = response.choices[0].message.content
            logger.info(f"Отримано відповідь LLM: {response_content}")
            response_json = json.loads(response_content)
            
            # Якщо модель загорнула все в кореневий об'єкт (наприклад, "meeting_summary" або подібний)
            # перевіряємо, чи немає там вкладеності з ключовими полями всередині.
            if isinstance(response_json, dict) and len(response_json) == 1:
                root_key = list(response_json.keys())[0]
                inner_value = response_json[root_key]
                if isinstance(inner_value, dict) and ("summary" in inner_value or "topics" in inner_value):
                    logger.info(f"Розпаковуємо вкладений JSON з ключа: {root_key}")
                    response_json = inner_value
            
            # Валідуємо отриманий JSON через Pydantic-модель
            summary_model = MeetingSummary.model_validate(response_json)
            logger.info("Аналіз зустрічі успішно завершено та провалідовано ШІ.")
            return summary_model

        except Exception as e:
            logger.error(f"Помилка при аналізі зустрічі через LLM: {e}")
            raise e

    @staticmethod
    def format_summary_to_markdown(summary: MeetingSummary) -> str:
        """Перетворює об'єкт MeetingSummary у красивий Markdown текст."""
        md = []
        md.append("# 📝 Протокол зустрічі та Action Items\n")
        
        md.append("## 📌 Короткий опис (TL;DR)")
        md.append(f"{summary.summary}\n")
        
        md.append("## 💬 Ключові теми обговорення")
        for i, t in enumerate(summary.topics, 1):
            md.append(f"### {i}. {t.topic}")
            for point in t.key_points:
                md.append(f"* {point}")
            md.append("")
            
        md.append("## 🤝 Прийняті рішення")
        if summary.decisions:
            for dec in summary.decisions:
                md.append(f"* {dec}")
        else:
            md.append("*Рішень не зафіксовано.*")
        md.append("")
        
        md.append("## ⚡ Завдання та доручення (Action Items)")
        if summary.action_items:
            for item in summary.action_items:
                md.append(f"* **Завдання:** {item.task}")
                md.append(f"  * 👤 **Відповідальний:** {item.assignee}")
                md.append(f"  * 📅 **Термін:** {item.due_date}")
        else:
            md.append("*Завдань не зафіксовано.*")
            
        return "\n".join(md)
