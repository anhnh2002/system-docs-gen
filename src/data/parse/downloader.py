# Copyright (c) Meta Platforms, Inc. and affiliates
import yaml
import os
import logging
from github import Github
from pathlib import Path
import git
from typing import Dict, Any, List
import time
from datetime import datetime
from tqdm import tqdm
import json

class GitHubRepoDownloader:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.token = self.config.get('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in config file")
        self.gh = Github(self.token)
        self.setup_logging()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            if 'search_criteria' not in config:
                config['search_criteria'] = {}
            return config
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file: {e}")
            raise
        except FileNotFoundError:
            logging.error(f"Config file not found: {config_path}")
            raise

    def setup_logging(self):
        log_filename = f"github_downloader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )

    def build_query(self) -> str:
        """Build GitHub search query from config."""
        criteria = self.config.get('search_criteria', {})
        query_parts = []
        
        # Handle owners/users
        if owners := criteria.get('owners'):
            if isinstance(owners, list):
                query_parts.extend(f"user:{owner}" for owner in owners)
            else:
                query_parts.append(f"user:{owners}")
        
        # Handle dates - ensure proper date format and use created: qualifier
        dates = criteria.get('dates', {})
        if created_after := dates.get('created_after'):
            # GitHub's search API requires YYYY-MM-DD format
            if isinstance(created_after, datetime):
                created_after = created_after.strftime('%Y-%m-%d')
            query_parts.append(f"created:>{created_after}")
        
        if created_before := dates.get('created_before'):
            if isinstance(created_before, datetime):
                created_before = created_before.strftime('%Y-%m-%d')
            query_parts.append(f"created:<{created_before}")
        
        # Handle language
        if language := criteria.get('language'):
            if isinstance(language, list):
                query_parts.append(f"language:{language[0]}")  # GitHub API limitation: one language at a time
            else:
                query_parts.append(f"language:{language}")
        
        # Handle stars
        if stars := criteria.get('stars'):
            if isinstance(stars, dict):
                if min_stars := stars.get('min'):
                    query_parts.append(f"stars:>{min_stars}")
                if max_stars := stars.get('max'):
                    query_parts.append(f"stars:<{max_stars}")
            else:
                query_parts.append(f"stars:>{stars}")
        
        # Handle forks
        if forks := criteria.get('forks'):
            if isinstance(forks, dict):
                if min_forks := forks.get('min'):
                    query_parts.append(f"forks:>{min_forks}")
                if max_forks := forks.get('max'):
                    query_parts.append(f"forks:<{max_forks}")
            else:
                query_parts.append(f"forks:>{forks}")
        
        # Handle size
        if size := criteria.get('size'):
            if isinstance(size, dict):
                if min_size := size.get('min'):
                    query_parts.append(f"size:>{min_size}")
                if max_size := size.get('max'):
                    query_parts.append(f"size:<{max_size}")
            else:
                query_parts.append(f"size:>{size}")
        
        # Handle license
        if license_type := criteria.get('license'):
            if isinstance(license_type, list):
                query_parts.append(f"license:{license_type[0]}")  # GitHub API limitation: one license at a time
            else:
                query_parts.append(f"license:{license_type}")
        
        query = ' '.join(query_parts) if query_parts else "is:public"
        logging.info(f"Search query: {query}")
        return query

    def clone_repository(self, repo, output_dir: Path) -> bool:
        """Clone a repository using GitPython."""
        repo_dir = output_dir / repo.full_name
        if repo_dir.exists():
            logging.info(f"Repository directory already exists: {repo_dir}")
            return False
        
        try:
            # Create clone URL with token
            clone_url = f"https://{self.token}@github.com/{repo.full_name}.git"
            
            # Clone the repository
            git.Repo.clone_from(clone_url, str(repo_dir))
            
            # Save repository metadata
            metadata = {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'language': repo.language,
                'license': repo.license.name if repo.license else None,
                'created_at': repo.created_at.isoformat() if repo.created_at else None,
                'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                'topics': repo.get_topics(),
                'size': repo.size,
                'clone_time': datetime.now().isoformat(),
            }
            
            with open(repo_dir / 'repo_metadata.yaml', 'w') as f:
                yaml.dump(metadata, f)
            
            logging.info(f"Successfully cloned: {repo.full_name}")
            return True
        except Exception as e:
            logging.error(f"Error cloning repository {repo.full_name}: {e}")
            return False

    def run(self):
        output_dir = Path(self.config.get('output_directory', 'downloaded_repos'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load existing metadata file
        meta_file = output_dir / 'repositories_metadata.json'
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                all_metadata = json.load(f)
        else:
            all_metadata = {
                'download_session': datetime.now().isoformat(),
                'search_query': self.build_query(),
                'repositories': {}
            }
        
        max_repos = self.config.get('max_repos', 5)
        skip_archived = self.config.get('skip_archived', True)
        skip_forks = self.config.get('skip_forks', True)
        min_python_percentage = self.config.get('min_python_percentage', 80)  # Default to 80% if not specified
        
        # Get date filters from config
        dates = self.config.get('search_criteria', {}).get('dates', {})
        created_after = dates.get('created_after')
        if isinstance(created_after, str):
            created_after = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
        
        created_before = dates.get('created_before')
        if isinstance(created_before, str):
            created_before = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
        
        query = self.build_query()
        logging.info(f"Starting repository search with query: {query}")
        
        try:
            repos = self.gh.search_repositories(
                query=query,
                sort=self.config.get('search_criteria', {}).get('sort', 'stars'),
                order=self.config.get('search_criteria', {}).get('order', 'desc')
            )
            
            total_count = repos.totalCount
            logging.info(f"Found {total_count} repositories matching the search criteria")
            
            downloaded = 0
            pbar = tqdm(total=max_repos, desc="Downloading repositories")
            
            for repo in repos:
                if downloaded >= max_repos:
                    break
                
                if skip_archived and repo.archived:
                    logging.info(f"Skipping archived repository: {repo.full_name}")
                    continue
                
                if skip_forks and repo.fork:
                    logging.info(f"Skipping forked repository: {repo.full_name}")
                    continue
                
                # Check Python language percentage
                try:
                    languages = repo.get_languages()
                    total_bytes = sum(languages.values())
                    python_bytes = languages.get('Python', 0)
                    
                    if total_bytes > 0:
                        python_percentage = (python_bytes / total_bytes) * 100
                        if python_percentage < min_python_percentage:
                            logging.info(f"Skipping repository {repo.full_name}: Python code is only {python_percentage:.2f}% (required: {min_python_percentage}%)")
                            continue
                        logging.info(f"Repository {repo.full_name} has {python_percentage:.2f}% Python code")
                    elif min_python_percentage > 0:
                        logging.info(f"Skipping repository {repo.full_name}: No language data available")
                        continue
                except Exception as e:
                    logging.warning(f"Couldn't check language stats for {repo.full_name}: {e}")
                    # Continue even if we can't check language stats, to avoid missing potentially valid repositories
                
                if self.clone_repository(repo, output_dir):
                    # Add repository metadata to the collective metadata
                    metadata = {
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'description': repo.description,
                        'stars': repo.stargazers_count,
                        'forks': repo.forks_count,
                        'language': repo.language,
                        'license': repo.license.name if repo.license else None,
                        'created_at': repo.created_at.isoformat() if repo.created_at else None,
                        'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                        'topics': repo.get_topics(),
                        'size': repo.size,
                        'clone_time': datetime.now().isoformat(),
                        'local_path': str(output_dir / repo.full_name)
                    }
                    all_metadata['repositories'][repo.full_name] = metadata
                    
                    # Update the metadata file after each successful download
                    with open(meta_file, 'w') as f:
                        json.dump(all_metadata, f, indent=2)
                    
                    downloaded += 1
                    pbar.update(1)
                
                # Respect GitHub API rate limits
                time.sleep(1)
            
            pbar.close()
            logging.info(f"Successfully downloaded {downloaded} repositories")
            logging.info(f"Metadata file created at: {meta_file}")
        
        except Exception as e:
            logging.error(f"Error during repository download process: {e}")
            raise

if __name__ == "__main__":
    try:
        downloader = GitHubRepoDownloader("config/download_repo_config.yaml")
        downloader.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise