import os
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

from crud import list_drivers, get_assignments_for_driver, get_assignments_for_date
from config import TELEGRAM_BOT_TOKEN

from db import init_db
init_db()

def fmt(assignments):
    if not assignments:
        return "Нет записей."
    out = []
    for a in assignments:
        line = f"{a.work_date} — {a.driver.full_name}: {a.task_type}"
        parts = []
        if a.description:
            parts.append(a.description)
        if a.vehicle:
            parts.append(a.vehicle.plate)
        if a.manager:
            parts.append(f"менеджер: {a.manager}")
        if parts:
            line += f" ({', '.join(parts)})"
        out.append(line)
    return "\n".join(out)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/drivers — список водителей\n"
        "/driver ФИО [дата]\n"
        "/day YYYY-MM-DD"
    )


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


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("drivers", drivers))
    app.add_handler(CommandHandler("driver", driver_cmd))
    app.add_handler(CommandHandler("day", day))

    app.run_polling()


if __name__ == "__main__":
    main()
