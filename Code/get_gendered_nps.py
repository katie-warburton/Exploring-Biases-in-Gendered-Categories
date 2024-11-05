
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

def is_gendered(line):
    return bool(re.search(r'\s(women|men|woman|man|female|male|feminine|masculine|males|females)/[A-Z]', line)) 
    #return bool(re.search(r'\s(women|men|female|male|feminine|masculine)/[A-Z]', line)) 

def is_propers(line):
    return bool(re.search(r'/(NNP|NNPS)/[A-Za-z]+/0', line))

def gen_is_proper(line):
    return bool(re.search(r'(women|men|woman|man|female|male|feminine|masculine|males|females)/(NNP|NNPS)/', line))
    #return bool(re.search(r'(women|men|female|male|feminine|masculine)/(NNP|NNPS)/', line))

def read_gzipped_file(url):
    response = requests.get(url)
    if response.status_code == 200:
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz_file:
            decompressed_data = gz_file.read()
        content = decompressed_data.decode('utf-8').split('\n')
        return content
    
def parse_file(content):
    gendered_data = []
    for line in content:
        # might be better to just remove anything that has a proper noun in it 
        #if isGendered(line):
        if is_gendered(line) and not is_propers(line) and not gen_is_proper(line):
            gendered_data.append(line.split('\t'))
    return gendered_data

def get_gendered_noun_phrases():
    gendered_data = []
    t0 = time.time()
    for i in range(99):
        num = f'{i:02}'
        url = f'http://commondatastorage.googleapis.com/books/syntactic-ngrams/eng/nounargs.{num}-of-99.gz'
        content = read_gzipped_file(url)
        gendered_data += parse_file(content)
        if i % 5 == 0:
            print(f'Finished parsing {i+1} file(s).')
            print(f'{len(gendered_data):,} gendered noun phrases found.')
            print(f'Time elapsed: {(time.time() - t0)/60:.2f} min\n')
    return gendered_data


def convert_to_csv(gendered_data, years, fp):
    i = 0
    with open(f'{fp}/gendered_nps.csv', 'w', newline='', encoding='utf8') as csvFile:
        csv_writer = csv.writer(csvFile, delimiter='\t')
        csv_writer.writerow(['HEAD', 'PHRASE', 'DEPENDENCY', 'TOTAL', *years])
        for line in gendered_data:
            head = line[0]
            words = re.findall(r'(^|\s)([^/]+/)', line[1])
            phrase = ' '.join([LEMMATIZER.lemmatize(w[1][:-1].strip()) for w in words])
            total_count = int(line[2])
            counts = np.zeros(years.shape, dtype=int)
            count_data = np.array([dat.split(',') for dat in line[3:]], dtype=int).T
            overlap = np.where(np.isin(years, count_data[0]))[0]
            value_idx = np.where(np.isin(count_data[0], years))[0]
            counts[overlap] = count_data[1][value_idx]
            dependencies = line[1]
            csv_writer.writerow([head, phrase, dependencies, total_count, *counts.tolist()])

def get_gendered_data(fp, years):
    gendered_data = get_gendered_noun_phrases()
    convert_to_csv(gendered_data, years, fp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Syntactic Google Ngram.")
    parser.add_argument('output_file', type=str, help='The path to the output file')    
    parser.add_argument('--start_year', type=int, default=1900,
                        help='An optional argument that specified the year to start collecting ngram frequencies from (default is "1900")')
    parser.add_argument('--end_year', type=int, default=2009,
                        help='An optional argument that specified the year to stop collecting ngram frequencies from (default is "2009")')
    args = parser.parse_args()
    get_gendered_data(args.output_file, np.arange(args.start_year, args.end_year))