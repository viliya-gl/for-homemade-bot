
import os
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

# Включаем ленивую загрузку для Chroma
os.environ["CHROMA_LAZY_LOAD"] = "1"

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_TOKEN не найден!")
    exit(1)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY не найден!")
    exit(1)

client = Groq(api_key=GROQ_API_KEY)

print("🔄 Загрузка Chroma...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="forhomemade",
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

def load_articles_to_chroma():
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    if collection.count() > 0:
        print(f"✅ В Chroma уже есть {collection.count()} документов")
        return
    
    print("📂 Загрузка статей в Chroma...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    count = 0
    for root, dirs, files in os.walk("./knowledge_base"):
        for file in files:
            if not file.endswith(".txt"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(path, "r", encoding="windows-1251") as f:
                    text = f.read()
            
            chunks = splitter.split_text(text)
            for i, chunk in enumerate(chunks):
                collection.add(
                    documents=[chunk],
                    ids=[f"{file[:-4]}_{count + i + 1}"]
                )
            count += len(chunks)
    
    print(f"✅ Загружено {count} чанков в Chroma")

load_articles_to_chroma()

def search_knowledge(query, top_k=2):
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        if results and results['documents'] and results['documents'][0]:
            return results['documents'][0]
        return []
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return []

def generate_answer(question, context_chunks):
    if not context_chunks:
        return "Извините, я не нашла информации в базе знаний. Попробуйте переформулировать вопрос."
    
    context = "\n\n".join(context_chunks)
    prompt = f"""
Ты — Валли, помощник бренда for.homemade.
Отвечай кратко и по делу, используя ТОЛЬКО контекст.
Если ответа нет — скажи: «Я не знаю».

### Контекст:
{context}

### Вопрос:
{question}

### Ответ:
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=512
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"

async def handle_message(update, context):
    question = update.message.text
    user_name = update.message.from_user.first_name
    print(f"\n📩 Вопрос от {user_name}: {question}")
    
    await update.message.reply_text("💭 Ищу ответ в базе знаний...")
    chunks = search_knowledge(question)
    answer = generate_answer(question, chunks)
    await update.message.reply_text(answer)

def main():
    print("🚀 Запуск бота с Chroma на Render...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()