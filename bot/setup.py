from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.save_and_load import save_profiles, user_profiles

GENDER, WEIGHT, UPDATE_GENDER, UPDATE_WEIGHT = range(4)

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mikä on sukupuolesi? (mies/nainen)")
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ["mies", "nainen"]:
        await update.message.reply_text("Virheellinen syöte. Kirjoita joko 'mies' tai 'nainen'.")
        return GENDER
    context.user_data["gender"] = gender
    await update.message.reply_text("Kuinka paljon painat kilogrammoina?")
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = int(update.message.text)
        if weight < 0:
            raise ValueError("Paino ei voi olla negatiivinen.")
        user_id = str(update.message.from_user.id)
        user_profiles[user_id] = {
            "gender": context.user_data["gender"],
            "weight": weight,
            "drink_count": 0,
            "start_time": 0,
            "elapsed_time": 0,
            "favorite_drink_size": 0,
            "favorite_drink_percentage": 0,
        }
        save_profiles()
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita paino numeroina.")
        return WEIGHT
    await update.message.reply_text("Valmista! Voit nyt alkaa käyttämään /drink komentoa!")
    return ConversationHandler.END

async def update_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ["mies", "nainen"]:
        await update.message.reply_text("Virheellinen syöte. Kirjoita joko 'mies' tai 'nainen'.")
        return UPDATE_GENDER
    user_profiles[str(update.message.from_user.id)]["gender"] = gender
    save_profiles()
    await update.message.reply_text("Sukupuoli päivitetty!")
    return ConversationHandler.END

async def update_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = int(update.message.text)
        if weight < 0:
            raise ValueError("Paino ei voi olla negatiivinen.")
        user_profiles[str(update.message.from_user.id)]["weight"] = weight
        save_profiles()
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita paino numeroina.")
        return UPDATE_WEIGHT
    await update.message.reply_text("Paino päivitetty!")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "edit_gender":
        await query.message.reply_text("Kirjoita uusi sukupuolesi (mies/nainen):")
        return UPDATE_GENDER
    elif data == "edit_weight":
        await query.message.reply_text("Kirjoita uusi paino kiloina:")
        return UPDATE_WEIGHT


