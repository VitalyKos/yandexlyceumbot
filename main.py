from io import BytesIO

from cdifflib import CSequenceMatcher
from PIL import Image, ImageChops
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters, MessageHandler

Context = ContextTypes.DEFAULT_TYPE
BOT_TOKEN = "ENTER BOT TOKEN"

files = {}


async def text_downloader(update: Update, context: Context):
    with BytesIO() as out_file:
        file = await context.bot.get_file(update.message.document)
        await file.download_to_memory(out_file)
        out_file.seek(0)
        files.setdefault(update.message.from_user.id, {"image": [], "text": []})["text"].append(out_file.read().decode('utf-8'))


async def image_downloader(update: Update, context: Context):
    with BytesIO() as out_file:
        file = await context.bot.get_file(update.message.document)
        await file.download_to_memory(out_file)
        out_file.seek(0)
        image = Image.open(out_file).convert("RGB")
        files.setdefault(update.message.from_user.id, {"image": [], "text": []})["image"].append(image)


async def reader(update: Update, context: Context):
    files.setdefault(update.message.from_user.id, {"image": [], "text": []})["text"].append(update.message.text)


async def compare(update: Update, context: Context):
    if not context.args or context.args[0] not in ("text", "image"):
        return await update.message.reply_text("Команда не распознана. (Используйте /help чтобы узнать как пользоваться ботом)")
    message = "*Результаты проверки:*\n\n"
    if context.args[0] == "text":
        text_files = files.setdefault(update.message.from_user.id, {"image": [], "text": []})["text"]
        if len(text_files) < 2:
            return await update.message.reply_text("Недостаточно файлов. Сначала загрузите файлы, затем используйте эту команду")
        for i in range(len(text_files)):
            for j in range(i + 1, len(text_files)):
                match = CSequenceMatcher(None, text_files[i], text_files[j])
                message += f"Тексты №{i + 1} и №{j + 1} похожи на {match.ratio() * 100:.2f}%\n"
        files[update.message.from_user.id]["text"].clear()
    if context.args[0] == "image":
        image_files = files.setdefault(update.message.from_user.id, {"image": [], "text": []})["image"]
        if len(image_files) < 2:
            return await update.message.reply_text("Недостаточно файлов. Сначала загрузите файлы, затем используйте эту команду")
        for i in range(len(image_files)):
            for j in range(i + 1, len(image_files)):
                diff = ImageChops.difference(image_files[i], image_files[j]).getbbox()
                message += f"Изображения №{i + 1} и №{j + 1} похожи на {(1 - (diff[2] - diff[0]) * (diff[3] - diff[1]) / (image_files[i].width * image_files[i].height)) * 100:.2f}%\n"
        files[update.message.from_user.id]["image"].clear()

    await update.message.reply_text(message, parse_mode="markdown")


async def help(update: Update, context: Context):
    await update.message.reply_text("Привет! Я бот для сравнений текстов или изображений.\n\n"
                                    "Для начала отправь мне файлы, который хочешь сравнить.\n"
                                    "Затем используй:\n"
                                    "*/compare image* чтобы сравнить отправленные изображения\n"
                                    "*/compare text* чтобы сравнить отправленные файлы с текстом _(обычные сообщения тоже считаются)_\n\n"
                                    "На выходе ты получишь схожесть в процентах для каждой пары файлов.",
                                    "markdown")

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("compare", compare))
application.add_handler(CommandHandler("help", help))
application.add_handler(MessageHandler(filters.Document.TEXT, text_downloader))
application.add_handler(MessageHandler(filters.Document.IMAGE, image_downloader))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reader))
application.run_polling()
