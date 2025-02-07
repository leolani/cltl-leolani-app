import argparse
import logging.config
import os
from pprint import pprint
from typing import Iterable, Dict

import cv2
import numpy as np
from cltl.backend.api.camera import CameraResolution
from cltl.face_recognition.api import FaceDetector
from cltl.friends.api import FriendStore
from cltl.vector_id.api import VectorIdentity


class FriendImporter:
    def __init__(self, friend_store: FriendStore, detector: FaceDetector, vector_id: VectorIdentity, resolution: CameraResolution):
        self.friend_store = friend_store
        self.detector = detector
        self.vector_id = vector_id
        self.resolution = resolution

    @classmethod
    def create(cls, vector_id_path: str, face_detector_url: str, age_detector_url: str,
               resolution: CameraResolution=CameraResolution.NATIVE, brain_url=None, brain_log_dir=None):
        from cltl.face_recognition.proxy import FaceDetectorProxy
        from cltl.vector_id.clusterid import ClusterIdentity
        from cltl.friends.brain import BrainFriendsStore

        detector = FaceDetectorProxy(start_infra=False, detector_url=face_detector_url, age_gender_url=age_detector_url)
        vector_id = ClusterIdentity.agglomerative(storage_path=vector_id_path)
        friend_store = BrainFriendsStore(address=brain_url, log_dir=brain_log_dir) if brain_url else None

        return cls(friend_store, detector, vector_id, resolution)

    @classmethod
    def create_autostart(cls, vector_id_path: str,
                         resolution: CameraResolution=CameraResolution.NATIVE, brain_url=None, brain_log_dir=None):
        from cltl.face_recognition.proxy import FaceDetectorProxy
        from cltl.vector_id.clusterid import ClusterIdentity
        from cltl.friends.brain import BrainFriendsStore

        detector = FaceDetectorProxy()
        vector_id = ClusterIdentity.agglomerative(storage_path=vector_id_path)
        friend_store = BrainFriendsStore(address=brain_url, log_dir=brain_log_dir) if brain_url else None

        return cls(friend_store, detector, vector_id, resolution)

    @classmethod
    def from_config(cls, config_path: str = None, no_brain: bool = False):
        from app import FaceRecognitionContainer, VectorIdContainer, LeolaniContainer
        from cltl.combot.infra.config.local import LocalConfigurationContainer

        class ImporterContainer(FaceRecognitionContainer, VectorIdContainer, LeolaniContainer, LocalConfigurationContainer):
            pass

        if config_path:
            ImporterContainer.load_configuration(config_path, additional_config_files=())
        else:
            ImporterContainer.load_configuration()

        container = ImporterContainer()
        container.load_configuration()

        detector = container.face_detector
        vector_id = container.vector_id
        friend_store = container.friend_store if not no_brain else None

        config = container.config_manager.get_config("cltl.video")

        return cls(friend_store, detector, vector_id, resolution=config.get_enum("resolution", CameraResolution))

    def friends_to_ids(self, friends: Dict[str, Iterable[str]]):
        if not self.detector or not self.vector_id:
            raise ValueError("No detector or vector ID store configured")

        with self.detector as face_detector:
            ids = {name: self._add_representations(name, face_detector, image_paths)
                   for name, image_paths in friends.items()}

        return ids

    def store_ids(self, friends: Dict[str, Iterable[str]]):
        if not self.friend_store:
            raise ValueError("No friend store configured")

        logger.info("Storing friends %s", friends.keys())
        logger.debug("Storing friends %s", friends)

        [self.friend_store.add_friend(identifier=id, names=[name]) for name, ids in friends.items() for id in ids]

    def _add_representations(self, name, face_detector, image_paths):
        logger.info("Adding representations for friend %s from %s", name, image_paths)
        representations = [self._encode_face(face_detector, path) for path in image_paths]
        representations = list(filter(lambda r: r is not None, representations))
        representations = np.vstack(representations)

        vector_ids = set(self.vector_id.add(representations))
        if len(vector_ids) > 1:
            logger.warning("Friend %s represented by multiple IDs: %s", name, vector_ids)

        return list(vector_ids)

    def _encode_face(self, face_detector, image_path):
        faces, _ = face_detector.detect(self._load_image(image_path))
        faces = list(faces)

        if len(faces) == 0:
            logger.warning("No faces detected in %s", image_path)
            return None
        elif len(faces) > 1:
            raise ValueError(f"Multiple faces detected in {image_path}")

        return np.atleast_2d(faces[0].embedding)

    def _load_image(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Image {image_path} could not be loaded")

        if not self.resolution == CameraResolution.NATIVE:
            image = cv2.resize(image, (self.resolution.width, self.resolution.height))

        return image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Friends importer')
    parser.add_argument('--friend', type=str, required=True, action='append', nargs="*",
                        help="Friend name followed by image paths")
    parser.add_argument('--ids-only', action='store_true',
                        help="Only add friends to the VectorID store, don't associate vector IDs to names")
    args, _ = parser.parse_known_args()

    logging.config.fileConfig(os.environ.get('CLTL_LOGGING_CONFIG', default='config/logging.config'),
                              disable_existing_loggers=False)
    logger = logging.getLogger(__name__)

    logger.info("Importing %s friends", len(args.friend))

    importer = FriendImporter.from_config(no_brain=args.ids_only)
    logger.info("Adding vector IDs for friends")
    ids = importer.friends_to_ids({friend[0]: friend[1:] for friend in args.friend})

    pprint(ids)

    if not args.ids_only:
        logger.info("Connecting friend IDs to names")
        importer.store_ids(ids)