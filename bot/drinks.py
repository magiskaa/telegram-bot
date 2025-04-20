import time
from bot.save_and_load import save_profiles, user_profiles
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

SIZE, PERCENTAGE = range(2)

async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    await update.message.reply_text("Minkä kokoinen juoma?")
    return SIZE

async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        size = float(update.message.text)
        if size <= 0:
            raise ValueError("Koko ei voi olla nolla tai negatiivinen.")
        context.user_data["size"] = size
        await update.message.reply_text("Kuinka monta prosenttia juomassa on alkoholia?")
        return PERCENTAGE
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita juomasi tilavuus litroina. (esim. 0.33)")
        return SIZE

async def get_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percentage = float(update.message.text)
        if percentage <= 0 or percentage > 100:
            raise ValueError("Prosentti ei voi olla negatiivinen tai yli sata.")
        context.user_data["percentage"] = percentage
        user_id = str(update.message.from_user.id)
        servings = calculate_alcohol(context.user_data["size"], context.user_data["percentage"])
        user_profiles[user_id]["drink_count"] += servings
        if user_profiles[user_id]["start_time"] == 0:
            user_profiles[user_id]["start_time"] = time.time()
        user_profiles[user_id]["elapsed_time"] = time.time() - user_profiles[user_id]["start_time"]
        save_profiles()
        await update.message.reply_text(f"Lisätty {servings} annosta.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita prosentti desimaalilukuna. (esim. 4.2)")
        return PERCENTAGE

def calculate_alcohol(vol, perc):
    pure_alcohol = vol * (perc / 100) * 789
    servings = pure_alcohol / 12
    return round(servings, 2)

def reset_drink_stats():
    for user_id in user_profiles:
        user_profiles[user_id]["drink_count"] = 0
        user_profiles[user_id]["start_time"] = 0
        user_profiles[user_id]["elapsed_time"] = 0
    save_profiles()

