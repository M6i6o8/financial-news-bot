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
# РАБОЧИЕ RSS-ИСТОЧНИКИ (ПРОВЕРЕНО)
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
# ФУНКЦИЯ СБОРА НОВОСТЕЙ ИЗ RSS
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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                async with session.get(feed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    # Парсим даже если статус не 200 (иногда данные есть)
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    
                    if feed.entries:
                        print(f'📰 Получено {len(feed.entries)} записей из {feed_url}')
                        
                        for entry in feed.entries[:15]:  # последние 15 новостей
                            title = entry.get('title', '')
                            # Проверяем по ключевым словам
                            if any(kw.lower() in title.lower() for kw in NEWS_KEYWORDS):
                                news_item = {
                                    'title': title,
                                    'link': entry.get('link', ''),
                                    'published': entry.get('published', entry.get('pubDate', '')),
                                    'source': feed_url.split('/')[2] if '//' in feed_url else feed_url
                                }
                                found_news.append(news_item)
                                print(f'✅ Найдено: {title[:70]}...')
                    else:
                        print(f'⚠️ Нет записей в RSS {feed_url}')
                        
            except asyncio.TimeoutError:
                print(f'⏰ Таймаут при парсинге {feed_url}')
            except Exception as e:
                print(f'❌ Ошибка при парсинге {feed_url}: {str(e)[:100]}')
                continue
    
    # Убираем дубликаты по заголовкам
    unique_news = []
    seen_titles = set()
    for item in found_news:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_news.append(item)
    
    print(f'📊 Всего уникальных новостей: {len(unique_news)}')
    
    # Возвращаем максимум 10 новостей
    # ЕСЛИ НОВОСТЕЙ НЕТ - ВОЗВРАЩАЕМ ПУСТОЙ СПИСОК (никаких заглушек!)
    return unique_news[:10]

# ============================================
# ГЕНЕРАЦИЯ ПОСТА ЧЕРЕЗ DEEPSEEK
# ============================================
async def generate_post(news_items):
    """
    Принимает список новостей, отправляет в DeepSeek,
    возвращает готовый текст поста.
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
        "2. Используй эмодзи для разделения блоков и привлечения внимания (🏦, 📊, 🏠, 💰, 📈)\n"
        "3. Если есть конкретные цифры (ставки, проценты, суммы) — обязательно их выдели\n"
        "4. Структурируй информацию: сначала самое важное, потом детали\n"
        "5. В конце добавь 3-5 хэштегов по теме (#ключеваяставка #ипотека #сбербанк и т.д.)\n"
        "6. НЕ используй комментарии типа 'Вот вариант:' или 'Надеюсь, подойдет'\n"
        "7. НЕ предлагай альтернативных версий\n"
        "8. Просто напиши ОДИН готовый пост\n\n"
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
            {
                "role": "system", 
                "content": "Ты — редактор финансового Telegram-канала. Твоя задача — писать только ОДИН итоговый пост по ключевой ставке и ипотеке. Никаких вариантов, никаких комментариев, только чистый текст готового поста с эмодзи."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.8,
        "max_tokens": 1000
    }
    
    print('📤 Отправляю запрос к DeepSeek...')
    try:
        timeout = aiohttp.ClientTimeout(total=60)
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
                    
                    # Постобработка: убираем возможные варианты
                    if "---" in content:
                        content = content.split("---")[0].strip()
                    if "Или чуть иначе:" in content:
                        content = content.split("Или чуть иначе:")[0].strip()
                    if "Вот вариант:" in content:
                        content = content.split("Вот вариант:")[1].strip() if "Вот вариант:" in content else content
                    
                    print('✅ Пост успешно сгенерирован')
                    return content
                else:
                    text = await response.text()
                    print(f'❌ Ошибка DeepSeek: {response.status} - {text}')
                    # Если DeepSeek не работает - не отправляем пост
                    return None
    except Exception as e:
        print(f'❌ Ошибка при запросе к DeepSeek: {e}')
        return None

# ============================================
# ПУБЛИКАЦИЯ НОВОСТЕЙ
# ============================================
async def publish_news():
    """
    Основная функция: собирает новости, генерирует пост, отправляет в Telegram.
    """
    print('📰 publish_news() стартовал')
    
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
    
    print(f'📝 Сгенерированный пост:\n{post_text[:200]}...')
    
    # Отправляем в Telegram
    try:
        await bot.send_message(TELEGRAM_CHANNEL_ID, post_text, parse_mode="Markdown")
        print('✅ Пост успешно отправлен в канал')
    except Exception as e:
        print(f'❌ Ошибка при отправке поста: {e}')
        # Пробуем отправить без Markdown
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
    Выполняется при старте бота: настраивает расписание.
    """
    print('🚀 Бот запускается...')
    
    # Настройка расписания
    scheduler = AsyncIOScheduler()
    
    # Утренний выпуск в 9:00
    scheduler.add_job(
        publish_news,
        'cron', 
        hour=9, 
        minute=0,
        id='morning_news'
    )
    
    # Дневной выпуск в 14:00
    scheduler.add_job(
        publish_news,
        'cron', 
        hour=14, 
        minute=0,
        id='afternoon_news'
    )
    
    # Вечерний выпуск в 18:00
    scheduler.add_job(
        publish_news,
        'cron', 
        hour=18, 
        minute=0,
        id='evening_news'
    )
    
    scheduler.start()
    print('⏰ Расписание установлено: 9:00, 14:00 и 18:00 ежедневно')
    print("✅ Бот готов к работе (посты только по реальным новостям)")

# ============================================
# ТОЧКА ВХОДА
# ============================================
async def main():
    await on_startup()
    # Держим event loop живым
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())