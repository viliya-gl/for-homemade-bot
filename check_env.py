import os
from dotenv import load_dotenv

load_dotenv()

print("=== Содержимое .env ===")
print("GROQ_API_KEY:", repr(os.environ.get("GROQ_API_KEY")))
print("TELEGRAM_TOKEN:", repr(os.environ.get("TELEGRAM_TOKEN")))
print("========================")

if not os.environ.get("TELEGRAM_TOKEN"):
    print("❌ TELEGRAM_TOKEN НЕ ЗАГРУЖЕН!")
else:
    print("✅ TELEGRAM_TOKEN загружен")
