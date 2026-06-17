import os
import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")

# DB
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

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton("🎮 بازی", callback_data="game")],
        [InlineKeyboardButton("💎 VIP", callback_data="vip")],
    ]
    await update.message.reply_text(
        "👋 سلام به ربات امیر علی فروزان",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- BUTTONS ----------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
    conn.commit()

    if q.data == "wallet":
        c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = c.fetchone()[0]
        await q.message.reply_text(f"💰 موجودی شما: {bal}")

    elif q.data == "game":
        reward = round(random.uniform(0.001, 0.01), 4)

        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, uid))
        conn.commit()

        await q.message.reply_text(f"🎮 بردی: +{reward}")

    elif q.data == "vip":
        c.execute("UPDATE users SET vip = 1 WHERE user_id=?", (uid,))
        conn.commit()

        await q.message.reply_text("💎 VIP فعال شد")

# ---------- RUN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
