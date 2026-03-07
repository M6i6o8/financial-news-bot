import os
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'arcee-ai/trinity-large-preview:free')

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# ============================================
# КЛЮЧЕВЫЕ СЛОВА ДЛЯ ФИЛЬТРАЦИИ НОВОСТЕЙ
# ============================================
NEWS_KEYWORDS = [
    # Ключевая ставка
    'ключевая ставка', 'ставка цб', 'ставка банка россии', 'ключевая',
    'цб рф', 'совет директоров цб', 'эльвира набиуллина',
    # Ипотека общее
    'ипотека', 'ипотечный', 'ставка по ипотеке', 'процент по ипотеке',
    'жилищное кредитование', 'первичное жилье', 'вторичка', 'новостройки',
    # Экономика
    'инфляция', 'годовая инфляция', 'рост цен', 'кредитование',
    # Банки
    'сбербанк', 'сбер', 'втб', 'газпромбанк', 'альфа-банк', 'альфа банк',
    'т-банк', 'тинькофф', 'промсвязьбанк', 'открытие', 'росбанк',
    'совкомбанк', 'рсхб', 'россельхозбанк', 'мкб', 'псб', 'ак барс', 'дом рф',
    # Ипотечные программы
    'льготная ипотека', 'семейная ипотека', 'сельская ипотека',
    'военная ипотека', 'господдержка', 'it ипотека', 'айти ипотека',
    'материнский капитал', 'субсидирование'
]

# ============================================
# РАБОЧИЕ RSS-ИСТОЧНИКИ
# ============================================
RSS_FEEDS = [
    # ТАСС - все новости
    'http://tass.ru/rss/v2.xml',
    # ТАСС - экономика
    'http://tass.ru/rss/v2.xml?sect=2061',
    # Интерфакс - главная лента
    'http://www.interfax.ru/rss.asp',
    # Интерфакс - экономика
    'http://www.interfax.ru/rss/ru/business.asp',
    # РИА Новости - экономика
    'https://ria.ru/export/rss2/economy/index.xml',
    # РИА Новости - главная
    'https://ria.ru/export/rss2/index.xml',
    # Российская газета
    'https://rg.ru/xml/index.xml',
    # Российская газета - экономика
    'https://rg.ru/xml/economy.xml',
    # Lenta.ru - экономика
    'https://lenta.ru/rss/news/economic',
    # Lenta.ru - главная
    'https://lenta.ru/rss',
    # CNews (IT и финансы)
    'https://www.cnews.ru/inc/rss/news.xml',
    # Коммерсант - главная
    'https://www.kommersant.ru/RSS/main.xml',
    # Коммерсант - экономика
    'https://www.kommersant.ru/RSS/news-economics.xml',
    # Ведомости
    'https://vedomosti.ru/rss/articles',
    # News.ru - главная
    'https://news.ru/rss/',
    # News.ru - экономика
    'https://news.ru/rss/economics/',
    # Banki.ru
    'https://www.banki.ru/xml/news.rss',
    # Прайм - финансы
    'https://1prime.ru/export/rss2/index.xml',
    # Прайм - новости
    'https://1prime.ru/export/rss2/rif/index.xml',
    # РБК - главная
    'https://rssexport.rbc.ru/rbc/news/news.rss',
    # РБК - экономика
    'https://rssexport.rbc.ru/rbc/news/economics.rss',
    # Forbes
    'https://forbes.ru/feed',
    # Известия - экономика
    'https://iz.ru/export/rss/economics.xml',
]

# ============================================
# ФУНКЦИЯ СБОРА НОВОСТЕЙ ИЗ RSS (С ТАЙМАУТАМИ)
# ============================================
async def fetch_news():
    """
    Парсит RSS-ленты, фильтрует по ключевым словам,
    возвращает список словарей с заголовком, ссылкой и датой.
    """
    print('🔍 fetch_news() стартовал')
    found_news = []
    
    async with aiohttp.ClientSession() as session:
        for feed_url in RSS_FEEDS:
            try:
                print(f'📡 Парсинг {feed_url}...')
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                # Таймаут 10 секунд на каждый RSS
                async with session.get(feed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    
                    if feed.entries:
                        for entry in feed.entries[:15]:
                            title = entry.get('title', '')
                            if any(kw.lower() in title.lower() for kw in NEWS_KEYWORDS):
                                news_item = {
                                    'title': title,
                                    'link': entry.get('link', ''),
                                    'published': entry.get('published', entry.get('pubDate', '')),
                                    'source': feed_url.split('/')[2] if '//' in feed_url else feed_url
                                }
                                found_news.append(news_item)
                                print(f'✅ Найдено: {title[:70]}...')
            except asyncio.TimeoutError:
                print(f'⏰ Таймаут при парсинге {feed_url} (10 сек)')
            except Exception as e:
                print(f'❌ Ошибка при парсинге {feed_url}: {str(e)[:100]}')
                continue
    
    # Убираем дубликаты
    unique_news = []
    seen_titles = set()
    for item in found_news:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_news.append(item)
    
    print(f'📊 Всего уникальных новостей: {len(unique_news)}')
    return unique_news[:10]

# ============================================
# ГЕНЕРАЦИЯ ПОСТА ЧЕРЕЗ DEEPSEEK (С ТАЙМАУТОМ)
# ============================================
async def generate_post(news_items):
    """
    Принимает список новостей, отправляет в DeepSeek,
    возвращает готовый текст поста или None при ошибке/таймауте.
    """
    print('🤖 generate_post() стартовал')
    
    # Формируем список новостей для промпта
    news_text = ""
    for i, item in enumerate(news_items, 1):
        news_text += f"{i}. {item['title']}\n"
        if item.get('link'):
            news_text += f"   🔗 {item['link']}\n"
    
    prompt = (
        "Ты — аналитик финансового Telegram-канала. Напиши ЕДИНСТВЕННУЮ итоговую сводку новостей "
        "по ключевой ставке и ипотеке в России на основе предоставленных материалов.\n\n"
        "ТРЕБОВАНИЯ К ПОСТУ:\n"
        "1. Пиши живым, разговорным языком, как для друзей\n"
        "2. Используй эмодзи (🏦, 📊, 🏠, 💰, 📈)\n"
        "3. Если есть конкретные цифры — обязательно их выдели\n"
        "4. В конце добавь 3-5 хэштегов по теме\n"
        "5. НИКАКИХ вариантов, комментариев или альтернатив — только один готовый пост\n\n"
        "НОВОСТИ ДЛЯ АНАЛИЗА:\n" + news_text
    )
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/your_channel",
        "X-Title": "Financial News Bot"
    }
    
    data = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "Ты — редактор финансового Telegram-канала. Пиши только один итоговый пост."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 1000
    }
    
    print('📤 Отправляю запрос к DeepSeek...')
    try:
        # Таймаут 30 секунд на весь запрос к DeepSeek
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                print(f'📥 Статус ответа: {response.status}')
                
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Чистка от возможных вариантов
                    for marker in ["---", "Или чуть иначе:", "Вот вариант:", "Вариант 1:", "Вариант 2:"]:
                        if marker in content:
                            content = content.split(marker)[0].strip()
                    
                    print('✅ Пост успешно сгенерирован')
                    return content
                else:
                    text = await response.text()
                    print(f'❌ Ошибка DeepSeek: {response.status} - {text}')
                    return None
    except asyncio.TimeoutError:
        print('❌ Таймаут при запросе к DeepSeek (30 сек)')
        return None
    except Exception as e:
        print(f'❌ Ошибка при запросе к DeepSeek: {e}')
        return None

# ============================================
# ПУБЛИКАЦИЯ НОВОСТЕЙ (С ОБЩИМ ТАЙМАУТОМ)
# ============================================
async def publish_news():
    """
    Основная функция с защитой от зависания — максимум 90 секунд на всё.
    """
    print('📰 publish_news() стартовал')
    
    try:
        # Общий таймаут 90 секунд на всю операцию
        await asyncio.wait_for(_publish_news_internal(), timeout=90)
    except asyncio.TimeoutError:
        print('❌ publish_news() превысила лимит времени (90 сек) — принудительно завершено')
        # Можно отправить уведомление админу, но пока просто логируем
    except Exception as e:
        print(f'❌ Непредвиденная ошибка в publish_news: {e}')

async def _publish_news_internal():
    """Внутренняя логика publish_news (выполняется с таймаутом)"""
    
    # Собираем новости
    news_items = await fetch_news()
    print(f'📋 Собрано новостей: {len(news_items)}')
    
    if not news_items:
        print('⚠️ Нет новостей для публикации - пропускаем')
        return
    
    # Генерируем пост
    post_text = await generate_post(news_items)
    
    if not post_text:
        print('⚠️ Не удалось сгенерировать пост - пропускаем')
        return
    
    print(f'📝 Пост сгенерирован, длина: {len(post_text)} символов')
    
    # Отправляем в Telegram
    try:
        await bot.send_message(TELEGRAM_CHANNEL_ID, post_text, parse_mode="Markdown")
        print('✅ Пост успешно отправлен в канал')
    except Exception as e:
        print(f'❌ Ошибка при отправке поста: {e}')
        # Пробуем без Markdown
        try:
            await bot.send_message(TELEGRAM_CHANNEL_ID, post_text)
            print('✅ Пост отправлен без Markdown')
        except Exception as e2:
            print(f'❌ Ошибка при повторной отправке: {e2}')

# ============================================
# ЗАПУСК И РАСПИСАНИЕ
# ============================================
async def on_startup():
    """
    Выполняется при старте бота.
    """
    print('🚀 Бот запускается...')
    
    # Очищаем старые задачи (на всякий случай)
    scheduler.remove_all_jobs()
    
    # Единственный выпуск в 15:00
    scheduler.add_job(
        publish_news,
        'cron', 
        hour=15, 
        minute=0,
        id='daily_news',
        replace_existing=True
    )
    
    scheduler.start()
    print('⏰ Расписание установлено: 15:00 ежедневно')
    
    # Для теста можно запустить сразу (раскомментируй если нужно)
    # await publish_news()
    
    print("✅ Бот готов к работе")

# ============================================
# ТОЧКА ВХОДА
# ============================================
async def main():
    await on_startup()
    # Держим event loop живым, но не нагружаем
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())