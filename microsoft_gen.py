from core.microsoft import MicrosoftClient, MicrosoftError
from core.solvers import ArkoseSelfSolver, SolverError
from random import choice, choices, randint
import string
import json
import itertools
import os
import random
import pickle
import threading

thread_count = 5

with open("data/config.json") as fp:
    config = json.load(fp)

with open("data/proxies.txt") as fp:
    proxy_list = fp.read().splitlines()
    random.shuffle(proxy_list)
    proxy_index = itertools.count(0)

with open("data/lists/first_names.txt") as fp:
    fname_list = fp.read().splitlines()

with open("data/lists/last_names.txt") as fp:
    lname_list = fp.read().splitlines()

if not os.path.isdir("data/microsoft"):
    os.mkdir("data/microsoft")

solver = ArkoseSelfSolver(
    public_key="B7D8911C-5CC8-A9A3-35B0-554ACEE604DA",
    service_url="https://client-api.arkoselabs.com",
    page_url="https://iframe.arkoselabs.com/B7D8911C-5CC8-A9A3-35B0-554ACEE604DA/index.html?mkt=en",
    page_title="Authentication",
    history_length=9)
solver.launch_browser()

def create_account():
    proxy_url = "http://" + proxy_list[next(proxy_index) % len(proxy_list)]
    ms_client = MicrosoftClient(proxy_url)
    token = None

    member_name = "".join(choices(
        string.ascii_lowercase,
        k=randint(10, 16))) + "@outlook.com"
    password = "".join(choices(
        string.ascii_letters + string.digits,
        k=randint(16, 32)))
    first_name = choice(fname_list)
    last_name = choice(lname_list)
    birth_date = (
        randint(1990, 2000),
        randint(1, 12),
        randint(1, 28))
    filename = member_name \
        .replace("@", "-") \
        .replace(".", "-") \
        + ".p"

    error_data = captcha_data = context_data = None
    for retry_num in range(2):
        try:
            ms_client.create_account(
                member_name=member_name,
                password=password,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                error_data=error_data,
                captcha_data=captcha_data,
                context_data=context_data
            )
            ms_client.create_xbox_account()

            with open("data/microsoft/" + filename, "wb") as fp:
                pickle.dump({
                    "client": ms_client,
                    "member_name": member_name,
                    "password": password,
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": birth_date
                }, fp)

            print(f"[success] {member_name}")
            break

        except MicrosoftError as err:
            if err.code != "1041":
                if retry_num != 0:
                    if err.code == "1043":
                        print(f"[abort] invalid token - {member_name}")
                    else:
                        print(f"[abort] error: {err.code} - {member_name}")
                        if token: solver.put_token(token)
                break
            
            try:
                token = solver.get_token()
            except SolverError:
                break

            error_data = json.loads(err.data)
            context_data = err.context
            captcha_data = {
                "type": "enforcement",
                "id": "B7D8911C-5CC8-A9A3-35B0-554ACEE604DA",
                "solution": token
            }
            print(f"[queued] {member_name}")

def thread_func():
    while True:
        try:
            create_account()
        except Exception as err:
            print(f"Thread error: {err!r}")

threads = [
    threading.Thread(target=thread_func)
    for _ in range(thread_count)
]
for thread in threads: thread.start()