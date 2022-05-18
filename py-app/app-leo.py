import logging.config
import pathlib
import random
import time
import uuid

import cltl.leolani.gestures as gestures
import requests
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
from cltl.brain.long_term_memory import LongTermMemory
from cltl.chatui.api import Chats
from cltl.chatui.memory import MemoryChats
from cltl.combot.event.emissor import ScenarioStarted, ScenarioStopped, LeolaniContext, TextSignalEvent
from cltl.combot.infra.config.k8config import K8LocalConfigurationContainer
from cltl.combot.infra.di_container import singleton
from cltl.combot.infra.event import Event
from cltl.combot.infra.event.memory import SynchronousEventBusContainer
from cltl.combot.infra.resource.threaded import ThreadedResourceContainer
from cltl.combot.infra.time_util import timestamp_now
from cltl.emissordata.api import EmissorDataStorage
from cltl.emissordata.file_storage import EmissorDataFileStorage
from cltl.face_recognition.api import FaceDetector
from cltl.face_recognition.proxy import FaceDetectorProxy

from cltl.mention_extraction.api import MentionExtractor
from cltl.nlp.api import NLP
from cltl.object_recognition.api import ObjectDetector
from cltl.object_recognition.proxy import ObjectDetectorProxy
from cltl.nlp.spacy_nlp import SpacyNLP
from cltl.mention_extraction.default_extractor import DefaultMentionExtractor
from cltl.vad.webrtc_vad import WebRtcVAD
from cltl.vector_id.api import VectorIdentity
from cltl.vector_id.clusterid import ClusterIdentity
from cltl_service.asr.service import AsrService
from cltl_service.backend.backend import BackendService
from cltl_service.backend.storage import StorageService
from cltl_service.brain.service import BrainService
from cltl_service.chatui.service import ChatUiService
from cltl_service.emissordata.client import EmissorDataClient
from cltl_service.emissordata.service import EmissorDataService
from cltl_service.entity_linking.service import DisambiguationService
from cltl_service.face_recognition.service import FaceRecognitionService
from cltl_service.leolani.service import LeolaniService
from cltl_service.object_recognition.service import ObjectRecognitionService
from cltl_service.reply_generation.service import ReplyGenerationService
from cltl_service.triple_extraction.service import TripleExtractionService
from cltl_service.nlp.service import NLPService
from cltl_service.mention_extraction.service import MentionExtractionService
from cltl_service.vad.service import VadService
from cltl_service.vector_id.service import VectorIdService
from emissor.representation.scenario import Scenario, Modality
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


class RemoteTextOutput(TextOutput):
    def __init__(self, remote_url: str):
        self._remote_url = remote_url

    def consume(self, text: str, language=None):
        tts_headers = {'Content-type': 'text/plain'}

        # animation = gestures.BOW
        animation = f"{random.choice(gestures.options)}"
        print("THIS IS WHAT YOU SHOULD VERBALIZE FOR US:", text, animation)

        response = f"\\^startTag({animation}){text}^stopTag({animation})"  #### cannot pass in strings with quotes!!

        requests.post(f"http://{self._remote_url}/text", data=response, headers=tts_headers)


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
        config = self.config_manager.get_config("cltl.backend.text_output")
        remote_url = config.get("remote_url")
        if remote_url:
            return RemoteTextOutput(remote_url)
        else:
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


class EmissorStorageContainer(InfraContainer):
    @property
    @singleton
    def emissor_storage(self) -> EmissorDataStorage:
        config = self.config_manager.get_config("cltl.emissor-data")
        return EmissorDataFileStorage(config.get("path"))

    @property
    @singleton
    def emissor_data_service(self) -> EmissorDataService:
        return EmissorDataService.from_config(self.emissor_storage,
                                              self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def emissor_data_client(self) -> EmissorDataClient:
        return EmissorDataClient("http://0.0.0.0:8000/emissor")

    def start(self):
        logger.info("Start Emissor Data Storage")
        super().start()
        self.emissor_data_service.start()

    def stop(self):
        logger.info("Stop Emissor Data Storage")
        self.emissor_data_service.stop()
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


class ASRContainer(EmissorStorageContainer, InfraContainer):
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

        return AsrService.from_config(asr, self.emissor_data_client,
                                      self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start ASR")
        super().start()
        self.asr_service.start()

    def stop(self):
        logger.info("Stop ASR")
        self.asr_service.stop()
        super().stop()


class TripleExtractionContainer(InfraContainer):
    @property
    @singleton
    def triple_extraction_service(self) -> TripleExtractionService:
        config = self.config_manager.get_config("cltl.triple_extraction")
        implementation = config.get("implementation")

        if implementation == "CFGAnalyzer":
            from cltl.triple_extraction.cfg_analyzer import CFGAnalyzer
            analyzer = CFGAnalyzer()
        elif implementation == "OIEAnalyzer":
            from cltl.triple_extraction.oie_analyzer import OIEAnalyzer
            analyzer = OIEAnalyzer()
        elif implementation == "spacyAnalyzer":
            from cltl.triple_extraction.spacy_analyzer import spacyAnalyzer
            analyzer = spacyAnalyzer()
        else:
            raise ValueError("Unsupported implementation " + implementation)

        return TripleExtractionService.from_config(analyzer, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Triple Extraction")
        super().start()
        self.triple_extraction_service.start()

    def stop(self):
        logger.info("Stop Triple Extraction")
        self.triple_extraction_service.stop()
        super().stop()


class BrainContainer(InfraContainer):
    @property
    @singleton
    def brain(self) -> LongTermMemory:
        config = self.config_manager.get_config("cltl.brain")
        brain_address = config.get("address")
        brain_log_dir = config.get("log_dir")

        # TODO figure out how to put the brain RDF files in the EMISSOR scenario folder
        return LongTermMemory(address=brain_address,
                              log_dir=pathlib.Path(brain_log_dir),
                              clear_all=False)

    @property
    @singleton
    def brain_service(self) -> BrainService:
        return BrainService.from_config(self.brain, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Brain")
        super().start()
        self.brain_service.start()

    def stop(self):
        logger.info("Stop Brain")
        self.brain_service.stop()
        super().stop()


class DisambiguatorContainer(BrainContainer, EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def disambiguation_service(self) -> DisambiguationService:
        config = self.config_manager.get_config("cltl.entity_linking")
        implementations = config.get("implementations")
        brain_address = config.get("address")
        brain_log_dir = config.get("log_dir")
        linkers = []

        if "NamedEntityLinker" in implementations:
            from cltl.entity_linking import NamedEntityLinker
            linker = NamedEntityLinker(address=brain_address,
                                       log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if "PronounLinker" in implementations:
            from cltl.reply_generation.rl_replier import PronounLinker
            # TODO This is OK here, we need to see how this will work in a containerized setting
            linker = PronounLinker(address=brain_address,
                                   log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if not linkers:
            raise ValueError("Unsupported implementation " + implementations)

        return DisambiguationService.from_config(linkers, self.emissor_data_client, self.event_bus,
                                                 self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Brain")
        super().start()
        self.disambiguation_service.start()

    def stop(self):
        logger.info("Stop Brain")
        self.disambiguation_service.stop()
        super().stop()


class ReplierContainer(BrainContainer, EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def reply_service(self) -> ReplyGenerationService:
        config = self.config_manager.get_config("cltl.reply_generation")
        implementations = config.get("implementations")
        repliers = []

        if "LenkaReplier" in implementations:
            from cltl.reply_generation.lenka_replier import LenkaReplier
            replier = LenkaReplier()
            repliers.append(replier)
        if "RLReplier" in implementations:
            from cltl.reply_generation.rl_replier import RLReplier
            # TODO This is OK here, we need to see how this will work in a containerized setting
            replier = RLReplier(self.brain)
            repliers.append(replier)
        if not repliers:
            raise ValueError("Unsupported implementation " + implementations)

        return ReplyGenerationService.from_config(repliers, self.emissor_data_client, self.event_bus,
                                                  self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Repliers")
        super().start()
        self.reply_service.start()

    def stop(self):
        logger.info("Stop Repliers")
        self.reply_service.stop()
        super().stop()


class ObjectRecognitionContainer(InfraContainer):
    @property
    @singleton
    def object_detector(self) -> ObjectDetector:
        return ObjectDetectorProxy()

    @property
    @singleton
    def object_recognition_service(self) -> FaceRecognitionService:
        return ObjectRecognitionService.from_config(self.object_detector, self.event_bus,
                                                    self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Object Recognition")
        super().start()
        self.object_recognition_service.start()

    def stop(self):
        logger.info("Stop Object Recognition")
        self.object_recognition_service.stop()
        super().stop()


class FaceRecognitionContainer(InfraContainer):
    @property
    @singleton
    def face_detector(self) -> FaceDetector:
        return FaceDetectorProxy()

    @property
    @singleton
    def face_recognition_service(self) -> FaceRecognitionService:
        return FaceRecognitionService.from_config(self.face_detector, self.event_bus,
                                                  self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Face Recognition")
        super().start()
        self.face_recognition_service.start()

    def stop(self):
        logger.info("Stop Face Recognition")
        self.face_recognition_service.stop()
        super().stop()


class VectorIdContainer(InfraContainer):
    @property
    @singleton
    def vector_id(self) -> VectorIdentity:
        config = self.config_manager.get_config("cltl.vector_id.agg")

        return ClusterIdentity.agglomerative(0, config.get_float("distance_threshold"))

    @property
    @singleton
    def vector_id_service(self) -> FaceRecognitionService:
        return VectorIdService.from_config(self.vector_id, self.event_bus,
                                           self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Vector ID")
        super().start()
        self.vector_id_service.start()

    def stop(self):
        logger.info("Stop Vector ID")
        self.vector_id_service.stop()
        super().stop()


class NLPContainer(InfraContainer):
    @property
    @singleton
    def nlp(self) -> NLP:
        config = self.config_manager.get_config("cltl.nlp.spacy")

        return SpacyNLP(config.get('model'))

    @property
    @singleton
    def nlp_service(self) -> NLPService:
        return NLPService.from_config(self.nlp, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start NLP service")
        super().start()
        self.nlp_service.start()

    def stop(self):
        logger.info("Stop NLP service")
        self.nlp_service.stop()
        super().stop()


class MentionExtractionContainer(InfraContainer):
    @property
    @singleton
    def mention_extractor(self) -> MentionExtractor:
        return DefaultMentionExtractor()

    @property
    @singleton
    def mention_extraction_service(self) -> MentionExtractionService:
        return MentionExtractionService.from_config(self.mention_extractor,
                                                    self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Mention Extraction Service")
        super().start()
        self.mention_extraction_service.start()

    def stop(self):
        logger.info("Stop Mention Extraction Service")
        self.mention_extraction_service.stop()
        super().stop()


class ChatUIContainer(EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def chats(self) -> Chats:
        return MemoryChats()

    @property
    @singleton
    def chatui_service(self) -> ChatUiService:
        return ChatUiService.from_config(MemoryChats(), self.emissor_data_client, self.event_bus, self.resource_manager,
                                         self.config_manager)

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
    def leolani_service(self) -> LeolaniService:
        return LeolaniService.from_config(self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Leolani")
        super().start()
        self.leolani_service.start()

    def stop(self):
        logger.info("Stop Leolani")
        self.leolani_service.stop()
        super().stop()


class ApplicationContainer(ChatUIContainer,
                           TripleExtractionContainer, ReplierContainer, BrainContainer,
                           NLPContainer, MentionExtractionContainer,
                           FaceRecognitionContainer, VectorIdContainer, ObjectRecognitionContainer,
                           ASRContainer, VADContainer,
                           EmissorStorageContainer, BackendContainer):
    pass


def main():
    ApplicationContainer.load_configuration()
    logger.info("Initialized Application")
    application = ApplicationContainer()
    add_print_handlers(application.event_bus)
    application.start()

    config = application.config_manager.get_config("cltl.leolani")
    scenario = create_scenario()
    application.event_bus.publish(config.get("topic_scenario"), Event.for_payload(ScenarioStarted.create(scenario)))

    web_app = DispatcherMiddleware(Flask("Leolani app"), {
        '/host': application.server,
        '/storage': application.storage_service.app,
        '/emissor': application.emissor_data_service.app,
        '/chatui': application.chatui_service.app,
    })

    run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=False, use_debugger=False, use_evalex=True)

    scenario.ruler.end = timestamp_now()
    application.event_bus.publish("cltl.topic.scenario", Event.for_payload(ScenarioStopped.create(scenario)))

    time.sleep(1)

    application.stop()


def create_scenario():
    AGENT = "Leolani"
    HUMAN_ID = "Piek"

    signals = {
        Modality.IMAGE.name.lower(): "./image.json",
        Modality.TEXT.name.lower(): "./text.json",
        Modality.AUDIO.name.lower(): "./audio.json"
    }

    scenario_context = LeolaniContext(AGENT, HUMAN_ID, str(uuid.uuid4()), get_location())
    return Scenario.new_instance(str(uuid.uuid4()), timestamp_now(), None, scenario_context, signals)


def get_location():
    try:
        return requests.get("https://ipinfo.io").json()
    except:
        return None


def add_print_handlers(event_bus):
    def print_event(event: Event):
        logger.info("APP event (%s): (%s)", event.metadata.topic, event.payload)

    def print_text_event(event: Event[TextSignalEvent]):
        logger.info("UTTERANCE event (%s): (%s)", event.metadata.topic, event.payload.signal.text)

    event_bus.subscribe("cltl.topic.scenario", print_event)
    event_bus.subscribe("cltl.topic.microphone", print_event)
    event_bus.subscribe("cltl.topic.image", print_event)
    event_bus.subscribe("cltl.topic.vad", print_event)
    event_bus.subscribe("cltl.topic.text_in", print_text_event)
    event_bus.subscribe("cltl.topic.text_out", print_text_event)
    event_bus.subscribe("cltl.topic.text_out_replier", print_text_event)
    event_bus.subscribe("cltl.topic.triple_extraction", print_event)
    event_bus.subscribe("cltl.topic.brain_response", print_event)


if __name__ == '__main__':
    main()
