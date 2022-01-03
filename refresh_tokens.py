from core.microsoft import MicrosoftClient, MicrosoftError
import itertools
import random
import threading
import pickle
import glob
import json
import os

thread_count = 500
queue = []
write_lock = threading.Lock()

with open("data/config.json") as fp:
    config = json.load(fp)

for fpath in glob.glob("data/microsoft/*.p"):
    with open(fpath, "rb") as fp:
        queue.append((fpath, pickle.load(fp)))
    
total_count = len(queue)
check_counter = 0
dead_counter = 0

if not os.path.exists("data/microsoft/dead"):
    os.mkdir("data/microsoft/dead")

with open("data/proxies.txt") as fp:
    proxy_list = fp.read().splitlines()
    random.shuffle(proxy_list)
    proxy_index = itertools.count(0)

if os.path.exists("data/tokens.txt"):
    os.remove("data/tokens.txt")

def update_stats():
    print(f"{check_counter:,} / {total_count:,} ({dead_counter:,} dead)", end="\r")

def thread_func():
    global check_counter
    global dead_counter
    global total_count

    while queue:
        fpath, item = queue.pop(0)
        proxy_url = "http://" + proxy_list[next(proxy_index) % len(proxy_list)]
        print(proxy_url)
        ms_client = item["client"]
        ms_client._rs.proxies.update({
            "http": proxy_url,
            "https": proxy_url
        })
        
        try:
            oauth_code = ms_client.oauth_authorize(
                config["client"]["id"],
                config["client"]["redirectUri"]
            )
            access_token = ms_client._request(
                method="POST",
                url="https://login.live.com/oauth20_token.srf",
                data={
                    "client_id": config["client"]["id"],
                    "client_secret": config["client"]["secret"],
                    "code": oauth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config["client"]["redirectUri"]
                }
            ).json()["access_token"]
            xbl_auth = ms_client._request(
                method="POST",
                url="https://user.auth.xboxlive.com/user/authenticate",
                headers={"Accept": "application/json"},
                json={
                "RelyingParty": "http://auth.xboxlive.com",
                    "TokenType": "JWT",
                    "Properties": {
                        "AuthMethod": "RPS",
                        "SiteName": "user.auth.xboxlive.com",
                        "RpsTicket": "d=" + access_token,
                    }
                }
            ).json()
            roblox_auth = ms_client._request(
                method="POST",
                url="https://xsts.auth.xboxlive.com/xsts/authorize",
                headers={"Accept": "application/json"},
                json={
                    "Properties": {
                        "SandboxId": "RETAIL",
                        "UserTokens": [
                            xbl_auth["Token"]
                        ]
                    },
                    "RelyingParty": "rp://auth.roblox.com/",
                    "TokenType": "JWT"
                }
            ).json()

            if not "DisplayClaims" in roblox_auth:
                total_count -= 1
                dead_counter += 1
                print(f"Could not obtain token for {item['member_name']}")
                update_stats()
                os.rename(fpath, fpath.replace("outlook/", "outlook/dead/"))
                continue
            
            token = "XBL3.0 x=%s;%s" % (
                roblox_auth["DisplayClaims"]["xui"][0]["uhs"],
                roblox_auth["Token"]
            )
            print(f"Refreshed token for {item['member_name']}")
            with write_lock:
                with open("data/tokens.txt", "a") as fp:
                    fp.write(token + "\n")
            check_counter += 1
            update_stats()

        except Exception as err:
            print(f"Error while refreshing {item['member_name']}: {err!r}")
            update_stats()
            queue.append((fpath, item))

threads = [
    threading.Thread(target=thread_func)
    for _ in range(thread_count)
]
for thread in threads: thread.start()