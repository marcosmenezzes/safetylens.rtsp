import unittest

import numpy as np

from src.core.detection import ImageProcessor


class ImageProcessorTest(unittest.TestCase):
    def test_neutral_settings_preserve_the_frame(self):
        frame = np.array([[[10, 80, 200], [30, 120, 240]]], dtype=np.uint8)
        processed = ImageProcessor.adjust_image(frame, 100, 100, 0, False)
        np.testing.assert_array_equal(processed, frame)


if __name__ == '__main__':
    unittest.main()
