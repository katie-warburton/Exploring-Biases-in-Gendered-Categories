import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import gzip
import json
import argparse
import csv
import pandas as pd
import re
'''
'''
def clean(word):
    word = word.lower()
    word = word.replace("'", " '").replace(')', " ) ").replace('(', " ( ")
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
    word = re.sub(' +', ' ', word)
    return word.strip()

def extract_lcsh(file):
    lcsh = {}
    print('Reading LCSH data...')
    for idx, line in enumerate(open(file)):
        if idx%50000==0:
            print(f'{idx} records processed')
        line = json.loads(line)
        # Define variables
        term_id = line['@id'][22:]
        heading, lcc, year_new, year_rev, year_dep, kind = None, None, None, None, None, None
        deletion_note, bt, nt, syns, former_head, lang = None, None, None, None, None, None
        alt_terms = {}
        for record in line['@graph']:
            if record['@id'][39:] == term_id:
                #Current Subject Heading 
                if 'madsrdf:Authority' in record['@type']:
                    heading = record['madsrdf:authoritativeLabel']['@value']
                    lang = record['madsrdf:authoritativeLabel']['@language']
                    kind = [t[8:] for t in record['@type'] if t[8:]!= 'Authority'][0]

                    if 'madsrdf:isMemberOfMADSCollection' in record:
                        collection = record['madsrdf:isMemberOfMADSCollection']
                    if type(collection) is list:
                        collection = [term['@id'][term['@id'].index('_')+1:] for term in collection]
                    else:
                        collection = [collection['@id']]

                    if 'LCSHAuthorizedHeadings' not in collection:
                        if 'Subdivisions' in collection:
                            kind = 'Subdivision'
                        else:
                            kind = 'Other'
                    if 'madsrdf:hasBroaderAuthority' in record:
                        # Broader Terms
                        bt = record['madsrdf:hasBroaderAuthority']
                        if type(bt) is list:
                            bt = [term['@id'][39:] for term in bt]
                        else:
                            bt = [bt['@id'][39:]]
                        bt = [idx for idx in bt if idx.strip()]
                        if bt == []:
                            bt = None
                    if 'madsrdf:hasNarrowerAuthority' in record:
                        # Narrower Terms
                        nt = record['madsrdf:hasNarrowerAuthority']
                        if type(nt) is list:
                            nt = [term['@id'][39:] for term in nt]
                        else:
                            nt = [nt['@id'][39:]]
                        nt = [idx for idx in nt if idx.strip()]
                        if nt == []:
                            nt = None
                    if 'madsrdf:hasVariant' in record:
                        # Synonyms of a term
                        syns = record['madsrdf:hasVariant']
                        if type(syns) is list:
                            syns = [term['@id'] for term in syns]
                        else:
                            syns = [syns['@id']]
                        syns = [s for s in syns if s.strip()]
                        if syns == []:
                            syns = None
                    if 'madsrdf:hasEarlierEstablishedForm' in record:
                        # Former Headings
                        former_head = record['madsrdf:hasEarlierEstablishedForm']
                        if type(former_head) is list:
                            former_head = [term['@id'] for term in former_head]
                        else:
                            former_head = [former_head['@id']]  
                        former_head = [f for f in former_head if f.strip()]
                        if former_head == []:
                            former_head = None
                # Deprecated heading          
                elif 'madsrdf:DeprecatedAuthority' in record['@type']:
                    heading = '_' + record['madsrdf:variantLabel']['@value']
                    lang = record['madsrdf:variantLabel']['@language']
                    kind = [t[8:] for t in record['@type'] if t[8:] != 'DeprecatedAuthority' and t[8:] !='Variant'][0]
                    if 'madsrdf:deletionNote' in record:
                        # Reason for deletion
                        deletion_note = record['madsrdf:deletionNote']['@value']
                # This shouldn't happen 
                else:
                    break 
            # If the heading has an associated library of congress classification
            if "lcc:ClassNumber" in record['@type']:
                lcc = record['madsrdf:code']
            # Collect date information
            if 'ri:RecordInfo' in record['@type']:
                if record['ri:recordStatus'] == 'new':
                    year_new = record['ri:recordChangeDate']['@value']
                    year_new = int(year_new[:4])
                elif record['ri:recordStatus'] == 'revised':
                    year_rev =  record['ri:recordChangeDate']['@value']
                    year_rev = int(year_rev[:4])
                elif record['ri:recordStatus'] == 'deprecated':
                    year_dep = record['ri:recordChangeDate']['@value']
                    year_dep = int(year_dep[:4])
            # Collect potential variants of a term
            if '_:n' in record['@id'] and 'madsrdf:Variant' in record['@type']:
                alt_terms[record['@id']] = record['madsrdf:variantLabel']['@value']
        # Term ids replaced with term for those not linked to a subject headings
        if former_head is not None:
            former_head = [alt_terms[i] for i in former_head]
        if syns is not None:
            syns = [alt_terms[i] for i in syns]
        if heading is not None: 
            lcsh[term_id] = {'heading': heading,
                            'cleaned': clean(heading),
                            'language': lang,
                            'formerHeadings': former_head, 
                            'lcc': lcc,
                            'type': kind,
                            'yearAdded': year_new,
                            'yearRevised': year_rev,
                            'yearDeprecated': year_dep,
                            'bt': bt,
                            'nt': nt,
                            'synonyms': syns,
                            'deleteNote': deletion_note}
    print(f'----------------\n{idx+1} records processed!')
    return lcsh
    
def has_parents(term):
    if term['bt'] is not None:
        return True

def has_children(term):
    if term['nt'] is not None:
        return True
'''
Collects the number of terms in the LCSH that are deprecated and returns a dictionary of these terms.
'''
def get_deprecated(lcsh):
    deprecated = {}
    for idx, term in lcsh.items():
        # if a deprecation date exists
        if term['yearDeprecated'] is not None:
            deprecated[idx] = term
    return deprecated

def get_current_lcsh(lcsh):
    pruned = {}
    for idx, term in lcsh.items():
        if term['yearDeprecated'] is None:
            pruned[idx] = term
    return pruned

'''
Remove deprecated LCSHs that were created and removed within the span of a year. 
'''
def prune_temporary_lcsh(lcsh):
    pruned = {}
    for idx, term in lcsh.items():
        if term['yearDeprecated'] is None:
            pruned[idx] = term
        else:
            if term['yearDeprecated'] - term['yearAdded'] >= 1:
                pruned[idx] = term
    return pruned

'''
Count the instances of each type of LCSH. 
'''
def count_types(lcsh):
    lcsh_types = {}
    for heading in lcsh.values():
        type = heading['type']
        if type in lcsh_types:
            lcsh_types[type] += 1
        else:
            lcsh_types[type] = 1
    return lcsh_types

'''
Collect all LCSH that are topics. This means that they are not subdivisions or complex headings.
Also ensures that they only reference parents/children thar are also topics. 
'''
# figure out how to make components of complex parents the parents!!
def get_english_topics(lcsh):
    topics = {}
    for idx, term in lcsh.items():
        if (term['type'] == 'Topic' and term['language'] == 'en'
            and 'characters)' not in term['heading'].lower()
            and '(imaginary' not in term['heading'].lower()
            and '(game' not in term['heading'].lower()
            and '(legend' not in term['heading'].lower()
            and '(tale' not in term['heading'].lower()
            and ' phenomenon)' not in term['heading'].lower()):
            topics[idx] = term
    return topics

def get_gendered_lcsh(men_words, women_words, lcsh):
    m_regex = re.compile(r'\b(?:%s)\b' % '|'.join(men_words), re.IGNORECASE)
    w_regex = re.compile(r'\b(?:%s)\b' % '|'.join(women_words), re.IGNORECASE)
    gendered_headings = {'CATEGORY': [], 'CLEANED': [], 'YEAR_ADDED': [], 'GENDER':[]}
    for idx in lcsh:
        gender = None
        cleaned_heading = lcsh[idx]['cleaned']
        m_flag = bool(m_regex.search(cleaned_heading))
        w_flag = bool(w_regex.search(cleaned_heading))
        if m_flag and w_flag:
            gender = 'A'
        elif m_flag:
            gender = 'M'
        elif w_flag:
            gender = 'W'
        if gender is not None:
            gendered_headings['CATEGORY'].append(lcsh[idx]['heading'])
            gendered_headings['CLEANED'].append(cleaned_heading)
            gendered_headings['GENDER'].append(gender)
            gendered_headings['YEAR_ADDED'].append(lcsh[idx]['yearAdded'])
    return pd.DataFrame(gendered_headings)

def save_as_csv(lcsh, name, fp):
    rows = []
    headers = ['ID', 'HEADING', 'CLEANED', 'LANGUAGE', 'LCC', 'TYPE', 'YEAR_ADDED', 'YEAR_REVISED', 
                'BT', 'NT', 'SYNONYMS', 'YEAR_DEPRECATED', 'FORMER_HEADINGS', 'DELETION_NOTE']
    for idx, term in lcsh.items():
        if term['bt'] is not None:
            bt = ';'.join(term['bt'])
        else:
            bt = "None"
        if term['nt'] is not None:
            nt = ';'.join(term['nt'])
        else:
            nt = "None"
        if term['synonyms'] is not None:
            synonyms = ';'.join(term['synonyms'])
        else:
            synonyms = "None"
        if term['formerHeadings'] is not None:
            former_headings = ';'.join(term['formerHeadings'])
        else:
            former_headings = "None"
        row = [idx, term['heading'], term['cleaned'], term['language'], 
            term['lcc'], term['type'], term['yearAdded'],
            term['yearRevised'], bt, nt, synonyms, term['yearDeprecated'], 
            former_headings, term['deleteNote']]
        rows.append(row)
    lcsh_df = pd.DataFrame(rows, columns=headers)
    lcsh_df.to_csv(f'{fp}/{name}.csv.gz', index=False, compression='gzip')
  

'''
Extracts the Library of Congress Subject Headings from the JSON-LD file and saves it as a pickle file.
'''
def process_lcsh(fp, m_words=['men', 'male'], w_words=['women', 'female'], save_all=False):
    lcsh = extract_lcsh(f"{fp}/subjects.madsrdf.jsonld")
    topic_lcsh = get_english_topics(lcsh)
    current_topic_lcsh = get_current_lcsh(topic_lcsh)
    gendered_lcsh = get_gendered_lcsh(m_words, w_words, current_topic_lcsh)
    gendered_lcsh.to_csv(f'{fp}/lcsh-gendered.csv', index=False)
    print(f'Gender tagged LCSH data saved in {fp}')
    if save_all:
        save_as_csv(lcsh, 'lcsh-all', fp)
        print(f'All LCSH data saved in {fp}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process LCSH Data.")

    parser.add_argument('folder_path', type=str, help='The path to the folder where data should be read and stored')
    parser.add_argument('--m_words', type=list, default=['men', 'male'], help='An argument containing the words used to find headings for men. Default list: [men, male]')
    parser.add_argument('--w_words', type=list, default=['women', 'female'], help='An argument containing the words used to find headings for women. Default list: [women, female]')
    parser.add_argument('--save_all', action='store_true', help='An optional argument that specifies whether to save the full set of lcsh')
    args = parser.parse_args()
    process_lcsh(args.folder_path, args.m_words, args.w_words, args.save_all)