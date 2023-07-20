import logging.config
import logging.config
import os
import pathlib
import random
import time

import cltl.leolani.gestures as gestures
import requests
from cltl.about.about import AboutImpl
from cltl.about.api import About
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
from cltl.combot.event.bdi import IntentionEvent
from cltl.combot.infra.config.k8config import K8LocalConfigurationContainer
from cltl.combot.infra.di_container import singleton
from cltl.combot.infra.event import Event
from cltl.combot.infra.event.memory import SynchronousEventBusContainer
from cltl.combot.infra.event_log import LogWriter
from cltl.combot.infra.resource.threaded import ThreadedResourceContainer
from cltl.emissordata.api import EmissorDataStorage
from cltl.emissordata.file_storage import EmissorDataFileStorage
from cltl.emotion_extraction.api import EmotionExtractor
from cltl.emotion_extraction.utterance_go_emotion_extractor import GoEmotionDetector
from cltl.emotion_extraction.utterance_vader_sentiment_extractor import VaderSentimentDetector
from cltl.emotion_responder.api import EmotionResponder
from cltl.emotion_responder.emotion_responder import EmotionResponderImpl
from cltl.face_emotion_extraction.api import FaceEmotionExtractor
from cltl.face_emotion_extraction.context_face_emotion_extractor import ContextFaceEmotionExtractor
from cltl.face_recognition.api import FaceDetector
from cltl.face_recognition.proxy import FaceDetectorProxy
from cltl.friends.api import FriendStore
from cltl.friends.brain import BrainFriendsStore
from cltl.friends.memory import MemoryFriendsStore
from cltl.g2ky.api import GetToKnowYou
from cltl.g2ky.verbal import VerbalGetToKnowYou
from cltl.g2ky.visual import VisualGetToKnowYou
from cltl.mention_extraction.api import MentionExtractor
from cltl.mention_extraction.default_extractor import DefaultMentionExtractor, TextMentionDetector, \
    NewFaceMentionDetector, ObjectMentionDetector, TextPerspectiveDetector, ImagePerspectiveDetector
from cltl.nlp.api import NLP
from cltl.nlp.spacy_nlp import SpacyNLP
from cltl.object_recognition.api import ObjectDetector
from cltl.object_recognition.proxy import ObjectDetectorProxy
from cltl.reply_generation.thought_selectors.random_selector import RandomSelector
from cltl.triple_extraction.chat_analyzer import ChatAnalyzer
from cltl.vad.webrtc_vad import WebRtcVAD
from cltl.vector_id.api import VectorIdentity
from cltl.vector_id.clusterid import ClusterIdentity
from cltl.visualresponder.api import VisualResponder
from cltl.visualresponder.visualresponder import VisualResponderImpl
from cltl_service.about.service import AboutService
from cltl_service.asr.service import AsrService
from cltl_service.backend.backend import BackendService
from cltl_service.backend.storage import StorageService
from cltl_service.bdi.service import BDIService
from cltl_service.brain.service import BrainService
from cltl_service.chatui.service import ChatUiService
from cltl_service.combot.event_log.service import EventLogService
from cltl_service.context.service import ContextService
from cltl_service.emissordata.client import EmissorDataClient
from cltl_service.emissordata.service import EmissorDataService
from cltl_service.emotion_extraction.service import EmotionExtractionService
from cltl_service.emotion_responder.service import EmotionResponderService
from cltl_service.entity_linking.service import DisambiguationService
from cltl_service.face_emotion_extraction.service import FaceEmotionExtractionService
from cltl_service.face_recognition.service import FaceRecognitionService
from cltl_service.g2ky.service import GetToKnowYouService
from cltl_service.idresolution.service import IdResolutionService
from cltl_service.intentions.chat import InitializeChatService
from cltl_service.intentions.init import InitService
from cltl_service.keyword.service import KeywordService
from cltl_service.mention_extraction.service import MentionExtractionService
from cltl_service.monitoring.service import MonitoringService
from cltl_service.nlp.service import NLPService
from cltl_service.object_recognition.service import ObjectRecognitionService
from cltl_service.reply_generation.service import ReplyGenerationService
from cltl_service.triple_extraction.service import TripleExtractionService
from cltl_service.vad.service import VadService
from cltl_service.vector_id.service import VectorIdService
from cltl_service.visualresponder.service import VisualResponderService
from emissor.representation.util import serializer as emissor_serializer
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from cltl.dialogue_act_classification.api import DialogueActClassifier
from cltl.dialogue_act_classification.midas_classifier import MidasDialogTagger
from cltl.dialogue_act_classification.silicone_classifier import SiliconeDialogueActClassifier
from cltl_service.dialogue_act_classification.service import DialogueActClassificationService

logging.config.fileConfig(os.environ.get('CLTL_LOGGING_CONFIG', default='config/logging.config'),
                          disable_existing_loggers=False)
logger = logging.getLogger(__name__)


class InfraContainer(SynchronousEventBusContainer, K8LocalConfigurationContainer, ThreadedResourceContainer):
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

        requests.post(f"{self._remote_url}/text", data=response, headers=tts_headers)


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
        if not self.config_manager.get_config('cltl.backend').get_boolean("run_server"):
            # Return a placeholder
            return ""

        audio_config = self.config_manager.get_config('cltl.audio')
        video_config = self.config_manager.get_config('cltl.video')

        return BackendServer(audio_config.get_int('sampling_rate'), audio_config.get_int('channels'),
                             audio_config.get_int('frame_size'),
                             video_config.get_enum('resolution', CameraResolution),
                             video_config.get_int('camera_index'))

    def start(self):
        logger.info("Start Backend")
        super().start()
        if self.server:
            self.server.start()
        self.storage_service.start()
        self.backend_service.start()

    def stop(self):
        try:
            logger.info("Stop Backend")
            self.storage_service.stop()
            self.backend_service.stop()
            if self.server:
                self.server.stop()
        finally:
            super().stop()


class EmissorStorageContainer(InfraContainer):
    @property
    @singleton
    def emissor_storage(self) -> EmissorDataStorage:
        return EmissorDataFileStorage.from_config(self.config_manager)

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
        try:
            logger.info("Stop Emissor Data Storage")
            self.emissor_data_service.stop()
        finally:
            super().stop()



class VADContainer(InfraContainer):
    @property
    @singleton
    def vad_service(self) -> VadService:
        config = self.config_manager.get_config("cltl.vad")

        implementation = config.get("implementation")
        if not implementation:
            logger.warning("No VAD configured")
            return False
        if implementation != "webrtc":
            raise ValueError("Unsupported VAD implementation: " + implementation)

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
        super().start()
        if self.vad_service:
            logger.info("Start VAD")
            self.vad_service.start()

    def stop(self):
        try:
            if self.vad_service:
                logger.info("Stop VAD")
                self.vad_service.stop()
        finally:
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

        if implementation == "google":
            from cltl.asr.google_asr import GoogleASR
            impl_config = self.config_manager.get_config("cltl.asr.google")
            asr = GoogleASR(impl_config.get("language"), impl_config.get_int("sampling_rate"),
                            hints=impl_config.get("hints", multi=True))
        elif implementation == "whisper":
            from cltl.asr.whisper_asr import WhisperASR
            impl_config = self.config_manager.get_config("cltl.asr.whisper")
            asr = WhisperASR(impl_config.get("model"), impl_config.get("language"), storage=storage)
        elif implementation == "speechbrain":
            from cltl.asr.speechbrain_asr import SpeechbrainASR
            impl_config = self.config_manager.get_config("cltl.asr.speechbrain")
            model = impl_config.get("model")
            asr = SpeechbrainASR(model, storage=storage)
        elif implementation == "wav2vec":
            from cltl.asr.wav2vec_asr import Wav2Vec2ASR
            impl_config = self.config_manager.get_config("cltl.asr.wav2vec")
            model = impl_config.get("model")
            asr = Wav2Vec2ASR(model, sampling_rate=sampling_rate, storage=storage)
        elif not implementation:
            asr = False
        else:
            raise ValueError("Unsupported implementation " + implementation)

        if asr:
            return AsrService.from_config(asr, self.emissor_data_client,
                                          self.event_bus, self.resource_manager, self.config_manager)
        else:
            logger.warning("No ASR implementation configured")
            return False

    def start(self):
        super().start()
        if self.asr_service:
            logger.info("Start ASR")
            self.asr_service.start()

    def stop(self):
        try:
            if self.asr_service:
                logger.info("Stop ASR")
                self.asr_service.stop()
        finally:
            super().stop()


class TripleExtractionContainer(InfraContainer):
    @property
    @singleton
    def triple_extraction_service(self) -> TripleExtractionService:
        config = self.config_manager.get_config("cltl.triple_extraction")
        implementation = config.get("implementation", multi=True)

        analyzers = []
        if "CFGAnalyzer" in implementation:
            from cltl.triple_extraction.cfg_analyzer import CFGAnalyzer
            analyzers.append(CFGAnalyzer(process_questions=False))
        if "CFGQuestionAnalyzer" in implementation:
            from cltl.question_extraction.cfg_question_analyzer import CFGQuestionAnalyzer
            analyzers.append(CFGQuestionAnalyzer())
        if "StanzaQuestionAnalyzer" in implementation:
            from cltl.question_extraction.stanza_question_analyzer import StanzaQuestionAnalyzer
            analyzers.append(StanzaQuestionAnalyzer())
        if "OIEAnalyzer" in implementation:
            from cltl.triple_extraction.oie_analyzer import OIEAnalyzer
            analyzers.append(OIEAnalyzer())
        if "spacyAnalyzer" in implementation:
            from cltl.triple_extraction.spacy_analyzer import spacyAnalyzer
            analyzers.append(spacyAnalyzer())
        if "conversational" in implementation:
            from cltl.triple_extraction.conversational_analyzer import ConversationalAnalyzer
            config = self.config_manager.get_config('cltl.triple_extraction.conversational')
            analyzers.append(ConversationalAnalyzer(config.get('model_path')))

        if not analyzers:
            raise ValueError("No supported analyzers in " + implementation)

        return TripleExtractionService.from_config(ChatAnalyzer(analyzers), self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Triple Extraction")
        super().start()
        self.triple_extraction_service.start()

    def stop(self):
        try:
            logger.info("Stop Triple Extraction")
            self.triple_extraction_service.stop()
        finally:
            super().stop()


class BrainContainer(InfraContainer):
    @property
    @singleton
    def brain(self) -> LongTermMemory:
        config = self.config_manager.get_config("cltl.brain")
        brain_address = config.get("address")
        brain_log_dir = config.get("log_dir")
        clear_brain = bool(config.get_boolean("clear_brain"))

        # TODO figure out how to put the brain RDF files in the EMISSOR scenario folder
        return LongTermMemory(address=brain_address,
                              log_dir=pathlib.Path(brain_log_dir),
                              clear_all=clear_brain)

    @property
    @singleton
    def brain_service(self) -> BrainService:
        return BrainService.from_config(self.brain, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Brain")
        super().start()
        self.brain_service.start()

    def stop(self):
        try:
            logger.info("Stop Brain")
            self.brain_service.stop()
        finally:
            super().stop()


class DisambiguationContainer(BrainContainer, InfraContainer):
    @property
    @singleton
    def disambiguation_service(self) -> DisambiguationService:
        config = self.config_manager.get_config("cltl.entity_linking")
        implementations = config.get("implementations")
        brain_address = config.get("address")
        brain_log_dir = config.get("log_dir")
        linkers = []

        if "NamedEntityLinker" in implementations:
            from cltl.entity_linking.linkers import NamedEntityLinker
            linker = NamedEntityLinker(address=brain_address,
                                       log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if "FaceIDLinker" in implementations:
            from cltl.entity_linking.face_linker import FaceIDLinker
            linker = FaceIDLinker(address=brain_address,
                                       log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if "PronounLinker" in implementations:
            # TODO This is OK here, we need to see how this will work in a containerized setting
            # from cltl.reply_generation.rl_replier import PronounLinker
            from cltl.entity_linking.linkers import PronounLinker
            linker = PronounLinker(address=brain_address,
                                   log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if not linkers:
            raise ValueError("Unsupported implementation " + implementations)

        logger.info("Initialized DisambiguationService with linkers %s",
                    [linker.__class__.__name__ for linker in linkers])

        return DisambiguationService.from_config(linkers, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Disambigution Service")
        super().start()
        self.disambiguation_service.start()

    def stop(self):
        try:
            logger.info("Stop Disambigution Service")
            self.disambiguation_service.stop()
        finally:
            super().stop()


class DialogueActClassficationContainer(InfraContainer):
    @property
    @singleton
    def dialogue_act_classifier(self) -> DialogueActClassifier:
        config = self.config_manager.get_config("cltl.dialogue_act_classification")
        implementation = config.get("implementation")

        if implementation == "midas":
            config = self.config_manager.get_config("cltl.dialogue_act_classification.midas")
            return MidasDialogTagger(config.get("model"))
        elif implementation == "silicone":
            return SiliconeDialogueActClassifier()
        elif not implementation:
            logger.warning("No DialogueClassifier implementation configured")
            return False
        else:
            raise ValueError("Unsupported DialogueClassifier implementation: " + implementation)

    @property
    @singleton
    def dialogue_act_classification_service(self) -> DialogueActClassificationService:
        if self.dialogue_act_classifier:
            return DialogueActClassificationService.from_config(self.dialogue_act_classifier,
                                                                self.event_bus, self.resource_manager,
                                                                self.config_manager)
        else:
            return False

    def start(self):
        super().start()
        if self.dialogue_act_classification_service:
            logger.info("Start Dialogue Act Classification Service")
            self.dialogue_act_classification_service.start()

    def stop(self):
        if self.dialogue_act_classification_service:
            logger.info("Stop Dialogue Act Classification Service")
            self.dialogue_act_classification_service.stop()
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
            thought_options = config.get("thought_options", multi=True) if "thought_options" in config else []
            randomness = config.float("randomness") if "randomness" in config else 1.0
            replier = LenkaReplier(RandomSelector(randomness=randomness, priority=thought_options))
            repliers.append(replier)
        if "RLReplier" in implementations:
            from cltl.reply_generation.rl_replier import RLReplier
            # TODO This is OK here, we need to see how this will work in a containerized setting
            replier = RLReplier(self.brain)
            repliers.append(replier)
        if "SimpleNLGReplier" in implementations:
            from cltl.reply_generation.simplenlg_replier import SimpleNLGReplier
            # TODO This is OK here, we need to see how this will work in a containerized setting
            replier = SimpleNLGReplier()
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
        try:
            logger.info("Stop Repliers")
            self.reply_service.stop()
        finally:
            super().stop()


class ObjectRecognitionContainer(InfraContainer):
    @property
    @singleton
    def object_detector(self) -> ObjectDetector:
        config = self.config_manager.get_config("cltl.object_recognition")

        implementation = config.get("implementation")
        if not implementation:
            logger.warning("No ObjectDetector configured")
            return False
        if implementation != "proxy":
            raise ValueError("Unknown FaceEmotionExtractor implementation: " + implementation)

        config = self.config_manager.get_config("cltl.object_recognition.proxy")
        start_infra = config.get_boolean("start_infra")
        detector_url = config.get("detector_url") if "detector_url" in config else None

        return ObjectDetectorProxy(start_infra, detector_url)

    @property
    @singleton
    def object_recognition_service(self) -> FaceRecognitionService:
        if self.object_detector:
            return ObjectRecognitionService.from_config(self.object_detector, self.event_bus,
                                                        self.resource_manager, self.config_manager)
        else:
            return False

    def start(self):
        super().start()
        if self.object_recognition_service:
            logger.info("Start Object Recognition")
            self.object_recognition_service.start()

    def stop(self):
        try:
            if self.object_recognition_service:
                logger.info("Stop Object Recognition")
                self.object_recognition_service.stop()
        finally:
            super().stop()


class FaceRecognitionContainer(InfraContainer):
    @property
    @singleton
    def face_detector(self) -> FaceDetector:
        config = self.config_manager.get_config("cltl.face_recognition")

        implementation = config.get("implementation")
        if not implementation:
            logger.warning("No FaceDetector configured")
            return False
        if implementation != "proxy":
            raise ValueError("Unknown FaceEmotionExtractor implementation: " + implementation)

        config = self.config_manager.get_config("cltl.face_recognition.proxy")
        start_infra = config.get_boolean("start_infra")
        detector_url = config.get("detector_url") if "detector_url" in config else None
        age_gender_url = config.get("age_gender_url") if "age_gender_url" in config else None

        return FaceDetectorProxy(start_infra, detector_url, age_gender_url)

    @property
    @singleton
    def face_recognition_service(self) -> FaceRecognitionService:
        if self.face_detector:
            return FaceRecognitionService.from_config(self.face_detector, self.event_bus,
                                                      self.resource_manager, self.config_manager)
        else:
            return False

    def start(self):
        super().start()
        if self.face_recognition_service:
            logger.info("Start Face Recognition")
            self.face_recognition_service.start()

    def stop(self):
        try:
            if self.face_recognition_service:
                logger.info("Stop Face Recognition")
                self.face_recognition_service.stop()
        finally:
            super().stop()


class VectorIdContainer(InfraContainer):
    @property
    @singleton
    def vector_id(self) -> VectorIdentity:
        config = self.config_manager.get_config("cltl.vector_id.agg")

        return ClusterIdentity.agglomerative(0, config.get_float("distance_threshold"), config.get("storage_path"))

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
        try:
            logger.info("Stop Vector ID")
            self.vector_id_service.stop()
        finally:
            super().stop()


class EmotionRecognitionContainer(InfraContainer):
    @property
    @singleton
    def emotion_extractor(self) -> EmotionExtractor:
        config = self.config_manager.get_config("cltl.emotion_recognition")
        implementation = config.get("impl")

        if implementation == "Go":
            config = self.config_manager.get_config("cltl.emotion_recognition.go")
            detector = GoEmotionDetector(config.get("model"))
        elif implementation == "Vader":
            detector = VaderSentimentDetector()
        elif not implementation:
            logger.warning("No EmotionExtractor implementation configured")
            detector = False
        else:
            raise ValueError("Unknown emotion extractor implementation: " + implementation)

        return detector

    @property
    @singleton
    def face_emotion_extractor(self) -> FaceEmotionExtractor:
        config = self.config_manager.get_config("cltl.face_emotion_recognition")

        implementation = config.get("implementation")
        if not implementation:
            logger.warning("No FaceEmotionExtractor configured")
            return False
        if implementation != "emotic":
            raise ValueError("Unknown FaceEmotionExtractor implementation: " + implementation)

        config = self.config_manager.get_config("cltl.face_emotion_recognition.emotic")

        return ContextFaceEmotionExtractor(config.get("model_context"),
                                           config.get("model_body"),
                                           config.get("model_emotic"),
                                           config.get("value_thresholds"))

    @property
    @singleton
    def emotion_responder(self) -> EmotionResponder:
        return EmotionResponderImpl()

    @property
    @singleton
    def emotion_recognition_service(self) -> EmotionExtractionService:
        if self.emotion_extractor:
            return EmotionExtractionService.from_config(self.emotion_extractor, self.event_bus,
                                                        self.resource_manager, self.config_manager)
        else:
            return False

    @property
    @singleton
    def face_emotion_recognition_service(self) -> FaceEmotionExtractionService:
        if self.face_emotion_extractor:
            return FaceEmotionExtractionService.from_config(self.face_emotion_extractor, self.event_bus,
                                                            self.resource_manager, self.config_manager)
        else:
            return False

    @property
    @singleton
    def emotion_responder_service(self) -> EmotionResponderService:
        return EmotionResponderService.from_config(self.emotion_responder, self.event_bus,
                                                   self.resource_manager, self.config_manager)

    def start(self):
        super().start()
        if self.emotion_recognition_service:
            logger.info("Start Emotion Recognition service")
            self.emotion_recognition_service.start()
        if self.face_emotion_recognition_service:
            logger.info("Start Face Emotion Recognition service")
            self.face_emotion_recognition_service.start()

    def stop(self):
        try:
            if self.face_emotion_recognition_service:
                logger.info("Stop Face Emotion Recognition service")
                self.face_emotion_recognition_service.stop()
            if self.emotion_recognition_service:
                logger.info("Stop Emotion Recognition service")
                self.emotion_recognition_service.stop()
        finally:
            super().stop()


class NLPContainer(InfraContainer):
    @property
    @singleton
    def nlp(self) -> NLP:
        config = self.config_manager.get_config("cltl.nlp.spacy")

        return SpacyNLP(config.get('model'), config.get('entity_relations', multi=True))

    @property
    @singleton
    def nlp_service(self) -> NLPService:
        return NLPService.from_config(self.nlp, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start NLP service")
        super().start()
        self.nlp_service.start()

    def stop(self):
        try:
            logger.info("Stop NLP service")
            self.nlp_service.stop()
        finally:
            super().stop()


class MentionExtractionContainer(InfraContainer):
    @property
    @singleton
    def mention_extractor(self) -> MentionExtractor:
        config = self.config_manager.get_config("cltl.mention_extraction")

        text_detector = TextMentionDetector()
        face_detector = NewFaceMentionDetector()
        object_detector = ObjectMentionDetector()
        text_perspective_detector = TextPerspectiveDetector()
        image_perspective_detector = ImagePerspectiveDetector(config.get_float("confidence_threshold"))

        return DefaultMentionExtractor(text_detector, text_perspective_detector, image_perspective_detector,
                                       face_detector, object_detector)

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
        try:
            logger.info("Stop Mention Extraction Service")
            self.mention_extraction_service.stop()
        finally:
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
        try:
            logger.info("Stop Chat UI")
            self.chatui_service.stop()
        finally:
            super().stop()


class AboutAgentContainer(EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def about_agent(self) -> About:
        return AboutImpl()

    @property
    @singleton
    def about_agent_service(self) -> GetToKnowYouService:
        return AboutService.from_config(self.about_agent, self.emissor_data_client,
                                        self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start AboutAgent")
        super().start()
        self.about_agent_service.start()

    def stop(self):
        try:
            logger.info("Stop AboutAgent")
            self.about_agent_service.stop()
        finally:
            super().stop()


class VisualResponderContainer(EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def visual_responder(self) -> VisualResponder:
        return VisualResponderImpl()

    @property
    @singleton
    def visual_responder_service(self) -> VisualResponderService:
        return VisualResponderService.from_config(self.visual_responder, self.emissor_data_client,
                                        self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start VisualResponder")
        super().start()
        self.visual_responder_service.start()

    def stop(self):
        try:
            logger.info("Stop VisualResponder")
            self.visual_responder_service.stop()
        finally:
            super().stop()


class LeolaniContainer(EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def friend_store(self) -> FriendStore:
        implementation = self.config_manager.get_config("cltl.leolani.friends").get("implementation")

        if implementation == "brain":
            config = self.config_manager.get_config("cltl.brain")
            brain_address = config.get("address")
            brain_log_dir = pathlib.Path(config.get("log_dir"))

            return BrainFriendsStore(brain_address, brain_log_dir)

        if implementation == "memory":
            return MemoryFriendsStore()

        raise ValueError("Unsupported implemenation: " + implementation)

    @property
    @singleton
    def id_resolution_service(self) -> MonitoringService:
        if self.config_manager.get_config("cltl.leolani.idresolution").get_boolean("active"):
            logger.info("Run with active IdResolutionService")
            return IdResolutionService.from_config(self.friend_store, self.emissor_data_client,
                                                   self.event_bus, self.resource_manager, self.config_manager)

        return []

    @property
    @singleton
    def monitoring_service(self) -> MonitoringService:
        return MonitoringService.from_config(self.friend_store, self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def keyword_service(self) -> KeywordService:
        return KeywordService.from_config(self.emissor_data_client,
                                          self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def context_service(self) -> ContextService:
        return ContextService.from_config(self.friend_store, self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def bdi_service(self) -> BDIService:
        # TODO make configurable
        # Model for testing without G2KY
        # bdi_model = {"init":
        #                  {"initialized": ["chat"]},
        #              "chat":
        #                  {"quit": ["init"]}
        #              }
        bdi_model = {"init":
                         {"initialized": ["g2ky"]},
                     "g2ky":
                         {"resolved": ["chat"]},
                     "chat":
                         {"quit": ["init"]}
                     }

        return BDIService.from_config(bdi_model, self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def init_intention(self) -> InitService:
        return InitService.from_config(self.emissor_data_client,
                                       self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def chat_intention(self) -> InitializeChatService:
        return InitializeChatService.from_config(self.emissor_data_client,
                                       self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Leolani services")
        super().start()
        self.bdi_service.start()
        self.context_service.start()
        self.init_intention.start()
        self.chat_intention.start()
        self.keyword_service.start()
        self.monitoring_service.start()
        if self.id_resolution_service:
            self.id_resolution_service.start()

    def stop(self):
        try:
            logger.info("Stop Leolani services")
            self.monitoring_service.stop()
            self.keyword_service.stop()
            self.init_intention.stop()
            self.chat_intention.stop()
            self.bdi_service.stop()
            self.context_service.stop()
            if self.id_resolution_service:
                self.id_resolution_service.stop()
        finally:
            super().stop()


class G2KYContainer(LeolaniContainer, EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def g2ky(self) -> GetToKnowYou:
        config = self.config_manager.get_config("cltl.g2ky")
        implementation = config.get("implementation")
        if implementation == "visual":
            config = self.config_manager.get_config("cltl.g2ky.visual")

            get_friends = self.friend_store.get_friends()
            friends = {face_id: names[1][0]
                       for face_id, names in get_friends.items()
                       if names[1]}

            logger.info("Initialized G2KY with %s friends", len(friends))

            return VisualGetToKnowYou(gaze_images=config.get_int("gaze_images"), friends=friends)
        elif implementation == "verbal":
            return VerbalGetToKnowYou()
        else:
            raise ValueError("Unknown G2KY implementation: " + implementation)

    @property
    @singleton
    def g2ky_service(self) -> GetToKnowYouService:
        return GetToKnowYouService.from_config(self.g2ky, self.emissor_data_client,
                                               self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start G2KY")
        super().start()
        self.g2ky_service.start()

    def stop(self):
        try:
            logger.info("Stop G2KY")
            self.g2ky_service.stop()
        finally:
            super().stop()


class ApplicationContainer(ChatUIContainer, G2KYContainer, LeolaniContainer,
                           AboutAgentContainer, VisualResponderContainer,
                           TripleExtractionContainer, DisambiguationContainer, ReplierContainer, BrainContainer,
                           NLPContainer, MentionExtractionContainer, DialogueActClassficationContainer,
                           FaceRecognitionContainer, VectorIdContainer,
                           ObjectRecognitionContainer, EmotionRecognitionContainer,
                           ASRContainer, VADContainer,
                           EmissorStorageContainer, BackendContainer):
    @property
    @singleton
    def log_writer(self):
        config = self.config_manager.get_config("cltl.event_log")

        return LogWriter(config.get("log_dir"), serializer)

    @property
    @singleton
    def event_log_service(self):
        return EventLogService.from_config(self.log_writer, self.event_bus, self.config_manager)

    def start(self):
        logger.info("Start EventLog")
        super().start()
        self.event_log_service.start()

    def stop(self):
        try:
            logger.info("Stop EventLog")
            self.event_log_service.stop()
        finally:
            super().stop()


def serializer(obj):
    try:
        return emissor_serializer(obj)
    except Exception:
        try:
            return vars(obj)
        except Exception:
            return str(obj)


def main():
    ApplicationContainer.load_configuration()
    logger.info("Initialized Application")
    application = ApplicationContainer()

    with application as started_app:
        intention_topic = started_app.config_manager.get_config("cltl.bdi").get("topic_intention")
        started_app.event_bus.publish(intention_topic, Event.for_payload(IntentionEvent(["init"])))


        routes = {
            '/storage': started_app.storage_service.app,
            '/emissor': started_app.emissor_data_service.app,
            '/chatui': started_app.chatui_service.app,
            '/monitoring': started_app.monitoring_service.app,
        }

        if started_app.server:
            routes['/host'] = started_app.server.app

        web_app = DispatcherMiddleware(Flask("Leolani app"), routes)

        run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=False, use_debugger=False, use_evalex=True)

        intention_topic = started_app.config_manager.get_config("cltl.bdi").get("topic_intention")
        started_app.event_bus.publish(intention_topic, Event.for_payload(IntentionEvent(["terminate"])))
        time.sleep(1)


if __name__ == '__main__':
    main()
