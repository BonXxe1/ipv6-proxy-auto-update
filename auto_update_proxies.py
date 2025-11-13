import requests
import time
import re
import json
from collections import defaultdict
import random

# 指定国家
countries = ['US', 'JP', 'KR', 'SG', 'TW', 'HK']

# 多源配置（GitHub raw + API）
sources = [
    # GitHub raw
    {'name': 'proxifly', 'url': 'https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt', 'format': 'ip_port_country', 'type': 'txt'},
    {'name': 'TheSpeedX', 'url': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt', 'format': 'ip_port', 'type': 'txt'},
    {'name': 'vakhov', 'url': 'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/main/proxies/http.txt', 'format': 'ip_port', 'type': 'txt'},
    {'name': 'jetkai', 'url': 'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt', 'format': 'ip_port', 'type': 'txt'},
    {'name': 'gfpcom', 'url': 'https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/proxies/http.txt', 'format': 'ip_port', 'type': 'txt'},
    # API (动态国家)
    {'name': 'proxyscrape', 'base_url': 'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&anonymity=elite', 'format': 'ip_port', 'type': 'api'},
    {'name': 'pubproxy', 'base_url': 'http://pubproxy.com/api/proxy?limit=10&type=http', 'format': 'json_ip_port_country', 'type': 'api'},
    {'name': 'proxylister', 'base_url': 'https://proxylister.com/api/proxies?protocol=https&anonymity=elite&limit=10', 'format': 'json_ip_port', 'type': 'api'},
    {'name': 'getproxylist', 'base_url': 'https://api.getproxylist.com/proxy?protocol[]=http&anonLevel[]=1&limit=10', 'format': 'json_ip_port', 'type': 'api'},
    {'name': 'free-proxy-list.net', 'url': 'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&simplified=true', 'format': 'ip_port', 'type': 'txt'},  # 代理API
]

def fetch_from_source(source, country=None):
    """从单个源拉取代理"""
    proxies = []
    try:
        if source['type'] == 'txt':
            resp = requests.get(source['url'], timeout=10)
            if resp.status_code == 200:
                lines = resp.text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        if source['format'] == 'ip_port_country' and '#' in line:
                            parts = line.split('#')
                            if len(parts) == 2 and parts[1].strip() in countries:
                                proxies.append(f"{parts[0].strip()}#{parts[1].strip()}")
                        elif source['format'] == 'ip_port':
                            proxies.append(f"{line.strip()}#{country or 'US'}")  # 默认US或指定
        elif source['type'] == 'api':
            url = source['base_url'] + (f"&country={country}" if country else "")
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                if 'json' in source['format']:
                    data = resp.json()
                    for item in data.get('data', data.get('proxies', [])):
                        ip_port = f"{item.get('ip', item.get('ipPort', '')) or ''}:{item.get('port', '')}"
                        country_code = item.get('country', 'US')
                        if ':' in ip_port and country_code in countries:
                            proxies.append(f"{ip_port}#{country_code}")
                else:
                    # TXT API
                    lines = resp.text.strip().split('\n')
                    for line in lines:
                        if ':' in line:
                            proxies.append(f"{line.strip()}#{country or 'US'}")
        print(f"从 {source['name']} 拉取 {len(proxies)} 个代理")
    except Exception as e:
        print(f"{source['name']} 拉取失败: {e}")
    return proxies

def test_proxy(proxy_str):
    """测试连通性"""
    parts = proxy_str.split('#')
    proxy_addr = parts[0]
    proxy_dict = {'http': f'http://{proxy_addr}', 'https': f'http://{proxy_addr}'}
    start_time = time.time()
    try:
        resp = requests.get('https://httpbin.org/ip', proxies=proxy_dict, timeout=10)
        delay = round(time.time() - start_time, 2)
        return resp.status_code == 200 and delay < 5
    except:
        return False

# 主流程
print("开始多源代理拉取与测试...")
all_proxies = []
for country in countries:
    for source in sources:
        new_proxies = fetch_from_source(source, country)
        all_proxies.extend(new_proxies[:10])  # 每个源/国家限10个

# 去重 + 随机
unique_proxies = list(dict.fromkeys(all_proxies))[:100]
random.shuffle(unique_proxies)
print(f"总独特代理: {len(unique_proxies)}")

# 测试连通性
success_proxies = []
for proxy in unique_proxies:
    if test_proxy(proxy):
        success_proxies.append(proxy)
    time.sleep(0.5)  # 限速

# 写入成功文件
with open('proxies_success.txt', 'w') as f:
    for proxy in success_proxies:
        f.write(proxy + '\n')

print(f"成功代理: {len(success_proxies)} | 写入 proxies_success.txt")
stats = defaultdict(int)
for p in success_proxies:
    stats[p.split('#')[1]] += 1
print("国家统计:", dict(stats))
