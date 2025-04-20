class SequenceNumber:
    def __init__(self, initial=0, max_seq=2**16):
        self.value = initial
        self.max_seq = max_seq
    
    def next(self):
        current = self.value
        self.value = (self.value + 1) % self.max_seq
        return current
    
    def is_in_window(self, seq_num, base, window_size):
        """Check if a sequence number is within a given window"""
        if base + window_size < self.max_seq:
            return base <= seq_num < base + window_size
        else:
            return seq_num >= base or seq_num < (base + window_size) % self.max_seq