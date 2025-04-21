import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from config.config import BOT_TOKEN
from bot.drinks import drink, get_size, get_percentage, reset_drink_stats, favorite_drink, get_favorite, favorite, calculate_bac, SIZE, PERCENTAGE, FAVORITE
from bot.setup import (
    setup, get_gender, get_age, get_height, get_weight, update_gender, update_age, update_height, update_weight, button_handler, 
    GENDER, AGE, HEIGHT, WEIGHT, UPDATE_GENDER, UPDATE_AGE, UPDATE_HEIGHT, UPDATE_WEIGHT, FAVORITE_SETUP
)
from bot.save_and_load import save_profiles, user_profiles


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
    save_profiles()

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

    stats_text = (
        f"{profile['name']}n statsit\n"
        f"===============================\n"
        f"Alkoholin määrä: {drinks:.2f} annosta.\n"
        f"Aloitus: {time.strftime('%H:%M:%S %d-%m-%Y', time.localtime(profile['start_time']))}.\n"
        f"Olet juonut {drinking_time:.2f} tuntia.\n"
        f"Arvioitu BAC: {bac*10:.2f}‰.\n"
        f"{sober_text}"
    )

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
    save_profiles()
    await update.message.reply_text("Tilastot nollattu.")
    return ConversationHandler.END

async def group_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drinkers = []
    for user in user_profiles:
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
            f"Juotu alkoholia: {sum([profile['drink_count'] for profile in drinkers]):.2f} annosta.\n"
            "\nLeaderboard:\n"
            f"{leaderboard}"
        )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Tervetuloa käyttämään veren alkoholipitoisuuden laskuria!\n"
        "Käytä /setup komentoa aloittaaksesi.\n"
        "Käytä /profile komentoa nähdäksesi profiilisi.\n"
        "Käytä /drink komentoa lisätäksesi juomia.\n"
        "Käytä /stats komentoa nähdäksesi tilastosi.\n"
        "Käytä /reset komentoa nollataksesi tilastosi.\n"
        "Käytä /favorite_drink komentoa asettaaksesi lempijuomasi.\n"
        "Käytä /favorite komentoa lisätäksesi lempijuomasi.\n"
        "Käytä /group_stats komentoa nähdäksesi ryhmän tilastot.\n"
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
    entry_points=[CommandHandler("favorite_drink", favorite_drink)],
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
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("group_id", group_id))

    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_drink_stats, 'cron', hour=14, minute=0)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()
