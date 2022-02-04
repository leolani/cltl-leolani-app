import logging.config

from cltl.asr.speechbrain_asr import SpeechbrainASR
from cltl.backend.api.backend import Backend
from cltl.backend.api.camera import CameraResolution, Camera
from cltl.backend.api.microphone import Microphone
from cltl.backend.api.storage import AudioStorage, ImageStorage
from cltl.backend.api.text_to_speech import TextToSpeech
from cltl.backend.impl.cached_storage import CachedAudioStorage, CachedImageStorage
from cltl.backend.impl.image_camera import ImageCamera
from cltl.backend.impl.sync_microphone import SynchronizedMicrophone
from cltl.backend.impl.sync_tts import SynchronizedTextToSpeech, TextOutputTTS
from cltl.backend.server import BackendServer
from cltl.backend.source.client_source import ClientAudioSource, ClientImageSource
from cltl.backend.source.console_source import ConsoleOutput
from cltl.backend.spi.audio import AudioSource
from cltl.backend.spi.image import ImageSource
from cltl.backend.spi.text import TextOutput
from cltl.chatui.api import Chats
from cltl.chatui.memory import MemoryChats
from cltl.combot.infra.config.k8config import K8LocalConfigurationContainer
from cltl.combot.infra.di_container import singleton
from cltl.combot.infra.event import Event
from cltl.combot.infra.event.memory import SynchronousEventBusContainer
from cltl.combot.infra.resource.threaded import ThreadedResourceContainer
from cltl.eliza.api import Eliza
from cltl.eliza.eliza import ElizaImpl
from cltl.vad.webrtc_vad import WebRtcVAD
from cltl_service.asr.service import AsrService
from cltl_service.backend.backend import BackendService
from cltl_service.backend.schema import TextSignalEvent
from cltl_service.backend.storage import StorageService
from cltl_service.chatui.service import ChatUiService
from cltl_service.eliza.service import ElizaService
from cltl_service.vad.service import VadService
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

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
    def image_storage(self) -> ImageStorage:
        return CachedImageStorage.from_config(self.config_manager)

    @property
    @singleton
    def audio_source(self) -> AudioSource:
        return ClientAudioSource.from_config(self.config_manager)

    @property
    @singleton
    def image_source(self) -> ImageSource:
        return ClientImageSource.from_config(self.config_manager)

    @property
    @singleton
    def text_output(self) -> TextOutput:
        return ConsoleOutput()

    @property
    @singleton
    def microphone(self) -> Microphone:
        return SynchronizedMicrophone(self.audio_source, self.resource_manager)

    @property
    @singleton
    def camera(self) -> Camera:
        config = self.config_manager.get_config("cltl.backend.image")

        return ImageCamera(self.image_source, config.get_float("rate"))

    @property
    @singleton
    def tts(self) -> TextToSpeech:
        return SynchronizedTextToSpeech(TextOutputTTS(self.text_output), self.resource_manager)

    @property
    @singleton
    def backend(self) -> Backend:
        return Backend(self.microphone, self.camera, self.tts)

    @property
    @singleton
    def backend_service(self) -> BackendService:
        return BackendService.from_config(self.backend, self.audio_storage, self.image_storage,
                                          self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def storage_service(self) -> StorageService:
        return StorageService(self.audio_storage, self.image_storage)

    @property
    @singleton
    def server(self) -> Flask:
        audio_config = self.config_manager.get_config('cltl.audio')
        video_config = self.config_manager.get_config('cltl.video')
        server = BackendServer(audio_config.get_int('sampling_rate'), audio_config.get_int('channels'),
                               audio_config.get_int('frame_size'),
                               video_config.get_enum('resolution', CameraResolution),
                               video_config.get_int('camera_index'))

        return server.app

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
        storage = None
        # DEBUG
        # storage = "/Users/tkb/automatic/workspaces/robo/eliza-parent/cltl-eliza-app/py-app/storage/audio/debug/vad"

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

        storage = None
        # DEBUG
        # storage = "/Users/tkb/automatic/workspaces/robo/eliza-parent/cltl-eliza-app/py-app/storage/audio/debug/asr"

        return AsrService.from_config(SpeechbrainASR(model, storage=storage), self.event_bus, self.resource_manager, self.config_manager)

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


def main():
    ApplicationContainer.load_configuration()

    logger.info("Initialized Application")

    application = ApplicationContainer()
    application.start()


    def print_event(event: Event):
        logger.info("APP event (%s): (%s)", event.metadata.topic, event.payload)
    def print_text_event(event: Event[TextSignalEvent]):
        logger.info("UTTERANCE event (%s): (%s)", event.metadata.topic, event.payload.signal.text)

    application.event_bus.subscribe("cltl.topic.microphone", print_event)
    application.event_bus.subscribe("cltl.topic.vad", print_event)
    application.event_bus.subscribe("cltl.topic.text_in", print_text_event)
    application.event_bus.subscribe("cltl.topic.text_out", print_text_event)

    web_app = DispatcherMiddleware(Flask("Eliza app"), {
        '/host': application.server,
        '/storage': application.storage_service.app,
        '/chatui': application.chatui_service.app,
    })

    run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=False, use_debugger=False, use_evalex=True)

    application.stop()


if __name__ == '__main__':
    main()