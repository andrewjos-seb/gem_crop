import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

HISTORY_FILE = 'analysis_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading history: {e}")
            return []
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with an inline keyboard to select a zone."""
    keyboard = []
    
    # Create a 5x5 grid of buttons matching the frontend
    for row in range(5):
        row_buttons = []
        for col in range(5):
            # Button text like "0-0", callback data like "zone_0_0"
            row_buttons.append(InlineKeyboardButton(f"{row}-{col}", callback_data=f"zone_{row}_{col}"))
        keyboard.append(row_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '🌾 Welcome to Krishikaran Bot!\n\nSelect a zone from the 5x5 grid to view its latest health status:', 
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("zone_"):
        parts = data.split("_")
        row = int(parts[1])
        col = int(parts[2])
        
        history = load_history()
        
        # Filter history for the selected zone
        zone_history = [item for item in history if item.get("row") == row and item.get("col") == col]
        
        if not zone_history:
            # If no data, add a back button to return to the grid
            keyboard = [[InlineKeyboardButton("🔙 Back to Grid", callback_data="back_to_grid")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"No analysis history found for Zone ({row},{col}). Have you analyzed it on the web dashboard yet?",
                reply_markup=reply_markup
            )
            return
            
        # The latest analysis is the first one in the list (since web backend inserts at index 0)
        latest = zone_history[0]
        score = latest.get("score", "N/A")
        health = str(latest.get("health", "Unknown")).upper()
        desc = latest.get("description", "No description.")
        img = latest.get("imageName", "Unknown image")
        time = latest.get("timestamp", "Unknown time")
        
        # Format the response message
        msg = f"🌾 *Zone ({row},{col}) Status*\n\n"
        
        # Health indicator emoji
        health_emoji = "🟢" if health == "GOOD" else "🟡" if health == "AVG" else "🔴"
        
        msg += f"{health_emoji} *Health:* {health} ({score}/10)\n"
        msg += f"📷 *Image:* {img}\n"
        msg += f"🕒 *Time:* {time}\n\n"
        msg += f"📝 *Notes:* {desc}\n\n"
        
        # Trend Analysis
        if len(zone_history) > 1:
            prev_score = zone_history[1].get("score")
            if prev_score is not None and isinstance(score, int) and isinstance(prev_score, int):
                diff = score - prev_score
                if diff > 0:
                    msg += f"📈 *Trend:* Health improved (+{diff}) since previous analysis."
                elif diff < 0:
                    msg += f"📉 *Trend:* Health declined (-{abs(diff)}) since previous analysis."
                else:
                    msg += f"➖ *Trend:* Health remained stable."
        
        # Back button
        keyboard = [[InlineKeyboardButton("🔙 Back to Grid", callback_data="back_to_grid")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup)

    elif data == "back_to_grid":
        # Re-render the grid
        keyboard = []
        for row in range(5):
            row_buttons = []
            for col in range(5):
                row_buttons.append(InlineKeyboardButton(f"{row}-{col}", callback_data=f"zone_{row}_{col}"))
            keyboard.append(row_buttons)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text='Select a zone from the 5x5 grid to view its latest health status:', 
            reply_markup=reply_markup
        )

def main() -> None:
    """Run the bot."""
    # Ensure token is available
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Please set it using: export TELEGRAM_BOT_TOKEN='your_bot_token'")
        return

    # Create the Application
    application = Application.builder().token(token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("zones", start))
    application.add_handler(CallbackQueryHandler(button))

    # Run polling
    print("🤖 Krishikaran Telegram Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
