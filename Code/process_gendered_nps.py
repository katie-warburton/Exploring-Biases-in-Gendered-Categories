import pandas as pd
import csv
import numpy as np
import nltk
import random
import re
from nltk.stem import WordNetLemmatizer
LEMMATIZER = WordNetLemmatizer()


NUMBER_WORDS = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 
                'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 
                'seventy', 'eighty', 'ninety', 'hundred', 'thousand', 'million', 'billion', 'trillion']

multi_num_regex = r'\b(' + r'|'.join(NUMBER_WORDS) + r'){2,}' + r'\b'

def process_nps(fp, year, min_freq=1):
    year = str(year)
    df = pd.read_csv(f'{fp}/gendered_nps.csv', sep='\t', usecols=lambda column: column != 'DEPENDENCY')
    condensed_df = df.groupby(['HEAD', 'PHRASE'], as_index=False).sum()
    condensed_df = condensed_df[condensed_df[year] >= min_freq]
    condensed_df.rename(columns={year: 'FREQ'}, inplace=True)
    return condensed_df[['HEAD', 'PHRASE', 'FREQ']]


def combine_on_gender(df):
    df['PHRASE'] = df['PHRASE'].str.replace(r'\bmen\b|\bmale\b|\bmasculine\b|\bman\b|\bmales\b', '<M>', regex=True)
    df['PHRASE'] = df['PHRASE'].str.replace(r'\bwomen\b|\bfemale\b|\bfeminine\b|\bwoman\b|\bfemales\b', '<W>', regex=True)
    #df['PHRASE'] = df['PHRASE'].str.replace(r'\bmale\b|\bmasculine\b|\bman\b', '<M>', regex=True)
    #df['PHRASE'] = df['PHRASE'].str.replace(r'\bfemale\b|\bfeminine\b|\bwoman\b', '<W>', regex=True)

    # I don't want to combine a/the/this/that/etc. with <M> or <W> if they are the only words in the phrase
    # because I want to keep the total singleton counts for <M> and <W> separate
    df['PHRASE'] = df['PHRASE'].apply(lambda p: re.sub(r'\ba |\bthe |\bthis |\bthat |\bthose |\bthese ', r'', p) if len(p.split()) > 2 else p)

    df['HEAD'] = df['HEAD'].str.replace(r'\bmen\b|\bmale\b|\bmasculine\b|\bman\b|\bmales\b', '<M>', regex=True)
    df['HEAD'] = df['HEAD'].str.replace(r'\bwomen\b|\bfemale\b|\bfeminine\b|\bwoman\b|\bfemales\b', '<W>', regex=True)
    df['HEAD'] = df['HEAD'].apply(lambda h: LEMMATIZER.lemmatize(h))
    #df['HEAD'] = df['HEAD'].str.replace(r'\bmale\b|\bmasculine\b|\bman\b', '<M>', regex=True)
    #df['HEAD'] = df['HEAD'].str.replace(r'\bfemale\b|\bfeminine\b|\bwoman\b', '<W>', regex=True)


    return df.groupby(['HEAD', 'PHRASE'], as_index=False).sum()

def separate_nps(df):
    stop_words = nltk.corpus.stopwords.words('english')  + ['several', 'many', 'numerous', 'fewer', ] + NUMBER_WORDS
    other = []
    modified_m_or_w = []
    m_and_w = []
    gendered_np = []
    all_nps = []
    for _, j in df.iterrows():
        non_stop_words = [w for w in j['PHRASE'].split() if w not in stop_words]
        if non_stop_words == ['<M>'] or non_stop_words == ['<W>']:
            other.append((j['HEAD'], j['PHRASE'], j['FREQ']))
            all_nps.append((j['HEAD'], j['PHRASE'], j['FREQ']))
        elif '<M>' in non_stop_words and '<W>' in non_stop_words: # don't want these in ALL_NPS!
            m_and_w.append((j['HEAD'], j['PHRASE'], j['FREQ']))
        elif non_stop_words.count('<M>') > 1 or non_stop_words.count('<W>') > 1:
            other.append((j['HEAD'], j['PHRASE'], j['FREQ']))
            all_nps.append((j['HEAD'], j['PHRASE'], j['FREQ']))
        elif re.search(r'\d+', j['PHRASE']) or re.search(multi_num_regex, j['PHRASE']):
            other.append((j['HEAD'], j['PHRASE'], j['FREQ']))
            all_nps.append((j['HEAD'], j['PHRASE'], j['FREQ']))
        elif len(non_stop_words) != len(j['PHRASE'].split()):
            other.append((j['HEAD'], j['PHRASE'], j['FREQ']))
            all_nps.append((j['HEAD'], j['PHRASE'], j['FREQ']))
        elif j['HEAD'] != '<M>' and j['HEAD'] != '<W>':
            gendered_np.append((j['HEAD'], j['PHRASE'], j['FREQ']))
            all_nps.append((j['HEAD'], j['PHRASE'], j['FREQ']))
        else:
            if j['PHRASE'].split()[-1] not in ['<M>', '<W>']:
                other.append((j['HEAD'], j['PHRASE'], j['FREQ']))
            else:
                modified_m_or_w.append((j['HEAD'], j['PHRASE'], j['FREQ']))  
            all_nps.append((j['HEAD'], j['PHRASE'], j['FREQ']))  
    return other, modified_m_or_w, m_and_w, gendered_np, all_nps
            
def write_to_csv(data, fp, name):
    with open(f'{fp}/{name}.csv', 'w', newline='', encoding='utf8') as csvFile:
        csv_writer = csv.writer(csvFile, delimiter='\t')
        csv_writer.writerow(['HEAD', 'PHRASE', 'FREQ'])
        for line in data:
            csv_writer.writerow(line)


def run():
    nps_2008 = process_nps('Data/Syntactic Ngram', 2008, 5)
    nps_2008 = combine_on_gender(nps_2008)
    nps_2008.sort_values(by='FREQ', ascending=False, inplace=True)
    with_stop_words, modified_m_or_w, m_an_w, gendered_np, all_nps = separate_nps(nps_2008)
    write_to_csv(with_stop_words, 'Data/Syntactic Ngram', 'other_nps')
    write_to_csv(modified_m_or_w, 'Data/Syntactic Ngram', 'modified_mw')
    write_to_csv(m_an_w, 'Data/Syntactic Ngram', 'ambiguous_nps')
    write_to_csv(gendered_np, 'Data/Syntactic Ngram', 'nouns_modified_by_gender')
    write_to_csv(all_nps, 'Data/Syntactic Ngram', 'all_gendered_nps')
run()