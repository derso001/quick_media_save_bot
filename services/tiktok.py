import aiohttp
from typing import Optional, Dict, Any


class TikTokService:
    API_URL = "https://www.tikwm.com/api/"

    @classmethod
    async def download_video(cls, url: str) -> Optional[Dict[str, Any]]:
        """
        Приймає посилання на TikTok, повертає словник із даними:
        - id: унікальний ID відео
        - video_url: пряме посилання на чисте відео
        - title: опис відео
        - author: автор
        - music_url: аудіодоріжка
        - music_title: назва музичного треку
        - images: список зображень (якщо слайдшоу)
        """
        params = {
            "url": url,
            "hd": 1
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(cls.API_URL, data=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if data.get("code") == 0:
                        res = data.get("data", {})
                        music_info = res.get("music_info", {})
                        return {
                            "id": str(res.get("id")),
                            "video_url": res.get("play"),
                            "title": res.get("title", ""),
                            "author": res.get("author", {}).get("nickname", "Автор"),
                            "music_url": res.get("music"),
                            "music_title": music_info.get("title") or "Оригінальний звук",
                            "images": res.get("images")
                        }
                    return None
            except Exception as e:
                print(f"Помилка парсингу TikTok: {e}")
                return None