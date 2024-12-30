from corelte.dict_list_handler import DictListHandler
from corelte.argument import Argument, OCRMode, MYOCR_SWIFT_PRG
from corelte.cursor import Cursor
from corelte.datetime_local import convert_local_to_utc, convert_utc_to_local
from corelte.reading import Reading
import cv2 
from datetime import datetime, timedelta
import glob
import os, os.path
from pathlib import Path
from PIL import Image, ImageEnhance
import pytesseract # type: ignore
from skimage.metrics import structural_similarity as compare_ssim
import subprocess
from tqdm import tqdm
from typing import Tuple, List, Optional
from dataclasses import dataclass, field

# types listes de fichiers avec l'index de frame et un nom de fichier
File_to_ocr = list[(int, str)] # index, filename
Files_to_ocr = list[File_to_ocr]

@dataclass
class Screencast:

    argument: Argument
    
    linesMp4: List[Reading] = field(default_factory=list)
    frames_to_ocr: Files_to_ocr = field(default_factory=list) 
    times_to_ocr: Files_to_ocr = field(default_factory=list)
    cursor: Cursor = field(default_factory=Cursor)
    hold_frame_reading: Reading = field(default_factory=lambda: Reading(0))
    hold_frame_time: Optional[datetime] = None
    mp4CreateDate: Optional[datetime] = None

    def __post_init__(self):
        # Move initialization logic from __init__ to __post_init__
        cmd = f"exiftool \"{self.argument.mp4_filename}\" | grep \"Media Create Date\""
        stream = os.popen(cmd)
        date_str = stream.read().replace('\n','')[-19:]
        self.mp4CreateDate = datetime.strptime(date_str,'%Y:%m:%d %H:%M:%S')

    def split_video_into_frames(self):

        if self.argument.erase_png:
            cmd = f'rm {self.argument.survey_img_dir}/*.png'
            subprocess.call(cmd, shell=True)

        # Si le job est déjà fait, on saute la suite
        lst = glob.glob( str(self.argument.survey_img_dir / '*.png'))
        if len(lst) > 0 : return 

        # Create an img folder if it doesn't exist (-p)
        subprocess.call(f'mkdir -p {self.argument.survey_img_dir}', shell=True)

        # Exctract 1 frame per second
        # crop = w,h,x,y
        # Attention, la résolution du screencast est de 886x1920
        # Extrait Les champs [Band, Bandwidth, CellId]
        #  "fps=1,{crop_lte_ios_18},format=gray,negate,gblur=sigma=1[blurred]" 

        match self.argument.ocr_mode:
            case OCRMode.TESSERACT, OCRMode.MYOCR: 
                crop_lte_ios_18 = 'crop=887:1030:0:0'
                subprocess.call(f'ffmpeg -i  {self.argument.mp4_filename} \
                                -vf \
                                "fps=1,{crop_lte_ios_18},format=gray,negate" \
                                {self.argument.survey_img_dir}/lte_%06d.png', shell=True)

            case OCRMode.MYOCR_PLUS: 
                   
                # crop_tac = 'crop=300:180:580:200'
                # crop_lte = 'crop=250:400:560:600'
                
                # dimension de la fenêtre sur les valeurs de l'horloge
                width_tim = 105
                height_tim = 40
                crop_tim = f'crop={width_tim}:{height_tim}:64:25'
                """new_width_tim = int(width_tim * self.argument.scale_factor)
                new_height_tim = int(height_tim * self.argument.scale_factor)
                scale_filter_tim = f'scale={new_width_tim}:{new_height_tim}' """
                # En fait, réduire les image de l'horloge n'apporte pas de gain de performance
                # {scale_filter_tim},
                # croppe la zone de l'heure, les 120 premières secondes
                subprocess.call(f'ffmpeg -i  {self.argument.mp4_filename} \
                                -vf \
                                "fps=1,{crop_tim},format=gray,negate" -t {self.argument.time_scan_probe} \
                                {self.argument.survey_img_dir}/tim_%06d.png', shell=True)
                
                # dimension de la fenêtre sur les valeurs LTE
                width_lte = 340
                height_lte = 840
                crop_lte = f'crop={width_lte}:{height_lte}:540:190'
                new_width_lte = int(width_lte * self.argument.scale_factor)
                new_height_lte = int(height_lte * self.argument.scale_factor)
                scale_filter_lte = f'scale={new_width_lte}:{new_height_lte}'

                # croppe la zone des paramètres LTE
                subprocess.call(f'ffmpeg -i  {self.argument.mp4_filename} \
                                -vf \
                                "fps=1,{crop_lte},{scale_filter_lte},format=gray,negate" \
                                {self.argument.survey_img_dir}/lte_%06d.png', shell=True)
        
                # croppe la zone TAC
                """             
                        subprocess.call(f'ffmpeg -i  {self.argument.mp4_filename} \
                                -vf \
                                "fps=1,{crop_tac},format=gray,negate,gblur=sigma=1[blurred]" \
                                {self.argument.survey_img_dir}/tac_%06d.png', shell=True) 
                                """

   # Function to compare two images
    def compare_frames(self, imageA, imageB):

        # Convert images to grayscale
        grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
        grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
        
        # Compute SSIM between two images
        (score, diff) = compare_ssim(grayA, grayB, full=False)
        
        return score


    def create_list_of_frames_to_ocr(self):
        """
        On crée une liste de fichiers frame à OCRiser qu'on sauve dans un fichier .txt
        la liste est aussi sauvée dans un fichier .json (avec la donnée key) pour pouvoir être réexploitée lors d'un run ultérieur
        """

#        def create_list(list: list[Frame_to_ocr], filter, score_min) -> None:
        def create_list(list: Files_to_ocr, filter, score_min) -> None:

            files = glob.glob(str(filter))
            files.sort() 
            

            img_prev = None
            for i, fname in tqdm(enumerate(files)):
                file_idx = i+1
                img = cv2.cvtColor(cv2.imread(fname), cv2.COLOR_BGR2GRAY)
                if i == 0: 
                    list.append((file_idx, fname))
                    #list[file_idx] = fname
                    #frame = Frame_to_ocr(key=file_idx, fname=fname)
                    #list.append(frame)
                    img_prev = img
                    continue

                # Compute SSIM between two images
                score = compare_ssim(img, img_prev, full=False)

                # si le score est moins que 1 - une petite marge, on l'ajoute à la liste car l'image est différente de la précédente.
                print(f"file_idx={file_idx} score={score}")
                if score < score_min:  # or i <= 30: #0.999: # Debug, on scanne les 30 premières secondes
                    list.append((file_idx, fname))
                    # list.append({'key':file_idx, 'fname':fname})

                img_prev = img

        
        #def save_to_txt(list : list[Frame_to_ocr], fname: Path):
        def save_to_txt(list : Files_to_ocr, fname: Path):
            with open(str(fname), 'w') as file:
                for element in list:
                    file.write(element[1] + '\n')
                #for element in list.values:
                 #   file.write(element['fname'] + '\n')  

        # utilitaire json
        h = DictListHandler()

        # Si la liste des frames à traiter est déjà faite, on la recharge ici
        if self.argument.tmp_frames_to_ocr_filename_json.exists():
            self.frames_to_ocr = h.read_from_json(self.argument.tmp_frames_to_ocr_filename_json)
        else:
            create_list(self.frames_to_ocr, self.argument.survey_img_dir / 'lte_*.png', score_min=0.999)
            save_to_txt(self.frames_to_ocr, self.argument.tmp_frames_to_ocr_filename_txt)
            h.save_to_json(self.frames_to_ocr, self.argument.tmp_frames_to_ocr_filename_json)

        # Si la liste des times à traiter est déjà faite, on la recharge ici
        if self.argument.tmp_times_to_ocr_filename_json.exists():
            self.times_to_ocr = h.read_from_json(self.argument.tmp_times_to_ocr_filename_json)
        else:
            create_list(self.times_to_ocr, self.argument.survey_img_dir / 'tim_*.png', score_min=0.95) # fine tuning 😀
            save_to_txt(self.times_to_ocr, self.argument.tmp_times_to_ocr_filename_txt)
            h.save_to_json(self.times_to_ocr, self.argument.tmp_times_to_ocr_filename_json)


    # Fonction pour effectuer l'OCR sur une région spécifique de l'image
    def selective_ocr_on_one_frame(self, image_path, region):
        """
        Args:
        - image_path: Chemin de l'image.
        - region: Tuple (left, top, right, bottom) définissant la région à analyser.

        Returns:
        - Le texte extrait de la région définie de l'image.
        """
        try:
            # Ouvrir l'image avec PIL
            image = Image.open(image_path)

            # Extraire la région spécifiée de l'image
            cropped_image = image.crop(region)

            # Augmente la brillance
            enhancer = ImageEnhance.Brightness(cropped_image)
            img = enhancer.enhance(2)
            #img.show()

            # Effectuer l'OCR sur l'image rognée
            text = pytesseract.image_to_string(img, config='--psm 13')

            return text
        except Exception as e:
            return f'Une erreur s\'est produite: {str(e)}'

    def process_ocr_frames_time(self):
        """
        Pour une raison de mauvais contraste, Tesseract se plante (parfois) dans la lecture de l'heure affichée en haut à gauche de l'image.
        L'amélioration consiste à scanner cette région avec d'autres paramètres pour améliorer le contraste à cet endroit précis.
        """
        # Définir la région à analyser : (left, top, right, bottom)
        region = (60, 25, 170, 65)  # rectangle autour de l'heure de l'iphone

        filter = self.argument.survey_img_dir / 'lte_*.png'
        lst = glob.glob(str(filter))
        lst.sort() 

        # seules les env. 100 premières lignes nous intéressent pour synchroniser l'heure

        line_range = min(100, len(lst))

        for i in range(line_range):
            nb_str = f'{i+1}'.zfill(6)  
            
            filename = f'{self.argument.survey_img_dir}/lte_{nb_str}.png'  
            time_str = self.selective_ocr_on_one_frame(filename, region)

            # Ajoute l'heure en début de fichier    
            filename = f'{self.argument.survey_img_dir}/lte_{nb_str}.txt'  
            with open(filename,'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.write(time_str + '\n' + content)
                f.close()

    def process_tesseract_on_frames(self):

        cmd = f'rm {self.argument.survey_img_dir}/*.txt'
        if self.argument.erase_txt:
            subprocess.call(cmd, shell=True)

        # Si déjà fait, on saute la suite
        list = glob.glob(str(self.argument.survey_img_dir / '*.txt'))
        if len(list)>0: return
        
        subprocess.call(f'find {self.argument.survey_img_dir} '
                        "-type f -name '*.png' | sort | parallel --progress 'tesseract {} {.} --psm 4 --dpi 300';", shell=True)
        
            # La seconde passe lit uniquement l'heure affichée, mais de manière plus fiable.
        print("procède à l'analyse ocr de l'heure affichée sur le screencast")
        self.process_ocr_frames_time()

    def needs_to_redo_ocr(self):
        # Efface tous les ficher txt, si option active
        if self.argument.erase_txt:
            cmd = f'rm {self.argument.survey_img_dir}/*.txt'
            subprocess.call(cmd, shell=True)

        # Si le processus est déjà fait, on saute la suite
        lst = glob.glob(f'{self.argument.survey_img_dir}/*.txt')
        return len(lst) == 0

    def process_myocr_on_frames(self):
        """
        On OCRise la liste des frames à traiter 
        """
        if not self.needs_to_redo_ocr():
            return

        #time        
        """ subprocess.call(f"find {self.argument.survey_img_dir} "
                        f"-type f -name 'tim_*.png' | sort | parallel --progress '{self.argument.myocr_swift_prg} " 
                        "{} {.}';", shell=True) """
        subprocess.call(f"cat {self.argument.tmp_times_to_ocr_filename_txt} | parallel --progress '{MYOCR_SWIFT_PRG} " 
                        "{} {.}';", shell=True)

        #lte
        subprocess.call(f"cat {self.argument.tmp_frames_to_ocr_filename_txt} | parallel --progress '{MYOCR_SWIFT_PRG} " 
                        "{} {.}';", shell=True)

 
 #      subprocess.call(f"find {self.argument.survey_img_dir} "
 #                       "-type f -name 'tac_*.png' | sort | parallel --progress '/Users/mext/kDrive/DEV/LTE/Swift/MyOCR/myocr {} {.}';", shell=True)


    # find words in an array of words
    def find_word(self, row,word,delta):
        try: found = row.index(word)
        except:
            #print('word not found. file_idx=', row.file_idx)
            #return ''
            return None
        try: return row[found + delta]
        except:
            #print('word found but delta out of bounds. file_idx=', row.file_idx)
            #return ''
            return None

    def filtrer_caracteres(self, texte):
        return ''.join([car for car in texte if car in [':', '0','1','2','3','4','5','6','7','8','9']])

    def convert_text_to_list_of_words(self, filename):
        words=[]
        try: # pour une raison inconnue, myocr ne renvoie pas de fichier txt pour le frame 000000
            with open(str(filename),'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.replace('\n','')
                    words += line.split(' ')
        except:
            pass            

        # Ôte les mots vides   
        for w in words[:]: # crée un copie non mutée pour l'énumération
            if w.strip() == '':
                words.remove(w)

        return words

    def extract_reading_from_frame(self, r: Reading, frame_fname: str) -> Tuple[Reading, bool]:

        # extrait la liste des mots du résultat de l'OCR    
        words = self.convert_text_to_list_of_words(frame_fname)

        # si liste trop petite c'est du garbage  
        if len(words) < 5: return r, False  

        # la valeur TAC est toujours présente
        r.tac = int(words[1]) if str(words[1]).isnumeric() else 0 

        # la position numéro de téléphone dans la liste peut varier. Si ce numéro est absent, le frame n'a aucun sens
        tel_position = 3 if len(words[3]) > 8 else 4 if len(words[4]) > 8 else 0
        if tel_position == 0: return r, False

        # le reste des valeurs se positionnent par rapport au numéro de téléphone
        for m in range(tel_position+1, len(words)):
            if not str(words[m]).isnumeric(): continue
            if m == tel_position+1:
                r.band = int(words[m]) 
            if m == tel_position + 4:
                r.cellid = int(words[m]) if len(words[m]) > 5 else 0 # le cell_if a en général 8 positions, et 7 dans de rare cas.
            if m == tel_position + 5:
                r.pci = int(words[m])
        
        return r, True

    def extract_reading_from_hold(self, r: Reading) -> Reading:

        # Les données n'ont pas changé depuis la dernière frame.
        r.band = self.hold_frame_reading.band
        r.cellid = self.hold_frame_reading.cellid
        r.pci = self.hold_frame_reading.pci
        r.tac = self.hold_frame_reading.tac
        return r


    def read_filtred_frames_files_into_linesMp4(self):

        if self.argument.ocr_mode != OCRMode.MYOCR_PLUS:
            raise Exception("Seul le mode OCR_PLUS peut passer par là.")

        # On parcours les frames png
        filter = self.argument.survey_img_dir / 'lte_*.png'
        lst = glob.glob(str(filter))
        lst.sort()
        
        frame_to_ocr_idx = 0
        time_to_ocr_idx = 0

        for i in range(len(lst)):
            
            file_idx = i+1 # décalage entre les listes python et les indexes de fichier

            r = Reading(self.argument.survey_id)
            r.file_idx = file_idx

            # Est-ce que cette frame a été OCR-isée?    
            #file_entry = self.frames_to_ocr[frame_to_ocr_idx]
            #file_entry = self.frames_to_ocr[frame_to_ocr_idx]
            
            file_entry, fname = self.frames_to_ocr[frame_to_ocr_idx]
            #if file_entry['key'] == file_idx:

            if file_entry == file_idx:

                # on incrémente l'index des frames ocr-isées    
                frame_to_ocr_idx += (frame_to_ocr_idx < len(self.frames_to_ocr) - 1) 

                # Lit les données LTE depuis le fichier txt
                #r, success = self.extract_reading_from_frame(r, Path(file_entry['fname']).with_suffix('.txt'))
                r, success = self.extract_reading_from_frame(r, Path(fname).with_suffix('.txt'))
                
                # Si les données ne sont pas valides, on abandonne cette mesure
                # if r == None:continue
                if success:
                    # On retient cette mesure pour les suivantes qui seraient identiques
                    self.hold_frame_reading.__dict__ = r.__dict__.copy()

            else:
                # Les données n'ont pas changé depuis la dernière frame.
                r = self.extract_reading_from_hold(r)


            # Lit les données de temps depuis le fichier txt sur les 90 premières secondes
            if file_idx <= self.argument.time_scan_probe:

                # Est-ce que cette frame a été ocr-isée?
                # BUG l'index time_to_ocr_idx reste toujours à zéro
                #file_entry = self.times_to_ocr[time_to_ocr_idx]
                file_entry, fname = self.times_to_ocr[time_to_ocr_idx]    
                #if file_entry['key'] == file_idx:    
                if file_entry == file_idx:    

                    # On incrémente l'index des frames ocr-isées    
                    time_to_ocr_idx += (time_to_ocr_idx < len(self.times_to_ocr) - 1) 

                    #filename = self.argument.survey_img_dir / f'tim_{str(file_idx).zfill(6)}.txt'
                    words = self.convert_text_to_list_of_words(Path(fname).with_suffix('.txt'))
                    if len(words)>0 :
                        # l'heure est le premier élément de la liste            
                        time_str = self.filtrer_caracteres(words[0])
                        print(f' i={i} words[0]={words[0]} time_str={time_str}')
                        try:
                            r.reading_time = datetime.strptime(time_str, '%H:%M').replace(year=self.mp4CreateDate.year, month=self.mp4CreateDate.month, day=self.mp4CreateDate.day)    
                            self.hold_frame_time = r.reading_time
                        except:
                            # On debug... 
                            #r.reading_time = None
                            r.reading_time = self.hold_frame_time # debug
                            print(f'Planté en i={i} time_str={time_str}')
                else:
                    r.reading_time = self.hold_frame_time

            self.linesMp4.append(r) # Même en cas d'erreur, on ajoute la ligne


    def read_frame_files_into_linesMp4(self):

        if self.argument.ocr_mode == OCRMode.MYOCR_PLUS:
            raise Exception("le mode OCR_PLUS n'a rien à faire là.")

        # Lit les données de l'horloge du screencast pour ajuster le temps
        filter = self.argument.survey_img_dir / 'lte_*.txt'
        lst = glob.glob(str(filter))
        lst.sort()

        for i in range(len(lst)):
            nb_str = f'{i+1}'.zfill(6)  
            filename = self.argument.survey_img_dir / f'lte_{nb_str}.txt' 
            words=[]
            words = self.convert_text_to_list_of_words(filename)
            
            r = Reading(self.argument.survey_id)

            r.file_idx = i+1
            # Récupère les autres données de mesure
            
            if self.argument.ocr_mode == OCRMode.TESSERACT:
                r.cellid = self.find_word(words, 'Cell',2)
                r.band = self.find_word(words, 'Band',1)
                r.pci = self.find_word(words, 'pci', 1)
                r.tac = self.find_word(words, 'TAC:',1)
                r.carrier = self.find_word(words, 'Carrier:', 1)
            
            if self.argument.ocr_mode == OCRMode.MYOCR:
                r.cellid = self.find_word(words, 'Cell',2)
                r.band = self.find_word(words, 'Band',1)
                r.pci = self.find_word(words, 'pci', 1)
                r.tac = self.find_word(words, 'TAC:',6)
                r.carrier = self.find_word(words, 'Carrier:', 6)
            
            r.check_errors()

            # Copie l'heure et la date de la mesure
            time_str = ''        
            if len(words)>0 :
                # l'heure est le premier élément de la liste            
                time_str = self.filtrer_caracteres(words[0])
                print(f' i={i} words[0]={words[0]} time_str={time_str}')
            try:
                r.reading_time = datetime.strptime(time_str, '%H:%M').replace(year=self.mp4CreateDate.year, month=self.mp4CreateDate.month, day=self.mp4CreateDate.day)    
            except:
                print(f'Planté en i={i} time_str={time_str}')
            finally:
                self.linesMp4.append(r) # Même en cas d'erreur, on ajoute la ligne

    def set_precise_time_in_linesMp4_rows(self):
        """
        Ajoute l'heure à la seconde près sur chaque frame du screencast
        """
        first_non_null_mp4_reading_time = None
        first_non_null_mp4_idx = -1
        first_minute_change_dt = None
        first_minute_change_idx = -1
        
        # 1. On définit les premières valeurs ou l'heure est lisible et le passage d'une minute à l'autre
        for i in range(len(self.linesMp4)):
            
            r = self.linesMp4[i]

            if r.reading_time == None: 
                continue

            # défini l'index de la première heure lisible sur le screencast
            # BUG self.linesMp4[0] indique l'heure actuelle, ce qui est faux
            # DEBUG on filtre lles dates nulle
            if r.reading_time != None and r.reading_time != datetime.min:
                if (first_non_null_mp4_reading_time == None): 
                    first_non_null_mp4_reading_time = r.reading_time
                    first_non_null_mp4_idx = i

                # défini l'index où pour la première fois, l'heure avance d'une minute    
                if (first_minute_change_dt == None) and (r.reading_time != first_non_null_mp4_reading_time):
                    first_minute_change_dt = r.reading_time
                    first_minute_change_idx = i
        
        print(f'first_non_null_mp4_reading_time {first_non_null_mp4_reading_time}')
        print(f'first_non_null_idx {first_non_null_mp4_idx}')
        print(f'first_minute_change_dt {first_minute_change_dt}')
        print(f'first_minute_change_idx {first_minute_change_idx}')
        print(f'-----------------')

        # 2. Ajoute la précision en seconde des mesures
        if first_minute_change_dt != None:
            
            dd = self.linesMp4[first_non_null_mp4_idx].reading_time

            # Il peut arriver que la detection de la minute qui avance prenne du temps
            # ...

            second = 60 - first_minute_change_idx + first_non_null_mp4_idx
            dd = dd.replace(second = second)
            
            for i in range(first_non_null_mp4_idx, len(self.linesMp4)):    
                r = self.linesMp4[i]
                r.reading_time = dd
                dd += timedelta(seconds=1)

        # 3. Ajuste à la seconde l'heure de la première mesure
        first_non_null_mp4_reading_time = self.linesMp4[first_non_null_mp4_idx].reading_time

        # 4. Index de la première mesure exploitable
        self.cursor.first_non_null_idx = first_non_null_mp4_idx

        # 5. Heure précise de la première mesure exploitable
        self.cursor.first_non_null_reading_time = first_non_null_mp4_reading_time
        
        # BUG first_non_null_mp4_reading_time est faux, il affiche la date du jour...
        print(f'first_non_null_mp4_reading_time {first_non_null_mp4_reading_time}')


