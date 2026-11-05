from vpython import rate

from core_Features import FeatureProcessor
from core_IMU import IMUProcessor
from core_Serial import RateMeter, SerialReceiver
from core_interface import CoreInterface

DEFAULT_COM_NUMBER = 6
FPS_LIMIT = 60


class CoreServer:
    """Orchestre l'application ; VPython reste responsable du serveur web local."""

    def __init__(self):
        self.receiver = None
        self.imu_processor = None
        self.feature_processor = None
        self.interface = CoreInterface(
            on_connect=self.connect,
            on_disconnect=self.disconnect,
            default_com=DEFAULT_COM_NUMBER,
        )
        self.fps_meter = RateMeter()

    def connect(self, port):
        self.interface.clear()
        is_recording = lambda: not self.interface.graphs.paused
        imu_processor = IMUProcessor(
            on_sample=self.interface.on_sample,
            is_recording=is_recording,
        )
        feature_processor = FeatureProcessor(is_recording=is_recording)
        self.interface.graphs.on_pause_change = self._on_pause_change
        receiver = SerialReceiver(
            port,
            on_imu_frame=imu_processor.submit_frame,
            on_feature_frame=feature_processor.submit_frame,
            on_other_frame=self._on_other_frame,
        )
        imu_processor.send_date = receiver.send_date
        feature_processor.send_date = receiver.send_date
        imu_processor.start()
        feature_processor.start()

        self.imu_processor = imu_processor
        self.feature_processor = feature_processor
        self.receiver = receiver
        if receiver.start():
            return True

        self.disconnect()
        return False

    def _on_pause_change(self, paused):
        if paused and self.feature_processor is not None:
            self.feature_processor.pause_recording()

    @staticmethod
    def _on_other_frame(frame):
        print(f"[Série] Message non reconnu : {frame.decode('utf-8', errors='replace')}")

    def disconnect(self):
        receiver, self.receiver = self.receiver, None
        imu_processor, self.imu_processor = self.imu_processor, None
        feature_processor, self.feature_processor = self.feature_processor, None
        if receiver is not None:
            receiver.stop()
        if imu_processor is not None:
            imu_processor.stop()
        if feature_processor is not None:
            feature_processor.stop()

    def run(self):
        print(f"[*] Interface lancée à {FPS_LIMIT} FPS, en attente de connexion...")
        self.fps_meter.start()
        try:
            while True:
                rate(FPS_LIMIT)
                self.fps_meter.tick()
                receiver = self.receiver
                feature_processor = self.feature_processor
                if receiver is None or feature_processor is None:
                    continue
                if receiver.connection_lost:
                    self.interface.visualizer.disconnect(
                        f"Connexion perdue avec {self.interface.visualizer.port_name}", False
                    )
                    continue
                _, feature_sample = feature_processor.snapshot()
                self.interface.refresh(
                    receiver.get_imu_frequency(),
                    receiver.get_feature_period_ms(),
                    self.fps_meter.stable_rate(),
                    feature_sample,
                )
        except KeyboardInterrupt:
            print("\n[*] Arrêt demandé...")
        finally:
            self.disconnect()
            self.fps_meter.stop()


def run():
    CoreServer().run()
