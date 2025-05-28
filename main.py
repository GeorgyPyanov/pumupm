from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Конфигурация (вставьте свои ключи здесь)
OPENAI_API_KEY = "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"  # Замените на реальный ключ
TELEGRAM_BOT_TOKEN = "7649241013:AAHpMTn1H44Sb5YEJ6SiayyBwmSspddhd1k"  # Замените на реальный токен
KNOWLEDGE_FILE = "base.txt"  # Путь к файлу с базой знаний
EMBEDDING_MODEL = "text-embedding-3-small"  # Модель для эмбеддингов
LLM_MODEL = "gpt-4o"  # Модель для генерации ответов

class HSEChatBot:
    def __init__(self, knowledge_file):
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY  # Используем переменную напрямую
        )
        self.vectorstore = self._create_vectorstore(knowledge_file)
        self.prompt_template = self._create_prompt_template()

    def _create_vectorstore(self, file_path):
        """Создает векторное хранилище из файла"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Файл {file_path} не найден!")

        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Разбиваем текст на чанки
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_text(text)

        # Создаем эмбеддинги
        embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY  # Используем переменную напрямую
        )
        return FAISS.from_texts(chunks, embeddings)

    def _create_prompt_template(self):
        """Шаблон для генерации ответов"""
        return ChatPromptTemplate.from_messages([
            ("system", "Ты — Дана, старшекурсница ВШЭ. Отвечай дружелюбно, с легкой иронией и на 'ты'."),
            ("human", """Контекст о ВШЭ:
{context}

Вопрос: {question}
Ответ (максимум 3 предложения, без лишних деталей):""")
        ])

    async def answer(self, question):
        """Генерирует ответ на вопрос"""
        # 1. Ищем релевантные чанки
        docs = self.vectorstore.similarity_search(question, k=3)
        context = "\n---\n".join([d.page_content for d in docs])

        # 2. Генерируем ответ через LLM
        chain = self.prompt_template | self.llm
        response = await chain.ainvoke({
            "context": context,
            "question": question
        })

        return response.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я Дана, твой виртуальный куратор из ВШЭ. Спрашивай что угодно о вузе!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bot = context.bot_data['hse_bot']
        response = await bot.answer(update.message.text)
        await update.message.reply_text(response)
    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("Упс, что-то сломалось... Попробуй позже")

if __name__ == '__main__':
    # Проверка наличия файла с базой знаний
    if not Path(KNOWLEDGE_FILE).exists():
        raise FileNotFoundError(f"Файл {KNOWLEDGE_FILE} не найден!")

    # Инициализация
    bot = HSEChatBot(KNOWLEDGE_FILE)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()  # Используем переменную напрямую
    app.bot_data['hse_bot'] = bot

    # Хендлеры
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск
    print("Бот запущен...")
    app.run_polling()