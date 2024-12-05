import re
import pandas as pd
from collections import defaultdict

def good_job_format(job_title, high_level_jobs):
    job_words = job_title.split(' ')
    if len(job_words) >= 1:
        return True
    else:
        first_word, second_word = job_words[0], job_words[1]
        if high_level_jobs[first_word]:
            if second_word in ['of', 'for', 'in']:
                return True
            else:
                return False
        else:
            return True

def get_jobs(job_dictionary):
    pruned_jobs = job_dictionary[(job_dictionary['FindPhraseStatus'] == 'assignedrole') 
                                 & (job_dictionary['ReplacePhrase'].notna()) 
                                 & (job_dictionary['ReplacePhrase'].str.split(' ').str.len() < 5)]
    pruned_jobs = pruned_jobs[['ReplacePhrase', 'AssignedRole']].rename(columns={'ReplacePhrase': 'TITLE', 'AssignedRole': 'CATEGORY'})
    pruned_jobs['TITLE'] = pruned_jobs['TITLE'].str.lower()
    pruned_jobs = pruned_jobs.drop_duplicates().reset_index(drop=True)
    pruned_jobs['CATEGORY'] = pruned_jobs['CATEGORY'].str.lower().str.split('-').str[0]

    category_counts = pruned_jobs['CATEGORY'].value_counts().rename_axis('CATEGORY').reset_index(name='COUNT')
    more_than_once = category_counts[category_counts['COUNT'] > 1]['CATEGORY'].tolist()
    pruned_jobs = pruned_jobs[~(pruned_jobs['TITLE'].str.contains('internship')|pruned_jobs['TITLE'].str.contains('jobs'))]

    job_words = set(list(pruned_jobs['TITLE'].values) + list(more_than_once) + ['waiter', 'employee', 'prostitute', 'sex worker', 'exotic dancer'])
    high_level_jobs = defaultdict(bool, {j: True for j in list(pruned_jobs['CATEGORY'].unique()) + ['nurse', 'registered nurse']})

    good_jobs = [job for job in job_words if (good_job_format(job, high_level_jobs) and not job.endswith('ress') and not job.endswith('rness') 
                                              and not bool(re.search(r'\b(men|man|male|males|woman|women|female|females|womens|mens)\b', job)))
                                              and not bool(re.search(r'\b(?!human\b|german\b)\w*man\b', job))]
    return good_jobs, high_level_jobs

def synonym_subset(syn):
    synonyms = syn.split(';')
    if len(synonyms) < 4:
        return synonyms
    else:
        return synonyms[:3]

def get_synonyms(job_dictionary, job_list, high_level_jobs):
    job_synonyms = job_dictionary[job_dictionary['FindPhraseStatus'] == 'assignedrole'][['FindPhrase', 'ReplacePhrase']].dropna().rename(columns={'FindPhrase': 'SYNONYM', 'ReplacePhrase': 'TITLE'})
    job_synonyms = job_synonyms.rename(columns={'FindPhrase': 'SYNONYM', 'ReplacePhrase': 'TITLE'})
    job_synonyms['SYNONYM'] = job_synonyms['SYNONYM'].str.lower()
    job_synonyms['TITLE'] = job_synonyms['TITLE'].str.lower()
    job_synonyms = job_synonyms[(job_synonyms['SYNONYM'].str.split(' ').str.len() < 5) &
                                ~(job_synonyms['SYNONYM'].str.contains('internship')) &
                                ~(job_synonyms['SYNONYM'].str.contains('jobs')) &
                                ~(job_synonyms['SYNONYM'].str.endswith('ress')) &
                                ~(job_synonyms['SYNONYM'].str.endswith('rness')) &
                                (job_synonyms['SYNONYM'].apply(lambda s: bool(re.search(r'\b(?!human\b|german\b)\w*man\b', s)) == False)) &
                                (job_synonyms['SYNONYM'] != job_synonyms['TITLE']) &
                                (job_synonyms['SYNONYM'].apply(lambda s: good_job_format(s, high_level_jobs))) &
                                (job_synonyms['SYNONYM'].apply(lambda s: bool(re.search(r'\b(men|male|males|women|female|females)\b', s)) == False))]
    job_synonyms = job_synonyms[job_synonyms['TITLE'].isin(job_list)].reset_index(drop=True)
    additional_jobs = pd.DataFrame([['rn', 'nurse'],
                                    ['rn', 'registered nurse'], 
                                    ['exotic dancer', 'stripper'], 
                                    ['exotic dancer', 'stripteaser'],
                                    ['physician', 'medical doctor'],
                                    ['physician', 'doctor'],
                                    ['employee', 'worker']], columns=['TITLE', 'SYNONYM'])
    job_synonyms = pd.concat([job_synonyms, additional_jobs], ignore_index=True)
    jobs_with_synonyms = job_synonyms.groupby('TITLE')['SYNONYM'].agg(';'.join).reset_index()
    jobs_with_synonyms['SYNONYM'] = jobs_with_synonyms['SYNONYM'].apply(synonym_subset)
    return jobs_with_synonyms


def lengthen(df):
    rows = []
    for _, row in df.iterrows():
        occupation = row['Occupation']
        if ',' in occupation:
            occupation_words = occupation.split(',')
            for word in occupation_words:
               rows.append({'Occupation': word.strip(), 'Number': row['Number'], '% Men': row['% Men'], '% Women': row['% Women']})
        else:
            rows.append({'Occupation': occupation, 'Number': row['Number'], '% Men': row['% Men'], '% Women': row['% Women']})
    return pd.DataFrame(rows)

def main():
    job_dictionary = pd.read_csv('Data/job_title_dictionary.txt', sep='\t')
    job_list, high_level_jobs = get_jobs(job_dictionary)
    job_synonyms = get_synonyms(job_dictionary, job_list, high_level_jobs)
    job_no_synonyms = [[j, ''] for j in job_list if j not in job_synonyms['TITLE'].values]
    job_no_synonyms = pd.DataFrame(job_no_synonyms, columns=['TITLE', 'SYNONYM'])
    job_synonyms = pd.concat([job_synonyms, job_no_synonyms]).reset_index(drop=True)

    job_synonyms['SYN_1'] = job_synonyms['SYNONYM'].str[0]
    job_synonyms['SYN_2'] = job_synonyms['SYNONYM'].str[1]
    job_synonyms['SYN_3'] = job_synonyms['SYNONYM'].str[2]
    # drop original column
    job_synonyms.drop(columns=['SYNONYM'], inplace=True)
    job_synonyms.to_csv('Data/jobs_with_synonyms.csv', index=False)

    job_dictionary_2 = pd.read_csv('Data/cleaned_us_career_data.csv')
    job_dictionary_2 = lengthen(job_dictionary_2)
    job_dictionary_2['Occupation'] = job_dictionary_2['Occupation'].str.lower()
    job_dictionary_2 = job_dictionary_2 = job_dictionary_2[(job_dictionary_2['Occupation'].str.split(' ').str.len() < 5) &
                                ~(job_dictionary_2['Occupation'].str.endswith('ress')) &
                                ~(job_dictionary_2['Occupation'].str.endswith('rness')) &
                                (job_dictionary_2['Occupation'].apply(lambda s: bool(re.search(r'\b(?!human\b|german\b)\w*man\b', s)) == False)) &
                                (job_dictionary_2['Occupation'].apply(lambda s: bool(re.search(r'\b(men|male|males|women|female|females)\b', s)) == False))]
    job_dictionary_2.reset_index(drop=True, inplace=True)
    job_dictionary_2.rename(columns={'Occupation': 'JOB', '% Women':'PROP_W', '% Men': 'PROP_M'}, inplace=True)
    job_dictionary_2 = job_dictionary_2[['JOB', 'PROP_W', 'PROP_M']]
    job_dictionary_2['PROP_W'] = job_dictionary_2['PROP_W'] / 100
    job_dictionary_2['PROP_M'] = job_dictionary_2['PROP_M'] / 100
    job_dictionary_2.to_csv('Data/us_job_stats_2019.csv', index=False)    


if __name__ == '__main__':
    print('getting jobs')
    main()
    