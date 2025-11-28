import os
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

from crud import list_drivers, get_assignments_for_driver, get_assignments_for_date
from config import TELEGRAM_BOT_TOKEN

from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import MessageHandler, filters
from datetime import date, timedelta

from db import init_db
init_db()

def fmt(assigns):
    lines = []
    for a in assigns:
        if a.vehicle:
            line = f"{a.driver.full_name}: {a.task_type} ({a.description}, {a.vehicle.plate}, менеджер: {a.manager})"
        else:
            line = f"{a.driver.full_name}: {a.task_type} ({a.description}, менеджер: {a.manager})"
        lines.append(line)
    return "\n".join(lines)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_menu()
    )


def main_menu():
    keyboard = [
        [KeyboardButton("📋 Расписание на сегодня"), KeyboardButton("📅 Расписание на завтра")],
        [KeyboardButton("📆 Расписание на дату")],
        [KeyboardButton("👥 Водители"), KeyboardButton("🚚 Машины")],
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("➕ Добавить водителя")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def drivers(update: Update, ctx):
    dr = list_drivers()
    if not dr:
        await update.message.reply_text("Нет водителей.")
        return
    await update.message.reply_text(
        "Водители:\n" + "\n".join(f"• {d.full_name}" for d in dr)
    )


async def driver_cmd(update: Update, ctx):
    args = ctx.args
    if not args:
        await update.message.reply_text("Использование: /driver ФИО [YYYY-MM-DD]")
        return

    date_filter = None
    if len(args) >= 2 and len(args[-1]) == 10:
        try:
            date_filter = datetime.strptime(args[-1], "%Y-%m-%d").date()
            name = " ".join(args[:-1])
        except:
            name = " ".join(args)
    else:
        name = " ".join(args)

    res = get_assignments_for_driver(name, date_filter)
    await update.message.reply_text(fmt(res))


async def day(update: Update, ctx):
    if not ctx.args:
        await update.message.reply_text("Использование: /day YYYY-MM-DD")
        return

    try:
        d = datetime.strptime(ctx.args[0], "%Y-%m-%d").date()
    except:
        await update.message.reply_text("Неверная дата.")
        return

    res = get_assignments_for_date(d)
    await update.message.reply_text(fmt(res))


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # --- 1. Расписание на сегодня ---
    if text == "📋 Расписание на сегодня":
        d = date.today()
        assigns = get_assignments_for_date(d)
        await update.message.reply_text(
            f"📋 Расписание на *{d}*:\n\n{fmt(assigns)}",
            parse_mode="Markdown"
        )

    # --- 2. Расписание на завтра ---
    elif text == "📅 Расписание на завтра":
        d = date.today() + timedelta(days=1)
        assigns = get_assignments_for_date(d)
        await update.message.reply_text(
            f"📅 Расписание на *{d}*:\n\n{fmt(assigns)}",
            parse_mode="Markdown"
        )

    # --- 3. Расписание на дату ---
    elif text == "📆 Расписание на дату":
        await update.message.reply_text(
            "Введите дату в формате *YYYY-MM-DD*:",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_date"] = True

    # --- 4. Список водителей ---
    elif text == "👥 Водители":
        dr = list_drivers()
        out = "\n".join(f"• {d.full_name}" for d in dr)
        await update.message.reply_text(f"👥 *Водители:*\n{out}", parse_mode="Markdown")

    # --- 5. Список машин ---
    elif text == "🚚 Машины":
        from db import get_session
        with get_session() as s:
            vehicles = s.query(Vehicle).order_by(Vehicle.plate).all()
        out = "\n".join(f"• {v.plate}" for v in vehicles)
        await update.message.reply_text(f"🚚 *Машины:* \n{out}", parse_mode="Markdown")

    # --- 6. Добавить задачу ---
    elif text == "➕ Добавить задачу":
        await update.message.reply_text(
            "Функция добавления задачи скоро будет. "
            "Скажи, как ты хочешь её — в виде диалога с выбором полей?"
        )

    # --- 7. Добавить водителя ---
    elif text == "➕ Добавить водителя":
        await update.message.reply_text(
            "Введите ФИО водителя:",
        )
        context.user_data["await_add_driver"] = True

    # --- 8. Ожидание даты ---
    elif context.user_data.get("awaiting_date"):
        try:
            d = date.fromisoformat(text)
            assigns = get_assignments_for_date(d)
            await update.message.reply_text(
                f"📆 Расписание на *{d}*:\n\n{fmt(assigns)}",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text("❌ Неверный формат даты. Введите YYYY-MM-DD.")
        finally:
            context.user_data["awaiting_date"] = False

    # --- 9. Ожидание ФИО для добавления водителя ---
    elif context.user_data.get("await_add_driver"):
        from crud import create_driver
        d = create_driver(text)
        await update.message.reply_text(f"✔ Водитель *{d.full_name}* добавлен.", parse_mode="Markdown")
        context.user_data["await_add_driver"] = False

    else:
        await update.message.reply_text("Не понял команду 🤔")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("drivers", drivers))
    app.add_handler(CommandHandler("driver", driver_cmd))
    app.add_handler(CommandHandler("day", day))

    app.run_polling()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))


if __name__ == "__main__":
    main()
