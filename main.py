from flask import Flask
from threading import Thread
import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Flask App for keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found. Set it in Koyeb Environment Variables.")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SelectionWayBot:
    def __init__(self):
        self.base_headers = {
            "sec-ch-ua-platform": "\"Windows\"",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
            "content-type": "application/json",
            "sec-ch-ua-mobile": "?0",
            "accept": "*/*",
            "origin": "https://www.selectionway.com",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.selectionway.com/",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=1, i"
        }
        self.user_sessions = {}

    def clean_url(self, url):
        if not url: return ""
        return url.replace(" ", "%")

    async def get_all_batches(self):
        courses_url = "https://backend.multistreaming.site/api/courses/active?userId=1448640"
        courses_headers = {"host": "backend.multistreaming.site", **self.base_headers}
        try:
            session = requests.Session()
            response = session.get(courses_url, headers=courses_headers)
            response.raise_for_status()
            courses_response = response.json()
            if courses_response.get("state") == 200: return True, courses_response["data"]
            return False, "Failed to get batches"
        except Exception as e: return False, f"Error: {str(e)}"

    async def get_my_batches(self, user_id):
        if user_id not in self.user_sessions: return False, "Please login first"
        user_data = self.user_sessions[user_id]
        courses_url = "https://backend.multistreaming.site/api/courses/my-courses"
        courses_headers = {"host": "backend.multistreaming.site", **self.base_headers}
        courses_data = {"userId": str(user_data['user_id'])}
        try:
            response = user_data['session'].post(courses_url, headers=courses_headers, json=courses_data)
            response.raise_for_status()
            courses_response = response.json()
            if courses_response.get("state") == "200": return True, courses_response["data"]
            return False, "Failed to get your courses"
        except Exception as e: return False, f"Error: {str(e)}"

    async def login_user(self, email, password, user_id):
        login_url = "https://selectionway.hranker.com/admin/api/user-login"
        login_headers = {"host": "selectionway.hranker.com", **self.base_headers}
        login_data = {"email": email, "password": password, "mobile": "", "otp": "", "logged_in_via": "web", "customer_id": 561}
        try:
            session = requests.Session()
            response = session.post(login_url, headers=login_headers, json=login_data)
            response.raise_for_status()
            login_response = response.json()
            if login_response.get("state") == 200:
                user_data = {'user_id': login_response["data"]["user_id"], 'token': login_response["data"]["token_id"], 'session': session}
                self.user_sessions[user_id] = user_data
                return True, "✅ Login successful!"
            return False, "❌ Login failed: Invalid credentials"
        except Exception as e: return False, f"❌ Login error: {str(e)}"

    async def extract_course_data_without_login(self, course_id, course_name):
        try:
            classes_url = f"https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"
            classes_headers = {"host": "backend.multistreaming.site", **self.base_headers}
            session = requests.Session()
            response = session.get(classes_url, headers=classes_headers)
            response.raise_for_status()
            classes_response = response.json()
            if classes_response.get("state") == 200:
                all_batches_success, all_batches = await self.get_all_batches()
                pdf_url = ""
                if all_batches_success:
                    for batch in all_batches:
                        if batch.get('id') == course_id:
                            pdf_url = self.clean_url(batch.get('batchInfoPdfUrl', ""))
                            break
                return True, {"classes_data": classes_response["data"], "pdf_url": pdf_url, "course_details": {"title": course_name}}
            return False, "Failed to get course data"
        except Exception as e: return False, f"Error: {str(e)}"

    async def extract_course_data_with_login(self, user_id, course_id, course_name):
        if user_id not in self.user_sessions: return False, "Please login first!"
        user_data = self.user_sessions[user_id]
        course_url = "https://backend.multistreaming.site/api/courses/by-id-2"
        course_headers = {"host": "backend.multistreaming.site", **self.base_headers}
        course_data = {"userId": str(user_data['user_id']), "id": course_id}
        try:
            response = user_data['session'].post(course_url, headers=course_headers, json=course_data)
            course_response = response.json()
            if course_response.get("state") != 200: return False, "Failed to get course details"
            course_details = course_response["data"]
            pdf_url = self.clean_url(course_details.get("batchInfoPdfUrl", ""))
            classes_url = f"https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"
            classes_headers = {"host": "backend.multistreaming.site", **self.base_headers}
            response = user_data['session'].get(classes_url, headers=classes_headers)
            response.raise_for_status()
            classes_response = response.json()
            if classes_response.get("state") == 200:
                return True, {"classes_data": classes_response["data"], "pdf_url": pdf_url, "course_details": course_details}
            return False, "Failed to get course data"
        except Exception as e: return False, f"Error: {str(e)}"

    def format_batches_list(self, courses_data, list_type="all"):
        if not courses_data: return "No batches found!", []
        message = "📚 *All Available Batches*\n\n" if list_type == "all" else "📚 *Your Batches*\n\n"
        batch_list = []
        if list_type == "all": batch_list = courses_data
        else:
            for group in courses_data:
                batch_list.extend(group.get("liveCourses", []) + group.get("recordedCourses", []))
        if not batch_list: return "❌ No batches found!", []
        for i, course in enumerate(batch_list, 1):
            title, price, c_type = course.get('title', 'Unknown'), course.get('discountPrice', 'N/A'), "🔴 LIVE" if course.get('isLive') else "📹 RECORDED"
            message += f"*{i}. {title}* | 💰 ₹{price} | {c_type}\n   🆔 `{course.get('id', 'N/A')}`\n\n"
        message += "👉 Reply with batch number or ID to extract."
        return message, batch_list

    def extract_all_data(self, classes_data, pdf_url, course_details):
        video_links, pdf_links = [], []
        if pdf_url: pdf_links.append(f"Batch Info PDF : {pdf_url}")
        if classes_data and "classes" in classes_data:
            for topic_group in classes_data["classes"]:
                for class_item in topic_group.get("classes", []):
                    title = class_item.get("title", "Unknown")
                    best_url = next((r.get("url") for r in class_item.get("mp4Recordings", []) if r.get("quality") == "720p"), None) or class_item.get("class_link")
                    if best_url: video_links.append(f"{title} : {best_url}")
        return video_links, pdf_links

    def create_course_file(self, course_name, video_links, pdf_links):
        filename = f"{''.join(c for c in course_name if c.isalnum()).replace(' ', '_')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"🎯 {course_name}\n\n📄 PDF:\n" + "\n".join(pdf_links) + "\n\n🎥 VIDEO:\n" + "\n".join(video_links))
        return filename

bot = SelectionWayBot()

async def start(update, context):
    keyboard = [[InlineKeyboardButton("🔐 Login", callback_data="login_extract")], [InlineKeyboardButton("📚 Batches", callback_data="list_batches")]]
    await update.message.reply_text("🤖 *SelectionWay Extractor*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "login_extract":
        context.user_data.update({'awaiting_login': True})
        await query.edit_message_text("Send credentials as `email:password`", parse_mode='Markdown')
    elif query.data == "list_batches":
        await query.edit_message_text("🔄 Loading...")
        success, result = await bot.get_all_batches()
        if success:
            msg, b_list = bot.format_batches_list(result, "all")
            context.user_data.update({'all_batches': b_list, 'awaiting_batch_id': True})
            await query.edit_message_text(msg, parse_mode='Markdown')

async def handle_message(update, context):
    text = update.message.text
    if context.user_data.get('awaiting_batch_selection'):
        # Handle batch selection logic...
        pass # (Add your existing batch selection logic here)
    elif context.user_data.get('awaiting_batch_id'):
        # Handle ID logic
        pass # (Add your logic here)
    elif context.user_data.get('awaiting_login'):
        # Handle login logic
        pass # (Add your logic here)

def main():
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
