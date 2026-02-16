import os
import telebot
import google.generativeai as genai
import time
import requests
import io
from PIL import Image
from flask import Flask, request

# ========================================
# 🔑 НАСТРОЙКИ - токены берутся из Environment Variables
# ========================================

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')  # Автоматически на Render

# ========================================
# 🎨 ПЕРСОНАЛИЗАЦИЯ (можно менять)
# ========================================

DEFAULT_PERSONALITY = {
    "name": "AI Ассистент",
    "role": "Я умный помощник, который отвечает на вопросы, анализирует изображения и помогает с задачами.",
    "style": "дружелюбный и полезный",
    "language": "русский"
}

# ========================================
# ⚙️ ИНИЦИАЛИЗАЦИЯ
# ========================================

app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
genai.configure(api_key=GOOGLE_API_KEY)

text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

active_chats = {}
bot_personalities = {}
user_settings = {}

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
    personality = bot_personalities.get(chat_id, DEFAULT_PERSONALITY)
    return f"""Ты - {personality['name']}. 
{personality['role']}
Твой стиль общения: {personality['style']}.
Отвечай на языке: {personality['language']}."""

def create_chat_with_personality(chat_id):
    personality_prompt = get_personality_prompt(chat_id)
    chat = text_model.start_chat(history=[])
    chat.send_message(f"[SYSTEM] {personality_prompt}")
    return chat

# ========================================
# 🌐 FLASK ROUTES (для webhook)
# ========================================

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>AI Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .status { font-size: 2em; margin: 20px; }
        </style>
    </head>
    <body>
        <h1>🤖 AI Bot is Running!</h1>
        <div class="status">✅ Status: ACTIVE</div>
        <p>🔗 Webhook Mode ON</p>
        <p>💚 Google Gemini Connected</p>
    </body>
    </html>
    """

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    """Обработка входящих сообщений от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/health')
def health():
    return {'status': 'ok', 'mode': 'webhook'}, 200

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

💡 Попробуй отправить фото или просто задай вопрос!
        """
    else:
        welcome_text = f"""
🤖 Привет! Я добавлен в группу!

Упоминай меня: @{bot.get_me().username} <вопрос>

⚙️ Админы могут настроить через /personality

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
    
    bot.send_message(chat_id, "🎭 Выбери личность для бота:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('personality_'))
def personality_callback(call):
    chat_id = call.message.chat.id
    personality_key = call.data.replace('personality_', '')
    
    if personality_key == 'custom':
        user_settings[call.from_user.id] = {'waiting_for': 'custom_personality'}
        bot.edit_message_text(
            "✏️ Опиши желаемую личность бота.\n\n"
            "Например:\n"
            "• Ты программист, который помогает с кодом\n"
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
    personality = bot_personalities.get(message.chat.id, DEFAULT_PERSONALITY)
    status_text = f"""
📊 **Текущая конфигурация:**

🎭 Личность: {personality['name']}
📝 Роль: {personality['role']}
💬 Стиль: {personality['style']}
🌐 Язык: {personality.get('language', 'русский')}

Измени через /personality
    """
    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['generate'])
def generate_image(message):
    chat_id = message.chat.id
    prompt = message.text.replace('/generate', '').strip()
    
    if not prompt:
        bot.send_message(chat_id, "❌ Укажи описание!\n\nПример: /generate красивый закат")
        return
    
    bot.send_chat_action(chat_id, 'upload_photo')
    
    try:
        status_msg = bot.send_message(chat_id, "🎨 Генерирую изображение...")
        
        if chat_id not in active_chats:
            active_chats[chat_id] = create_chat_with_personality(chat_id)
        
        translation = active_chats[chat_id].send_message(
            f"Переведи на английский кратко для генерации изображения: {prompt}"
        )
        english_prompt = translation.text.strip()
        
        image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(english_prompt)}?width=1024&height=1024&nologo=true"
        
        bot.delete_message(chat_id, status_msg.message_id)
        bot.send_photo(
            chat_id,
            image_url,
            caption=f"🎨 **{prompt}**\n🌐 EN: {english_prompt}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['clear'])
def clear_chat(message):
    active_chats[message.chat.id] = create_chat_with_personality(message.chat.id)
    bot.send_message(message.chat.id, "🗑️ История очищена!")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📖 **Руководство:**

**💬 Общение**
Просто пиши - я отвечу!

**🖼️ Изображения**
📷 Отправь фото → я опишу
🎨 /generate <описание> → создам картинку

**📁 Файлы**
Отправь .txt, .py, .js → я прочитаю

**🎭 Личность**
/personality → выбери стиль

**👥 В группах**
Упомяни @botname

**Команды:**
/start - Меню
/personality - Настройка
/generate - Генерация
/status - Конфигурация
/clear - Очистить
/help - Помощь

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
            
            if chat_id not in active_chats:
                active_chats[chat_id] = create_chat_with_personality(chat_id)
            
            response = active_chats[chat_id].send_message(prompt)
            bot.send_message(chat_id, f"📁 **{file_name}:**\n\n{response.text}", parse_mode='Markdown')
        else:
            bot.send_message(chat_id, f"❌ Формат .{file_extension} не поддерживается.\n\nПоддерживаются: .txt, .md, .py, .js, .json")
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

# ========================================
# 💬 ОБРАБОТКА ТЕКСТА
# ========================================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    user_text = message.text
    
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
            bot.send_message(chat_id, f"✅ Кастомная личность установлена!\n\n📝 {user_text}")
            return
    
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
        bot.send_message(chat_id, response.text)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

# ========================================
# 🚀 ЗАПУСК
# ========================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI-БОТ ЗАПУЩЕН (WEBHOOK MODE)")
    print("=" * 60)
    
    # Удаляем старый webhook
    bot.remove_webhook()
    time.sleep(1)
    
    # Устанавливаем новый webhook
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    bot.set_webhook(url=webhook_url)
    
    print(f"✅ Webhook: {webhook_url}")
    print("✅ Google Gemini: подключен")
    print("✅ Бот готов!")
    print("=" * 60)
    
    # Запускаем Flask на порту 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)