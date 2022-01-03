from .exceptions import SolverError
from flask import Flask, request
from queue import Queue, Empty
import threading
import subprocess
import logging
import os

os.environ["WERKZEUG_RUN_MAIN"] = "true"
logging.getLogger("werkzeug").disabled = True

class ArkoseSelfSolver:
    def __init__(self,
        public_key: str,
        service_url: str,
        page_url: str = None,
        page_title: str = None,
        history_length: int = 1,
        port: int = 5532
    ):
        self._public_key = public_key
        self._service_url = service_url
        self._page_url = page_url
        self._page_title = page_title
        self._history_length = history_length
        self._port_num = port
        self._token_queue = Queue()
        self._start_server()

    def launch_browser(self):
        subprocess.Popen([
            "start",
            "",
            f"{self.get_url()}/"],
            shell=True)

    def get_url(self):
        return f"http://127.0.0.1:{self._port_num}"

    def put_token(self, token):
        self._token_queue.put(token)

    def get_token(self):
        try:
            token = self._token_queue.get(True, timeout=30)
            return token
        except Empty:
            raise SolverError

    def _start_server(self):
        app = Flask("SelfSolver")

        @app.route("/")
        def index():
            return """
            <br/>
            <button onclick="reloadCaptcha()">Reload</button>

            <script>
                let f
                function reloadCaptcha() {
                    if (history.length > 15) {
                        window.open(location.href)
                        window.close()
                        return
                    }
                    if (!f) {
                        f = document.createElement("iframe")
                        f.id = "captchaFrame"
                        f.style = "height: 350px; width: 350px; border: none;"
                        document.body.prepend(f)
                    }
                    f.src = "/captcha"
                }
                window.addEventListener("message", e => {
                    if (e.data == "reload") {
                        reloadCaptcha()
                    }
                })
                reloadCaptcha()
            </script>
            """

        @app.route("/send-token", methods=["POST"])
        def submit_token():
            token = request.get_json()["token"]
            self._token_queue.put(token)
            return ""

        @app.route("/captcha")
        def present_captcha():
            return """
                <div id="CAPTCHA"></div>
                <iframe
                    src="https://iframe.arkoselabs.com/{public_key}/index.html?mkt=en"
                    sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
                    style="display: none"
                    id="enforcementFrame"
                    title="Making sure you're human"
                ></iframe>

                <script>
                    let f = document.getElementById("enforcementFrame")

                    async function submitToken(token) {
                        await fetch("/send-token", {
                            method: "POST",
                            headers: {"content-type": "application/json"},
                            body: JSON.stringify({token: token})
                        })
                        top.postMessage("reload", "*")
                    }
                    
                    function changeFrameSize(data) {
                        f.style = `height: ${data.frameHeight}px; width: ${data.frameWidth}px; border: none;`
                    }
                    
                    window.addEventListener("message", e => {
                        let data = JSON.parse(e.data)
                        if (data.eventId == "challenge-complete") {
                            submitToken(data.payload.sessionToken)
                        } else if (data.eventId == "challenge-loaded") {
                            changeFrameSize(data.payload)
                        } else if (data.eventId == "challenge-iframeSize") {
                            changeFrameSize(data.payload)
                        }
                    }, false)
                </script>
                """ \
                .replace("{public_key}", self._public_key)

        threading.Thread(
            target=app.run,
            kwargs={"host": "0.0.0.0", "port": self._port_num}
            ).start()