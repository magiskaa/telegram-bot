import time
import re
from bot.save_and_load import save_profiles, user_profiles
from bot.utils import name_conjugation
from bot.calculations import calculate_alcohol, calculate_bac
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

SIZE, PERCENTAGE = range(2)
FORGOTTEN_TIME, FORGOTTEN_DRINK = range(2)

# Drink command
async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    await update.message.reply_text("Minkä kokoinen juoma? Voit vähentää juoman asettamalla koon negatiiviseksi.")
    return SIZE

async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        size = float(update.message.text)
        if size == 0:
            raise ValueError("Koko ei voi olla nolla.")
        
        context.user_data["size"] = size
        await update.message.reply_text("Kuinka monta prosenttia juomassa on alkoholia?")
        return PERCENTAGE
    except ValueError as e:
        if "Koko ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Kirjoita juoman koko numeroina: (esim. 0.33)")
        return SIZE

async def get_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percentage = float(update.message.text)
        if percentage <= 0 or percentage > 100:
            raise ValueError("Prosentti ei voi olla negatiivinen, 0 tai yli sata.")
        
        context.user_data["percentage"] = percentage
        
        user_id = str(update.message.from_user.id)
        profile = user_profiles[user_id]

        servings = calculate_alcohol(context.user_data["size"], context.user_data["percentage"])
        profile["drink_count"] += servings

        if context.user_data["size"] < 0:
            if profile["highest_BAC"] > 0.1:
                profile["highest_BAC"] -= 0.1
            else:
                profile["highest_BAC"] = 0.0 
            for drink in reversed(profile["drink_history"]):
                if drink["size"] == abs(context.user_data["size"]) and drink["percentage"] == context.user_data["percentage"]:
                    profile["drink_history"].remove(drink)
                    if len(profile["drink_history"]) == 0:
                        profile["drink_count"] = 0
                        profile["start_time"] = 0
                        profile["elapsed_time"] = 0
                        profile["BAC"] = 0
                        profile["highest_BAC"] = 0
                        save_profiles()
                        text = (
                            f"Poistettu juoma: {abs(context.user_data['size'])}l {context.user_data['percentage']}% "
                            f"({abs(servings)} annosta)."
                        )
                    else:
                        await calculate_bac(update, context, user_id)
                        text = (
                            f"Poistettu juoma: {abs(context.user_data['size'])}l {context.user_data['percentage']}% "
                            f"({abs(servings)} annosta).\nBAC: {profile['BAC']:.3f}‰"
                        )
                    break
                else:
                    text = "Juomaa ei löytynyt juomahistoriasta."

            await update.message.reply_text(text)
            return ConversationHandler.END

        current_time = time.time()
        size = context.user_data["size"]
        if size <= 0.06:
            time_adjustment = 1 * 60
        elif size <= 0.33:
            time_adjustment = 10 * 60
        elif size <= 0.5:
            time_adjustment = 15 * 60
        else:
            time_adjustment = 20 * 60

        profile["drink_history"].append({
            "size": context.user_data["size"],
            "percentage": context.user_data["percentage"],
            "servings": servings,
            "timestamp": current_time - time_adjustment
        })
        save_profiles()

        if profile["start_time"] == 0:
            profile["start_time"] = current_time - time_adjustment

        await calculate_bac(update, context, user_id)
        
        await update.message.reply_text(f"Lisätty {servings} annosta.\nBAC: {profile['BAC']:.3f}‰")
        
        return ConversationHandler.END
    except ValueError as e:
        if "Prosentti ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Kirjoita juoman prosentti numeroina: (esim. 4.2)")
        return PERCENTAGE
    
# Favorite command
async def favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return
    if user_profiles[user_id]["favorite_drink_size"] == "ei määritetty":
        await update.message.reply_text("Et ole vielä määrittänyt lempijuomaasi. Käytä /favorite_setup komentoa ensin.")
        return

    profile = user_profiles[user_id]
    size = float(profile["favorite_drink_size"])
    percentage = float(profile["favorite_drink_percentage"])
    servings = calculate_alcohol(size, percentage)
    profile["drink_count"] += servings

    current_time = time.time()
    if size <= 0.06:
        time_adjustment = 1 * 60
    elif size <= 0.33:
        time_adjustment = 10 * 60
    elif size <= 0.5:
        time_adjustment = 15 * 60
    else:
        time_adjustment = 20 * 60

    profile["drink_history"].append({
        "size": size,
        "percentage": percentage,
        "servings": servings,
        "timestamp": current_time - time_adjustment
    })
    save_profiles()

    if profile["start_time"] == 0:
        profile["start_time"] = current_time - time_adjustment

    await calculate_bac(update, context, user_id)

    await update.message.reply_text(
        f"{user_profiles[user_id]['favorite_drink_name'].capitalize()} +1 "
        f"({servings} annosta).\nBAC: {profile['BAC']:.3f}‰"
    )

# Forgotten drink command
async def forgotten_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    await update.message.reply_text("Kirjoita unohtuneen juoman koko ja prosentit: (esim. 0.33 4.2)")
    return FORGOTTEN_TIME

async def get_forgotten_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        forgotten = update.message.text
        forgotten_size, forgotten_percentage = forgotten.split()
        
        size = float(forgotten_size)
        percentage = float(forgotten_percentage)

        if size <= 0:
            raise ValueError("Koko ei voi olla nolla tai negatiivinen.")
        elif percentage > 100 or percentage <= 0:
            raise ValueError("Prosentti ei voi olla negatiivinen, 0 tai yli 100.")

        context.user_data["forgotten_size"] = size
        context.user_data["forgotten_percentage"] = percentage

        await update.message.reply_text("Mihin aikaan aloitit juoman? (esim. 20:46)")
        return FORGOTTEN_DRINK
    except ValueError as e:
        if "Koko ei" in str(e) or "Prosentti ei" in str(e):
            await update.message.reply_text(f"Virheellinen syöte. {e}")
        else:
            await update.message.reply_text("Virheellinen syöte. Kirjoita unohtuneen juoman koko ja prosentit: (esim. 0.33 4.2)")
        return FORGOTTEN_TIME

async def get_forgotten_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    forgotten_time = update.message.text
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", forgotten_time):
        await update.message.reply_text("Virheellinen aika. Kirjoita aika muodossa HH:MM.")
        return FORGOTTEN_DRINK

    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]

    servings = calculate_alcohol(context.user_data["forgotten_size"], context.user_data["forgotten_percentage"])
    profile["drink_count"] += servings

    timestamp = time.mktime(time.strptime(f"{time.strftime('%Y-%m-%d')} {forgotten_time}", "%Y-%m-%d %H:%M"))

    profile["drink_history"].append({
        "size": context.user_data["forgotten_size"],
        "percentage": context.user_data["forgotten_percentage"],
        "servings": servings,
        "timestamp": timestamp
    })

    if profile["start_time"] == 0:
        profile["start_time"] = timestamp
    elif timestamp < profile["start_time"]:
        profile["start_time"] = timestamp

    save_profiles()

    await calculate_bac(update, context, user_id)

    await update.message.reply_text(
        f"Lisätty unohtunut juoma: {context.user_data['forgotten_size']}l "
        f"{context.user_data['forgotten_percentage']}% ({servings} annosta).\n"
        f"Juomasi aloitusaika: {forgotten_time}.\n"
        f"Arvioitu BAC: {profile['BAC']:.3f}‰"
    )
    return ConversationHandler.END

# Delete last drink command
async def delete_last_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    profile = user_profiles[user_id]
    if len(profile["drink_history"]) == 0:
        await update.message.reply_text("Ei juomia poistettavaksi.")
        return

    profile["drink_count"] -= profile["drink_history"][-1]["servings"]

    profile["drink_history"].pop()

    if len(profile["drink_history"]) == 0:
        profile["drink_count"] = 0
        profile["start_time"] = 0
        profile["elapsed_time"] = 0
        profile["BAC"] = 0
        profile["highest_BAC"] = 0
        save_profiles()
    else:
        profile["BAC"] = await calculate_bac(update, context, user_id)

    await update.message.reply_text("Viimeisin juoma poistettu.")

# Drink history command
async def drink_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if user_id not in user_profiles:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return

    if len(profile["drink_history"]) == 0:
        await update.message.reply_text("Ei juomahistoriaa.")
        return

    history_text = (
        f"{name_conjugation(profile['name'], 'n')} juomahistoria\n"
        "==========================\n"
    )
    for i, drink in enumerate(profile["drink_history"], 1):
        if drink['size'] <= 0.06:
            time_adjustment = 1 * 60
        elif drink['size'] <= 0.33:
            time_adjustment = 10 * 60
        elif drink['size'] <= 0.5:
            time_adjustment = 15 * 60
        else:
            time_adjustment = 20 * 60
        history_text += (
            f"{i}. {drink['size']}l {drink['percentage']}% ({drink['servings']} annosta)\n"
            f"Juoman lopetus: {time.strftime('%H:%M:%S', time.gmtime(drink['timestamp'] + 3 * 3600 + time_adjustment))}\n\n"
        )

    await update.message.reply_text(history_text)
