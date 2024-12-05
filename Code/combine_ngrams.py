import re
import pandas as pd
import inflect
from collections import defaultdict
from nltk.stem import WordNetLemmatizer
 
lemmatizer = WordNetLemmatizer()


def convert_pos(pos_gram):
    if pos_gram == 'noun':
        return 'n'
    elif pos_gram == 'adj':
        return 'a'
    elif pos_gram == 'propn':
        return 'n'
    else:
        return None
    
def get_gender_of_gram(gram):
    if '<M>' in gram and '<W>' in gram:
        return 'A'
    elif '<M>' in gram:
        return 'M'
    elif '<W>' in gram:
        return 'W'
    else:
        return 'A'
    

def no_duplicate_func_words(gram):
    if gram.count('in') <= 1 and gram.count('of') <= 1 and gram.count('and') <= 1 and gram.count('for') <= 1 and gram.count('by') <= 1:
        return True
    else:
        return False
    
def no_two_letters(gram):
    words = [w for w in gram.split(' ') if w not in ['of', 'by', 'in', 'for', 'and']]
    return all(len(w) > 2 for w in words)

def fm_as_adj(gram):
    if bool(re.search(r'\b(female|male)$', gram)):
        return False
    elif bool(re.search(r'\b(female|male)\b (in|of|and|for|by)', gram)):
        return False
    elif bool(re.search(r' female ', gram)) and '_noun' not in gram.split('female ')[-1]:
        return False
    elif bool(re.search(r' male ', gram)) and '_noun' not in gram.split('male ')[-1]:
        return False
    else:
        return True

def regularize_gram(gram):
    words = gram.split(' ')
    pos_words = [w.split('_') if w.count('_') == 1 else [w, None] for w in words]
    lemmatized_words = [lemmatizer.lemmatize(w, pos=convert_pos(pos)) if convert_pos(pos) is not None else w for w, pos in pos_words]
    return ' '.join(lemmatized_words)

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def prune_grams(gram_df, extended=False):
    # remove words with numbers and with more than one in/of/and/for/by
    pruned_df = gram_df[(~gram_df['PHRASE'].str.contains(r'\d', regex=True)) & (gram_df['PHRASE'].apply(no_duplicate_func_words)) & (gram_df['PHRASE'].apply(is_ascii))]
    if not extended:
        pruned_df = pruned_df[pruned_df['PHRASE'].apply(lambda x: bool(re.search(r'\b(woman|man|males|females)\b', x)) == False)]
        pruned_df = pruned_df[pruned_df['PHRASE'].apply(fm_as_adj)]
    pruned_df['PHRASE'] = pruned_df['PHRASE'].apply(regularize_gram)
    pruned_df['PHRASE'] = pruned_df['PHRASE'].apply(lambda x: re.sub(r'\b(men|man|male|males|mens)\b', '<M>', x))
    pruned_df['PHRASE'] = pruned_df['PHRASE'].apply(lambda x: re.sub(r'\b(women|woman|female|females|womens)\b', '<W>', x))
    # pruned_df['PHRASE'] = pruned_df['PHRASE'].apply(regularize_gram)
    pruned_df = pruned_df[(~pruned_df['PHRASE'].str.contains('_') ) & (pruned_df['PHRASE'].apply(no_two_letters))]
    return pruned_df.groupby('PHRASE').sum().reset_index()


def get_within_range(gram_df, start_year, end_year):
    years =  [f'{y}' for y in range(start_year, end_year+1)]
    subset_grams = gram_df[['PHRASE'] + years].copy()
    subset_grams['FREQ'] = subset_grams[years].sum(axis=1)
    subset_grams = subset_grams[subset_grams['FREQ'] > 0]
    subset_grams['GENDER'] = subset_grams['PHRASE'].apply(get_gender_of_gram)
    subset_grams.rename(columns={'PHRASE': 'GRAM'}, inplace=True)
    return subset_grams[['GRAM', 'FREQ', 'GENDER']]


def combine_grams():
    bigrams = pd.read_csv('Data/Google Ngram/bigrams-gendered.csv')
    trigrams = pd.read_csv('Data/Google Ngram/trigrams-gendered.csv')
    # fourgrams = pd.read_csv('Data/Google Ngram/fourgrams-gendered.csv')
    # bigrams = prune_grams(bigrams)
    # trigrams = prune_grams(trigrams)
    # fourgrams = prune_grams(fourgrams)
    ngrams = pd.concat([bigrams, trigrams], ignore_index=True)
    ngrams = prune_grams(ngrams)
    ngrams_current = get_within_range(ngrams, 2010, 2019)
    ngrams_20th = get_within_range(ngrams, 1900, 1999)
    ngrams_current.to_csv('Data/Google Ngram/ngrams_2010-2019.csv', index=False)
    ngrams_20th.to_csv('Data/Google Ngram/ngrams_20th_century.csv', index=False)

if __name__ == '__main__':
    combine_grams()