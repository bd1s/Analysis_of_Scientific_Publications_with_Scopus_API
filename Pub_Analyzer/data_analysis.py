import json
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import seaborn as sns
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
import os

with open("Config.json") as con_file:
    config = json.load(con_file)

client = ElsClient(config['apikey'])
if 'insttoken' in config:
    client.inst_token = config['insttoken']

def get_publications(topic, start=0, count=25):
    query = f"SUBJAREA({topic})"
    base_url = 'https://api.elsevier.com/content/search/scopus'
    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': config['apikey']
    }
    params = {
        'query': query,
        'start': start,
        'count': count
    }

    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('https://', adapter)

    try:
        response = session.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()['search-results']['entry']
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        return None

def extract_fields_to_dataframe(publications, topic):
    data = []
    for publication in publications:
        fields = {
            'topic': topic,
            'authors': publication.get('dc:creator', ''),
            'title': publication.get('dc:title', ''),
            'publicationName': publication.get('prism:publicationName', ''),
            'doi': publication.get('prism:doi', ''),
            'volume': publication.get('prism:volume', ''),
            'issue': publication.get('prism:issueIdentifier', ''),
            'pageRange': publication.get('prism:pageRange', ''),
            'coverDate': publication.get('prism:coverDate', ''),
            'affiliation': publication.get('affiliation', ''),
            'citedbyCount': publication.get('citedby-count', 0)
        }
        data.append(fields)

    df = pd.DataFrame(data)
    return df

def get_all_publications_for_topic(topic, total_count=100, batch_size=25):
    all_publications = []
    for start in range(0, total_count, batch_size):
        publications = get_publications(topic, start=start, count=batch_size)
        if not publications:
            break
        all_publications.extend(publications)
    return all_publications

def retrieve_and_process_data(topics):
    total_dataframes = []

    for topic in topics:
        publications = get_all_publications_for_topic(topic, total_count=100)
        if publications:
            df = extract_fields_to_dataframe(publications, topic)
            total_dataframes.append(df)

    merged_df = pd.concat(total_dataframes, ignore_index=True)
    merged_df.to_csv('publications.csv', index=False)

    df = pd.read_csv('publications.csv')

    def extract_affiliation_details(affiliation):
        try:
            if isinstance(affiliation, str):
                affilname_match = re.search(r"'affilname': '([^']+)'", affiliation)
                country_match = re.search(r"'affiliation-country': '([^']+)'", affiliation)

                affilname = affilname_match.group(1) if affilname_match else None
                country = country_match.group(1) if country_match else None

                return affilname, country
            else:
                return None, None
        except Exception as e:
            print(f"Error during affiliation extraction: {e}")
            return None, None

    df[['affilname', 'affiliation-country']] = df['affiliation'].apply(
        lambda x: pd.Series(extract_affiliation_details(x))
    )

    imputer = SimpleImputer(strategy='mean')
    df[['citedbyCount']] = imputer.fit_transform(df[['citedbyCount']])
    df.fillna('', inplace=True)
    df['coverDate'] = pd.to_datetime(df['coverDate'], errors='coerce')
    df['year'] = df['coverDate'].dt.year
    df['month'] = df['coverDate'].dt.month

    scaler = StandardScaler()
    df[['citedbyCount']] = scaler.fit_transform(df[['citedbyCount']])
    df.drop_duplicates(inplace=True)
    df.to_csv('publications_preprocessed.csv', index=False)

    return df

def generate_analysis(df):
    if not os.path.exists('static/plots'):
        os.makedirs('static/plots')

    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x='citedbyCount', bins=20, kde=True)
    plt.title('Distribution of Citations per Publication')
    plt.xlabel('Number of Citations')
    plt.ylabel('Frequency')
    plt.savefig('static/plots/citations_distribution.png')
    plt.close()

    top_authors = df.groupby('authors')['citedbyCount'].sum().nlargest(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_authors.values, y=top_authors.index)
    plt.title('Distribution of Citations by Author (Top 10)')
    plt.xlabel('Number of Citations')
    plt.ylabel('Author')
    plt.savefig('static/plots/citations_by_author.png')
    plt.close()

    top_authors_pubs = df['authors'].value_counts().nlargest(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_authors_pubs.values, y=top_authors_pubs.index)
    plt.title('Number of Publications by Author (Top 10)')
    plt.xlabel('Number of Publications')
    plt.ylabel('Author')
    plt.savefig('static/plots/publications_by_author.png')
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='year')
    plt.title('Number of Publications by Year')
    plt.xlabel('Year')
    plt.ylabel('Number of Publications')
    plt.savefig('static/plots/publications_by_year.png')
    plt.close()

    top_journals = df['publicationName'].value_counts().nlargest(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_journals.values, y=top_journals.index)
    plt.title('Distribution of Publications by Journal (Top 10)')
    plt.xlabel('Number of Publications')
    plt.ylabel('Journal')
    plt.savefig('static/plots/publications_by_journal.png')
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='topic')
    plt.title('Distribution of Publications by Topic')
    plt.xlabel('Topic')
    plt.ylabel('Number of Publications')
    plt.xticks(rotation=90)
    plt.savefig('static/plots/publications_by_topic.png')
    plt.close()

    top_affiliations = df['affilname'].value_counts().nlargest(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_affiliations.values, y=top_affiliations.index)
    plt.title('Distribution of Publications by Affiliation (Top 10)')
    plt.xlabel('Number of Publications')
    plt.ylabel('Affiliation')
    plt.savefig('static/plots/publications_by_affiliation.png')
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='affiliation-country')
    plt.title('Geographical Distribution of Affiliations by Country')
    plt.xlabel('Country')
    plt.ylabel('Number of Publications')
    plt.xticks(rotation=90)
    plt.savefig('static/plots/affiliations_by_country.png')
    plt.close()
