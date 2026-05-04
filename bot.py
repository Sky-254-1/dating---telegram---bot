import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import os

TOKEN = os.getenv("token")

logging.basicConfig(level=logging.INFO)

# --- DATABASE SETUP ---
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    age TEXT,
    bio TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS likes (
    liker INTEGER,
    liked INTEGER
)
""")

conn.commit()


# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💘 Welcome to LoveMatch!\n\n"
        "Use /profile to create your profile.\n"
        "Use /find to discover people."
    )


# --- CREATE PROFILE ---
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send your profile like this:\n\nName, Age, Bio"
    )


async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    try:
        name, age, bio = text.split(",", 2)

        cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, name, age, bio)
        VALUES (?, ?, ?, ?)
        """, (user_id, name.strip(), age.strip(), bio.strip()))

        conn.commit()

        await update.message.reply_text("✅ Profile saved!")
    except:
        await update.message.reply_text("❌ Format: Name, Age, Bio")


# --- FIND MATCH ---
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("SELECT * FROM users WHERE user_id != ?", (user_id,))
    users = cursor.fetchall()

    if not users:
        await update.message.reply_text("No users available 😢")
        return

    # pick first user (can randomize later)
    user = users[0]
    target_id, name, age, bio = user

    keyboard = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{target_id}"),
            InlineKeyboardButton("❌ Skip", callback_data="skip"),
        ]
    ]

    await update.message.reply_text(
        f"👤 {name}, {age}\n\n{bio}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# --- HANDLE BUTTONS ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("like_"):
        liked_id = int(data.split("_")[1])

        # save like
        cursor.execute(
            "INSERT INTO likes (liker, liked) VALUES (?, ?)",
            (user_id, liked_id),
        )
        conn.commit()

        # check match
        cursor.execute(
            "SELECT * FROM likes WHERE liker=? AND liked=?",
            (liked_id, user_id),
        )
        match = cursor.fetchone()

        if match:
            await query.edit_message_text("🎉 IT'S A MATCH! ❤️")
        else:
            await query.edit_message_text("❤️ Liked!")

    else:
        await query.edit_message_text("❌ Skipped")


# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_profile))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
