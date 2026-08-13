import unittest

from tvc_api.errors import APIError
from tvc_api.schemas import JobRequest, OPERATION_PRIORITIES


class ValidationTests(unittest.TestCase):
    def test_required_priorities_are_fixed(self) -> None:
        self.assertEqual(100, OPERATION_PRIORITIES["motion-transfer-video"])
        self.assertEqual(90, OPERATION_PRIORITIES["prompt-video"])
        self.assertEqual(30, OPERATION_PRIORITIES["clothes-replacement"])
        self.assertEqual(20, OPERATION_PRIORITIES["scene-replacement"])
        self.assertEqual(10, OPERATION_PRIORITIES["image-upscale-restoration"])
        self.assertEqual(90, OPERATION_PRIORITIES["text_to_video"])
        self.assertEqual(90, OPERATION_PRIORITIES["image_to_video"])
        self.assertEqual(100, OPERATION_PRIORITIES["first_last_frame_to_video"])
        self.assertEqual(100, OPERATION_PRIORITIES["reference_to_video"])

    def test_model_must_match_operation(self) -> None:
        with self.assertRaises(APIError) as raised:
            JobRequest.parse({"operation": "clothes-replacement", "model_id": "wan22-animate", "inputs": {"image": "x"}})
        self.assertEqual("validation_error", raised.exception.code)

    def test_inputs_must_not_be_empty(self) -> None:
        with self.assertRaises(APIError):
            JobRequest.parse({"operation": "prompt-video", "model_id": "wan22-animate", "inputs": {}})

    def test_video_task_type_must_match_operation(self) -> None:
        with self.assertRaises(APIError) as raised:
            JobRequest.parse({"operation": "text_to_video", "model_id": "minimax_h3",
                              "inputs": {"prompt": "x"},
                              "parameters": {"task_type": "reference_to_video"}})
        self.assertEqual("validation_error", raised.exception.code)


if __name__ == "__main__":
    unittest.main()

