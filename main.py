import time
import random
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, CallbackQueryHandler, filters
from datetime import time as datetime_time
from config.config import BOT_TOKEN, TOP_3_GIFS
from bot.save_and_load import save_profiles, user_profiles
from bot.drinks import (
    drink, get_size, get_percentage, reset_drink_stats, favorite_drink, get_favorite, favorite, name_conjugation, calculate_bac, get_group_id, recap,
    SIZE, PERCENTAGE, FAVORITE
)
from bot.setup import (
    setup, get_gender, get_age, get_height, get_weight, update_gender, update_age, update_height, update_weight, button_handler, 
    GENDER, AGE, HEIGHT, WEIGHT, UPDATE_GENDER, UPDATE_AGE, UPDATE_HEIGHT, UPDATE_WEIGHT, FAVORITE_SETUP
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Heipat! Lasken veren alkoholipitoisuutesi🍻.\n"
        "Aloita kirjoittamalla /setup. Apua saat kirjoittamalla /help."
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles.get(user_id)
    if not profile:
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Peruutettu.")
    return ConversationHandler.END

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles.get(user_id)
    if not profile:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return
    if profile["start_time"] == 0:
        await update.message.reply_text("Et ole vielä aloittanut juomista.")
        return
    
    profile["elapsed_time"] = time.time() - profile["start_time"]

    drinking_time = profile["elapsed_time"] / 3600

    drinks = profile["drink_count"]
    weight = profile["weight"]
    gender = profile["gender"]
    age = profile["age"]
    height = profile["height"]
    if gender == "mies":
        TBW = 2.447 - 0.09516 * age + 0.1074 * height + 0.3362 * weight
    else:
        TBW = -2.097 + 0.1069 * height + 0.2466 * weight
    r = TBW / weight
    total_grams_of_alcohol = drinks * 12
    
    bac = total_grams_of_alcohol / (weight*1000 * r) * 100
    grams_per_kg = 0.1 * weight
    bac_elim = grams_per_kg / (weight*1000 * r) * 100
    bac -= bac_elim * drinking_time
    bac = max(0, bac)

    profile["BAC"] = bac * 10

    if bac > 0:
        hours_until_sober = bac / 0.015
        sober_timestamp = time.time() + (hours_until_sober * 3600)
        sober_time_str = time.strftime("%H:%M", time.gmtime(sober_timestamp + 3 * 3600))
        sober_text = f"Selvinpäin olet noin klo {sober_time_str}."
    else:
        sober_text = "Olet jo selvinpäin."

    drinking_time_h = math.floor(drinking_time)
    drinking_time_m = int(drinking_time % 1 * 60)
    stats_text = (
        f"{name_conjugation(profile['name'], 'n')} statsit\n"
        f"===============================\n"
        f"Alkoholin määrä: {drinks:.2f} annosta.\n"
        f"Aloitus: {time.strftime('%H:%M:%S', time.localtime(profile['start_time']))}.\n"
        f"Olet juonut {drinking_time_h}h {drinking_time_m}min.\n"
        f"Arvioitu BAC: {bac*10:.2f}‰.\n"
        f"{sober_text}"
    )

    if profile["BAC"] == 0:
        profile["start_time"] = 0
        profile["elapsed_time"] = 0
        profile["drink_count"] = 0
    
    save_profiles()

    await update.message.reply_text(stats_text)
    return ConversationHandler.END

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    user_profiles[user_id]["drink_count"] = 0
    user_profiles[user_id]["start_time"] = 0
    user_profiles[user_id]["elapsed_time"] = 0
    user_profiles[user_id]["BAC"] = 0
    user_profiles[user_id]["highest_drink_count"] = 0
    user_profiles[user_id]["highest_BAC"] = 0

    save_profiles()

    await update.message.reply_text("Tilastot nollattu.")
    return ConversationHandler.END

async def group_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drinkers = []
    for user in user_profiles:
        if user == "top_3":
            continue
        profile = user_profiles[user]
        if profile["drink_count"] == 0:
            continue
        else:
            calculate_bac(user)
            drinkers.append(profile)

    leaderboard = ""
    sorted_drinkers = sorted(drinkers, key=lambda x: x["BAC"], reverse=True)
    for i, profile in enumerate(sorted_drinkers, 1):
        leaderboard += f"{i}. {profile['name']} {profile['BAC']:.2f}‰ ({profile['drink_count']:.2f} annosta)\n"

    if len(drinkers) != 0:
        await update.message.reply_text(
            "Ryhmän tilastot\n"
            "===============================\n"
            f"Juojia: {len(drinkers)}\n"
            f"Alkoholia juotu: {sum([profile['drink_count'] for profile in drinkers]):.2f} annosta.\n"
            "\nLeaderboard tällä hetkellä:\n"
            f"{leaderboard}"
        )

async def top_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first = user_profiles["top_3"]["1"]
    second = user_profiles["top_3"]["2"]
    third = user_profiles["top_3"]["3"]

    group_id = get_group_id()
    text = (
        "Top 3 kännit\n"
        "======================================\n"
        f"1. {first['name'].capitalize()} {first['BAC']:.2f}‰ ({first['drinks']:.2f} annosta) {first['day']}\n"
        f"2. {second['name'].capitalize()} {second['BAC']:.2f}‰ ({second['drinks']:.2f} annosta) {second['day']}\n"
        f"3. {third['name'].capitalize()} {third['BAC']:.2f}‰ ({third['drinks']:.2f} annosta) {third['day']}\n"
    )

    await context.bot.send_animation(
        chat_id=group_id,
        animation=random.choice(TOP_3_GIFS),
        caption=text
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Käytettävissäsi olevat komennot:\n"
        "\n/drink - Syötä vapaavalintainen juoma. Ensiksi juoman koko ja sen jälkeen prosentit. Voit vähentää juoman asettamalla juoman koon negatiiviseksi.\n"
        "/favorite - Syötä lempijuomasi.\n"
        "/stats - Katsele omia tämän iltaisia juomatilastoja. Lähettää tilastot siihen chattiin missä käytät komentoa.\n"
        "/group_stats - Katsele ryhmän tämän iltaisia juomatilastoja. Lähettää tilastot siihen chattiin missä käytät komentoa.\n"
        "/top3 - Katsele Top 3 kännit -listaa. Lähettää listan ryhmään.\n"
        "/profile - Katsele profiiliasi ja muokkaa tietojasi tarvittaessa.\n"
        "/setup - Aseta profiilisi tiedot. Sukupuoli, ikä, pituus, paino.\n"
        "/favorite_setup - Aseta lempijuomasi (esim. 0.33 4.2 kupari).\n"
        "/cancel - Peruuta (esim. setup taikka drink).\n"
        "/reset - Resetoi tämän illan juomatilastosi.\n"
        "/help - Näytää tämän viestin."
    )
    await update.message.reply_text(help_text)

async def group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.effective_chat.id
    with open("config/group_id.txt", "w") as f:
        f.write(str(group_id))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

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

    drink_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("drink", drink)],
        states={
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_size)],
            PERCENTAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_percentage)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(drink_conv_handler)

    favorite_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("favorite_setup", favorite_drink)],
    states={
        FAVORITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_favorite)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(favorite_conv_handler)

    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("favorite", favorite))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("group_stats", group_stats))
    app.add_handler(CommandHandler("top3", top_3))
    app.add_handler(CommandHandler("help", help))
    
    app.add_handler(CommandHandler("group_id", group_id))

    job_queue = app.job_queue
    job_queue.run_daily(recap, datetime_time(hour=9, minute=0)) # Timezone is set to UTC so this is 12:00
    job_queue.run_daily(reset_drink_stats, datetime_time(hour=11, minute=0)) # This is 14:00

    app.run_polling()


if __name__ == "__main__":
    main()
