import requests
import time
import re
import json
import random
from collections import defaultdict
import sys
import traceback  # 调试

try:
    import ipaddress
except ImportError:
    print("ipaddress not found - installing via pip failed?")
    sys.exit(1)

# 指定国家
countries = ['US', 'JP', 'KR', 'SG', 'TW', 'HK']

# 18个源（含Cloudflare）
sources = [
    # 原15个 + 3个Cloudflare（保持简略）
    {'name': 'prxchk_socks5_ipv6', 'url': 'https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
    # ... (其他14个源，省略以节省空间 - 使用之前完整列表)
    {'name': 'cloudflare_ips_v6', 'url': 'https://www.cloudflare.com/ips-v6/', 'format': 'cidr_list', 'type': 'txt', 'protocol': 'http'},
    {'name': 'davie3_cf_ipv6', 'url': 'https://raw.githubusercontent.com/Davie3/mikrotik-cloudflare-iplist/main/cloudflare-ips-v6.rsc', 'format': 'ip_port', 'type': 'txt', 'protocol': 'socks5'},
    {'name': 'ircfspace_cf_ips', 'url': 'https://raw.githubusercontent.com/ircfspace/cf-ip-ranges/main/cloudflare-ipv6.json', 'format': 'json_cidr', 'type': 'json', 'protocol': 'http'},
]

def is_ipv6(ip):
    try:
        ipaddress.IPv6Address(ip)
        return True
    except ipaddress.AddressValueError as e:
        print(f"IPv6验证失败: {e}")
        return False

def generate_random_ipv6_from_cidr(cidr):
    try:
        network = ipaddress.IPv6Network(cidr, strict=False)
        hosts = list(network.hosts())
        if hosts:
            random_ip = str(random.choice(hosts))
            return random_ip
        else:
            print(f"警告: CIDR {cidr} 无主机IP")
            return None
    except Exception as e:
        print(f"CIDR生成失败 {cidr}: {e}")
        return None

def fetch_from_source(source, country=None):
    proxies = []
    try:
        resp = requests.get(source['url'], timeout=15)
        if resp.status_code == 200:
            if 'cidr' in source['format']:
                # Cloudflare CIDR处理
                lines = resp.text.strip().split('\n')
                cidrs = []
                if source['format'] == 'json_cidr':
                    data = resp.json()
                    cidrs = data.get('ipv6_cidrs', [])
                else:
                    cidrs = [line.strip() for line in lines if '/' in line and ':' in line]
                count = 0
                for cidr in cidrs[:10]:  # 限10个
                    random_ip = generate_random_ipv6_from_cidr(cidr)
                    if random_ip:
                        port = random.randint(80, 1080)
                        ip_port = f"[{random_ip}]:{port}"
                        proxies.append(f"{ip_port}#{country or 'US'}#{source['protocol']}")
                        count += 1
                print(f"从 {source['name']} 解析 {count} 个Cloudflare IPv6代理")
            else:
                # 标准TXT/JSON处理（添加try-except）
                lines = resp.text.strip().split('\n')
                count = 0
                for line in lines[:20]:
                    try:
                        ip_port = line.strip()
                        ip = ip_port.split(':')[0]
                        if is_ipv6(ip):
                            proxies.append(f"{ip_port}#{country or 'US'}#{source['protocol']}")
                            count += 1
                    except Exception as e:
                        print(f"行解析失败: {line} - {e}")
                print(f"从 {source['name']} 拉取 {count} 个IPv6代理")
        else:
            print(f"{source['name']} 状态码: {resp.status_code}")
    except Exception as e:
        print(f"{source['name']} 拉取异常: {traceback.format_exc()}")
    return proxies

def test_proxy(proxy_str):
    try:
        parts = proxy_str.split('#')
        proxy_addr = parts[0]
        protocol = parts[2] if len(parts) > 2 else 'http'
        proxy_dict = {
            'http': f"{protocol}://{proxy_addr}",
            'https': f"{protocol}://{proxy_addr}"
        }
        start_time = time.time()
        resp = requests.get('https://httpbin.org/ip', proxies=proxy_dict, timeout=15)
        delay = round(time.time() - start_time, 2)
        return resp.status_code == 200 and delay < 10, delay
    except Exception as e:
        delay = round(time.time() - start_time if 'start_time' in locals() else 0, 2)
        print(f"测试异常 {proxy_str}: {e}")
        return False, delay

# 主流程（添加全局try-except）
try:
    print("开始多源IPv6代理拉取与测试 (2025-11-13，含Cloudflare)...")
    all_proxies = []
    for country in countries:
        for source in sources:
            new_proxies = fetch_from_source(source, country)
            all_proxies.extend(new_proxies[:5])

    unique_proxies = list(dict.fromkeys(all_proxies))[:60]
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
        time.sleep(0.5)

    with open('proxies_success.txt', 'w') as f:
        if success_proxies:
            for proxy in success_proxies:
                f.write(proxy + '\n')
            print(f"写入 {len(success_proxies)} 个成功IPv6代理")
        else:
            f.write("无可用IPv6代理 - 检查源或网络\n")
            print("警告: 无成功代理")

    print(f"成功IPv6代理: {len(success_proxies)} | 已写入 proxies_success.txt")
    print("国家统计:", dict(stats))
except Exception as e:
    print(f"主流程异常: {traceback.format_exc()}")
    with open('proxies_success.txt', 'w') as f:
        f.write(f"脚本整体失败: {str(e)}\n")
    sys.exit(1)  # 明确退出码
