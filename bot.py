import os
import sqlite3
import random
import google.generativeai as genai

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= AI =================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    vip INTEGER DEFAULT 0
)
""")
conn.commit()


def get_user(uid):
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users(user_id) VALUES(?)", (uid,))
        conn.commit()


def add_balance(uid, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()


def set_vip(uid):
    c.execute("UPDATE users SET vip=1 WHERE user_id=?", (uid,))
    conn.commit()


def is_vip(uid):
    c.execute("SELECT vip FROM users WHERE user_id=?", (uid,))
    return c.fetchone()[0] == 1


# ================= UI =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 AI Chat", callback_data="ai")],
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("💎 VIP", callback_data="vip")],
        [InlineKeyboardButton("🔗 Invite", callback_data="invite")],
    ])


# ================= COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)

    await update.message.reply_text(
        "سلام 👋 به ربات خوش اومدی",
        reply_markup=menu()
    )


# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    get_user(uid)

    if q.data == "ai":
        context.user_data["ai"] = True
        await q.message.reply_text("💬 حالا پیام بفرست برای AI")

    elif q.data == "wallet":
        c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = c.fetchone()[0]
        await q.message.reply_text(f"💰 موجودی شما: {bal}")

    elif q.data == "vip":
        set_vip(uid)
        await q.message.reply_text("💎 VIP فعال شد!")

    elif q.data == "invite":
        await q.message.reply_text(
            "🔗 لینک دعوت:\nhttps://t.me/your_bot"
        )


# ================= AI CHAT =================
def ask_ai(text):
    try:
        return model.generate_content(text).text
    except:
        return "❌ خطا در AI"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)

    if context.user_data.get("ai"):
        if not is_vip(uid):
            await update.message.reply_text("❌ فقط VIP می‌تواند استفاده کند")
            return

        reply = ask_ai(update.message.text)
        await update.message.reply_text(reply)
        return

    # ================= GAME =================
    reward = random.uniform(0.001, 0.01)
    if is_vip(uid):
        reward *= 2

    add_balance(uid, reward)
    await update.message.reply_text(f"🎮 +{reward:.4f} تومان اضافه شد")


# ================= RUN =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
