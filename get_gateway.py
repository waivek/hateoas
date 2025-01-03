from requests_ip_rotator import ApiGateway
from waivek import read, write, rel2abs
import os
import furl

def get_cache_path():
    return rel2abs("data/gateway_cache.json")

def get_gateway_with_caching(domain):
    cache_path = get_cache_path()
    if not os.path.exists(cache_path) or os.path.getsize(cache_path) == 0:
        write({}, cache_path)
    cache_D = read(cache_path)

    gateway = ApiGateway(domain)

    if domain in cache_D:
        endpoints = cache_D[domain]
        gateway.start(endpoints=endpoints)
    else:
        returned_endpoints = gateway.start()
        cache_D[domain] = returned_endpoints
        write(cache_D, cache_path)

    return gateway

def url_to_domain(url):
    f = furl.furl(url)
    return f.origin

def get_anonymous_session(url):
    import requests
    import rich
    domain = url_to_domain(url)
    gateway = get_gateway_with_caching(domain)
    session = requests.Session()
    session.mount(domain, gateway)
    rich.print("[black on yellow bold] WARNING [/] Using AWS API Gateway. Be mindful of costs.")
    return session
