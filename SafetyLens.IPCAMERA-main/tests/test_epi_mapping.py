import unittest
from types import SimpleNamespace

from src.core.detection import EPIDetector, _deduplicate
from src.core.epis import EPI_NAMES, MISSING_EPI_IDS


class EpiMappingTest(unittest.TestCase):
    def test_missing_classes_have_one_canonical_name(self):
        self.assertEqual(MISSING_EPI_IDS, {4, 5, 6, 7})
        self.assertEqual(
            {EPI_NAMES[class_id] for class_id in MISSING_EPI_IDS},
            {'Sem_Oculos', 'Sem_Capacete', 'Sem_Luva', 'Sem_Abafador'},
        )

    def test_detector_filters_uncertain_and_overlapping_boxes_in_model(self):
        class Model:
            def predict(self, frame, **kwargs):
                self.kwargs = kwargs
                return [SimpleNamespace(boxes=[])]

        detector = EPIDetector.__new__(EPIDetector)
        detector.model = Model()
        detector.min_confidence = .5
        detector.epi_mapping = EPI_NAMES
        detector.ausentes_ids = MISSING_EPI_IDS

        detector.detect(None)

        self.assertEqual(detector.model.kwargs, {'conf': .5, 'iou': .3, 'verbose': False})

    def test_detector_keeps_only_the_strongest_box_for_the_same_hand(self):
        detections = [
            (2, .82, (100, 100, 220, 240)),
            (2, .51, (110, 110, 210, 230)),
            (6, .38, (105, 105, 215, 235)),
            (6, .77, (300, 100, 420, 240)),
        ]

        self.assertEqual(_deduplicate(detections), [detections[0], detections[3]])


if __name__ == '__main__':
    unittest.main()
