from .. import chrome
from .utils import encrypt_cipher, find_inbetween, iso_date
from .exceptions import MicrosoftError
from urllib.parse import urlparse
from socket import gethostbyname
import json as jsonlib
import requests

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning)

class MicrosoftClient:
    _rs: requests.Session

    def __init__(self,
        proxy_url: str = None,
        timeout: tuple = (5, 120)
    ):
        self._rs = requests.Session()
        self._rs.timeout = timeout
        self._rs.verify = False
        self._rs.proxies.update({
            "http": proxy_url,
            "https": proxy_url
        })

    def __enter__(self):
        return self
    
    def __exit__(self, *_):
        self._rs.close()

    def oauth_authorize(self, client_id, redirect_uri):
        oauth_url = f"https://login.live.com/oauth20_authorize.srf" \
                    f"?client_id={client_id}&response_type=code" \
                    f"&redirect_uri={redirect_uri}" \
                    f"&scope=XboxLive.signin%20XboxLive.offline_access"
        
        response = self._request(
            method="GET",
            url=oauth_url,
            headers={"User-Agent": chrome.user_agent},
            allow_redirects=False
        )

        if "/Consent/Update" in response.text:
            url = find_inbetween(response.text, 'action="', '"')
            rd = find_inbetween(response.text, 'id="rd" value="', '"')
            ipt = find_inbetween(response.text, 'id="ipt" value="', '"')
            pprid = find_inbetween(response.text, 'id="pprid" value="', '"')
            uaid = find_inbetween(response.text, 'id="uaid" value="', '"')
            _client_id = find_inbetween(response.text, 'id="client_id" value="', '"')
            scope = find_inbetween(response.text, 'id="scope" value="', '"')

            response = self._request(
                method="POST",
                url=url,
                headers={"User-Agent": chrome.user_agent},
                data={
                    "rd": rd,
                    "ipt": ipt,
                    "pprid": pprid,
                    "uaid": uaid,
                    "client_id": _client_id,
                    "scope": scope
                })
            canary = find_inbetween(response.text, 'name="canary" value="', '"')

            response = self._request(
                method="POST",
                url=url,
                headers={"User-Agent": chrome.user_agent},
                data={
                    "canary": canary,
                    "client_id": _client_id,
                    "scope": scope,
                    "cscope": "",
                    "ucaccept": "Yes"
                },
                allow_redirects=False)

        if not "location" in response.headers:
            raise MicrosoftError(9999)

        if response.headers["location"].startswith("https://login.live.com/oauth20_authorize.srf"):
            final_url = self._request(
                method="GET",
                url=response.headers["location"],
                headers={"User-Agent": chrome.user_agent},
                allow_redirects=False
            ).headers["location"]
            
        else:
            final_url = response.headers["location"]
        
        return final_url \
            .split("code=", 1)[1] \
            .split("&", 1)[0] \
            .split("#", 1)[0]

    def create_xbox_account(self):
        response = self._request(
            method="GET",
            url="https://account.xbox.com/en-US/auth/getTokensSilently" \
                "?rp=http%3A%2F%2Fxboxlive.com,http%3A%2F%2Fmp.microsoft.com%2F," \
                "http%3A%2F%2Fgssv.xboxlive.com%2F,rp%3A%2F%2Fgswp.xboxlive.com%2F",
            headers={
                "User-Agent": chrome.user_agent
            })
        response.raise_for_status()
        token = response.headers["set-cookie"].split("token=", 1)[1].split(";", 1)[0]
        
        response = self._request(
            method="GET",
            url="https://account.xbox.com/sk-sk/accountcreation?rtc=1"
        )
        url = find_inbetween(response.text, 'action="', '"')
        pprid = find_inbetween(response.text, 'id="pprid" value="', '"')
        nap = find_inbetween(response.text, 'id="NAP" value="', '"')
        anon = find_inbetween(response.text, 'id="ANON" value="', '"')
        t = find_inbetween(response.text, 'id="t" value="', '"')

        response = self._request(
            method="POST",
            url=url,
            headers={
                "User-Agent": chrome.user_agent
            },
            data={
                "pprid": pprid,
                "NAP": nap,
                "ANON": anon,
                "t": t
            }
        )
        response.raise_for_status()

        try:
            response2 = self._request(
                method="POST",
                url="https://account.xbox.com/en-us/xbox/account/api/v1/accountscreation/CreateXboxLiveAccount",
                headers={
                    "Connection": "keep-alive",
                    "User-Agent": chrome.user_agent,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "sec-ch-ua-platform": '"Windows"',
                    "Origin": "https://account.xbox.com",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "__RequestVerificationToken": token,
                    "Sec-Fetch-Dest": "empty",
                    "Referer": "https://account.xbox.com/en-us/accountcreation",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-US,en;q=0.9"
                },
                data="partnerOptInChoice=false&msftOptInChoice=false&isChild=false&returnUrl=",
                timeout=5
            )
            response2.raise_for_status()
        except requests.Timeout:
            pass

    def create_account(self,
        member_name: str,
        password: str,
        first_name: str,
        last_name: str,
        birth_date: tuple,
        country_code: str = None,
        error_data: dict = None,
        captcha_data: dict = None,
        context_data: dict = None
    ):
        if not error_data: error_data = {}
        if not context_data:
            response = self._request(
                method="GET",
                url="https://signup.live.com/signup",
                headers={
                    "Connection": "keep-alive",
                    "sec-ch-ua": f'" Not A;Brand";v="{chrome.version}", "Chromium";v="{chrome.version}", "Google Chrome";v="{chrome.version}"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                    "User-Agent": chrome.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            context_data = {
                "uaid": find_inbetween(response.text, '"uaid":"', '"'),
                "tcxt": find_inbetween(response.text, '"tcxt":', "}", True),
                "scid": find_inbetween(response.text, '"scid":', ","),
                "canary": find_inbetween(response.text, '"apiCanary":', ",", True),
                "ski": find_inbetween(response.text, 'var SKI="', '"'),
                "cipher_key": find_inbetween(response.text, 'var Key="', '"'),
                "random_num": find_inbetween(response.text, 'var randomNum="', '"'),
                "site_id": find_inbetween(response.text, '"siteId":"', '"'),
                "fid": find_inbetween(response.text, '"fid":"', '"'),
                "hpgid": 200650,
                "uiflvr": 1001,
                "referrer_url": response.url.replace(gethostbyname("signup.live.com"), "signup.live.com"),
                "country_code": country_code or find_inbetween(response.text, '"country":"', '"')
            }

        response2 = self._request(
            method="POST",
            url=f"https://signup.live.com/API/CreateAccount?lic=1&uaid={context_data['uaid']}",
            headers={
                "Connection": "keep-alive",
                "x-ms-apiVersion": "2",
                "uaid": context_data["uaid"],
                "DNT": "1",
                "sec-ch-ua-mobile": "?0",
                "User-Agent": chrome.user_agent,
                "canary": context_data["canary"],
                "Content-Type": "application/json",
                "hpgid": str(context_data["hpgid"]),
                "Accept": "application/json",
                "tcxt": context_data["tcxt"],
                "uiflvr": str(context_data["uiflvr"]),
                "scid": context_data["scid"],
                "sec-ch-ua": f'" Not A;Brand";v="{chrome.version}", "Chromium";v="{chrome.version}", "Google Chrome";v="{chrome.version}"',
                "x-ms-apiTransport": "xhr",
                "sec-ch-ua-platform": '"Windows"',
                "Origin": "https://signup.live.com",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": context_data["referrer_url"],
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9"
            },
            data=jsonlib.dumps({
                "RequestTimeStamp": iso_date(),
                "MemberName": member_name,
                "CheckAvailStateMap": [f"{member_name}:undefined"],
                "EvictionWarningShown": [],
                "UpgradeFlowToken": {},
                "FirstName": first_name,
                "LastName": last_name,
                "MemberNameChangeCount": 1,
                "MemberNameAvailableCount": 1,
                "MemberNameUnavailableCount": 0,
                "CipherValue": encrypt_cipher(
                    password,
                    random_num=context_data["random_num"],
                    ski=context_data["ski"],
                    cipher_key=context_data["cipher_key"]),
                "SKI": context_data["ski"],
                "BirthDate": f"{birth_date[2]:02d}:{birth_date[1]:02d}:{birth_date[0]}",
                "Country": context_data["country_code"],
                "IsOptOutEmailDefault": False,
                "IsOptOutEmailShown": True,
                "IsOptOutEmail": False,
                "LW": True,
                "SiteId": context_data["site_id"],
                "IsRDM": 0,
                "WReply": None,
                "ReturnUrl": None,
                "SignupReturnUrl": None,
                "uiflvr": int(context_data["uiflvr"]),
                "uaid": context_data["uaid"],
                "SuggestedAccountType": "EASI",
                "SuggestionType": "Prefer",
                "HFId": context_data["fid"],
                "encAttemptToken": error_data.get("encAttemptToken", ""),
                "dfpRequestId": error_data.get("dfpRequestId", ""),
                "scid": int(context_data["scid"]),
                "hpgid": int(context_data["hpgid"]),
                **({
                    "HType": captcha_data["type"],
                    "HSol": captcha_data["solution"],
                    "HPId": captcha_data["id"]
                } if captcha_data else {})
            }, separators=(",", ":"))
        )
        signup_data = response2.json()

        if (err := signup_data.get("error")):
            if err["code"] == "1041":
                context_data["hpgid"] = 201040
            raise MicrosoftError(
                code=err["code"],
                data=err.get("data"),
                context=context_data)
                
        response3 = self._request(
            method="POST",
            url=signup_data["redirectUrl"],
            headers={
                "Connection": "keep-alive",
                "DNT": "1",
                "sec-ch-ua-mobile": "?0",
                "User-Agent": chrome.user_agent,
                "Accept": "application/json",
                "sec-ch-ua": f'" Not A;Brand";v="{chrome.version}", "Chromium";v="{chrome.version}", "Google Chrome";v="{chrome.version}"',
                "sec-ch-ua-platform": '"Windows"',
                "Origin": "https://signup.live.com",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Referer": "https://signup.live.com/",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9"
            },
            data={
                "slt": signup_data["slt"]
            }
        )
        response3.raise_for_status()

        url_post = find_inbetween(response3.text, "urlPost:'", "'")
        ppft = find_inbetween(response3.text, "sFT:'", "'")

        response4 = self._request(
            method="POST",
            url=url_post,
            headers={
                "Connection": "keep-alive",
                "DNT": "1",
                "sec-ch-ua-mobile": "?0",
                "User-Agent": chrome.user_agent,
                "Accept": "application/json",
                "sec-ch-ua": f'" Not A;Brand";v="{chrome.version}", "Chromium";v="{chrome.version}", "Google Chrome";v="{chrome.version}"',
                "sec-ch-ua-platform": '"Windows"',
                "Origin": "https://login.live.com",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Referer": response3.url,
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9"
            },
            data={
                "LoginOptions": "1",
                "type": "28",
                "ctx": "",
                "hpgrequestid": "",
                "PPFT": ppft,
                "i19": "1997"
            }
        )
        response4.raise_for_status()
        
        return signup_data

    def _request(self,
        method: str,
        url: str,
        headers: dict = {},
        allow_redirects = True,
        _retry = None,
        **kwargs
    ) -> requests.Response:
        _retry = _retry or 0
        hostname = urlparse(url).hostname
        host = gethostbyname(hostname)

        url = url.replace(hostname, host, 1)
        headers["Host"] = hostname

        try:
            response = self._rs.request(
                method=method,
                url=url,
                headers=headers,
                allow_redirects=False,
                **kwargs)
        except requests.exceptions.ProxyError:
            if _retry > 1:
                raise
            return self._request(
                method, url, headers, allow_redirects, _retry=_retry+1, **kwargs)

        if allow_redirects and response.status_code in (301, 302):
            return self._request(
                method, response.headers["location"], headers, **kwargs)

        return response