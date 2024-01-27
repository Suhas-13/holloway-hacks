import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

from collections import deque
import cv2
import time

class GestureRecogniser:
    def __init__(self):
        base_options = mp_python.BaseOptions(model_asset_path='gesture_recognizer.task')
        options = vision.GestureRecognizerOptions(base_options=base_options)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)

    def process_image(self, image):
        """Recognize gestures in the input image and return the top gesture."""
        recognition_result = self.recognizer.recognize(image=mp.Image(
                    data=image,
                    image_format=mp.ImageFormat.SRGB,
                ))

        if not recognition_result.gestures:
            return None

        top_gesture = recognition_result.gestures[0][0]
        return top_gesture


class HandLandmarkRecogniser:
    def __init__(self):
        self.base_options = mp_python.BaseOptions(model_asset_path='hand_landmarker.task')
        self.options = vision.HandLandmarkerOptions(base_options=self.base_options,
                                            num_hands=2)
        self.detector = vision.HandLandmarker.create_from_options(self.options)

    def process_image(self, image):
        mp_image = mp.Image(
                    data=image,
                    image_format=mp.ImageFormat.SRGB,
                )

        detection_result = self.detector.detect(mp_image)
        if not detection_result or not detection_result.hand_landmarks:
            return None
        return detection_result.hand_landmarks[0]
        #print(self.hand_landmarks)

    def process_landmarks(self, hand_landmarks):
        hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()

        hand_landmarks_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) 
            for landmark in hand_landmarks
        ])
        return hand_landmarks_proto
    
    def get_finger_tip_landmarks(self, hand_landmarks):
        """Get the landmarks of the finger tips."""
        hand_landmarks_proto = self.process_landmarks(hand_landmarks)
        finger_tip_landmarks = []
        for finger_tip_index in [8, 12, 16, 20]:
            finger_tip_landmarks.append(hand_landmarks_proto.landmark[finger_tip_index])
        return finger_tip_landmarks
    

    
OPEN_PALM_GESTURE = "Open_Palm"
CLOSED_FIST_GESTURE = "Closed_Fist"
SPEAK_GESTURE = "Pointing_Up"
FLIP_GESTURE = "Victory"

class VideoCaptureHandler:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.gesture_recogniser = GestureRecogniser()
        self.hand_landmarker = HandLandmarkRecogniser()
        self.last_open_palm_frame = -1
        self.gesture_threshold = 0.3
        self.frame_number = 0
        self.capture_frame_threshold = 150
        self.flash_card_mode = True
        self.pinkie_tip_history = deque(maxlen=25)
        self.pinkie_not_detected_counter = 0

    def track_pinkie_tip(self, finger_tip_landmarks):
        """Track the pinkie tip and return the direction."""
        if not finger_tip_landmarks:
            self.pinkie_not_detected_counter += 1
            if self.pinkie_not_detected_counter >= 5:
                self.pinkie_tip_history.clear()
                self.pinkie_not_detected_counter = 0
            return None

        self.pinkie_not_detected_counter = 0
        pinkie_tip = finger_tip_landmarks[0]
        self.pinkie_tip_history.append(pinkie_tip)
        if len(self.pinkie_tip_history) < 10:
            return None
        if self.pinkie_tip_history[0].x > pinkie_tip.x:
            return "Left"
        elif self.pinkie_tip_history[0].x < pinkie_tip.x:
            return "Right"
        return None

    def do_save_webpage(self):
        """Functionality to save the webpage."""
        print("Saving webpage")

    def process_capture_gesture(self, gesture):
        if gesture == OPEN_PALM_GESTURE:
            self.last_open_palm_frame = self.frame_number
        elif gesture == CLOSED_FIST_GESTURE:
            if self.frame_number - self.last_open_palm_frame < self.capture_frame_threshold:
                self.do_save_webpage()
                self.last_open_palm_frame = -1

    def do_query(self):
        """Functionality to query the webpage."""
        print("Querying webpage")

    def do_flip_flashcard(self):
        """Functionality to flip the flashcard."""
        print("Flipping flashcard")

    def process_speak_gesture(self, gesture):
        if gesture == SPEAK_GESTURE:
            self.do_query()

    def process_flip_gesture(self, gesture):
        if gesture == FLIP_GESTURE:
            self.do_flip_flashcard()
    
    def run(self):
        """Main loop for video capture and processing."""
        while self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                break

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            gesture = self.gesture_recogniser.process_image(rgb_image)

            if gesture:
                if gesture.score > self.gesture_threshold:
                    self.process_capture_gesture(gesture.category_name)
                    self.process_speak_gesture(gesture.category_name)
                    self.process_flip_gesture(gesture.category_name)
                    #self.process_swipe_gesture(gesture.category_name)
            
            if self.flash_card_mode:
                hand_landmarks = self.hand_landmarker.process_image(rgb_image)
                finger_tip_landmarks = None
                if hand_landmarks:
                    finger_tip_landmarks = self.hand_landmarker.get_finger_tip_landmarks(hand_landmarks)
                direction = self.track_pinkie_tip(finger_tip_landmarks)
                if direction:
                    print(direction)

            self.frame_number += 1



if __name__ == "__main__":
    video_capture_handler = VideoCaptureHandler()
    video_capture_handler.run()