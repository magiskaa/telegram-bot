import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from config.config import BOT_TOKEN
from bot.drinks import drink, get_size, get_percentage, reset_drink_stats, SIZE, PERCENTAGE
from bot.setup import setup, get_gender, get_weight, update_gender, update_weight, button_handler, GENDER, WEIGHT, UPDATE_GENDER, UPDATE_WEIGHT
from bot.save_and_load import save_profiles, user_profiles


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heipat! Lasken veren alkoholipitoisuutesi🍻. Aloita kirjoittamalla /setup.")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles.get(user_id)
    if not profile:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return
    
    profile_text = (
        f"Sukupuoli: {profile["gender"]}\n"
        f"Paino: {profile["weight"]} kg\n"
    )

    keyboard = [
        [InlineKeyboardButton("Muokkaa sukupuolta", callback_data="edit_gender")],
        [InlineKeyboardButton("Muokkaa painoa", callback_data="edit_weight")]
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
    weight = profile["weight"] * 1000
    gender = profile["gender"]
    r = 0.68 if gender == "mies" else 0.55
    total_grams_of_alcohol = drinks * 12
    
    bac = total_grams_of_alcohol / (weight * r) * 100
    bac -= 0.015 * drinking_time
    bac = max(0, bac) 

    if bac > 0:
        hours_until_sober = bac / 0.015
        sober_timestamp = time.time() + (hours_until_sober * 3600)
        sober_time_str = time.strftime("%H:%M", time.localtime(sober_timestamp))
        sober_text = f"Selvinpäin olet noin klo {sober_time_str}."
    else:
        sober_text = "Olet jo selvinpäin."

    stats_text = (
        f"Alkoholin määrä: {drinks:.2f} annosta.\n"
        f"Aloitus: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(profile['start_time']))}.\n"
        f"Olet juonut {drinking_time:.2f} tuntia.\n"
        f"Arvioitu BAC: {bac*10:.4f}‰.\n"
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
    save_profiles()
    await update.message.reply_text("Tilastot nollattu.")
    return ConversationHandler.END



def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    setup_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setup", setup), CallbackQueryHandler(button_handler)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            UPDATE_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_gender)],
            UPDATE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_weight)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(CommandHandler("profile", profile))
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

    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))

    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_drink_stats, 'cron', hour=12, minute=0)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()
