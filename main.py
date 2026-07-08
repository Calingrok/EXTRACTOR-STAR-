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
        """Clean URL by removing spaces"""
        if not url:
            return ""
        return url.replace(" ", "%")

    async def get_all_batches(self):
        """Get all active batches without login"""
        courses_url = "https://backend.multistreaming.site/api/courses/active?userId=1448640"
        
        courses_headers = {
            "host": "backend.multistreaming.site",
            **self.base_headers
        }
        
        try:
            session = requests.Session()
            response = session.get(courses_url, headers=courses_headers)
            response.raise_for_status()
            
            courses_response = response.json()
            if courses_response.get("state") == 200:
                return True, courses_response["data"]
            else:
                return False, "Failed to get batches"
                
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def get_my_batches(self, user_id):
        """Get user's own batches after login"""
        if user_id not in self.user_sessions:
            return False, "Please login first"
        
        user_data = self.user_sessions[user_id]
        courses_url = "https://backend.multistreaming.site/api/courses/my-courses"
        
        courses_headers = {
            "host": "backend.multistreaming.site",
            "content-length": "20",
            **self.base_headers
        }
        
        courses_data = {
            "userId": str(user_data['user_id'])
        }
        
        try:
            response = user_data['session'].post(courses_url, headers=courses_headers, json=courses_data)
            response.raise_for_status()
            
            courses_response = response.json()
            if courses_response.get("state") == "200":
                return True, courses_response["data"]
            else:
                return False, "Failed to get your courses"
                
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def login_user(self, email, password, user_id):
        """Login to SelectionWay"""
        login_url = "https://selectionway.hranker.com/admin/api/user-login"
        
        login_headers = {
            "host": "selectionway.hranker.com",
            "content-length": "106",
            **self.base_headers
        }
        
        login_data = {
            "email": email,
            "password": password,
            "mobile": "",
            "otp": "",
            "logged_in_via": "web",
            "customer_id": 561
        }
        
        try:
            session = requests.Session()
            response = session.post(login_url, headers=login_headers, json=login_data)
            response.raise_for_status()
            
            login_response = response.json()
            if login_response.get("state") == 200:
                user_data = {
                    'user_id': login_response["data"]["user_id"],
                    'token': login_response["data"]["token_id"],
                    'session': session
                }
                self.user_sessions[user_id] = user_data
                return True, "✅ Login successful!"
            else:
                return False, "❌ Login failed: Invalid credentials"
                
        except Exception as e:
            return False, f"❌ Login error: {str(e)}"

    async def extract_course_data_without_login(self, course_id, course_name):
        """Extract course data without login"""
        try:
            # Get course classes directly without login
            classes_url = f"https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"
            classes_headers = {
                "host": "backend.multistreaming.site",
                **self.base_headers
            }
            
            session = requests.Session()
            response = session.get(classes_url, headers=classes_headers)
            response.raise_for_status()
            
            classes_response = response.json()
            if classes_response.get("state") == 200:
                # Get course details from active batches to find PDF URL
                all_batches_success, all_batches = await self.get_all_batches()
                pdf_url = ""
                
                if all_batches_success:
                    for batch in all_batches:
                        if batch.get('id') == course_id:
                            pdf_url = self.clean_url(batch.get('batchInfoPdfUrl', ""))
                            break
                
                return True, {
                    "classes_data": classes_response["data"],
                    "pdf_url": pdf_url,
                    "course_details": {"title": course_name}
                }
            else:
                return False, "Failed to get course data"
                
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def extract_course_data_with_login(self, user_id, course_id, course_name):
        """Extract course data with login"""
        if user_id not in bot.user_sessions:
            return False, "Please login first!"
        
        user_data = self.user_sessions[user_id]
        
        # Get course details first
        course_url = "https://backend.multistreaming.site/api/courses/by-id-2"
        course_headers = {
            "host": "backend.multistreaming.site",
            "content-length": "52",
            **self.base_headers
        }
        
        course_data = {
            "userId": str(user_data['user_id']),
            "id": course_id
        }
        
        try:
            # Get course details
            response = user_data['session'].post(course_url, headers=course_headers, json=course_data)
            course_response = response.json()
            
            if course_response.get("state") != 200:
                return False, "Failed to get course details"
            
            course_details = course_response["data"]
            pdf_url = self.clean_url(course_details.get("batchInfoPdfUrl", ""))
            
            # Get course classes
            classes_url = f"https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"
            classes_headers = {
                "host": "backend.multistreaming.site",
                **self.base_headers
            }
            
            response = user_data['session'].get(classes_url, headers=classes_headers)
            response.raise_for_status()
            
            classes_response = response.json()
            if classes_response.get("state") == 200:
                return True, {
                    "classes_data": classes_response["data"],
                    "pdf_url": pdf_url,
                    "course_details": course_details
                }
            else:
                return False, "Failed to get course data"
                
        except Exception as e:
            return False, f"Error: {str(e)}"

    def format_batches_list(self, courses_data, list_type="all"):
        """Format batches list for display"""
        if not courses_data:
            return "No batches found!", []
        
        if list_type == "all":
            message = "📚 *All Available Batches*\n\n"
        else:
            message = "📚 *Your Batches*\n\n"
        
        batch_list = []
        
        # Extract all batches from response
        if list_type == "all":
            # For all batches, courses_data is direct list
            for course in courses_data:
                batch_list.append(course)
        else:
            # For my batches, courses_data has nested structure
            for course_group in courses_data:
                live_courses = course_group.get("liveCourses", [])
                recorded_courses = course_group.get("recordedCourses", [])
                
                for course in live_courses + recorded_courses:
                    batch_list.append(course)
        
        if not batch_list:
            return "❌ No batches found!", []
        
        for i, course in enumerate(batch_list, 1):
            title = course.get('title', 'Unknown')
            course_id = course.get('id', 'N/A')
            price = course.get('discountPrice', course.get('price', 'N/A'))
            category = course.get('mainCategory', {}).get('mainCategoryName', 'General')
            course_type = "🔴 LIVE" if course.get('isLive') else "📹 RECORDED"
            
            message += f"*{i}. {title}*\n"
            message += f"   🆔 `{course_id}`\n"
            message += f"   📁 {category}\n"
            message += f"   💰 ₹{price} | {course_type}\n"
            message += f"   📖 {course.get('short_description', 'No description')}\n\n"
        
        if list_type == "my":
            message += "👉 Reply with batch number to extract (e.g., `1`)"
        else:
            message += "👉 Reply with *batch ID* to extract (e.g., `68ce5fe8bb3c8f24bb3d4f77`)"
        
        return message, batch_list

    def extract_all_data(self, classes_data, pdf_url, course_details):
        """Extract all data from course"""
        video_links = []
        pdf_links = []
        
        # Add main PDF if available
        if pdf_url:
            pdf_links.append(f"Batch Info PDF : {pdf_url}")
        
        # Extract video links
        if classes_data and "classes" in classes_data:
            for topic_group in classes_data["classes"]:
                for class_item in topic_group.get("classes", []):
                    title = class_item.get("title", "Unknown Title")
                    mp4_recordings = class_item.get("mp4Recordings", [])
                    
                    # Find best quality
                    best_url = None
                    best_quality = ""
                    
                    for recording in mp4_recordings:
                        quality = recording.get("quality", "")
                        url = recording.get("url", "")
                        
                        if quality == "720p":
                            best_url = url
                            best_quality = "720p"
                            break
                        elif quality == "480p" and not best_url:
                            best_url = url
                            best_quality = "480p"
                        elif quality == "360p" and not best_url:
                            best_url = url
                            best_quality = "360p"
                    
                    if not best_url:
                        best_url = class_item.get("class_link", "")
                        best_quality = "YouTube"
                    
                    if best_url:
                        video_links.append(f"{title}({best_quality}) : {best_url}")
        
        return video_links, pdf_links

    def create_course_file(self, course_name, video_links, pdf_links):
        """Create course file with modern format"""
        # Clean filename from special characters
        clean_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{clean_name.replace(' ', '_')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"🎯 {course_name}\n\n")
            
            # Write PDF links
            if pdf_links:
                f.write("📄 PDF FILES:\n")
                for pdf in pdf_links:
                    f.write(f"{pdf}\n")
                f.write("\n")
            
            # Write video links
            if video_links:
                f.write("🎥 VIDEO LINKS:\n")
                for video in video_links:
                    f.write(f"{video}\n")
        
        return filename

# Create bot instance
bot = SelectionWayBot()

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with buttons"""
    keyboard = [
        [InlineKeyboardButton("🔐 Login & Extract", callback_data="login_extract")],
        [InlineKeyboardButton("📚 List All Batches", callback_data="list_batches")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *SelectionWay Extractor Bot*\n\n"
        "Choose an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "login_extract":
        context.user_data['awaiting_login'] = True
        context.user_data['action_type'] = 'login_extract'
        await query.edit_message_text(
            "🔐 *Login Required*\n\n"
            "Please send your login credentials in this format:\n"
            "`email:password`\n\n"
            "Example:\n"
            "`9007111119:Ty28@`",
            parse_mode='Markdown'
        )
    
    elif query.data == "list_batches":
        await query.edit_message_text("🔄 Loading all batches...")
        
        success, result = await bot.get_all_batches()
        if success:
            batches_list, batch_list = bot.format_batches_list(result, "all")
            # Store all batches in context
            context.user_data['all_batches'] = batch_list
            context.user_data['awaiting_batch_id'] = True
            context.user_data['action_type'] = 'all_batches'
            
            await query.edit_message_text(batches_list, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if context.user_data.get('awaiting_login'):
        # Handle login credentials
        if ":" in text:
            email, password = text.split(":", 1)
            email = email.strip()
            password = password.strip()
            
            await update.message.reply_text("🔄 Logging in...")
            
            success, message = await bot.login_user(email, password, user_id)
            if success:
                context.user_data['awaiting_login'] = False
                
                # Get USER'S OWN batches after login
                await update.message.reply_text("🔄 Loading your batches...")
                success, my_batches = await bot.get_my_batches(user_id)
                
                if success:
                    formatted_list, batch_list = bot.format_batches_list(my_batches, "my")
                    # Store user's batches in context
                    context.user_data['my_batches'] = batch_list
                    context.user_data['awaiting_batch_selection'] = True
                    
                    await update.message.reply_text(
                        formatted_list,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(f"✅ Login successful but {my_batches}")
            else:
                await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "❌ Invalid format! Please use:\n`email:password`",
                parse_mode='Markdown'
            )
    
    elif context.user_data.get('awaiting_batch_selection'):
        # Handle batch number selection (with login)
        if text.isdigit():
            batch_number = int(text)
            batch_list = context.user_data.get('my_batches', [])
            
            if 1 <= batch_number <= len(batch_list):
                selected_batch = batch_list[batch_number - 1]
                course_id = selected_batch.get('id')
                course_name = selected_batch.get('title', 'Course')
                
                await update.message.reply_text(f"🔄 Extracting *{course_name}*...", parse_mode='Markdown')
                
                success, result = await bot.extract_course_data_with_login(user_id, course_id, course_name)
                
                if success:
                    await process_extraction_result(update, course_name, result)
                    # Reset selection state
                    context.user_data['awaiting_batch_selection'] = False
                else:
                    await update.message.reply_text(f"❌ {result}")
            else:
                await update.message.reply_text(f"❌ Please enter a number between 1 and {len(batch_list)}")
        else:
            await update.message.reply_text("❌ Please enter a valid number")
    
    elif context.user_data.get('awaiting_batch_id'):
        # Handle batch ID input (without login - from all batches)
        batch_id = text.strip()
        
        # Find batch name from stored batches
        batch_list = context.user_data.get('all_batches', [])
        course_name = "Unknown Course"
        
        for batch in batch_list:
            if batch.get('id') == batch_id:
                course_name = batch.get('title', 'Unknown Course')
                break
        
        await update.message.reply_text(f"🔄 Extracting *{course_name}*...", parse_mode='Markdown')
        
        success, result = await bot.extract_course_data_without_login(batch_id, course_name)
        
        if success:
            await process_extraction_result(update, course_name, result)
            # Reset selection state
            context.user_data['awaiting_batch_id'] = False
        else:
            await update.message.reply_text(f"❌ {result}")
    
    elif text.startswith('/'):
        await update.message.reply_text("Please use /start to begin")

async def process_extraction_result(update, course_name, result):
    """Process extraction result and send file"""
    video_links, pdf_links = bot.extract_all_data(
        result["classes_data"], 
        result["pdf_url"], 
        result["course_details"]
    )
    
    # Create file
    filename = bot.create_course_file(course_name, video_links, pdf_links)
    
    # Modern caption
    total_videos = len(video_links)
    total_pdfs = len(pdf_links)
    
    caption = (
        f"🎯 *{course_name}*\n\n"
        f"📊 *Extraction Complete!*\n"
        f"• 🎥 Total Videos: {total_videos}\n"
        f"• 📄 Total PDFs: {total_pdfs}\n"
        f"• 📦 File: `{filename}`\n\n"
        f"✅ *All links are ready to use!*"
    )
    
    # Send file to user
    with open(filename, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename=filename,
            caption=caption,
            parse_mode='Markdown'
        )

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(login_extract|list_batches)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    print("🤖 Bot is running...")
    application.run_polling()

import asyncio

async def main():
    # Flask को बैकग्राउंड में शुरू रखें
    keep_alive()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run polling
    print("🤖 Bot is running...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # यह Flask को भी चलने देगा और बोट को भी
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
