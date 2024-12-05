
import requests
import re
from bs4 import BeautifulSoup
import inflect

p = inflect.engine()

def scrape_wikipedia_links1(url, column):
    # Send a GET request to the Wikipedia page
    response = requests.get(url)
    wiki_links = []

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        htmltable = soup.find('table', {'class': 'wikitable'})
        identities = []
        for row in htmltable.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > column:
                identity = [a.get_text(strip=True) for a in cells[column].find_all('a')]
                identities.extend(identity)
        return identities


def clean_identity(identity):
    identity = identity.replace('-', ' ').replace("'", " '").lower()
    if '(' in identity:
        split_ids = identity.split('(')
    elif ' and ' in identity:
        split_ids = identity.split(' and ')
    else:
        split_ids = [identity]
    cleaned_ids = []
    for id in split_ids:
        if '[' in id:
            id = id.split('[')[0]
        elif 'people' in id:
            id = id.split('people')[0]
        # replace punctuation with spaces
        id = re.sub(r'[^\w\s]', ' ', id)
        # remove extra spaces
        id = re.sub(r'\s+', ' ', id).strip()
        if id == '':
            continue
        # add the plural and singular forms of the identity but must check which form its currently in using inflect
        # if p.singular_noun(id) is not False:
        #     cleaned_ids.append(id)
        #     cleaned_ids.append(p.singular_noun(id))
        # else:
        #     cleaned_ids.append(id)
        #     cleaned_ids.append(p.plural(id))
        cleaned_ids.append(id)

    return cleaned_ids

def clean(identities):
    cleaned_identities = []
    for identity in identities:
        cleaned_identities.extend(clean_identity(identity))
    return cleaned_identities

def get_cultural_identities():
    ethnicities = scrape_wikipedia_links1('https://en.wikipedia.org/wiki/List_of_contemporary_ethnic_groups', 0)
    ethnicities = clean(ethnicities)
    nationalities = scrape_wikipedia_links1('https://en.wikipedia.org/wiki/List of adjectival and demonymic forms for countries and nations', 1)
    nationalities = clean(nationalities)
    return list(set(ethnicities + nationalities + ['north american', 'south american', 'central american', 
                                                   'east asian', 'south asian', 'southeast asian', 'central asian',
                                                     'middle eastern', 'north african', 'sub saharan african',
                                                       'australian', 'pacific islander', 'european', 'easter european',
                                                       'western european', 'southern european', 'northern european', 'eurasian',
                                                         'asian', 'african', 'black', 'white', 'latino', 'hispanic', 'latin american',
                                                           'indigenous', 'native american', 'aboriginal', 'aboriginal australian', 'first nations',
                                                             'inuit', 'metis']))


if __name__ == '__main__':
    identities = get_cultural_identities()
    with open('Data/cultural_identities.txt', 'w', encoding='utf-8') as f:
        f.write('IDENTITY\n')
        for identity in identities:
            if identity.strip() != '':
                f.write(identity + '\n')