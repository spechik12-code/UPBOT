#!/usr/bin/env python3
"""
Утилиты для работы с прокси
"""
import requests
import random
import time
import logging
from config import PROXY_LIST, get_proxy, get_proxies_dict, PROXY_TIMEOUT

logger = logging.getLogger(__name__)

def test_proxy(proxy_url, test_url="https://43xgeorgia.me", timeout=10):
    """
    Протестировать прокси
    Возвращает (успех, время_ответа, статус_код, сообщение)
    """
    try:
        proxies = get_proxies_dict(proxy_url)
        start_time = time.time()
        
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Encoding": "gzip, deflate"
            },
            verify=False
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            content = response.text.lower()
            if any(block in content for block in ['ddos-guard', 'captcha', 'access denied']):
                return False, response_time, response.status_code, "blocked"
            return True, response_time, response.status_code, "working"
        else:
            return False, response_time, response.status_code, f"http_{response.status_code}"
            
    except requests.exceptions.ConnectTimeout:
        return False, timeout, 0, "connect_timeout"
    except requests.exceptions.ReadTimeout:
        return False, timeout, 0, "read_timeout"
    except requests.exceptions.ProxyError:
        return False, 0, 0, "proxy_error"
    except Exception as e:
        return False, 0, 0, f"error: {type(e).__name__}"

def health_check_proxies():
    """
    Проверить все прокси и вернуть рабочие
    """
    working_proxies = []
    
    logger.info("🔍 Проверка здоровья прокси...")
    for i, proxy in enumerate(PROXY_LIST, 1):
        logger.info(f"  {i}/{len(PROXY_LIST)}. Тестирую {proxy[:50]}...")
        
        success, resp_time, status, message = test_proxy(proxy, timeout=PROXY_TIMEOUT)
        
        if success:
            logger.info(f"    ✅ {resp_time:.2f}с")
            working_proxies.append({
                'url': proxy,
                'response_time': resp_time,
                'status': status
            })
        else:
            logger.info(f"    ❌ {message}")
        
        time.sleep(1)
    
    working_proxies.sort(key=lambda x: x['response_time'])
    
    logger.info(f"📊 Результат: {len(working_proxies)}/{len(PROXY_LIST)} прокси рабочие")
    
    if working_proxies:
        logger.info("🏆 Лучшие прокси:")
        for i, proxy_data in enumerate(working_proxies[:3], 1):
            logger.info(f"  {i}. {proxy_data['url'][:60]}... - {proxy_data['response_time']:.2f}с")
    
    return [p['url'] for p in working_proxies]

def get_working_proxy():
    """
    Получить рабочий прокси (с проверкой)
    """
    if not PROXY_LIST:
        return None
    
    proxy = get_proxy()
    success, _, _, _ = test_proxy(proxy, timeout=5)
    
    if success:
        return proxy
    
    working = health_check_proxies()
    
    if working:
        return random.choice(working)
    
    return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== ТЕСТ ПРОКСИ УТИЛИТ ===")
    
    if PROXY_LIST:
        print(f"Найдено прокси в конфиге: {len(PROXY_LIST)}")
        health_check_proxies()
    else:
        print("❌ Прокси не настроены в .env файле")
