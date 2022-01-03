import json

config = {"client": {}}

try:
    with open("data/config.json", "rb") as fp:
        config = json.load(fp)
except:
    pass

config["client"]["id"] = input("Client ID: ").strip()
config["client"]["secret"] = input("Client Secret: ").strip()
config["client"]["redirectUri"] = "http://localhost/"

with open("data/config.json", "w") as fp:
    json.dump(config, fp)

input("Saved! Press enter to exit ..")