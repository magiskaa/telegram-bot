import random
import math
import openai
import telegram
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.save_and_load import save_profiles, user_profiles
from config.config import GROUP_ID, ADMIN_ID, OPENAI_API, ANNOUNCEMENT_TEXT

ANNOUNCEMENT, ANSWER = range(2)
announcement_text = ""
saved_announcement = ""

# Admin commands
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Sinulla ei ole oikeuksia tähän komentoon.")
        return
    
    await update.message.reply_text(
        "Admin komennot:\n\n"
        "/group_id\n\n"
        "/reset_top3\n\n"
        "/announcement\n\n"
        "/saved_announcement"
    )

async def group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Sinulla ei ole oikeuksia tähän komentoon.")
        return
    
    group_id = update.effective_chat.id
    with open("data/group_id.txt", "w") as f:
        f.write(str(group_id))

async def reset_top_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Sinulla ei ole oikeuksia tähän komentoon.")
        return
    
    user_profiles["top_3"]["1"] = {
        "name": "ei kukaan",
        "BAC": 0,
        "drinks": 0,
        "day": "ei milloinkaan"
    }
    user_profiles["top_3"]["2"] = {
        "name": "ei kukaan",
        "BAC": 0,
        "drinks": 0,
        "day": "ei milloinkaan"
    }
    user_profiles["top_3"]["3"] = {
        "name": "ei kukaan",
        "BAC": 0,
        "drinks": 0,
        "day": "ei milloinkaan"
    }
    save_profiles()
    await update.message.reply_text("Top 3 resetattu.")

async def announcement_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Sinulla ei ole oikeuksia tähän komentoon.")
        return
    
    await update.message.reply_text("Kirjoita ilmoitus, jonka haluat lähettää ryhmään.")
    return ANNOUNCEMENT

async def announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global announcement_text
    openai.api_key = OPENAI_API
    announcement_details = update.message.text
    model = "gpt-4.1-mini"
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": ANNOUNCEMENT_TEXT + f"Tarkemmat tiedot tulevat tässä: {announcement_details}"}
        ],
    )
    announcement_text = response.choices[0].message.content
    await update.message.reply_text(announcement_text)

    await update.message.reply_text("Haluatko lähettää tämän ryhmään vai laittaa säästöön? (k/e/s)")
    return ANSWER
    
async def send_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global announcement_text, saved_announcement
    answer = update.message.text
    if answer.lower() == "k":
        await context.bot.send_message(chat_id=GROUP_ID, text=announcement_text)
        await update.message.reply_text("Ilmoitus lähetetty ryhmään.")
        return ConversationHandler.END
    elif answer.lower() == "e":
        await update.message.reply_text("Ilmoitus peruutettu.")
        return ConversationHandler.END
    elif answer.lower() == "s":
        saved_announcement = announcement_text
        await update.message.reply_text("Ilmoitus tallennettu. Voit lähettää sen myöhemmin.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Virheellinen syöte. Ilmoitus peruutettu.")
        return ConversationHandler.END

async def send_saved_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global saved_announcement
    if saved_announcement:
        await context.bot.send_message(chat_id=GROUP_ID, text=saved_announcement)
        await update.message.reply_text("Tallennettu tiedote lähetetty ryhmään.")
    else:
        await update.message.reply_text("Ei tallennettuja tiedotteita.")



