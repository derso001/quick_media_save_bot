import html
import re
from typing import Dict, Any

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, URLInputFile, InputMediaPhoto
from aiogram.utils.chat_action import ChatActionSender

from services.tiktok import TikTokService
from keyboards.inline import MediaCallback, get_media_keyboard

from database.db import get_or_create_user, increment_requests, get_stats

router = Router()

TIKTOK_REGEX = r"https?://(?:www\.|vm\.|vt\.|t\.)?tiktok\.com/[^\s]+"

# Простий кеш у пам'яті:
# video_cache: {media_id: telegram_file_id}
# audio_cache: {media_id: {"url": music_url, "title": music_title, "file_id": telegram_file_id}}
VIDEO_CACHE: Dict[str, str] = {}
AUDIO_CACHE: Dict[str, Dict[str, Any]] = {}


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user:
        await get_or_create_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

    user_name = message.from_user.first_name if message.from_user else "друже"
    await message.answer(
        f"Привіт, {user_name}! 👋\n\n"
        "Я <b>QuickSave Bot</b> — завантажую відео та аудіо з TikTok без водяних знаків.\n\n"
        "⚡️ Просто надішли мені посилання на пост!",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Інструкція:</b>\n"
        "1. Скопіюй посилання на пост у TikTok.\n"
        "2. Надішли його сюди.\n"
        "3. Отримай відео та можливість окремо завантажити звук у MP3.",
        parse_mode="HTML"
    )


@router.message(F.text.regexp(TIKTOK_REGEX))
async def handle_tiktok_link(message: Message):
    match = re.search(TIKTOK_REGEX, message.text)
    if not match:
        return

    url = match.group(0)
    status_msg = await message.reply("⏳ Обробляю запит...")

    async with ChatActionSender.upload_video(bot=message.bot, chat_id=message.chat.id):
        media_data = await TikTokService.download_video(url)

        if not media_data:
            await status_msg.edit_text("❌ Не вдалося отримати контент. Перевір посилання (можливо, акаунт або відео приватні).")
            return

        media_id = media_data.get("id")
        bot_user = await message.bot.get_me()
        safe_title = html.escape(media_data.get("title", "")[:100])
        safe_author = html.escape(media_data.get("author", "Автор"))

        caption = (
            f"🎬 <b>{safe_title}</b>\n"
            f"👤 Автор: {safe_author}\n\n"
            f"🤖 Завантажено через @{bot_user.username}"
        )

        # Зберігаємо аудіо в тимчасовий кеш для подальшого завантаження по кнопці
        if media_id and media_data.get("music_url"):
            AUDIO_CACHE[media_id] = {
                "url": media_data["music_url"],
                "title": media_data.get("music_title", "tiktok_audio"),
                "file_id": None
            }

        try:
            images = media_data.get("images")

            # ВАРІАНТ 1: Слайдшоу / галерея
            if images and isinstance(images, list) and len(images) > 0:
                chunk_size = 10
                image_chunks = [images[i:i + chunk_size] for i in range(0, len(images), chunk_size)]

                for index, chunk in enumerate(image_chunks):
                    media_group = []
                    for i, img_url in enumerate(chunk):
                        if index == 0 and i == 0:
                            media_group.append(InputMediaPhoto(media=img_url, caption=caption, parse_mode="HTML"))
                        else:
                            media_group.append(InputMediaPhoto(media=img_url))

                    await message.reply_media_group(media=media_group)

                # Додаємо окреме повідомлення з кнопкою аудіо для слайдшоу
                if media_id and media_data.get("music_url"):
                    await message.reply(
                        "🎵 Бажаєш завантажити аудіодоріжку з цього слайдшоу?",
                        reply_markup=get_media_keyboard(media_id)
                    )

            # ВАРІАНТ 2: Відео (перевіряємо кеш file_id)
            elif media_data.get("video_url"):
                reply_markup = get_media_keyboard(media_id) if media_id and media_data.get("music_url") else None

                # Якщо відео вже надсилалося раніше — беремо з кешу за 0 секунд
                if media_id and media_id in VIDEO_CACHE:
                    await message.reply_video(
                        video=VIDEO_CACHE[media_id],
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                else:
                    file_name = f"{media_data.get('author', 'tiktok')}_video.mp4"
                    video_file = URLInputFile(media_data["video_url"], filename=file_name)
                    sent_msg = await message.reply_video(
                        video=video_file,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                    # Кешуємо telegram file_id відправленого відео
                    if media_id and sent_msg.video:
                        VIDEO_CACHE[media_id] = sent_msg.video.file_id

            else:
                await status_msg.edit_text("❌ Не вдалося знайти ні відео, ні зображень за цим посиланням.")
                return

            await status_msg.delete()
            if message.from_user:
                await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
                await increment_requests(message.from_user.id)

        except Exception as e:
            await status_msg.edit_text("❌ Сталася помилка при надсиланні медіа в Telegram.")
            print(f"Помилка відправки в TG: {e}")


@router.callback_query(MediaCallback.filter(F.action == "audio"))
async def handle_audio_download(callback: CallbackQuery, callback_data: MediaCallback):
    media_id = callback_data.media_id
    audio_info = AUDIO_CACHE.get(media_id)

    if not audio_info or not audio_info.get("url"):
        await callback.answer("⚠️ Аудіо застаріло або недоступне. Надішли посилання повторно.", show_alert=True)
        return

    await callback.answer("⏳ Завантажую аудіо...")

    async with ChatActionSender.upload_voice(bot=callback.bot, chat_id=callback.message.chat.id):
        try:
            # Якщо аудіо вже кешоване через file_id
            if audio_info.get("file_id"):
                await callback.message.reply_audio(
                    audio=audio_info["file_id"],
                    caption="🎵 Аудіодоріжка з TikTok"
                )
            else:
                audio_file = URLInputFile(
                    audio_info["url"],
                    filename=f"{audio_info.get('title', 'audio')}.mp3"
                )
                sent_audio = await callback.message.reply_audio(
                    audio=audio_file,
                    caption=f"🎵 <b>{html.escape(audio_info.get('title', 'Аудіо'))}</b>",
                    parse_mode="HTML"
                )
                # Зберігаємо file_id аудіо
                if sent_audio.audio:
                    AUDIO_CACHE[media_id]["file_id"] = sent_audio.audio.file_id

        except Exception as e:
            await callback.message.reply("❌ Не вдалося надіслати аудіо.")
            print(f"Помилка відправки аудіо: {e}")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = await get_stats()
    text = (
        "📊 <b>Статистика бота:</b>\n\n"
        f"👥 Загалом користувачів: <b>{stats['total_users']}</b>\n"
        f"📥 Завантажено медіа: <b>{stats['total_downloads']}</b>\n"
        f"⭐ Преміум підписників: <b>{stats['premium_users']}</b>"
    )
    await message.answer(text, parse_mode="HTML")