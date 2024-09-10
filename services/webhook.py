# -*- coding:utf-8 -*-
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from sanic import Sanic
from sanic.log import logger
from sanic.worker.loader import AppLoader
from sanic_ext import Extend, Config

from core import settings
from core.application import BaseApplication
from core.console import console
from core.discover import autodiscover
from core.log import LOGGING_CONFIG_DEFAULTS
from core.utils import asyncio_utls

asyncio_utls.use_uvloop()


def create_app(app_name: str) -> Sanic:
    webhook_service.init()
    app = webhook_service.sanic_app
    return app


class WebhookService(BaseApplication):

    def __init__(self, app_name, pid_file_path=None, log_file_path=None, config=None):
        super().__init__(app_name, pid_file_path, log_file_path, config)
        self.log_config = LOGGING_CONFIG_DEFAULTS

    def init(self):
        self.sanic_app = Sanic(self.app_name, strict_slashes=True, log_config=self.log_config)
        Extend(self.sanic_app, config=Config(oas=False, oas_autodoc=False))
        self.sanic_app.ctx.threads = ThreadPoolExecutor()
        self.sanic_app.update_config({"RESPONSE_TIMEOUT": 120,
                                      "REQUEST_TIMEOUT": 120,
                                      "KEEP_ALIVE_TIMEOUT": 120,
                                      "REAL_IP_HEADER": "x-real-ip",
                                      "FALLBACK_ERROR_FORMAT": "json",
                                      })

        # client_register_listener()
        autodiscover(
            self.sanic_app,
            "apps.webhook",
            recursive=True,
        )

        self.sanic_app.static("/static", settings.STATIC_ROOT, name="static")
        self.sanic_app.static("/media", settings.MEDIA_ROOT, name="media")
        self.sanic_app.register_listener(self.before_server_start, "before_server_start")
        self.sanic_app.register_listener(self.after_server_stop, "after_server_stop")
        self._setup_system_signals()

    async def before_server_start(self, app, loop):
        logger.setLevel(settings.LOGGER_LEVEL)

    async def after_server_stop(self, app, loop):
        pass

    def run(self, *args, **kwargs):
        console.print("Starting Webhook services", style="bold green")
        console.print(
            f"Your webhook is running at http://{settings.get_webhook_listen_host()}:{settings.get_webhook_listen_port()}/api/v1/hooks",
            style="bold green")
        console.print(f"Your webhook secret key is {settings.get_secret_key()}", style="bold green")
        loader = AppLoader(factory=partial(create_app, self.app_name))
        app = loader.load()
        app.prepare(host=settings.get_webhook_listen_host(),
                    port=settings.get_webhook_listen_port(),
                    debug=settings.DEBUG,
                    motd=False,
                    auto_reload=settings.AUTO_RELOAD,
                    workers=settings.WEB_HOOK_WORKERS,
                    access_log=settings.WEB_HOOK_ACCESS_LOG)
        Sanic.serve(primary=app, app_loader=loader)


webhook_service = WebhookService("Webhook")

