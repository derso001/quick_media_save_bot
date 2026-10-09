import html
import re
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, URLInputFile, InputMediaPhoto
from aiogram.utils.chat_action import ChatActionSender

from services.tiktok import TikTokService

router = Router()

TIKTOK_REGEX = r"https?://(?:www\.|vm\.|vt\.|t\.)?tiktok\.com/[^\s]+"


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "друже"
    await message.answer(
        f"Привіт, {user_name}! 👋\n\n"
        "Я <b>QuickSave Bot</b> — завантажую медіа без водяних знаків.\n\n"
        "⚡️ Просто надішли мені посилання на TikTok, і я поверну тобі відео або фотогалерею!",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Інструкція:</b>\n"
        "1. Скопіюй посилання на пост у TikTok.\n"
        "2. Надішли його сюди.\n"
        "3. Отримай чистий файл без водяних знаків.",
        parse_mode="HTML"
    )


@router.message(F.text.regexp(TIKTOK_REGEX))
async def handle_tiktok_link(message: Message):
    match = re.search(TIKTOK_REGEX, message.text)
    if not match:
        return

    url = match.group(0)
    status_msg = await message.reply("⏳ Завантажую медіа, зачекай трішки...")

    async with ChatActionSender.upload_video(bot=message.bot, chat_id=message.chat.id):
        media_data = await TikTokService.download_video(url)

        if not media_data:
            await status_msg.edit_text("❌ Не вдалося отримати контент. Перевір посилання (можливо, акаунт або відео приватні).")
            return

        bot_user = await message.bot.get_me()
        safe_title = html.escape(media_data.get("title", "")[:100])
        safe_author = html.escape(media_data.get("author", "Автор"))

        caption = (
            f"🎬 <b>{safe_title}</b>\n"
            f"👤 Автор: {safe_author}\n\n"
            f"🤖 Завантажено через @{bot_user.username}"
        )

        try:
            images = media_data.get("images")

            # ВАРІАНТ 1: Це слайдшоу / галерея картинок
            if images and isinstance(images, list) and len(images) > 0:
                # Telegram дозволяє надсилати максимум до 10 медіа в одному альбомі
                # Розбиваємо список картинок на пачки по 10 штук
                chunk_size = 10
                image_chunks = [images[i:i + chunk_size] for i in range(0, len(images), chunk_size)]

                for index, chunk in enumerate(image_chunks):
                    media_group = []
                    for i, img_url in enumerate(chunk):
                        # Додаємо підпис тільки до першого фото першого альбому
                        if index == 0 and i == 0:
                            media_group.append(InputMediaPhoto(media=img_url, caption=caption, parse_mode="HTML"))
                        else:
                            media_group.append(InputMediaPhoto(media=img_url))

                    await message.reply_media_group(media=media_group)

            # ВАРІАНТ 2: Це стандартне відео
            elif media_data.get("video_url"):
                video_file = URLInputFile(
                        media_data["video_url"],
                        filename="tiktok_video.mp4"
                    )
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await status_msg.edit_text("❌ Не вдалося знайти ні відео, ні зображень за цим посиланням.")
                return

            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text("❌ Сталася помилка при надсиланні медіа в Telegram.")
            print(f"Помилка відправки в TG: {e}")