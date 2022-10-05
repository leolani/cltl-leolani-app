import contextlib
import json
import logging.config
import os
from collections import defaultdict
from datetime import datetime

import time
from cltl.combot.event.bdi import IntentionEvent
from cltl.combot.event.emissor import TextSignalEvent
from cltl.combot.infra.event import Event
from emissor.representation.util import serializer as emissor_serializer
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

logging.config.fileConfig('config/logging.config', disable_existing_loggers=False)
logger = logging.getLogger(__name__)

from app import (BackendContainer,
                 EmissorStorageContainer,
                 VADContainer,
                 ASRContainer,
                 TripleExtractionContainer,
                 BrainContainer,
                 DisambiguationContainer,
                 ReplierContainer,
                 ObjectRecognitionContainer,
                 FaceRecognitionContainer,
                 VectorIdContainer,
                 NLPContainer,
                 MentionExtractionContainer,
                 ChatUIContainer,
                 AboutAgentContainer,
                 VisualResponderContainer,
                 LeolaniContainer,
                 G2KYContainer,
                 EmotionRecognitionContainer
                 )


class ApplicationContainer(ChatUIContainer, G2KYContainer, LeolaniContainer,
                           AboutAgentContainer, VisualResponderContainer,
                           TripleExtractionContainer, DisambiguationContainer, ReplierContainer, BrainContainer,
                           NLPContainer, MentionExtractionContainer,
                           FaceRecognitionContainer, VectorIdContainer,
                           ObjectRecognitionContainer, EmotionRecognitionContainer,
                           ASRContainer, VADContainer,
                           EmissorStorageContainer, BackendContainer):
    pass


def add_print_handlers(event_bus):
    def print_event(event: Event):
        logger.info("APP event (%s): (%s)", event.metadata.topic, event.payload)

    def print_bdi_event(event: Event):
        logger.info("BDI event (%s): (%s)", event.metadata.topic, event.payload)

    def print_text_event(event: Event[TextSignalEvent]):
        logger.info("UTTERANCE event (%s): (%s)", event.metadata.topic, event.payload.signal.text)

    event_counts = defaultdict(int)
    def event_stats(event):
        event_counts[event.metadata.topic] += 1
        if sum(event_counts.values()) % 10 == 0:
            logger.info("STATS: %s", event_counts)

    event_bus.subscribe("cltl.topic.scenario", print_event)
    event_bus.subscribe("cltl.topic.speaker", print_event)
    event_bus.subscribe("cltl.topic.intention", print_bdi_event)
    event_bus.subscribe("cltl.topic.desire", print_bdi_event)
    event_bus.subscribe("cltl.topic.microphone", print_event)
    event_bus.subscribe("cltl.topic.image", print_event)
    event_bus.subscribe("cltl.topic.vad", print_event)
    event_bus.subscribe("cltl.topic.text_in", print_text_event)
    event_bus.subscribe("cltl.topic.chat_text_in", print_text_event)
    event_bus.subscribe("cltl.topic.text_out", print_text_event)
    event_bus.subscribe("cltl.topic.text_out_replier", print_text_event)
    event_bus.subscribe("cltl.topic.triple_extraction", print_event)
    event_bus.subscribe("cltl.topic.brain_response", print_event)

    [event_bus.subscribe(topic, event_stats) for topic in event_bus.topics]


def get_event_log_path(config):
    log_dir = config.get('event_log')
    date_now = datetime.now()

    os.makedirs(log_dir, exist_ok=True)

    return f"{log_dir}/{date_now :%y_%m_%d-%H_%M_%S}.json"


@contextlib.contextmanager
def event_log(event_bus, config):
    def log_event(event):
        try:
            event_log.write(json.dumps(event, default=serializer, indent=2) + ',\n')
        except:
            logger.exception("Failed to write event: %s", event)

    with open(get_event_log_path(config), "w") as event_log:
        event_log.writelines(['['])

        topics = event_bus.topics
        for topic in topics:
            event_bus.subscribe(topic, log_event)
        logger.info("Subscribed %s to %s", event_log.name, topics)

        yield None

        event_log.writelines([']'])


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
    add_print_handlers(application.event_bus)
    application.start()

    intention_topic = application.config_manager.get_config("cltl.bdi").get("topic_intention")
    application.event_bus.publish(intention_topic, Event.for_payload(IntentionEvent(["init"])))

    config = application.config_manager.get_config("cltl.leolani")
    with event_log(application.event_bus, config):
        routes = {
            '/storage': application.storage_service.app,
            '/emissor': application.emissor_data_service.app,
            '/chatui': application.chatui_service.app,
            '/monitoring': application.monitoring_service.app,
        }

        if application.server:
            routes['/host'] = application.server.app

        web_app = DispatcherMiddleware(Flask("Leolani app"), routes)

        run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=False, use_debugger=False, use_evalex=True)

        intention_topic = application.config_manager.get_config("cltl.bdi").get("topic_intention")
        application.event_bus.publish(intention_topic, Event.for_payload(IntentionEvent(["terminate"])))
        time.sleep(1)

        application.stop()


if __name__ == '__main__':
    main()
