import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from supabase import create_client
from openai import OpenAI
from dotenv import load_dotenv
import json
import time

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_URL = "https://saiyashwanth.com"
START_URL = f"{BASE_URL}/articles"


def is_same_domain(url):
    return urlparse(url).netloc in ["saiyashwanth.com", "www.saiyashwanth.com", ""]


def extract_article_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else "Untitled"
        
        article = soup.find('article') or soup.find('main') or soup.find('body')
        
        for tag in article.find_all(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        
        paragraphs = article.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        return {
            "title": title_text,
            "content": content[:10000],
            "url": url,
            "word_count": len(content.split())
        }
    except Exception as e:
        print(f"  ✗ Failed to extract from {url}: {e}")
        return None


def crawl_articles(start_url, max_articles=50):
    visited = set()
    to_visit = [start_url]
    articles = []
    
    print(f"🕷️  Crawling {start_url}...")
    
    while to_visit and len(articles) < max_articles:
        url = to_visit.pop(0)
        
        if url in visited:
            continue
        
        visited.add(url)
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            for link in links:
                full_url = urljoin(BASE_URL, link['href'])
                
                if is_same_domain(full_url) and full_url not in visited:
                    if '/articles/' in full_url or full_url == START_URL:
                        if full_url not in to_visit:
                            to_visit.append(full_url)
            
            if url != START_URL and '/articles/' in url:
                article = extract_article_content(url)
                if article and article['word_count'] > 200:
                    articles.append(article)
                    print(f"  ✓ Scraped: {article['title'][:50]}... ({article['word_count']} words)")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Failed to crawl {url}: {e}")
    
    return articles


def store_articles_as_signals(articles):
    print(f"\n💾 Storing {len(articles)} articles as external signals...")
    
    for article in articles:
        signal_data = {
            "source": "your_blog",
            "source_id": article['url'],
            "author": "CEO",
            "content": f"{article['title']}\n\n{article['content']}",
            "url": article['url'],
            "tags": ["article", "blog", "cold_start"],
            "analyzed": False,
            "metrics": {"word_count": article['word_count']}
        }
        
        try:
            supabase.table("external_signals").upsert(signal_data).execute()
            print(f"  ✓ Stored: {article['title'][:60]}...")
        except Exception as e:
            print(f"  ✗ Failed: {e}")


def analyze_articles_batch(articles):
    print(f"\n🧠 Analyzing articles for learnings...")
    
    combined_content = "\n\n---\n\n".join([
        f"Title: {a['title']}\n{a['content'][:2000]}"
        for a in articles[:10]
    ])
    
    agents = {
        "strategist_lead": "Extract strategic themes, positioning, and narrative patterns",
        "creator_lead": "Extract content structure, writing techniques, and style patterns",
        "analyst_lead": "Extract what makes content effective and observable success patterns"
    }
    
    all_learnings = {}
    
    for agent_id, focus in agents.items():
        print(f"\n  Generating learnings for {agent_id}...")
        
        prompt = f"""Analyze these articles from the CEO's blog.

        Sample articles:
        {combined_content[:4000]}

        Your focus: {focus}

        Generate 5-8 high-quality learnings.

        Return JSON:
        {{
        "learnings": [
            {{
            "type": "pattern" | "insight" | "preference" | "strategy",
            "statement": "specific learning",
            "confidence": 0.7-0.9,
            "tags": ["relevant", "tags"],
            "evidence": "brief reference"
            }}
        ]
        }}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            learnings_data = json.loads(response.choices[0].message.content)
            all_learnings[agent_id] = learnings_data.get("learnings", [])
            print(f"    ✓ Generated {len(all_learnings[agent_id])} learnings")
            
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            all_learnings[agent_id] = []
    
    return all_learnings


def insert_learnings(agent_learnings):
    print(f"\n💾 Inserting learnings into database...")
    
    total = 0
    
    for agent_id, learnings in agent_learnings.items():
        for learning in learnings:
            learning_data = {
                "agent_id": agent_id,
                "type": learning["type"],
                "statement": learning["statement"],
                "confidence": learning["confidence"],
                "tags": learning.get("tags", []),
                "evidence_refs": [{
                    "source": "website_articles",
                    "content": learning.get("evidence", "")
                }],
                "ceo_boosted": True,
            }
            
            try:
                supabase.table("learnings").insert(learning_data).execute()
                total += 1
            except Exception as e:
                print(f"    ✗ Failed: {e}")
    
    print(f"  ✓ Inserted {total} learnings from articles")


def main():
    print("🚀 Website Ingestion: saiyashwanth.com/articles\n")
    print("=" * 60)
    
    articles = crawl_articles(START_URL, max_articles=50)
    
    if not articles:
        print("\n❌ No articles found!")
        return
    
    print(f"\n✓ Scraped {len(articles)} articles")
    print(f"  Total words: {sum(a['word_count'] for a in articles):,}")
    
    store_articles_as_signals(articles)
    
    agent_learnings = analyze_articles_batch(articles)
    
    insert_learnings(agent_learnings)
    
    print("\n" + "=" * 60)
    print("✅ Website Ingestion Complete!")
    print(f"\nYour agents now have:")
    print(f"  • {len(articles)} articles as reference")
    print(f"  • {sum(len(l) for l in agent_learnings.values())} new learnings")
    print("\nThey understand your writing across multiple pieces! 🎉")


if __name__ == "__main__":
    main()
