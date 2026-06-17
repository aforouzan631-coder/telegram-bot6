import os
import sqlite3
import random
from datetime import datetime, date, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import google.generativeai as genai

# ================= AI =================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

BOT_TOKEN = os.getenv("BOT_TOKEN")
LIMIT = 40

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
accepted INTEGER DEFAULT 0,
daily_msg INTEGER DEFAULT 0,
last_reset TEXT,
vip_until TEXT,
balance REAL DEFAULT 0,
free_msgs INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= RULES =================
RULES = """📜 قوانین:
✔ استفاده درست
✔ اسپم ممنوع
✔ برای ادامه باید قبول کنید"""

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 AI", callback_data="ai")],
        [InlineKeyboardButton("⛏ ماین", callback_data="mine")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton("💎 VIP", callback_data="vip")],
        [InlineKeyboardButton("🤝 دعوت", callback_data="invite")]
    ])

def rules_btn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✔ قبول", callback_data="accept"),
         InlineKeyboardButton("❌ رد", callback_data="deny")]
    ])

# ================= VIP =================
def is_vip(uid):
    c.execute("SELECT vip_until FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    if not r or not r[0]:
        return False
    return datetime.fromisoformat(r[0]) > datetime.now()

def set_vip(uid):
    vip_time = datetime.now() + timedelta(days=30)
    c.execute("UPDATE users SET vip_until=? WHERE user_id=?", (vip_time.isoformat(), uid))
    conn.commit()

# ================= LIMIT =================
def can_use(uid):
    c.execute("SELECT daily_msg FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    used = r[0] if r else 0

    if is_vip(uid):
        return True

    if used >= LIMIT:
        return False

    c.execute("UPDATE users SET daily_msg = daily_msg + 1 WHERE user_id=?", (uid,))
    conn.commit()
    return True

# ================= AI =================
def ask_ai(text):
    try:
        res = model.generate_content(text)
        return res.text
    except Exception as e:
        return f"AI ERROR: {e}"

# ================= MINE GAME =================
def mine(uid):
    reward = random.uniform(0.0001, 0.01)
    if is_vip(uid):
        reward *= 2

    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, uid))
    conn.commit()
    return reward

# ================= START =================
async def start(update: Update, context):
    uid = update.effective_user.id
    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
    conn.commit()

    await update.message.reply_text(RULES, reply_markup=rules_btn())

# ================= RULES =================
async def rules(update: Update, context):
    q = update.callback_query
    uid = q.from_user.id

    if q.data == "deny":
        await q.message.reply_text("⛔ دسترسی بسته شد")
        return

    c.execute("UPDATE users SET accepted=1 WHERE user_id=?", (uid,))
    conn.commit()

    await q.message.edit_text("✔ خوش آمدی", reply_markup=menu())

# ================= BUTTONS =================
async def buttons(update: Update, context):
    q = update.callback_query
    uid = q.from_user.id
    d = q.data

    if d == "ai":
        context.user_data["ai"] = True
        await q.message.reply_text("💬 پیام بده")
        return

    if d == "mine":
        r = mine(uid)
        await q.message.reply_text(f"⛏ درآمد: {r:.5f}")
        return

    if d == "wallet":
        c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = c.fetchone()[0]
        await q.message.reply_text(f"💰 موجودی: {bal:.5f}")
        return

    if d == "vip":
        set_vip(uid)
        await q.message.reply_text("💎 VIP فعال شد")
        return

    if d == "invite":
        link = f"https://t.me/YOUR_BOT_USERNAME?start={uid}"
        await q.message.reply_text(link)
        return

# ================= CHAT =================
async def handle(update: Update, context):
    uid = update.effective_user.id

    if context.user_data.get("ai"):
        if not can_use(uid):
            await update.message.reply_text("❌ محدودیت 40 پیام")
            return

        ans = ask_ai(update.message.text)
        await update.message.reply_text(ans)

# ================= RUN =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(rules, pattern="accept|deny"))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
