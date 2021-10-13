import logging.config
from types import SimpleNamespace

from cltl.chatui.memory import MemoryChats
from cltl.combot.infra.config.local import load_configuration, LocalConfigurationManager
from cltl.combot.infra.event.memory import SynchronousEventBus
from cltl.combot.infra.resource.threaded import ThreadedResourceManager
from cltl_service.chatui.service import ChatUiService
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from cltl.eliza.eliza import ElizaImpl
from cltl_service.eliza.service import ElizaService

logging.config.fileConfig('config/logging.config')
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    configs=["config/default.config"]
    config = load_configuration(None, configs)

    infra = [SynchronousEventBus(), ThreadedResourceManager(), LocalConfigurationManager(config)]

    logger.info("Initialized Application with local event bus")

    services = SimpleNamespace(**{
        'chat_ui': ChatUiService.from_config(MemoryChats(), *infra),
        'eliza': ElizaService.from_config(ElizaImpl(), *infra)
    })

    [service.start() for service in vars(services).values()]

    app = Flask("Eliza app")
    application = DispatcherMiddleware(app, {
        '/chatui': services.chat_ui.app,
    })

    run_simple('0.0.0.0', 8000, application, threaded=True, use_reloader=True, use_debugger=True, use_evalex=True)

    [service.stop() for service in vars(services).values()]