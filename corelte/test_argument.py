from corelte.argument import Argument
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import unittest


NETWORK_ID = 1 # 1=Swisscom; 4=Orange-F
SURVEY_ID = 202


class TestArgument(unittest.TestCase):
    

    @classmethod
    def setUpClass(cls):
        cls.arg=Argument(NETWORK_ID, SURVEY_ID, verbose=False)
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        del cls.arg
        return super().tearDownClass()    
    
    """ def setUp(self):
        self.arg = Argument(NETWORK_ID, SURVEY_ID, verbose=False)
        return super().setUp()

    def tearDown(self):
        del self.arg
        return super().tearDown() """

    def test_attributes(self):
        self.assertEqual(self.arg.survey_dir, Path("/Users/mext/SURVEYS/Net_01/02/00/Survey_0202"))
        
    #@unittest.skip("Ce test fait double emploi avec le précédent.")
    def test_files_presence(self):
        self.assertTrue(Path.exists(self.arg.mp4_filename),"Le fichier mp4 est absent")
        self.assertTrue(Path.exists(self.arg.gps_filename),"Le fichier gps est absent")
        self.assertTrue(Path.exists(self.arg.arg_filename),"Le fichier arg.yaml est absent")
        
    def test_ocr_program_presence(self):
        self.assertTrue(Path.exists(self.arg.gps_filename),f"Le programme myocr est absent en {self.arg.myocr_swift_prg}")



def main():
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()