import telebot
import pyotp
import requests
import time
import random
from datetime import datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
BOT_TOKEN = '8783194900:AAH__MsqIgqwKn_-Pzg2NdxQsIJ1OjvAVY8'
ADMIN_ID = 8783194900 # আপনার অ্যাডমিন আইডি
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# ডাইনামিক সেটিংস
settings = {
    "fb_task_status": True,
    "ig_old_status": True,
    "submit_link": "https://submitwork.org",
    "save_sheet_url": "YOUR_SAVE_SHEET_URL",
    "otp_api_key": "YOUR_DONGVANFB_API_KEY"
}

user_tasks = {} # {user_id: {'start_time': t, 'otp_taken': False}}
cooldowns = {} # ৩ মিনিটের ব্লক

# --- পাসওয়ার্ড লজিক (৭ অক্ষর + তারিখ) ---
def get_custom_pass():
    names = ["Tanjimz", "Saidurz", "Rifatxx", "Siampro", "Mimlove", "Rohanzx", "Anikpro"]
    name = random.choice(names)
    day = datetime.now().strftime("%d")
    return f"{name}{day}"

# --- ওটিপি ও ২এফএ ফাংশন ---
def fetch_hotmail_otp(email, key, uuid):
    # dongvanfb API লজিক
    url = f"https://dongvanfb.net/get_code_mail?mail={email}&key={key}&uuid={uuid}"
    try:
        r = requests.get(url).json()
        return r.get('code', 'কোড পাওয়া যায়নি')
    except:
        return "API Error"

# --- মেইন মেনু ---
@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📋 কাজ', '🏆 লিডারবোর্ড', '💰 ব্যালেন্স')
    bot.send_message(message.chat.id, "👋 স্বাগতম বস! কাজ শুরু করতে মেনু সিলেক্ট করুন।", reply_markup=markup)

# --- ফেসবুক টাস্ক লজিক ---
@bot.message_handler(func=lambda m: m.text == '📋 কাজ')
def work_menu(message):
    markup = types.InlineKeyboardMarkup()
    if settings["fb_task_status"]:
        markup.add(types.InlineKeyboardButton("🔥 FB 30Frnd + Hotmail (৳১০)", callback_data="fb_start"))
    if settings["ig_old_status"]:
        markup.add(types.InlineKeyboardButton("🍪 IG Cookies Old", callback_data="ig_old_start"))
    bot.send_message(message.chat.id, "👇 আপনার টাস্ক বেছে নিন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "fb_start")
def fb_task_init(call):
    uid = call.from_user.id
    # ৩ মিনিটের ব্লক চেক
    if uid in cooldowns and time.time() < cooldowns[uid]:
        wait = int((cooldowns[uid] - time.time()) / 60)
        bot.answer_callback_query(call.id, f"⚠️ ওটিপি নিয়েছেন! {wait+1} মিনিট পর নতুন কাজ পাবেন।", show_alert=True)
        return

    passw = get_custom_pass()
    user_tasks[uid] = {'start_time': time.time(), 'otp_taken': False}
    
    msg = f"👤 **User:** fb_user_{random.randint(100,999)}\n🔑 **Pass:** {passw}\n📧 **Mail:** Loading from Sheet..."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📩 Get Mail OTP", callback_data="get_otp"))
    markup.add(types.InlineKeyboardButton("🔐 Get 2FA Code", callback_data="get_2fa"))
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "get_otp")
def otp_handler(call):
    uid = call.from_user.id
    # ৩০ মিনিট সাইলেন্ট টাইম-আউট চেক
    if time.time() - user_tasks[uid]['start_time'] > 1800:
        bot.answer_callback_query(call.id, "❌ ৩০ মিনিট শেষ! কাজটি ক্লোজ করা হয়েছে।", show_alert=True)
        return

    bot.answer_callback_query(call.id, "🔄 ওটিপি চেক করা হচ্ছে...")
    user_tasks[uid]['otp_taken'] = True
    cooldowns[uid] = time.time() + 180 # ৩ মিনিটের ব্লক সেট
    bot.send_message(call.message.chat.id, "📩 আপনার ওটিপি: 123456")

# --- ২এফএ ডিকোডার ---
@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa(call):
    msg = bot.send_message(call.message.chat.id, "🔐 আপনার ২এফএ কি (Secret Key) দিন:")
    bot.register_next_step_handler(msg, process_2fa)

def process_2fa(message):
    try:
        totp = pyotp.TOTP(message.text.replace(" ", ""))
        bot.send_message(message.chat.id, f"✅ আপনার লগইন কোড: {totp.now()}")
    except:
        bot.send_message(message.chat.id, "❌ ভুল কি! আবার চেষ্টা করুন।")

# --- অ্যাডমিন প্যানেল ---
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚫 FB Task: ON/OFF", callback_data="toggle_fb"))
        markup.add(types.InlineKeyboardButton("🔗 Edit Submit Link", callback_data="edit_link"))
        bot.send_message(message.chat.id, "👑 অ্যাডমিন কন্ট্রোল প্যানেল", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "toggle_fb")
def toggle_fb(call):
    settings["fb_task_status"] = not settings["fb_task_status"]
    bot.answer_callback_query(call.id, f"FB Task এখন {'চালু' if settings['fb_task_status'] else 'বন্ধ'}")

# --- Render-এ বেঁচে থাকার জন্য Flask (Keep Alive) ---
@app.route('/')
def home(): return "Bot is Alive!"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.polling(none_stop=True)
                     
