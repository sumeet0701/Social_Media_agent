import os, sys
import json
import requests
import time
from datetime import datetime, timedelta
import pandas as pd
import tweepy
from newspaper import Article
from utils.logger import logger
from utils.exception import SocialMediaAgentException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CompanyDataCollector:
    """
    Module to collect company information from various sources
    """
    def __init__(self, company_name, company_description):
        logger.info(f"{'='*20} Company Data Collector started {'='*20}")
        self.company_name = company_name
        self.company_description = company_description
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.company_data = {
            "basic_info": {
                "name": company_name,
                "description": company_description,
                "timestamp": datetime.now().isoformat()
            },
            "news": [],
            "website_content": {},
            "industry_keywords": [],
            "competitors": []
        }
        logger.info(f"Initialized CompanyDataCollector for {company_name}")
    
    def fetch_google_search_results(self, num_results=10):
        """Get company information from Google Custom Search API"""
        logger.info(f"{'='*20} Fetching Google search results started {'='*20}")
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': os.getenv("GOOGLE_CSE_ID"),  # Custom Search Engine ID
                'q': f"{self.company_name} company information",
                'num': num_results
            }
            
            response = requests.get(url, params=params)
            logger.info(f"{'='*20} Google search results fetched successfully  {'='*20}")
            if response.status_code == 200:
                search_results = response.json()
                
                # Extract information from search results
                logger.info(f"{'='*20} Extracting information from search results {'='*20}")
                if 'items' in search_results:
                    self.company_data["search_results"] = []
                    
                    # Extract official website URL if found
                    for item in search_results['items']:
                        if item.get('displayLink', '').lower() in self.company_name.lower() or self.company_name.lower() in item.get('displayLink', '').lower():
                            self.company_data["basic_info"]["official_website"] = item.get('link')
                        
                        # Store search result for further processing
                        self.company_data["search_results"].append({
                            "title": item.get('title', ''),
                            "link": item.get('link', ''),
                            "snippet": item.get('snippet', '')
                        })
                    
                    logger.info(f"Fetched {len(self.company_data['search_results'])} Google search results")
                    return True
            
            logger.info(f"Failed to fetch Google search results: {response.status_code}")
            return False
        except Exception as e:
            raise SocialMediaAgentException(e, sys) from e
    
    def fetch_news_articles(self, days_back=30):
        """Fetch recent news articles about the company"""
        logger.info(f"{'='*20} Fetching news articles started {'='*20}")
        try:
            today = datetime.now()
            from_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            url = f"https://newsapi.org/v2/everything"
            params = {
                'apiKey': self.news_api_key,
                'q': self.company_name,
                'from': from_date,
                'sortBy': 'relevancy',
                'language': 'en'
            }
            logger.info(f"{'='*20} Fetching news articles from News API {'='*20}")
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'ok':
                    articles = data.get('articles', [])
                    for article in articles[:20]:  # Limit to 20 most relevant articles
                        self.company_data["news"].append({
                            "title": article.get('title', ''),
                            "source": article.get('source', {}).get('name', ''),
                            "url": article.get('url', ''),
                            "publishedAt": article.get('publishedAt', ''),
                            "content": article.get('content', ''),
                            "description": article.get('description', '')
                        })
                    
                    logger.info(f"Fetched {len(self.company_data['news'])} news articles")
                    return True
            
            logger.info(f"Failed to fetch news articles: {response.status_code}")
            return False
        except Exception as e:
            raise SocialMediaAgentException(e, sys) from e
    
    def scrape_company_website(self):
        """Scrape content from the company's official website"""
        logger.info(f"{'='*20} Scraping company website started {'='*20}")
        try:
            if not self.company_data["basic_info"].get("official_website"):
                logger.info("No official website URL found")
                return False
                
            website_url = self.company_data["basic_info"]["official_website"]
            
            article = Article(website_url)
            article.download()
            article.parse()
            
            # Extract main page content
            self.company_data["website_content"]["main"] = {
                "title": article.title,
                "text": article.text,
                "top_image": article.top_image
            }
            
            # Try to scrape about page
            about_urls = [
                f"{website_url.rstrip('/')}/about",
                f"{website_url.rstrip('/')}/about-us",
                f"{website_url.rstrip('/')}/company",
                f"{website_url.rstrip('/')}/our-company"
            ]
            logger.info(f"{'='*20} Fetching about page started {'='*20}")
            for about_url in about_urls:
                try:
                    about_article = Article(about_url)
                    about_article.download()
                    about_article.parse()
                    logger.info(f"{'='*20} About page fetched successfully {'='*20}")
                    if len(about_article.text) > 100:  # Ensure we got meaningful content
                        self.company_data["website_content"]["about"] = {
                            "title": about_article.title,
                            "text": about_article.text
                        }
                        break
                except:
                    continue
            
            # Try to scrape products/services page
            logger.info(f"{'='*20} Fetching products/services page started {'='*20}")
            product_urls = [
                f"{website_url.rstrip('/')}/products",
                f"{website_url.rstrip('/')}/services",
                f"{website_url.rstrip('/')}/brands"
            ]
            logger.info(f"{'='*20} Fetching products/services page started {'='*20}")
            for product_url in product_urls:
                try:
                    product_article = Article(product_url)
                    product_article.download()
                    product_article.parse()
                    
                    if len(product_article.text) > 100:
                        self.company_data["website_content"]["products"] = {
                            "title": product_article.title,
                            "text": product_article.text
                        }
                        break
                except:
                    continue
            
            logger.info(f"Scraped company website with {len(self.company_data['website_content'])} sections")
            return True
        except Exception as e:
            raise SocialMediaAgentException(e, sys) from e
    
    def extract_industry_keywords(self):
        """Extract industry-related keywords from collected data"""
        try:
            logger.info(f"{'='*20} Extracting industry-related keywords started {'='*20}")
            all_text = []
            
            # Add website content
            for section in self.company_data["website_content"].values():
                if isinstance(section, dict) and "text" in section:
                    all_text.append(section["text"])
            
            # Add news content - Filter out None values
            for article in self.company_data["news"]:
                content = article.get("content", "")
                description = article.get("description", "")
                if content:  # Only add non-None content
                    all_text.append(content)
                if description:  # Only add non-None description
                    all_text.append(description)
            
            # Simple keyword extraction based on frequency
            # Filter out None values and convert to string
            all_text = [str(text) for text in all_text if text is not None]
            combined_text = " ".join(all_text).lower()
            
            words = combined_text.split()
            word_freq = {}
            
            stopwords = ["the", "and", "or", "in", "on", "at", "to", "a", "an", "of", "for", "with", "by"]
            for word in words:
                if word not in stopwords and len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
            self.company_data["industry_keywords"] = [keyword for keyword, freq in top_keywords]
            
            logger.info(f"Extracted {len(self.company_data['industry_keywords'])} industry keywords")
            return True
        except Exception as e:
            raise SocialMediaAgentException(e, sys) from e
    
    def find_competitors(self):
        """Find potential competitors based on collected data"""
        try:
            # In a real implementation, you would use more sophisticated methods
            # This is a simplified approach
            
            # Search for competitors
            logger.info(f"{'='*20} Finding competitors started {'='*20}")
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': os.getenv("GOOGLE_CSE_ID"),
                'q': f"{self.company_name} competitors in {self.company_data['industry_keywords'][:3]}",
                'num': 10
            }
            logger.info(f"{'='*20} Finding competitors started {'='*20}")
            response = requests.get(url, params=params)
            competitors = []
            
            if response.status_code == 200:
                search_results = response.json()
                
                if 'items' in search_results:
                    for item in search_results['items']:
                        # Extract company names from search results
                        # This is a simplified approach
                        snippet = item.get('snippet', '')
                        title = item.get('title', '')
                        
                        # Look for phrases like "X and its competitors including Y, Z..."
                        if "competitors" in snippet.lower() or "competitors" in title.lower():
                            competitors.append({
                                "source": item.get('link', ''),
                                "title": title,
                                "snippet": snippet
                            })
            logger.info(f"{'='*20} Finding competitors started {'='*20}")
            self.company_data["competitors"] = competitors
            logger.info(f"Found {len(competitors)} competitor references")
            return True
        except Exception as e:
            raise SocialMediaAgentException(e, sys) from e
    
    def collect_all_company_data(self):
        """Collect all company data from various sources"""
        logger.info(f"{'='*20} Collecting all company data started {'='*20}")
        results = {
            "google_search": self.fetch_google_search_results(),
            "news": self.fetch_news_articles(),
            "website": self.scrape_company_website(),
            "keywords": self.extract_industry_keywords(),
            "competitors": self.find_competitors()
        }
        logger.info(f"{'='*20} Collecting all company data started {'='*20}")
        # Save data to file
        output_dir = "data/companies"
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"{'='*20} Collecting all company data started {'='*20}")  
        filename = f"{output_dir}/{self.company_name.replace(' ', '_').lower()}_data.json"
        with open(filename, 'w') as f:
            json.dump(self.company_data, f, indent=2)
        
        logger.info(f"Saved company data to {filename}")
        return {
            "status": results,
            "company_data": self.company_data,
            "file_path": filename
        }


class SocialMediaExtractor:
    """
    Module to extract social media data from company profiles
    """
    def __init__(self, company_name):
        self.company_name = company_name
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        self.bluesky_handle = os.getenv("BLUESKY_HANDLE")
        self.bluesky_password = os.getenv("BLUESKY_PASSWORD")
        
        self.social_data = {
            "twitter": [],
            "bluesky": [],
            "mastodon": [],
            "threads": [],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Initialized SocialMediaExtractor for {company_name}")
    
    def extract_twitter_data(self, username, count=200):
        """Extract data from Twitter for the given username"""
        try:
            auth = tweepy.OAuth1UserHandler(
                self.twitter_api_key, 
                self.twitter_api_secret,
                self.twitter_access_token, 
                self.twitter_access_secret
            )
            api = tweepy.API(auth)
            
            # Get user profile info
            user = api.get_user(screen_name=username)
            self.social_data["twitter_profile"] = {
                "username": username,
                "name": user.name,
                "description": user.description,
                "followers_count": user.followers_count,
                "friends_count": user.friends_count,
                "statuses_count": user.statuses_count,
                "profile_image_url": user.profile_image_url_https
            }
            
            # Get user tweets
            tweets = api.user_timeline(screen_name=username, count=count, tweet_mode="extended")
            
            for tweet in tweets:
                tweet_data = {
                    "id": tweet.id_str,
                    "created_at": tweet.created_at.isoformat(),
                    "text": tweet.full_text,
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count,
                    "hashtags": [hashtag['text'] for hashtag in tweet.entities.get('hashtags', [])],
                    "mentions": [mention['screen_name'] for mention in tweet.entities.get('user_mentions', [])],
                    "is_retweet": hasattr(tweet, 'retweeted_status'),
                    "media": []
                }
                
                # Extract media if available
                if 'media' in tweet.entities:
                    for media in tweet.entities['media']:
                        tweet_data["media"].append({
                            "type": media.get('type', ''),
                            "url": media.get('media_url_https', '')
                        })
                
                # Get some replies if possible
                try:
                    replies = tweepy.Cursor(
                        api.search_tweets,
                        q=f"to:{username}",
                        since_id=tweet.id_str
                    ).items(10)
                    
                    tweet_replies = []
                    for reply in replies:
                        if reply.in_reply_to_status_id_str == tweet.id_str:
                            tweet_replies.append({
                                "id": reply.id_str,
                                "text": reply.text,
                                "user": reply.user.screen_name,
                                "created_at": reply.created_at.isoformat()
                            })
                    
                    tweet_data["replies"] = tweet_replies
                except Exception as e:
                    logger.info(f"Error fetching replies: {str(e)}")
                    tweet_data["replies"] = []
                
                self.social_data["twitter"].append(tweet_data)
            
            logger.info(f"Extracted {len(self.social_data['twitter'])} tweets from Twitter for {username}")
            return True
        except Exception as e:
            logger.info.error(f"Error extracting Twitter data: {str(e)}")
            return False
    
    def extract_bluesky_data(self, handle):
        """Extract data from Bluesky for the given handle"""
        # This is a placeholder as Bluesky API access is still evolving
        # In a real implementation, you would use the atproto library
        try:
            # Placeholder implementation
            logger.info(f"Bluesky extraction for {handle} is not fully implemented yet")
            
            # Adding dummy data for demonstration
            self.social_data["bluesky"] = [
                {
                    "id": f"dummy-{i}",
                    "text": f"Sample Bluesky post {i} for {self.company_name}",
                    "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
                    "likes": 5 + i,
                    "replies": 1 + (i % 3)
                } for i in range(10)
            ]
            
            return True
        except Exception as e:
            logger.info.error(f"Error extracting Bluesky data: {str(e)}")
            return False
    
    def extract_mastodon_data(self, handle, instance="mastodon.social"):
        """Extract data from Mastodon for the given handle"""
        # Placeholder for Mastodon implementation
        # In a real implementation, you would use the Mastodon.py library
        try:
            logger.info(f"Mastodon extraction for {handle}@{instance} is not fully implemented yet")
            
            # Adding dummy data for demonstration
            self.social_data["mastodon"] = [
                {
                    "id": f"mast-{i}",
                    "text": f"Sample Mastodon post {i} for {self.company_name}",
                    "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
                    "favourites": 4 + i,
                    "reblogs": 1 + (i % 4),
                    "replies": 2 + (i % 3)
                } for i in range(10)
            ]
            
            return True
        except Exception as e:
            logger.info.error(f"Error extracting Mastodon data: {str(e)}")
            return False
    
    def extract_threads_data(self, username):
        """Extract data from Threads (via Facebook Graph API or scraping) for the given username"""
        # This is a placeholder as Threads doesn't have an official public API yet
        # In a real implementation, you might need to use web scraping
        try:
            logger.info(f"Threads extraction for {username} is not fully implemented yet")
            
            # Adding dummy data for demonstration
            self.social_data["threads"] = [
                {
                    "id": f"thread-{i}",
                    "text": f"Sample Threads post {i} for {self.company_name}",
                    "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
                    "likes": 10 + i*2,
                    "replies": 3 + (i % 5)
                } for i in range(10)
            ]
            
            return True
        except Exception as e:
            logger.info.error(f"Error extracting Threads data: {str(e)}")
            return False
    
    def collect_all_social_data(self, twitter_handle=None, bluesky_handle=None, 
                               mastodon_handle=None, threads_handle=None):
        """Collect all social media data for the company"""
        results = {
            "twitter": False,
            "bluesky": False,
            "mastodon": False,
            "threads": False
        }
        
        if twitter_handle:
            results["twitter"] = self.extract_twitter_data(twitter_handle)
            
        if bluesky_handle:
            results["bluesky"] = self.extract_bluesky_data(bluesky_handle)
            
        if mastodon_handle:
            parts = mastodon_handle.split('@')
            if len(parts) > 2:
                username = parts[1]
                instance = parts[2]
                results["mastodon"] = self.extract_mastodon_data(username, instance)
            else:
                results["mastodon"] = self.extract_mastodon_data(mastodon_handle)
            
        if threads_handle:
            results["threads"] = self.extract_threads_data(threads_handle)
        
        # Save data to file
        output_dir = "data/social"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{output_dir}/{self.company_name.replace(' ', '_').lower()}_social_data.json"
        with open(filename, 'w') as f:
            json.dump(self.social_data, f, indent=2)
        
        logger.info(f"Saved social media data to {filename}")
        
        return {
            "status": results,
            "social_data": self.social_data,
            "file_path": filename
        }


class DataCollectionOrchestrator:
    """
    Orchestrates the entire data collection process
    """
    def __init__(self, company_name, company_description):
        logger.info(f"{'='*20} Data Collection Orchestrator started {'='*20}")
        self.company_name = company_name
        self.company_description = company_description
        logger.info(f"Initializing data collection for {company_name}")
    
    def collect_all_data(self, social_handles=None):
        """
        Collect all data for the company, including company information and social media
        
        Args:
            social_handles (dict): Dictionary with social media handles
                                 Format: {'twitter': 'handle', 'bluesky': 'handle', etc.}
        """
        logger.info(f"{'='*20} Collecting all data started {'='*20}")
        start_time = time.time()
        
        # Step 1: Collect company information
        company_collector = CompanyDataCollector(self.company_name, self.company_description)
        company_result = company_collector.collect_all_company_data()
        logger.info(f"{'='*20} Collecting all data started {'='*20}")
        # Step 2: Collect social media data
        # social_collector = SocialMediaExtractor(self.company_name)
        logger.info(f"{'='*20} Collecting all data started {'='*20}")
        if not social_handles:
            social_handles = {}
            
        # social_result = social_collector.collect_all_social_data(
        #     twitter_handle=social_handles.get('twitter'),
        #     bluesky_handle=social_handles.get('bluesky'),
        #     mastodon_handle=social_handles.get('mastodon'),
        #     threads_handle=social_handles.get('threads')
        # )
        logger.info(f"{'='*20} Collecting all data started {'='*20}")
        end_time = time.time()
        duration = end_time - start_time
        
        # Create final results
        results = {
            "company_name": self.company_name,
            "collection_timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "company_data_status": company_result["status"],
            # "social_data_status": social_result["status"],
            "company_data_path": company_result["file_path"],
            # "social_data_path": social_result["file_path"]
        }
        
        # Save summary to file
        logger.info(f"{'='*20} Collecting all data started {'='*20}")
        output_dir = "data/summaries"
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"{'='*20} Collecting all data started {'='*20}")
        filename = f"{output_dir}/{self.company_name.replace(' ', '_').lower()}_collection_summary.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Data collection completed in {duration:.2f} seconds")
        logger.info(f"Summary saved to {filename}")
        
        return results


# E