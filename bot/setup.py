from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.save_and_load import save_profiles, user_profiles

GENDER, AGE, HEIGHT, WEIGHT, UPDATE_AGE, UPDATE_GENDER, UPDATE_HEIGHT, UPDATE_WEIGHT, FAVORITE_SETUP = range(9)

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mikä on sukupuolesi? (mies/nainen)")
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ["mies", "nainen"]:
        await update.message.reply_text("Virheellinen syöte. Kirjoita joko 'mies' tai 'nainen'.")
        return GENDER
    context.user_data["gender"] = gender
    await update.message.reply_text("Mikä on ikäsi?")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 0:
            raise ValueError("Ikä ei voi olla negatiivinen.")
        context.user_data["age"] = age
        await update.message.reply_text("Mikä on pituutesi senttimetreinä?")
        return HEIGHT
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita ikä numeroina.")
        return AGE
    
async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = int(update.message.text)
        if height < 0:
            raise ValueError("Pituus ei voi olla negatiivinen.")
        context.user_data["height"] = height
        await update.message.reply_text("Mikä on painosi kiloina?")
        return WEIGHT
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita pituus numeroina.")
        return HEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = int(update.message.text)
        if weight < 0:
            raise ValueError("Paino ei voi olla negatiivinen.")
        user_id = str(update.message.from_user.id)
        user_profiles[user_id] = {
            "name": update.message.from_user.first_name,
            "gender": context.user_data["gender"],
            "age": context.user_data["age"],
            "height": context.user_data["height"],
            "weight": weight,
            "drink_count": 0,
            "start_time": 0,
            "elapsed_time": 0,
            "BAC": 0,
            "highest_drink_count": 0,
            "highest_BAC": 0,
            "favorite_drink_size": "ei määritetty",
            "favorite_drink_percentage": "ei määritetty",
            "favorite_drink_name": "ei määritetty",
            "BAC_1_7": 0,
            "BAC_2_0": 0,
            "BAC_2_3": 0,
            "BAC_2_7": 0
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
    elif data == "edit_favorite":
        await query.message.reply_text("Kirjoita uusi lempijuomasi koko, prosentit ja nimi (esim. 0.33 4.2 kupari):")
        return FAVORITE_SETUP


