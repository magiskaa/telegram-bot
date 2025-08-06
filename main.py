import html
import json
import logging
import traceback
import openai
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, CallbackQueryHandler, filters
from datetime import time as datetime_time
from datetime import datetime
from config.config import BOT_TOKEN, OPENAI_API, ADMIN_ID
from bot.save_and_load import user_profiles
from bot.job_queue import reset_drink_stats, recap, bac_update
from bot.stats import stats, reset, personal_best, group_stats, top_3
from bot.admin import (
<<<<<<< HEAD
    admin, announcement_input, announcement, send_announcement, group_id, reset_top_3, send_saved_announcement, admin_stats, get_stats, admin_drinks, get_drinks,
=======
    admin, announcement_input, announcement, send_announcement, group_id, reset_top_3, send_saved_announcement, admin_stats, get_stats, admin_drinks, get_drinks, group_pb,
>>>>>>> 9d4abdb6f33c652091ae4fb1309f0761e7b899b3
    ANNOUNCEMENT, ANSWER, GET_STATS, GET_DRINKS
)
from bot.drinks import (
    drink, drink_button_handler, get_drink, favorite, favorite_button_handler, forgotten_drink, forgotten_button_handler, get_forgotten_drink, 
    get_forgotten_time, delete_drink, delete_drink_button_handler, drink_history, add_latest_drink,
    DRINK, FORGOTTEN_TIME, FORGOTTEN_DRINK
)
from bot.setup import (
    setup, get_gender, get_age, get_height, get_weight, profile, update_gender, update_age, 
    update_height, update_weight, button_handler, favorite_drink, favorite_drink_button_handler, get_favorite,
    GENDER, AGE, HEIGHT, WEIGHT, UPDATE_GENDER, UPDATE_AGE, UPDATE_HEIGHT, UPDATE_WEIGHT, FAVORITE
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ASK = 1
FIRST_ASK = True

# User commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Heipat! Lasken veren alkoholipitoisuutesi🍻.\n"
        "Aloita kirjoittamalla /setup. Apua saat kirjoittamalla /help."
    )

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FIRST_ASK
    FIRST_ASK = True
    await update.message.reply_text("Peruutettu.")
    return ConversationHandler.END

# Help command
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Käytettävissäsi olevat komennot:\n"
        "\n/drink - Syötä vapaavalintainen juoma. Ensiksi juoman koko ja sen jälkeen prosentit. Voit vähentää juoman asettamalla juoman koon negatiiviseksi.\n"
        "/favorite - Syötä lempijuomasi.\n"
        "/add_last - Syötä viimeisin lisäämäsi juoma.\n"
        "/stats - Katsele omia tämän iltaisia juomatilastoja. Lähettää tilastot siihen chattiin missä käytät komentoa.\n"
        "/drinks - Katsele omaa tämän iltaista juomahistoriaa.\n"
        "/group_stats - Katsele ryhmän tämän iltaisia juomatilastoja. Lähettää tilastot siihen chattiin missä käytät komentoa.\n"
        "/pb - Katsele omaa henkilökohtaista ennätystä.\n"
        "/top3 - Katsele Top 3 kännit -listaa. Lähettää listan sinne missä käytät komentoa.\n"
        "/forgotten - Lisää juoma jonka olet unohtanut lisätä aiemmin. Kirjoita ensiksi juoman koko ja prosentit, ja sen jälkeen juoman aloitusaika."
        "/profile - Katsele profiiliasi ja muokkaa tietojasi tarvittaessa.\n"
        "/setup - Aseta profiilisi tiedot. Sukupuoli, ikä, pituus, paino.\n"
        "/favorite_setup - Aseta lempijuomasi (esim. 0.33 4.2 kupari).\n"
        "/friend - Kysy tekoälykaverilta jotain syvällistä. Lopeta keskustelu sanomalla 'heippa' tai komennolla /cancel.\n"
        "/delete - Poista viimeisin lisäämäsi juoma.\n"
        "/cancel - Peruuta (setup, drink, forgotten, favorite_setup tai friend).\n"
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


# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update: ", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update:\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    with open("data/error_log.txt", "a") as f:
        f.write(f"{datetime.now(ZoneInfo('Europe/Helsinki'))} - Handler error: {context.error}\n")

    await context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode=ParseMode.HTML)


def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))

        # Setup conversation handler
        setup_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", setup), CallbackQueryHandler(button_handler, pattern="^edit_")],
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
        app.add_handler(setup_conv_handler)

        # Drink conversation handler
        drink_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("drink", drink), CallbackQueryHandler(drink_button_handler, pattern="^drink_")],
            states={
                DRINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_drink)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(drink_conv_handler)

        # Favorite drink conversation handler
        favorite_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("favorite_setup", favorite_drink), CallbackQueryHandler(favorite_drink_button_handler, pattern="^modify_")],
            states={
                FAVORITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_favorite)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(favorite_conv_handler)

        # Forgotten drink conversation handler
        forgotten_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("forgotten", forgotten_drink), CallbackQueryHandler(forgotten_button_handler, pattern="^forgotten_")],
            states={
                FORGOTTEN_DRINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_forgotten_drink)],
                FORGOTTEN_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_forgotten_time)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(forgotten_conv_handler)

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
        app.add_handler(CallbackQueryHandler(favorite_button_handler, pattern="^favorite_"))
        app.add_handler(CommandHandler("add_last", add_latest_drink))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CommandHandler("pb", personal_best))
        app.add_handler(CommandHandler("drinks", drink_history))
        app.add_handler(CommandHandler("reset", reset))
        app.add_handler(CommandHandler("group_stats", group_stats))
        app.add_handler(CommandHandler("top3", top_3))
        app.add_handler(CommandHandler("delete", delete_drink))
        app.add_handler(CallbackQueryHandler(delete_drink_button_handler, pattern="^delete_"))
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

        stats_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("get_stats", admin_stats)],
            states={
                GET_STATS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_stats)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(stats_conv_handler)

        drinks_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("get_drinks", admin_drinks)],
            states={
                GET_DRINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_drinks)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(drinks_conv_handler)

        app.add_handler(CommandHandler("group_id", group_id))
        app.add_handler(CommandHandler("reset_top3", reset_top_3))
        app.add_handler(CommandHandler("saved_announcement", send_saved_announcement))
        app.add_handler(CommandHandler("group_pb", group_pb))
        app.add_handler(CommandHandler("admin", admin))

        # Error handler
        app.add_error_handler(error_handler)

        # Job queue
        job_queue = app.job_queue
        job_queue.run_daily(recap, datetime_time(hour=9, minute=0)) # Timezone is set to UTC so this is 12:00 in GMT+3
        job_queue.run_daily(reset_drink_stats, datetime_time(hour=9, minute=0, second=2)) # This is 12:00.02
        job_queue.run_repeating(bac_update, interval=30, first=0)

        app.run_polling()
    except Exception as e:
        print(f"Error in main: {e}")


if __name__ == "__main__":
    main()
