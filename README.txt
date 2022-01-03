Requirements:
- Python 3.9.7 or later: https://www.python.org/downloads/
- Nodejs: https://nodejs.org/ (LTS)
- HTTP proxies (ip:port, user:pass@ip:port or ip:port:user:pass)

Setup python modules:
- Run install_modules.bat

Setup proxies:
- Place your list of HTTP proxies in the data/proxies.txt file

Setup microsoft app:
- Browse to https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
- Press the "New registration" button
- Fill in the following info
-   Name: anything
-   Supported account types: Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)
-   Redirect URI: (Web) http://localhost/
- Press the "Register" button
-----------------------------
- Open setup_app.py
- For "Client ID":
-   Copy and paste the "Application (client) ID" field on the page
- For "Client Secret":
-   Navigate to the "Certificates & secrets" tab on the page
-   Click "New client secret", then "Add"
-   Copy and paste the "Value" field of the created token

Generate microsoft accounts:
- Open microsoft_gen.py
- Solve captchas. Each solve gives you one MS account, increasing your checking capacity by about 20 an hour.

Refresh tokens:
Tokens need to be refreshed once per 24 hours, or after MS account additions.
- Open refresh_tokens.py

Setup combos:
- Place your list of USER/EMAIL:PASS combos in the data/combos.txt file

Cracking:
- Run cracker.py. Hits will be logged into the output folder.

Filter unverified accounts:
filter_unverified.py allows you to get rid of most verified Roblox accounts, which'd be 2fa-prompted anyway.