from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.save_and_load import save_profiles, user_profiles
from bot.utils import validate_profile, name_conjugation

GENDER, AGE, HEIGHT, WEIGHT, UPDATE_AGE, UPDATE_GENDER, UPDATE_HEIGHT, UPDATE_WEIGHT = range(8)
FAVORITE = 1

# Setup command
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
        if age < 18:
            raise ValueError("Et saa käyttää tätä bottia ennen kuin olet 18-vuotias.")
        
        context.user_data["age"] = age

        await update.message.reply_text("Mikä on pituutesi senttimetreinä?")
        return HEIGHT
    except ValueError as e:
        if "Et saa" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Iän pitää olla kokonaisluku.")
        return AGE
    
async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = int(update.message.text)
        if height <= 0:
            raise ValueError("Pituus ei voi olla negatiivinen tai 0.")
        
        context.user_data["height"] = height

        await update.message.reply_text("Mikä on painosi kiloina?")
        return WEIGHT
    except ValueError as e:
        if "Pituus ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Pituuden pitää olla positiivinen kokonaisluku.")
        return HEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = int(update.message.text)
        if weight <= 0:
            raise ValueError("Paino ei voi olla negatiivinen tai 0.")
        
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
            "highest_BAC": 0,
            "favorites": [
            {
                "name": "ei määritetty",
                "size": 0,
                "percentage": 0
            },
            {
                "name": "ei määritetty",
                "size": 0,
                "percentage": 0
            },
            {
                "name": "ei määritetty",
                "size": 0,
                "percentage": 0
            },
            {
                "name": "ei määritetty",
                "size": 0,
                "percentage": 0
            }],
            "BAC_1_7": 0,
            "BAC_2_0": 0,
            "BAC_2_3": 0,
            "BAC_2_7": 0,
            "PB_BAC": 0,
            "PB_dc": 0,
            "PB_day": 0,
            "drink_history": []
        }
        save_profiles()

        await update.message.reply_text("Valmista! Voit nyt alkaa käyttämään /drink komentoa!")
        return ConversationHandler.END
    except ValueError as e:
        if "Paino ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Painon pitää olla positiivinen kokonaisluku.")
        return WEIGHT

# Profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END
    
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]

    profile_text = (
        f"{name_conjugation(profile['name'], 'n')} profiili\n"
        f"=========================\n"
        f"Sukupuoli: {profile['gender']}\n"
        f"Ikä: {profile['age']} vuotta\n"
        f"Pituus: {profile['height']} cm\n"
        f"Paino: {profile['weight']} kg"
    )

    keyboard = [
        [InlineKeyboardButton("♀️♂️Muokkaa sukupuolta", callback_data="edit_gender")],
        [InlineKeyboardButton("🎂🔞Muokkaa ikää", callback_data="edit_age")],
        [InlineKeyboardButton("1️⃣6️⃣0️⃣Muokkaa pituutta", callback_data="edit_height")],
        [InlineKeyboardButton("🏋️⚖️Muokkaa painoa", callback_data="edit_weight")],
        [InlineKeyboardButton("❌Peruuta", callback_data="edit_cancel")],
    ]

    await update.message.reply_text(
        profile_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
        if age < 18:
            raise ValueError("Et saa käyttää tätä bottia ennen kuin olet 18-vuotias.")
        
        user_profiles[str(update.message.from_user.id)]["age"] = age

        save_profiles()

        await update.message.reply_text("Ikä päivitetty!")
        return ConversationHandler.END
    except ValueError as e:
        if "Et saa" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Iän pitää olla positiivinen kokonaisluku.")
        return UPDATE_AGE

async def update_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = int(update.message.text)
        if height <= 0:
            raise ValueError("Pituus ei voi olla negatiivinen tai 0.")
        
        user_profiles[str(update.message.from_user.id)]["height"] = height
        
        save_profiles()

        await update.message.reply_text("Pituus päivitetty!")
        return ConversationHandler.END
    except ValueError as e:
        if "Pituus ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Pituuden pitää olla positiivinen kokonaisluku.")
        return UPDATE_HEIGHT

async def update_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = int(update.message.text)
        if weight <= 0:
            raise ValueError("Paino ei voi olla negatiivinen.")
        
        user_profiles[str(update.message.from_user.id)]["weight"] = weight

        save_profiles()

        await update.message.reply_text("Paino päivitetty!")
        return ConversationHandler.END
    except ValueError as e:
        if "Paino ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Painon pitää olla positiivinen kokonaisluku.")
        return UPDATE_WEIGHT

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
    elif data == "edit_cancel":
        await query.edit_message_text("Peruutettu.")
        return ConversationHandler.END

# Favorite drink setup command
async def favorite_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END
    
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]

    buttons = [
        InlineKeyboardButton("1. Muokkaa", callback_data="modify_1"),
        InlineKeyboardButton("2. Muokkaa", callback_data="modify_2"),
        InlineKeyboardButton("3. Muokkaa", callback_data="modify_3"),
        InlineKeyboardButton("4. Muokkaa", callback_data="modify_4"),
        InlineKeyboardButton("❌Peruuta", callback_data="modify_cancel"),
    ]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    first = profile["favorites"][0]
    second = profile["favorites"][1]
    third = profile["favorites"][2]
    fourth = profile["favorites"][3]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Valitse mitä lempijuomaasi muokkaat:\n"
        f"1. {first['name']} {first['size']}l, {first['percentage']}%\n"
        f"2. {second['name']} {second['size']}l, {second['percentage']}%\n"
        f"3. {third['name']} {third['size']}l, {third['percentage']}%\n"
        f"4. {fourth['name']} {fourth['size']}l, {fourth['percentage']}%",
        reply_markup=reply_markup
    )

async def favorite_drink_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "modify_cancel":
        await query.edit_message_text("Peruutettu.")
        return ConversationHandler.END
    elif data.startswith("modify_"):
        drink_index = int(data.split("_")[1]) - 1
        context.user_data["favorite_drink_index"] = drink_index
        await query.edit_message_text("Kirjoita uusi lempijuomasi koko, prosentit ja nimi (esim. 0.33 4.2 kupari tai 0,5 8,0 karhu):")
        return FAVORITE
    else:
        await query.edit_message_text("Virheellinen valinta.")
        return ConversationHandler.END

async def get_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        favorite = update.message.text.strip().replace(",", ".")
        favorite_size, favorite_percentage, favorite_name = favorite.split()
        favorite_size = float(favorite_size)
        favorite_percentage = float(favorite_percentage)
        favorite_name = favorite_name.capitalize()

        if favorite_size <= 0:
            raise ValueError("Koko ei voi olla nolla tai negatiivinen.")
        elif favorite_percentage > 100 or favorite_percentage <= 0:
            raise ValueError("Prosentti ei voi olla negatiivinen, 0 tai yli 100.")

        user_id = str(update.message.from_user.id)
        profile = user_profiles[user_id]

        drink = profile["favorites"][context.user_data["favorite_drink_index"]]
        drink["name"] = favorite_name
        drink["size"] = favorite_size
        drink["percentage"] = favorite_percentage

        save_profiles()

        await update.message.reply_text(f"{context.user_data['favorite_drink_index'] + 1}. Lempijuomasi on nyt {favorite_name}.")
        return ConversationHandler.END
    except ValueError as e:
        if "Koko ei" in str(e) or "Prosentti ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Kirjoita lempijuomasi koko, prosentit ja nimi (esim. 0.33 4.2 kupari tai 0,5 8,0 karhu):")
        return FAVORITE
