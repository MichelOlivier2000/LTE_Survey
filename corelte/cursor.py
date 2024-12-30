from dataclasses import dataclass

@dataclass
class Cursor:

    def __init__(self):
            
        self.first_non_null_idx = 0 
        self.first_non_null_reading_time = None



    