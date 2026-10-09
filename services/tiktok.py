import aiohttp
from typing import Optional, Dict, Any


class TikTokService:
    API_URL = "https://www.tikwm.com/api/"

    @classmethod
    async def download_video(cls, url: str) -> Optional[Dict[str, Any]]:
        """
        Приймає посилання на TikTok, повертає словник із даними:
        - video_url: пряме посилання на чисте відео
        - title: опис відео
        - author: автор
        - music_url: аудіодоріжка
        """
        params = {
            "url": url,
            "hd": 1  # Запит на максимальну якість
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(cls.API_URL, data=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    # TikWM повертає код 0 у разі успіху
                    if data.get("code") == 0:
                        res = data.get("data", {})
                        return {
                            "video_url": res.get("play"),      # Відео без водяного знака
                            "title": res.get("title", ""),
                            "author": res.get("author", {}).get("nickname", "Автор"),
                            "music_url": res.get("music"),
                            "images": res.get("images")        # Якщо це фото-слайдшоу
                        }
                    return None
            except Exception as e:
                print(f"Помилка парсингу TikTok: {e}")
                return None