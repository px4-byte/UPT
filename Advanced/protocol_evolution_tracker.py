import logging
from typing import Dict, List
from datetime import datetime
import numpy as np

class ProtocolEvolutionTracker:
    def __init__(self):
        self.logger = logging.getLogger("UPTEvolutionTracker")
        self.versions = {}
        self.features_history = {}

    def track_protocol_evolution(self, traffic_over_time: Dict[datetime, List[bytes]]) -> Dict:
        """Track protocol evolution"""
        try:
            versions = {}
            for timestamp, packets in traffic_over_time.items():
                version, features = self._detect_version(packets)
                versions[timestamp] = version
                self.features_history[timestamp] = features
            evolution_path = self._analyze_evolution(versions)
            return {
                "historical_evolution": evolution_path,
                "predicted_changes": self._predict_future_evolution(evolution_path),
                "preparation_recommendations": ["update_rules"] if evolution_path else []
            }
        except Exception as e:
            self.logger.error(f"Evolution tracking error: {e}")
            return {}

    def _detect_version(self, packets: List[bytes]) -> tuple:
        """Detect protocol version from packets"""
        try:
            features = [len(p) for p in packets]
            avg_size = sum(features) / max(1, len(features))
            return ("v1.0" if avg_size < 100 else "v2.0", features)
        except Exception as e:
            self.logger.error(f"Version detection error: {e}")
            return ("v1.0", [])

    def _analyze_evolution(self, versions: Dict[datetime, str]) -> List:
        """Analyze protocol version changes"""
        return sorted(versions.items(), key=lambda x: x[0])

    def _predict_future_evolution(self, evolution_path: List) -> List:
        """Predict future protocol versions using moving average"""
        try:
            if not evolution_path:
                return []
            sizes = [self.features_history[timestamp][0] for timestamp, _ in evolution_path if self.features_history.get(timestamp)]
            if len(sizes) < 3:
                return ["v2.0"]
            ma = np.mean(sizes[-3:])  # 3-point moving average
            return ["v3.0" if ma > 150 else "v2.0"]
        except Exception as e:
            self.logger.error(f"Evolution prediction error: {e}")
            return ["v2.0"]