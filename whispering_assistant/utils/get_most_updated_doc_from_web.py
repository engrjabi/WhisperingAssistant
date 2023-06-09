import itertools
from pprint import pprint
from langchain.schema import Document
from langchain.text_splitter import TokenTextSplitter
from search_engines import Google
from fuzzywuzzy import fuzz
import nltk
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from InstructorEmbedding import INSTRUCTOR
from sklearn.metrics.pairwise import cosine_similarity
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
import asyncio

model = INSTRUCTOR('hkunlp/instructor-base', device="cpu")
engine = Google()
nltk.download('punkt')
nltk.download('stopwords')

similarity_threshold = 0.92


# If the word is longer than 5 characters, we should include the whole word instead of cutting it.
def get_root_words(query):
    query = re.sub(r"[^a-zA-Z0-9\s]", "", query)  # Remove all non-alphabetic and non-numeric characters
    stemmer = PorterStemmer()
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(query)
    filtered_words = [word for word in words if word not in stop_words]  # filter out stop words
    root_words = [word if len(word) > 8 else stemmer.stem(word) for word in filtered_words]
    return root_words


def remove_fuzzy_duplicates(array, similarity_threshold=80):
    # Initialize an empty list to store the unique items
    unique_items = []

    # Loop through each item in the array
    for item in array:
        # If the item is not similar to any item in unique_items, add it to unique_items
        if not any(fuzz.ratio(item, unique_item) > similarity_threshold for unique_item in unique_items):
            unique_items.append(item)

    return unique_items


def filter_with_adjacent_items(array, query_root_keywords, num_adjacent):
    # Initialize a list to store indices of items containing the keywords
    indices = []

    # Loop through the array to find indices of items containing the keywords
    for i, item in enumerate(array):
        if any(keyword.lower() in item.lower() for keyword in query_root_keywords):
            indices.append(i)

    # Initialize a list to store the final filtered items
    filtered_items = []

    # Add items at the indices found and their adjacent items to the filtered items list
    for index in indices:
        start = max(0, index - num_adjacent)  # Ensure start is not less than 0
        end = min(len(array), index + num_adjacent + 1)  # Ensure end does not exceed the length of the array
        filtered_items.extend(array[start:end])

    return filtered_items


async def extract_text(session: ClientSession, url: str, query_root_keywords=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    # Create a ClientTimeout object. For example, to timeout after 10 seconds:
    timeout = aiohttp.ClientTimeout(total=2)

    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            try:
                html = await response.text()
            except UnicodeDecodeError:
                print("Error decoding response text as UTF-8. Attempting with replacement characters.")
                raw_response = await response.read()
                html = raw_response.decode('utf-8', 'replace')

        soup = BeautifulSoup(html, 'html.parser')

    except asyncio.TimeoutError:
        print("The request timed out.")
        return ""

    for script in soup(['script', 'style']):  # remove all javascript and stylesheet code
        script.extract()

    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())

    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

    # drop blank lines and lines with less than or equal to 5 words
    text = '\n'.join(
        chunk for chunk in chunks if chunk and (8 < len(chunk.split()) < 200 or len(chunk.split()) > 400)).split(
        '\n')

    text = filter_with_adjacent_items(text, query_root_keywords=query_root_keywords, num_adjacent=3)
    text = remove_fuzzy_duplicates(text)

    return text


async def scrape_async(keywords, results_links):
    async with aiohttp.ClientSession() as session:
        tasks = [extract_text(session, link, query_root_keywords=keywords) for link in results_links]
        scrape_results = await asyncio.gather(*tasks, return_exceptions=True)
    return scrape_results


# Incase we don't meet the threshold still return the highest on all the searches
max_similarity = 0.0
best_document = ""


def get_similar_contexts(query_text):
    global max_similarity, best_documents

    # We are resetting it here so that we don't get the previous results from previous searches
    max_similarity = 0.0
    best_documents = []

    keywords = get_root_words(query_text)
    search_engine_results = engine.search(query_text, pages=1)

    search_engine_texts = "  ".join(search_engine_results.text())

    text_splitter = TokenTextSplitter(chunk_size=410, chunk_overlap=102)
    search_engine_texts_documents = text_splitter.split_documents([Document(page_content=search_engine_texts)])

    similarities, related_page_contents = get_similarities(query_text, search_engine_texts_documents)

    # Here we sort the results by their similarity and select the top 3
    top_three = sorted(zip(similarities, related_page_contents), key=lambda pair: pair[0], reverse=True)[:2]

    if all(similarity > similarity_threshold for similarity, _ in top_three):
        best_documents.extend([content for _, content in top_three])
        return " ".join(best_documents)

    # If the search result texts do not have enough context, we need to scrape results
    search_engine_links = search_engine_results.links()[:5]
    scrape_async_results = asyncio.run(scrape_async(keywords, search_engine_links))

    flattened_scrape_async_results = list(itertools.chain(*scrape_async_results))
    string_scrape_async_results = '  '.join(flattened_scrape_async_results)

    scrape_async_results_documents = text_splitter.split_documents([Document(page_content=string_scrape_async_results)])

    similarities, related_page_contents = get_similarities(query_text, scrape_async_results_documents)

    top_three = sorted(zip(similarities, related_page_contents), key=lambda pair: pair[0], reverse=True)[:2]

    best_documents.extend([content for _, content in top_three])

    print("📌 best_documents", best_documents)

    return search_engine_texts + " ".join(best_documents)


def get_similarities(query_text, documents_to_search):
    query_text_decorated = [
        ['represent question for retrieving relevant documents: ',
         'Can this document answer this question?: ' + '"' + query_text + '"']]

    document_page_contents = [doc.page_content for doc in documents_to_search]

    query_embeddings = model.encode(query_text_decorated)

    scores_and_contents = []

    # Getting higher similarity if storage instruction is not added: storage = 'represent document for retrieval: '
    for document_page_content in document_page_contents:
        print("📌 document_page_content", document_page_content)
        corpus_embeddings = model.encode([document_page_content])
        similarity = cosine_similarity(query_embeddings, corpus_embeddings)[0][0]
        print("📌 similarities", similarity)

        scores_and_contents.append((similarity, document_page_content))
        scores_and_contents.sort(key=lambda x: x[0], reverse=True)  # sort by score

        if len(scores_and_contents) > 2:  # if we have more than 3 results
            scores_and_contents = scores_and_contents[:2]  # keep only top 3

        # if we have 3 results with high scores, we can return early
        if len(scores_and_contents) == 2 and all(score > similarity_threshold for score, _ in scores_and_contents):
            return [score for score, _ in scores_and_contents], [content for _, content in scores_and_contents]

    # if we reach this point, we didn't find 3 results with high scores
    # we return the top 3 results (or less if there are less than 3)
    return [score for score, _ in scores_and_contents], [content for _, content in scores_and_contents]

# 📌 TEST Execution
# get_similar_contexts('is intel i9 better than ryzen?')
