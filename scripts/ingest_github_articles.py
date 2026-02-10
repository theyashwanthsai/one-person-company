import os
import requests
import frontmatter
from supabase import create_client
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GITHUB_REPO = "theyashwanthsai/DigitalGarden"
CONTENT_PATH = "public/content"
GITHUB_API_BASE = "https://api.github.com"
RAW_CONTENT_BASE = "https://raw.githubusercontent.com"


def get_files_from_github(repo, path):
    """Recursively get all markdown files from GitHub repo"""
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
    
    print(f"📂 Fetching: {path}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        items = response.json()
        
        files = []
        
        for item in items:
            if item['type'] == 'file' and item['name'].endswith('.md'):
                files.append({
                    'name': item['name'],
                    'path': item['path'],
                    'download_url': item['download_url']
                })
                print(f"  ✓ Found: {item['name']}")
            
            elif item['type'] == 'dir':
                print(f"  📁 Exploring subdirectory: {item['name']}")
                sub_files = get_files_from_github(repo, item['path'])
                files.extend(sub_files)
        
        return files
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []


def download_and_parse_markdown(file_info):
    """Download markdown file and parse frontmatter + content"""
    try:
        response = requests.get(file_info['download_url'])
        response.raise_for_status()
        
        # Parse frontmatter
        post = frontmatter.loads(response.text)
        
        # Extract metadata
        title = post.get('title', file_info['name'].replace('.md', ''))
        date = post.get('date', post.get('created', ''))
        tags = post.get('tags', [])
        
        # Get content
        content = post.content.strip()
        word_count = len(content.split())
        
        # Build public URL (assuming your site mirrors the repo structure)
        public_url = f"https://saiyashwanth.com/{file_info['path'].replace('public/content/', '').replace('.md', '')}"
        
        return {
            'title': title,
            'content': content,
            'url': public_url,
            'github_path': file_info['path'],
            'word_count': word_count,
            'date': date,
            'tags': tags if isinstance(tags, list) else []
        }
    
    except Exception as e:
        print(f"    ✗ Failed to parse {file_info['name']}: {e}")
        return None


def fetch_all_articles():
    """Fetch all articles from GitHub"""
    print("🚀 Fetching articles from GitHub\n")
    print(f"   Repo: {GITHUB_REPO}")
    print(f"   Path: {CONTENT_PATH}\n")
    print("=" * 60)
    
    # Get all markdown files
    files = get_files_from_github(GITHUB_REPO, CONTENT_PATH)
    
    if not files:
        print("\n❌ No markdown files found!")
        return []
    
    print(f"\n{'=' * 60}")
    print(f"✓ Found {len(files)} markdown files\n")
    print("📝 Downloading and parsing...\n")
    
    articles = []
    
    for file_info in files:
        article = download_and_parse_markdown(file_info)
        
        if article and article['word_count'] > 50:  # Skip very short files
            articles.append(article)
            print(f"  ✓ {len(articles)}. {article['title'][:60]}... ({article['word_count']} words)")
        else:
            print(f"  ✗ Skipped: {file_info['name']} (too short or failed)")
    
    return articles


def store_articles_as_signals(articles):
    """Store articles in external_signals table"""
    print(f"\n💾 Storing {len(articles)} articles as external signals...")
    
    stored = 0
    
    for article in articles:
        signal_data = {
            "source": "github_blog",
            "source_id": article['github_path'],
            "author": "CEO",
            "content": f"{article['title']}\n\n{article['content']}",
            "url": article['url'],
            "tags": ["article", "blog", "github", "cold_start"] + article.get('tags', []),
            "analyzed": False,
            "metrics": {
                "word_count": article['word_count'],
                "date": article.get('date', '')
            }
        }
        
        try:
            # Insert new signal (skip if already exists)
            result = supabase.table("external_signals").insert(signal_data).execute()
            stored += 1
            print(f"  ✓ {stored}/{len(articles)}: {article['title'][:60]}...")
        
        except Exception as e:
            # Skip duplicates silently
            if 'duplicate key' in str(e).lower() or '23505' in str(e):
                stored += 1
                print(f"  ↻ {stored}/{len(articles)}: {article['title'][:60]}... (already exists)")
            else:
                print(f"  ✗ Failed: {e}")
    
    print(f"\n✓ Successfully stored {stored} articles")


def analyze_articles_batch(articles):
    """Generate learnings from articles using LLM"""
    print(f"\n🧠 Analyzing articles for learnings...")
    
    # Take a representative sample (up to 10 articles)
    sample = articles[:10]
    
    combined_content = "\n\n---\n\n".join([
        f"Title: {a['title']}\nTags: {', '.join(a.get('tags', []))}\n{a['content'][:2000]}"
        for a in sample
    ])
    
    agents = {
        "strategist_lead": "Extract strategic themes, positioning, and narrative patterns from the CEO's writing",
        "creator_lead": "Extract content structure, writing techniques, hooks, and style patterns",
        "analyst_lead": "Extract what makes content effective, topic patterns, and observable success factors"
    }
    
    all_learnings = {}
    
    for agent_id, focus in agents.items():
        print(f"\n  🤖 Generating learnings for {agent_id}...")
        
        prompt = f"""Analyze these articles from the CEO's blog (GitHub: {GITHUB_REPO}).

Sample articles ({len(sample)} of {len(articles)} total):
{combined_content[:4000]}

Your focus: {focus}

Generate 5-8 high-quality learnings that will help this agent understand the CEO's:
- Writing style and voice
- Preferred topics and themes
- Content patterns and structures
- Strategic positioning

Return JSON:
{{
  "learnings": [
    {{
      "type": "pattern" | "insight" | "preference" | "strategy",
      "statement": "specific, actionable learning",
      "confidence": 0.7-0.9,
      "tags": ["relevant", "tags"],
      "evidence": "brief reference to article or pattern"
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
    """Insert learnings into database"""
    print(f"\n💾 Inserting learnings into database...")
    
    total = 0
    
    for agent_id, learnings in agent_learnings.items():
        for learning in learnings:
            learning_data = {
                "agent_id": agent_id,
                "type": learning["type"],
                "statement": learning["statement"],
                "confidence": learning["confidence"],
                "tags": learning.get("tags", []) + ["github", "cold_start"],
                "evidence_refs": [{
                    "source": "github_blog",
                    "repo": GITHUB_REPO,
                    "content": learning.get("evidence", "")
                }],
                "ceo_boosted": True,
            }
            
            try:
                supabase.table("learnings").insert(learning_data).execute()
                total += 1
            except Exception as e:
                print(f"    ✗ Failed to insert learning: {e}")
    
    print(f"  ✓ Inserted {total} learnings from GitHub articles")


def main():
    print("🚀 GitHub Article Ingestion")
    print(f"   Source: https://github.com/{GITHUB_REPO}")
    print(f"   Path: {CONTENT_PATH}\n")
    print("=" * 60)
    
    # Step 1: Fetch articles
    articles = fetch_all_articles()
    
    if not articles:
        print("\n❌ No articles found!")
        return
    
    print(f"\n{'=' * 60}")
    print(f"✓ Processed {len(articles)} articles")
    print(f"  Total words: {sum(a['word_count'] for a in articles):,}")
    
    # Step 2: Store as external signals
    store_articles_as_signals(articles)
    
    # Step 3: Generate learnings
    agent_learnings = analyze_articles_batch(articles)
    
    # Step 4: Insert learnings
    insert_learnings(agent_learnings)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ GitHub Article Ingestion Complete!")
    print(f"\nYour agents now have:")
    print(f"  • {len(articles)} articles as reference")
    print(f"  • {sum(len(l) for l in agent_learnings.values())} new learnings")
    print(f"  • {sum(a['word_count'] for a in articles):,} total words of context")
    print("\nThey understand your writing from your entire blog! 🎉")


if __name__ == "__main__":
    main()

