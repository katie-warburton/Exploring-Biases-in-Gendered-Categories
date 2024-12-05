import re
import pandas as pd
import inflect
from collections import defaultdict
from nltk.stem import WordNetLemmatizer
 
lemmatizer = WordNetLemmatizer()

p = inflect.engine()

def remove_gender(category, words):
    remove_pattern = re.compile(r'\b' + r'\b|\b'.join(words) + r'\b')
    cat = remove_pattern.sub('', category)
    return re.sub(r'\s+', ' ', cat).strip()

def get_concepts(gendered_cats, gender_words):
    m_idx = gendered_cats.index[gendered_cats['GENDER'] == 'M'].tolist()
    w_idx = gendered_cats.index[gendered_cats['GENDER'] == 'W'].tolist()

    filtered = gendered_cats.loc[gendered_cats['GENDER'] != 'A']
    filtered['DEGENDERED'] = filtered['CLEANED'].apply(lambda x: remove_gender(x, gender_words))

    paired_cats = (
        filtered.groupby('DEGENDERED')
        .apply(lambda x: list(x.index))  # Get list of indices for each group
        .reset_index(name='INDICES') 
    )
    wm_idx_pairs = paired_cats[paired_cats['INDICES'].str.len() > 1]['INDICES'].tolist()
    multiples = [p for p in wm_idx_pairs if len(p) > 2]
    wm_idx_pairs = [p for p in wm_idx_pairs if len(p) == 2]
    for pair in multiples:
        pair_mw_singular, pair_mw_plural, pair_mf = [], [], []
        for idx in pair:
            if bool(re.search(r'\b(man|woman)\b', gendered_cats.loc[idx, 'CLEANED'])):
                pair_mw_singular.append(idx)
            if bool(re.search(r'\b(men|women)\b', gendered_cats.loc[idx, 'CLEANED'])):
                pair_mw_plural.append(idx)
            elif bool(re.search(r'\b(male|female)\b', gendered_cats.loc[idx, 'CLEANED'])):
                pair_mf.append(idx)
        if len(pair_mw_singular) == 2:
            wm_idx_pairs.append(pair_mw_singular)
        if len(pair_mw_plural) == 2:
            wm_idx_pairs.append(pair_mw_plural)
        if len(pair_mf) == 2:
            wm_idx_pairs.append(pair_mf)
    wm_idx_pairs = [[pair[0], pair[1]] if gendered_cats.loc[pair[0], 'GENDER'] == 'W' else [pair[1], pair[0]] for pair in wm_idx_pairs]
    wm_idx  = [i for pair in wm_idx_pairs for i in pair]
    m_idx = [i for i in m_idx if i not in wm_idx]
    w_idx = [i for i in w_idx if i not in wm_idx]
    m = [(None, gendered_cats.loc[i, 'CATEGORY']) for i in m_idx]
    w = [(gendered_cats.loc[i, 'CATEGORY'], None) for i in w_idx]
    wm = [(gendered_cats.loc[i[0], 'CATEGORY'], gendered_cats.loc[i[1], 'CATEGORY']) for i in wm_idx_pairs]
    return w, m, wm

def remove_brackets(text):
    no_brackets = re.sub(r'\([^)]*\)', '', text)
    return re.sub(r'\s+', ' ', no_brackets).strip()

def get_category_hash(gendered_cats, tag):
    cat_hash = defaultdict(list)
    for idx, row in gendered_cats.iterrows():
        cat_hash[row[tag]].append(idx)
    return cat_hash

def pluralize(text):
    if p.singular_noun(text) is not False:
        return text
    else:
        return p.plural(text)

def get_gendered_jobs(jobs_df, gendered_cats, gendered_words):
    gendered_cats['DEGENDERED'] = gendered_cats['CLEANED'].apply(lambda x: remove_brackets(remove_gender(x, gendered_words)))
    category_hash = get_category_hash(gendered_cats, 'DEGENDERED')
    gendered_cats.drop('DEGENDERED', axis=1, inplace=True)
    job_subset = []
    for _, row in jobs_df.iterrows():
        if p.singular_noun(row['TITLE']) is not False:
            sing_job = p.singular_noun(row['TITLE'])
            plur_job = row['TITLE']
        else:
            sing_job = row['TITLE']
            plur_job = p.plural(row['TITLE'])
        syn1 = p.plural(row['SYN_1']) if type(row['SYN_1']) is str else ''
        syn2 = p.plural(row['SYN_2'] )if type(row['SYN_2']) is str else ''
        syn3 = p.plural(row['SYN_3']) if type(row['SYN_3']) is str else ''
        if  category_hash[plur_job] != []:
            job_subset.extend(category_hash[plur_job])
        elif category_hash[sing_job] != []:
            job_subset.extend(category_hash[sing_job])
        elif syn1 != '' and category_hash[syn1] != []:
            job_subset.extend(category_hash[syn1])
        elif syn2 != '' and category_hash[syn2] != []:
            job_subset.extend(category_hash[syn2])
        elif syn3 != '' and category_hash[syn3] != []:
            job_subset.extend(category_hash[syn3])
    job_subset = list(set(job_subset))
    return gendered_cats.loc[job_subset].reset_index(drop=True, inplace=False)

def get_job_stats(gendered_cats, job_gender_stats, gendered_words):
    gendered_cats['JOB'] = gendered_cats['CLEANED'].apply(lambda x:pluralize(remove_brackets(remove_gender(x, gendered_words))))
    job_gender_stats_mod = job_gender_stats.copy()
    job_gender_stats_mod['JOB'] = job_gender_stats_mod['JOB'].apply(lambda x:pluralize(x))
    return pd.merge(gendered_cats, job_gender_stats_mod, on='JOB')[['JOB', 'PROP_W', 'GENDER']]


def get_label(label):
    label = re.sub(r'W+', 'W', label)
    label = re.sub(r'M+', 'M', label)
    label = list(label)
    label.sort(reverse=True)
    return ''.join(label)

def get_gendered_identities(identities_df, gendered_cats, gendered_words):
    gendered_cats['DEGENDERED'] = gendered_cats['CLEANED'].apply(lambda x: remove_brackets(remove_gender(x, gendered_words)))
    category_hash = get_category_hash(gendered_cats, 'DEGENDERED')
    gendered_cats.drop('DEGENDERED', axis=1, inplace=True)
    identity_subset = []
    for _, row in identities_df.iterrows():
        identity = row['IDENTITY']
        if identity in category_hash:
            identity_subset.extend(category_hash[identity])
        elif p.plural(identity) in category_hash:
            identity_subset.extend(category_hash[p.plural(identity)])
        elif p.singular_noun(identity) is not False and p.singular_noun(identity) in category_hash:
            identity_subset.extend(category_hash[p.singular_noun(identity)])
        elif p.singular_noun(identity) is False and identity + ' american' in category_hash:
            identity_subset.extend(category_hash[identity + ' american'])
    identity_subset = list(set(identity_subset))
    return gendered_cats.loc[identity_subset].reset_index(drop=True, inplace=False)

def remove_ngram_gender(gram):
    gram = re.sub(r'(<M>|<W>)', '<P>', gram)
    return re.sub(r'\s+', ' ', gram).strip()

def get_cases(prop_w):
    if prop_w < 0.4:
        return 'M'
    elif prop_w > 0.6:
        return 'W'
    else:
        return 'WM'

def group_ngrams(ngram_df, min_freq):
    ngram_df['CATEGORY'] = ngram_df['GRAM'].apply(remove_ngram_gender)
    ngram_df = ngram_df[ngram_df['FREQ'] >= min_freq]
    ngram_m = ngram_df[ngram_df['GENDER'] == 'M']
    ngram_m.rename(columns={'FREQ': 'FREQ_M'}, inplace=True)
    ngram_w = ngram_df[ngram_df['GENDER'] == 'W']
    ngram_w.rename(columns={'FREQ': 'FREQ_W'}, inplace=True)
    paired = pd.merge(ngram_m, ngram_w, on='CATEGORY')
    paired['TOTAL_GEN_FREQ'] = paired['FREQ_W'] + paired['FREQ_M']
    paired['PROP_W'] = paired['FREQ_W'] / paired['TOTAL_GEN_FREQ']
    paired = paired[['CATEGORY', 'PROP_W', 'TOTAL_GEN_FREQ']]
    paired['CASE'] = paired['PROP_W'].apply(get_cases)
    return paired
    

def get_case_counts(paired_gram_df):
    cases = paired_gram_df.groupby('CASE').count().reset_index()[['CASE', 'CATEGORY']]
    w, m, wm = 0, 0, 0
    cases = cases.to_dict(orient='records')
    for c in cases:
        if c['CASE'] == 'M':
            m = c['CATEGORY']
        elif c['CASE'] == 'W':
            w = c['CATEGORY']
        elif c['CASE'] == 'WM':
            wm = c['CATEGORY']
    return w, wm, m

def get_gendered_jobs_lang(job_df, grams_df):
    category_hash = get_category_hash(grams_df, 'CATEGORY')
    job_subset = []
    for _, row in job_df.iterrows():
        job = lemmatizer.lemmatize(row['TITLE'])
        syn1 = lemmatizer.lemmatize(row['SYN_1']) if type(row['SYN_1']) is str else ''
        syn2 = lemmatizer.lemmatize(row['SYN_2'] )if type(row['SYN_2']) is str else ''
        syn3 = lemmatizer.lemmatize(row['SYN_3']) if type(row['SYN_3']) is str else ''
        job_str = '<P> ' + job
        if category_hash[job_str] != []:
            job_subset.extend(category_hash[job_str])
        if syn1 != '' and syn1 != job and category_hash['<P> ' + syn1] != []:
            job_subset.extend(category_hash['<P> ' + syn1])
        if syn2 != '' and syn2 != job and syn2 != syn1 and category_hash['<P> ' + syn2] != []:
            job_subset.extend(category_hash['<P> ' + syn2])
        if syn3 != '' and syn3 != job and syn3 != syn1 and syn3 != syn2 and category_hash['<P> ' + syn3] != []:
            job_subset.extend(category_hash['<P> ' + syn3])
    job_subset = list(set(job_subset))
    return grams_df.loc[job_subset].reset_index(drop=True, inplace=False)

def get_gendered_identities_lang(identities_df, grams_df):
    category_hash = get_category_hash(grams_df, 'CATEGORY')
    identity_subset = []
    for _, row in identities_df.iterrows():
        identity = lemmatizer.lemmatize(row['IDENTITY'])
        identity_n = lemmatizer.lemmatize(identity, pos='n')
        identity_a = lemmatizer.lemmatize(identity, pos='a')
        identity_str = identity_n + ' <P>'
        if category_hash[identity_str] != []:
            identity_subset.extend(category_hash[identity_str])
        if identity_a != identity_n and category_hash[identity_a + ' <P>'] != []:
            identity_subset.extend(category_hash[identity_a + ' <P>'])
        if identity != identity_n and identity != identity_a and category_hash[identity] != []:
            identity_subset.extend(category_hash[identity])
    identity_subset = list(set(identity_subset))
    return grams_df.loc[identity_subset].reset_index(drop=True, inplace=False)
    

def lemmatize_job_words(gram):
    words = gram.split(' ')
    lemmatized = [lemmatizer.lemmatize(word) for word in words]
    return '<P> ' + ' '.join(lemmatized)


def get_job_stats_ngram(gendered_grams, job_gender_stats):
    gendered_grams['JOB'] = gendered_grams['CATEGORY']
    gendered_grams.rename(columns={'PROP_W': 'GEN_PROP_W'}, inplace=True)
    job_gender_stats_mod = job_gender_stats.copy()
    job_gender_stats_mod['JOB'] = job_gender_stats_mod['JOB'].apply(lemmatize_job_words) 
    merged = pd.merge(gendered_grams, job_gender_stats_mod, on='JOB')[['JOB', 'PROP_W', 'GEN_PROP_W', 'CASE']]
    gendered_grams.drop('JOB', axis=1, inplace=True)
    return merged

def combine_job_datasets(job_df1, jobs_df2):
    jobs_df2['JOB'] = jobs_df2['JOB'].apply(lambda x: pluralize(x))
    job_df1['JOB'] = job_df1['JOB'].apply(lambda x: pluralize(x))
    combined = pd.concat([job_df1, jobs_df2]).drop_duplicates(subset='JOB', keep='first').reset_index(drop=True)
    return combined