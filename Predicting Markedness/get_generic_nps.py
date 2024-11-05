
import time
import csv
import re
import io
import requests
import gzip
import numpy as np
import argparse
from nltk.stem import WordNetLemmatizer
LEMMATIZER = WordNetLemmatizer()


with open('Predicting Markedness/role nouns.txt', 'r') as f:
    role_nouns = f.read().split('\n')
ROLE_NOUNS = [noun.split(',')[0].lower() for noun in role_nouns]

def is_propers(line):
    return bool(re.search(r'/(NNP|NNPS)/[A-Za-z]+/0', line))

def read_gzipped_file(url):
    response = requests.get(url)
    if response.status_code == 200:
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz_file:
            decompressed_data = gz_file.read()
        content = decompressed_data.decode('utf-8').split('\n')
        return content
    
def parse_file(content):
    data = []
    for line in content:
        # might be better to just remove anything that has a proper noun in it 
        #if isGendered(line):
        line = line.split('\t')
        if len(line) > 1 and not is_propers(line[1]):
            words = re.findall(r'(^|\s)([^/]+/)', line[1])
            phrase = ' '.join([w[1][:-1] for w in words])
            if phrase.lower() in ROLE_NOUNS:
                data.append([phrase.lower(), line[2], *line[3:]])
            elif phrase.lower() + 's' in ROLE_NOUNS:
                data.append([phrase.lower() + 's', line[2], *line[3:]])
    return data

def get_noun_phrases():
    data = []
    t0 = time.time()
    for i in range(99):
        num = f'{i:02}'
        url = f'http://commondatastorage.googleapis.com/books/syntactic-ngrams/eng/nounargs.{num}-of-99.gz'
        content = read_gzipped_file(url)
        data += parse_file(content)
        if i % 5 == 0:
            print(f'Finished parsing {i+1} file(s).')
            print(f'{len(data):,} noun phrases found.')
            print(f'Time elapsed: {(time.time() - t0)/60:.2f} min\n')
    return data


def convert_to_csv(data, years, fp):
    i = 0
    with open(f'{fp}/role_nps.csv', 'w', newline='', encoding='utf8') as csvFile:
        csv_writer = csv.writer(csvFile, delimiter='\t')
        csv_writer.writerow(['ROLE NOUN', 'TOTAL', *years])
        for line in data:
            phrase = ' '.join([LEMMATIZER.lemmatize(w) for w in line[0].split()])
            total_count = int(line[1])
            counts = np.zeros(years.shape, dtype=int)
            count_data = np.array([dat.split(',') for dat in line[2:]], dtype=int).T
            overlap = np.where(np.isin(years, count_data[0]))[0]
            value_idx = np.where(np.isin(count_data[0], years))[0]
            counts[overlap] = count_data[1][value_idx]
            csv_writer.writerow([phrase, total_count, *counts.tolist()])

def get_data(fp, years):
    data = get_noun_phrases()
    convert_to_csv(data, years, fp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Syntactic Google Ngram.")
    parser.add_argument('output_file', type=str, help='The path to the output file')    
    parser.add_argument('--start_year', type=int, default=1900,
                        help='An optional argument that specified the year to start collecting ngram frequencies from (default is "1900")')
    parser.add_argument('--end_year', type=int, default=2009,
                        help='An optional argument that specified the year to stop collecting ngram frequencies from (default is "2009")')
    args = parser.parse_args()
    get_data(args.output_file, np.arange(args.start_year, args.end_year))