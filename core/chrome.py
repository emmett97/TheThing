from http.client import HTTPSConnection
import json

def get_user_agent():
    conn = HTTPSConnection("jnrbsn.github.io")
    conn.request("GET", "/user-agents/user-agents.json")
    return json.loads(conn.getresponse().read())[0]

user_agent = get_user_agent()
version = user_agent \
    .split("Chrome/", 1)[1] \
    .split(".", 1)[0]