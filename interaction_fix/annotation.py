import uuid
from typing import Iterable

from cltl.combot.event.emissor import ConversationalAgent
from cltl.combot.infra.time_util import timestamp_now
from cltl.emotion_extraction.api import Emotion
from cltl.emotion_extraction.utterance_go_emotion_extractor import GoEmotionDetector
from emissor.persistence import ScenarioStorage
from emissor.representation.scenario import Modality, TextSignal, Annotation, class_type, Mention, class_source

from cltl.dialogue_act_classification.api import DialogueAct
from cltl.dialogue_act_classification.midas_classifier import MidasDialogTagger


def dialogue_act_mention(text_signal: TextSignal, acts: Iterable[DialogueAct], source: str):
    segment = text_signal.ruler
    annotations = [Annotation(class_type(DialogueAct), dialogueAct, source, timestamp_now())
                   for dialogueAct in acts]

    return Mention(str(uuid.uuid4()), [segment], annotations)


def emotion_mention(text_signal: TextSignal, emotions: Iterable[Emotion], source: str) -> Mention:
    segment = text_signal.ruler
    annotations = [Annotation(class_type(Emotion), emotion, source, timestamp_now())
                   for emotion in emotions]

    return Mention(str(uuid.uuid4()), [segment], annotations)


def is_speaker(signal: TextSignal):
    return any(is_speaker_annotation(annotation)
               for mention in signal.mentions for annotation in mention.annotations)


def is_speaker_annotation(annotation):
    return (annotation.type == ConversationalAgent.__name__
            and annotation.value == ConversationalAgent.SPEAKER.name)


def process_scenario(scenario_id, dialogue_tagger, emotion_detector):
    scenario_ctrl = storage.load_scenario(scenario_id)
    scenario_ctrl.load_signals([Modality.TEXT])

    print("Processing:", scenario_ctrl.id, "with", len(scenario_ctrl.signals[Modality.TEXT]), "utterances")

    dialogue_acts = list((signal, dialogue_tagger.extract_dialogue_act(signal.text), class_source(dialogue_tagger))
                     for signal in scenario_ctrl.signals[Modality.TEXT]
                     if is_speaker(signal))

    mentions = [(tagged_signal[0], dialogue_act_mention(*tagged_signal)) for tagged_signal in dialogue_acts]
    for signal, mention in mentions:
        signal.mentions.append(mention)

    print("Added dialogue acts to", len(dialogue_acts), "signals")

    emotions = [(signal, emotion_detector.extract_text_emotions(signal.text), class_source(dialogue_tagger))
                for signal in scenario_ctrl.signals[Modality.TEXT]
                if is_speaker(signal)]
    mentions = [(tagged_signal[0], emotion_mention(*tagged_signal)) for tagged_signal in emotions]

    for signal, mention in mentions:
        signal.mentions.append(mention)

    print("Added emotions to", len(emotions), "signals")

    storage.save_scenario(scenario_ctrl)


if __name__ == '__main__':
    storage = ScenarioStorage("data")
    scenarios = list(storage.list_scenarios())
    print("Processing scenarios: ", scenarios)

    dialogue_tagger = MidasDialogTagger("resources/midas-da-roberta/classifier.pt")
    emotion_detector = GoEmotionDetector("bhadresh-savani/bert-base-go-emotion")

    for scenario_id in scenarios:
        process_scenario(scenario_id, dialogue_tagger, emotion_detector)
