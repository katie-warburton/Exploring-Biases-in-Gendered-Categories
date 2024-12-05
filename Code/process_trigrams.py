import time
import csv
import re
import requests
import gzip
import numpy as np
from collections import defaultdict

FINAL_PATTERN = re.compile(
    r"""
    ^(?:woman|man|male|female|women|men|females|males)\b      
    \s+                                                      
    (?:(?:\w+_(?:adj|noun|propn))|(?:in|of|and|for|by))       
    \s+                                                      
    (?:\w+_(?:noun|propn))                                
    |
    (?:\w+_(?:adj|noun|propn))                                
    \s+                                                       
    (?:(?:\w+_(?:adj|noun|propn))|(?:in|of|and|for|by))      
    \s+                                                       
    \b(?:woman|man|male|female|women|men|females|males)\b      
    |
    (?:\w+_(?:adj|noun|propn))                                
    \s+                                                       
    \b(?:woman|man|male|female|women|men|females|males)\b      
    \s+                                                       
    (?:\w+_(?:noun|propn))$   
    """,
    re.VERBOSE | re.IGNORECASE
)

def is_gendered_format(line):
    return bool(FINAL_PATTERN.match(line))

def get_counts(gram, freq_data, years, countDict):
    count_data = np.array([dat.split(',')[:2] for dat in freq_data], dtype=int).T
    year_data, count_data = count_data[0], count_data[1]
    
    overlap = np.isin(years, year_data)
    counts = np.zeros_like(years, dtype=int)
    counts[overlap] = count_data[np.isin(year_data, years)]
    
    if counts.any():
        countDict[gram] = countDict.get(gram, np.zeros_like(years)) + counts

def read_file(url, count_dict, years):
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with gzip.GzipFile(fileobj=response.raw, mode='rb', compresslevel=1) as f:
            for line in f:
                data = line.decode('utf-8').split('\t')
                trigram = data[0].lower()
                freq_data = data[1:]
                if is_gendered_format(trigram) and len(freq_data) != 0:
                    get_counts(trigram, freq_data, years, count_dict)
                        
              
def parse_trigrams(year_start=1900, year_end=2019):
    t0 = time.time()
    years = np.arange(year_start, year_end + 1)
    countDict = defaultdict(lambda: np.zeros_like(years))
    print('STARTING...')
    for i in range(6881):
        num = f'{i:05}'
        url = f'http://storage.googleapis.com/books/ngrams/books/20200217/eng/3-{num}-of-06881.gz'
        read_file(url, countDict, years)
        if i % 50 == 0:
            print(f'Processed {i+1} files')
            print(f'Time elapsed: {(time.time() - t0)/60:.2f} minutes')
            print('SAVING PROGRESS...')
            with open('csvs/trigrams-gendered.csv', 'w', encoding='utf-8', newline="") as f:
                writer = csv.writer(f,  delimiter=",")
                writer.writerow(['PHRASE', *years])
                for word, counts in countDict.items():
                    writer.writerow([word, *counts])
    print('DONE!')
    print(f'Time elapsed: {(time.time() - t0)/60:.2f} minutes')
    with open('trigrams-gendered-final.csv', 'w', encoding='utf-8', newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(['PHRASE', *years])
        for word, counts in countDict.items():
            writer.writerow([word, *counts])

if __name__ == '__main__':
    parse_trigrams()