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

def escape_markdown(text):
    """Helper function to escape markdown special characters for Telegram Markdown V1."""
    if text is None:
        return ""
    # Characters that have special meaning in Markdown V1: _, *, `, [
    return str(text).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')

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
    
    # Add a global summary button
    keyboard.append([InlineKeyboardButton("📊 View Fleet Summary", callback_data="fleet_summary")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '🌾 Welcome to Krishikaran Bot!\n\nSelect a zone from the 5x5 grid or click "View Fleet Summary" to see the overall farm status:', 
        reply_markup=reply_markup
    )

async def get_summary_text():
    """Generate a fleet-wide summary text."""
    history = load_history()
    if not history:
        return "No analysis history found. Please analyze zones via the web dashboard first."

    # Group by zone to get the LATEST status for each
    latest_zone_status = {}
    # Since history is newest first, the first one we see is the latest
    for item in history:
        row = item.get("row")
        col = item.get("col")
        key = f"{row}-{col}"
        if key not in latest_zone_status:
            latest_zone_status[key] = item

    total_analyzed = len(latest_zone_status)
    good_count = 0
    avg_count = 0
    bad_count = 0
    critical_zones = []
    attention_zones = []

    for item in latest_zone_status.values():
        health = str(item.get("health", "")).lower()
        if health == 'good':
            good_count += 1
        elif health == 'avg':
            avg_count += 1
            attention_zones.append(item)
        elif health == 'bad':
            bad_count += 1
            critical_zones.append(item)

    msg = "📊 *Krishikaran Fleet Summary*\n\n"
    msg += f"🚜 *Total Zones Analyzed:* {total_analyzed}\n"
    msg += f"✅ *Healthy:* {good_count}\n"
    msg += f"⚠️ *At Risk:* {avg_count}\n"
    msg += f"🚨 *Critical:* {bad_count}\n\n"

    if critical_zones:
        msg += "🔴 *CRITICAL ACTION REQUIRED:*\n"
        for z in critical_zones:
            msg += f"• *Zone ({z.get('row')},{z.get('col')})*: Score {z.get('score')}/10\n"
        msg += "\n"

    if attention_zones:
        msg += "🟡 *Performance Warnings:*\n"
        for z in attention_zones:
            msg += f"• *Zone ({z.get('row')},{z.get('col')})*: Score {z.get('score')}/10\n"
        msg += "\n"

    if not critical_zones and not attention_zones:
        msg += "✅ All analyzed zones are performing optimally.\n"

    return msg

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /summary command."""
    msg = await get_summary_text()
    await update.message.reply_text(msg, parse_mode='Markdown')

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
        
        # Escape dynamic content for Markdown
        e_health = escape_markdown(health)
        e_score = escape_markdown(score)
        e_desc = escape_markdown(desc)
        e_img = escape_markdown(img)
        e_time = escape_markdown(time)
        
        # Format the response message
        msg = f"🌾 *Zone ({row},{col}) Status*\n\n"
        
        # Health indicator emoji
        health_emoji = "🟢" if health == "GOOD" else "🟡" if health == "AVG" else "🔴"
        
        msg += f"{health_emoji} *Health:* {e_health} ({e_score}/10)\n"
        msg += f"📷 *Image:* {e_img}\n"
        msg += f"🕒 *Time:* {e_time}\n\n"
        msg += f"📝 *Notes:* {e_desc}\n\n"
        
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

    elif data == "fleet_summary":
        msg = await get_summary_text()
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
        
        # Add a global summary button
        keyboard.append([InlineKeyboardButton("📊 View Fleet Summary", callback_data="fleet_summary")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text='Select a zone from the 5x5 grid or click "View Fleet Summary" to see the overall farm status:', 
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
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CallbackQueryHandler(button))

    # Run polling
    print("🤖 Krishikaran Telegram Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
