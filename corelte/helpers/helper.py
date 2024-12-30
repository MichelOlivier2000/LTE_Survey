import csv

class Helper:

    
    def __init__(self):
        pass
    
    def save_csv_file(self, lines, filename):
        # writing to csv file
        with open(filename, 'w') as csvfile:

            # creating a csv writer object
            csvwriter = csv.writer(csvfile)

            # writing the fields
            if lines != None:
                if len(lines)>0:
                    csvwriter.writerow(lines[0].fields()) # should be static

                # writing the data rows
                for r in lines:
                    csvwriter.writerow(r.csv_row())

