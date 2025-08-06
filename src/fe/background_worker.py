#!/usr/bin/env python3
"""
Background worker for processing documentation generation jobs.
"""

import os
import time
import threading
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Dict

from main import DocumentationGenerator, Config
from .models import JobStatus
from .cache_manager import CacheManager
from .github_processor import GitHubRepoProcessor
from .config import WebAppConfig


class BackgroundWorker:
    """Background worker for processing documentation generation jobs."""
    
    def __init__(self, cache_manager: CacheManager, temp_dir: str = None):
        self.cache_manager = cache_manager
        self.temp_dir = temp_dir or WebAppConfig.TEMP_DIR
        self.running = False
        self.processing_queue = Queue(maxsize=WebAppConfig.QUEUE_SIZE)
        self.job_status: Dict[str, JobStatus] = {}
    
    def start(self):
        """Start the background worker thread."""
        if not self.running:
            self.running = True
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
            print("Background worker started")
    
    def stop(self):
        """Stop the background worker."""
        self.running = False
    
    def add_job(self, job_id: str, job: JobStatus):
        """Add a job to the processing queue."""
        self.job_status[job_id] = job
        self.processing_queue.put(job_id)
    
    def get_job_status(self, job_id: str) -> JobStatus:
        """Get job status by ID."""
        return self.job_status.get(job_id)
    
    def get_all_jobs(self) -> Dict[str, JobStatus]:
        """Get all job statuses."""
        return self.job_status
    
    def _worker_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                if not self.processing_queue.empty():
                    job_id = self.processing_queue.get(timeout=1)
                    self._process_job(job_id)
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"Worker error: {e}")
                time.sleep(1)
    
    def _process_job(self, job_id: str):
        """Process a single documentation generation job."""
        if job_id not in self.job_status:
            return
        
        job = self.job_status[job_id]
        
        try:
            # Update job status
            job.status = 'processing'
            job.started_at = datetime.now()
            job.progress = "Starting repository clone..."
            
            # Check cache first
            cached_docs = self.cache_manager.get_cached_docs(job.repo_url)
            if cached_docs and Path(cached_docs).exists():
                job.status = 'completed'
                job.completed_at = datetime.now()
                job.docs_path = cached_docs
                job.progress = "Documentation retrieved from cache"
                print(f"Job {job_id}: Using cached documentation")
                return
            
            # Clone repository
            repo_info = GitHubRepoProcessor.get_repo_info(job.repo_url)
            # Use repo full name for temp directory (already URL-safe since job_id is URL-safe)
            temp_repo_dir = os.path.join(self.temp_dir, job_id)
            
            job.progress = f"Cloning repository {repo_info['full_name']}..."
            
            if not GitHubRepoProcessor.clone_repository(repo_info['clone_url'], temp_repo_dir):
                raise Exception("Failed to clone repository")
            
            # Generate documentation
            job.progress = "Analyzing repository structure..."
            
            # Create config for documentation generation
            config = Config(
                repo_path=temp_repo_dir,
                output_dir="output",
                dependency_graph_dir=os.path.join("output", "dependency_graphs"),
                docs_dir=os.path.join("output", "docs", f"{job_id}-docs")
            )
            
            job.progress = "Generating documentation..."
            
            # Generate documentation
            doc_generator = DocumentationGenerator(config)
            
            # Run the async documentation generation in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(doc_generator.run())
            finally:
                loop.close()
            
            # Cache the results
            docs_path = os.path.abspath(config.docs_dir)
            self.cache_manager.add_to_cache(job.repo_url, docs_path)
            
            # Update job status
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.docs_path = docs_path
            job.progress = "Documentation generation completed"
            
            print(f"Job {job_id}: Documentation generated successfully")
            
        except Exception as e:
            # Update job status with error
            job.status = 'failed'
            job.completed_at = datetime.now()
            job.error_message = str(e)
            job.progress = f"Failed: {str(e)}"
            
            print(f"Job {job_id}: Failed with error: {e}")
        
        finally:
            # Cleanup temporary repository
            if 'temp_repo_dir' in locals() and os.path.exists(temp_repo_dir):
                try:
                    subprocess.run(['rm', '-rf', temp_repo_dir], check=True)
                except Exception as e:
                    print(f"Failed to cleanup temp directory: {e}")