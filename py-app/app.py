import logging.config

from cltl.backend.api.microphone import Microphone
from cltl.backend.api.storage import AudioStorage
from cltl.backend.impl.cached_storage import CachedAudioStorage
from cltl.backend.impl.sync_microphone import SimpleMicrophone
from cltl.backend.source.client_source import ClientAudioSource
from cltl.backend.spi.audio import AudioSource
from cltl.chatui.api import Chats
from cltl.chatui.memory import MemoryChats
from cltl.combot.infra.config.k8config import K8LocalConfigurationContainer
from cltl.combot.infra.di_container import singleton
from cltl.combot.infra.event.memory import SynchronousEventBusContainer
from cltl.combot.infra.resource.threaded import ThreadedResourceContainer
from cltl.asr.wav2vec_asr import Wav2Vec2ASR
from cltl.vad.webrtc_vad import WebRtcVAD
from cltl_service.backend.backend import AudioBackendService
from cltl_service.backend.storage import StorageService
from cltl_service.chatui.service import ChatUiService
from cltl_service.vad.service import VadService
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

import host
from cltl.eliza.api import Eliza
from cltl.eliza.eliza import ElizaImpl
from cltl_service.asr.service import AsrService
from cltl_service.eliza.service import ElizaService
from host.server import backend_server

logging.config.fileConfig('config/logging.config', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


class InfraContainer(SynchronousEventBusContainer, K8LocalConfigurationContainer, ThreadedResourceContainer):
    def start(self):
        pass

    def stop(self):
        pass


class BackendContainer(InfraContainer):
    @property
    @singleton
    def audio_storage(self) -> AudioStorage:
        return CachedAudioStorage.from_config(self.config_manager)

    @property
    @singleton
    def audio_source(self) -> AudioSource:
        return ClientAudioSource.from_config(self.config_manager)

    @property
    @singleton
    def microphone(self) -> Microphone:
        return SimpleMicrophone(self.audio_source)

    @property
    @singleton
    def backend_service(self) -> AudioBackendService:
        return AudioBackendService.from_config(self.microphone, self.audio_storage, self.event_bus, self.config_manager)

    @property
    @singleton
    def storage_service(self) -> StorageService:
        return StorageService(self.audio_storage)

    @property
    @singleton
    def server(self) -> Flask:
        config = self.config_manager.get_config('cltl.audio')

        return host.server.backend_server(config.get_int('sampling_rate'),
                                          config.get_int('channels'),
                                          config.get_int('frame_size'))

    def start(self):
        logger.info("Start Backend")
        super().start()
        self.storage_service.start()
        self.backend_service.start()

    def stop(self):
        logger.info("Stop Backend")
        self.storage_service.stop()
        self.backend_service.stop()
        super().stop()


class VADContainer(InfraContainer):
    @property
    @singleton
    def vad_service(self) -> VadService:
        storage = "/Users/tkb/automatic/workspaces/robo/eliza-parent/cltl-eliza-app/py-app/storage/audio/debug/vad"
        return VadService.from_config(WebRtcVAD(storage=storage), self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start VAD")
        super().start()
        self.vad_service.start()

    def stop(self):
        logger.info("Stop VAD")
        self.vad_service.stop()
        super().stop()


class ASRContainer(InfraContainer):
    @property
    @singleton
    def asr_service(self) -> AsrService:
        config = self.config_manager.get_config("cltl.asr")
        model = config.get("model")
        sampling_rate = config.get_int("sampling_rate")
        storage = "/Users/tkb/automatic/workspaces/robo/eliza-parent/cltl-eliza-app/py-app/storage/audio/debug/asr"

        return AsrService.from_config(Wav2Vec2ASR(model, sampling_rate, storage=storage), self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start ASR")
        super().start()
        self.asr_service.start()

    def stop(self):
        logger.info("Stop ASR")
        self.asr_service.stop()
        super().stop()


class ChatUIContainer(InfraContainer):
    @property
    @singleton
    def chats(self) -> Chats:
        return MemoryChats()

    @property
    @singleton
    def chatui_service(self) -> ChatUiService:
        return ChatUiService.from_config(MemoryChats(), self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Chat UI")
        super().start()
        self.chatui_service.start()

    def stop(self):
        logger.info("Stop Chat UI")
        self.chatui_service.stop()
        super().stop()


class ElizaContainer(InfraContainer):
    @property
    @singleton
    def eliza(self) -> Eliza:
        return ElizaImpl()

    @property
    @singleton
    def eliza_service(self) -> ElizaService:
        return ElizaService.from_config(self.eliza, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Eliza")
        super().start()
        self.eliza_service.start()

    def stop(self):
        logger.info("Stop Eliza")
        self.eliza_service.stop()
        super().stop()


class ApplicationContainer(ElizaContainer, ChatUIContainer, ASRContainer, VADContainer, BackendContainer):
    pass


if __name__ == '__main__':
    ApplicationContainer.load_configuration()

    logger.info("Initialized Application")

    application = ApplicationContainer()
    application.start()

    application.event_bus.subscribe("cltl.topic.microphone", lambda e: print("mic", e))
    application.event_bus.subscribe("cltl.topic.vad", lambda e: print("vad", e))
    application.event_bus.subscribe("cltl.topic.text_in", lambda e: print("text_in", e))

    web_app = DispatcherMiddleware(Flask("Eliza app"), {
        '/host': application.server,
        '/storage': application.storage_service.app,
        '/chatui': application.chatui_service.app,
    })

    run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=True, use_debugger=True, use_evalex=True)

    application.stop()