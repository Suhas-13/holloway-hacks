import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2
from voice_recorder import VoiceRecorder, VoicePlayer
from collections import deque
from mac_alerts import alerts
import cv2
import multiprocessing
import time
import threading
import asyncio
from beepy import beep
from server import PDFServer
from vectors.redis_handler import RedisManager

MINIMUM_FRAMES_SPEAK_NOT_DETECTED = 30
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
SCRAP_GESTURE = "Victory"

class VideoCaptureHandler:
    def __init__(self, queue):
        self.cap = cv2.VideoCapture(0)
        self.queue = queue
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
        self.queue.put("save")

        self.last_save_frame = self.frame_number


    async def process_capture_gesture(self, gesture):
        if self.recording_mode:
            return
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
        
    def scrap_query(self):
        """Functionality to scrap the recording."""
        if not self.recording_mode:
            return
        print("Scrapping recording")
        self.recording_mode = False
        audio_thread = threading.Thread(target=alerts.play_success())
        audio_thread.start()
        self.voice_recorder.stop_recording()


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
        if not query_text:
            self.voice_player.read_out_text("No query detected.")
            return
        response = self.make_query(query_text)
        self.voice_player.read_out_text(response)


    def do_flip_flashcard(self):
        """Functionality to flip the flashcard."""
        print("Flipping flashcard")

    async def process_speak_gesture(self, gesture):
        if gesture == SPEAK_GESTURE:
            self.start_query()
        else:
            self.no_recording_gesture_detected_counter += 1
            if self.no_recording_gesture_detected_counter >= MINIMUM_FRAMES_SPEAK_NOT_DETECTED:
                self.stop_query()
                self.no_recording_gesture_detected_counter = 0


    def process_scrap_recording_gesture(self, gesture):
        if gesture == SCRAP_GESTURE:
            self.scrap_query()
    
    async def main(self):
        await self.run()

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
                    await self.process_speak_gesture(gesture.category_name)
                    self.process_scrap_recording_gesture(gesture.category_name)
                    self.no_recording_gesture_detected_counter = 0
                    #self.process_swipe_gesture(gesture.category_name)
            else:
                self.no_recording_gesture_detected_counter += 1
                if self.no_recording_gesture_detected_counter >= MINIMUM_FRAMES_SPEAK_NOT_DETECTED:
                    self.stop_query()
                    self.no_recording_gesture_detected_counter = 0
            
            if self.flash_card_mode:
                hand_landmarks = self.hand_landmarker.process_image(rgb_image)
                finger_tip_landmarks = None
                if hand_landmarks:
                    finger_tip_landmarks = self.hand_landmarker.get_finger_tip_landmarks(hand_landmarks)
                direction = self.track_pinkie_tip(finger_tip_landmarks)

            self.frame_number += 1


def video_capture_process(queue):
    video_capture_handler = VideoCaptureHandler(queue)
    asyncio.run(video_capture_handler.main())

def pdf_server_process(queue):
    server = PDFServer(queue)  # Assuming None for redis_manager
    server.start_websocket_server()

    


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    video_process = multiprocessing.Process(target=video_capture_process, args=(queue,))
    server_process = multiprocessing.Process(target=pdf_server_process, args=(queue,))

    # Starting processes
    video_process.start()
    server_process.start()

    # Waiting for processes to finish (if they ever do)
    video_process.join()
    server_process.join()
