import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2
from voice_recorder import VoiceRecorder, VoicePlayer
from collections import deque
from mac_alerts import alerts
import cv2
import time
import threading
import asyncio
from beepy import beep
from server import PDFServer
from vectors.redis_handler import RedisManager

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
        self.gesture_threshold = 0.5
        self.frame_number = 0
        self.capture_frame_threshold = 150
        self.flash_card_mode = False
        self.pinkie_tip_history = deque(maxlen=25)
        self.pinkie_not_detected_counter = 0
        self.recording_mode = False
        self.no_recording_gesture_detected_counter = 0
        self.voice_recorder = VoiceRecorder()
        self.voice_player = VoicePlayer()
        self.redis_manager = RedisManager()
        self.pdf_server = PDFServer(self.redis_manager)
        self.last_save_frame = -1
        self.save_cooldown = 50

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
    

    async def do_save_webpage(self):
        """Functionality to save the webpage."""
        if self.frame_number - self.last_save_frame < self.save_cooldown:
            return
        print("Saving webpage")
        beep(5)
        self.pdf_server.event.set()

        self.last_save_frame = self.frame_number


    async def process_capture_gesture(self, gesture):
        if gesture == OPEN_PALM_GESTURE:
            self.last_open_palm_frame = self.frame_number
        elif gesture == CLOSED_FIST_GESTURE:
            if self.frame_number - self.last_open_palm_frame < self.capture_frame_threshold:
                await self.do_save_webpage()
            self.last_open_palm_frame = -1

    def start_query(self):
        """Functionality to query the personal brain."""
        if self.recording_mode:
            return
        print("Starting recording")
        audio_thread = threading.Thread(target=alerts.play_notication)
        audio_thread.start()
        self.recording_mode = True
        self.voice_recorder.start_recording()
        

        
    def make_query(self, query_text):
        manager = RedisManager()
        return manager.ask_gpt(query_text)
        
    def stop_query(self):
        """Functionality to stop querying the brain."""
        if not self.recording_mode:
            return
        print("Stopping recording")
        self.recording_mode = False
        audio_thread = threading.Thread(target=alerts.play_success())
        audio_thread.start()
        query_text = self.voice_recorder.stop_recording()
        print("Query: " + query_text)
        response = self.make_query(query_text)
        self.voice_player.read_out_text(response)


    def do_flip_flashcard(self):
        """Functionality to flip the flashcard."""
        print("Flipping flashcard")

    def process_speak_gesture(self, gesture):
        if gesture == SPEAK_GESTURE:
            self.start_query()
        else:
            self.no_recording_gesture_detected_counter += 1
            if self.no_recording_gesture_detected_counter >= 2:
                self.stop_query()
                self.no_recording_gesture_detected_counter = 0

    def process_flip_gesture(self, gesture):
        if gesture == FLIP_GESTURE:
            self.do_flip_flashcard()
    
    async def main(self):
        task1 = asyncio.create_task(self.run())
        server_thread = threading.Thread(target=self.pdf_server.start_websocket_server, daemon=True)
        server_thread.start()

        await task1

    async def run(self):
        """Main loop for video capture and processing."""

        while self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                break

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            gesture = self.gesture_recogniser.process_image(rgb_image)

            if gesture:
                if gesture.score > self.gesture_threshold:
                    await self.process_capture_gesture(gesture.category_name)
                    self.process_speak_gesture(gesture.category_name)
                    self.process_flip_gesture(gesture.category_name)
                    self.no_recording_gesture_detected_counter = 0
                    #self.process_swipe_gesture(gesture.category_name)
            else:
                self.no_recording_gesture_detected_counter += 1
                if self.no_recording_gesture_detected_counter >= 2:
                    self.stop_query()
                    self.no_recording_gesture_detected_counter = 0
            
            if self.flash_card_mode:
                hand_landmarks = self.hand_landmarker.process_image(rgb_image)
                finger_tip_landmarks = None
                if hand_landmarks:
                    finger_tip_landmarks = self.hand_landmarker.get_finger_tip_landmarks(hand_landmarks)
                direction = self.track_pinkie_tip(finger_tip_landmarks)

            self.frame_number += 1

            await asyncio.sleep(0)



if __name__ == "__main__":
    video_capture_handler = VideoCaptureHandler()
    asyncio.run(video_capture_handler.main())
