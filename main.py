import openai
import requests
import os
import time
from bs4 import BeautifulSoup
from typing import Dict, List, Union, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def summarize(text: str, title: Optional[str] = None) -> str:
    if title:
        title = "Use the following title: " + title + "\n\n"
    prompt = (f"Summarize the following text. "
              "Make the summary interesting as it will be read out loud "
              "in a podcast format. The host and audience are very interested in "
              "programming and AI. Make it roughly two paragraphs long"
              " add transition words before and after to make the summary flow well."
              " as it will be combined with other summaries."
              " start by crafting an intro sentence that hooks the audience."
              " Then, summarize the text in a concise manner."
              f"{title if title else ''}"
              f"\n\nText: {text}\n\nSummary:")

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]


def get_hn_posts(post_type: str, num_posts: int) -> List[Dict[str, Union[str, int]]]:
    params = {
        'query': '',
        'tags': post_type,
        'numericFilters': 'points>1',
        'hitsPerPage': num_posts,
        'page': 0
    }

    response = requests.get('http://hn.algolia.com/api/v1/search_by_date', params=params)
    response.raise_for_status()
    data = response.json()
    return data['hits']


def get_comments_from_post(post_id: str) -> List[Dict[str, Union[str, int]]]:
    params = {
        'query': '',
        'tags': 'comment,story_' + post_id,
        'hitsPerPage': 1000,
        'page': 0
    }

    response = requests.get('http://hn.algolia.com/api/v1/search_by_date', params=params)
    response.raise_for_status()
    data = response.json()
    return data['hits']

def extract_text(html_content: Optional[str]) -> Optional[str]:
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        return ' '.join(soup.stripped_strings)
    return None


def get_text_from_hn_post(post: Dict[str, Union[str, int, None]]) -> Tuple[str, Union[str, int, None]]:
    url = post.get('url')
    if url:
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return ("html", soup.prettify())
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch content from {url}. Error: {e}")
            return ("ERROR", None)
    return ("text", post.get('story_text'))


def chunk_text(text: str, max_length: int) -> List[str]:
    words = text.split()
    chunks = []
    current_chunk = [] 
    current_length = 0
    for word in words:
        if current_length + len(word) <= max_length:
            current_chunk.append(word)
            current_length += len(word)
        else:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)

    chunks.append(' '.join(current_chunk))
    return chunks


def map_title_summary(posts: List[Dict[str, Union[str, int]]]) -> Dict[str, str]:
    title_summary_map = {}

    for post in posts:
        title = post.get('title')
        post_type, content = get_text_from_hn_post(post)
        print(f"Summarizing {title}")
        if post_type == "ERROR":
            continue

        if post_type == "html":
            content = extract_text(content)

        comments = []
        if 'ask_hn' in post['_tags']:
            comments = get_comments_from_post(str(post['objectID']))
            comments_text = ' '.join([comment['comment_text'] for comment in comments])
            print(f"Comments: {comments_text}")
            content += " Comments: " + comments_text

        if len(content) > 12000:
            chunks = chunk_text(content, 12000)
            chunk_summaries = []

            for chunk in chunks:
                chunk_summary = summarize(chunk + "\nPlease provide a brief summary.")
                chunk_summaries.append(chunk_summary)
                time.sleep(10)

            full_summary_text = ' '.join(chunk_summaries)
            try:
                final_summary = summarize(full_summary_text + "\nPlease provide a concise final summary.", title)
            except Exception as e:
                continue
        else:
            final_summary = summarize(content, title)

        title_summary_map[title] = final_summary
        print(f"Title: {title}\nSummary: {final_summary}\n\n")
        time.sleep(15)
    return title_summary_map


def curate(title_summary_map: Dict[str, str]) -> str:
    podcast_script = "Here's your daily summary."

    for i, title in enumerate(title_summary_map):
        summary = title_summary_map[title]
        podcast_script += summary

    return podcast_script


def main():
    posts = get_hn_posts('story', 5)
    # posts += get_hn_posts('ask_hn', 5)
    title_summary_map = map_title_summary(posts)
    podcast_script = curate(title_summary_map)
    print(f"Podcast script: {podcast_script}")


if __name__ == "__main__":
    main()
