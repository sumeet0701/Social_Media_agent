from src.agents.Data_collection_agent import DataCollectionOrchestrator
import json

if __name__ == "__main__":
    # Example company
    company_name = "HDFC Bank"
    company_description = "Leading Bank in India"
    
    # Social media handles
    social_handles = {
        "twitter": "HUL_News",
        "bluesky": "hindustanunilever.bsky.social",
        "mastodon": "@hindustanunilever@mastodon.social",
        "threads": "hindustanunilever"
    }
    
    # Run data collection
    orchestrator = DataCollectionOrchestrator(company_name, company_description)
    results = orchestrator.collect_all_data(social_handles)
    
    print(json.dumps(results, indent=2))



