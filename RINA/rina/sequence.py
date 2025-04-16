class SequenceNumber:
    """Handles sequence numbers and window operations for flow control"""
    def __init__(self, initial=0, max_value=2**16-1):
        self.value = initial
        self.max_value = max_value
    
    def next(self):
        """Get the next sequence number and increment"""
        current = self.value
        self.value = (self.value + 1) % (self.max_value + 1)
        return current
    
    def is_in_window(self, seq_num, base_seq, window_size):
        """Check if sequence number is within the window"""
        # Handle wrap-around for sequence numbers
        if base_seq + window_size > self.max_value:
            # Window wraps around
            return (seq_num >= base_seq) or (seq_num < ((base_seq + window_size) % (self.max_value + 1)))
        else:
            # Normal case
            return base_seq <= seq_num < base_seq + window_size