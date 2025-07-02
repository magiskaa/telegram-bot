import math
import openai
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.save_and_load import save_profiles, user_profiles
from bot.calculations import calculate_bac, calculate_peak_bac
from bot.utils import name_conjugation, validate_admin, get_timezone, time_adjustment
from config.config import GROUP_ID, ADMIN_ID, OPENAI_API, ANNOUNCEMENT_TEXT

ANNOUNCEMENT, ANSWER = range(2)
announcement_text = ""
saved_announcement = ""
GET_STATS = 1
GET_DRINKS = 1

# Admin commands
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
    await update.message.reply_text(
        "👨‍💻Admin komennot:\n\n"
        "/group_id\n\n"
        "/reset_top3\n\n"
        "/announcement\n\n"
        "/saved_announcement\n\n"
        "/get_stats\n\n"
        "/get_drinks"
    )

async def group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
    group_id = update.effective_chat.id
    with open("data/group_id.txt", "w") as f:
        f.write(str(group_id))

async def reset_top_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
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
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
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
        await update.message.reply_text("⚠️Virheellinen syöte. Ilmoitus peruutettu.")
        return ConversationHandler.END

async def send_saved_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
    global saved_announcement
    if saved_announcement:
        await context.bot.send_message(chat_id=GROUP_ID, text=saved_announcement)
        await update.message.reply_text("Tallennettu tiedote lähetetty ryhmään.")
    else:
        await update.message.reply_text("Ei tallennettuja tiedotteita.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
    await update.message.reply_text("Kenen tilastot haluat nähdä?")
    return GET_STATS

async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.text.lower()
    for user_id in user_profiles:
        if user_id == "top_3":
            continue
        if user == user_profiles[user_id]["name"].lower():
            profile = user_profiles[user_id]
            id = user_id
            break
        else:
            profile = None

    if not profile:
        await update.message.reply_text("Ei ole olemassa sen nimistä käyttäjää. Syötä uudestaan:")
        return GET_STATS
    
    stats = await show_stats(update, context, profile, id)
    await context.bot.send_message(chat_id=ADMIN_ID, text=stats)
    return ConversationHandler.END

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, profile, user_id):
    if profile["start_time"] == 0:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"{profile['name']} ei ole vielä aloittanut juomista.")
        return ConversationHandler.END
    
    bac_elim = await calculate_bac(update, context, user_id, noSaving=True)

    bac_max = calculate_peak_bac(user_id)

    name = profile['name'].capitalize()
    bac = profile["BAC"]
    drinking_time = profile["elapsed_time"] / 3600
    drinks = profile["drink_count"]

    if bac*10 > profile["highest_BAC"]:
        profile["highest_BAC"] = bac
    
    if bac > 0:
        context.user_data["max_BAC"] -= bac_elim * drinking_time
        hours_until_sober = context.user_data["max_BAC"] / bac_elim
        sober_timestamp = get_timezone() + (hours_until_sober * 3600)
        sober_time_str = datetime.fromtimestamp(sober_timestamp, tz=ZoneInfo("Europe/Helsinki")).strftime("%H:%M")
        sober_text = f"{name} on selvinpäin noin klo {sober_time_str}."
    else:
        sober_text = f"{name} on jo selvinpäin."

    peak_text = "Huippu saavutettu." if profile["highest_BAC"] >= bac_max else f"{bac_max:.3f}‰."

    drinking_time_h = math.floor(drinking_time)
    drinking_time_m = int(drinking_time % 1 * 60)
    stats_text = (
        f"📊{name_conjugation(profile['name'], 'n')} statsit\n"
        f"==========================\n"
        f"{name} on nauttinut {drinks:.2f} annosta.\n"
        f"{name} aloitti klo {datetime.fromtimestamp(profile['start_time'], tz=ZoneInfo('Europe/Helsinki')).strftime('%H:%M:%S')}.\n"
        f"{name} on juonut {drinking_time_h}h {drinking_time_m}min.\n"
        f"{sober_text}\n\n"
        f"Arvioitu BAC nyt: *{bac:.3f}‰*.\n"
        f"Illan korkein BAC: *{profile['highest_BAC']:.3f}‰*.\n"
        f"Tuleva korkein BAC: *{peak_text}*"
    )
    
    save_profiles()

    return stats_text

async def drinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await validate_admin(update, context)
    if result:
        return ConversationHandler.END
    
    await update.message.reply_text("Kenen juomahistorian haluat nähdä?")
    return GET_DRINKS

async def get_drinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.text.lower()
    for user_id in user_profiles:
        if user_id == "top_3":
            continue
        if user == user_profiles[user_id]["name"].lower():
            profile = user_profiles[user_id]
            break
        else:
            profile = None

    if not profile:
        await update.message.reply_text("Ei ole olemassa sen nimistä käyttäjää. Syötä uudestaan:")
        return GET_DRINKS

    drinks = await show_drinks(update, context, profile)
    await context.bot.send_message(chat_id=ADMIN_ID, text=drinks, parse_mode="Markdown")
    return ConversationHandler.END

async def show_drinks(update: Update, context: ContextTypes.DEFAULT_TYPE, profile):
    if len(profile["drink_history"]) == 0:
        await update.message.reply_text(f"{name_conjugation(profile['name'], 'lla')} ei ole juomahistoriaa.")
        return

    history_text = (
        f"🍻{name_conjugation(profile['name'], 'n')} juomahistoria\n"
        "==========================\n"
    )
    for i, drink in enumerate(profile["drink_history"], 1):
        time_adj = time_adjustment(drink["size"])
        history_text += (
            f"{i}. *{drink['size']}l* *{drink['percentage']}%* ({drink['servings']} annosta)\n"
            f"Juoman lopetus: {datetime.fromtimestamp(drink['timestamp'] + time_adj, tz=ZoneInfo('Europe/Helsinki')).strftime('%H:%M:%S')}\n\n"
        )

    return history_text

