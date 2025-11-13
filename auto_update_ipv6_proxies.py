import requests
import time
import random
from collections import defaultdict
import sys
import signal
import os

# 信号处理：优雅中断
def signal_handler(sig, frame):
    print("收到中断信号，强制写入文件...")
    with open('proxies_success.txt', 'w') as f:
        f.write("操作被取消 - 可能超时或runner中断\n")
    sys.exit(1)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# 指定国家
countries = ['US', 'JP', 'KR', 'SG', 'TW', 'HK']

# 简化源（10个，优先Cloudflare）
sources = [
    {'name': 'prxchk_socks5_ipv6', 'url': 'https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
    {'name': 'cloudflare_ips_v6', 'url': 'https://www.cloudflare.com/ips-v6/', 'format': 'cidr_list', 'type': 'txt', 'protocol': 'http'},
    {'name': 'davie3_cf_ipv6', 'url': 'https://raw.githubusercontent.com/Davie3/mikrotik-cloudflare-iplist/main/cloudflare-ips-v6.rsc', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
    {'name': 'ircfspace_cf_ips', 'url': 'https://raw.githubusercontent.com/ircfspace/cf-ip-ranges/main/cloudflare-ipv6.json', 'format': 'json_cidr', 'type': 'json', 'protocol': 'http'},
    {'name': 'proxyscrape_socks5_ipv6', 'base_url': 'https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&anonymity=elite', 'format': 'ip_port', 'type': 'api', 'protocol': 'socks5'},
    {'name': 'pubproxy_socks5_ipv6', 'base_url': 'http://pubproxy.com/api/proxy?limit=10&type=socks5', 'format': 'json_ip_port_country', 'type': 'api', 'protocol': 'socks5'},
    {'name': 'getproxylist_socks5_ipv6', 'base_url': 'https://api.getproxylist.com/proxy?protocol[]=socks5&country[]=US&anonLevel[]=1&limit=10', 'format': 'json_ip_port', 'type': 'api', 'protocol': 'socks5'},
    {'name': 'TheSpeedX_socks5_ipv6', 'url': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
    {'name': 'jetkai_socks5_ipv6', 'url': 'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
    {'name': 'gfpcom_socks5_ipv6', 'url': 'https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/proxies/socks5.txt', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
]

def is_ipv6(ip):
    try:
        from ipaddress import IPv6Address
        IPv6Address(ip)
        return True
    except:
        return False

def fetch_from_source(source, country=None, retries=3):
    proxies = []
    for attempt in range(retries):
        try:
            resp = requests.get(source.get('url', source['base_url'] + (f"&country={country}" if country else "")), timeout=10)  # 缩短超时
            if resp.status_code == 200:
                # 简化处理：假设TXT格式，过滤IPv6
                lines = resp.text.strip().split('\n')
                count = 0
                for line in lines[:10]:  # 限10行
                    ip_port = line.strip()
                    if ':' in ip_port:
                        ip = ip_port.split(':')[0]
                        if is_ipv6(ip):
                            proxies.append(f"{ip_port}#{country or 'US'}#{source['protocol']}")
                            count += 1
                print(f"从 {source['name']} 拉取 {count} 个IPv6代理 (尝试 {attempt+1})")
                break
            else:
                print(f"{source['name']} 状态码: {resp.status_code}")
        except Exception as e:
            print(f"{source['name']} 尝试 {attempt+1} 失败: {e}")
            if attempt == retries - 1:
                print(f"{source['name']} 所有重试失败")
    return proxies

def test_proxy(proxy_str):
    try:
        parts = proxy_str.split('#')
        proxy_addr = parts[0]
        protocol = parts[2] if len(parts) > 2 else 'http'
        proxy_dict = {'http': f"{protocol}://{proxy_addr}", 'https': f"{protocol}://{proxy_addr}"}
        start_time = time.time()
        resp = requests.get('https://httpbin.org/ip', proxies=proxy_dict, timeout=10)
        delay = round(time.time() - start_time, 2)
        return resp.status_code == 200 and delay < 10, delay
    except Exception as e:
        delay = round(time.time() - start_time if 'start_time' in locals() else 0, 2)
        return False, delay

# 主流程
print("开始多源IPv6代理拉取与测试 (2025-11-13)...")
all_proxies = []
for country in countries:
    for source in sources:
        new_proxies = fetch_from_source(source, country)
        all_proxies.extend(new_proxies[:3])  # 减少数量

unique_proxies = list(dict.fromkeys(all_proxies))[:30]  # 减少测试数量
random.shuffle(unique_proxies)
print(f"总独特IPv6代理: {len(unique_proxies)}")

success_proxies = []
stats = defaultdict(int)
for proxy in unique_proxies:
    success, delay = test_proxy(proxy)
    if success:
        success_proxies.append(proxy)
        stats[proxy.split('#')[1]] += 1
    print(f"测试 {proxy} - {'成功' if success else '失败'} (延迟: {delay}s)")
    time.sleep(0.3)  # 缩短间隔

with open('proxies_success.txt', 'w') as f:
    if success_proxies:
        for proxy in success_proxies:
            f.write(proxy + '\n')
        print(f"写入 {len(success_proxies)} 个成功IPv6代理")
    else:
        f.write("无可用IPv6代理 - 操作可能被取消\n")
        print("警告: 无成功代理")

print(f"成功IPv6代理: {len(success_proxies)} | 已写入 proxies_success.txt")
print("国家统计:", dict(stats))
