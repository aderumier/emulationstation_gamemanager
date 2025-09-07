#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameManager - Game Collection Management System
Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Global Download Manager for HTTPX HTTP/2 Image Downloads

This module provides a singleton download manager that maintains a persistent
HTTPX HTTP/2 client for efficient image downloads across multiple tasks.
"""

import httpx
import asyncio
import threading
import queue
import time
from typing import List, Dict, Any, Optional


class DownloadManager:
    """Global download manager with persistent HTTPX HTTP/2 client"""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.lock = threading.Lock()
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        self.consumer_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # HTTPX configuration
        self.limits = httpx.Limits(
            max_connections=20,
            max_keepalive_connections=20,
            keepalive_expiry=30.0
        )
        
        self.timeout = httpx.Timeout(
            timeout=60.0,
            connect=10.0,
            read=30.0
        )
        
        self.headers = {
            'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'accept-language': 'fr,en;q=0.9',
            'cache-control': 'no-cache',
            'dnt': '1',
            'pragma': 'no-cache',
            'priority': 'i',
            'referer': 'https://gamesdb.launchbox-app.com/',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        }
        
        self.cookies = None
        
    def start(self, cookies: Optional[Dict] = None):
        """Start the download manager with optional cookies"""
        with self.lock:
            if self.is_running:
                return
                
            self.cookies = cookies
            self.shutdown_event.clear()
            self.consumer_thread = threading.Thread(target=self._consumer_thread, daemon=True)
            self.consumer_thread.start()
            self.is_running = True
            
    def stop(self):
        """Stop the download manager and cancel all active downloads"""
        with self.lock:
            if not self.is_running:
                return
                
            print("🛑 Stopping download manager and cancelling active downloads...")
            self.shutdown_event.set()
            
            # Flush the download queue - remove all pending tasks
            queue_size = 0
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                    queue_size += 1
                except queue.Empty:
                    break
            
            if queue_size > 0:
                print(f"🛑 Flushed {queue_size} pending download tasks from queue")
            
            # Cancel all active download tasks
            if hasattr(self, 'active_tasks') and self.active_tasks:
                print(f"🛑 Cancelling {len(self.active_tasks)} active download tasks...")
                for task in list(self.active_tasks):
                    if not task.done():
                        task.cancel()
                self.active_tasks.clear()
            
            # Close the HTTPX client if it exists
            if hasattr(self, 'client') and self.client:
                try:
                    import asyncio
                    # Schedule client close in the event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.client.aclose())
                    else:
                        loop.run_until_complete(self.client.aclose())
                    print("🛑 HTTPX client closed")
                except Exception as e:
                    print(f"⚠️  Warning: Could not close HTTPX client: {e}")
            
            if self.consumer_thread:
                self.consumer_thread.join(timeout=5)  # Reduced timeout for faster shutdown
                if self.consumer_thread.is_alive():
                    print("⚠️  Warning: Consumer thread did not stop gracefully")
            
            self.is_running = False
            print("🛑 Download manager stopped")
            
    def add_task(self, task: Dict[str, Any]):
        """Add a download task to the queue"""
        self.task_queue.put(task)
        
    def wait_for_completion(self, expected_count: int) -> List[Dict[str, Any]]:
        """Wait for all downloads to complete and return results"""
        results = []
        for _ in range(expected_count):
            try:
                # Check if we should stop (shutdown event is set)
                if self.shutdown_event.is_set():
                    print(f"🛑 Download manager stopped - returning {len(results)} completed downloads")
                    break
                
                # Check if the task has been stopped
                if self.check_task_status():
                    print(f"🛑 Task stopped by user - stopping download manager")
                    self.shutdown_event.set()
                    break
                    
                result = self.result_queue.get(timeout=1)  # Check every second for stop requests
                if 'error' in result:
                    print(f"❌ Download error: {result['error']}")
                else:
                    results.append(result)
            except queue.Empty:
                # Check if we should stop during timeout
                if self.shutdown_event.is_set():
                    print(f"🛑 Download manager stopped - returning {len(results)} completed downloads")
                    break
                
                # Check if the task has been stopped during timeout
                if self.check_task_status():
                    print(f"🛑 Task stopped by user - stopping download manager")
                    self.shutdown_event.set()
                    break
                    
                continue  # Continue waiting, don't break on timeout
        return results
    
    def check_task_status(self):
        """Check if the current task has been stopped (imports app module to check)"""
        try:
            # Cache the import to avoid repeated imports
            if not hasattr(self, '_is_task_stopped_func'):
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from app import is_task_stopped
                self._is_task_stopped_func = is_task_stopped
            return self._is_task_stopped_func()
        except ImportError:
            # If we can't import the app module, assume task is running
            return False
        
    def _consumer_thread(self):
        """Consumer thread that processes download queue with HTTPX and 20 parallel downloads"""
        import asyncio
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def process_download_queue():
            """Process download queue with 20 parallel downloads using HTTPX with HTTP/2"""
            
            try:
                # Create HTTPX AsyncClient with HTTP/2 support and persistent connections
                async with httpx.AsyncClient(
                    limits=self.limits,
                    timeout=self.timeout,
                    headers=self.headers,
                    cookies=self.cookies,
                    http2=True,  # Enable HTTP/2 support
                    follow_redirects=True
                ) as client:
                    
                    self.client = client
                    
                    async def download_single_image_async(task):
                        """Download a single image with HTTPX"""
                        # Import here to avoid circular imports
                        import sys
                        import os
                        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                        from app import download_launchbox_image_httpx
                        
                        gamelist_field = task['gamelist_field']
                        download_url = task['download_url']
                        local_path = task['local_path']
                        media_type = task['media_type']
                        region = task['region']
                        filename = task['filename']
                        game_name = task.get('game_name', 'Unknown')
                        game_prefix = f"[{game_name}]"
                        
                        # Check if task has been stopped before starting download
                        if self.check_task_status():
                            print(f"{game_prefix} 🛑 Task stopped - skipping {gamelist_field} download")
                            return {
                                'success': False,
                                'gamelist_field': gamelist_field,
                                'local_path': local_path,
                                'message': 'Task stopped by user',
                                'download_time': 0
                            }
                        
                        # Start timing for this specific image download
                        image_start_time = time.time()
                        
                        print(f"{game_prefix} Downloading {gamelist_field} ('{region}')")
                        
                        # Download the image using HTTPX client
                        success, message = await download_launchbox_image_httpx(
                            download_url, local_path, media_type=media_type, 
                            client=client, game_name=game_name
                        )
                        
                        # Calculate total time for this image
                        image_total_time = time.time() - image_start_time
                        
                        if success:
                            print(f"{game_prefix} ✅ Success: {gamelist_field} → {task['local_filename']}")
                        else:
                            print(f"{game_prefix} ❌ Failed: {message}")
                        
                        return {
                            'success': success,
                            'gamelist_field': gamelist_field,
                            'local_path': f'./media/{task["media_directory"]}/{task["local_filename"]}',
                            'message': message,
                            'download_time': image_total_time
                        }
                    
                    print(f"🔧 Consumer thread started with HTTPX HTTP/2 client (20 parallel connections)")
                    
                    # Track active downloads and results
                    active_tasks = set()
                    results = []
                    
                    while True:
                        # Check for shutdown signal - be more aggressive about stopping
                        if self.shutdown_event.is_set():
                            print("🛑 Shutdown event set - cancelling all active downloads and clearing queue")
                            # Cancel all active tasks
                            for task in list(active_tasks):
                                if not task.done():
                                    task.cancel()
                            active_tasks.clear()
                            # Clear the task queue
                            queue_cleared = 0
                            while not self.task_queue.empty():
                                try:
                                    self.task_queue.get_nowait()
                                    queue_cleared += 1
                                except queue.Empty:
                                    break
                            if queue_cleared > 0:
                                print(f"🛑 Cleared {queue_cleared} pending tasks from queue")
                            break
                        
                        # Check if task has been stopped by user
                        if self.check_task_status():
                            print("🛑 Task stopped by user - cancelling all active downloads")
                            # Cancel all active tasks
                            for task in list(active_tasks):
                                if not task.done():
                                    task.cancel()
                            active_tasks.clear()
                            # Clear the task queue
                            while not self.task_queue.empty():
                                try:
                                    self.task_queue.get_nowait()
                                except queue.Empty:
                                    break
                            break
                        
                        # Start new downloads up to 20 parallel
                        while len(active_tasks) < 20 and not self.task_queue.empty():
                            try:
                                task = self.task_queue.get_nowait()
                                # Create and schedule the download task
                                download_task = asyncio.create_task(download_single_image_async(task))
                                active_tasks.add(download_task)
                            except queue.Empty:
                                break
                        
                        # Process completed downloads
                        if active_tasks:
                            # Wait for at least one download to complete
                            done, pending = await asyncio.wait(
                                active_tasks, 
                                return_when=asyncio.FIRST_COMPLETED,
                                timeout=0.1
                            )
                            
                            # Remove completed tasks from active set
                            active_tasks -= done
                            
                            # Process results from completed downloads
                            for task in done:
                                try:
                                    result = task.result()
                                    results.append(result)
                                    self.result_queue.put(result)
                                except Exception as e:
                                    error_result = {'error': str(e)}
                                    results.append(error_result)
                                    self.result_queue.put(error_result)
                        else:
                            # No active downloads, small delay to prevent busy waiting
                            await asyncio.sleep(0.1)
                    
                    print(f"🔗 All downloads completed, HTTPX HTTP/2 client connections maintained for potential reuse")
                    
            except Exception as e:
                print(f"❌ Error in download consumer thread: {e}")
                self.result_queue.put({'error': str(e)})
            finally:
                # Keep the event loop running for potential reuse
                print(f"🔄 Consumer thread completed, connections remain available")
        
        try:
            # Run the async download queue processor in this thread's event loop
            loop.run_until_complete(process_download_queue())
        except Exception as e:
            print(f"❌ Error in download consumer thread: {e}")
            self.result_queue.put({'error': str(e)})
        finally:
            # Keep the event loop running for potential reuse
            print(f"🔄 Consumer thread completed, connections remain available")

# Global instance
_download_manager = None
_manager_lock = threading.Lock()

def get_download_manager() -> DownloadManager:
    """Get the global download manager instance"""
    global _download_manager
    
    with _manager_lock:
        if _download_manager is None:
            _download_manager = DownloadManager()
            _download_manager.start()
        return _download_manager

def stop_download_manager():
    """Stop the global download manager"""
    global _download_manager
    
    with _manager_lock:
        if _download_manager:
            _download_manager.stop()
            _download_manager = None
