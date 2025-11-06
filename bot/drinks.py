import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bot.save_and_load import save_profiles, user_profiles
from bot.utils import *
from bot.calculations import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

DRINK = 1
FORGOTTEN_DRINK, FORGOTTEN_TIME = range(2)
TARGET_BAC = 1

COMMON_DRINKS = [
    ("🍺Olut 0.33l, 4.2%", 0.33, 4.2),
    ("🍺Olut 0.5l, 8.0%", 0.5, 8.0),
    ("🐙Lonkero 0.33l, 5.5%", 0.33, 5.5),
    ("🐙Lonkero 0.5l, 5.5%", 0.5, 5.5),
    ("🍐Siideri 0.33l, 4.7%", 0.33, 4.7),
    ("🫧Seltzer 0.33l, 4.5%", 0.33, 4.5),
    ("🍷Viini 0.16l, 12%", 0.12, 13),
    ("🥃Viina 0.04l, 40%", 0.04, 40)
]

# Targetbac command
async def target_bac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END
    
    await update.message.reply_text("Mikä on tavoitepromillesi ja aika jolloin haluat saavuttaa kyseisen kännin? (esim. 1.5 3 -> 1.5 promillea 3 tunnin päästä)")
    return TARGET_BAC

async def get_target_bac_and_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        text = update.message.text.strip().replace(",", ".")
        parts = text.split()

        if len(parts) < 2:
            raise ValueError("Syötä vähintään kaksi lukua (esim. 1.5 3).")

        target_bac = float(parts[0])
        target_time = float(parts[1])

        if target_bac <= 0:
            raise ValueError("Tavoite-BAC täytyy olla positiivinen.")
        if target_bac > 3:
            raise ValueError("Ethän suunnittele yli 3 promillen känniä🥺.")
        if target_time <= 0 or target_time > 12:
            raise ValueError("Ajan täytyy olla positiivinen ja alle 12 tuntia.")

        servings_needed = calculate_target_bac_servings(user_id, target_bac, target_time)

        beer_servings = calculate_alcohol(0.33, 4.2)
        long_drink_servings = calculate_alcohol(0.5, 5.5)
        cider_servings = calculate_alcohol(0.33, 4.7)
        wine_servings = calculate_alcohol(0.16, 12)
        kossu_servings = calculate_alcohol(0.04, 38)

        beer_count = servings_needed / beer_servings
        long_drink_count = servings_needed / long_drink_servings
        cider_count = servings_needed / cider_servings
        wine_count = servings_needed / wine_servings
        kossu_count = servings_needed / kossu_servings

        await update.message.reply_text(
            "📈 Kännitavoite\n"
            "===========================\n"
            f"Tavoiteesi on {target_bac:.3f}‰ {target_time}h päästä.\n"
            "Tarvittava määrä kutakin juomaa tavoitekännin saavuttamiseen:\n"
            f"  • ≈ {beer_count:.2f} x 🍺0.33l, 4.2%\n"
            f"  • ≈ {long_drink_count:.2f} x 🐙0.5l, 5.5%\n"
            f"  • ≈ {cider_count:.2f} x 🍐0.33l, 4.7%\n"
            f"  • ≈ {wine_count:.2f} x 🍷0.16l, 12.0%\n"
            f"  • ≈ {kossu_count:.2f} x 🥃0.04l, 38.0%\n"
        )
        return ConversationHandler.END

    except ValueError as e:
        if "Ethän suunnittele" in str(e):
            await update.message.reply_text(f"{e}")
        else:
            await update.message.reply_text(f"⚠️Virheellinen syöte: {e}")
        return TARGET_BAC

# Drink command
async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END
    
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    favorites = profile["favorites"]

    buttons = [InlineKeyboardButton(drink[0], callback_data=f"drink_{i}") for i, drink in enumerate(COMMON_DRINKS)]
    favorite_buttons = [InlineKeyboardButton(f"😍{favorite['name']} {favorite['size']}l, {favorite['percentage']}%", callback_data=f"drink_{i+100}") for i, favorite in enumerate(favorites) if favorite["name"] != "ei määritetty"]
    buttons.extend(favorite_buttons)
    buttons.append(InlineKeyboardButton("🤷Muu", callback_data=f"drink_{len(COMMON_DRINKS)}"))
    buttons.append(InlineKeyboardButton("❌Peruuta", callback_data="drink_cancel"))
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Valitse juoma:",
        reply_markup=reply_markup
    )

async def drink_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "drink_cancel":
        await query.edit_message_text("Peruutettu.")
        return ConversationHandler.END
    if data.startswith("drink_"):
        index = int(data.split("_")[1])
        if index < 0:
            await query.edit_message_text("Virheellinen valinta.")
            return ConversationHandler.END
        elif index == len(COMMON_DRINKS):
            await query.edit_message_text("Kirjoita juoman koko ja prosentit: (esim. 0.33 4.2 tai 0,5 8,0)")
            return DRINK
        else:
            await select_drink(update, context)
    else:
        await query.edit_message_text("Virheellinen valinta.")
        return ConversationHandler.END

async def select_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("drink_"):
        await query.message.reply_text("Virheellinen valinta.")
        return
    
    user_id = str(query.from_user.id)
    profile = user_profiles[user_id]
    
    index = int(data.split("_")[1])
    if index >= 100:
        index -= 100
        size = profile["favorites"][index]["size"]
        percentage = profile["favorites"][index]["percentage"]
    else:
        name, size, percentage = COMMON_DRINKS[index]
    
    servings = calculate_alcohol(size, percentage)
    profile["drink_count"] += servings

    current_time = get_timezone()
    time_adj = time_adjustment(size)

    profile["drink_history"].append({
        "size": size,
        "percentage": percentage,
        "servings": servings,
        "timestamp": current_time - time_adj
    })
    save_profiles()

    if profile["BAC"] == 0 and profile["start_time"] != 0:
        profile["second_start"] = current_time - time_adj

    if profile["start_time"] == 0:
        profile["start_time"] = current_time - time_adj

    await calculate_bac(update, context, user_id)

    await query.edit_message_text(
        f"🍺Lisätty {servings} annosta.\nBAC: *{profile['BAC']:.3f}‰*",
        parse_mode="Markdown"
    )
    return ConversationHandler.END
    
async def get_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        drink = update.message.text.strip().replace(",", ".")
        size, percentage = map(float, drink.split())
        if size <= 0:
            raise ValueError("Koko ei voi olla 0 tai negatiivinen.")
        elif percentage <= 0 or percentage > 100:
            raise ValueError("Prosentit ei voi olla 0, negatiivinen tai yli 100.")

        user_id = str(update.message.from_user.id)
        profile = user_profiles[user_id]

        servings = calculate_alcohol(size, percentage)

        if servings > 4:
            raise ValueError("Tosson aika paljon viinaa. Ettet kai vaan ole syöttänyt juoman tietoja väärin?")

        profile["drink_count"] += servings

        current_time = get_timezone()
        time_adj = time_adjustment(size)

        profile["drink_history"].append({
            "size": size,
            "percentage": percentage,
            "servings": servings,
            "timestamp": current_time - time_adj
        })
        save_profiles()

        if profile["BAC"] == 0 and profile["start_time"] != 0:
            profile["second_start"] = current_time - time_adj

        if profile["start_time"] == 0:
            profile["start_time"] = current_time - time_adj

        await calculate_bac(update, context, user_id)
        
        await update.message.reply_text(f"🍺Lisätty {servings} annosta.\nBAC: *{profile['BAC']:.3f}‰*", parse_mode="Markdown")
        
        return ConversationHandler.END
    except ValueError as e:
        if "Koko ei" in str(e) or "Prosentit ei" in str(e):
            await update.message.reply_text(f"⚠️Virheellinen syöte. {e} Kirjoita juoman koko ja prosentit uudestaan:")
        elif "Tosson aika" in str(e):
            await update.message.reply_text(f"⚠️{e} Kirjoita juoman koko ja prosentit uudestaan:")
        else:
            await update.message.reply_text("⚠️Virheellinen syöte. Kirjoita juoman koko ja prosentit uudestaan:")
        return DRINK

# Favorite command
async def favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END
    
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    first = profile["favorites"][0]
    second = profile["favorites"][1]
    third = profile["favorites"][2]
    fourth = profile["favorites"][3]
       
    buttons = [
        InlineKeyboardButton(f"1. {first['name']}", callback_data="favorite_1"),
        InlineKeyboardButton(f"2. {second['name']}", callback_data="favorite_2"),
        InlineKeyboardButton(f"3. {third['name']}", callback_data="favorite_3"),
        InlineKeyboardButton(f"4. {fourth['name']}", callback_data="favorite_4"),
        InlineKeyboardButton("❌Peruuta", callback_data="favorite_cancel")
    ]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"😍{name_conjugation(profile['name'], 'n')} suosikkijuomat\n"
        "===========================\n"
        f"1. {first['name']} {first['size']}l, {first['percentage']}%\n"
        f"2. {second['name']} {second['size']}l, {second['percentage']}%\n"
        f"3. {third['name']} {third['size']}l, {third['percentage']}%\n"
        f"4. {fourth['name']} {fourth['size']}l, {fourth['percentage']}%",
        reply_markup=reply_markup
    )

async def favorite_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "favorite_cancel":
        await query.edit_message_text("Peruutettu.")
        return ConversationHandler.END
    elif data.startswith("favorite_"):
        index = int(data.split("_")[1]) - 1
        user_id = str(query.from_user.id)
        profile = user_profiles[user_id]

        drink = profile["favorites"][index]
        size = drink["size"]
        percentage = drink["percentage"]

        if drink["name"] == "ei määritetty":
            await query.edit_message_text("Juomaa ei ole määritetty.")
            return ConversationHandler.END
        
        servings = calculate_alcohol(size, percentage)
        profile["drink_count"] += servings
        
        current_time = get_timezone()
        time_adj = time_adjustment(size)

        profile["drink_history"].append({
            "size": size,
            "percentage": percentage,
            "servings": servings,
            "timestamp": current_time - time_adj
        })
        save_profiles()

        if profile["BAC"] == 0 and profile["start_time"] != 0:
            profile["second_start"] = current_time - time_adj

        if profile["start_time"] == 0:
            profile["start_time"] = current_time - time_adj

        await calculate_bac(update, context, user_id)

        await query.edit_message_text(
            f"😋{drink['name']} +1 ({servings} annosta).\n"
            f"BAC: *{profile['BAC']:.3f}‰*",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    else:
        await query.edit_message_text("Virheellinen valinta.")
        return ConversationHandler.END

# Forgotten drink command
async def forgotten_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END

    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    favorites = profile["favorites"]

    buttons = [InlineKeyboardButton(drink[0], callback_data=f"forgotten_{i}") for i, drink in enumerate(COMMON_DRINKS)]
    favorite_buttons = [InlineKeyboardButton(f"😍{favorite['name']} {favorite['size']}l, {favorite['percentage']}%", callback_data=f"forgotten_{i+100}") for i, favorite in enumerate(favorites) if favorite["name"] != "ei määritetty"]
    buttons.extend(favorite_buttons)
    buttons.append(InlineKeyboardButton("🤷Muu", callback_data=f"forgotten_{len(COMMON_DRINKS)}"))
    buttons.append(InlineKeyboardButton("❌Peruuta", callback_data="forgotten_cancel"))
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Valitse unohtunut juoma:",
        reply_markup=reply_markup
    )

async def forgotten_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "forgotten_cancel":
        await query.edit_message_text("Peruutettu.")
        return ConversationHandler.END
    if data.startswith("forgotten_"):
        index = int(data.split("_")[1])
        if index < 0:
            await query.edit_message_text("Virheellinen valinta.")
            return ConversationHandler.END
        elif index == len(COMMON_DRINKS):
            await query.edit_message_text("Kirjoita unohtuneen juoman koko ja prosentit: (esim. 0.33 4.2 tai 0,5 8,0)")
            return FORGOTTEN_DRINK
        elif index >= 100:
            index -= 100
            user_id = str(query.from_user.id)
            profile = user_profiles[user_id]
            context.user_data["forgotten_size"] = profile["favorites"][index]["size"]
            context.user_data["forgotten_percentage"] = profile["favorites"][index]["percentage"]
            await query.edit_message_text("Mihin aikaan aloitit juoman? (kirjoita aika muodossa HH:MM tai HH.MM)")
            return FORGOTTEN_TIME
        else:
            name, size, percentage = COMMON_DRINKS[index]
            context.user_data["forgotten_size"] = size
            context.user_data["forgotten_percentage"] = percentage
            await query.edit_message_text("Mihin aikaan aloitit juoman? (kirjoita aika muodossa HH:MM tai HH.MM)")
            return FORGOTTEN_TIME
    else:
        await query.edit_message_text("Virheellinen valinta.")
        return ConversationHandler.END

async def get_forgotten_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        forgotten = update.message.text.strip().replace(",", ".")
        forgotten_size, forgotten_percentage = forgotten.split()
        
        size = float(forgotten_size)
        percentage = float(forgotten_percentage)

        if size <= 0:
            raise ValueError("Koko ei voi olla nolla tai negatiivinen.")
        elif percentage > 100 or percentage <= 0:
            raise ValueError("Prosentti ei voi olla negatiivinen, 0 tai yli 100.")

        context.user_data["forgotten_size"] = size
        context.user_data["forgotten_percentage"] = percentage

        if calculate_alcohol(size, percentage) > 4:
            raise ValueError("Tosson aika paljon viinaa. Ettet kai vaan ole syöttänyt juoman tietoja väärin?")

        await update.message.reply_text("Mihin aikaan aloitit juoman? (kirjoita aika muodossa HH:MM tai HH.MM)")
        return FORGOTTEN_TIME
    except ValueError as e:
        if "Koko ei" in str(e) or "Prosentti ei" in str(e):
            await update.message.reply_text(f"⚠️Virheellinen syöte. {e} Kirjoita unohtuneen juoman koko ja prosentit uudestaan:")
        elif "Tosson aika" in str(e):
            await update.message.reply_text(f"⚠️{e} Kirjoita unohtuneen juoman koko ja prosentit uudestaan:")
        else:
            await update.message.reply_text("⚠️Virheellinen syöte. Kirjoita unohtuneen juoman koko ja prosentit uudestaan:")
        return FORGOTTEN_DRINK

async def get_forgotten_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    forgotten_time = update.message.text.strip().replace(".", ":")
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", forgotten_time):
        await update.message.reply_text("Virheellinen aika. Kirjoita aika muodossa HH:MM tai HH.MM.")
        return FORGOTTEN_TIME

    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]

    servings = calculate_alcohol(context.user_data["forgotten_size"], context.user_data["forgotten_percentage"])
    profile["drink_count"] += servings

    now = datetime.now(ZoneInfo("Europe/Helsinki"))
    drink_time = datetime.strptime(forgotten_time, "%H:%M").time()
    drink_datetime = datetime.combine(now.date(), drink_time, tzinfo=ZoneInfo("Europe/Helsinki"))
    if drink_datetime > now:
        drink_datetime -= timedelta(days=1)
    timestamp = drink_datetime.timestamp()

    profile["drink_history"].append({
        "size": context.user_data["forgotten_size"],
        "percentage": context.user_data["forgotten_percentage"],
        "servings": servings,
        "timestamp": timestamp
    })

    if profile["BAC"] == 0 and profile["start_time"] != 0:
        profile["second_start"] = timestamp

    if profile["start_time"] == 0:
        profile["start_time"] = timestamp
    elif timestamp < profile["start_time"]:
        profile["start_time"] = timestamp

    profile["drink_history"] = sorted(profile["drink_history"], key=lambda x: x["timestamp"])

    save_profiles()

    await calculate_bac(update, context, user_id)

    await update.message.reply_text(
        f"🤔Lisätty unohtunut juoma: {context.user_data['forgotten_size']}l "
        f"{context.user_data['forgotten_percentage']}% ({servings} annosta).\n"
        f"Juomasi aloitusaika: {forgotten_time}.\n"
        f"Arvioitu BAC: *{profile['BAC']:.3f}‰*",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Delete last drink command
async def delete_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END

    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if len(profile["drink_history"]) == 0:
        await update.message.reply_text("Ei juomia poistettavaksi.")
        return

    drinks = await drink_history(update, context, isDelete=True)

    buttons = [InlineKeyboardButton(f"{i+1}. {str(drink['size'])}l, {str(drink['percentage'])}%", callback_data=f"delete_{i}") for i, drink in enumerate(profile["drink_history"])]
    buttons.append(InlineKeyboardButton("❌Peruuta", callback_data="delete_cancel"))
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        drinks,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def delete_drink_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "delete_cancel":
        await query.edit_message_text("Poisto peruutettu.")
        return ConversationHandler.END
    elif data.startswith("delete_"):
        index = int(data.split("_")[1])
        user_id = str(query.from_user.id)
        profile = user_profiles[user_id]

        if index < 0 or index >= len(profile["drink_history"]):
            await query.edit_message_text("Virheellinen valinta.")
            return ConversationHandler.END

        drink = profile["drink_history"][index]
        servings = drink["servings"]

        profile["drink_history"].pop(index)

        if len(profile["drink_history"]) == 0:
            profile["drink_count"] = 0
            profile["start_time"] = 0
            profile["elapsed_time"] = 0
            profile["BAC"] = 0
            profile["highest_BAC"] = 0
            save_profiles()
            await query.edit_message_text("Juomahistoria tyhjennetty.")
            return ConversationHandler.END
        else:
            if index == 0:
                profile["start_time"] = profile["drink_history"][0]["timestamp"]
            
            profile["drink_count"] -= servings
            recalculate_highest_bac(user_id, drink)
            await calculate_bac(update, context, user_id)
            await query.edit_message_text(
                f"⏏️Poistettu juoma:\n{index+1}. *{drink['size']}l* *{drink['percentage']}%* ({servings} annosta).\n"
                f"Juoman lopetus: {datetime.fromtimestamp(drink['timestamp'], tz=ZoneInfo('Europe/Helsinki')).strftime('%H:%M:%S')}\n",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

# Drink history command
async def drink_history(update: Update, context: ContextTypes.DEFAULT_TYPE, isDelete=False):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END

    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if len(profile["drink_history"]) == 0:
        await update.message.reply_text("Ei juomahistoriaa.")
        return

    history_text = (
        f"🍻{name_conjugation(profile['name'], 'n')} juomahistoria\n"
        "==========================\n"
    )
    for i, drink in enumerate(profile["drink_history"], 1):
        time_adj = time_adjustment(drink["size"])
        history_text += (
            f"{i}. *{drink['size']}l*, *{drink['percentage']}%* ({drink['servings']} annosta)\n"
            f"Juoman lopetus: {datetime.fromtimestamp(drink['timestamp'] + time_adj, tz=ZoneInfo('Europe/Helsinki')).strftime('%H:%M:%S')}\n\n"
        )

    if isDelete:
        return history_text
    else:
        await update.message.reply_text(history_text, parse_mode="Markdown")

# Latest drink command
async def add_latest_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_profile(update, context)
    if result:
        return ConversationHandler.END
    
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if len(profile["drink_history"]) == 0:
        await update.message.reply_text("Ei juomahistoriaa.")
        return

    drink = profile["drink_history"][-1]
    size = drink["size"]
    time_adj = time_adjustment(size)
    current_time = get_timezone()

    latest_drink = {
        "size": drink["size"],
        "percentage": drink["percentage"],
        "servings": drink["servings"],
        "timestamp": current_time - time_adj
    }

    profile["drink_history"].append(latest_drink)
    profile["drink_count"] += latest_drink["servings"]

    if profile["BAC"] == 0 and profile["start_time"] != 0:
        profile["second_start"] = current_time - time_adj

    save_profiles()

    await calculate_bac(update, context, user_id)

    await update.message.reply_text(
        f"⏮️Viimeisin juoma lisätty ({latest_drink['servings']} annosta).\n"
        f"BAC: *{profile['BAC']:.3f}‰*",
        parse_mode="Markdown"
    )