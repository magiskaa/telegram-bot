import time
import random
import math
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, CallbackQueryHandler, filters
from datetime import time as datetime_time
from config.config import BOT_TOKEN, GROUP_ID, TOP_3_GIFS, OPENAI_API, ADMIN_ID, ANNOUNCEMENT_TEXT
from bot.save_and_load import save_profiles, user_profiles
from bot.drinks import (
    drink, get_size, get_percentage, reset_drink_stats, favorite_drink, get_favorite, favorite, delete_last_drink, name_conjugation, calculate_bac, recap, bac_update,
    SIZE, PERCENTAGE, FAVORITE
)
from bot.setup import (
    setup, get_gender, get_age, get_height, get_weight, update_gender, update_age, update_height, update_weight, button_handler, 
    GENDER, AGE, HEIGHT, WEIGHT, UPDATE_GENDER, UPDATE_AGE, UPDATE_HEIGHT, UPDATE_WEIGHT, FAVORITE_SETUP
)

ASK = 1
FIRST_ASK = True
ANNOUNCEMENT, ANSWER = range(2)
announcement_text = ""
saved_announcement = ""

# User commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Heipat! Lasken veren alkoholipitoisuutesi🍻.\n"
        "Aloita kirjoittamalla /setup. Apua saat kirjoittamalla /help."
    )

# Profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if user_id not in user_profiles:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return
    
    if profile["favorite_drink_size"] == "ei määritetty":
        favorite_drink_text = ""
    else:
        favorite_drink_text = f"{profile['favorite_drink_name'].capitalize()}: {profile['favorite_drink_size'].replace('.', ',')}l {profile['favorite_drink_percentage'].replace('.', ',')}%"

    profile_text = (
        f"{profile['name'].capitalize()}n profiili\n"
        f"\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\\=\n"
        f"Sukupuoli: {profile['gender']}\n"
        f"Ikä: {profile['age']} vuotta\n"
        f"Pituus: {profile['height']} cm\n"
        f"Paino: {profile['weight']} kg\n"
        f"Lempijuoma: {profile['favorite_drink_name']}\n"
        f"{favorite_drink_text}"
    )

    keyboard = [
        [InlineKeyboardButton("Muokkaa sukupuolta", callback_data="edit_gender")],
        [InlineKeyboardButton("Muokkaa ikää", callback_data="edit_age")],
        [InlineKeyboardButton("Muokkaa pituutta", callback_data="edit_height")],
        [InlineKeyboardButton("Muokkaa painoa", callback_data="edit_weight")],
        [InlineKeyboardButton("Muokkaa lempijuomaa", callback_data="edit_favorite")],
    ]

    await update.message.reply_text(
        profile_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FIRST_ASK
    FIRST_ASK = True
    await update.message.reply_text("Peruutettu.")
    return ConversationHandler.END

# Own stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if user_id not in user_profiles:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return
    if profile["start_time"] == 0:
        await update.message.reply_text("Et ole vielä aloittanut juomista.")
        return
    
    bac_elim = await calculate_bac(update, context, user_id, noSaving=True)

    bac = profile["BAC"]
    drinking_time = profile["elapsed_time"] / 3600
    drinks = profile["drink_count"]
    
    if bac > 0:
        if drinking_time < 0.75:
            elimination_factor = drinking_time / 0.25
            elimination_time = drinking_time * elimination_factor
        else:
            elimination_time = drinking_time

        context.user_data["max_BAC"] -= bac_elim * elimination_time
        hours_until_sober = context.user_data["max_BAC"] / bac_elim
        sober_timestamp = time.time() + (hours_until_sober * 3600)
        sober_time_str = time.strftime("%H:%M", time.gmtime(sober_timestamp + 3 * 3600))
        sober_text = f"Selvinpäin olet noin klo {sober_time_str}."
    else:
        sober_text = "Olet jo selvinpäin."

    drinking_time_h = math.floor(drinking_time)
    drinking_time_m = int(drinking_time % 1 * 60)
    stats_text = (
        f"{name_conjugation(profile['name'], 'n')} statsit\n"
        f"==========================\n"
        f"Alkoholin määrä: {drinks:.2f} annosta.\n"
        f"Aloitus: {time.strftime('%H:%M:%S', time.gmtime(profile['start_time'] + 3 * 3600))}.\n"
        f"Olet juonut {drinking_time_h}h {drinking_time_m}min.\n"
        f"Arvioitu BAC: {bac*10:.3f}‰.\n"
        f"{sober_text}"
    )
    
    save_profiles()

    await update.message.reply_text(stats_text)

# Personal best command
async def personal_best(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if user_id not in user_profiles:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return

    if profile["PB_BAC"] == 0:
        await update.message.reply_text("Ei henkilökohtaista ennätystä.")
        return
    else:
        pb_text = (
            f"{name_conjugation(profile['name'], 'n')} henkilökohtainen ennätys\n"
            f"=============================\n"
            f"BAC: {profile['PB_BAC']:.2f}‰ ({profile['PB_dc']:.2f} annosta)\n"
            f"Päivä: {profile['PB_day']}"
        )
        await update.message.reply_text(pb_text)

# Own stats reset command
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    user_profiles[user_id]["drink_count"] = 0
    user_profiles[user_id]["start_time"] = 0
    user_profiles[user_id]["elapsed_time"] = 0
    user_profiles[user_id]["BAC"] = 0
    user_profiles[user_id]["highest_BAC"] = 0
    user_profiles[user_id]["BAC_1_7"] = 0
    user_profiles[user_id]["BAC_2_0"] = 0
    user_profiles[user_id]["BAC_2_3"] = 0
    user_profiles[user_id]["BAC_2_7"] = 0
    user_profiles[user_id]["drink_history"] = []

    save_profiles()

    await update.message.reply_text("Tilastot nollattu.")

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

# Group stats command
async def group_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drinkers = []
    for user in user_profiles:
        if user == "top_3":
            continue
        profile = user_profiles[user]
        if profile["drink_count"] == 0:
            continue
        else:
            await calculate_bac(update, context, user)
            drinkers.append(profile)

    leaderboard = ""
    sorted_drinkers = sorted(drinkers, key=lambda x: x["BAC"], reverse=True)
    for i, profile in enumerate(sorted_drinkers, 1):
        leaderboard += f"{i}. {profile['name']} {profile['BAC']:.2f}‰ ({profile['drink_count']:.2f} annosta)\n"

    if len(drinkers) != 0:
        await update.message.reply_text(
            "Ryhmän tilastot\n"
            "==========================\n"
            f"Juojia: {len(drinkers)}\n"
            f"Alkoholia juotu: {sum([profile['drink_count'] for profile in drinkers]):.2f} annosta.\n"
            "\nLeaderboard tällä hetkellä:\n"
            f"{leaderboard}"
        )
    else:
        await update.message.reply_text("Ei juojia tällä hetkellä.")

# Top 3 command
async def top_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first = user_profiles["top_3"]["1"]
    second = user_profiles["top_3"]["2"]
    third = user_profiles["top_3"]["3"]

    text = (
        "Top 3 kännit\n"
        "=============================\n"
        f"1. {first['name'].capitalize()} {first['BAC']:.2f}‰ ({first['drinks']:.2f} annosta) {first['day']}\n"
        f"2. {second['name'].capitalize()} {second['BAC']:.2f}‰ ({second['drinks']:.2f} annosta) {second['day']}\n"
        f"3. {third['name'].capitalize()} {third['BAC']:.2f}‰ ({third['drinks']:.2f} annosta) {third['day']}\n"
    )

    await context.bot.send_animation(
        chat_id=GROUP_ID,
        animation=random.choice(TOP_3_GIFS),
        caption=text
    )

# Help command
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Käytettävissäsi olevat komennot:\n"
        "\n/drink - Syötä vapaavalintainen juoma. Ensiksi juoman koko ja sen jälkeen prosentit. Voit vähentää juoman asettamalla juoman koon negatiiviseksi.\n"
        "/favorite - Syötä lempijuomasi.\n"
        "/stats - Katsele omia tämän iltaisia juomatilastoja. Lähettää tilastot siihen chattiin missä käytät komentoa.\n"
        "/pb - Katsele omaa henkilökohtaista ennätystä.\n"
        "/drinks - Katsele omaa tämän iltaista juomahistoriaa.\n"
        "/group_stats - Katsele ryhmän tämän iltaisia juomatilastoja. Lähettää tilastot siihen chattiin missä käytät komentoa.\n"
        "/top3 - Katsele Top 3 kännit -listaa. Lähettää listan ryhmään.\n"
        "/profile - Katsele profiiliasi ja muokkaa tietojasi tarvittaessa.\n"
        "/setup - Aseta profiilisi tiedot. Sukupuoli, ikä, pituus, paino.\n"
        "/favorite_setup - Aseta lempijuomasi (esim. 0.33 4.2 kupari).\n"
        "/friend - Kysy tekoälykaverilta jotain syvällistä. Lopeta keskustelu sanomalla 'heippa' tai komennolla /cancel.\n"
        "/delete - Poista viimeisin lisäämäsi juoma.\n"
        "/cancel - Peruuta (esim. setup taikka drink).\n"
        "/reset - Resetoi tämän illan juomatilastosi.\n"
        "/help - Näytää tämän viestin."
    )
    await update.message.reply_text(help_text)

# AI friend command
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mitä haluaisit kysyä? Voit lopettaa keskustelun sanomalla 'heippa' tai komennolla /cancel.")
    return ASK

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FIRST_ASK
    openai.api_key = OPENAI_API
    user_message = update.message.text
    user_id = str(update.message.from_user.id)

    if user_message.lower() == "heippa" or user_message.lower() == "heippa!":
        await update.message.reply_text("Heippa!")
        FIRST_ASK = True
        return ConversationHandler.END
    
    if FIRST_ASK:
        FIRST_ASK = False
        message = (
            "Olet tekoälykaveri, jolta saatan kysyä mitä tahansa mieleeni juolahtaa, "
             "tai jopa jotain syvällisempiäkin asioita. Vastaa suht lyhyesti ja aina suomeksi. "
             f"Nimeni on {user_profiles[user_id]['name']}. "
             f"Tässä mietteeni tällä kertaa: {user_message}"
        )
    else:
        message = user_message


    model = "gpt-4.1-mini"
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": message}
        ],
    )
    await update.message.reply_text(response.choices[0].message.content)
    return ASK

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


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Setup conversation handler
    setup_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup), CallbackQueryHandler(button_handler)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            UPDATE_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_gender)],
            UPDATE_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_age)],
            UPDATE_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_height)],
            UPDATE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_weight)],
            FAVORITE_SETUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_favorite)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(setup_conv_handler)

    # Drink conversation handler
    drink_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("drink", drink)],
        states={
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_size)],
            PERCENTAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_percentage)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(drink_conv_handler)

    # Favorite drink conversation handler
    favorite_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("favorite_setup", favorite_drink)],
    states={
        FAVORITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_favorite)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(favorite_conv_handler)

    # AI friend conversation handler
    ask_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("friend", ask)],
        states={
            ASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(ask_conv_handler)

    # User commands
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("favorite", favorite))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("pb", personal_best))
    app.add_handler(CommandHandler("drinks", drink_history))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("group_stats", group_stats))
    app.add_handler(CommandHandler("top3", top_3))
    app.add_handler(CommandHandler("delete", delete_last_drink))
    app.add_handler(CommandHandler("help", help))
    
    # Admin commands
    announcement_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("announcement", announcement_input)],
        states={
            ANNOUNCEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, announcement)],
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_announcement)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(announcement_conv_handler)

    app.add_handler(CommandHandler("group_id", group_id))
    app.add_handler(CommandHandler("reset_top3", reset_top_3))
    app.add_handler(CommandHandler("saved_announcement", send_saved_announcement))
    app.add_handler(CommandHandler("admin", admin))

    job_queue = app.job_queue
    job_queue.run_daily(recap, datetime_time(hour=9, minute=0)) # Timezone is set to UTC so this is 12:00 in GMT+3
    job_queue.run_daily(reset_drink_stats, datetime_time(hour=9, minute=0, second=2)) # This is 12:00.02
    job_queue.run_repeating(bac_update, interval=60, first=0)

    app.run_polling()


if __name__ == "__main__":
    main()
