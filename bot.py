from datetime import datetime, date, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from db import init_db, get_session
from models import Vehicle
from crud import (
    list_drivers,
    get_assignments_for_driver,
    get_assignments_for_date,
    create_driver,
)


def fmt(assignments):
    """Форматируем список задач для ответа бота."""
    if not assignments:
        return "На эту дату задач нет."

    lines = []
    for a in assignments:
        # водитель
        driver_name = a.driver.full_name if a.driver else "неизвестный водитель"
        line = f"{driver_name}: {a.task_type}"

        parts = []
        if a.description:
            parts.append(a.description)
        if a.vehicle:
            parts.append(a.vehicle.plate)
        if a.manager:
            parts.append(f"менеджер: {a.manager}")

        if parts:
            line += " (" + ", ".join(parts) + ")"

        lines.append(line)

    return "\n".join(lines)


def main_menu():
    keyboard = [
        [KeyboardButton("📋 Расписание на сегодня"), KeyboardButton("📅 Расписание на завтра")],
        [KeyboardButton("📆 Расписание на дату")],
        [KeyboardButton("👥 Водители"), KeyboardButton("🚚 Машины")],
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("➕ Добавить водителя")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_menu(),
    )


async def drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dr = list_drivers()
    if not dr:
        await update.message.reply_text("В базе пока нет водителей.")
        return

    text = "👥 *Водители:*\n" + "\n".join(f"• {d.full_name}" for d in dr)
    await update.message.reply_text(text, parse_mode="Markdown")


async def driver_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /driver ФИО [YYYY-MM-DD]")
        return

    date_filter = None
    if len(args) >= 2 and len(args[-1]) == 10 and args[-1][4] == "-" and args[-1][7] == "-":
        try:
            date_filter = datetime.strptime(args[-1], "%Y-%m-%d").date()
            name = " ".join(args[:-1])
        except Exception:
            name = " ".join(args)
    else:
        name = " ".join(args)

    assigns = get_assignments_for_driver(name, date_filter)
    text = fmt(assigns)
    await update.message.reply_text(text)


async def day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /day YYYY-MM-DD")
        return

    try:
        d = datetime.strptime(context.args[0], "%Y-%m-%d").date()
    except Exception:
        await update.message.reply_text("❌ Неверный формат даты. Используй YYYY-MM-DD.")
        return

    assigns = get_assignments_for_date(d)
    text = fmt(assigns)
    await update.message.reply_text(text)


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # --- 1. Сегодня ---
    if text == "📋 Расписание на сегодня":
        d = date.today()
        assigns = get_assignments_for_date(d)
        await update.message.reply_text(
            f"📋 Расписание на *{d}*:\n\n{fmt(assigns)}",
            parse_mode="Markdown",
        )

    # --- 2. Завтра ---
    elif text == "📅 Расписание на завтра":
        d = date.today() + timedelta(days=1)
        assigns = get_assignments_for_date(d)
        await update.message.reply_text(
            f"📅 Расписание на *{d}*:\n\n{fmt(assigns)}",
            parse_mode="Markdown",
        )

    # --- 3. Расписание на дату ---
    elif text == "📆 Расписание на дату":
        await update.message.reply_text(
            "Введите дату в формате *YYYY-MM-DD*:",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_date"] = True

    # --- 4. Список водителей ---
    elif text == "👥 Водители":
        dr = list_drivers()
        if not dr:
            await update.message.reply_text("В базе пока нет водителей.")
            return

        out = "\n".join(f"• {d.full_name}" for d in dr)
        await update.message.reply_text(f"👥 *Водители:*\n{out}", parse_mode="Markdown")

    # --- 5. Список машин ---
    elif text == "🚚 Машины":
        with get_session() as s:
            vehicles = s.query(Vehicle).order_by(Vehicle.plate).all()

        if not vehicles:
            await update.message.reply_text("В базе пока нет машин.")
            return

        out = "\n".join(f"• {v.plate}" for v in vehicles)
        await update.message.reply_text(f"🚚 *Машины:*\n{out}", parse_mode="Markdown")

    # --- 6. Добавить задачу (заглушка) ---
    elif text == "➕ Добавить задачу":
        await update.message.reply_text(
            "Функцию добавления задач сделаем диалогом.\n"
            "Сейчас уже работает расписание по датам и добавление водителей."
        )

    # --- 7. Добавить водителя ---
    elif text == "➕ Добавить водителя":
        await update.message.reply_text("Введите ФИО водителя:")
        context.user_data["await_add_driver"] = True

    # --- 8. Ожидаем дату для 'Расписание на дату' ---
    elif context.user_data.get("awaiting_date"):
        try:
            d = date.fromisoformat(text)
            assigns = get_assignments_for_date(d)
            await update.message.reply_text(
                f"📆 Расписание на *{d}*:\n\n{fmt(assigns)}",
                parse_mode="Markdown",
            )
        except Exception:
            await update.message.reply_text("❌ Неверный формат даты. Введите YYYY-MM-DD.")
        finally:
            context.user_data["awaiting_date"] = False

    # --- 9. Ожидаем ФИО для 'Добавить водителя' ---
    elif context.user_data.get("await_add_driver"):
        d = create_driver(text)
        if d:
            await update.message.reply_text(
                f"✔ Водитель *{d.full_name}* добавлен.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Пустое имя. Водитель не добавлен.")
        context.user_data["await_add_driver"] = False

    else:
        await update.message.reply_text("Не понял команду 🤔")


async def on_startup(app):
    # На всякий случай чистим webhook, чтобы не было 409 Conflict
    await app.bot.delete_webhook(drop_pending_updates=True)


def main():
    # создаём таблицы, если их ещё нет
    init_db()

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("drivers", drivers))
    app.add_handler(CommandHandler("driver", driver_cmd))
    app.add_handler(CommandHandler("day", day))

    # Обработчик кнопок / обычного текста
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    app.run_polling()


if __name__ == "__main__":
    main()
