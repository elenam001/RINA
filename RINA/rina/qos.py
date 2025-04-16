class QoS:
    def __init__(self, bandwidth=None, latency=None, reliability=1):
        self.bandwidth = bandwidth
        self.latency = latency
        self.reliability = reliability

    def to_dict(self):
        return {
            "bandwidth": self.bandwidth,
            "latency": self.latency,
            "reliability": self.reliability
        }