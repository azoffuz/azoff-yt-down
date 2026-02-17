import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp

# BOT TOKENINI ENVIRONMENT'DAN OLAMIZ (Xavfsizlik uchun)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Iltimos, Render'da Environment Variable sifatida tokenni kiriting.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Render.com bepul tarifi botni o'chirib qo'ymasligi uchun web server
async def handle(request):
    return web.Response(text="Botingiz muvaffaqiyatli ishlamoqda!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# YouTube havolasini tekshirish uchun Regex
YT_REGEX = r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+'

def get_video_info(url):
    ydl_opts = {'quiet': True, 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception:
            return None

def download_media(ydl_opts, url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=True)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("👋 Assalomu alaykum! Menga YouTube video yoki shorts linkini yuboring.")

@dp.message(F.text.regexp(YT_REGEX))
async def process_youtube_link(message: types.Message):
    wait_msg = await message.answer("⏳ Ma'lumotlar olinmoqda, biroz kuting...")
    url = message.text

    # YouTube ma'lumotlarini olish
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, get_video_info, url)

    if not info:
        await wait_msg.edit_text("❌ Xatolik yuz berdi. Video topilmadi yoki yopiq.")
        return

    title = info.get('title', 'Noma\'lum video')
    video_url = info.get('webpage_url', url)
    channel = info.get('uploader', 'Noma\'lum_kanal')
    channel_url = info.get('uploader_url', '')
    video_id = info.get('id')

    # Xabar matnini tayyorlash
    text = (
        f"📺 <a href='{video_url}'>{title}</a> ➡️\n"
        f"👤 <a href='{channel_url}'>#{channel.replace(' ', '')}</a> ➡️\n\n"
        f"✅ 144p, 240p, 360p (Mavjud)\n"
        f"🚀 480p, 720p (Mavjud)\n"
        f"🔥 1080p (Mavjud)\n\n"
        f"<b>Formatni tanlang ⬇️</b>\n\n"
        f"ℹ️ <i>Eslatma: Telegram qoidasiga ko'ra bot 50MB dan katta fayllarni yubora olmaydi.</i>"
    )

    # Tugmalarni yasash
    builder = InlineKeyboardBuilder()
    
    resolutions = [
        ("📹 144p", "144"), ("📹 240p", "240"), 
        ("📹 360p", "360"), ("📹 480p", "480"), 
        ("📹 720p", "720"), ("📹 1080p", "1080"),
        ("🎧 MP3", "mp3")
    ]

    for text_btn, res in resolutions:
        # Callback data 64 baytdan oshmasligi kerak, shuning uchun qisqartma qildik
        builder.button(text=text_btn, callback_data=f"dl_{video_id}_{res}")

    builder.adjust(3, 2, 2)

    await wait_msg.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(call: types.CallbackQuery):
    await call.answer("Yuklanmoqda... Bu biroz vaqt olishi mumkin.", show_alert=False)
    
    data = call.data.split("_")
    video_id = data[1]
    res = data[2]
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    msg = await call.message.answer(f"⏳ Yuklab olinmoqda ({res})... Kutib turing.")

    filename = f"{video_id}_{res}"
    
    if res == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{filename}.%(ext)s',
            'writethumbnail': True, # Rasm yuklash
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegMetadata', 'add_metadata': True}, # Metadata qo'shish
                {'key': 'EmbedThumbnail'}, # Rasmni mp3 ga joylash
            ],
            'quiet': True
        }
        ext = "mp3"
    else:
        ydl_opts = {
            'format': f'bestvideo[height<={res}]+bestaudio/best[height<={res}]/best',
            'outtmpl': f'{filename}.%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True
        }
        ext = "mp4"

    try:
        loop = asyncio.get_event_loop()
        # Yuklash jarayonini asinxronda ishga tushirish
        info = await loop.run_in_executor(None, download_media, ydl_opts, url)
        
        file_path = f"{filename}.{ext}"
        
        # 50 MB limitni tekshirish
        if os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 49.5:
                await msg.edit_text("❌ Kechirasiz, bu videoning hajmi 50MB dan katta. Telegram botlar 50MB dan katta fayllarni yubora olmaydi.")
                return

        await msg.edit_text("⬆️ Telegramga yuklanmoqda...")
        
        if ext == "mp3":
            artist = info.get('artist') or info.get('creator') or info.get('uploader', 'Noma\'lum Ijrochi')
            title = info.get('track') or info.get('title', 'Noma\'lum Qo\'shiq')
            
            await bot.send_audio(
                chat_id=call.from_user.id, 
                audio=types.FSInputFile(file_path),
                title=title,
                performer=artist
            )
        else:
            await bot.send_video(call.from_user.id, types.FSInputFile(file_path))
            
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Xatolik yuz berdi. Video hajmi juda katta yoki ruxsat etilmagan.\nSabab: {str(e)[:100]}")
    finally:
        # Xotira to'lmasligi uchun fayllarni va rasmlarni (webp/jpg) serverdan o'chirish
        for f in os.listdir():
            if f.startswith(filename):
                try:
                    os.remove(f)
                except Exception:
                    pass

async def main():
    # Web serverni orqa fonda ishga tushirish
    asyncio.create_task(web_server()) 
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
