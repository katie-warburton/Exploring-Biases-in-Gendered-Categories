import re
import numpy as np
from collections import Counter
from nltk.stem import WordNetLemmatizer
from pluralizer import Pluralizer

lemmatizer = WordNetLemmatizer()
pluralizer = Pluralizer()
    

WOMEN_WORDS = ["women", "female", "feminine"]
MEN_WORDS = ["men", "male", "masculine"]
GENDERED_WORDS = WOMEN_WORDS + MEN_WORDS

PEOPLE_WORDS = ['people', 'humans', 'human beings']

STOP_WORDS = ["in", "of", "and", "as", "at", "for", "the", "a", "an", "'s"]

def percent(subset, total):
    return (subset/total)*100

def clean_all(terms, tag, duplicates=Counter(), lcsh=False):
    for idx, term in terms.items():
        terms[idx]['cleaned'] = deep_clean(term[tag], duplicates, lcsh)
    
def deep_clean(word, duplicates=Counter(), lcsh=False):
    if lcsh and 'law)' in word.lower():
        word = re.sub(r'\((.*?)\)', r'in \1', word)
    elif lcsh and 'theology)' in word.lower():
        word = re.sub(r'\((.*?)\)', r'in \1', word)
    elif lcsh and ' people)' in word.lower():
        no_brackets = ' '.join(re.sub(r'\(.*?\)', r'', word).lower().split())
        if duplicates[no_brackets] > 1:
            word = word.replace(')', ' )').replace('(', '( ')
        else:
            word = re.sub(r'\((.*?)\)', r'people', word)
    elif '(' in word and ')' in word:
        #no_brackets = ' '.join(re.sub(r'\(.*?\)', r'', word).lower().split())
        #if duplicates[no_brackets.lower()] > 1:
        word = word.replace(')', ' )').replace('(', '( ')
        
        #else:
            #word = no_brackets
    return clean(word)

def clean(word):
    word = word.lower()
    word = word.replace("'", " '")
    word = re.sub(r'[_|\-|.|;|:|\?|!|/|"]', ' ', word)
    word = re.sub(' +', ' ', word)
    if word.count(',') == 1:
        parts = word.split(',')
        part1 = parts[0].strip()
        part2 = parts[1].strip()
        word = part2 + ' ' + part1
    elif word.count(',') > 1:
        word = re.sub(r"(\w+(( | ')\w+)*), ((\w+)( \w+)*)", r'\4 \1', word).replace(',', '')
    word = word.replace('&', ' and ')
    word = word.replace(',', ' ')
    word = re.sub(' +', ' ', word)
    return word.strip()

'''
Collect all terms in the LCSH that contain a words from a list. 
The parameter tag is the key that the word is stored under in the dictionary representing the LCSH. 
Returns a dictionary of the terms that contain the words in the list.
'''
def tag_with_gender(terms, list_type):
    if list_type.lower() == 'm':
        gender_words = MEN_WORDS
    elif list_type.lower() == 'w':
        gender_words = WOMEN_WORDS
    else:
        raise ValueError('Incorrect list type. Must be either m or w.')
    for idx, term in terms.items():
        flag = False
        head = term['cleaned']
        term_words = [w for w in head.split(' ')]
        for word in gender_words:
            if word in term_words:
                term['genderWord'] = word
                flag = True
                break
        if flag:
            if terms[idx]['gender'] is not None and terms[idx]['gender'] != list_type.upper():
                terms[idx]['gender'] = 'A'
            else:
                terms[idx]['gender'] = list_type.upper()
                
def split_into_gendered(terms):
    m_terms = {idx:term for idx, term in terms.items() if term['gender'] == 'M'}
    w_terms = {idx:term for idx, term in terms.items() if term['gender'] == 'W'}
    a_terms = {idx:term for idx, term in terms.items() if term['gender'] == 'A'}
    return m_terms, w_terms, a_terms

def remove_gender(term, tag):
    cleaned = clean(term[tag]).replace(')', '').replace('(', '')
    words = [word for word in cleaned.split(' ') if word not in GENDERED_WORDS]
    return ' '.join(words)

def get_concept_idxs(m_terms, w_terms, tag):
    wm = []
    m = {idx  for idx in m_terms}
    w = {idx for idx in w_terms}
    m_hash = {remove_gender(term, tag):idx for idx, term in m_terms.items()}
    w_hash = {remove_gender(term, tag):idx for idx, term in w_terms.items()}
    if len(m_hash) != len(m_terms) or len(w_hash) != len(w_terms):
        print([m_terms[idx] for idx in m if idx not in m_hash.values()])
        print([w_terms[idx] for idx in w if idx not in w_hash.values()])
        '''this shouldn't happen as the only word I'm removing is the gendered one.
           If this is changed to include things like mothers/fathers, sisters/brothers, etc., this might occur'''
        print('Warning: Duplicates in gendered terms!')
    for term, idx in m_hash.items():
        if term in w_hash:
            paired_idx = w_hash[term]
            wm.append((idx, paired_idx))
            m.remove(idx)
            w.remove(paired_idx)
    m = [(idx, None) for idx in m]
    w = [(None, idx) for idx in w]
    return wm + m + w
 
def get_place_holder(term):
    gender_word = term['genderWord']
    cleaned_term = term['cleaned']
    if term['gender'] == 'M':
        replacement = WOMEN_WORDS[MEN_WORDS.index(gender_word)]
    elif term['gender'] == 'W':
        replacement = MEN_WORDS[WOMEN_WORDS.index(gender_word)]
    return re.sub(rf'\b{re.escape(gender_word)}\b', replacement.upper(), cleaned_term)

def get_generic(term, tag):
    IN = ['in', 'for', 'of', 'as', 'at', 'with', 'on', 'to']
    try:
        gender_word = term['genderWord']    
    except KeyError:
        print(term)
    cleaned_term = term['cleaned']
    words = cleaned_term.split(' ')
    gender_idx = words.index(gender_word)
    people = PEOPLE_WORDS[0]
    if len(words) == 1:
        generic = PEOPLE_WORDS
    elif gender_word in WOMEN_WORDS[1:] + MEN_WORDS[1:]: 
        if f'-{gender_word}' in term[tag].lower():
            words.pop(gender_idx)
            words.pop(gender_idx-1)
            generic = [' '.join(words)]
        else:
            generic = [' '.join(words[:gender_idx] + words[gender_idx+1:])]
    elif gender_idx == len(words)-1:
        if len(words) == 2:
            gen1 = pluralizer.pluralize(words[0])
            words[gender_idx] = people
            gen2 = ' '.join(words)
            generic = [gen2, gen1]
        elif words[gender_idx-1] == 'and':
            generic = [' '.join(words[:-2])]
        elif words[gender_idx-1] in IN:
            generic = [' '.join(words[:gender_idx-1])]
        else:
            gen1 = ' '.join(words[:gender_idx-1] + [pluralizer.pluralize(words[gender_idx-1])])
            words[gender_idx] = people
            gen2 = ' '.join(words)
            generic = [gen2, gen1]
            pass
    else:
        if words[gender_idx+1] in IN:
            if gender_idx > 0:
                gen1 = pluralizer.pluralize(words[gender_idx-1]) + ' ' + ' '.join(words[gender_idx+1:])
                words[gender_idx] = 'people'
                gen2 = ' '.join(words)
                generic = [gen2, gen1]
            else:
                words[gender_idx] = 'people'
                generic = [' '.join(words)]
        elif words[gender_idx+1] == 'and' or words[gender_idx-1] == 'and':
            words.pop(gender_idx)
            words.remove('and')
            gen2 = ' '.join(words)
            generic = [gen2]
        elif words[gender_idx+1] == 'owned':
            generic = [' '.join(words[:gender_idx] + words[gender_idx+2:])]
        # think on this one
        elif words[gender_idx+1] == "'s" or words[gender_idx+1] == "'":
            gen1 = ' '.join(words[:gender_idx] + words[gender_idx+2:])
            words[gender_idx] = 'people'
            gen2 = ' '.join(words)
            generic = [gen2, gen1]
        elif gender_idx == 0:
            generic = [' '.join(words[1:])]
        else:
            gen1 = ' '.join(words[:gender_idx] + words[gender_idx+1:])
            words[gender_idx] = 'people'
            gen2 = ' '.join(words)
            generic = [gen2, gen1]
    no_the = []
    for gen in generic:
        if 'the' in gen:
            no_the.append(re.sub(r'(^|[^a-zA-Z])the([^a-zA-Z]|$)', r' ', gen).strip())
    return generic + no_the

def find_generic(term, generic_categories, tag):
    generic = get_generic(term, tag)
    match = None
    for variant in generic:
        match = match_generic(variant, generic_categories)
        if match is not None:
            break
    return match

def match_generic(term, term_dict):
    if term in term_dict:
        return term
    elif pluralizer.singular(term) in term_dict:
        return pluralizer.singular(term)
    elif 'people in ' in term:
        new_term = term.replace('people in ', '').strip() + ' workers'
        if new_term in term_dict:
            return new_term
        else:
            return None
    elif 'people' in term:
        new_term1 = term.replace('people', 'adults')
        # new_term3 = term.replace('people', 'indians') #comes from outdated terminology of the LCSH for indigenous peoples
        if new_term1 in term_dict:
            return new_term1
        # elif new_term3 in term_dict:
        #     return new_term3
        else:
            return None
    else:
        return None

def split_into_categories(gendered_idxs, terms, tag):
    categories = {'m':[], 'w':[], 'g':[], 
                  'mInLCSH':[], 'wInLCSH':[], 'gInLCSH':[], 
                  'mDate':[], 'wDate':[], 'gDate':[], 
                  'mIdx':[], 'wIdx':[], 'gIdx':[]
                  }
    ignore_idxs = {idx for idx_pair in gendered_idxs for idx in idx_pair if idx is not None}
    generic_terms = {term['cleaned']:idx for idx, term in terms.items() if idx not in ignore_idxs}
    for m_idx, w_idx in gendered_idxs:
        if m_idx is None:
            m_term = None
            categories['m'].append(get_place_holder(terms[w_idx]))
            categories['mInLCSH'].append(0)
            categories['mDate'].append(9999)
        else:
            m_term = terms[m_idx]
            categories['m'].append(m_term['heading'].lower())
            categories['mInLCSH'].append(1)
            categories['mDate'].append(m_term['yearAdded'])

        categories['mIdx'].append(m_idx)                        
        if w_idx is None:
            w_term = None
            categories['w'].append(get_place_holder(terms[m_idx]))
            categories['wInLCSH'].append(0)
            categories['wDate'].append(9999)
        else:
            w_term = terms[w_idx]
            categories['w'].append(w_term['heading'].lower())
            categories['wInLCSH'].append(1)
            categories['wDate'].append(w_term['yearAdded'])
        categories['wIdx'].append(w_idx)

        if m_term is not None:
            base_term = m_term
            generic = find_generic(base_term, generic_terms, tag)

        else:
            base_term = w_term
            generic = find_generic(base_term, generic_terms, tag)
        if generic is not None:
            g_idx = generic_terms[generic]
            categories['g'].append(terms[g_idx]['heading'].lower())
            categories['gInLCSH'].append(1)
            categories['gDate'].append(terms[g_idx]['yearAdded'])
            categories['gIdx'].append(g_idx)
        else:
            categories['g'].append(re.sub(rf'\b{re.escape(base_term['genderWord'])}\b', r'PEOPLE', base_term['cleaned']))
            categories['gInLCSH'].append(0)
            categories['gDate'].append(9999)
            categories['gIdx'].append(None)
    return categories

def bias_across_time(dates, categories):
    total_concepts = len(categories['w'])
    asymmetry = []
    marked = []
    for date in dates:
        wg_date = [(categories['w'][i], categories['g'][i]) for i in range(total_concepts) if ((categories['mInLCSH'][i] == 0  or 
                                                                                                categories['mDate'][i] > date) and 
                                                                                               (categories['wInLCSH'][i] == 1 and 
                                                                                                categories['wDate'][i] <= date) and
                                                                                               (categories['gInLCSH'][i] == 1 and 
                                                                                                categories['gDate'][i] <= date))]
        mg_date = [(categories['m'][i], categories['g'][i]) for i in range(total_concepts) if ((categories['wInLCSH'][i] == 0 or 
                                                                                                categories['wDate'][i] > date) and 
                                                                                               (categories['mInLCSH'][i] == 1 and 
                                                                                                categories['mDate'][i] <= date) and
                                                                                               (categories['gInLCSH'][i] == 1 and 
                                                                                                categories['gDate'][i] <= date))]
        w_date = [(categories['w'][i]) for i in range(total_concepts) if ((categories['mInLCSH'][i] == 0 or 
                                                                           categories['mDate'][i] > date) and 
                                                                          (categories['wInLCSH'][i] == 1 and 
                                                                           categories['wDate'][i] <= date) and
                                                                          (categories['gInLCSH'][i] == 0 or
                                                                           categories['gDate'][i] > date))] 
        m_date = [(categories['m'][i]) for i in range(total_concepts) if ((categories['wInLCSH'][i] == 0 or
                                                                           categories['wDate'][i] > date) and 
                                                                          (categories['mInLCSH'][i] == 1 and 
                                                                           categories['mDate'][i] <= date) and
                                                                          (categories['gInLCSH'][i] == 0 or
                                                                           categories['gDate'][i] > date))]
        w_unbalanced = len(wg_date) + len(w_date)
        m_unbalanced = len(mg_date) + len(m_date)
        w_marked = len(wg_date)
        m_marked = len(mg_date)
        asymmetry.append((w_unbalanced, m_unbalanced))
        marked.append((w_marked, m_marked))
    return asymmetry, marked    
 

def compareFreqs(lcshData, includeZero=False, normalize=False):
    if includeZero:
        contingency = np.zeros((3,3))
    else:
        contingency = np.zeros((3,2))
    for i in range(len(lcshData['m'])):
        if lcshData['mInLCSH'][i] == 0 and lcshData['wInLCSH'][i] == 1:
            if lcshData['wFreq'][i] > lcshData['mFreq'][i]:
                contingency[0,0] += 1
            elif lcshData['wFreq'][i] < lcshData['mFreq'][i]:
                contingency[0,1] += 1
            elif includeZero and lcshData['wFreq'][i] == lcshData['mFreq'][i]  and lcshData['mFreq'][i] == 0:
                contingency[0,2] += 1
        elif lcshData['mInLCSH'][i] == 1 and lcshData['wInLCSH'][i] == 0:
            if lcshData['wFreq'][i] > lcshData['mFreq'][i]:
                contingency[1,0] += 1
            elif lcshData['wFreq'][i] < lcshData['mFreq'][i]:
                contingency[1,1] += 1
            elif includeZero and lcshData['wFreq'][i] == lcshData['mFreq'][i] and lcshData['mFreq'][i] == 0:
                contingency[1,2] += 1
        elif lcshData['mInLCSH'][i] == 1 and lcshData['wInLCSH'][i] == 1:
            if lcshData['wFreq'][i] > lcshData['mFreq'][i]:
                contingency[2,0] += 1
            elif lcshData['wFreq'][i] < lcshData['mFreq'][i]:
                contingency[2,1] += 1
            elif includeZero and lcshData['wFreq'][i] == lcshData['mFreq'][i] and lcshData['mFreq'][i] == 0:
                contingency[2,2] += 1
    if normalize:
        contingency = contingency/contingency.sum(axis=1)[:,None]
    return contingency

def get_ngram_over_threshold(gram_df, thresholds):
    gram_lists = []
    for t in thresholds:
        greater_than_t = gram_df[gram_df['FREQ'] >= t]['PHRASE'].values
        gram_lists.append(greater_than_t)
    return gram_lists

def get_gendered_ngrams(gram_list):
    m_grams = [gram for gram in gram_list if '<M>' in gram]
    w_grams = [gram for gram in gram_list if '<W>' in gram]
    return m_grams, w_grams

def get_ngram_cases(m_grams, w_grams):
    no_M = {re.sub(r'<M>', '', gram):gram for gram in m_grams}
    no_W = {re.sub(r'<W>', '', gram):gram for gram in w_grams}
    m = [(no_M[k], None) for k in set(no_M.keys()) - set(no_W.keys())]
    w = [(None, no_W[k]) for k in set(no_W.keys()) - set(no_M.keys())]
    wm = [(no_M[k], no_W[k]) for k in set(no_M.keys()) & set(no_W.keys())]
    return m, w, wm
        
