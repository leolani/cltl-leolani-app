import logging.config
import numpy as np
from cltl.asr.wav2vec_asr import Wav2Vec2ASR
from cltl.backend.source.pyaudio_source import PyAudioSource
from cltl.vad.webrtc_vad import WebRtcVAD

from cltl.backend.api.util import raw_frames_to_np

logging.config.fileConfig('config/logging.config', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    source = PyAudioSource(16000, 1, 480)
    vad = WebRtcVAD()
    asr = Wav2Vec2ASR(model_id="facebook/wav2vec2-large-960h", sampling_rate=16000)

    while True:
        try:
            with source as audio:
                frames = raw_frames_to_np(audio, source.frame_size, source.channels, source.depth)
                speech, offset, consumed = tuple(vad.detect_vad(frames, source.rate))
                text = asr.speech_to_text(np.concatenate(tuple(speech)), source.rate)
        except:
            logger.exception("Failed")