import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import argparse
import csv
import copy
import re
from collections import Counter
from collections import defaultdict
from Code import marking_gender as gm

def extract_lcsh(file):
    lcsh = {}
    print('Reading LCSH data...')
    for idx, line in enumerate(open(file)):
        if idx%50000==0:
            print(f'{idx} records processed')
        line = json.loads(line)
        # Define variables
        term_id = line['@id'][22:]
        heading, lcc, year_new, year_rev, year_dep, kind = None, "None", None, "None", "None", None
        deletion_note, bt, nt, syns, former_head, lang = "None", None, None, None, None, None
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
                    if 'madsrdf:hasNarrowerAuthority' in record:
                        # Narrower Terms
                        nt = record['madsrdf:hasNarrowerAuthority']
                        if type(nt) is list:
                            nt = [term['@id'][39:] for term in nt]
                        else:
                            nt = [nt['@id'][39:]]
                    if 'madsrdf:hasVariant' in record:
                        # Synonyms of a term
                        syns = record['madsrdf:hasVariant']
                        if type(syns) is list:
                            syns = [term['@id'] for term in syns]
                        else:
                            syns = [syns['@id']]
                    if 'madsrdf:hasEarlierEstablishedForm' in record:
                        # Former Headings
                        former_head = record['madsrdf:hasEarlierEstablishedForm']
                        if type(former_head) is list:
                            former_head = [term['@id'] for term in former_head]
                        else:
                            former_head = [former_head['@id']]  


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
                elif record['ri:recordStatus'] == 'revised':
                    year_rev =  record['ri:recordChangeDate']['@value']
                elif record['ri:recordStatus'] == 'deprecated':
                    year_dep = record['ri:recordChangeDate']['@value']
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
'''
Get the year a LCSH was added to the online database
'''
def get_year_added(term):
    return int(term['yearAdded'][:4])

def get_year_deprecated(term):
    if term['yearDeprecated'] is not None and term['yearDeprecated'] != 'None':
        return int(term['yearDeprecated'][:4])
    else:
        return None
    
def has_parents(term):
    parent_flag = False
    if term['bt'] is not None:
        parents = [idx for idx in term['bt'] if idx.strip()]
        if parents != []:
            parent_flag =  True
    return parent_flag

def has_children(term):
    child_flag = False
    if term['nt'] is not None:
        children = [idx for idx in term['nt'] if idx.strip()]
        if children != []:
            child_flag = True
    return child_flag

'''
Collects the number of terms in the LCSH that are deprecated and returns a dictionary of these terms.
'''
def get_deprecated(lcsh):
    deprecated = {}
    for idx, term in lcsh.items():
        # if a deprecation date exists
        if get_year_deprecated(term) is not None:
            deprecated[idx] = term
    return deprecated

def prune_deprecated(lcsh):
    pruned = {}
    for idx, term in lcsh.items():
        if get_year_deprecated(term) is None:
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
            if get_year_deprecated(term) - get_year_added(term) >= 1:
                pruned[idx] = term
    return pruned

'''
Count the instances of each type of LCSH. The types are as follows:
    'Topic', 'Geographic', 'CorporateName', 'FamilyName', 
    'Title', 'ConferenceName', 'PersonalName', 'ComplexSubject',
    'GenreForm', 'HierarchicalGeographic'
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
def get_topics(lcsh):
    topics = {}
    lcsh, pruned= prune_names_and_titles(lcsh)
    for idx, term in lcsh.items():
        if (term['type'] == 'Topic' and term['language'] == 'en'):
            topics[idx] = copy.deepcopy(term)
            if has_parents(term):
                topics[idx]['bt'] = {idx for idx in term['bt'] if idx.strip() and not pruned[idx] and lcsh[idx]['type'] == 'Topic'}
                if topics[idx]['bt'] == {}:
                    topics[idx]['bt'] = None
            if has_children(term):
                topics[idx]['nt'] = {idx for idx in term['nt'] if idx.strip() and not pruned[idx] and lcsh[idx]['type'] == 'Topic'}
                if topics[idx]['nt'] == {}:
                    topics[idx]['nt'] = None 
    return topics

'''
Prune the LCSH to remove terms that are not useful for analysis.
'''
def prune_names_and_titles(lcsh):
    headings = {}
    pruned = defaultdict(bool)
    for idx, term in lcsh.items():
        # a lot of specific cases of terms that I don't want to include in the analysis. 
        if ('(Fictitious character' not in term['heading']
            and '(Symbolic character' not in term['heading']
            and '(Legendary character' not in term['heading']
            and '(Game)' not in term['heading']
            and '(International relations)' not in term['heading']
            and 'word)' not in term['heading']
            and '(Legend)' not in term['heading']
            and '(Miracle)' not in term['heading']
            and '(Race horse)' not in term['heading']
            and '(Horse)' not in term['heading']
            and '(Dog)' not in term['heading']
            and ' mythology)' not in term['heading']
            and 'deities)' not in term['heading']
            and '(Parable)' not in term['heading']
            and '(Tale)' not in term['heading']
            and '(Nickname)' not in term['heading']
            and '(Statue)' not in term['heading']
            and 'deity)' not in term['heading']
            and 'locomotives)' not in term['heading']
            and '(Imaginary' not in term['heading']):
            headings[idx] = term
        else:
            pruned[idx] = True
    return headings, pruned

def tag_gendered_lcsh(lcsh):
    for idx in lcsh:
        lcsh[idx]['gender'] = None
        lcsh[idx]['genderWord'] = None
    gm.tag_with_gender(lcsh, 'm')
    gm.tag_with_gender(lcsh, 'w')
    #gendered_headings = {idx:term for idx, term in lcsh.items() if lcsh[idx]['gender'] is not None}
    #return gendered_headings

def convert_none(val):
    if val == 'None':
        return None
    else:
        return val

def convert_list(val): 
    if val == 'None':
        return None
    else:
        return val.split(';')

def write_row(csv_writer, idx, term, gendered=False):
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
    row = [idx, term['heading'], term['cleaned'], term['language'], term['lcc'], term['type'], int(term['yearAdded'][:4]), term['yearRevised'], bt, nt, synonyms, term['yearDeprecated'], former_headings, term['deleteNote']]
    if gendered:
        row.append(term['gender'])
        row.append(term['genderWord'])
    csv_writer.writerow(row)


def save_as_csv(lcsh, name, fp, gendered=False):
    with open(f'{fp}/{name}.csv', 'w', newline='', encoding='utf8') as csvFile:
        csv_writer = csv.writer(csvFile, delimiter='\t')
        headers = ['ID', 'HEADING', 'CLEANED', 'LANGUAGE', 'LCC', 'TYPE', 'YEAR_ADDED', 'YEAR_REVISED', 
                   'BT', 'NT', 'SYNONYMS', 'YEAR_DEPRECATED', 'FORMER_HEADINGS', 'DELETION_NOTE']
        if gendered:
            headers.append('GENDER')
            headers.append('GENDER_WORD')
        csv_writer.writerow(headers)
        for idx, term in lcsh.items():
            write_row(csv_writer, idx, term, gendered)

def csv_to_dict(fp, gendered=False):
    lcsh = {}
    with open(fp, 'r', newline='', encoding='utf8') as csvFile:
        csv_reader = csv.reader(csvFile, delimiter='\t')
        next(csv_reader)
        for row in csv_reader:
            idx, heading, cleaned, lang, lcc, kind, year_new = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            year_rev = row[7]
            bt = convert_list(row[8])
            nt = convert_list(row[9])
            syns = convert_list(row[10])
            year_dep = row[11]
            former_headings = convert_list(row[12])
            delete_note = row[13]
            lcsh[idx] = {'heading': heading,
                         'cleaned': cleaned,
                         'language': lang,
                         'lcc': lcc,
                         'type': kind,
                         'yearAdded': int(year_new[:4]),
                         'yearRevised': year_rev,
                         'bt': bt,
                         'nt': nt,
                         'synonyms': syns,
                         'yearDeprecated': year_dep,
                         'formerHeadings': former_headings,
                         'deleteNote': delete_note}
            if gendered:
                lcsh[idx]['gender'] = row[14]
                lcsh[idx]['genderWord'] = row[15]
    return lcsh

'''
Extracts the Library of Congress Subject Headings from the JSON-LD file and saves it as a pickle file.
'''
from collections import Counter
def process_lcsh(fp, save_all=True, save_deprecated=True):
    lcsh = extract_lcsh(f"{fp}/subjects.madsrdf.jsonld")
    no_brackets = Counter([' '.join(re.sub(r'\(.*?\)', r'', t['heading']).lower().split()) for t in lcsh.values() if ' people)' in t['heading'].lower()])
    gm.clean_all(lcsh, 'heading', no_brackets, True)
    print(len([t['cleaned'] for t in lcsh.values() if t['type'] == 'Topic']))
    print(len(list(set([t['cleaned'] for t in lcsh.values() if t['type'] == 'Topic']))))
    topic_lcsh = get_topics(lcsh)
    tag_gendered_lcsh(topic_lcsh)
    current_topic_lcsh = prune_deprecated(topic_lcsh)
    save_as_csv(current_topic_lcsh, 'lcsh-topics', fp, True)
    print(f'Gender tagged LCSH data saved in {fp}')
    if save_all:
        save_as_csv(lcsh, 'lcsh-all', fp)
        print(f'All LCSH data saved in {fp}')
    if save_deprecated:
        deprecated_lcsh = get_deprecated(topic_lcsh)
        save_as_csv(deprecated_lcsh, 'lcsh-topics-deprecated', fp, True)
        print(f'Deprecated LCSH data saved in {fp}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process LCSH Data.")

    parser.add_argument('folder_path', type=str, help='The path to the folder where data should be read and stored')
    parser.add_argument('--save_all', action='store_true', help='An optional argument that specifies whether to save the full set of lcsh')
    parser.add_argument('--save_deprecated', action='store_true',  help='An optional argument that specifies whether to save the deprecated LCSH')
    args = parser.parse_args()
    process_lcsh(args.folder_path, args.save_all, args.save_deprecated)

    # subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

    # parser_load_lcsh = subparsers.add_parser('all_lcsh', help='Read LCSH data from a JSON-LD file and save it as a CSV file')
    # parser_load_lcsh.add_argument('output_file', type=str, help='The path to the output file')
    # parser_load_lcsh.add_argument('--save_all', action='store_true', help='An optional argument that specifies whether to save the full set of lcsh')
    # parser_load_lcsh.add_argument('--get_deprecated', action='store_true',  help='An optional argument that specifies whether to extract only deprecated LCSH')
    
    # parser_gendered_lcsh = subparsers.add_parser('gendered_lcsh', help='Extract gendered LCSH from the LCSH data')
    # parser_gendered_lcsh.add_argument('path', type=str, help='The path to the folder where data should be read and stored')
    # parser_gendered_lcsh.add_argument('--input_file', type=str, default='lcsh-topics', help='An optional argument that specified the path to the file containing the LCSH data')
    # parser_gendered_lcsh.add_argument('--save_deprecated', action='store_true', help='An optional argument that specifies whether to save deprecated gendered LCSH')
    # # args = parser.parse_args()

    # if args.command == 'all_lcsh':
    #     process_lcsh(args.output_file, args.save_all, args.get_deprecated)

    # elif args.command == 'gendered_lcsh':
    #     process_gendered_lcsh(args.path, args.input_file, args.save_deprecated)
 