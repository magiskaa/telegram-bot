import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, CallbackQueryHandler, filters
from config.config import BOT_TOKEN

GENDER, AGE, HEIGHT, WEIGHT = range(4)
UPDATE_GENDER, UPDATE_AGE, UPDATE_HEIGHT, UPDATE_WEIGHT = range(4, 8)

PROFILE_FILE = "config/user_profiles.json"

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_profiles():
    with open(PROFILE_FILE, "w") as f:
        json.dump(user_profiles, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heipat! Lasken veren alkoholipitoisuutesi🍻. Aloita kirjoittamalla /setup.")

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mikä on sukupuolesi? (mies/nainen)")
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ["mies", "nainen"]:
        await update.message.reply_text("Virheellinen syöte. Kirjoita joko 'mies' tai 'nainen'.")
        return GENDER
    context.user_data["gender"] = gender
    await update.message.reply_text("Kuinka vanha olet?")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 0:
            raise ValueError("Ikä ei voi olla negatiivinen.")
        context.user_data["age"] = age
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita ikä numeroina.")
        return AGE
    await update.message.reply_text("Kuinka pitkä olet senttimetreinä?")
    return HEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = int(update.message.text)
        if height < 0:
            raise ValueError("Pituus ei voi olla negatiivinen.")
        context.user_data["height"] = height
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita pituus numeroina.")
        return HEIGHT
    await update.message.reply_text("Kuinka paljon painat kiloina?")
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = int(update.message.text)
        if weight < 0:
            raise ValueError("Paino ei voi olla negatiivinen.")
        user_id = str(update.message.from_user.id)
        user_profiles[user_id] = {
            "gender": context.user_data["gender"],
            "age": context.user_data["age"],
            "height": context.user_data["height"],
            "weight": weight
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

async def update_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 0:
            raise ValueError("Ikä ei voi olla negatiivinen.")
        user_profiles[str(update.message.from_user.id)]["age"] = age
        save_profiles()
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita ikä numeroina.")
        return UPDATE_AGE
    await update.message.reply_text("Ikä päivitetty!")
    return ConversationHandler.END

async def update_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = int(update.message.text)
        if height < 0:
            raise ValueError("Pituus ei voi olla negatiivinen.")
        user_profiles[str(update.message.from_user.id)]["height"] = height
        save_profiles()
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita pituus numeroina.")
        return UPDATE_HEIGHT
    await update.message.reply_text("Pituus päivitetty!")
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

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles.get(user_id)
    if not profile:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return
    
    profile_text = (
        f"Sukupuoli: {profile["gender"]}\n"
        f"Ikä: {profile["age"]}\n"
        f"Pituus: {profile["height"]} cm\n"
        f"Paino: {profile["weight"]} kg\n"
    )

    keyboard = [
        [InlineKeyboardButton("Muokkaa sukupuolta", callback_data="edit_gender")],
        [InlineKeyboardButton("Muokkaa ikää", callback_data="edit_age")],
        [InlineKeyboardButton("Muokkaa pituutta", callback_data="edit_height")],
        [InlineKeyboardButton("Muokkaa painoa", callback_data="edit_weight")]
    ]

    await update.message.reply_text(
        profile_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "edit_gender":
        await query.message.reply_text("Kirjoita uusi sukupuolesi (mies/nainen):")
        return UPDATE_GENDER
    elif data == "edit_age":
        await query.message.reply_text("Kirjoita uusi ikä:")
        return UPDATE_AGE
    elif data == "edit_height":
        await query.message.reply_text("Kirjoita uusi pituus senttimetreinä:")
        return UPDATE_HEIGHT
    elif data == "edit_weight":
        await query.message.reply_text("Kirjoita uusi paino kiloina:")
        return UPDATE_WEIGHT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Peruutettu.")
    return ConversationHandler.END

async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kuinka monta annosta alkoholia olet nauttinut?")

user_profiles = load_profiles()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("setup", setup), CallbackQueryHandler(button_handler)],
    states={
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
        HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
        UPDATE_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_gender)],
        UPDATE_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_age)],
        UPDATE_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_height)],
        UPDATE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_weight)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
app.add_handler(CommandHandler("profile", profile))
app.add_handler(conv_handler)

app.add_handler(CommandHandler("drink", drink))

app.run_polling()
