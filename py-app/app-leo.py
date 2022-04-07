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
from cltl.leolani.api import Leolani
from cltl.leolani.leolani import LeolaniImpl
from cltl.vad.webrtc_vad import WebRtcVAD
from cltl_service.asr.service import AsrService
from cltl_service.backend.backend import BackendService
from cltl_service.backend.schema import TextSignalEvent
from cltl_service.backend.storage import StorageService
from cltl_service.chatui.service import ChatUiService
from cltl_service.leolani.service import LeolaniService
from cltl_service.vad.service import VadService
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

##### PIEK adaptations:
from emissor.representation.scenario import TextSignal
from emissor.representation.scenario import ImageSignal
import cltl.leolani.emissor_api as emissor_api
import time
import pathlib
import random
import requests
from cltl import brain
from cltl.triple_extraction.api import Chat
from cltl.triple_extraction.spacy_analyzer import spacyAnalyzer
from cltl.triple_extraction.cfg_analyzer import CFGAnalyzer
from cltl.reply_generation.lenka_replier import LenkaReplier

import cltl.leolani.gestures as gestures
import cltl.leolani.talk as talk
import cltl.leolani.watch as watch

logging.config.fileConfig('config/logging.config', disable_existing_loggers=False)
logger = logging.getLogger(__name__)

class DisplayComponent():
    """
    Show content on the robot's display.
    """

    def __init__(self):
        super(DisplayComponent, self).__init__()

        self._log.debug("Initializing DisplayComponent")

    def show_on_display(self, url):
        # type: (Union[str, unicode]) -> None
        """
        Show URL

        Parameters
        ----------
        url: str
            WebPage/Image URL
        """
        event = Event({'url': url}, None)
        self.event_bus.publish(TOPIC, event)

    def hide_display(self):
        # type: () -> None
        """Hide whatever is shown on the display"""
        event = Event({'url': None}, None)
        self.event_bus.publish(TOPIC, event)

class InfraContainer(SynchronousEventBusContainer, K8LocalConfigurationContainer, ThreadedResourceContainer):
    def start(self):
        pass

    def stop(self):
        pass


class RemoteTextOutput(TextOutput):
    def consume(self, text: str, language=None):
        tts_headers = {'Content-type': 'text/plain'}

        # animation = gestures.BOW
        animation = f"{random.choice(gestures.options)}"
        print("THIS IS WHAT YOU SHOULD VERBALIZE FOR US:", text, animation)

        response = f"\\^startTag({animation}){text}^stopTag({animation})"  #### cannot pass in strings with quotes!!

        requests.post("http://192.168.1.176:8000/text", data=response, headers=tts_headers)

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
        return RemoteTextOutput()
       # return ConsoleOutput()        # Piek

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
        config = self.config_manager.get_config("cltl.vad.webrtc")
        activity_window = config.get_int("activity_window")
        activity_threshold = config.get_float("activity_threshold")
        allow_gap = config.get_int("allow_gap")
        padding = config.get_int("padding")
        storage = None
        # DEBUG
        # storage = "/Users/tkb/automatic/workspaces/robo/eliza-parent/cltl-eliza-app/py-app/storage/audio/debug/vad"

        vad = WebRtcVAD(activity_window, activity_threshold, allow_gap, padding, storage=storage)

        return VadService.from_config(vad, self.event_bus, self.resource_manager, self.config_manager)

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
        sampling_rate = config.get_int("sampling_rate")
        implementation = config.get("implementation")

        storage = None
        # DEBUG
        # storage = "/Users/tkb/automatic/workspaces/robo/eliza-parent/cltl-eliza-app/py-app/storage/audio/debug/asr"

        if implementation == "speechbrain":
            from cltl.asr.speechbrain_asr import SpeechbrainASR
            impl_config = self.config_manager.get_config("cltl.asr.speechbrain")
            model = impl_config.get("model")
            asr = SpeechbrainASR(model, storage=storage)
        elif implementation == "wav2vec":
            from cltl.asr.wav2vec_asr import Wav2Vec2ASR
            impl_config = self.config_manager.get_config("cltl.asr.wav2vec")
            model = impl_config.get("model")
            asr = Wav2Vec2ASR(model, sampling_rate=sampling_rate, storage=storage)
        else:
            raise ValueError("Unsupported implementation " + implementation)

        return AsrService.from_config(asr, self.event_bus, self.resource_manager, self.config_manager)

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

class LeolaniContainer(InfraContainer):
    @property
    @singleton
    def leolani(self) -> Leolani:
        return LeolaniImpl()

    @property
    @singleton
    def leolani_service(self) -> LeolaniService:
        return LeolaniService.from_config(self.leolani, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Leolani")
        super().start()
        self.leolani_service.start()

    def stop(self):
        logger.info("Stop Leolani")
        self.leolani_service.stop()
        super().stop()


class ApplicationContainer(LeolaniContainer, ChatUIContainer, ASRContainer, VADContainer, BackendContainer):
    pass


def main():
    ApplicationContainer.load_configuration()

    logger.info("Initialized Application")

    application = ApplicationContainer()


    #Start a scenario
    ##### Setting the agents
    AGENT = "Leolani"
    HUMAN_NAME = "Piek"
    HUMAN_ID = "Piek"
    DATA = "./data"
    scenarioStorage, scenario_ctrl, imagefolder, rdffolder, location, place_id = emissor_api.start_a_scenario(AGENT, HUMAN_ID, HUMAN_NAME, DATA)

    # Initialise a chat
    chat = Chat(HUMAN_ID)

    replier = LenkaReplier()
    analyzer = CFGAnalyzer()
    #analyzer = spacyAnalyzer()

    # Initialise the brain in GraphDB
    log_path = pathlib.Path(rdffolder)
    my_brain = brain.LongTermMemory(address="http://localhost:7200/repositories/sandbox", log_dir=log_path,  clear_all=True)

    def print_event(event: Event):
        logger.info("APP event (%s): (%s)", event.metadata.topic, event.payload)

    def print_text_event(event: Event[TextSignalEvent]):
        logger.info("UTTERANCE event (%s): (%s)", event.metadata.topic, event.payload.signal.text)

    def print_text_event_speaker(event: Event[TextSignalEvent]):
        textSignal = TextSignal.for_scenario(None, 0, 0, None, event.payload.signal.text)
        emissor_api.add_speaker_annotation(textSignal, HUMAN_ID)
        scenario_ctrl.append_signal(textSignal)

        reply_textSignal = talk.understand_remember_reply(scenario_ctrl, textSignal, chat, replier, analyzer,AGENT, HUMAN_ID, my_brain, location, place_id, logger)

        emissor_api.add_speaker_annotation(reply_textSignal, AGENT)
        scenario_ctrl.append_signal(reply_textSignal)
        modifiedPayload = TextSignalEvent.create(reply_textSignal)
        modifiedEvent = Event.for_payload(modifiedPayload)
        application.event_bus.publish("cltl.topic.text_out", modifiedEvent)
        logger.info("UTTERANCE reply (%s): (%s)", modifiedEvent.metadata.topic, modifiedEvent.payload.signal.text)
        
    def repeat_text_event(event: Event[TextSignalEvent]):
        textSignal = TextSignal.for_scenario(None, 0, 0, None, "You said:"+event.payload.signal.text)
        #### Parrot
        modifiedPayload = TextSignalEvent.create(textSignal)
        modifiedEvent = Event.for_payload(modifiedPayload)
        application.event_bus.publish("cltl.topic.text_out", modifiedEvent)
        emissor_api.add_speaker_annotation(textSignal, HUMAN_ID)
        scenario_ctrl.append_signal(textSignal)
        logger.info("UTTERANCE event (%s): (%s)", modifiedEvent.metadata.topic, modifiedEvent.payload.signal.text)

    def print_text_event_agent(event: Event[TextSignalEvent]):
        textSignal = TextSignal.for_scenario(None, 0, 0, None, event.payload.signal.text)
        emissor_api.add_speaker_annotation(textSignal, AGENT)
        scenario_ctrl.append_signal(textSignal)
        logger.info("UTTERANCE event (%s): (%s)", event.metadata.topic, event.payload.signal.text)


    def watch_event(event: Event):
        ##imageSignal = ImageSignal.for_scenario()
        logger.info("WATCH event (%s): (%s)", event.metadata.topic, event.payload.signal.image)
        # watch_and_remember(scenario_ctrl, camera, imagefolder, my_brain, location, place_id)

    application.event_bus.subscribe("cltl.topic.microphone", print_event)
    application.event_bus.subscribe("cltl.topic.image", print_event)
    application.event_bus.subscribe("cltl.topic.vad", print_event)
    application.event_bus.subscribe("cltl.topic.text_in", print_text_event_speaker)
    application.event_bus.subscribe("cltl.topic.text_in",  repeat_text_event)
    application.event_bus.subscribe("cltl.topic.text_out", print_text_event_agent)

    application.start()

    web_app = DispatcherMiddleware(Flask("Leolani app"), {
        '/host': application.server,
        '/storage': application.storage_service.app,
        '/chatui': application.chatui_service.app,
    })

    run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=False, use_debugger=False, use_evalex=True)

    #Save the scenario
    scenario_ctrl.scenario.ruler.end = int(time.time() * 1e3)
    scenarioStorage.save_scenario(scenario_ctrl)
    
    application.stop()



if __name__ == '__main__':
    main()
