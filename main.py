import os
import telebot
import google.generativeai as genai
from keep_alive import keep_alive
import time
import requests
import io
from PIL import Image

# ========================================
# 🔑 НАСТРОЙКИ - ИЗМЕНИ НА СВОЁ!
# ========================================

# ВАРИАНТ 1: Вставь токены прямо сюда (не рекомендуется!)
# TELEGRAM_TOKEN = "8271375613:AAEkkfH2wA50EvFjIAfgrSjJIo3Cd-DoS_s"  # ИЗМЕНИ НА СВОЙ ТОКЕН ОТ @BotFather
# GOOGLE_API_KEY = "AIzaSyAMaGlpRIeiTJvE5a8JmacufpnRT2UfyB0"  # ИЗМЕНИ НА СВОЙ КЛЮЧ ОТ Google

# ВАРИАНТ 2: Через Secrets на Replit (рекомендуется!)
# Tools → Secrets → добавь TELEGRAM_BOT_TOKEN и GOOGLE_API_KEY
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Берёт из Secrets
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')  # Берёт из Secrets

# ========================================
# 🎨 ПЕРСОНАЛИЗАЦИЯ (можно менять)
# ========================================

# Стандартная личность бота
DEFAULT_PERSONALITY = {
    "name": "AI Ассистент",  # ИЗМЕНИ: Имя бота
    "role": "Я умный помощник, который отвечает на вопросы, анализирует изображения и помогает с задачами.",  # ИЗМЕНИ: Роль
    "style": "дружелюбный и полезный",  # ИЗМЕНИ: Стиль общения
    "language": "русский"  # ИЗМЕНИ: Язык (english, spanish и т.д.)
}

# ========================================
# ⚙️ ИНИЦИАЛИЗАЦИЯ (НЕ ТРОГАЙ!)
# ========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)

# Модели
text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# Хранилища
active_chats = {}
bot_personalities = {}
user_settings = {}

# Готовые шаблоны личностей
PERSONALITY_TEMPLATES = {
    "assistant": {
        "name": "Помощник",
        "role": "Я профессиональный ассистент, помогаю с задачами и отвечаю на вопросы.",
        "style": "деловой и точный"
    },
    "friend": {
        "name": "Друг",
        "role": "Я твой веселый друг! Общаюсь непринужденно, шучу и поддерживаю.",
        "style": "дружелюбный и неформальный"
    },
    "expert": {
        "name": "Эксперт",
        "role": "Я эксперт в различных областях. Даю глубокие и детальные ответы.",
        "style": "академический и профессиональный"
    },
    "comedian": {
        "name": "Юморист",
        "role": "Я шутник! Отвечаю с юмором и сарказмом.",
        "style": "веселый и саркастичный"
    },
    "teacher": {
        "name": "Учитель",
        "role": "Я терпеливый учитель. Объясняю сложные вещи простым языком.",
        "style": "образовательный и понятный"
    }
}

# ========================================
# 🛠️ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ========================================

def get_personality_prompt(chat_id):
    """Получить промпт с личностью для чата"""
    personality = bot_personalities.get(chat_id, DEFAULT_PERSONALITY)
    return f"""Ты - {personality['name']}. 
{personality['role']}
Твой стиль общения: {personality['style']}.
Отвечай на языке: {personality['language']}."""

def create_chat_with_personality(chat_id):
    """Создать чат с учетом личности"""
    personality_prompt = get_personality_prompt(chat_id)
    chat = text_model.start_chat(history=[])
    chat.send_message(f"[SYSTEM] {personality_prompt}")
    return chat

# ========================================
# 📝 КОМАНДЫ БОТА
# ========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    
    active_chats[chat_id] = create_chat_with_personality(chat_id)
    
    if chat_type == 'private':
        welcome_text = """
🤖 Привет! Я мультифункциональный AI-бот!

✨ Что я умею:
━━━━━━━━━━━━━━━━━━━━━
💬 **Общение**
   • Отвечаю на вопросы
   • Помню контекст беседы
   
🖼️ **Работа с изображениями**
   • Анализ фото (что на картинке)
   • Генерация изображений по описанию
   
📁 **Обработка файлов**
   • PDF документы
   • Текстовые файлы
   • Код файлы
   
👥 **Работа в группах**
   • Отвечаю на упоминания
   • Настраиваемая личность

━━━━━━━━━━━━━━━━━━━━━
📝 **Команды:**

/start - Это меню
/personality - Настроить личность
/generate <описание> - Создать изображение
/clear - Очистить историю
/help - Подробная помощь
/status - Моя настройка

━━━━━━━━━━━━━━━━━━━━━
🎯 **Попробуй:**
• Отправь фото - я опишу его
• Напиши "/generate космический корабль" 
• Просто задай вопрос

💡 Добавь меня в группу!
        """
    else:
        welcome_text = f"""
🤖 Привет! Я добавлен в группу!

Упомяни меня: @{bot.get_me().username} <вопрос>

⚙️ Админы: /personality - настроить личность

Команды:
/status - Моя роль
/generate - Создать изображение
        """
    
    bot.send_message(chat_id, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['personality'])
def setup_personality(message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    
    if chat_type != 'private':
        try:
            member = bot.get_chat_member(chat_id, message.from_user.id)
            if member.status not in ['creator', 'administrator']:
                bot.send_message(chat_id, "⛔ Только админы могут менять личность!")
                return
        except:
            pass
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    buttons = []
    for key, personality in PERSONALITY_TEMPLATES.items():
        emoji = {"assistant": "💼", "friend": "😊", "expert": "🎓", 
                "comedian": "😄", "teacher": "👨‍🏫"}.get(key, "🤖")
        buttons.append(
            telebot.types.InlineKeyboardButton(
                f"{emoji} {personality['name']}", 
                callback_data=f"personality_{key}"
            )
        )
    
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    
    markup.row(telebot.types.InlineKeyboardButton(
        "✏️ Своя настройка", 
        callback_data="personality_custom"
    ))
    
    bot.send_message(
        chat_id,
        "🎭 Выбери личность для бота:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('personality_'))
def personality_callback(call):
    chat_id = call.message.chat.id
    personality_key = call.data.replace('personality_', '')
    
    if personality_key == 'custom':
        user_settings[call.from_user.id] = {'waiting_for': 'custom_personality'}
        bot.edit_message_text(
            "✏️ Опиши личность бота.\n\n"
            "Например:\n"
            "• Ты программист, помогаешь с кодом\n"
            "• Ты фитнес тренер\n"
            "• Ты психолог\n\n"
            "Отправь описание:",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
    else:
        personality = PERSONALITY_TEMPLATES[personality_key]
        bot_personalities[chat_id] = personality
        active_chats[chat_id] = create_chat_with_personality(chat_id)
        
        bot.edit_message_text(
            f"✅ Личность: **{personality['name']}**\n\n"
            f"📝 {personality['role']}\n"
            f"💬 Стиль: {personality['style']}",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['status'])
def show_status(message):
    chat_id = message.chat.id
    personality = bot_personalities.get(chat_id, DEFAULT_PERSONALITY)
    
    status_text = f"""
📊 **Текущая конфигурация:**

🎭 Личность: {personality['name']}
📝 Роль: {personality['role']}
💬 Стиль: {personality['style']}
🌐 Язык: {personality.get('language', 'русский')}

/personality - изменить
    """
    bot.send_message(chat_id, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['generate'])
def generate_image(message):
    chat_id = message.chat.id
    prompt = message.text.replace('/generate', '').strip()
    
    if not prompt:
        bot.send_message(chat_id, "❌ Укажи описание!\n\nПример: /generate красивый закат")
        return
    
    bot.send_chat_action(chat_id, 'upload_photo')
    
    try:
        status_msg = bot.send_message(chat_id, "🎨 Генерирую...")
        
        # Переводим на английский
        if chat_id not in active_chats:
            active_chats[chat_id] = create_chat_with_personality(chat_id)
        
        translation = active_chats[chat_id].send_message(
            f"Переведи на английский для генерации изображения: {prompt}"
        )
        english_prompt = translation.text.strip()
        
        # Генерируем через бесплатный API
        image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(english_prompt)}?width=1024&height=1024&nologo=true"
        
        bot.delete_message(chat_id, status_msg.message_id)
        bot.send_photo(
            chat_id,
            image_url,
            caption=f"🎨 **{prompt}**\n🌐 {english_prompt}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['clear'])
def clear_chat(message):
    chat_id = message.chat.id
    active_chats[chat_id] = create_chat_with_personality(chat_id)
    bot.send_message(chat_id, "🗑️ История очищена!")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📖 **Руководство:**

━━━━━━━━━━━━━━━━━━━━━
**💬 Общение**
Просто пиши - я отвечу!

**🖼️ Изображения**
📷 Отправь фото → я опишу
🎨 /generate <описание> → создам картинку

**📁 Файлы**
Отправь .txt, .py, .js файл → я прочитаю

**🎭 Личность**
/personality → выбери стиль общения

**👥 В группах**
Упомяни @botname для ответа

━━━━━━━━━━━━━━━━━━━━━
**Команды:**
/start - Меню
/personality - Настройка
/generate - Создать изображение
/status - Моя настройка
/clear - Очистить историю
/help - Эта помощь

🆓 Полностью бесплатно!
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# ========================================
# 🖼️ ОБРАБОТКА ИЗОБРАЖЕНИЙ
# ========================================

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(downloaded_file))
        caption = message.caption or "Что на этом изображении? Опиши подробно."
        
        response = vision_model.generate_content([caption, image])
        
        # ОТПРАВЛЯЕМ БЕЗ REPLY
        bot.send_message(chat_id, f"🖼️ **Анализ:**\n\n{response.text}", parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

# ========================================
# 📁 ОБРАБОТКА ФАЙЛОВ
# ========================================

@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = message.document.file_name
        file_extension = file_name.split('.')[-1].lower()
        
        if file_extension in ['txt', 'md', 'py', 'js', 'json', 'html', 'css']:
            try:
                content = downloaded_file.decode('utf-8')
            except:
                content = downloaded_file.decode('cp1251')
            
            if len(content) > 10000:
                content = content[:10000] + "\n\n[файл обрезан]"
            
            prompt = f"Файл {file_name}:\n\n{content}\n\nОпиши содержание файла."
            
        else:
            bot.send_message(chat_id, f"❌ Формат .{file_extension} не поддерживается.\n\nПоддерживаются: .txt, .md, .py, .js, .json")
            return
        
        if chat_id not in active_chats:
            active_chats[chat_id] = create_chat_with_personality(chat_id)
        
        response = active_chats[chat_id].send_message(prompt)
        
        # ОТПРАВЛЯЕМ БЕЗ REPLY
        bot.send_message(chat_id, f"📁 **{file_name}:**\n\n{response.text}", parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

# ========================================
# 💬 ОБРАБОТКА ТЕКСТА
# ========================================

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    user_text = message.text
    
    # Проверка кастомной настройки
    if message.from_user.id in user_settings:
        if user_settings[message.from_user.id].get('waiting_for') == 'custom_personality':
            bot_personalities[chat_id] = {
                "name": "Кастомная роль",
                "role": user_text,
                "style": "как описано",
                "language": "русский"
            }
            active_chats[chat_id] = create_chat_with_personality(chat_id)
            del user_settings[message.from_user.id]
            
            # ОТПРАВЛЯЕМ БЕЗ REPLY
            bot.send_message(chat_id, f"✅ Кастомная личность установлена!\n\n📝 {user_text}")
            return
    
    # В группах только на упоминания
    if chat_type != 'private':
        bot_username = bot.get_me().username
        if f"@{bot_username}" not in user_text and not message.reply_to_message:
            return
        user_text = user_text.replace(f"@{bot_username}", "").strip()
    
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        if chat_id not in active_chats:
            active_chats[chat_id] = create_chat_with_personality(chat_id)
        
        response = active_chats[chat_id].send_message(user_text)
        
        # ОТПРАВЛЯЕМ БЕЗ REPLY - ПРОСТО КАК ОБЫЧНОЕ СООБЩЕНИЕ
        bot.send_message(chat_id, response.text)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")
        print(f"Error: {e}")

# ========================================
# 🚀 ЗАПУСК БОТА
# ========================================

def main():
    print("=" * 60)
    print("🚀 AI-БОТ ЗАПУЩЕН!")
    print("=" * 60)
    print("✅ Google Gemini подключен")
    print("✅ Telegram Bot готов")
    print("✅ Анализ изображений: ВКЛ")
    print("✅ Генерация изображений: ВКЛ")
    print("✅ Обработка файлов: ВКЛ")
    print("✅ Настройка личности: ВКЛ")
    print("✅ Работа в группах: ВКЛ")
    print("=" * 60)
    
    keep_alive()
    
    while True:
        try:
            print("📡 Получаю сообщения...")
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
            print("♻️ Перезапуск...")

if __name__ == '__main__':
    main()