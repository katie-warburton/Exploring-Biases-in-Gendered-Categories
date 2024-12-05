
import re
import pandas as pd

def read_wikipedia_data():
    with open('Data/Wikipedia/categories', 'r', encoding='utf-8') as f:
        data = f.readlines()
    return data

def process_wikipedia_data(data):
    categories = {'CATEGORY': [], 'CLEANED': []}
    for line in data:
        cat = line.strip()
        cleaned = cat.strip().lower().replace('_', ' ')
        cleaned = cleaned.replace("'", " '").replace('(' , ' ( ').replace(')', ' ) ')
        cleaned = re.sub(r'[^\w\s\'\)\(]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        categories['CATEGORY'].append(cat)
        categories['CLEANED'].append(cleaned)
    return pd.DataFrame(categories).drop_duplicates().reset_index(drop=True)


def get_gendered_categories(men_words, women_words, wiki_categories):
    m_regex = re.compile(r'\b(?:%s)\b' % '|'.join(men_words), re.IGNORECASE)
    w_regex = re.compile(r'\b(?:%s)\b' % '|'.join(women_words), re.IGNORECASE)
    gendered_wiki = {'CATEGORY': [], 'CLEANED': [], 'GENDER': []}
    for i in range(len(wiki_categories['CLEANED'])):
        gender = None
        cleaned_cat = wiki_categories['CLEANED'][i]
        m_flag = bool(m_regex.search(cleaned_cat))
        w_flag = bool(w_regex.search(cleaned_cat))
        if m_flag and w_flag:
            gender = 'A'
        elif m_flag:
            gender = 'M'
        elif w_flag:
            gender = 'W'
        if gender is not None:
            gendered_wiki['CATEGORY'].append(wiki_categories['CATEGORY'][i])
            gendered_wiki['CLEANED'].append(cleaned_cat)
            gendered_wiki['GENDER'].append(gender)
    return pd.DataFrame(gendered_wiki)
        
def main(fp, m_words, w_words, save_all=False):
    data = read_wikipedia_data()
    wiki_categories = process_wikipedia_data(data)
    gendered_wiki = get_gendered_categories(m_words, w_words, wiki_categories)
    gendered_wiki.to_csv(fp + '/wikipedia-gendered.csv', index=False)
    if save_all:
        wiki_categories.to_csv(fp + '/wikipedia-all.csv', index=False)

if __name__ == '__main__':
    main('Data/Wikipedia', ['men', 'male'], ['women', 'female'], save_all=True)