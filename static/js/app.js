/**
 * GameManager - Game Collection Management System
 * Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

class GameCollectionManager {
    constructor() {
        this.games = [];
        this.currentSystem = null;
        this.gridApi = null;
        this.editingGamePath = null; // Store ROM path instead of index
        this.modifiedGames = new Set();
        this.mediaPreviewEnabled = false;
        this.showingMediaPreview = false; // Flag to prevent multiple simultaneous media preview calls
        this.currentMediaPreviewGame = null; // Track current game shown in media preview
        this.uploadInProgress = false; // Track if upload is in progress
        this.selectedGames = [];
        this.selectedMedia = []; // Track selected media for deletion (array for multiple selection)
        this.selectedThumbnails = []; // Track selected thumbnails for deletion
        this.thumbnailViewEnabled = false; // Track thumbnail view state
        this.lazyLoadingObserver = null; // Track lazy loading observer
        this.mediaFieldsCache = null; // Cache for media fields from config
        this.pendingBestMatchResults = null;
        this.currentBestMatchIndex = 0;
        this.duplicatesFilterActive = false; // Track duplicates filter state
        this.hiddenFilterActive = false; // Track hidden filter state
        this.currentNavigationIndex = 0; // Track current navigation position
        this.eventSource = null;
        this.logHistory = [];
        this.lastProcessedGame = null;
        this.lastClickedColumn = null; // Track which column was last clicked for double-click behavior
        this.screenscraperSearchInProgress = false; // Track ScreenScraper search progress
        
        // Task refresh debouncing
        this.isRefreshingTasks = false; // Flag to prevent overlapping refresh calls
        this.taskRefreshTimeout = null; // Timeout for debounced refresh
        this.refreshCallCount = 0; // Track actual API calls made
        this.refreshSkipCount = 0; // Track calls that were skipped due to debouncing
        
        // Initialize clear image cache button visibility (Media Preview is default active tab)
        setTimeout(() => {
            const clearCacheContainer = document.getElementById('clearImageCacheContainer');
            if (clearCacheContainer) {
                clearCacheContainer.classList.remove('d-none');
            }
        }, 100);
        
        // YouTube operations
        this.currentYouTubeGame = null; // Store current game for YouTube operations
        this.suppressYouTubeSearchReopen = false; // Prevent reopening search modal during downloads
        
        // Throttling variables for performance
        this.pendingLogUpdates = [];
        this.logUpdateTimer = null;
        this.logUpdateThrottle = 100; // Update log every 100ms max
        
        // Modal state management
        this.isModalOpen = false;
        this.modalEventListenersAdded = false; // Prevent duplicate modal event listeners
        
        // Task grid management
        this.taskGridApi = null;
        this.currentTaskData = new Map(); // Store current task data for change detection
        
        // Game grid management
        this.currentGameData = new Map(); // Store current game data for change detection
        
        // State persistence control
        this.stateSavingEnabled = false; // Control when state saving is allowed
        
        // Live log streaming
        this.currentLogStream = null;
        
        // Grid refresh tracking for completed tasks
        this.processedGridRefreshTasks = new Set();
        
        // Systems configuration cache
        this.systemsConfigCache = {
            platforms: null,
            screenscraperSystems: null,
            igdbPlatforms: null,
            mobygamesSystems: null,
            lastUpdated: null,
            cacheTimeout: 5 * 60 * 1000 // 5 minutes
        };
        
        // Task panel resizing
        this.taskPanelResizing = false;
        this.taskPanelStartHeight = 0;
        this.taskPanelStartY = 0;
        
        // WebSocket for real-time updates
        this.socket = null;
        
        // Media mappings cache
        this.mediaMappingsCache = null;
        this.select2Instance = null; // Select2 instance
        
        this.initializeEventListeners();
        this.loadState();
        
        // Initialize Select2 immediately to apply styling
        this.initializeSelect2();
        
        this.checkExistingTask();
        
        // Initialize media mappings cache (don't await to avoid blocking constructor)
        this.initializeMediaMappingsCache();

        // Initialize task grid
        this.initializeTaskGrid();
        
        // Start auto-refresh for tasks since panel is always visible
        this.startTaskAutoRefresh();
        
        // Initialize Bootstrap tabs for the combined panel
        this.initializeTabs();
        
        // Initialize edit modal delete button
        this.initializeEditModalDeleteButton();
        
        // Add event listener for edit modal cleanup when closed
        this.initializeEditModalCleanup();
        
        // Initialize search modal cleanup
        this.initializeSearchModalCleanup();
        
        // Initialize cache configuration modal
        this.initializeCacheConfigurationModal();
        
        // Initialize systems configuration modal
        this.initializeSystemsModal();
        
        // Initialize media fields configuration modal
        this.initializeMediaFieldsModal();
        
        // Initialize launchbox configuration modal
        this.initializeLaunchboxConfigModal();
        
        // Initialize IGDB configuration modal
        this.initializeIgdbConfigModal();
        
        // Initialize ScreenScraper configuration modal
        this.initializeScreenscraperConfigModal();
        
        // Initialize MobyGames configuration modal
        this.initializeMobygamesConfigModal();
        
        // Initialize DAT Scrapper configuration modal
        this.initializeDatscrapperConfigModal();
        
        // Initialize SteamGridDB configuration modal
        this.initializeSteamgriddbConfigModal();
        
        // Initialize Steam configuration modal
        this.initializeSteamConfigModal();
        
        // Initialize system scraper configuration modal
        this.initializeSystemScraperConfigModal();
        
        // Initialize application configuration modal
        this.initializeAppConfigurationModal();
        
        // Initialize video configuration modal
        this.initializeVideoConfigurationModal();
        
        // Initialize change password modal
        this.initializeChangePasswordModal();
        
        // Initialize image context menu
        this.initializeImageContextMenu();
        
        // Initialize WebSocket connection after everything else is ready
        setTimeout(() => {
            this.initializeWebSocket();
        }, 100);
        
        // Clean up any stale room memberships on page load
        this.cleanupStaleRooms();

    }

    cleanupStaleRooms() {
        // Clean up any stale room memberships from previous sessions
        // This helps prevent cross-system contamination
        if (this.socket && this.currentSystem) {
            // The WebSocket will handle the actual cleanup when it connects
        }
    }

    initializeTabs() {
        // Initialize Bootstrap tabs for the combined panel
        try {
            
            // Get the tab elements
            const mediaPreviewTab = document.getElementById('media-preview-tab');
            const taskManagementTab = document.getElementById('task-management-tab');
            const mediaPreviewContent = document.getElementById('media-preview-content');
            const taskManagementContent = document.getElementById('task-management-content');

            if (mediaPreviewTab && taskManagementTab && mediaPreviewContent && taskManagementContent) {
                // Add click event listeners for manual tab switching
                mediaPreviewTab.addEventListener('click', () => {
                    this.switchTab('media-preview');
                });
                
                taskManagementTab.addEventListener('click', () => {
                    this.switchTab('task-management');
                });
                
                // Add Bootstrap tab event listeners for when tabs are shown
                mediaPreviewContent.addEventListener('shown.bs.tab', () => {
                    // Always refresh media preview for currently selected game
                    if (this.gridApi) {
                        const selectedRows = this.gridApi.getSelectedRows();
                        if (selectedRows.length > 0) {
                            this.showMediaPreview(selectedRows[0]);
                        } else {
                            this.hideMediaPreview();
                        }
                    }
                });
                
                taskManagementContent.addEventListener('shown.bs.tab', () => {
                    // Clear media preview content when switching to task management to free memory
                    const mediaPreviewContent = document.getElementById('mediaPreviewContent');
                    if (mediaPreviewContent) {
                        mediaPreviewContent.innerHTML = '';
                    }
                });
                
                // Set initial tab state
                this.switchTab('media-preview');
                
            } else {

            }
        } catch (error) {
        }
    }
    
    switchTab(tabName) {
        // Remove active class from all tabs and content
        const tabs = document.querySelectorAll('#combinedPanelTabs .nav-link');
        const contents = document.querySelectorAll('.tab-pane');
        
        tabs.forEach(tab => tab.classList.remove('active'));
        contents.forEach(content => content.classList.remove('show', 'active'));
        
        // Add active class to selected tab and content
        if (tabName === 'media-preview') {
            document.getElementById('media-preview-tab').classList.add('active');
            document.getElementById('media-preview-content').classList.add('show', 'active');
            
            // Show media preview action buttons for media preview tab
            const mediaPreviewActionsContainer = document.getElementById('mediaPreviewActionsContainer');
            if (mediaPreviewActionsContainer) {
                mediaPreviewActionsContainer.classList.remove('d-none');
            }
            
            // Always refresh media preview for currently selected game
            if (this.gridApi) {
                const selectedRows = this.gridApi.getSelectedRows();
                if (selectedRows.length > 0) {
                    this.showMediaPreview(selectedRows[0]);
                } else {
                    this.hideMediaPreview();
                }
            }
        } else if (tabName === 'task-management') {
            document.getElementById('task-management-tab').classList.add('active');
            document.getElementById('task-management-content').classList.add('show', 'active');
            
            // Hide media preview action buttons for task management tab
            const mediaPreviewActionsContainer = document.getElementById('mediaPreviewActionsContainer');
            if (mediaPreviewActionsContainer) {
                mediaPreviewActionsContainer.classList.add('d-none');
            }
            
            // Clear media preview content when switching to task management to free memory
            const mediaPreviewContent = document.getElementById('mediaPreviewContent');
            if (mediaPreviewContent) {
                mediaPreviewContent.innerHTML = '';
            }
            
        }
    }

    isMediaPreviewTabActive() {
        const mediaPreviewTab = document.getElementById('media-preview-tab');
        const mediaPreviewContent = document.getElementById('media-preview-content');
        
        return mediaPreviewTab && mediaPreviewContent && 
               mediaPreviewTab.classList.contains('active') && 
               mediaPreviewContent.classList.contains('show') && 
               mediaPreviewContent.classList.contains('active');
    }

    async checkTaskQueue() {
        // Check the current task queue status
        try {
            const response = await fetch('/api/task/queue', {
                credentials: 'same-origin',
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for queue data
                }
            });
            if (response.ok) {
                const queueStatus = await response.json();
                return queueStatus;
            }
        } catch (error) {
        }
        return null;
    }

    async getAllTasks() {
        // Get all tasks from the API
        try {
            const response = await fetch('/api/tasks', {
                credentials: 'same-origin',
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for task data
                }
            });
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Error getting all tasks:', error);
        }
        return {};
    }

    async showTaskQueueStatus() {
        // Display the current task queue status
        const queueStatus = await this.checkTaskQueue();
        if (queueStatus) {
            if (queueStatus.queue_length > 0) {
                const queuedTasks = queueStatus.queued_tasks.map(task => 
                    `${task.type} (${new Date(task.timestamp * 1000).toLocaleTimeString()})`
                ).join(', ');
                
                this.showToast(`⏳ ${queueStatus.queue_length} task(s) queued: ${queuedTasks}`, 'warning');
            } else if (queueStatus.current_task.status === 'running') {
                this.showToast(`🔄 Current task: ${queueStatus.current_task.type}`, 'info');
            } else {
                this.showToast('✅ No tasks running or queued', 'success');
            }
        }
    }

    async refreshTasks() {
        // Prevent overlapping calls - if a refresh is already in progress, skip this call
        if (this.isRefreshingTasks) {
            this.refreshSkipCount++;
            console.log(`Task refresh already in progress, skipping this call (skipped: ${this.refreshSkipCount})`);
            return;
        }
        
        this.isRefreshingTasks = true;
        this.refreshCallCount++;
        console.log(`Starting task refresh... (call #${this.refreshCallCount})`);
        
        try {
            // Use the combined endpoint to get both tasks and queue status in one call
            const response = await fetch('/api/task/status-and-queue', {
                redirect: 'manual', // Don't follow redirects automatically
                credentials: 'same-origin', // Include cookies for authentication
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for polling requests
                }
            });
            
            // Check if we're being redirected to login (authentication required)
            if (response.type === 'opaqueredirect' || response.status === 0 || 
                (response.redirected && response.url.includes('/login'))) {
                this.stopTaskAutoRefresh();
                return;
            }
            
            if (response.ok) {
                const data = await response.json();
                let tasks = data.all_tasks || {}; // Get all tasks from the combined response
                
                // Get queued tasks from the combined response and add them to the task grid
                if (data.queue && data.queue.queued_tasks) {
                    data.queue.queued_tasks.forEach(queuedTask => {
                        // Create a task object for queued tasks
                        const queuedTaskObj = {
                            id: queuedTask.task_id,
                            type: queuedTask.type,
                            status: 'queued',
                            start_time: queuedTask.timestamp,
                            progress_percentage: 0,
                            current_step: 0,
                            total_steps: 0,
                            username: 'Unknown',
                            data: queuedTask.data || {}
                        };
                        tasks[queuedTask.task_id] = queuedTaskObj;
                    });
                }
                
                // Reconstruct missing fields from log history after restart (only once)
                if (!this.historyLoaded) {
                    try {
                        const needsHistory = Object.values(tasks).some(t => !t?.data?.system_name || (!t.total_steps && !t.progress_percentage));
                        if (needsHistory) {
                            const histResp = await fetch('/api/tasks/history', {
                                credentials: 'same-origin',
                                headers: {
                                    'Accept-Encoding': 'gzip, deflate' // Enable compression for history data
                                }
                            });
                            if (histResp.ok) {
                                const history = await histResp.json();
                                for (const [tid, h] of Object.entries(history)) {
                                    if (!tasks[tid]) {
                                        tasks[tid] = h;
                                    } else {
                                        const t = tasks[tid];
                                        t.data = t.data || {};
                                        if (!t.data.system_name && h.data && h.data.system_name) t.data.system_name = h.data.system_name;
                                        if (!t.total_steps && h.total_steps) t.total_steps = h.total_steps;
                                        if (!t.current_step && h.current_step) t.current_step = h.current_step;
                                        if (!t.progress_percentage && h.progress_percentage) t.progress_percentage = h.progress_percentage;
                                        if ((!t.stats || Object.keys(t.stats).length === 0) && h.stats) t.stats = h.stats;
                                    }
                                }
                            }
                        }
                        this.historyLoaded = true; // Mark as loaded to avoid future calls
                    } catch (e) {
                        this.historyLoaded = true; // Mark as loaded even on error to avoid retries
                    }
                }
                this.displayTasksInGrid(tasks);
                // Check for completed tasks that need grid refresh
                this.checkForGridRefresh(tasks);
            } else if (response.status === 401) {
                this.stopTaskAutoRefresh();
            } else {
            }
        } catch (error) {
            console.error('Error refreshing tasks:', error);
        } finally {
            // Always reset the flag, even if there was an error
            this.isRefreshingTasks = false;
            console.log(`Task refresh completed (calls: ${this.refreshCallCount}, skipped: ${this.refreshSkipCount})`);
        }
    }

    async checkForGridRefresh(tasks) {
        // Check for newly completed tasks that need grid refresh
        for (const [taskId, task] of Object.entries(tasks)) {
            // Skip if we've already processed this task for grid refresh
            if (this.processedGridRefreshTasks.has(taskId)) {
                continue;
            }
            
            // Check if this is a completed task that needs grid refresh
            if (task.status === 'completed' && task.grid_refresh_needed && task.data && task.data.system_name) {
                
                // Only refresh if the user is currently viewing the same system
                if (this.currentSystem === task.data.system_name) {
                    
                    // Mark this task as processed
                    this.processedGridRefreshTasks.add(taskId);
                    
                    // Refresh the grid for this system
                    await this.loadRomSystem(task.data.system_name);
                    
                    // No need for additional refresh since loadRomSystem now uses efficient updates
                    // Acknowledge refresh so future sessions don't re-trigger
                    try {
                        await fetch(`/api/tasks/${taskId}/ack-refresh`, { method: 'POST' });
                    } catch (e) {
                    }
                } else {
                    
                    // Mark this task as processed to avoid checking it again
                    this.processedGridRefreshTasks.add(taskId);
                    // Still clear the flag so it doesn't spam when reopening
                    try {
                        await fetch(`/api/tasks/${taskId}/ack-refresh`, { method: 'POST' });
                    } catch (e) {
                    }
                }
            }
        }
    }

    displayTasksInGrid(tasks) {
        if (!this.taskGridApi) {
            this.initializeTaskGrid();
        }

        // Convert tasks to grid data format
        const gridData = Object.values(tasks).map(task => {
            // Extract total games from task data for progress calculation
            let totalGames = 0;
            if (task.data && task.data.system_name) {
                // For image download, scraping, and YouTube download tasks, get total games from total_steps
                if (task.type === 'image_download' || task.type === 'scraping' || task.type === 'youtube_download_batch') {
                    // This will be updated when the task actually runs
                    totalGames = task.total_steps || 0;
                }
            }
            
            return {
                id: task.id,
                type: this.getTaskDisplayName(task.type),
                status: task.status,
                startTime: task.start_time ? new Date(task.start_time * 1000).toLocaleString() : 'N/A',
                duration: task.duration ? `${task.duration.toFixed(1)}s` : 'N/A',
                progress: task.progress_percentage || 0,
                currentStep: task.current_step || 0,
                totalSteps: task.total_steps || totalGames,
                username: task.username || 'Unknown',
                system: (task.data && task.data.system_name) ? task.data.system_name : '',
                data: task
            };
        });

        // Sort tasks: running first, then queued, then by start time (newest first)
        gridData.sort((a, b) => {
            if (a.status === 'running' && b.status !== 'running') return -1;
            if (a.status !== 'running' && b.status === 'running') return 1;
            if (a.status === 'queued' && b.status !== 'queued' && b.status !== 'running') return -1;
            if (a.status !== 'queued' && b.status === 'queued' && a.status !== 'running') return 1;
            return (b.data.start_time || 0) - (a.data.start_time || 0);
        });

        // Check if this is the first load or if we need to add/remove rows
        const currentRowCount = this.taskGridApi.getDisplayedRowCount();
        const newRowCount = gridData.length;
        
        // If row count changed significantly or it's the first load, use setGridOption
        if (currentRowCount === 0 || Math.abs(currentRowCount - newRowCount) > 2) {
            this.taskGridApi.setGridOption('rowData', gridData);
            // Update our stored data
            this.currentTaskData.clear();
            gridData.forEach(row => {
                this.currentTaskData.set(row.id, row);
            });
        } else {
            // Use refreshCells for efficient updates
            this.updateTaskGridData(gridData);
        }
    }

    updateTaskGridData(newGridData) {
        // Efficiently update task grid using refreshCells instead of setGridOption
        const newDataMap = new Map();
        newGridData.forEach(row => {
            newDataMap.set(row.id, row);
        });

        // Find rows that need to be added, updated, or removed
        const rowsToAdd = [];
        const rowsToUpdate = [];
        const rowsToRemove = [];

        // Check for new rows and updates
        newDataMap.forEach((newRow, id) => {
            const currentRow = this.currentTaskData.get(id);
            if (!currentRow) {
                rowsToAdd.push(newRow);
            } else if (this.hasTaskDataChanged(currentRow, newRow)) {
                rowsToUpdate.push(newRow);
            }
        });

        // Check for removed rows
        this.currentTaskData.forEach((currentRow, id) => {
            if (!newDataMap.has(id)) {
                rowsToRemove.push(id);
            }
        });

        // Handle row additions and removals
        if (rowsToAdd.length > 0 || rowsToRemove.length > 0) {
            // If we have structural changes, fall back to setGridOption
            this.taskGridApi.setGridOption('rowData', newGridData);
            this.currentTaskData = newDataMap;
            return;
        }

        // Update existing rows with changed data
        if (rowsToUpdate.length > 0) {
            rowsToUpdate.forEach(updatedRow => {
                // Find the row node and update its data
                this.taskGridApi.forEachNode(node => {
                    if (node.data && node.data.id === updatedRow.id) {
                        node.setData(updatedRow);
                    }
                });
                // Update our stored data
                this.currentTaskData.set(updatedRow.id, updatedRow);
            });

            // Refresh cells to reflect the changes
            this.taskGridApi.refreshCells({
                force: true // Force refresh to ensure all changes are visible
            });
        }
    }

    hasTaskDataChanged(oldRow, newRow) {
        // Compare key fields that might change during task execution
        return (
            oldRow.status !== newRow.status ||
            oldRow.progress !== newRow.progress ||
            oldRow.currentStep !== newRow.currentStep ||
            oldRow.duration !== newRow.duration ||
            oldRow.data.current_step !== newRow.data.current_step ||
            oldRow.data.progress_percentage !== newRow.data.progress_percentage ||
            oldRow.data.status !== newRow.data.status
        );
    }

    async updateGameGridData(newGames) {
        // Efficiently update game grid using refreshCells instead of setGridOption
        if (!this.gridApi || newGames === null || newGames === undefined) return;

        // Debug: Check for hidden games in the input
        const hiddenGames = newGames.filter(game => game.hidden === 'true');
        if (hiddenGames.length > 0) {
        }
        
        // Filter out hidden games by default (unless hidden filter is active)
        let filteredGames = newGames;
        if (!this.hiddenFilterActive) {
            const beforeCount = newGames.length;
            filteredGames = newGames.filter(game => {
                const isHidden = game.hidden === 'true';
                if (isHidden) {
                }
                return !isHidden;
            });
            const afterCount = filteredGames.length;
        } else {
        }
        
        // Deduplicate input by path to avoid duplicate node ids
        const newDataMap = new Map();
        filteredGames.forEach(game => {
            if (game && game.path) {
                newDataMap.set(game.path, game);
            }
        });
        const dedupedGames = Array.from(newDataMap.values());
        
        // Check if this is the first load or if we need to add/remove rows
        const currentRowCount = this.gridApi.getDisplayedRowCount();
        const newRowCount = dedupedGames.length;
        
        // If row count changed significantly, it's the first load, or we're clearing the grid, use setGridOption
        if (currentRowCount === 0 || Math.abs(currentRowCount - newRowCount) > 5 || newRowCount === 0) {
            this.gridApi.setGridOption('rowData', dedupedGames);
        // Update our stored data
        this.currentGameData.clear();
        dedupedGames.forEach(game => {
            this.currentGameData.set(game.path, game);
        });
        
        // Update the games counter to reflect displayed rows
        this.updateSelectionDisplay();
        
        // Setup lazy loading for thumbnail view if enabled
        if (this.thumbnailViewEnabled) {
            setTimeout(() => {
                this.setupLazyLoading();
            }, 100);
        }
        return;
        }
        
        // Find games that need to be added, updated, or removed
        const gamesToAdd = [];
        const gamesToUpdate = [];
        const gamesToRemove = [];
        
        // Check for new games and updates
        newDataMap.forEach((newGame, path) => {
            const currentGame = this.currentGameData.get(path);
            if (!currentGame) {
                gamesToAdd.push(newGame);
            } else if (this.hasGameDataChanged(currentGame, newGame)) {
                gamesToUpdate.push(newGame);
            }
        });
        
        // Check for removed games
        this.currentGameData.forEach((currentGame, path) => {
            if (!newDataMap.has(path)) {
                gamesToRemove.push(path);
            }
        });
        
        // Handle game additions and removals
        if (gamesToAdd.length > 0 || gamesToRemove.length > 0) {
            // If we have structural changes, fall back to setGridOption
            this.gridApi.setGridOption('rowData', dedupedGames);
            this.currentGameData = newDataMap;
            
            // Update the games counter to reflect displayed rows
            this.updateSelectionDisplay();
            return;
        }
        
        // Update existing games with changed data
        if (gamesToUpdate.length > 0) {
            gamesToUpdate.forEach(updatedGame => {
                // Find the row node and update its data
                this.gridApi.forEachNode(node => {
                    if (node.data && node.data.path === updatedGame.path) {
                        node.setData(updatedGame);
                    }
                });
                // Update our stored data
                this.currentGameData.set(updatedGame.path, updatedGame);
            });
            
            // Refresh cells to reflect the changes
            this.gridApi.refreshCells({
                force: true // Force refresh to ensure all changes are visible
            });
            
            // Update the games counter to reflect displayed rows
            this.updateSelectionDisplay();
        }
        
        // Setup lazy loading for thumbnail view if enabled
        if (this.thumbnailViewEnabled) {
            setTimeout(() => {
                this.setupLazyLoading();
            }, 100);
        }
    }

    hasGameDataChanged(oldGame, newGame) {
        // Compare key fields that might change during task execution
        return (
            oldGame.video !== newGame.video ||
            oldGame.image !== newGame.image ||
            oldGame.boxart !== newGame.boxart ||
            oldGame.screenshot !== newGame.screenshot ||
            oldGame.marquee !== newGame.marquee ||
            oldGame.fanart !== newGame.fanart ||
            oldGame.titleshot !== newGame.titleshot ||
            oldGame.cartridge !== newGame.cartridge ||
            oldGame.boxback !== newGame.boxback ||
            oldGame.extra1 !== newGame.extra1 ||
            oldGame.manual !== newGame.manual ||
            oldGame.wheel !== newGame.wheel ||
            oldGame.thumbnail !== newGame.thumbnail ||
            oldGame.desc !== newGame.desc ||
            oldGame.developer !== newGame.developer ||
            oldGame.publisher !== newGame.publisher ||
            oldGame.genre !== newGame.genre ||
            oldGame.rating !== newGame.rating ||
            oldGame.players !== newGame.players ||
            oldGame.igdbid !== newGame.igdbid ||
            oldGame.launchboxid !== newGame.launchboxid ||
            oldGame.mobygamesid !== newGame.mobygamesid ||
            oldGame.steamid !== newGame.steamid ||
            oldGame.screenscraperid !== newGame.screenscraperid ||
            oldGame.steamgridid !== newGame.steamgridid ||
            oldGame.youtubeurl !== newGame.youtubeurl ||
            oldGame.releasedate !== newGame.releasedate ||
            oldGame.name !== newGame.name
        );
    }
    initializeTaskGrid() {
        const taskGridElement = document.getElementById('taskGrid');
        if (!taskGridElement) return;

        // Define column definitions
        const columnDefs = [
            {
                headerName: 'User',
                field: 'username',
                width: 100,
                sortable: true,
                filter: true
            },
            {
                headerName: 'System',
                field: 'system',
                width: 120,
                sortable: true,
                filter: true
            },
            {
                headerName: 'Type',
                field: 'type',
                width: 150,
                sortable: true,
                filter: true
            },
            {
                headerName: 'Status',
                field: 'status',
                width: 120,
                sortable: true,
                filter: true,
                cellRenderer: (params) => {
                    const status = params.value;
                    const displayText = this.getTaskStatusText(status);
                    return `<span class="task-status-badge ${status}">${displayText}</span>`;
                }
            },
            {
                headerName: 'Started',
                field: 'startTime',
                width: 150,
                sortable: true
            },
            {
                headerName: 'Duration',
                field: 'duration',
                width: 100,
                sortable: true
            },
            {
                headerName: 'Progress',
                field: 'progress',
                width: 200,
                sortable: true,
                cellRenderer: (params) => {
                    const progress = params.value;
                    const currentStep = params.data.currentStep;
                    const totalSteps = params.data.totalSteps;
                    const status = params.data.status;
                    
                    // Special display for queued tasks
                    if (status === 'queued') {
                        return `
                            <div class="task-progress-bar queued">
                                <div class="task-progress-fill" style="width: 0%"></div>
                                <div class="task-progress-text">Queued</div>
                            </div>
                        `;
                    }

                    let progressText = `${progress}%`;
                    if (totalSteps > 0) {
                        progressText += ` (${currentStep}/${totalSteps} games)`;
                    } else if (progress > 0) {
                        progressText += ` (${currentStep} games)`;
                    }
                    
                    return `
                        <div class="task-progress-bar">
                            <div class="task-progress-fill" style="width: ${progress}%"></div>
                            <div class="task-progress-text">${progressText}</div>
                        </div>
                    `;
                }
            },
            {
                headerName: 'Actions',
                field: 'actions',
                width: 80,
                sortable: false,
                cellRenderer: (params) => {
                    const status = params.data.status;
                    const taskId = params.data.id;
                    const taskType = params.data.type;
                    let buttons = '';
                    
                    if (status === 'running') {
                        buttons = `<button class="btn btn-outline-warning btn-sm" onclick="window.gameManager.stopTask('${taskId}')">
                            <i class="bi bi-stop-circle"></i> Stop
                        </button>`;
                    } else if (status === 'queued') {
                        buttons = `<button class="btn btn-outline-danger btn-sm" onclick="window.gameManager.deleteTask('${taskId}')">
                            <i class="bi bi-trash"></i> Delete
                        </button>`;
                    } else if (status === 'waiting_confirmation' && taskType === 'rom_scan') {
                        buttons = `<button class="btn btn-outline-danger btn-sm" onclick="window.gameManager.stopTask('${taskId}')">
                            <i class="bi bi-x-circle"></i> Cancel
                        </button>`;
                    }
                    
                    return `<div class="task-actions-cell">${buttons}</div>`;
                }
            }
        ];

        // Grid options
        const gridOptions = {
            columnDefs: columnDefs,
            rowData: [],
            defaultColDef: {
                resizable: true,
                sortable: true
            },
            rowHeight: 35,
            headerHeight: 35,
            suppressRowClickSelection: true,
            suppressCellFocus: true,
            onRowDoubleClicked: (params) => {
                this.showTaskLog(params.data.id);
            },
            // State persistence
            onColumnMoved: () => {
                this.saveGridState();
            },
            onColumnResized: () => {
                this.saveGridState();
            },
            onSortChanged: () => {
                this.saveGridState();
            },
            onFilterChanged: () => {
                this.saveGridState();
            },
            onColumnVisible: () => {
                this.saveGridState();
            },
            onColumnPinned: () => {
                this.saveGridState();
            },
            // Additional events for better state capture
            onGridReady: () => {
                setTimeout(() => this.restoreGridState(), 500);
            }
        };

        // Create the grid
        this.taskGridApi = agGrid.createGrid(taskGridElement, gridOptions);
        
        // Set the height after grid creation
        const savedHeight = this.getCookie('taskPanelHeight');
        if (savedHeight) {
            const height = parseInt(savedHeight);
            if (height >= 160 && height <= 800) {
                taskGridElement.style.height = height + 'px';
            }
        } else {
            taskGridElement.style.height = '160px';
        }
        
        // Wait for grid to be ready before restoring state
        this.taskGridApi.addEventListener('gridReady', () => {
            this.restoreGridState();
        });
        
        // Also try to restore state after a short delay as fallback
        setTimeout(() => {
            if (this.taskGridApi && this.taskGridApi.isGridReady && this.taskGridApi.isGridReady()) {
                this.restoreGridState();
            } else {
            }
        }, 1000);
        
        // Additional fallback for task grid
        setTimeout(() => {
            this.restoreGridState();
        }, 2000);
        
        // Fallback: Enable state saving after a timeout even if restore fails
        setTimeout(() => {
            if (!this.stateSavingEnabled) {
                this.stateSavingEnabled = true;
            }
        }, 3000);
    }
    
    saveGridState() {
        if (!this.taskGridApi) {
            return;
        }
        
        if (!this.stateSavingEnabled) {
            return;
        }
        
        try {
            // Use proper AG Grid Column State API
            const columnState = this.taskGridApi.getColumnState();
            
            const state = {
                columnState: columnState,
                timestamp: Date.now()
            };
            
            const stateJson = JSON.stringify(state);
            this.setCookie('taskGridState', stateJson);

        } catch (error) {
        }
    }
    
        restoreGridState() {
        if (!this.taskGridApi) {
            return;
        }
        
        try {
            const savedState = this.getCookie('taskGridState');
            if (!savedState) {
            } else {
                const state = JSON.parse(savedState);
                
                // Restore column state using proper AG Grid API
                if (state.columnState && state.columnState.length > 0) {
                    const success = this.taskGridApi.applyColumnState({
                        state: state.columnState
                    });
                    
                    if (success) {
                    } else {
                    }
                }
            }
            
            // Always enable state saving after restoration attempt (whether successful or not)
            this.stateSavingEnabled = true;
            
        } catch (error) {
            // Even on error, enable state saving so the grid can work
            this.stateSavingEnabled = true;
        }
    }

    saveMainGridState() {
        if (!this.gridApi) {
            return;
        }
        
        if (!this.stateSavingEnabled) {
            return;
        }
        
        try {
            // Use proper AG Grid Column State API
            const columnState = this.gridApi.getColumnState();
            
            const state = {
                columnState: columnState,
                timestamp: Date.now()
            };
            
            const stateJson = JSON.stringify(state);
            this.setCookie('mainGridState', stateJson);

        } catch (error) {
        }
    }
    
        restoreMainGridState() {
        if (!this.gridApi) {
            return;
        }
        
        try {
            const savedState = this.getCookie('mainGridState');
            
            if (!savedState) {
            } else {
                const state = JSON.parse(savedState);
                
                // Restore column state using proper AG Grid API
                if (state.columnState && state.columnState.length > 0) {
                    const success = this.gridApi.applyColumnState({
                        state: state.columnState
                    });
                    
                    if (success) {
                    } else {
                    }
                }
            }
            
            // Always enable state saving after restoration attempt (whether successful or not)
            this.stateSavingEnabled = true;
            
        } catch (error) {
            // Even on error, enable state saving so the grid can work
            this.stateSavingEnabled = true;
        }
    }

    getTaskDisplayName(taskType) {
        const names = {
            'image_download': 'Image Download',
            'media_scan': 'Media Scan',
            'scraping': 'LaunchBox Scraping',
            'igdb_scraping': 'IGDB Scraping',
            'screenscraper_scraping': 'ScreenScraper Scraping'
        };
        return names[taskType] || taskType;
    }

    getTaskStatusText(status) {
        const statusTexts = {
            'idle': 'Idle',
            'running': 'Running',
            'completed': 'Completed',
            'error': 'Error',
            'queued': 'Queue',
            'stopped': 'Stopped'
        };
        return statusTexts[status] || status;
    }

    async showTaskLog(taskId) {
        try {
            // Fetch full task details from API (includes data and progress fields)
            const response = await fetch(`/api/tasks/${taskId}`);
            if (!response.ok) {
                console.error('Failed to fetch task details:', response.status);
                return;
            }
            
            const task = await response.json();
            if (!task) {
                console.error('Task not found:', taskId);
                return;
            }

            // If task is running, use streaming endpoint for live updates
            if (task.status === 'running') {
                this.displayTaskLogModal(taskId, '');
                this.startLiveLogStream(taskId);
            } else {
                // For completed tasks, fetch static log
                const logResponse = await fetch(`/api/tasks/${taskId}/log`);
                if (logResponse.ok) {
                    const data = await logResponse.json();
                    this.displayTaskLogModal(taskId, data.log);
                } else {
                    console.error('Failed to fetch task log:', logResponse.status);
                }
            }
        } catch (error) {
            console.error('Error showing task log:', error);
        }
    }

    startLiveLogStream(taskId) {
        // Close any existing stream
        if (this.currentLogStream) {
            this.currentLogStream.close();
        }

        // Create EventSource for live log streaming
        const eventSource = new EventSource(`/api/tasks/${taskId}/log/stream`);
        this.currentLogStream = eventSource;

        // Buffer for batching DOM updates
        this.logUpdateBuffer = [];
        this.logUpdateTimeout = null;
        
        // Throttling for very rapid updates
        this.lastUpdateTime = 0;
        this.minUpdateInterval = 50; // Minimum 50ms between updates

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.error) {
                    eventSource.close();
                    return;
                }

                const logContent = document.getElementById('taskLogContent');
                if (!logContent) return;

                if (data.type === 'initial') {
                    // Initial log content - render immediately
                    this.renderLogContent(logContent, data.log, 'replace');
                } else if (data.type === 'update') {
                    // Apply throttling for very rapid updates
                    const now = Date.now();
                    if (now - this.lastUpdateTime >= this.minUpdateInterval) {
                        this.bufferLogUpdate(logContent, data.log);
                        this.lastUpdateTime = now;
                    } else {
                        // Still buffer the update but don't show indicator
                        this.bufferLogUpdate(logContent, data.log);
                    }
                } else if (data.type === 'final') {
                    // Final log content - render immediately
                    this.renderLogContent(logContent, data.log, 'replace');
                    eventSource.close();
                }

                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            } catch (error) {
            }
        };

        eventSource.onerror = (error) => {
            eventSource.close();
        };
    }

    bufferLogUpdate(logContent, newLogContent) {
        // Split the new log content into lines and add to buffer
        const newLines = newLogContent.split('\n').filter(line => line.trim() !== '');
        this.logUpdateBuffer.push(...newLines);
        
        // Show buffering indicator
        this.showBufferingIndicator(logContent, true);
        
        // Clear existing timeout
        if (this.logUpdateTimeout) {
            clearTimeout(this.logUpdateTimeout);
        }
        
        // Set timeout to batch update (max 100ms delay)
        this.logUpdateTimeout = setTimeout(() => {
            this.flushLogBuffer(logContent);
            this.showBufferingIndicator(logContent, false);
        }, 100);
    }

    showBufferingIndicator(logContent, show) {
        // Find or create buffering indicator
        let indicator = logContent.querySelector('.buffering-indicator');
        
        if (show && !indicator) {
            // Create buffering indicator
            indicator = document.createElement('div');
            indicator.className = 'buffering-indicator text-muted small';
            indicator.innerHTML = '<i class="fas fa-sync-alt fa-spin me-2"></i>Buffering logs...';
            indicator.style.cssText = 'padding: 5px; background: rgba(0,0,0,0.05); border-radius: 3px; margin: 5px 0;';
            logContent.appendChild(indicator);
        } else if (!show && indicator) {
            // Remove buffering indicator
            indicator.remove();
        }
    }

    flushLogBuffer(logContent) {
        if (this.logUpdateBuffer.length === 0) return;
        
        // Create document fragment for efficient DOM manipulation
        const fragment = document.createDocumentFragment();
        
        // Add all buffered lines to fragment
        this.logUpdateBuffer.forEach(line => {
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.textContent = line;
            fragment.appendChild(div);
        });
        
        // Append fragment to log content (single DOM operation)
        logContent.appendChild(fragment);
        
        // Limit log content to prevent performance issues (keep last 1000 lines)
        const maxLines = 1000;
        const logEntries = logContent.querySelectorAll('.log-entry');
        if (logEntries.length > maxLines) {
            const linesToRemove = logEntries.length - maxLines;
            for (let i = 0; i < linesToRemove; i++) {
                logEntries[i].remove();
            }
        }
        
        // Clear buffer
        this.logUpdateBuffer = [];
        this.logUpdateTimeout = null;
    }

    renderLogContent(logContentElement, logContent, mode = 'append') {
        // Ensure logContent is a string and split into lines
        const logLines = typeof logContent === 'string' ? logContent : String(logContent);
        const lines = logLines.split('\n').filter(line => line.trim() !== '');
        
        if (mode === 'replace') {
            // Replace all content
            logContentElement.innerHTML = lines
                .map(line => `<div class="log-entry">${line}</div>`)
                .join('');
        } else {
            // Append content
            const fragment = document.createDocumentFragment();
            lines.forEach(line => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.textContent = line;
                fragment.appendChild(div);
            });
            logContentElement.appendChild(fragment);
        }
    }

    stopLiveLogStream() {
        if (this.currentLogStream) {
            this.currentLogStream.close();
            this.currentLogStream = null;
        }
        
        // Clean up buffer and timeout
        if (this.logUpdateTimeout) {
            clearTimeout(this.logUpdateTimeout);
            this.logUpdateTimeout = null;
        }
        this.logUpdateBuffer = [];
    }

    displayTaskLogModal(taskId, logContent) {
        // Get task details for the modal header
        const task = this.getTaskById(taskId);
        if (!task) return;

        // Store task ID in modal dataset for download functionality
        const modal = document.getElementById('taskLogModal');
        modal.dataset.taskId = taskId;

        // Update modal content
        document.getElementById('modalTaskType').textContent = this.getTaskDisplayName(task.type);
        document.getElementById('modalTaskStatus').textContent = this.getTaskStatusText(task.status);
        document.getElementById('modalTaskStartTime').textContent = task.start_time ? 
            new Date(task.start_time * 1000).toLocaleString() : 'N/A';
        document.getElementById('modalTaskDuration').textContent = task.duration ? 
            `${task.duration.toFixed(1)}s` : 'N/A';

        // Display log content
        document.getElementById('taskLogContent').innerHTML = logContent
            .split('\n')
            .map(line => `<div class="log-entry">${line}</div>`)
            .join('');

        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }

    getTaskById(taskId) {
        // Get task details from the grid data
        if (this.taskGridApi) {
            const rowData = this.taskGridApi.getRenderedNodes().map(node => node.data);
            const task = rowData.find(row => row.id === taskId);
            if (task) {
                return {
                    id: task.id,
                    type: task.type,
                    status: task.status,
                    start_time: task.startTime !== 'N/A' ? new Date(task.startTime).getTime() / 1000 : null,
                    duration: task.duration !== 'N/A' ? parseFloat(task.duration.replace('s', '')) : null
                };
            }
        }
        return null;
    }

    async stopTask(taskId) {
        try {
            // Use the general task stop endpoint for all tasks
            const response = await fetch(`/api/tasks/${taskId}/stop`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showToast(result.message || 'Task stopped successfully', 'success');
                
                // Refresh the task list to show updated status
                this.refreshTasks();
                
                // If this was a ROM scan task, restore scan button state
                const taskResponse = await fetch('/api/tasks', {
                    headers: {
                        'Accept-Encoding': 'gzip, deflate' // Enable compression for task data
                    }
                });
                if (taskResponse.ok) {
                    const tasks = await taskResponse.json();
                    const task = tasks.find(t => t.id === taskId);
                    if (task && task.type === 'rom_scan') {
                        this.restoreScanButtonState();
                    }
                }
                
                // Avoid an immediate manual grid reload here; rely on WebSocket/system update
                // to perform a single, authoritative refresh and prevent duplicate updates.
            } else {
                const errorData = await response.json();
                this.showToast(errorData.error || 'Failed to stop task', 'error');
            }
        } catch (error) {
            this.showToast('Error stopping task', 'error');
        }
    }

    async deleteTask(taskId) {
        try {
            // Confirm deletion
            if (!confirm('Are you sure you want to delete this queued task?')) {
                return;
            }

            const response = await fetch(`/api/tasks/${taskId}/delete`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showToast(result.message || 'Task deleted successfully', 'success');
                
                // Refresh the task list to remove the deleted task
                this.refreshTasks();
            } else {
                const errorData = await response.json();
                this.showToast(errorData.error || 'Failed to delete task', 'error');
            }
        } catch (error) {
            this.showToast('Error deleting task', 'error');
        }
    }

    downloadTaskLog() {
        // Get the current task ID from the modal
        const taskId = this.getCurrentModalTaskId();
        if (!taskId) {
            this.showToast('Unable to determine task ID', 'error');
            return;
        }

        // Download the log file directly from the server
        const downloadUrl = `/api/tasks/${taskId}/log/download`;
        
        // Create a temporary link and trigger download
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        this.showToast('Log download started', 'success');
    }

    getCurrentModalTaskId() {
        // Try to get task ID from the modal context
        // This is a fallback method - ideally we'd store the task ID when opening the modal
        const modal = document.getElementById('taskLogModal');
        if (modal && modal.dataset.taskId) {
            return modal.dataset.taskId;
        }
        
        // If no stored task ID, try to find it from the current log stream
        if (this.currentLogStream && this.currentLogStream.url) {
            const match = this.currentLogStream.url.match(/\/api\/tasks\/([^\/]+)\/log\/stream/);
            if (match) {
                return match[1];
            }
        }
        
        return null;
    }

    startTaskAutoRefresh() {
        // Auto-refresh tasks every second, but only if we're on the main page and authenticated
        if (!this.taskRefreshInterval && window.location.pathname === '/') {
            // First, check if we're authenticated by making a test request
            this.checkAuthenticationAndStartRefresh();
        }
    }
    
    async checkAuthenticationAndStartRefresh() {
        try {
            const response = await fetch('/api/tasks', {
                method: 'HEAD', // Just check if we can access the endpoint
                redirect: 'manual',
                credentials: 'same-origin', // Include cookies for authentication
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression
                }
            });
            
            // If we get a successful response or a 401 (which means we're authenticated but no tasks)
            if (response.ok || response.status === 401) {
                this.taskRefreshInterval = setInterval(() => {
                    // Clear any pending timeout
                    if (this.taskRefreshTimeout) {
                        clearTimeout(this.taskRefreshTimeout);
                    }
                    
                    // Set a timeout to ensure we don't call refreshTasks too frequently
                    this.taskRefreshTimeout = setTimeout(() => {
                        this.refreshTasks();
                    }, 100); // Small delay to debounce rapid calls
                }, 1000);
            } else {
            }
        } catch (error) {
        }
    }

    stopTaskAutoRefresh() {
        if (this.taskRefreshInterval) {
            clearInterval(this.taskRefreshInterval);
            this.taskRefreshInterval = null;
        }
        
        // Also clear any pending timeout
        if (this.taskRefreshTimeout) {
            clearTimeout(this.taskRefreshTimeout);
            this.taskRefreshTimeout = null;
        }
        
        // Reset the refresh flag
        this.isRefreshingTasks = false;
    }

    getRefreshStatistics() {
        return {
            calls: this.refreshCallCount,
            skipped: this.refreshSkipCount,
            efficiency: this.refreshCallCount > 0 ? (this.refreshSkipCount / (this.refreshCallCount + this.refreshSkipCount) * 100).toFixed(1) + '%' : '0%'
        };
    }

    showToast(message, type = 'info') {
        // Show a toast notification
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            if (toast.parentNode) {
                document.body.removeChild(toast);
            }
        });
    }
    initializeEventListeners() {
        // System selection - support both old select and new searchable combobox
        const systemSelect = document.getElementById('systemSelect');
        if (systemSelect) {
            systemSelect.addEventListener('change', (e) => {
            this.loadRomSystem(e.target.value);
            });
        }
        
        // Listen for system selection from searchable combobox
        document.addEventListener('systemSelected', (e) => {
            this.loadRomSystem(e.detail.system.name);
        });

        // Button event listeners
        document.getElementById('unifiedScanBtn').addEventListener('click', () => this.unifiedScan());
        document.getElementById('saveGamelistBtn').addEventListener('click', () => this.saveGamelist());
        document.getElementById('confirmGamelistSave').addEventListener('click', () => this.confirmGamelistSave());
        document.getElementById('forceImportGamelistBtn').addEventListener('click', () => this.showForceImportModal());
        document.getElementById('confirmForceImportBtn').addEventListener('click', () => this.confirmForceImport());
        document.getElementById('clearImageCacheBtn').addEventListener('click', () => this.clearImageCache());
        document.getElementById('startResizeMediasBtn').addEventListener('click', () => this.startResizeMedias());
        document.getElementById('startImportMediasBtn').addEventListener('click', () => this.startImportMedias());
        
        document.getElementById('scrapLaunchboxBtn').addEventListener('click', () => this.scrapLaunchbox());
        document.getElementById('scrapIgdbBtn').addEventListener('click', () => this.scrapIgdb());
        document.getElementById('scrapSteamBtn').addEventListener('click', () => this.scrapSteam());
        document.getElementById('scrapSteamgriddbBtn').addEventListener('click', () => this.scrapSteamgriddb());
        const screenscraperBtn = document.getElementById('scrapScreenscraperBtn');
        if (screenscraperBtn) {
            screenscraperBtn.addEventListener('click', () => {
                this.scrapScreenscraper();
            });
            
        } else {
        }
        
        document.getElementById('scrapMobygamesBtn').addEventListener('click', () => this.scrapMobygames());
        
        document.getElementById('scrapDatscrapperBtn').addEventListener('click', () => this.scrapDatscrapper());
        
        // Add event listeners for find best match dropdown options
        document.getElementById('findBestMatchLaunchboxBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.findBestMatchForSelectedOriginal(); // Use original LaunchBox functionality
        });
        document.getElementById('findBestMatchMobygamesBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.findBestMatchForSelectedMobygames(); // Use MobyGames-specific functionality
        });
        document.getElementById('findBestMatchDatscrapperBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.findBestMatchForSelectedDatscrapper(); // Use DAT Scrapper-specific functionality
        });
        document.getElementById('findBestMatchSteamBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.findBestMatchForSelectedSteam(); // Use Steam-specific functionality
        });
        document.getElementById('findBestMatchIgdbBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.findBestMatchForSelectedIgdb(); // Use IGDB-specific functionality
        });
        
        document.getElementById('global2DBoxGeneratorBtn').addEventListener('click', () => this.generate2DBoxForSelected());
        document.getElementById('globalYoutubeDownloadBtn').addEventListener('click', () => this.openYoutubeDownloadModal());
        document.getElementById('startYoutubeDownloadBtn').addEventListener('click', () => this.startYoutubeDownload());
        
        // Initialize global algorithm selector
        this.initializeGlobalAlgorithmSelector();

        // Task log modal download button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'downloadTaskLogBtn') {
                this.downloadTaskLog();
            }
        });

        // Task log modal event listeners
        const taskLogModal = document.getElementById('taskLogModal');
        if (taskLogModal) {
            taskLogModal.addEventListener('hidden.bs.modal', () => {
                this.stopLiveLogStream();
            });
        }

        document.getElementById('saveGameChanges').addEventListener('click', async () => await this.saveGameChangesFromModal());
        
        // Add event listeners for favorite and kidgame fields
        document.getElementById('editFavorite').addEventListener('click', () => this.toggleFavorite());
        document.getElementById('editKidgame').addEventListener('click', () => this.toggleKidgame());
        document.getElementById('manualScrapBtn').addEventListener('click', async () => {
            // Save changes first before opening manual scrap modal
            await this.saveGameChangesFromModal();
            await this.openManualScrapModal();
        });
        
        // Manual scrap button in media preview pane
        document.getElementById('manualScrapPreviewBtn').addEventListener('click', async () => {
            await this.openManualScrapFromPreview();
        });
        document.getElementById('applyManualScrapResults').addEventListener('click', async () => await this.applyManualScrapResults());
        
        // IGDB test connection button
        document.getElementById('testIgdbConnectionBtn').addEventListener('click', async () => await this.testIgdbConnection());
        
        // ScreenScraper test connection button
        const testScreenscraperBtn = document.getElementById('testScreenscraperConnectionBtn');
        if (testScreenscraperBtn) {
            testScreenscraperBtn.addEventListener('click', async () => await this.testScreenscraperConnection());
        } else {
            console.warn('testScreenscraperConnectionBtn not found');
        }
        
        // SteamGridDB test connection button
        const testSteamgriddbBtn = document.getElementById('testSteamgriddbConnectionBtn');
        if (testSteamgriddbBtn) {
            testSteamgriddbBtn.addEventListener('click', async () => await this.testSteamgriddbConnection());
        } else {
            console.warn('testSteamgriddbConnectionBtn not found');
        }
        
        // Handle manual scrap modal cancel button
        document.getElementById('manualScrapModal').addEventListener('hidden.bs.modal', () => {
            // Only reopen game edit modal if manual scrap was opened from game edit modal
            if (!this.manualScrapFromPreview) {
                // When manual scrap modal is closed, ensure the game edit modal is still open
                const editModal = document.getElementById('editGameModal');
                if (editModal && !editModal.classList.contains('show')) {
                    // Reopen the game edit modal if it was closed
                    const editModalInstance = new bootstrap.Modal(editModal);
                    editModalInstance.show();
                    
                    // Repopulate the edit modal fields if they're empty
                    if (this.editingGamePath) {
                        const game = this.games.find(g => g.path === this.editingGamePath);
                        if (game) {
                            // Check if fields are empty and repopulate if needed
                            const nameField = document.getElementById('editName');
                            if (!nameField.value) {
                                this.populateEditModal(game);
                            }
                        }
                    }
                }
            }
        });

        document.getElementById('clearFiltersBtn').addEventListener('click', async () => await this.clearAllFilters());
        document.getElementById('thumbnailViewBtn').addEventListener('click', () => this.toggleThumbnailView());
        document.getElementById('toggleColumnsPanelBtn').addEventListener('click', () => this.toggleColumnsPanel());
        document.getElementById('showAllColumnsBtn').addEventListener('click', () => this.showAllColumns());
        document.getElementById('hideAllColumnsBtn').addEventListener('click', () => this.hideAllColumns());
        document.getElementById('resetColumnsBtn').addEventListener('click', () => this.resetColumns());

        // Media preview is now always enabled (no checkbox needed)

        // Force download toggle (in LaunchBox Configuration modal)
        document.getElementById('forceDownloadImagesModal').addEventListener('change', (e) => {
            this.setCookie('forceDownloadImages', e.target.checked);
        });

        // IGDB overwrite text fields toggle (in IGDB Configuration modal)
        document.getElementById('overwriteTextFieldsModal').addEventListener('change', (e) => {
            this.setCookie('overwriteTextFields', e.target.checked);
        });

        // IGDB overwrite media fields toggle (in IGDB Configuration modal)
        document.getElementById('overwriteMediaFieldsModal').addEventListener('change', (e) => {
            this.setCookie('overwriteMediaFields', e.target.checked);
        });

        // Steam overwrite media fields toggle (in Steam Configuration modal)
        document.getElementById('overwriteMediaFieldsSteamModal').addEventListener('change', (e) => {
            this.setCookie('overwriteMediaFieldsSteam', e.target.checked);
        });

        // Steam overwrite text fields toggle (in Steam Configuration modal)
        document.getElementById('overwriteTextFieldsSteamModal').addEventListener('change', (e) => {
            this.setCookie('overwriteTextFieldsSteam', e.target.checked);
        });

        // SteamGridDB overwrite media fields toggle (in SteamGridDB Configuration modal)
        document.getElementById('overwriteMediaFieldsSteamGridDBModal').addEventListener('change', (e) => {
            this.setCookie('overwriteMediaFieldsSteamGridDB', e.target.checked);
        });

        // ScreenScraper overwrite text fields toggle (in ScreenScraper Configuration modal)
        document.getElementById('overwriteTextFieldsScreenscraperModal').addEventListener('change', (e) => {
            this.setCookie('overwriteTextFieldsScreenscraper', e.target.checked);
        });

        // ScreenScraper overwrite media fields toggle (in ScreenScraper Configuration modal)
        document.getElementById('overwriteMediaFieldsScreenscraperModal').addEventListener('change', (e) => {
            this.setCookie('overwriteMediaFieldsScreenscraper', e.target.checked);
        });

        // IGDB field selection checkboxes
        document.querySelectorAll('.igdb-field-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', async () => {
                await this.saveIgdbFieldSettings();
            });
        });

        // Steam field selection checkboxes
        document.querySelectorAll('.steam-field-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', async () => {
                await this.saveSteamFieldSettings();
            });
        });

        // IGDB field selection quick actions
        document.getElementById('selectAllFields').addEventListener('click', async () => {
            document.querySelectorAll('.igdb-field-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
            await this.saveIgdbFieldSettings();
        });

        document.getElementById('deselectAllFields').addEventListener('click', async () => {
            document.querySelectorAll('.igdb-field-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
            await this.saveIgdbFieldSettings();
        });

        // Steam field selection quick actions
        document.getElementById('selectAllSteamFields').addEventListener('click', async () => {
            document.querySelectorAll('.steam-field-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
            await this.saveSteamFieldSettings();
        });

        document.getElementById('deselectAllSteamFields').addEventListener('click', async () => {
            document.querySelectorAll('.steam-field-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
            await this.saveSteamFieldSettings();
        });

        // SteamGridDB field selection checkboxes
        document.querySelectorAll('.steamgriddb-field-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', async () => {
                await this.saveSteamGridDBFieldSettings();
            });
        });

        // SteamGridDB field selection quick actions
        document.getElementById('selectAllSteamGridDBFields').addEventListener('click', async () => {
            document.querySelectorAll('.steamgriddb-field-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
            await this.saveSteamGridDBFieldSettings();
        });

        document.getElementById('deselectAllSteamGridDBFields').addEventListener('click', async () => {
            document.querySelectorAll('.steamgriddb-field-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
            await this.saveSteamGridDBFieldSettings();
        });

        // ScreenScraper field selection checkboxes
        document.querySelectorAll('.screenscraper-field-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', async () => {
                await this.saveScreenscraperFieldSettings();
            });
        });

        // ScreenScraper field selection quick actions
        document.getElementById('selectAllScreenscraperFields').addEventListener('click', async () => {
            document.querySelectorAll('.screenscraper-field-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
            await this.saveScreenscraperFieldSettings();
        });

        document.getElementById('deselectAllScreenscraperFields').addEventListener('click', async () => {
            document.querySelectorAll('.screenscraper-field-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
            await this.saveScreenscraperFieldSettings();
        });

        // LaunchBox field selection checkboxes
        document.querySelectorAll('.launchbox-field-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', async () => {
                await this.saveLaunchboxFieldSettings();
            });
        });

        // LaunchBox field selection quick actions
        document.getElementById('selectAllLaunchboxFields').addEventListener('click', async () => {
            document.querySelectorAll('.launchbox-field-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
            await this.saveLaunchboxFieldSettings();
        });

        document.getElementById('deselectAllLaunchboxFields').addEventListener('click', async () => {
            document.querySelectorAll('.launchbox-field-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
            await this.saveLaunchboxFieldSettings();
        });

        // LaunchBox overwrite text fields checkbox
        const overwriteTextFieldsCheckbox = document.getElementById('overwriteTextFieldsLaunchbox');
        if (overwriteTextFieldsCheckbox) {
            overwriteTextFieldsCheckbox.addEventListener('change', (e) => {
                this.setCookie('launchboxOverwriteTextFields', e.target.checked);
            });
        } else {
        }

        // Grid selection change - handled by grid API listener

        // Delete selected games button
        document.getElementById('deleteSelectedBtn').addEventListener('click', () => this.showDeleteConfirmation());
        
        // Show hidden button
        document.getElementById('showHiddenBtn').addEventListener('click', () => this.toggleHiddenFilter());
        
        // Show duplicates button
        document.getElementById('showDuplicatesBtn').addEventListener('click', () => this.toggleDuplicatesFilter());
        
        // Confirm delete button
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => {
            if (this.gameToDelete) {
                // Single game deletion
                this.confirmSingleGameDelete();
            } else {
                // Bulk deletion
                this.deleteSelectedGames();
            }
        });

        // Add global keyboard event listener for delete key and arrow navigation
        document.addEventListener('keydown', (event) => {
            // Handle Delete key with priority: thumbnails first, then media, then games
            if (event.key === 'Delete') {
                // If thumbnails are selected, delete thumbnails (highest priority)
                if (this.selectedThumbnails && this.selectedThumbnails.length > 0) {
                    event.preventDefault();
                    this.deleteSelectedThumbnails();
                    return; // Exit early, don't process other deletions
                }
                
                // If media is selected, delete media (second priority)
                if (this.selectedMedia && this.selectedMedia.length > 0) {
                    event.preventDefault();
                    this.deleteSelectedMedia();
                    return; // Exit early, don't process game deletion
                }
                
                // If no media selected but games are selected and grid has focus, delete games
                if (this.selectedGames.length > 0 && 
                    (document.activeElement === document.body || 
                     document.activeElement.closest('.ag-root-wrapper'))) {
                    event.preventDefault();
                    this.showDeleteConfirmation();
                }
            }
            
            // Arrow key navigation for grid rows
            if ((event.key === 'ArrowUp' || event.key === 'ArrowDown') && 
                (document.activeElement === document.body || 
                 document.activeElement.closest('.ag-root-wrapper'))) {
                event.preventDefault();
                this.navigateAndPreviewRow(event.key === 'ArrowUp' ? 'up' : 'down');
            }
            
            // Home/End key navigation for first/last rows
            if ((event.key === 'Home' || event.key === 'End') && 
                (document.activeElement === document.body || 
                 document.activeElement.closest('.ag-root-wrapper'))) {
                event.preventDefault();
                this.navigateAndPreviewRow(event.key === 'Home' ? 'first' : 'last');
            }
            
            // Enter key to open edit modal for selected row
            if (event.key === 'Enter' && 
                (document.activeElement === document.body || 
                 document.activeElement.closest('.ag-root-wrapper'))) {
                event.preventDefault();
                this.openEditModalForSelectedRow();
            }
        });
    }

    initializeWebSocket() {
        try {
            
            // Check if Socket.IO is available
            if (typeof io === 'undefined') {
                setTimeout(() => this.initializeWebSocket(), 500);
                return;
            }
            
            // Initialize Socket.IO connection
            this.socket = io();
            
            // Connection events
            this.socket.on('connect', () => {
                this.showToast('Connected to real-time updates', 'success');
            });
            
            this.socket.on('disconnect', () => {
                this.showToast('Disconnected from real-time updates', 'warning');
            });
            
            // System update events
            this.socket.on('system_updated', (data) => {
                this.handleSystemUpdate(data);
            });
            
            // Join system room when system is loaded
            this.socket.on('connected', (data) => {
                if (this.currentSystem) {
                    this.socket.emit('join_system', { system: this.currentSystem });
                }
            });
            
            // Task completion events
            this.socket.on('task_completed', (data) => {
                this.handleTaskCompletion(data);
            });
            
            // Add cleanup on page unload
            window.addEventListener('beforeunload', () => {
                if (this.socket && this.currentSystem) {
                    this.socket.emit('leave_system', { system: this.currentSystem });
                }
            });

        } catch (error) {
            // Retry after a delay
            setTimeout(() => this.initializeWebSocket(), 1000);
        }
    }
    
    handleSystemUpdate(data) {
        const { system, action, data: updateData } = data;

        // Only process updates for the current system
        if (system !== this.currentSystem) {
            return;
        }

        switch (action) {
            case 'gamelist_updated':
                // Show more specific message based on what actually changed
                if (updateData.updated_count > 0) {
                    this.showToast(`Scraping completed: ${updateData.updated_count} games updated`, 'success');
                } else {
                    this.showToast(`Gamelist refreshed: ${updateData.games_count} total games`, 'info');
                }
                // For gamelist updates, fetch fresh data to ensure consistency
                this.refreshGameGridWithData();
                // Also refresh the system dropdown to update game counts
                this.loadAvailableSystems();
                break;
                
            case 'games_deleted':
                this.showToast(`Deleted ${updateData.deleted_files.length} files`, 'info');
                // For deletions, we need to fetch the updated data first
                this.syncGameData();
                break;
                
            case 'game_updated':
                this.showToast(`Game updated: ${updateData.rom_path}`, 'info');
                // For game updates, we need to fetch the latest data to sync properly
                this.syncGameData();
                break;
                
            default:
        }
    }
    
    refreshGameGrid() {
        if (this.currentSystem && this.gridApi) {
            // Use AG Grid's efficient refreshCells API to update the grid
            // This preserves selection, scroll position, and filters while updating data
            this.gridApi.refreshCells({ 
                force: true,
                suppressFlash: false,
                rowNodes: undefined // Refresh all rows
            });
        }
    }
    
    resetUIState() {
        // Reset any stuck UI state
        this.selectedMatchIndex = -1;
        this.currentMatches = null;
        this.currentOriginalGameName = null;
        this.currentOriginalGamePath = null;
        this.isModalOpen = false;
        this.pendingBestMatchResults = null;
        this.currentBestMatchIndex = 0;
        this.currentModalContext = null;
        
        // Re-enable any disabled buttons
        const applyBtn = document.getElementById('applySelectedMatch');
        if (applyBtn) {
            applyBtn.disabled = true;
        }
        
        // Clear any selection highlights
        document.querySelectorAll('.match-card.selected').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Force remove any modal-related CSS classes that might be stuck
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        // Remove any stuck modal backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }
        
        // Reset modal event listeners flag to allow fresh listeners next time
        this.modalEventListenersAdded = false;
        
    }
    
    async refreshGameGridWithData() {
        if (!this.currentSystem || !this.gridApi) return;
        
        try {
            
            // Fetch the latest gamelist data
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for large gamelist data
                }
            });
            if (response.ok) {
                const result = await response.json();
                
                if (result.success && result.games) {
                    // Update the local games array (deduplicate by path to avoid duplicate nodes)
                    const uniqueByPath = new Map();
                    for (const g of result.games) {
                        if (g && g.path) {
                            uniqueByPath.set(g.path, g);
                        }
                    }
                    this.games = Array.from(uniqueByPath.values());
                    
                    // Use AG Grid's setGridOption to efficiently update the grid
                    // This will preserve selection and scroll position
                    await this.refreshGridData();
                    // Keep our current game map in sync to ensure diff updates work later
                    this.currentGameData = new Map();
                    this.games.forEach(game => this.currentGameData.set(game.path, game));
                    
                }
            }
        } catch (error) {
            // Fallback to regular refresh if fetch fails
            this.refreshGameGrid();
        }
    }
    
    async syncGameData() {
        if (!this.currentSystem || !this.gridApi) return;
        
        try {
            
            // Fetch the latest gamelist data
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for large gamelist data
                }
            });
            if (response.ok) {
                const result = await response.json();
                
                if (result.success && result.games) {
                    // Update the local games array
                    this.games = result.games;
                    
                    // Use AG Grid's setGridOption to efficiently update the grid
                    // This will preserve selection and scroll position
                    await this.refreshGridData();
                    
                    // Refresh media preview for currently selected game if any
                    if (this.mediaPreviewEnabled && this.currentMediaPreviewGame) {
                        const selectedRows = this.gridApi.getSelectedRows();
                        if (selectedRows.length > 0) {
                            this.showMediaPreview(selectedRows[0]);
                        }
                    }
                    
                }
            }
        } catch (error) {
            // Fallback to full refresh if sync fails
            this.refreshGameGrid();
        }
    }

    initializeTaskPanelResizing() {
        const resizeHandle = document.getElementById('taskPanelResizeHandle');
        const tabbedComponent = document.querySelector('#combinedPanelTabContent');
        const taskGrid = document.getElementById('taskGrid');
        
        if (!resizeHandle || !tabbedComponent || !taskGrid) return;
        
        // Mouse down event
        resizeHandle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.taskPanelResizing = true;
            this.taskPanelStartHeight = tabbedComponent.offsetHeight;
            this.taskPanelStartY = e.clientY;
            
            // Add resizing class to body
            document.body.classList.add('resizing');
            
            // Add event listeners for mouse move and mouse up
            document.addEventListener('mousemove', this.handleTaskPanelResize);
            document.addEventListener('mouseup', this.stopTaskPanelResize);
        });
        
        // Touch events for mobile support
        resizeHandle.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.taskPanelResizing = true;
            this.taskPanelStartHeight = tabbedComponent.offsetHeight;
            this.taskPanelStartY = e.touches[0].clientY;
            
            document.body.classList.add('resizing');
            
            document.addEventListener('touchmove', this.handleTaskPanelResize);
            document.addEventListener('touchend', this.stopTaskPanelResize);
        });
    }
    
    handleTaskPanelResize = (e) => {
        if (!this.taskPanelResizing) return;
        
        const tabbedComponent = document.querySelector('#combinedPanelTabContent');
        const taskGrid = document.getElementById('taskGrid');
        if (!tabbedComponent || !taskGrid) return;
        
        const currentY = e.clientY || (e.touches && e.touches[0].clientY);
        if (!currentY) return;
        
        const deltaY = this.taskPanelStartY - currentY;
        const newHeight = Math.max(200, Math.min(800, this.taskPanelStartHeight + deltaY));
        
        // Add resizing class for visual feedback
        tabbedComponent.classList.add('resizing');
        taskGrid.classList.add('resizing');
        
        // Update height of the entire tabbed component
        tabbedComponent.style.height = newHeight + 'px';
        
        // Also update task grid height to fill the available space
        const gridHeight = Math.max(160, newHeight - 60); // Subtract space for headers
        taskGrid.style.height = gridHeight + 'px';
        
        // Show height indicator
        this.showHeightIndicator(newHeight);
        
        // Save the height preference
        this.setCookie('taskPanelHeight', newHeight);
        
        // Refresh the grid to ensure proper rendering
        if (this.taskGridApi) {
            this.taskGridApi.refreshCells();
        }
    }
    
    stopTaskPanelResize = () => {
        this.taskPanelResizing = false;
        document.body.classList.remove('resizing');
        
        // Remove resizing class from tabbed component and task grid
        const tabbedComponent = document.querySelector('#combinedPanelTabContent');
        const taskGrid = document.getElementById('taskGrid');
        if (tabbedComponent) {
            tabbedComponent.classList.remove('resizing');
        }
        if (taskGrid) {
            taskGrid.classList.remove('resizing');
        }
        
        // Hide height indicator
        this.hideHeightIndicator();
        
        // Remove event listeners
        document.removeEventListener('mousemove', this.handleTaskPanelResize);
        document.removeEventListener('mouseup', this.stopTaskPanelResize);
        document.removeEventListener('touchmove', this.handleTaskPanelResize);
        document.removeEventListener('touchend', this.stopTaskPanelResize);
    }
    
    showHeightIndicator(height) {
        // Create or update height indicator
        let indicator = document.getElementById('heightIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'heightIndicator';
            indicator.className = 'height-indicator';
            document.body.appendChild(indicator);
        }
        
        indicator.textContent = `${height}px`;
        indicator.style.display = 'block';
    }
    
    hideHeightIndicator() {
        const indicator = document.getElementById('heightIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    showDeleteConfirmation() {
        if (this.selectedGames.length === 0) {
            this.showToast('No games selected for deletion', 'warning');
            return;
        }
        
        // Update the modal with the count of selected games
        document.getElementById('deleteGameCount').textContent = this.selectedGames.length;
        
        // Show the confirmation modal
        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        modal.show();
    }
    
    async deleteSelectedGames() {
        if (this.selectedGames.length === 0) return;
        
        try {
            // Get the selected game names for display
            const gameNames = this.selectedGames.map(game => game.name).join(', ');
            
            // Delete associated ROM and media files for each selected game
            const deletedFiles = [];
            for (const game of this.selectedGames) {
                const filesDeleted = await this.deleteGameFiles(game);
                deletedFiles.push(...filesDeleted);
            }
            
            // Remove games from the games array using ROM file path as unique identifier
            const gameRomPaths = this.selectedGames.map(game => game.path);
            this.games = this.games.filter(game => !gameRomPaths.includes(game.path));
            
            // Update gamelist.xml to remove deleted games
            // Use deletedFiles which contains the full paths with system directory
            await this.updateGamelistAfterDeletion(deletedFiles);
            
            // Clear the selection
            this.selectedGames = [];
            this.gridApi.deselectAll();
            
            // Update the grid
            await this.refreshGridData();
            
            // Update the games count
            this.updateGamesCount();
            
            // Update the delete button state
            this.updateDeleteButtonState();
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
            modal.hide();
            
            // Show success message with file deletion info
            const fileCount = deletedFiles.length;
            const message = `Successfully deleted ${gameRomPaths.length} game(s) and ${fileCount} associated file(s)`;
            this.showToast(message, 'success');
            
            // Log the deletion
            
        } catch (error) {
            this.showToast('Error deleting games', 'error');
        }
    }

    async checkExistingTask() {
        // Check if there's an existing task running when the page loads
        try {
            const response = await fetch('/api/task/status-and-queue', {
                credentials: 'same-origin',
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression
                }
            });
            if (response.ok) {
                const data = await response.json();
                const task = data.current_task;
                if (task.status === 'running') {
                    this.displayExistingTask(task);
                } else if (task.status === 'completed' || task.status === 'error') {
                    this.displayCompletedTask(task);
                }
            }
        } catch (error) {
        }
    }

    displayExistingTask(task) {
        // Display an existing running task
        if (task.type === 'media_scan') {
            // Media scan tasks are now handled by the task panel
        }
        // Note: scraping and image_download tasks are now handled by the task panel
    }

    displayCompletedTask(task) {
        // Display a completed task result
        if (task.type === 'media_scan') {
            // Media scan tasks are now handled by the task panel
        }
        // Note: scraping and image_download tasks are now handled by the task panel
    }
    async loadRomSystem(systemName) {
        if (!systemName) return;

        // Store previous system for cleanup
        const previousSystem = this.currentSystem;
        
        // Update current system
        this.currentSystem = systemName;
        this.setCookie('selectedSystem', systemName);
        
        // Update force import menu item state
        this.updateForceImportMenuState();
        
        // Leave previous system room if different
        if (this.socket && previousSystem && previousSystem !== systemName) {
            this.socket.emit('leave_system', { system: previousSystem });
        }
        
        // Join WebSocket room for this system
        if (this.socket) {
            this.socket.emit('join_system', { system: systemName });
        }
        
        // Clear selection only when actually changing systems, not when refreshing the same system
        if (previousSystem && previousSystem !== systemName) {
        if (this.gridApi) {
            this.gridApi.deselectAll();
        }
        this.selectedGames = [];
        }
        
        // Reset filters when changing systems
        if (this.duplicatesFilterActive) {
            await this.resetDuplicatesFilter();
        }
        if (this.hiddenFilterActive) {
            await this.resetHiddenFilter();
        }
        
        this.updateSelectionDisplay();
        
        try {
            const response = await fetch(`/api/rom-system/${systemName}/gamelist`, {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for large gamelist data
                }
            });
            if (response.ok) {
                const data = await response.json();
                this.games = data.games || [];

                // Only initialize grid if it doesn't exist yet
                if (!this.gridApi) {
                    await this.initializeGrid();
                }
                
                this.updateGamesCount();
                this.enableButtons();
                
                // Set the row data directly for client-side row model
                if (this.gridApi) {
                    // Use efficient update method instead of setGridOption
                    await this.updateGameGridData(this.games);
                    // Load saved column state
                    this.loadColumnState();
                }
                
                // Media preview is now always enabled
                this.mediaPreviewEnabled = true;
                
                // Reset navigation index to start when loading new system
                this.currentNavigationIndex = 0;
            }
        } catch (error) {
        }
    }

    async initializeGrid() {
        const gridDiv = document.getElementById('gamesGrid');
        gridDiv.innerHTML = '';

        // Wait for media mappings cache to be ready
        let attempts = 0;
        while (!this.mediaMappingsCache && attempts < 50) { // Wait up to 5 seconds
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (!this.mediaMappingsCache) {
        }

        // Generate dynamic column definitions
        const baseColumns = [
                { 
                    headerName: '', 
                    field: 'checkbox', 
                    width: 50, 
                    checkboxSelection: true, 
                    headerCheckboxSelection: true,
                    pinned: 'left',
                    resizable: false,
                    sortable: false,
                    filter: false
                },
                { 
                    field: 'name', 
                    headerName: 'Name ✏️', 
                    editable: true, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 2,
                    cellStyle: { 
                        fontWeight: 'bold',
                        backgroundColor: '#f8f9fa'
                    },
                    // Add a custom cell renderer for the name field to show edit indicator
                    cellRenderer: (params) => {
                        if (params.data && this.modifiedGames.has(params.data.id)) {
                            return `<span style="color: #28a745; font-weight: bold;">✏️ ${params.value}</span>`;
                        }
                        return params.value;
                    },
                    // Add header tooltip
                    headerTooltip: 'Click to edit game names inline. Press Enter on a selected row to start editing quickly.',
                    // Configure editing behavior
                    cellEditor: 'agTextCellEditor',
                    cellEditorParams: {
                        maxLength: 1000
                    },

                },
                { 
                    field: 'launchboxid', 
                    headerName: 'Launchbox ID', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1,
                    headerTooltip: 'Launchbox Database ID for exact matching. Auto-populated when scraping.',
                    cellStyle: { 
                        backgroundColor: '#e8f5e8',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    },
                    valueFormatter: function(params) {
                        // Ensure launchboxid is displayed as a string
                        return params.value ? String(params.value) : '';
                    },
                    valueParser: function(params) {
                        // Parse as integer for sorting/filtering
                        return params.newValue ? parseInt(params.newValue, 10) : null;
                    }
                },
                { 
                    field: 'igdbid', 
                    headerName: 'IGDB ID', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1,
                    headerTooltip: 'IGDB Database ID for exact matching. Auto-populated when scraping.',
                    cellStyle: { 
                        backgroundColor: '#e8f4fd',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    }
                },
                { 
                    field: 'screenscraperid', 
                    headerName: 'ScreenScraper ID', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1,
                    headerTooltip: 'ScreenScraper Database ID for exact matching. Auto-populated when scraping.',
                    cellStyle: { 
                        backgroundColor: '#fff3cd',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    }
                },
                { 
                    field: 'steamid', 
                    headerName: 'Steam ID', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1,
                    headerTooltip: 'Steam App ID for exact matching. Auto-populated when scraping.',
                    cellStyle: { 
                        backgroundColor: '#d1ecf1',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    }
                },
                { 
                    field: 'steamgridid', 
                    headerName: 'SteamGridDB ID', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1,
                    headerTooltip: 'SteamGridDB Game ID for media downloads. Auto-populated when scraping.',
                    cellStyle: { 
                        backgroundColor: '#e2e3e5',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    }
                },
                { 
                    field: 'mobygamesid', 
                    headerName: 'MobyGames ID', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1,
                    headerTooltip: 'MobyGames Database ID for exact matching. Auto-populated when scraping.',
                    cellStyle: { 
                        backgroundColor: '#f8d7da',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    }
                },

                { 
                    field: 'path', 
                    headerName: 'Path', 
                    editable: false,
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1
                },
                { 
                    field: 'desc', 
                    headerName: 'Description', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 2
                },
                { 
                    field: 'genre', 
                    headerName: 'Genre', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1
                },
                { 
                    field: 'developer', 
                    headerName: 'Developer', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1
                },
                { 
                    field: 'publisher', 
                    headerName: 'Publisher', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1
                },
                { 
                    field: 'rating', 
                    headerName: 'Rating', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1
                },
                { 
                    field: 'players', 
                    headerName: 'Players', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1
                },
                { 
                    field: 'video', 
                    headerName: 'Video', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1, 
                    cellRenderer: this.mediaCellRenderer
                },
                { 
                    field: 'youtubeurl', 
                    headerName: 'YouTube URL', 
                    editable: true, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 2,
                    headerTooltip: 'YouTube URL for game videos. Can be edited manually or populated by scraping.',
                    cellStyle: { 
                        backgroundColor: '#fff3cd',
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                    },
                    cellEditor: 'agTextCellEditor',
                    cellEditorParams: {
                        maxLength: 500
                    }
                }
            ];

        // Generate dynamic media columns from config
        const dynamicMediaColumns = await this.generateDynamicMediaColumns();
        
        // Combine base columns with dynamic media columns
        const allColumns = [...baseColumns, ...dynamicMediaColumns];

        const gridOptions = {
            // Use ROM path as unique row identifier for better update handling
            getRowId: (params) => {
                // Use the ROM path as the unique identifier since it's unique for each game
                return params.data.path || params.data.id || `game_${Math.random()}`;
            },
            // Apply custom row styling based on game properties using getRowClass
            getRowClass: (params) => {
                if (params.data && params.data.hidden === 'true') {
                    console.log(`Applying hidden-game-row class to: ${params.data.name}`);
                    return 'hidden-game-row';
                }
                return null;
            },
            // Ensure keyboard navigation respects current filters by resetting index
            onFilterChanged: () => {
                try {
                    const displayed = this.gridApi ? this.gridApi.getDisplayedRowCount() : 0;
                    this.currentNavigationIndex = displayed > 0 ? 0 : 0;
                } catch (e) {
                    // no-op
                }
            },
            columnDefs: allColumns,
            // Client-side Row Model Configuration (enables sorting)
            rowModelType: 'clientSide',
            rowSelection: 'multiple',
            suppressRowClickSelection: false,
            domLayout: 'normal',
            // Compact grid configuration
            rowHeight: 28,
            headerHeight: 32,
            defaultColDef: {
                sortable: true,
                filter: true,
                resizable: true,
                editable: false, // Default to non-editable
                filterParams: {
                    buttons: ['apply', 'reset'],
                    closeOnApply: true
                }
            },
            // Filter configuration
            suppressMenuHide: true,
            // Ensure grid stays visible during filtering
            suppressRowHoverHighlight: false,
            suppressCellFocus: false,
            // Stop editing when cell loses focus (not on Enter)
            stopEditingWhenCellsLoseFocus: true,

            // Enable column management features available in Community version
            suppressMovableColumns: false,
            suppressMenuHide: true,
            suppressRowHoverHighlight: false,
            suppressCellFocus: false,
            // Context menu for Community version
            onCellContextMenu: (event) => {
                console.log('onCellContextMenu triggered', event);
                event.event.preventDefault();
                event.event.stopPropagation();
                this.showContextMenu(event);
            },
            // State persistence event handlers
            onColumnMoved: () => {
                this.saveMainGridState();
            },
            onColumnResized: () => {
                this.saveMainGridState();
            },
            onSortChanged: () => {
                this.saveMainGridState();
            },
            onFilterChanged: () => {
                this.saveMainGridState();
            },
            onColumnVisible: () => {
                this.saveMainGridState();
            },
            onColumnPinned: () => {
                this.saveMainGridState();
            }
        };

        // Create the grid using the new createGrid method
        this.gridApi = agGrid.createGrid(gridDiv, gridOptions);
        
        // Apply custom CSS class to prevent theme conflicts with popups
        gridDiv.classList.add('game-grid-container');
        
        // Prevent browser context menu on the grid
        gridDiv.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            event.stopPropagation();
        });
        
        // Setup lazy loading for thumbnail view
        setTimeout(() => {
            this.setupLazyLoading();
        }, 100);
        
        // Focus on first row when grid is first loaded
        this.focusFirstRow();

        // Add selection change listener
        this.gridApi.addEventListener('selectionChanged', () => {
            const selectedRows = this.gridApi.getSelectedRows();
            this.selectedGames = selectedRows;
            
            // Show media preview for selected games
            if (selectedRows.length > 0) {
                this.showMediaPreview(selectedRows[0]);
            } else {
                this.hideMediaPreview();
            }
            
            // Update selection display immediately
            this.updateSelectionDisplay();
            
            // Update delete button state
            this.updateDeleteButtonState();
            
            // Update Find Best Match button state
            this.updateFindBestMatchButtonState();
            
            // Update 2D Box Generator button state
            this.update2DBoxGeneratorButtonState();
            
            // Update YouTube Download button state
            this.updateYoutubeDownloadButtonState();
        });

        // Add row click listener for immediate media preview
        this.gridApi.addEventListener('rowClicked', async (event) => {
            if (this.mediaPreviewEnabled) {
                await this.showMediaPreview(event.data);
                // Sync navigation index to the clicked row
                this.syncNavigationIndex(event.data);
            }
        });

        // Add cell editing event listeners
        this.gridApi.addEventListener('cellValueChanged', (event) => {
            
            // Mark the game as modified when inline editing occurs
            if (event.data && event.colDef.field) {
                this.markGameAsModified(event.data);
                
                // Show a small notification that the change was made
                this.showInlineEditNotification(event.colDef.field, event.oldValue, event.newValue);
            }
        });

        // Add cell editing started event listener
        this.gridApi.addEventListener('cellEditingStarted', (event) => {
        });

        // Add cell editing stopped event listener
        this.gridApi.addEventListener('cellEditingStopped', (event) => {
        });
        
        // State persistence events are now handled in gridOptions
        
        // Restore main grid state after initialization
        setTimeout(() => {
            this.restoreMainGridState();
        }, 500);
        
        // Fallback: Enable state saving after a timeout even if restore fails
        setTimeout(() => {
            if (!this.stateSavingEnabled) {
                this.stateSavingEnabled = true;
            }
        }, 2000);

        // Add keyboard event listener for quick editing and delete
        this.gridApi.addEventListener('keydown', (event) => {
            // Start editing name field when Enter is pressed on a selected row
            if (event.key === 'Enter' && !event.target.classList.contains('ag-cell-edit-input')) {
                const selectedRow = this.gridApi.getSelectedRows()[0];
                if (selectedRow) {
                    // Start editing the name field of the selected row
                    this.gridApi.startEditingCell({
                        rowIndex: this.gridApi.getRowIndex(selectedRow),
                        colKey: 'name'
                    });
                    event.preventDefault();
                }
            }
        });

        // Add cell value changed listener to mark games as modified
        this.gridApi.addEventListener('cellValueChanged', (event) => {
            this.markGameAsModified(event.data);
        });

        // Add double-click listener for editing
        this.gridApi.addEventListener('rowDoubleClicked', (event) => {
            // For double-click, we'll use a simpler approach
            // Check if the last clicked cell was in the video column
            if (this.lastClickedColumn && this.isVideoColumn(this.lastClickedColumn)) {
                this.editGameWithPreviewTab(event.data);
            } else {
                this.editGame(event.data);
            }
        });

        // Track which column was last clicked
        this.gridApi.addEventListener('cellClicked', (event) => {
            if (event.column && event.column.colId) {
                this.lastClickedColumn = event.column.colId;
            }
        });

        // Context menu is handled by onCellContextMenu in gridOptions

        // Add filter event listeners to refresh data and maintain visibility
        this.gridApi.addEventListener('filterChanged', async () => {
            await this.refreshGridData();
            this.ensureGridVisibility();
        });

        this.gridApi.addEventListener('filterModified', () => {
            this.ensureGridVisibility();
        });

        this.gridApi.addEventListener('filterOpened', () => {
            this.ensureGridVisibility();
        });

        this.gridApi.addEventListener('filterClosed', () => {
            this.ensureGridVisibility();
        });

        // Add grid refresh event listener for lazy loading
        this.gridApi.addEventListener('gridReady', () => {
            if (this.thumbnailViewEnabled) {
                setTimeout(() => {
                    this.setupLazyLoading();
                }, 100);
            }
        });
    }

    // Get filtered data based on current grid filters
    getFilteredData() {
        if (!this.gridApi) return this.games;
        
        // Get all active filters from the grid
        const filterModel = this.gridApi.getFilterModel();
        
        // If no filters are active, return all data
        if (!filterModel || Object.keys(filterModel).length === 0) {
            return this.games;
        }
        
        // Apply filters to the data
        return this.games.filter(game => {
            return Object.keys(filterModel).every(field => {
                const filter = filterModel[field];
                if (!filter) return true;
                
                const value = game[field];
                if (value === null || value === undefined) return false;
                
                const stringValue = String(value).toLowerCase();
                
                // Handle different filter types
                if (filter.type === 'contains') {
                    return stringValue.includes(filter.filter.toLowerCase());
                } else if (filter.type === 'equals') {
                    return stringValue === filter.filter.toLowerCase();
                } else if (filter.type === 'startsWith') {
                    return stringValue.startsWith(filter.filter.toLowerCase());
                } else if (filter.type === 'endsWith') {
                    return stringValue.endsWith(filter.filter.toLowerCase());
                }
                
                return true;
            });
        });
    }

    // Get filtered data based on current grid filters
    getFilteredData() {
        if (!this.gridApi) return this.games;
        
        // Get all active filters from the grid
        const filterModel = this.gridApi.getFilterModel();
        
        // If no filters are active, return all data
        if (!filterModel || Object.keys(filterModel).length === 0) {
            return this.games;
        }
        
        // Apply filters to the data
        return this.games.filter(game => {
            return Object.keys(filterModel).every(field => {
                const filter = filterModel[field];
                if (!filter) return true;
                
                const value = game[field];
                if (value === null || value === undefined) return false;
                
                const stringValue = String(value).toLowerCase();
                
                // Handle different filter types
                if (filter.type === 'contains') {
                    return stringValue.includes(filter.filter.toLowerCase());
                } else if (filter.type === 'equals') {
                    return stringValue === filter.filter.toLowerCase();
                } else if (filter.type === 'startsWith') {
                    return stringValue.startsWith(filter.filter.toLowerCase());
                } else if (filter.type === 'endsWith') {
                    return stringValue.endsWith(filter.filter.toLowerCase());
                }
                
                return true;
            });
        });
    }

    // Refresh grid data when filters change
    async refreshGridData() {
        if (this.gridApi) {
            // Check if duplicates filter is active
            if (this.duplicatesFilterActive) {
                // If duplicates filter is active, reapply it
                const duplicateGames = this.findDuplicateGames();
                await this.updateGameGridData(duplicateGames);
            } else {
                // Normal refresh - use all games
            await this.updateGameGridData(this.games);
            }
        }
    }

    // Clear all active filters from the grid
    async clearAllFilters() {
        if (this.gridApi) {
            // Clear all filters
            this.gridApi.setFilterModel(null);
            
            // Refresh the grid data efficiently
            await this.refreshGridData();
            
            // Update the games count display
            this.updateGamesCount();
            
        }
    }

    // Custom cell renderer for media fields - shows 0 or 1
    mediaCellRenderer(params) {
        const value = params.value;
        if (value && value.trim() !== '') {
            return '<span class="badge bg-success">1</span>';
        } else {
            return '<span class="badge bg-secondary">0</span>';
        }
    }

    // Ensure grid visibility during filter operations
    ensureGridVisibility() {
        const gridElement = document.getElementById('gamesGrid');
        if (gridElement) {
            // Only fix if the grid is actually hidden
            if (gridElement.style.display === 'none') {
                gridElement.style.display = 'block';
            }
            
            // Force AG Grid to refresh if needed
            if (this.gridApi) {
                setTimeout(() => {
                    this.gridApi.refreshCells();
                }, 50);
            }
        }
    }

    showContextMenu(event) {
        console.log('showContextMenu called', event);
        
        const game = event.data;
        const selectedGames = this.gridApi.getSelectedRows();
        const isMultipleSelected = selectedGames.length > 1;
        
        const contextMenu = document.createElement('div');
        contextMenu.className = 'dropdown-menu show position-fixed';
        contextMenu.style.cssText = `top: ${event.event.clientY}px; left: ${event.event.clientX}px; z-index: 1000;`;
        
        let menuItems = '';
        
        // Single game operations
        if (!isMultipleSelected) {
            menuItems = `
                <a class="dropdown-item" href="#" onclick="gameManager.editGame(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                    <i class="bi bi-pencil"></i> Edit
                </a>
                <a class="dropdown-item" href="#" onclick="gameManager.scanGameMedia(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                    <i class="bi bi-search"></i> Scan Media
                </a>
                <a class="dropdown-item" href="#" onclick="gameManager.moveRom(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                    <i class="bi bi-folder2-open"></i> Move ROM
                </a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item" href="#" onclick="gameManager.toggleGameHidden(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                    <i class="bi bi-${game.hidden === 'true' ? 'eye' : 'eye-slash'}"></i> ${game.hidden === 'true' ? 'Unhidden' : 'Hide'} Game
                </a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item text-danger" href="#" data-action="delete-game" data-game='${JSON.stringify(game)}'>
                    <i class="bi bi-trash"></i> Delete
                </a>
            `;
        } else {
            // Multiple games selected - show bulk operations
            menuItems = `
                <div class="dropdown-header">Bulk Operations (${selectedGames.length} games)</div>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item" href="#" onclick="gameManager.moveSelectedGames()">
                    <i class="bi bi-folder2-open"></i> Move Selected
                </a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item" href="#" onclick="gameManager.hideSelectedGames()">
                    <i class="bi bi-eye-slash"></i> Hide Selected
                </a>
                <a class="dropdown-item" href="#" onclick="gameManager.showSelectedGames()">
                    <i class="bi bi-eye"></i> Unhide Selected
                </a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item" href="#" data-action="delete-selected-games">
                    <i class="bi bi-trash text-danger"></i> Delete Selected
                </a>
            `;
        }
        
        contextMenu.innerHTML = menuItems;
        
        // Add event delegation for context menu items
        contextMenu.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const action = e.target.closest('[data-action]')?.getAttribute('data-action');
            if (action === 'delete-game') {
                const gameData = e.target.closest('[data-game]')?.getAttribute('data-game');
                if (gameData) {
                    try {
                        const game = JSON.parse(gameData);
                        this.deleteGame(game);
                    } catch (error) {
                        console.error('Error parsing game data:', error);
                    }
                }
            } else if (action === 'delete-selected-games') {
                this.showDeleteConfirmation();
            }
            
            // Remove the context menu
            if (contextMenu.parentNode) {
                contextMenu.remove();
            }
        });
        
        document.body.appendChild(contextMenu);
        
        // Remove context menu when clicking elsewhere
        const removeMenu = () => {
            if (contextMenu.parentNode) {
                contextMenu.remove();
            }
            document.removeEventListener('click', removeMenu);
        };
        
        setTimeout(() => {
            document.addEventListener('click', removeMenu);
        }, 100);
    }

    async editGame(game) {
        this.editingGamePath = game.path; // Store ROM path as identifier
        // Find the game index for reliable identification
        this.editingGameIndex = this.games.findIndex(g => g.path === game.path);
        await this.populateEditModal(game);
        
        const modal = new bootstrap.Modal(document.getElementById('editGameModal'));
        modal.show();
    }

    async toggleGameHidden(game) {
        const newHiddenValue = game.hidden !== 'true';
        await this.updateGamesHidden([game.path], newHiddenValue);
    }

    async hideSelectedGames() {
        const selectedGames = this.gridApi.getSelectedRows();
        if (selectedGames.length === 0) {
            this.showAlert('No games selected', 'warning');
            return;
        }
        
        const romPaths = selectedGames.map(game => game.path);
        await this.updateGamesHidden(romPaths, true);
    }

    async showSelectedGames() {
        const selectedGames = this.gridApi.getSelectedRows();
        if (selectedGames.length === 0) {
            this.showAlert('No games selected', 'warning');
            return;
        }
        
        const romPaths = selectedGames.map(game => game.path);
        await this.updateGamesHidden(romPaths, false);
    }

    async updateGamesHidden(romPaths, hiddenValue) {
        try {
            // Save current filter state before refreshing
            const currentFilterModel = this.gridApi.getFilterModel();
            
            const response = await fetch(`/api/rom-system/${this.currentSystem}/games/update-hidden`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    rom_paths: romPaths,
                    hidden: hiddenValue
                })
            });

            const result = await response.json();

            if (result.success) {
                // Update the local data
                this.games.forEach(game => {
                    if (romPaths.includes(game.path)) {
                        console.log(`Updating game ${game.name}: hidden = ${hiddenValue ? 'true' : 'false'}`);
                        game.hidden = hiddenValue ? 'true' : 'false';
                    }
                });

                // Force update the grid with the new data
                this.gridApi.setGridOption('rowData', [...this.games]);
                
                // Restore filter state after data update
                if (currentFilterModel && Object.keys(currentFilterModel).length > 0) {
                    this.gridApi.setFilterModel(currentFilterModel);
                }
                
                // Force refresh all cells to update styling and row classes
                setTimeout(() => {
                    this.gridApi.refreshCells({ 
                        force: true,
                        suppressFlash: false,
                        rowNodes: undefined
                    });
                    // Also refresh the viewport to ensure row classes are reapplied
                    this.gridApi.redrawRows();
                    
                    // If hidden filter is active, refresh it to show newly hidden games
                    if (this.hiddenFilterActive) {
                        // Force refresh the grid to show all games including newly hidden ones
                        this.gridApi.setGridOption('rowData', [...this.games]);
                    }
                }, 100);
                
                // Show success message
                const action = hiddenValue ? 'hidden' : 'shown';
                this.showAlert(`${result.updated_count} games ${action} successfully`, 'success');
            } else {
                this.showAlert(result.error || 'Failed to update games', 'error');
            }
        } catch (error) {
            console.error('Error updating games hidden status:', error);
            this.showAlert('Failed to update games', 'error');
        }
    }


    async moveRom(game) {
        this.movingGame = game;
        this.movingGames = [game]; // Single game in array for consistency
        await this.showDirectoryExplorer();
    }

    async moveSelectedGames() {
        const selectedGames = this.gridApi.getSelectedRows();
        if (selectedGames.length === 0) {
            this.showAlert('No games selected', 'warning');
            return;
        }

        this.movingGames = selectedGames;
        this.movingGame = selectedGames[0]; // For display purposes
        await this.showDirectoryExplorer();
    }

    async showDirectoryExplorer() {
        // Update modal with game information
        if (this.movingGames.length === 1) {
            document.getElementById('movingGameName').textContent = this.movingGame.name;
        } else {
            document.getElementById('movingGameName').textContent = `${this.movingGames.length} games selected`;
        }
        document.getElementById('currentSystemName').textContent = this.currentSystem;
        
        // Create and show the directory explorer modal
        const modal = new bootstrap.Modal(document.getElementById('directoryExplorerModal'));
        modal.show();
        
        // Load the root directory of the current system
        await this.loadDirectoryContents('/');
    }

    async loadDirectoryContents(path) {
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/explore-directory?path=${encodeURIComponent(path)}`);
            const result = await response.json();
            
            if (result.success) {
                this.displayDirectoryContents(result.contents, path);
            } else {
                this.showAlert(result.error || 'Failed to load directory contents', 'error');
            }
        } catch (error) {
            console.error('Error loading directory contents:', error);
            this.showAlert('Failed to load directory contents', 'error');
        }
    }

    displayDirectoryContents(contents, currentPath) {
        const container = document.getElementById('directoryContents');
        container.innerHTML = '';
        
        // Add breadcrumb navigation
        const breadcrumb = document.createElement('nav');
        breadcrumb.setAttribute('aria-label', 'breadcrumb');
        breadcrumb.innerHTML = this.createBreadcrumb(currentPath);
        container.appendChild(breadcrumb);
        
        // Add current path display
        const pathDisplay = document.createElement('div');
        pathDisplay.className = 'alert alert-info';
        pathDisplay.innerHTML = `<strong>Current Path:</strong> ${currentPath}`;
        container.appendChild(pathDisplay);
        
        // Add create directory button
        const createDirBtn = document.createElement('button');
        createDirBtn.className = 'btn btn-outline-primary mb-3';
        createDirBtn.innerHTML = '<i class="bi bi-folder-plus"></i> Create New Directory';
        createDirBtn.onclick = () => this.showCreateDirectoryDialog(currentPath);
        container.appendChild(createDirBtn);
        
        // Add directory contents
        const table = document.createElement('table');
        table.className = 'table table-hover';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Directory Name</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="directoryTableBody">
            </tbody>
        `;
        container.appendChild(table);
        
        const tbody = document.getElementById('directoryTableBody');
        
        // Add parent directory entry if not at root
        if (currentPath !== '/') {
            const parentRow = document.createElement('tr');
            parentRow.innerHTML = `
                <td><i class="bi bi-arrow-up"></i> ..</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="gameManager.loadDirectoryContents('${this.getParentPath(currentPath)}')">Open</button>
                    <button class="btn btn-sm btn-outline-success" onclick="gameManager.selectMoveDestination('${this.getParentPath(currentPath)}')">Select</button>
                </td>
            `;
            tbody.appendChild(parentRow);
        }
        
        // Add root directory selection if not already at root
        if (currentPath !== '/') {
            const rootRow = document.createElement('tr');
            rootRow.innerHTML = `
                <td><i class="bi bi-house"></i> Root Directory</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="gameManager.loadDirectoryContents('/')">Open</button>
                    <button class="btn btn-sm btn-outline-success" onclick="gameManager.selectMoveDestination('/')">Select</button>
                </td>
            `;
            tbody.appendChild(rootRow);
        } else {
            // If we're at root, add a "Select Root" option
            const rootRow = document.createElement('tr');
            rootRow.innerHTML = `
                <td><i class="bi bi-house"></i> Root Directory (Current)</td>
                <td>
                    <button class="btn btn-sm btn-outline-success" onclick="gameManager.selectMoveDestination('/')">Select Root</button>
                </td>
            `;
            tbody.appendChild(rootRow);
        }
        
        // Add directories (filter out directories with file extensions)
        contents.directories.forEach(dir => {
            // Check if directory name has a file extension
            const hasExtension = /\.[a-zA-Z0-9]+$/.test(dir.name);
            
            if (!hasExtension) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><i class="bi bi-folder"></i> ${dir.name}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary me-2" onclick="gameManager.loadDirectoryContents('${dir.path}')">Open</button>
                        <button class="btn btn-sm btn-outline-success" onclick="gameManager.selectMoveDestination('${dir.path}')">Select</button>
                    </td>
                `;
                tbody.appendChild(row);
            }
        });
        
        // Files are not displayed - only directories for ROM moving
    }

    createBreadcrumb(currentPath) {
        const parts = currentPath.split('/').filter(part => part);
        let breadcrumb = '<ol class="breadcrumb">';
        breadcrumb += '<li class="breadcrumb-item"><a href="#" onclick="gameManager.loadDirectoryContents(\'/\')">Root</a></li>';
        
        let path = '';
        parts.forEach(part => {
            path += '/' + part;
            breadcrumb += `<li class="breadcrumb-item"><a href="#" onclick="gameManager.loadDirectoryContents('${path}')">${part}</a></li>`;
        });
        
        breadcrumb += '</ol>';
        return breadcrumb;
    }

    getParentPath(currentPath) {
        const parts = currentPath.split('/').filter(part => part);
        if (parts.length <= 1) return '/';
        return '/' + parts.slice(0, -1).join('/');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async showCreateDirectoryDialog(currentPath) {
        const name = prompt('Enter directory name:');
        if (name && name.trim()) {
            await this.createDirectory(currentPath, name.trim());
        }
    }

    async createDirectory(currentPath, name) {
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/create-directory`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: currentPath,
                    name: name
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert('Directory created successfully', 'success');
                await this.loadDirectoryContents(currentPath);
            } else {
                this.showAlert(result.error || 'Failed to create directory', 'error');
            }
        } catch (error) {
            console.error('Error creating directory:', error);
            this.showAlert('Failed to create directory', 'error');
        }
    }

    async selectMoveDestination(destinationPath) {
        if (!this.movingGames || this.movingGames.length === 0) return;
        
        // Format the destination path for display
        let displayPath = destinationPath;
        if (destinationPath === '/') {
            displayPath = 'Root Directory';
        }
        
        let confirmMessage;
        if (this.movingGames.length === 1) {
            confirmMessage = `Move "${this.movingGames[0].name}" to "${displayPath}"?`;
        } else {
            confirmMessage = `Move ${this.movingGames.length} games to "${displayPath}"?`;
        }
        
        if (confirm(confirmMessage)) {
            await this.performBulkMove(this.movingGames, destinationPath);
        }
    }

    async performMove(game, destinationPath) {
        await this.performBulkMove([game], destinationPath);
    }

    async performBulkMove(games, destinationPath) {
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/move-roms-bulk`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    games: games.map(game => ({ path: game.path, name: game.name })),
                    destination_path: destinationPath
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                const gameCount = games.length;
                this.showAlert(`${gameCount} game${gameCount > 1 ? 's' : ''} moved successfully`, 'success');
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('directoryExplorerModal'));
                modal.hide();
                
                // Refresh the grid to show updated paths
                console.log(`Refreshing grid after moving ${gameCount} ROMs...`);
                await this.loadRomSystem(this.currentSystem);
                console.log('Grid refreshed successfully');
            } else {
                this.showAlert(result.error || 'Failed to move ROMs', 'error');
            }
        } catch (error) {
            console.error('Error moving ROMs:', error);
            this.showAlert('Failed to move ROMs', 'error');
        }
    }

    async editGameWithPreviewTab(game) {
        this.editingGamePath = game.path; // Store ROM path as identifier
        // Find the game index for reliable identification
        this.editingGameIndex = this.games.findIndex(g => g.path === game.path);
        await this.populateEditModal(game);
        
        const modal = new bootstrap.Modal(document.getElementById('editGameModal'));
        modal.show();
        
        // Wait for modal to be fully visible, then switch to preview tab
        setTimeout(() => {
            this.switchToPreviewTab();
        }, 100);
    }
    async populateEditModal(game) {
        console.log('populateEditModal called with game:', game);
        // Clear all fields first to ensure no residual data
        document.getElementById('editName').value = '';
        document.getElementById('editPath').value = '';
        document.getElementById('editDescription').value = '';
        document.getElementById('editGenre').value = '';
        document.getElementById('editDeveloper').value = '';
        document.getElementById('editPublisher').value = '';
        document.getElementById('editRating').value = '';
        document.getElementById('editPlayers').value = '';
        document.getElementById('editReleasedate').value = '';
        document.getElementById('editLaunchboxId').value = '';
        document.getElementById('editIgdbId').value = '';
        document.getElementById('editScreenscraperId').value = '';
        document.getElementById('editSteamId').value = '';
        document.getElementById('editSteamgridid').value = '';
        document.getElementById('editYoutubeurl').value = '';
        
        // Clear favorite and kidgame fields
        const favoriteIcon = document.getElementById('editFavorite');
        favoriteIcon.className = 'bi bi-star text-muted';
        favoriteIcon.style.fontSize = '1.5rem';
        favoriteIcon.style.cursor = 'pointer';
        favoriteIcon.style.transition = 'all 0.2s ease';
        favoriteIcon.title = 'Click to add to favorites';
        
        const kidgameIcon = document.getElementById('editKidgame');
        kidgameIcon.className = 'bi bi-emoji-smile text-muted';
        kidgameIcon.style.fontSize = '1.5rem';
        kidgameIcon.style.cursor = 'pointer';
        kidgameIcon.style.transition = 'all 0.2s ease';
        kidgameIcon.title = 'Click to mark as kid game';
        
        // Now populate with game data
        document.getElementById('editName').value = game.name || '';
        document.getElementById('editPath').value = game.path || '';
        document.getElementById('editDescription').value = game.desc || '';
        document.getElementById('editGenre').value = game.genre || '';
        document.getElementById('editDeveloper').value = game.developer || '';
        document.getElementById('editPublisher').value = game.publisher || '';
        document.getElementById('editRating').value = game.rating || '';
        document.getElementById('editPlayers').value = game.players || '';
        
        // Handle release date with calendar widget conversion
        let releaseDateValue = game.releasedate || '';
        if (releaseDateValue) {
            // Convert to ISO 8601 format if not already in correct format
            releaseDateValue = this.convertReleaseDateToISO8601(releaseDateValue);
            // Convert to YYYY-MM-DD format for date input
            releaseDateValue = this.convertISO8601ToDateInput(releaseDateValue);
        }
        // Set the date value with a small delay to ensure the modal is fully rendered
        setTimeout(() => {
            const dateInputElement = document.getElementById('editReleasedate');
            if (dateInputElement) {
                dateInputElement.value = releaseDateValue;
            }
        }, 100);
        
        document.getElementById('editLaunchboxId').value = game.launchboxid || '';
        document.getElementById('editIgdbId').value = game.igdbid || '';
        document.getElementById('editScreenscraperId').value = game.screenscraperid || '';
        document.getElementById('editSteamId').value = game.steamid || '';
        document.getElementById('editSteamgridid').value = game.steamgridid || '';
        document.getElementById('editMobygamesid').value = game.mobygamesid || '';
        document.getElementById('editYoutubeurl').value = game.youtubeurl || '';
        
        // Populate favorite and kidgame fields
        if (game.favorite === true || game.favorite === 'true') {
            favoriteIcon.className = 'bi bi-star-fill text-warning';
            favoriteIcon.style.fontSize = '1.5rem';
            favoriteIcon.style.cursor = 'pointer';
            favoriteIcon.style.transition = 'all 0.2s ease';
            favoriteIcon.title = 'Click to remove from favorites';
        }
        // Set kidgame smiley icon state
        if (game.kidgame === true || game.kidgame === 'true') {
            kidgameIcon.className = 'bi bi-emoji-smile-fill text-success';
            kidgameIcon.style.fontSize = '1.5rem';
            kidgameIcon.style.cursor = 'pointer';
            kidgameIcon.style.transition = 'all 0.2s ease';
            kidgameIcon.title = 'Click to remove kid game mark';
        }
        
        // Populate the media tab with the same media display as the preview panel
        await this.showEditGameMedia(game);
        
        // Populate the video preview tab
        this.showEditGameVideo(game);
        
        // Initialize YouTube download functionality
        this.initializeYouTubeDownload(game);
        
        // Ensure the first tab is active and visible
        this.initializeEditModalTabs();
        
        // Initialize Find Best Match button for edit modal
        this.initializeEditModalFindBestMatch();
        
        // Initialize IGDB search button for edit modal
        this.initializeEditModalIgdbSearch();
        
        // Initialize ScreenScraper search button for edit modal
        this.initializeEditModalScreenscraperSearch();
        
        // Initialize Steam search button for edit modal
        this.initializeEditModalSteamSearch();
        
        // Initialize SteamGridDB search button for edit modal
        this.initializeEditModalSteamgridSearch();
        
        // Initialize MobyGames search button for edit modal
        this.initializeEditModalMobygamesSearch();
        
        // Initialize YouTube preview button for edit modal
        this.initializeEditModalYoutubePreview();
        
        // Initialize delete video button
        this.initializeDeleteVideoButton(game);
        
        // Initialize manual crop button
        this.initializeManualCropButton(game);
    }
    initializeEditModalTabs() {
        // Ensure the first tab is active and visible
        const firstTab = document.getElementById('game-info-tab');
        const firstTabContent = document.getElementById('game-info-content');
        
        if (firstTab && firstTabContent) {
            // Remove active class from all tabs and content
            document.querySelectorAll('#editGameModalTabs .nav-link').forEach(tab => {
                tab.classList.remove('active');
                tab.setAttribute('aria-selected', 'false');
            });
            document.querySelectorAll('#editGameModalTabContent .tab-pane').forEach(content => {
                content.classList.remove('show', 'active');
            });
            
            // Activate the first tab
            firstTab.classList.add('active');
            firstTab.setAttribute('aria-selected', 'true');
            firstTabContent.classList.add('show', 'active');
        }
        
        // Initialize Find Best Match button
        this.initializeFindBestMatchButton();
        
        // Add release date validation
        const releasedateField = document.getElementById('editReleasedate');
        if (releasedateField) {
            releasedateField.addEventListener('blur', () => {
                this.validateReleaseDate(releasedateField);
            });
        }
    }
    
    validateReleaseDate(field) {
        const value = field.value.trim();
        if (!value) {
            // Clear any previous validation state
            field.classList.remove('is-valid', 'is-invalid');
            return;
        }
        
        // Check if the value matches the expected date input format (YYYY-MM-DD)
        const dateInputPattern = /^\d{4}-\d{2}-\d{2}$/;
        if (dateInputPattern.test(value)) {
            // Additional validation: check if it's a valid date
            const date = new Date(value + 'T00:00:00');
            if (!isNaN(date.getTime())) {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');
            } else {
                field.classList.remove('is-valid');
                field.classList.add('is-invalid');
                this.showAlert('Please select a valid date', 'warning');
            }
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            this.showAlert('Please select a valid date using the calendar widget', 'warning');
        }
    }
    
    convertReleaseDateToISO8601(dateInput) {
        /**
         * Convert various date formats to ISO 8601 format (YYYYMMDDTHHMMSS)
         * This is a JavaScript implementation of the Python format_releasedate_to_iso8601 function
         */
        if (!dateInput || dateInput === '') {
            return '';
        }
        
        // If already in correct format, return as-is
        const iso8601Pattern = /^\d{8}T\d{6}$/;
        if (iso8601Pattern.test(dateInput)) {
            return dateInput;
        }
        
        try {
            // Handle timestamps (numbers)
            if (!isNaN(dateInput) && !isNaN(parseFloat(dateInput))) {
                const timestamp = parseFloat(dateInput);
                const date = new Date(timestamp * 1000); // Convert to milliseconds
                return this.formatDateToISO8601(date);
            }
            
            // Handle various string formats
            const dateStr = dateInput.toString().trim();
            
            // If already in YYYYMMDD format, add time
            if (/^\d{8}$/.test(dateStr)) {
                return dateStr + 'T000000';
            }
            
            // Try to parse various date formats
            const formats = [
                // ISO formats
                /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/,  // 1990-02-01T12:30:45
                /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.\d+/,  // 1990-02-01T12:30:45.123456
                /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z/,  // 1990-02-01T12:30:45Z
                /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\+\d{2}:\d{2}/,  // 1990-02-01T12:30:45+00:00
                
                // Date only formats
                /^(\d{4})-(\d{2})-(\d{2})$/,  // 1990-02-01
                /^(\d{4})\/(\d{2})\/(\d{2})$/,  // 1990/02/01
                /^(\d{2})\/(\d{2})\/(\d{4})$/,  // 02/01/1990
                /^(\d{2})\/(\d{2})\/(\d{4})$/,  // 01/02/1990
                
                // Year-month only
                /^(\d{4})-(\d{2})$/,  // 1990-02
                
                // Year only
                /^(\d{4})$/,  // 1990
                
                // Steam format
                /^(\d{1,2})\s+(\w{3}),\s+(\d{4})$/,  // 01 Feb, 1990
            ];
            
            for (const format of formats) {
                const match = dateStr.match(format);
                if (match) {
                    let year, month, day, hour = 0, minute = 0, second = 0;
                    
                    if (format.source.includes('T')) {
                        // ISO format with time
                        [, year, month, day, hour, minute, second] = match;
                    } else if (format.source.includes('\\w{3}')) {
                        // Steam format: 01 Feb, 1990
                        [, day, monthName, year] = match;
                        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                        month = (monthNames.indexOf(monthName) + 1).toString().padStart(2, '0');
                        day = day.padStart(2, '0');
                    } else if (format.source.includes('\\d{4}')) {
                        // Various date formats
                        if (format.source.includes('\\d{4}-\\d{2}-\\d{2}')) {
                            // YYYY-MM-DD
                            [, year, month, day] = match;
                        } else if (format.source.includes('\\d{4}/\\d{2}/\\d{2}')) {
                            // YYYY/MM/DD
                            [, year, month, day] = match;
                        } else if (format.source.includes('\\d{2}/\\d{2}/\\d{4}')) {
                            // MM/DD/YYYY or DD/MM/YYYY (assume MM/DD/YYYY)
                            [, month, day, year] = match;
                        } else if (format.source.includes('\\d{4}-\\d{2}')) {
                            // YYYY-MM
                            [, year, month] = match;
                            day = '01';
                        } else if (format.source.includes('^\\d{4}$')) {
                            // YYYY
                            [, year] = match;
                            month = '01';
                            day = '01';
                        }
                    }
                    
                    if (year) {
                        // Ensure proper padding
                        year = year.padStart(4, '0');
                        month = (month || '01').padStart(2, '0');
                        day = (day || '01').padStart(2, '0');
                        hour = (hour || '00').padStart(2, '0');
                        minute = (minute || '00').padStart(2, '0');
                        second = (second || '00').padStart(2, '0');
                        
                        return `${year}${month}${day}T${hour}${minute}${second}`;
                    }
                }
            }
            
            // If no format matched, try to parse as a general date
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                return this.formatDateToISO8601(date);
            }
            
        } catch (error) {
            console.warn('Error converting release date:', error);
        }
        
        // If all parsing attempts failed, return the original value
        return dateInput;
    }
    
    formatDateToISO8601(date) {
        /**
         * Format a JavaScript Date object to ISO 8601 format (YYYYMMDDTHHMMSS)
         */
        const year = date.getFullYear().toString().padStart(4, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        const hour = date.getHours().toString().padStart(2, '0');
        const minute = date.getMinutes().toString().padStart(2, '0');
        const second = date.getSeconds().toString().padStart(2, '0');
        
        return `${year}${month}${day}T${hour}${minute}${second}`;
    }
    
    convertISO8601ToDateInput(iso8601Date) {
        /**
         * Convert ISO 8601 format (YYYYMMDDTHHMMSS) to YYYY-MM-DD for date input
         */
        if (!iso8601Date || iso8601Date === '') {
            return '';
        }
        
        // Extract date part (YYYYMMDD) from YYYYMMDDTHHMMSS
        const datePart = iso8601Date.substring(0, 8);
        if (datePart.length === 8) {
            const year = datePart.substring(0, 4);
            const month = datePart.substring(4, 6);
            const day = datePart.substring(6, 8);
            return `${year}-${month}-${day}`;
        }
        
        return '';
    }
    
    convertDateInputToISO8601(dateInputValue) {
        /**
         * Convert YYYY-MM-DD from date input to ISO 8601 format (YYYYMMDDTHHMMSS)
         */
        if (!dateInputValue || dateInputValue === '') {
            return '';
        }
        
        // Date input provides YYYY-MM-DD format
        const date = new Date(dateInputValue + 'T00:00:00');
        if (!isNaN(date.getTime())) {
            return this.formatDateToISO8601(date);
        }
        
        return '';
    }
    
    initializeFindBestMatchButton() {
        const findBestMatchBtn = document.getElementById('findBestMatchBtn');
        if (findBestMatchBtn) {
            // Remove any existing event listeners to prevent duplicates
            const newBtn = findBestMatchBtn.cloneNode(true);
            findBestMatchBtn.parentNode.replaceChild(newBtn, findBestMatchBtn);
            
            // Add the event listener to the new button
            newBtn.addEventListener('click', () => {
                const gameName = document.getElementById('editName').value;
                if (gameName && gameName.trim()) {
                    // Get current game path for reliable identification
                    const currentGame = this.getCurrentEditingGame();
                    const gamePath = currentGame ? currentGame.path : null;
                    this.showPartialMatches(gameName, null, 'gameEdit', gamePath);
                } else {
                    this.showAlert('Please enter a game name first', 'warning');
                }
            });
        }
    }

    switchToPreviewTab() {
        // Deactivate all tabs
        document.querySelectorAll('#editGameModalTabs .nav-link').forEach(tab => {
            tab.classList.remove('active');
            tab.setAttribute('aria-selected', 'false');
        });
        document.querySelectorAll('#editGameModalTabContent .tab-pane').forEach(content => {
            content.classList.remove('show', 'active');
        });
        
        // Activate the video preview tab
        const videoTab = document.getElementById('game-video-tab');
        const videoContent = document.getElementById('game-video-content');
        
        if (videoTab && videoContent) {
            videoTab.classList.add('active');
            videoTab.setAttribute('aria-selected', 'true');
            videoContent.classList.add('show', 'active');
            
            // Populate the video content immediately
            if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
                const currentGame = this.games[this.editingGameIndex];
                this.showEditGameVideo(currentGame);
            }
        }
    }

    switchToTaskManagementTab() {
        // Switch to the main task management tab in the combined panel
        const taskManagementTab = document.getElementById('task-management-tab');
        if (taskManagementTab) {
            // Trigger a click on the task management tab
            taskManagementTab.click();
        }
    }

    isVideoColumn(columnId) {
        // Check if the column is a video-related column
        return columnId === 'video' || columnId === 'video_thumb';
    }

    async getMediaFieldsFromConfig() {
        // Use cached fields if available
        if (this.mediaFieldsCache && Array.isArray(this.mediaFieldsCache)) {
            return this.mediaFieldsCache;
        }
        
        // Fetch from API
        try {
            const response = await fetch('/api/media-fields', {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for media fields data
                }
            });
            
            if (!response.ok) {
                throw new Error(`API call failed with status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && Array.isArray(data.fields)) {
                this.mediaFieldsCache = data.fields;
                return this.mediaFieldsCache;
            } else {
                throw new Error(data.error || 'Invalid response format');
            }
        } catch (error) {
            // Fallback to default media fields if API call fails
            const fallbackFields = ['marquee', 'boxart', 'image', 'cartridge', 'fanart', 'titleshot', 'boxback', 'thumbnail'];
            this.mediaFieldsCache = fallbackFields;
            return this.mediaFieldsCache;
        }
    }

    async getMediaMappings() {
        // Use cached mappings if available
        if (this.mediaMappingsCache) {
            return this.mediaMappingsCache;
        }
        
        // If not cached, fetch from API
        try {
            const response = await fetch('/api/media-mappings', {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for media mappings data
                }
            });
            const data = await response.json();
            
            if (data.success) {
                this.mediaMappingsCache = data.mappings;
                return this.mediaMappingsCache;
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            throw error;
        }
    }

    async initializeMediaMappingsCache() {
        // Fetch media mappings once when the application starts
        try {
            const response = await fetch('/api/media-mappings', {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for media mappings data
                }
            });
            const data = await response.json();
            
            if (data.success) {
                this.mediaMappingsCache = data.mappings;
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            throw error;
        }
    }
    
    async generateDynamicMediaColumns() {
        // Get media fields dynamically from config.json (excluding video since it's handled as a static column)
        let mediaFields;
        try {
            mediaFields = await this.getMediaFieldsFromConfig();
        } catch (error) {
            // Fallback to default media fields if API fails
            mediaFields = ['marquee', 'boxart', 'image', 'cartridge', 'fanart', 'titleshot', 'manual', 'boxback', 'thumbnail'];
        }
        
        // Ensure mediaFields is an array
        if (!Array.isArray(mediaFields)) {
            mediaFields = ['marquee', 'boxart', 'image', 'cartridge', 'fanart', 'titleshot', 'manual', 'boxback', 'thumbnail'];
        }
        
        // Generate column definitions for each media type
        const mediaColumns = [];
        
        for (const fieldName of mediaFields) {
            // Use the media field name as header
            const headerName = fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
            
            mediaColumns.push({
                field: fieldName,
                headerName: headerName,
                editable: false,
                sortable: true,
                filter: true,
                resizable: true,
                flex: 1,
                cellRenderer: this.mediaCellRenderer
            });
        }
        
        return mediaColumns;
    }

    async showEditGameMedia(game) {
        const mediaContent = document.getElementById('editGameMediaContent');
        if (!mediaContent) return;
        
        // Clear existing content and media selection
        mediaContent.innerHTML = '';
        this.clearMediaSelection();
        
        // Get media fields from config.json mappings (excluding video)
        const mediaFields = await this.getMediaFieldsFromConfig();
        
        mediaFields.forEach(field => {
            const mediaItem = document.createElement('div');
            mediaItem.className = 'media-preview-item';
            mediaItem.style.cssText = 'width: calc(20% - 6.4px); min-width: 180px; height: 200px; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #dee2e6; border-radius: 8px; background-color: #a1a1a1; transition: all 0.2s ease;';
            
            if (game[field] && game[field].trim()) {
                // Display actual media file
                let imagePath = game[field];
                if (imagePath && !imagePath.startsWith('roms/')) {
                    imagePath = `roms/${this.currentSystem}/${imagePath}`;
                }
                
                if (imagePath.toLowerCase().endsWith('.pdf')) {
                    // PDF file - show PDF logo
                    mediaItem.innerHTML = `
                        <div class="media-placeholder" style="width: calc(100% - 20px); height: 140px; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 2px dashed #dee2e6; border-radius: 4px; background-color: #a1a1a1;" ondblclick="if (!gameManager.uploadInProgress) { gameManager.uploadMediaForGame(gameManager.games.find(g => g.id === ${game.id}), '${field}'); } else { gameManager.showAlert('Upload in progress. Please wait...', 'warning'); }" onclick="gameManager.selectEditModalMediaItem(this, '${field}', gameManager.games.find(g => g.id === ${game.id}), '${game[field]}')" title="PDF Document: ${game[field]}\nDouble-click to upload new media\nClick to select for deletion">
                            <i class="bi bi-file-earmark-pdf" style="font-size: 3rem; color: #dc3545; margin-bottom: 0.5rem;"></i>
                            <small style="color: #6c757d; text-align: center;">PDF Document</small>
                        </div>
                        <small class="d-block text-center mt-1" style="font-size: 0.7rem; color: #6c757d;">${field}</small>
                    `;
                } else {
                    // Regular image file
                    const img = document.createElement('img');
                    // Add cache-busting parameter to avoid stale cached images
                    const urlPath = imagePath.startsWith('/') ? imagePath : `/${imagePath}`;
                    const cacheSep = urlPath.includes('?') ? '&' : '?';
                    img.src = `${urlPath}${cacheSep}v=${Date.now()}`;
                    img.alt = `${field} for ${game.name}`;
                    img.title = `${field}: ${game[field]}\nDouble-click to upload new media\nClick to select for deletion\nRight-click for rotate menu`;
                    img.style.cssText = 'width: calc(100% - 20px); height: 140px; object-fit: contain; cursor: pointer; border-radius: 4px;';
                    img.oncontextmenu = (e) => this.showImageContextMenu(e, mediaItem, game, field);
                    img.ondblclick = () => {
                        if (!this.uploadInProgress) {
                            this.uploadMediaForGame(game, field);
                        } else {
                            this.showAlert('Upload in progress. Please wait...', 'warning');
                        }
                    };
                    img.onclick = () => this.selectEditModalMediaItem(mediaItem, field, game, game[field]);
                    img.onerror = () => {
                        // If image fails to load, show placeholder
                        mediaItem.innerHTML = `
                            <div class="media-placeholder" style="width: calc(100% - 20px); height: 140px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 2px dashed #dee2e6; border-radius: 4px; background-color: #a1a1a1;" ondblclick="if (!gameManager.uploadInProgress) { gameManager.uploadMediaForGame(gameManager.games.find(g => g.id === ${game.id}), '${field}'); } else { gameManager.showAlert('Upload in progress. Please wait...', 'warning'); }" title="Double-click to upload media">
                                <div style="text-align: center; color: #6c757d;">
                                    <i class="bi bi-image" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                                    Double-click<br>to upload
                                </div>
                            </div>
                            <small class="d-block text-center mt-1" style="font-size: 0.7rem; color: #6c757d;">${field}</small>
                        `;
                    };
                    mediaItem.appendChild(img);
                }
                
                // Filename display removed - no longer showing ROM path text under game image
                
                // Add field label
                const fieldLabel = document.createElement('small');
                fieldLabel.className = 'd-block text-center mt-1';
                fieldLabel.textContent = field;
                fieldLabel.style.cssText = 'font-size: 0.7rem; color: #6c757d;';
                mediaItem.appendChild(fieldLabel);
                
                // Add button container
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'd-flex gap-1 mt-1';
                buttonContainer.style.cssText = 'justify-content: center;';
                
                // Add multiscraper download button
                const multiscraperBtn = document.createElement('button');
                multiscraperBtn.className = 'btn btn-outline-success btn-sm';
                multiscraperBtn.style.cssText = 'font-size: 0.6rem; padding: 2px 6px;';
                multiscraperBtn.innerHTML = '<i class="bi bi-search"></i>';
                multiscraperBtn.title = 'Multiscraper Download';
                multiscraperBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.openMultiscraperMediaModal(game, field);
                };
                buttonContainer.appendChild(multiscraperBtn);
                
                // Add LaunchBox download button
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'btn btn-outline-primary btn-sm';
                downloadBtn.style.cssText = 'font-size: 0.6rem; padding: 2px 6px;';
                downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
                downloadBtn.title = 'Download from LaunchBox';
                downloadBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.openLaunchBoxMediaModal(game, field);
                };
                buttonContainer.appendChild(downloadBtn);
                
                mediaItem.appendChild(buttonContainer);
            } else {
                // Display placeholder for missing media
                mediaItem.innerHTML = `
                    <div class="media-placeholder" style="width: calc(100% - 20px); height: 140px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 2px dashed #dee2e6; border-radius: 4px; background-color: #a1a1a1;" ondblclick="if (!gameManager.uploadInProgress) { gameManager.uploadMediaForGame(gameManager.games.find(g => g.id === ${game.id}), '${field}'); } else { gameManager.showAlert('Upload in progress. Please wait...', 'warning'); }" title="Double-click to upload media">
                        <div style="text-align: center; color: #6c757d;">
                            <i class="bi bi-image" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                            Double-click<br>to upload
                        </div>
                    </div>
                    <small class="d-block text-center mt-1" style="font-size: 0.7rem; color: #6c757d;">${field}</small>
                    <div class="d-flex gap-1 mt-1" style="justify-content: center;">
                        <button class="btn btn-outline-success btn-sm" style="font-size: 0.6rem; padding: 2px 6px;" title="Multiscraper Download" onclick="gameManager.openMultiscraperMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                            <i class="bi bi-search"></i>
                        </button>
                        <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 2px 6px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                            <i class="bi bi-download"></i>
                        </button>
                    </div>
                `;
            }
            
            mediaContent.appendChild(mediaItem);
        });
    }
    
    async openLaunchBoxMediaModal(game, mediaType) {
        // Set modal title and game info
        document.getElementById('launchboxMediaGameName').textContent = game.name;
        document.getElementById('launchboxMediaType').textContent = mediaType;
        
        // Show progress
        const progressDiv = document.getElementById('launchboxMediaProgress');
        progressDiv.style.display = 'block';
        progressDiv.textContent = 'Loading available media from LaunchBox...';
        
        // Clear content
        const contentDiv = document.getElementById('launchboxMediaContent');
        contentDiv.innerHTML = '';
        
        // Show modal
        const modalElement = document.getElementById('launchboxMediaModal');
        const modal = new bootstrap.Modal(modalElement);
        
        // Add event listener for modal close to refresh media preview
        const handleModalClose = () => {
            if (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path === game.path) {
                // Update the currentMediaPreviewGame with the fresh data from the grid
                const freshGame = this.games.find(g => g.path === game.path);
                if (freshGame) {
                    this.currentMediaPreviewGame = freshGame;
                    this.showMediaPreview(this.currentMediaPreviewGame);
                }
            }
            // Remove the event listener to prevent duplicates
            modalElement.removeEventListener('hidden.bs.modal', handleModalClose);
        };
        
        modalElement.addEventListener('hidden.bs.modal', handleModalClose);
        modal.show();
        
        try {
            // Fetch available media from LaunchBox
            const response = await fetch(`/api/launchbox-media/${game.launchboxid}/${mediaType}`, {
                credentials: 'include'
            });
            if (!response.ok) {
                // Try to get the error details from the response
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage += ` - ${errorData.error}`;
                    }
                } catch (e) {
                    // If we can't parse the response as JSON, just use the status text
                    errorMessage += ` - ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            
            if (data.success && data.media && data.media.length > 0) {
                // Display available media options
                this.displayLaunchBoxMediaOptions(data.media, game, mediaType);
                progressDiv.style.display = 'none';
            } else {
                contentDiv.innerHTML = '<div class="col-12"><div class="alert alert-info">No media available for this game and type in LaunchBox database.</div></div>';
                progressDiv.style.display = 'none';
            }
        } catch (error) {
            // Extract just the error message without the HTTP status prefix
            let errorMessage = error.message;
            if (errorMessage.includes('HTTP error! status: 404 - ')) {
                errorMessage = errorMessage.replace('HTTP error! status: 404 - ', '');
            }
            contentDiv.innerHTML = '<div class="col-12"><div class="alert alert-danger">' + errorMessage + '</div></div>';
            progressDiv.style.display = 'none';
        }
    }
    
    async openMultiscraperMediaModal(game, mediaType) {
        // Set modal title and game info
        document.getElementById('multiscraperMediaGameName').textContent = game.name;
        document.getElementById('multiscraperMediaType').textContent = mediaType;
        
        // Show progress
        const progressDiv = document.getElementById('multiscraperMediaProgress');
        progressDiv.style.display = 'block';
        progressDiv.textContent = 'Searching for media from multiple sources...';
        
        // Clear content
        const contentDiv = document.getElementById('multiscraperMediaContent');
        contentDiv.innerHTML = '';
        
        // Show modal
        const modalElement = document.getElementById('multiscraperMediaModal');
        const modal = new bootstrap.Modal(modalElement);
        
        // Add event listener for modal close to refresh media preview
        const handleModalClose = () => {
            if (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path === game.path) {
                // Update the currentMediaPreviewGame with the fresh data from the grid
                const freshGame = this.games.find(g => g.path === game.path);
                if (freshGame) {
                    this.currentMediaPreviewGame = freshGame;
                    this.showMediaPreview(this.currentMediaPreviewGame);
                }
            }
            // Remove the event listener to prevent duplicates
            modalElement.removeEventListener('hidden.bs.modal', handleModalClose);
        };
        
        modalElement.addEventListener('hidden.bs.modal', handleModalClose);
        modal.show();
        
        try {
            // Perform multiscraper search for the specific media type
            const response = await fetch('/api/multiscraper-search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    game_name: game.name,
                    media_type: mediaType,
                    system_name: this.currentSystem
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                // Display available media options from multiple sources
                this.displayMultiscraperMediaOptions(data.results, game, mediaType);
                progressDiv.style.display = 'none';
            } else {
                contentDiv.innerHTML = '<div class="col-12"><div class="alert alert-info">No media found for this game and type from any source.</div></div>';
                progressDiv.style.display = 'none';
            }
        } catch (error) {
            contentDiv.innerHTML = '<div class="col-12"><div class="alert alert-danger">Error searching for media: ' + error.message + '</div></div>';
            progressDiv.style.display = 'none';
        }
    }
    
    displayMultiscraperMediaOptions(mediaResults, game, mediaType) {
        const contentDiv = document.getElementById('multiscraperMediaContent');
        contentDiv.innerHTML = '';
        
        mediaResults.forEach((result, index) => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4 mb-3';
            
            const card = document.createElement('div');
            card.className = 'card h-100';
            card.style.cursor = 'pointer';
            
            const img = document.createElement('img');
            img.className = 'card-img-top';
            img.style.height = '300px';
            img.style.objectFit = 'contain';
            img.style.backgroundColor = '#f8f9fa';
            img.src = result.url;
            img.alt = `${mediaType} from ${result.source}`;
            img.onerror = () => {
                img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg==';
            };
            
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body d-flex flex-column';
            
            const title = document.createElement('h6');
            title.className = 'card-title';
            title.textContent = `${result.source} - ${mediaType}`;
            
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-primary btn-sm mt-auto';
            downloadBtn.textContent = 'Download';
            downloadBtn.onclick = (e) => {
                e.stopPropagation();
                this.downloadMultiscraperMedia(result.url, game, mediaType);
            };
            
            cardBody.appendChild(title);
            cardBody.appendChild(downloadBtn);
            
            card.appendChild(img);
            card.appendChild(cardBody);
            col.appendChild(card);
            contentDiv.appendChild(col);
        });
    }
    
    async downloadMultiscraperMedia(mediaUrl, game, mediaType) {
        try {
            const response = await fetch('/api/download-multiscraper-media', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    media_url: mediaUrl,
                    game_name: game.name,
                    media_type: mediaType,
                    system_name: this.currentSystem
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Media downloaded successfully for ${game.name}`, 'success');
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('multiscraperMediaModal'));
                if (modal) {
                    modal.hide();
                }
                // Refresh media preview
                if (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path === game.path) {
                    this.showMediaPreview(this.currentMediaPreviewGame);
                }
            } else {
                this.showAlert(data.error || 'Failed to download media', 'danger');
            }
        } catch (error) {
            this.showAlert('Error downloading media: ' + error.message, 'danger');
        }
    }
    
    displayLaunchBoxMediaOptions(mediaOptions, game, mediaType) {
        const contentDiv = document.getElementById('launchboxMediaContent');
        contentDiv.innerHTML = '';
        
        mediaOptions.forEach((media, index) => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4 mb-3';
            
            const card = document.createElement('div');
            card.className = 'card h-100';
            card.style.cursor = 'pointer';
            
            const img = document.createElement('img');
            img.className = 'card-img-top';
            img.style.height = '300px';
            img.style.objectFit = 'contain';
            img.style.backgroundColor = '#f8f9fa';
            img.src = media.url;
            img.alt = `${mediaType} option ${index + 1}`;
            img.onerror = () => {
                img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg==';
            };
            
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body d-flex flex-column';
            
            const title = document.createElement('h6');
            title.className = 'card-title';
            title.textContent = `${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} ${index + 1}`;
            
            const region = document.createElement('p');
            region.className = 'card-text text-muted small';
            region.textContent = `Region: ${media.region || 'Unknown'}`;
            
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-primary btn-sm mt-auto';
            downloadBtn.textContent = 'Download & Replace';
            downloadBtn.onclick = () => this.downloadAndReplaceMedia(game, mediaType, media);
            
            cardBody.appendChild(title);
            cardBody.appendChild(region);
            cardBody.appendChild(downloadBtn);
            
            card.appendChild(img);
            card.appendChild(cardBody);
            col.appendChild(card);
            contentDiv.appendChild(col);
        });
    }
    
    async downloadAndReplaceMedia(game, mediaType, mediaData) {
        try {
            // Show progress
            const progressDiv = document.getElementById('launchboxMediaProgress');
            progressDiv.style.display = 'block';
            progressDiv.textContent = 'Downloading and replacing media...';

            const response = await fetch('/api/download-launchbox-media', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    game_id: game.launchboxid,
                    rom_path: game.path,
                    media_type: mediaType,
                    media_url: mediaData.url,
                    region: mediaData.region,
                    system_name: this.currentSystem
                })
            });
            
            if (!response.ok) {
                // Try to get the error details from the response
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage += ` - ${errorData.error}`;
                    }
                } catch (e) {
                    // If we can't parse the response as JSON, just use the status text
                    errorMessage += ` - ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Update the local game object with the new media path
                if (result.media_path) {
                    game[mediaType] = result.media_path;
                    this.markGameAsModified(game);
                    
                    // Refresh the main grid to show updated media
                    if (this.gridApi) {
                        this.gridApi.refreshCells();
                    }
                }
                
                // Show success message
                progressDiv.textContent = 'Media downloaded and replaced successfully!';
                progressDiv.className = 'text-success mt-1';
                
                // Close modal after a short delay
                setTimeout(() => {
                    const modalElement = document.getElementById('launchboxMediaModal');
                    const modal = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
                    modal.hide();
                    
                    // Refresh the edit game media display
                    this.showEditGameMedia(game);
                    
                    // Also refresh the main interface media preview if it's currently showing this game
                    if (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path === game.path) {
                        // Update the currentMediaPreviewGame with the fresh data from the grid
                        const freshGame = this.games.find(g => g.path === game.path);
                        if (freshGame) {
                            this.currentMediaPreviewGame = freshGame;
                            this.showMediaPreview(this.currentMediaPreviewGame);
                        }
                    }
                }, 1500);
            } else {
                throw new Error(result.error || 'Unknown error occurred');
            }
        } catch (error) {
            const progressDiv = document.getElementById('launchboxMediaProgress');
            // Extract just the error message without the HTTP status prefix
            let errorMessage = error.message;
            if (errorMessage.includes('HTTP error! status: 404 - ')) {
                errorMessage = errorMessage.replace('HTTP error! status: 404 - ', '');
            }
            progressDiv.textContent = 'Error: ' + errorMessage;
            progressDiv.className = 'text-danger mt-1';
        }
    }
    
    showEditGameVideo(game) {
        const videoContent = document.getElementById('editGameVideoContent');
        if (!videoContent) return;

        // Clear existing content
        videoContent.innerHTML = '';
        
        // Define video fields to display
        const videoFields = ['video', 'video_mp4', 'video_avi', 'video_mov', 'video_mkv'];
        
        videoFields.forEach(field => {
            if (game[field] && game[field].trim()) {
                const videoItem = document.createElement('div');
                videoItem.className = 'video-preview-item';
                videoItem.style.cssText = 'width: 1200px; margin-bottom: 1rem; position: relative;';
                
                // Create video element with reduced height
                const video = document.createElement('video');
                video.controls = true;
                video.style.cssText = 'width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);';
                video.style.maxHeight = '400px';
                
                // Fix video URL by adding roms/<system>/ prefix if missing
                // Use the current system that was set when loading the games
                let videoPath = game[field];
                if (videoPath && !videoPath.startsWith('roms/')) {
                    videoPath = `roms/${this.currentSystem}/${videoPath}`;
                }
                video.src = videoPath;
                video.title = `${field}: ${game[field]}`;
                
                // Store video field for delete button functionality
                videoItem.setAttribute('data-video-field', field);
                
                // Add error handling
                video.onerror = () => {
                    videoItem.innerHTML = `
                        <div class="video-placeholder" style="width: 1200px; height: 600px; background-color: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d; font-size: 1.2rem; text-align: center;">
                            <div>
                                <i class="bi bi-camera-video" style="font-size: 4rem; margin-bottom: 1rem; display: block;"></i>
                                Video<br>Unavailable
                            </div>
                        </div>
                    `;
                };
                
                videoItem.appendChild(video);
                videoContent.appendChild(videoItem);
            }
        });
        
        // If no videos found, show message with upload option
        if (videoContent.children.length === 0) {
            videoContent.innerHTML = `
                <div class="text-center text-muted" style="width: 100%; padding: 2rem;">
                    <i class="bi bi-camera-video" style="font-size: 3rem; margin-bottom: 1rem; display: block;"></i>
                    <h6>No Video Files</h6>
                    <p class="mb-3">This game doesn't have any video files associated with it.</p>
                    <button class="btn btn-primary" onclick="gameManager.uploadMediaForGame(gameManager.games.find(g => g.id === ${game.id}), 'video')">
                        <i class="bi bi-cloud-upload me-2"></i>Upload Video
                    </button>
                </div>
            `;
        }
    }
    
    getFilenameFromPath(filePath) {
        if (!filePath || !filePath.trim()) return 'No file';
        // Extract filename from path (handle both forward and backward slashes)
        const filename = filePath.split(/[\/\\]/).pop();
        return filename || 'No file';
    }
    
    fixImagePath(imagePath) {
        if (!imagePath || !imagePath.trim()) return '';

        // If the path already starts with 'roms/', return as is
        if (imagePath.startsWith('roms/')) {
            return imagePath;
        }
        
        // Get current system from URL
        const currentSystem = this.getCurrentRomSystem();
        
        if (!currentSystem) {
            return imagePath;
        }
        
        // Add the missing prefix
        const fullPath = `roms/${currentSystem}/${imagePath}`;
        return fullPath;
    }
    
    uploadMedia(mediaField, gameId) {
        // Find the game by ID to get its ROM path
        const game = this.games.find(g => g.id === gameId);
        if (!game) {
            this.showAlert('Game not found', 'error');
            return;
        }
        
        // Use the existing uploadMediaForGame function with ROM path
        this.uploadMediaForGame(game, mediaField);
    }
    
    uploadMediaForGame(game, mediaField) {
        // Check if upload is already in progress
        if (this.uploadInProgress) {
            this.showAlert('Upload already in progress. Please wait...', 'warning');
            return;
        }
        
        // Create a file input element
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*,video/*';
        fileInput.style.display = 'none';
        
        // Add change event listener
        fileInput.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            if (file) {
                // Set upload in progress
                this.uploadInProgress = true;
                
                // Show modal loading state
                this.showModalUploadProgress(mediaField, file);
                
                try {
                    await this.handleMediaUpload(file, mediaField, game.path);
                    
                    // Get the updated game object from the main games array
                    const updatedGame = this.games.find(g => g.path === game.path);
                    if (updatedGame) {
                        // Refresh the media preview with the updated game object
                        this.showMediaPreview(updatedGame);
                    }
                    
                    // Show success message
                    this.showAlert(`${mediaField} uploaded successfully`, 'success');
                } catch (error) {
                    this.showAlert('Error uploading media file', 'error');
                } finally {
                    // Clear upload state
                    this.uploadInProgress = false;
                    this.hideModalUploadProgress();
                }
            }
            
            // Clean up
            document.body.removeChild(fileInput);
        });
        
        // Trigger file selection
        document.body.appendChild(fileInput);
        fileInput.click();
    }
    showModalUploadProgress(mediaField, file) {
        // Find the edit modal
        const editModal = document.getElementById('editGameModal');
        if (!editModal) return;
        
        // Create or update upload progress overlay
        let progressOverlay = document.getElementById('uploadProgressOverlay');
        if (!progressOverlay) {
            progressOverlay = document.createElement('div');
            progressOverlay.id = 'uploadProgressOverlay';
            progressOverlay.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                border-radius: 8px;
            `;
            editModal.querySelector('.modal-content').style.position = 'relative';
            editModal.querySelector('.modal-content').appendChild(progressOverlay);
        }
        
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        const isVideo = mediaField === 'video';
        const message = isVideo 
            ? `Uploading video (${fileSize} MB)...<br>This may take a moment for large files...` 
            : `Uploading ${mediaField} (${fileSize} MB)...<br>Please wait...`;
            
        progressOverlay.innerHTML = `
            <div style="text-align: center; color: white; padding: 20px;">
                <div class="spinner-border text-light mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5>${message}</h5>
                <p class="mb-0">Please do not close this modal or navigate away...</p>
            </div>
        `;
        progressOverlay.style.display = 'flex';
    }
    
    hideModalUploadProgress() {
        const progressOverlay = document.getElementById('uploadProgressOverlay');
        if (progressOverlay) {
            progressOverlay.style.display = 'none';
        }
    }
    async deleteVideoForGame(game, mediaField) {
        if (!confirm(`Are you sure you want to delete the ${mediaField} video for "${game.name}"?`)) {
            return;
        }
        
        try {
            // Show loading state
            this.showAlert(`Deleting ${mediaField} video...`, 'info');
            
            // Make API call to delete the video
            const response = await fetch(`/api/rom-system/${this.currentSystem}/game/delete-media`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    media_field: mediaField,
                    rom_path: game.path
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Update the game object in the main games array
                const gameIndex = this.games.findIndex(g => g.id === game.id);
                if (gameIndex !== -1) {
                    this.games[gameIndex][mediaField] = '';
                }
                
                // Refresh the media preview
                this.showMediaPreview(this.games[gameIndex]);
                
                // Refresh the video preview tab to remove the deleted video
                this.showEditGameVideo(this.games[gameIndex]);
                
                // Update the delete button state
                this.updateDeleteVideoButtonState(this.games[gameIndex]);
                
                // Show success message
                this.showAlert(`${mediaField} video deleted successfully`, 'success');
            } else {
                throw new Error(result.error || 'Failed to delete video');
            }
        } catch (error) {
            this.showAlert(`Error deleting ${mediaField} video: ${error.message}`, 'error');
        }
    }
    
    async handleMediaUpload(file, mediaField, romPath) {
        try {
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('media_file', file);
            formData.append('media_field', mediaField);
            formData.append('rom_path', romPath);
            
            // Show detailed loading state with file info
            const fileSize = (file.size / (1024 * 1024)).toFixed(2);
            const isVideo = mediaField === 'video';
            const waitingMessage = isVideo 
                ? `Uploading video (${fileSize} MB)... This may take a moment for large files...` 
                : `Uploading ${mediaField} (${fileSize} MB)... Please wait...`;
            this.showAlert(waitingMessage, 'info');
            
            // Upload the file
            const response = await fetch(`/api/rom-system/${this.currentSystem}/game/upload-media`, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    
                    // Update the game object with new media path
                    const game = this.games.find(g => g.path === romPath);
                    if (game) {
                        game[mediaField] = result.media_path;
                        
                        this.markGameAsModified(game);
                        
                        // Refresh the main grid to show updated media
                        this.gridApi.refreshCells();
                        
                        // If the edit modal is open, refresh the media display
                        const editModal = document.getElementById('editGameModal');
                        if (editModal && editModal.classList.contains('show')) {
                            this.showEditGameMedia(game);
                            
                            // If it's a video upload, also refresh the video preview tab
                            if (mediaField === 'video') {
                                this.showEditGameVideo(game);
                            }
                        }
                        
                        // If media preview is showing for this game, refresh it
                        if (this.mediaPreviewEnabled && this.currentMediaPreviewGame && 
                            this.currentMediaPreviewGame.path === game.path) {
                            // Add a longer delay to ensure gamelist is fully updated and processed
                            setTimeout(() => {
                                this.showMediaPreview(game);
                            }, 1000);
                        }
                        
                        // Show success message with file info
                        const successMessage = isVideo 
                            ? `Video uploaded successfully! (${fileSize} MB)` 
                            : `${mediaField} uploaded successfully! (${fileSize} MB)`;
                        this.showAlert(successMessage, 'success');
                    } else {
                    }
                } else {
                    this.showAlert(`Failed to upload ${mediaField}: ${result.error}`, 'error');
                }
            } else {
                this.showAlert(`Failed to upload ${mediaField}`, 'error');
            }
        } catch (error) {
            this.showAlert(`Error uploading ${mediaField}`, 'error');
        }
    }
    
    async saveGameChangesFromModal() {
        if (!this.editingGamePath) return;

        const game = this.games.find(g => g.path === this.editingGamePath);
        if (!game) {
            this.showAlert('Error: Game not found. Please close and reopen the edit modal.', 'error');
            return;
        }
        
        // Store original values to detect changes
        const originalGame = { ...game };
        
        // Update the game object with form values
        game.name = document.getElementById('editName').value;
        game.desc = document.getElementById('editDescription').value;
        game.genre = document.getElementById('editGenre').value;
        game.developer = document.getElementById('editDeveloper').value;
        game.publisher = document.getElementById('editPublisher').value;
        game.rating = document.getElementById('editRating').value;
        game.players = document.getElementById('editPlayers').value;
        // Convert date input back to internal format
        const dateInputValue = document.getElementById('editReleasedate').value;
        game.releasedate = this.convertDateInputToISO8601(dateInputValue);
        game.launchboxid = document.getElementById('editLaunchboxId').value;
        game.igdbid = document.getElementById('editIgdbId').value;
        game.screenscraperid = document.getElementById('editScreenscraperId').value;
        game.steamid = document.getElementById('editSteamId').value;
        game.steamgridid = document.getElementById('editSteamgridid').value;
        game.mobygamesid = document.getElementById('editMobygamesid').value;
        game.youtubeurl = document.getElementById('editYoutubeurl').value;
        
        // Handle favorite field (star icon)
        const favoriteIcon = document.getElementById('editFavorite');
        game.favorite = favoriteIcon.classList.contains('bi-star-fill');
        
        // Handle kidgame field (smiley icon)
        game.kidgame = this.isKidgameActive();

        // Detect which fields changed
        const changedFields = [];
        if (originalGame.name !== game.name) changedFields.push('name');
        if (originalGame.desc !== game.desc) changedFields.push('desc');
        if (originalGame.genre !== game.genre) changedFields.push('genre');
        if (originalGame.developer !== game.developer) changedFields.push('developer');
        if (originalGame.publisher !== game.publisher) changedFields.push('publisher');
        if (originalGame.rating !== game.rating) changedFields.push('rating');
        if (originalGame.players !== game.players) changedFields.push('players');
        if (originalGame.releasedate !== game.releasedate) changedFields.push('releasedate');
        if (originalGame.launchboxid !== game.launchboxid) changedFields.push('launchboxid');
        if (originalGame.igdbid !== game.igdbid) changedFields.push('igdbid');
        if (originalGame.screenscraperid !== game.screenscraperid) changedFields.push('screenscraperid');
        if (originalGame.steamid !== game.steamid) changedFields.push('steamid');
        if (originalGame.steamgridid !== game.steamgridid) changedFields.push('steamgridid');
        if (originalGame.mobygamesid !== game.mobygamesid) changedFields.push('mobygamesid');
        if (originalGame.youtubeurl !== game.youtubeurl) changedFields.push('youtubeurl');
        if (originalGame.favorite !== game.favorite) changedFields.push('favorite');
        if (originalGame.kidgame !== game.kidgame) changedFields.push('kidgame');

        try {
            // Immediately save changes to gamelist.xml
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    games: this.games,
                    changed_games: [{
                        game_id: game.id,
                        game_name: game.name,
                        rom_path: game.path,
                        changed_fields: changedFields
                    }]
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Clear modified games since they're now saved
                this.modifiedGames.clear();
                
                this.showAlert('Changes saved directly to gamelist.xml!', 'success');
                
                // Refresh the grid to show updated values, respecting current filters
                await this.refreshGridData();
                
                // Move focus away from modal before hiding it
                const safeElement = document.querySelector('#gamesCount') || document.body;
                if (safeElement) {
                    safeElement.focus();
                }
                
                const modal = bootstrap.Modal.getInstance(document.getElementById('editGameModal'));
                modal.hide();
            } else {
                const errorText = await response.text();
                this.showAlert('Error saving changes to gamelist.xml', 'danger');
            }
        } catch (error) {
            this.showAlert('Error saving changes to gamelist.xml', 'danger');
        }
    }

    async openManualScrapFromPreview() {
        // Get the currently selected game from the grid
        if (!this.gridApi) {
            this.showAlert('No game grid available', 'error');
            return;
        }

        const selectedRows = this.gridApi.getSelectedRows();
        if (selectedRows.length === 0) {
            this.showAlert('Please select a game first', 'error');
            return;
        }

        const game = selectedRows[0];
        if (!game || !game.path) {
            this.showAlert('Invalid game selected', 'error');
            return;
        }

        // Set the game path for manual scraping
        this.currentManualScrapRomPath = game.path;
        this.manualScrapSelectedMedia = {};
        
        // Flag to indicate this was opened from media preview pane, not game edit modal
        this.manualScrapFromPreview = true;

        // Show the manual scrap modal
        const modal = new bootstrap.Modal(document.getElementById('manualScrapModal'));
        modal.show();

        // Show loading state
        document.getElementById('manualScrapLoading').style.display = 'block';
        document.getElementById('manualScrapContent').style.display = 'none';

        try {
            // Call the manual scrap API
            const response = await fetch(`/api/rom-system/${this.currentSystem}/game/manual-scrap`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    rom_path: game.path
                })
            });

            if (response.ok) {
                const result = await response.json();
                // store results for apply mapping if needed
                this.lastManualScrapResults = result.results || {};
                this.lastManualScrapTextFields = (result.results && result.results.text_fields) || {};
                this.displayManualScrapResults(result.results);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error during manual scrap:', error);
            this.showAlert('Error during manual scraping: ' + error.message, 'error');
            
            // Hide loading state
            document.getElementById('manualScrapLoading').style.display = 'none';
            document.getElementById('manualScrapContent').style.display = 'block';
        }
    }

    async openManualScrapModal() {
        if (!this.editingGamePath) {
            this.showAlert('No game selected for manual scraping', 'error');
            return;
        }

        const game = this.games.find(g => g.path === this.editingGamePath);
        if (!game) {
            this.showAlert('Game not found for manual scraping', 'error');
            return;
        }

        // Keep rom path and clear previous selections
        this.currentManualScrapRomPath = game.path;
        this.manualScrapSelectedMedia = {};
        
        // Flag to indicate this was opened from game edit modal, not media preview pane
        this.manualScrapFromPreview = false;

        // Show the manual scrap modal
        const modal = new bootstrap.Modal(document.getElementById('manualScrapModal'));
        modal.show();

        // Show loading state
        document.getElementById('manualScrapLoading').style.display = 'block';
        document.getElementById('manualScrapContent').style.display = 'none';

        try {
            // Call the manual scrap API
            const response = await fetch(`/api/rom-system/${this.currentSystem}/game/manual-scrap`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    rom_path: game.path
                })
            });

            if (response.ok) {
                const result = await response.json();
                // store results for apply mapping if needed
                this.lastManualScrapResults = result.results || {};
                this.lastManualScrapTextFields = (result.results && result.results.text_fields) || {};
                this.displayManualScrapResults(result.results);
            } else {
                const errorData = await response.json();
                this.showAlert(`Error: ${errorData.error}`, 'error');
                modal.hide();
            }
        } catch (error) {
            this.showAlert('Error performing manual scrap', 'error');
            modal.hide();
        }
    }

    displayManualScrapResults(results) {
        // Hide loading state
        document.getElementById('manualScrapLoading').style.display = 'none';
        document.getElementById('manualScrapContent').style.display = 'block';

        // Populate text fields table
        this.populateTextFieldsTable(results.text_fields);
        
        // Populate media fields
        this.populateMediaFields(results.media_fields);

        // Enable the apply button
        document.getElementById('applyManualScrapResults').disabled = false;
    }

    populateTextFieldsTable(textFields) {
        const tbody = document.getElementById('textFieldsTableBody');
        tbody.innerHTML = '';

        const fieldLabels = {
            'name': 'Name',
            'desc': 'Description',
            'developer': 'Developer',
            'publisher': 'Publisher',
            'genre': 'Genre',
            'releasedate': 'Release Date',
            'rating': 'Rating',
            'nbvotes': 'Number of Votes'
        };

        Object.entries(textFields).forEach(([fieldKey, fieldData]) => {
            const row = document.createElement('tr');
            
            // Field name
            const fieldCell = document.createElement('td');
            fieldCell.textContent = fieldLabels[fieldKey] || fieldKey;
            fieldCell.className = 'fw-bold';
            row.appendChild(fieldCell);

            // Current value
            const currentCell = document.createElement('td');
            currentCell.textContent = fieldData.current || 'N/A';
            currentCell.className = 'text-muted';
            row.appendChild(currentCell);

            // Make the row track selection state
            row.dataset.field = fieldKey;
            row.dataset.selected = 'current';

            // Make current cell clickable to select 'current'
            currentCell.dataset.source = 'current';
            currentCell.style.cursor = 'pointer';
            currentCell.title = 'Click to select current value';
            currentCell.addEventListener('click', () => {
                this.setTextFieldSelection(row, 'current');
            });

            // Source columns (IGDB, ScreenScraper, LaunchBox, MobyGames)
            const sources = ['igdb', 'screenscraper', 'launchbox', 'mobygames'];
            sources.forEach(source => {
                const sourceCell = document.createElement('td');
                const sourceValue = fieldData.sources[source] || '';
                sourceCell.textContent = sourceValue || 'N/A';
                sourceCell.className = sourceValue ? 'text-success' : 'text-muted';
                sourceCell.dataset.source = source;
                sourceCell.style.cursor = 'pointer';
                if (sourceValue) {
                    sourceCell.title = `Click to select ${source}`;
                }
                sourceCell.addEventListener('click', () => {
                    // Only allow selecting if there is a value for this source
                    if (fieldData.sources[source]) {
                        this.setTextFieldSelection(row, source);
                    }
                });
                row.appendChild(sourceCell);
            });

            // Initialize selection highlight on 'current'
            this.setTextFieldSelection(row, 'current');

            tbody.appendChild(row);
        });
    }

    setTextFieldSelection(row, source) {
        row.dataset.selected = source;
        // Clear highlight from all selectable cells in this row
        row.querySelectorAll('td[data-source]').forEach(td => {
            td.classList.remove('table-active');
        });
        // Highlight the selected cell
        const selectedCell = row.querySelector(`td[data-source="${source}"]`);
        if (selectedCell) {
            selectedCell.classList.add('table-active');
        }
    }

    populateMediaFields(mediaFields) {
        const container = document.getElementById('mediaFieldsContainer');
        container.innerHTML = '';

        const mediaTypes = {
            'image': 'Box Art',
            'marquee': 'Marquee',
            'video': 'Video'
        };

        Object.entries(mediaFields)
            .filter(([mediaKey]) => mediaKey !== 'video' && mediaKey !== 'manual')
            .forEach(([mediaKey, mediaData]) => {
            const card = document.createElement('div');
            card.className = 'card mb-3';
            
            const cardHeader = document.createElement('div');
            cardHeader.className = 'card-header';
            // Display the exact gamelist media field name
            cardHeader.innerHTML = `<h6 class="mb-0"><i class="bi bi-image me-2"></i>${mediaKey}</h6>`;
            card.appendChild(cardHeader);

            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';
            
            // Removed 'Current' preview section per request

            // Source options
            const sourcesSection = document.createElement('div');
            sourcesSection.innerHTML = '<h6>Available Sources:</h6>';
            
            // Build a grid of selectable cards for all available media URLs
            const grid = document.createElement('div');
            grid.className = 'row row-cols-2 row-cols-md-3 row-cols-lg-4 g-2';

            // Helper to create a selectable tile
            const createTile = (source, url, index, metadata = {}) => {
                const col = document.createElement('div');
                col.className = 'col';
                const tile = document.createElement('div');
                tile.className = 'card h-100 selectable-media-item';
                tile.style.cursor = 'pointer';
                tile.dataset.mediaKey = mediaKey;
                tile.dataset.source = source;
                tile.dataset.index = String(index);
                tile.innerHTML = `
                    <div class="media-preview-item" style="width: 100%; height: 150px;">
                        ${this.getMediaPreview(url, mediaKey)}
                    </div>
                    <div class="card-body py-2">
                        <div class="small text-muted">${source.charAt(0).toUpperCase() + source.slice(1)}</div>
                        <div class="image-metadata" style="font-size: 0.75rem; color: #6c757d; margin-top: 4px;">
                            <div class="resolution-info">Loading...</div>
                            ${metadata.region ? `<div class="region-info">Region: ${metadata.region}</div>` : ''}
                        </div>
                    </div>
                `;
                // Hover full preview like game grid (images only)
                tile.addEventListener('mouseenter', (ev) => {
                    if (mediaKey !== 'video') {
                        this.showThumbnailHover(ev, url, mediaKey);
                    }
                });
                tile.addEventListener('mouseleave', () => this.hideThumbnailHover());
                tile.addEventListener('click', () => {
                    // remove highlight from other tiles for this media key
                    card.querySelectorAll('.selectable-media-item').forEach(el => el.classList.remove('border', 'border-primary'));
                    tile.classList.add('border', 'border-primary');
                    // store selection on instance
                    if (!this.manualScrapSelectedMedia) this.manualScrapSelectedMedia = {};
                    // For MobyGames, use page_url for full-size download, otherwise use url
                    const downloadUrl = (source === 'mobygames' && metadata.page_url) ? metadata.page_url : url;
                    this.manualScrapSelectedMedia[mediaKey] = { source, index, url: downloadUrl };
                });

                // Image resolution will be loaded automatically via onload event

                col.appendChild(tile);
                return col;
            };

            // Default tile: Keep Current
            grid.appendChild(createTile('current', mediaData.current, -1));
            // Preselect current
            grid.querySelector('.selectable-media-item').classList.add('border', 'border-primary');
            if (!this.manualScrapSelectedMedia) this.manualScrapSelectedMedia = {};
            this.manualScrapSelectedMedia[mediaKey] = { source: 'current', index: -1, url: mediaData.current };

            // Add tiles for each source. Each source may be an array of URLs or metadata objects.
            const sources = ['igdb', 'screenscraper', 'launchbox', 'steam', 'steamgriddb', 'mobygames'];
            sources.forEach(source => {
                const values = mediaData.sources[source];
                if (!values) return;
                const items = Array.isArray(values) ? values : [values];
                items.forEach((item, idx) => {
                    // Handle both old format (URL strings) and new format (metadata objects)
                    if (typeof item === 'string') {
                        grid.appendChild(createTile(source, item, idx));
                    } else if (typeof item === 'object' && item.url) {
                        grid.appendChild(createTile(source, item.url, idx, item));
                    }
                });
            });

            sourcesSection.appendChild(grid);
            cardBody.appendChild(sourcesSection);
            card.appendChild(cardBody);
            container.appendChild(card);
        });
    }

    getMediaPreview(mediaPath, mediaType) {
        if (!mediaPath) {
            return '<div class="media-placeholder"><i class="bi bi-image"></i><br>No Media</div>';
        }

        let mediaUrl;
        
        // Check if it's an external URL (starts with http:// or https://)
        if (mediaPath.startsWith('http://') || mediaPath.startsWith('https://')) {
            // External URL, use directly
            mediaUrl = mediaPath;
        } else {
            // Local file path - handle as before
            // Remove leading ./ if present
            let cleanPath = mediaPath;
            if (cleanPath.startsWith('./')) {
                cleanPath = cleanPath.substring(2);
            }
            
            // Check if the path already contains the full structure starting with /roms/
            if (cleanPath.startsWith('/roms/')) {
                // Path already contains full structure, use it as-is
                mediaUrl = cleanPath;
            } else if (cleanPath.startsWith('media/')) {
                // Path starts with media/, it's a relative path from system root
                mediaUrl = `/roms/${this.currentSystem}/${cleanPath}`;
            } else {
                // Path is just a filename, construct the full URL
                mediaUrl = `/roms/${this.currentSystem}/media/${mediaType}s/${cleanPath}`;
            }
        }
        
        if (mediaType === 'video') {
            return `<video src="${mediaUrl}" style="width: 100%; height: 100%; object-fit: cover;" controls></video>`;
        } else {
            return `<img src="${mediaUrl}" style="width: 100%; height: 100%; object-fit: contain;" onload="gameManager.handleImageLoad(this)" onerror="gameManager.handleImageError(this)">`;
        }
    }

    handleImageError(imgEl) {
        if (!imgEl || !imgEl.parentElement) return;
        imgEl.parentElement.innerHTML = '<div class="media-placeholder"><i class="bi bi-image"></i><br>Error</div>';
    }

    handleImageLoad(imgEl) {
        // Find the tile containing this image
        const tile = imgEl.closest('.selectable-media-item');
        if (!tile) return;

        // Get the resolution info element
        const resolutionInfo = tile.querySelector('.resolution-info');
        if (!resolutionInfo) return;

        // Update the resolution display
        if (imgEl.naturalWidth > 0 && imgEl.naturalHeight > 0) {
            resolutionInfo.textContent = `Resolution: ${imgEl.naturalWidth}x${imgEl.naturalHeight}`;
        } else {
            resolutionInfo.textContent = 'Resolution: Unknown';
        }
    }


    async applyManualScrapResults() {
        try {
            const applyBtn = document.getElementById('applyManualScrapResults');
            const applyingBar = document.getElementById('manualScrapApplying');
            const downloadLog = document.getElementById('manualScrapDownloadLog');
            const modalBody = document.querySelector('#manualScrapModal .modal-body');
            const modalContent = document.querySelector('#manualScrapModal .modal-content');
            
            // Disable apply button and show loading state
            if (applyBtn) applyBtn.disabled = true;
            if (applyingBar) {
                applyingBar.classList.remove('d-none');
                applyingBar.classList.add('d-flex');
            }
            
            // Show download progress log
            if (downloadLog) {
                downloadLog.classList.remove('d-none');
                // Clear previous logs
                const logContent = document.getElementById('downloadLogContent');
                if (logContent) {
                    logContent.innerHTML = '<div class="text-muted">Starting downloads...</div>';
                }
            } else {
                console.error('Download log element not found');
            }
            
            // Grey out the modal content
            if (modalContent) {
                modalContent.style.opacity = '0.6';
                modalContent.style.pointerEvents = 'none';
            }

            // Function to update download log
            const updateDownloadLog = (message, type = 'info') => {
                console.log(`updateDownloadLog: ${message} (${type})`);
                const logContent = document.getElementById('downloadLogContent');
                if (logContent) {
                    const timestamp = new Date().toLocaleTimeString();
                    const logEntry = document.createElement('div');
                    logEntry.className = `mb-1 small`;
                    
                    let icon = '📄';
                    let textClass = 'text-muted';
                    if (type === 'success') {
                        icon = '✅';
                        textClass = 'text-success';
                    } else if (type === 'error') {
                        icon = '❌';
                        textClass = 'text-danger';
                    } else if (type === 'warning') {
                        icon = '⚠️';
                        textClass = 'text-warning';
                    } else if (type === 'download') {
                        icon = '⬇️';
                        textClass = 'text-primary';
                    }
                    
                    logEntry.innerHTML = `<span class="text-muted">[${timestamp}]</span> <span class="${textClass}">${icon} ${message}</span>`;
                    logContent.appendChild(logEntry);
                    logContent.scrollTop = logContent.scrollHeight;
                    console.log(`Added log entry: ${message}`);
                } else {
                    console.error('downloadLogContent element not found');
                }
            };

            // Collect selected values from the form
            const selectedValues = {};
            
            // Get text field selections from table rows (each row stores dataset field and selected)
            const textRows = document.querySelectorAll('#textFieldsTableBody tr');
            textRows.forEach(row => {
                const fieldName = row.dataset.field;
                const selectedSource = row.dataset.selected;
                if (!fieldName || !selectedSource) return;
                selectedValues[fieldName] = selectedSource;
                if (selectedSource !== 'current' && this.lastManualScrapTextFields && this.lastManualScrapTextFields[fieldName]) {
                    const sourceVal = this.lastManualScrapTextFields[fieldName].sources && this.lastManualScrapTextFields[fieldName].sources[selectedSource];
                    if (sourceVal !== undefined && sourceVal !== null) {
                        selectedValues[`${fieldName}_value`] = sourceVal;
                    }
                }
            });

            // Get media field selections from selected tiles
            if (this.manualScrapSelectedMedia) {
                Object.entries(this.manualScrapSelectedMedia).forEach(([fieldName, sel]) => {
                    selectedValues[fieldName] = sel.source;
                    selectedValues[`${fieldName}_index`] = sel.index;
                    selectedValues[`${fieldName}_url`] = sel.url;
                });
            }

            // Include the current rom path for backend to identify the game
            const romPath = this.currentManualScrapRomPath || (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path);
            
            updateDownloadLog('Sending request to apply changes...', 'info');
            
            // Send to backend to apply and download
            const resp = await fetch(`/api/rom-system/${this.currentSystem}/game/manual-scrap/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ rom_path: romPath, selections: selectedValues })
            });
            
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                updateDownloadLog(`Error: ${err.error || `HTTP ${resp.status}`}`, 'error');
                throw new Error(err.error || `HTTP ${resp.status}`);
            }
            
            updateDownloadLog('Processing response...', 'info');
            const result = await resp.json();
            
            // Log download results if available
            if (result.downloads) {
                updateDownloadLog(`Downloaded ${result.downloads.success || 0} files successfully`, 'success');
                if (result.downloads.failed && result.downloads.failed > 0) {
                    updateDownloadLog(`${result.downloads.failed} downloads failed`, 'warning');
                }
            }
            
            updateDownloadLog('Changes applied successfully!', 'success');
            this.showAlert('Manual scrap results applied successfully!', 'success');
            // Refresh games from server to reflect updates
            await this.refreshGameGridWithData();
            
            // Refresh media preview if it's showing the same game
            if (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path === romPath) {
                const updatedGame = this.games.find(g => g.path === romPath);
                if (updatedGame) {
                    await this.showMediaPreview(updatedGame);
                }
            }
            
            // Note: Game edit modal will be repopulated in setTimeout below
            // Close the manual scrap modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('manualScrapModal'));
            modal && modal.hide();
            
            // Only reopen game edit modal if manual scrap was opened from game edit modal
            if (!this.manualScrapFromPreview) {
                // Ensure game edit modal is reopened with updated data
                setTimeout(() => {
                    if (this.editingGamePath) {
                        const updatedGame = this.games.find(g => g.path === this.editingGamePath);
                        if (updatedGame) {
                            console.log('Repopulating edit modal with game:', updatedGame);
                            // Always repopulate the edit modal with fresh data
                            this.populateEditModal(updatedGame);
                            
                            // Show the edit modal if it's not already visible
                            const editModal = document.getElementById('editGameModal');
                            if (editModal && !editModal.classList.contains('show')) {
                                const editModalInstance = new bootstrap.Modal(editModal);
                                editModalInstance.show();
                            }
                        } else {
                            console.error('Could not find updated game for path:', this.editingGamePath);
                        }
                    } else {
                        console.error('No editingGamePath set');
                    }
                }, 300); // Small delay to ensure modal transitions complete
            }

        } catch (error) {
            this.showAlert('Error applying manual scrap results', 'error');
        }
        finally {
            const applyBtn = document.getElementById('applyManualScrapResults');
            const applyingBar = document.getElementById('manualScrapApplying');
            const downloadLog = document.getElementById('manualScrapDownloadLog');
            const modalContent = document.querySelector('#manualScrapModal .modal-content');
            
            // Hide applying state
            if (applyingBar) {
                applyingBar.classList.remove('d-flex');
                applyingBar.classList.add('d-none');
            }
            
            // Hide download log
            if (downloadLog) {
                downloadLog.classList.add('d-none');
            }
            
            // Restore modal content
            if (modalContent) {
                modalContent.style.opacity = '1';
                modalContent.style.pointerEvents = 'auto';
            }
            
            // Re-enable apply button
            if (applyBtn) applyBtn.disabled = false;
        }
    }

    async scanGameMedia(game) {
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/game/${game.id}/scan-media`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    // Update the game data with new media paths
                    Object.assign(game, result.media_paths);
                    this.markGameAsModified(game);
                    this.gridApi.refreshCells();
                    this.showAlert('Media scan completed successfully!', 'success');
                }
            }
        } catch (error) {
            this.showAlert('Error scanning game media', 'danger');
        }
    }
    
    showGameEditFindBestMatch() {
        // Get current game data from edit modal
        const gameName = document.getElementById('editName').value;
        const systemName = this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Please select a game and system first', 'warning');
            return;
        }
        
        // Store current modal context
        this.currentModalContext = 'gameEdit';
        this.currentModalData = {
            name: gameName,
            system: systemName
        };
        
        // Load algorithm preference before showing modal
        this.loadGameEditAlgorithmPreference();
        
        // Show the game edit match modal
        // Get current game path for reliable identification
        const currentGame = this.getCurrentEditingGame();
        const gamePath = currentGame ? currentGame.path : null;
        this.showPartialMatches(gameName, null, 'gameEdit', gamePath);
        
        // Focus on the input field after modal is shown
        setTimeout(() => {
            const inputField = document.getElementById('gameEditOriginalGameNameInput');
            if (inputField) {
                inputField.focus();
            }
        }, 300);
    }
    
    async showGameEditIgdbSearch() {
        // Get current game data from edit modal
        const gameName = document.getElementById('editName').value;
        const systemName = this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Please select a game and system first', 'warning');
            return;
        }
        
        // Get system configuration to find IGDB platform
        const response = await fetch('/api/config', {
            headers: {
                'Accept-Encoding': 'gzip, deflate' // Enable compression for config data
            }
        });
        if (!response.ok) {
            this.showAlert('Failed to load system configuration', 'error');
            return;
        }
        const config = await response.json();
        const systemsConfig = config.systems || {};
        const systemConfig = systemsConfig[systemName] || {};
        const igdbPlatform = systemConfig.igdb;
        
        if (!igdbPlatform) {
            this.showAlert(`No IGDB platform configured for system '${systemName}'`, 'warning');
            return;
        }
        
        // Store current modal context
        this.currentModalContext = 'gameEdit';
        this.currentModalData = {
            name: gameName,
            system: systemName,
            igdbPlatform: igdbPlatform
        };
        
        // Show the IGDB search modal
        this.showIgdbSearchModal(gameName, igdbPlatform, systemName);
    }
    
    async showIgdbSearchModal(gameName, platformNameOrId, systemName) {
        // Prevent multiple simultaneous requests
        if (this.igdbSearchInProgress) {
            console.log('🔧 DEBUG: IGDB search already in progress, ignoring request');
            return;
        }
        
        this.igdbSearchInProgress = true;
        
        // Set the game name in the editable input field
        document.getElementById('igdbSearchGameNameInput').value = gameName;
        
        // Store system name and platform for use in results display
        this.currentIgdbSearchSystem = systemName;
        this.currentIgdbSearchPlatform = platformNameOrId;
        
        // Clear previous results
        document.getElementById('igdbSearchResults').innerHTML = '';
        document.getElementById('igdbSearchError').style.display = 'none';
        
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('igdbSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        modal.show();
        
        // Focus on the input field
        document.getElementById('igdbSearchGameNameInput').focus();
        
        // Show spinner
        document.getElementById('igdbSearchSpinner').style.display = 'inline-block';
        
        try {
            // Perform initial search
            await this.performIgdbSearch();
        } catch (error) {
            document.getElementById('igdbSearchSpinner').style.display = 'none';
            this.showIgdbSearchError('Error searching local IGDB database: ' + error.message);
        } finally {
            // Reset the flag to allow future requests
            this.igdbSearchInProgress = false;
        }
    }
    
    async performIgdbSearch() {
        try {
            const gameName = document.getElementById('igdbSearchGameNameInput').value.trim();
            if (!gameName) {
                this.showIgdbSearchError('Please enter a game name to search');
                return;
            }
            
            console.log('🔧 DEBUG: Making IGDB local database search request for:', gameName);
            // Search for games in local IGDB database
            const response = await fetch('/api/igdb/database/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_name: gameName,
                    platform_id: this.currentIgdbSearchPlatform,
                    limit: 10
                })
            });
            
            const result = await response.json();
            
            // Hide spinner
            document.getElementById('igdbSearchSpinner').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displayIgdbSearchResults(result.games);
            } else {
                this.showIgdbSearchError(result.error || 'Failed to search local IGDB database');
            }
            
        } catch (error) {
            document.getElementById('igdbSearchSpinner').style.display = 'none';
            this.showIgdbSearchError('Error searching local IGDB database: ' + error.message);
        }
    }
    
    async performMobygamesSearch() {
        try {
            const gameName = document.getElementById('mobygamesSearchGameNameInput').value.trim();
            if (!gameName) {
                this.showMobygamesSearchError('Please enter a game name to search');
                return;
            }
            
            // Show spinner
            document.getElementById('mobygamesSearchSpinner').style.display = 'inline-block';
            
            console.log('🔧 DEBUG: Making MobyGames search request for:', gameName);
            const response = await fetch('/api/mobygames/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_name: gameName,
                    system_name: this.currentMobygamesSearchSystem,
                    limit: 10
                })
            });
            
            const result = await response.json();
            
            // Hide spinner
            document.getElementById('mobygamesSearchSpinner').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displayMobygamesSearchResults(result.games);
            } else {
                this.showMobygamesSearchError(result.error || 'Failed to search MobyGames database');
            }
            
        } catch (error) {
            document.getElementById('mobygamesSearchSpinner').style.display = 'none';
            this.showMobygamesSearchError('Error searching MobyGames database: ' + error.message);
        }
    }
    
    async performScreenscraperSearch() {
        // Prevent multiple simultaneous requests
        if (this.screenscraperSearchInProgress) {
            return;
        }
        
        this.screenscraperSearchInProgress = true;
        
        try {
            const gameName = document.getElementById('screenscraperSearchGameNameInput').value.trim();
            if (!gameName) {
                this.showScreenscraperSearchError('Please enter a game name to search');
                return;
            }
            
            // Show spinner
            document.getElementById('screenscraperSearchSpinner').style.display = 'inline-block';
            const response = await fetch('/api/screenscraper/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_name: gameName,
                    system_name: this.currentScreenscraperSearchSystem,
                    limit: 10
                })
            });
            
            const result = await response.json();
            
            // Hide spinner
            document.getElementById('screenscraperSearchSpinner').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displayScreenscraperSearchResults(result.games);
            } else {
                this.showScreenscraperSearchError(result.error || 'Failed to search ScreenScraper database');
            }
            
        } catch (error) {
            document.getElementById('screenscraperSearchSpinner').style.display = 'none';
            this.showScreenscraperSearchError('Error searching ScreenScraper database: ' + error.message);
        } finally {
            // Reset the flag to allow future requests
            this.screenscraperSearchInProgress = false;
        }
    }
    
    async performSteamgridSearch() {
        try {
            const gameName = document.getElementById('steamgridSearchGameNameInput').value.trim();
            if (!gameName) {
                this.showSteamgridSearchError('Please enter a game name to search');
                return;
            }
            
            // Show spinner
            document.getElementById('steamgridSearchSpinner').style.display = 'inline-block';
            
            console.log('🔧 DEBUG: Making SteamGridDB search request for:', gameName);
            const response = await fetch('/api/steamgriddb/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_name: gameName,
                    limit: 10
                })
            });
            
            const result = await response.json();
            
            // Hide spinner
            document.getElementById('steamgridSearchSpinner').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displaySteamgridSearchResults(result.games);
            } else {
                this.showSteamgridSearchError(result.error || 'Failed to search SteamGridDB database');
            }
            
        } catch (error) {
            document.getElementById('steamgridSearchSpinner').style.display = 'none';
            this.showSteamgridSearchError('Error searching SteamGridDB database: ' + error.message);
        }
    }
    
    async performSteamSearch() {
        try {
            const gameName = document.getElementById('steamSearchGameNameInput').value.trim();
            if (!gameName) {
                this.showSteamSearchError('Please enter a game name to search');
                return;
            }
            
            // Show spinner
            document.getElementById('steamSearchSpinner').style.display = 'inline-block';
            
            console.log('🔧 DEBUG: Making Steam search request for:', gameName);
            const response = await fetch('/api/steam/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_name: gameName,
                    system_name: this.currentSteamSearchSystem || '',
                    limit: 10
                })
            });
            
            const result = await response.json();
            
            // Hide spinner
            document.getElementById('steamSearchSpinner').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displaySteamSearchResults(result.games);
            } else {
                this.showSteamSearchError(result.error || 'Failed to search Steam database');
            }
            
        } catch (error) {
            document.getElementById('steamSearchSpinner').style.display = 'none';
            this.showSteamSearchError('Error searching Steam database: ' + error.message);
        }
    }
    
    async performLaunchboxSearch() {
        try {
            const gameName = document.getElementById('gameEditOriginalGameNameInput').value.trim();
            if (!gameName) {
                this.showAlert('Please enter a game name to search', 'warning');
                return;
            }
            
            // Show loading spinner
            document.getElementById('gameEditLoadingSpinner').style.display = 'inline-block';
            
            console.log('🔧 DEBUG: Making LaunchBox search request for:', gameName);
            
            // Get system name
            const systemName = this.currentModalData?.system || this.currentSystem;
            if (!systemName) {
                this.showAlert('System not found', 'warning');
                return;
            }
            
            const response = await fetch('/api/get-top-matches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ game_name: gameName, system_name: systemName })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide loading spinner
            document.getElementById('gameEditLoadingSpinner').style.display = 'none';
            
            if (data.success) {
                // Get the current game path for reliable identification
                const currentGame = this.getCurrentEditingGame();
                const gamePath = currentGame ? currentGame.path : null;
                this.displayPartialMatchModal(gameName, data.matches, 'gameEdit', gamePath);
            } else {
                this.showAlert('Error getting matches: ' + data.error, 'danger');
            }
            
        } catch (error) {
            document.getElementById('gameEditLoadingSpinner').style.display = 'none';
            this.showAlert('Error searching LaunchBox database: ' + error.message, 'danger');
        }
    }
    
    displayIgdbSearchResults(games) {
        const resultsContainer = document.getElementById('igdbSearchResults');
        
        if (!games || games.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><div class="alert alert-info">No games found in local IGDB database.</div></div>';
            return;
        }
        
        let html = '';
        games.forEach((game, index) => {
            const rating = game.rating ? Math.round(game.rating) : 'N/A';
            const summary = game.summary ? (game.summary.length > 200 ? game.summary.substring(0, 200) + '...' : game.summary) : 'No description available';
            
            // Get platform names from IGDB data
            // Note: In local database, platforms might be IDs or objects
            let platformNames = 'Unknown Platform';
            if (game.platforms && game.platforms.length > 0) {
                if (typeof game.platforms[0] === 'object') {
                    // Platform objects with names
                    platformNames = game.platforms.map(p => p.name).join(', ');
                } else {
                    // Platform IDs - we'll show the IDs for now
                    platformNames = `Platform IDs: ${game.platforms.join(', ')}`;
                }
            }
            
            // Add cover image with IGDB URL format
            // Note: Local database uses 'cover' field with image_id
            const coverId = game.cover || game.cover_id;
            const coverImage = coverId ? 
                `<img src="https://images.igdb.com/igdb/image/upload/t_720p/${coverId}.jpg" 
                     class="card-img-top" 
                     style="height: 200px; object-fit: contain; background-color: #f8f9fa;" 
                     alt="${game.name}"
                     onerror="this.style.display='none';">` : 
                `<div class="card-img-top bg-light d-flex align-items-center justify-content-center" style="height: 200px;"><i class="bi bi-image text-muted" style="font-size: 2rem;"></i></div>`;
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        ${coverImage}
                        <div class="card-body">
                            <h6 class="card-title">${game.name}</h6>
                            <p class="card-text small text-muted">${summary}</p>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">Rating: ${rating}/100</small>
                                <small class="text-muted">ID: ${game.id}</small>
                            </div>
                            ${game._similarity_score ? `<div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-success">Match: ${Math.round(game._similarity_score * 100)}%</small>
                            </div>` : ''}
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="badge bg-info">${platformNames}</small>
                                <small class="text-muted">IGDB</small>
                            </div>
                        </div>
                        <div class="card-footer">
                            <button type="button" class="btn btn-info btn-sm w-100" onclick="gameManager.selectIgdbGame(${game.id}, '${game.name.replace(/'/g, "\\'")}')">
                                <i class="bi bi-check-circle me-1"></i>Select This Game
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
    }
    
    
    showIgdbSearchError(message) {
        const errorContainer = document.getElementById('igdbSearchError');
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    async selectIgdbGame(igdbId, gameName) {
        // Update the IGDB ID field in the edit modal
        document.getElementById('editIgdbId').value = igdbId;
        
        // Close the IGDB search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('igdbSearchModal'));
        if (modal) {
            modal.hide();
        }
        
        // Force cleanup of modal state to prevent interface getting stuck
        setTimeout(() => {
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                backdrop.remove();
            });
        }, 100);
        
        // Clear modal state
        this.currentModalContext = null;
        this.currentModalData = null;
        
        // Update the game data and mark as modified
        if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            const game = this.games[this.editingGameIndex];
            game.igdbid = igdbId;
            this.markGameAsModified(game);
            
            this.showAlert(`IGDB ID set to ${igdbId} for "${gameName}". Remember to save changes when ready.`, 'success');
        } else {
        this.showAlert(`IGDB ID set to ${igdbId} for "${gameName}"`, 'success');
        }
    }
    
    async showGameEditScreenscraperSearch() {
        // Get current game data from edit modal
        const gameName = document.getElementById('editName').value;
        const systemName = this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Please select a game and system first', 'warning');
            return;
        }
        
        // Store current modal context
        this.currentModalContext = 'gameEdit';
        this.currentModalData = {
            name: gameName,
            system: systemName
        };
        
        // Show the ScreenScraper search modal with auto-search
        this.showScreenscraperSearchModal(gameName, systemName);
    }
    
    async showScreenscraperSearchModal(gameName, systemName, autoSearch = true) {
        // Set the game name in the editable input field
        document.getElementById('screenscraperSearchGameNameInput').value = gameName;
        
        // Store system name for use in results display
        this.currentScreenscraperSearchSystem = systemName;
        
        // Clear previous results
        document.getElementById('screenscraperSearchResults').innerHTML = '';
        document.getElementById('screenscraperSearchError').style.display = 'none';
        
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('screenscraperSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        modal.show();
        
        // Focus on the input field
        document.getElementById('screenscraperSearchGameNameInput').focus();
        
        // Only perform auto-search if requested
        if (autoSearch) {
            // Show spinner
            document.getElementById('screenscraperSearchSpinner').style.display = 'inline-block';
            
            try {
                // Perform initial search
                await this.performScreenscraperSearch();
            } catch (error) {
                document.getElementById('screenscraperSearchSpinner').style.display = 'none';
                this.showScreenscraperSearchError('Error searching ScreenScraper games: ' + error.message);
            }
        }
    }
    
    displayScreenscraperSearchResults(games) {
        const resultsContainer = document.getElementById('screenscraperSearchResults');
        
        if (!games || games.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><div class="alert alert-info">No games found in ScreenScraper database.</div></div>';
            return;
        }
        
        let html = '';
        games.forEach((game, index) => {
            const description = game.description ? (game.description.length > 200 ? game.description.substring(0, 200) + '...' : game.description) : 'No description available';
            const genre = game.genre || 'Unknown Genre';
            const publisher = game.publisher || 'Unknown Publisher';
            const boxImage = game.box_image || null;
            
            // Create image HTML with fallback
            const imageHtml = boxImage ? `
                <div class="mb-2 text-center">
                    <img src="${boxImage}" class="img-fluid rounded" style="max-height: 200px; width: auto;" 
                         onerror="handleScreenscraperImageError(this)" 
                         alt="Game box art" loading="lazy">
                </div>
            ` : `
                <div class="mb-2 text-center">
                    <div class="d-flex align-items-center justify-content-center" style="height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;">
                        <div class="text-muted">
                            <i class="bi bi-image" style="font-size: 2rem;"></i>
                            <div class="small">No box art available</div>
                        </div>
                    </div>
                </div>
            `;
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        ${imageHtml}
                        <div class="card-body">
                            <h6 class="card-title">${game.name}</h6>
                            <p class="card-text small text-muted">${description}</p>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">Genre: ${genre}</small>
                                <small class="text-muted">ID: ${game.id}</small>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="badge bg-warning">${publisher}</small>
                                <small class="text-muted">ScreenScraper</small>
                            </div>
                        </div>
                        <div class="card-footer">
                            <button type="button" class="btn btn-warning btn-sm w-100" onclick="gameManager.selectScreenscraperGame(${game.id}, '${game.name.replace(/'/g, "\\'")}')">
                                <i class="bi bi-check-circle me-1"></i>Select This Game
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
        
        // Load box images asynchronously using the URLs from search results
        this.loadScreenscraperImagesAsync(games);
    }
    
    async loadScreenscraperImagesAsync(games) {
        // Load images in parallel for better performance using URLs from search results
        const imagePromises = games.map(game => this.loadScreenscraperImageForGame(game.id, game.box_image));
        await Promise.allSettled(imagePromises);
    }
    
    async loadScreenscraperImageForGame(gameId, boxImageUrl) {
        const imageContainer = document.getElementById(`screenscraper-image-${gameId}`);
        if (!imageContainer) {
            return;
        }
        
        if (boxImageUrl) {
            // Create a new image element to test if the URL loads
            const img = new Image();
            img.onload = () => {
                // Image loaded successfully, replace placeholder
                imageContainer.innerHTML = `
                    <img src="${boxImageUrl}" class="img-fluid rounded" style="max-height: 200px; width: auto;" 
                         onerror="this.parentElement.innerHTML='<div class=\\"text-muted\\"><i class=\\"bi bi-image\\" style=\\"font-size: 2rem;\\"></i><div class=\\"small\\">No box art available</div></div>'" 
                         alt="Game box art" loading="lazy">
                `;
            };
            img.onerror = () => {
                // Image failed to load, show no image available
                imageContainer.innerHTML = `
                    <div class="text-muted">
                        <i class="bi bi-image" style="font-size: 2rem;"></i>
                        <div class="small">No box art available</div>
                    </div>
                `;
            };
            img.src = boxImageUrl;
        } else {
            // No box image URL provided, show no image available
            imageContainer.innerHTML = `
                <div class="text-muted">
                    <i class="bi bi-image" style="font-size: 2rem;"></i>
                    <div class="small">No box art available</div>
                </div>
            `;
        }
    }
    
    showScreenscraperSearchError(message) {
        const errorContainer = document.getElementById('screenscraperSearchError');
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    async selectScreenscraperGame(screenscraperId, gameName) {
        // Update the ScreenScraper ID field in the edit modal
        document.getElementById('editScreenscraperId').value = screenscraperId;
        
        // Close the ScreenScraper search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('screenscraperSearchModal'));
        if (modal) {
            modal.hide();
        }
        
        // Force cleanup of modal state to prevent interface getting stuck
        setTimeout(() => {
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                backdrop.remove();
            });
        }, 100);
        
        // Clear modal state
        this.currentModalContext = null;
        this.currentModalData = null;
        
        // Update the game data and mark as modified
        if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            const game = this.games[this.editingGameIndex];
            game.screenscraperid = screenscraperId;
            this.markGameAsModified(game);
            
            this.showAlert(`ScreenScraper ID set to ${screenscraperId} for "${gameName}". Remember to save changes when ready.`, 'success');
        } else {
            this.showAlert(`ScreenScraper ID set to ${screenscraperId} for "${gameName}"`, 'success');
        }
    }
    
    async showGameEditSteamSearch() {
        // Get current game data from edit modal
        const gameName = document.getElementById('editName').value;
        const systemName = this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Please select a game and system first', 'warning');
            return;
        }
        
        // Store current modal context
        this.currentModalContext = 'gameEdit';
        this.currentModalData = {
            name: gameName,
            system: systemName
        };
        
        // Show the Steam search modal
        this.showSteamSearchModal(gameName, systemName);
    }
    
    async showSteamSearchModal(gameName, systemName) {
        // Set the game name in the modal input field
        document.getElementById('steamSearchGameNameInput').value = gameName;
        
        // Store system name for use in results display
        this.currentSteamSearchSystem = systemName;
        
        // Clear previous results
        document.getElementById('steamSearchResults').innerHTML = '';
        document.getElementById('steamSearchError').style.display = 'none';
        
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('steamSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        modal.show();
        
        // Focus on the input field
        document.getElementById('steamSearchGameNameInput').focus();
        
        // Show spinner
        document.getElementById('steamSearchSpinner').style.display = 'inline-block';
        
        try {
            // Perform initial search
            await this.performSteamSearch();
        } catch (error) {
            document.getElementById('steamSearchSpinner').style.display = 'none';
            this.showSteamSearchError('Error searching Steam games: ' + error.message);
        }
    }
    
    displaySteamSearchResults(games) {
        const resultsContainer = document.getElementById('steamSearchResults');
        
        if (!games || games.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><div class="alert alert-info">No games found in Steam database.</div></div>';
            return;
        }

        let html = '';
        games.forEach((game, index) => {
            const description = game.description ? (game.description.length > 200 ? game.description.substring(0, 200) + '...' : game.description) : 'No description available';
            const price = game.price || 'Free';
            const releaseDate = game.release_date || 'Unknown';
            const similarityScore = game.similarity_score ? Math.round(game.similarity_score * 100) : 0;
            
            // Create image HTML with capsule image URLs from search results
            const capsuleImage = game.capsule_image || null;
            const imageHtml = capsuleImage ? `
                <div class="mb-2 text-center">
                    <img src="${capsuleImage}" class="img-fluid rounded" style="max-height: 200px; width: auto;" 
                         onerror="handleSteamImageError(this)" 
                         alt="Steam capsule art" loading="lazy">
                </div>
            ` : `
                <div class="mb-2 text-center">
                    <div class="d-flex align-items-center justify-content-center" style="height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;">
                        <div class="text-muted">
                            <i class="bi bi-image" style="font-size: 2rem;"></i>
                            <div class="small">No capsule art available</div>
                        </div>
                    </div>
                </div>
            `;
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            ${imageHtml}
                            <h6 class="card-title">${game.name}</h6>
                            <p class="card-text small text-muted">${description}</p>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">Price: ${price}</small>
                                <small class="text-muted">ID: ${game.appid}</small>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="badge bg-success">${releaseDate}</small>
                                <small class="badge bg-info">${similarityScore}% match</small>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">Steam</small>
                            </div>
                        </div>
                        <div class="card-footer">
                            <button type="button" class="btn btn-success btn-sm w-100" onclick="gameManager.selectSteamGame(${game.appid}, '${game.name.replace(/'/g, "\\'")}')">
                                <i class="bi bi-check-circle me-1"></i>Select This Game
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
    }
    
    
    showSteamSearchError(message) {
        const errorContainer = document.getElementById('steamSearchError');
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    async selectSteamGame(steamId, gameName) {
        // Update the Steam ID field in the edit modal
        document.getElementById('editSteamId').value = steamId;
        
        // Close the Steam search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('steamSearchModal'));
        if (modal) {
            modal.hide();
        }
        
        // Clear modal state
        this.currentModalContext = null;
        this.currentModalData = null;
        
        // Update the game data and mark as modified
        if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            const game = this.games[this.editingGameIndex];
            game.steamid = steamId;
            this.markGameAsModified(game);
            
            this.showAlert(`Steam ID set to ${steamId} for "${gameName}". Remember to save changes when ready.`, 'success');
        } else {
            this.showAlert(`Steam ID set to ${steamId} for "${gameName}"`, 'success');
        }
    }
    
    async showGameEditSteamgridSearch() {
        // Get current game data from edit modal
        const gameName = document.getElementById('editName').value;
        const systemName = this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Please select a game and system first', 'warning');
            return;
        }
        
        // Store current modal context
        this.currentModalContext = 'gameEdit';
        this.currentModalData = {
            name: gameName,
            system: systemName
        };
        
        // Show the SteamGridDB search modal
        this.showSteamgridSearchModal(gameName, systemName);
    }
    
    async showGameEditMobygamesSearch() {
        // Get current game data from edit modal
        const gameName = document.getElementById('editName').value;
        const systemName = this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Please select a game and system first', 'warning');
            return;
        }
        
        // Store current modal context
        this.currentModalContext = 'gameEdit';
        this.currentModalData = {
            name: gameName,
            system: systemName
        };
        
        // Show the MobyGames search modal
        this.showMobygamesSearchModal(gameName, systemName);
    }
    
    async showMobygamesSearchModal(gameName, systemName) {
        // Set the game name in the editable input field
        document.getElementById('mobygamesSearchGameNameInput').value = gameName;
        
        // Store system name for use in results display
        this.currentMobygamesSearchSystem = systemName;
        
        // Clear previous results
        document.getElementById('mobygamesSearchResults').innerHTML = '';
        document.getElementById('mobygamesSearchError').style.display = 'none';
        
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('mobygamesSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        modal.show();
        
        // Focus on the input field
        document.getElementById('mobygamesSearchGameNameInput').focus();
        
        // Show spinner
        document.getElementById('mobygamesSearchSpinner').style.display = 'inline-block';
        
        try {
            // Perform initial search
            await this.performMobygamesSearch();
        } catch (error) {
            document.getElementById('mobygamesSearchSpinner').style.display = 'none';
            this.showMobygamesSearchError('Error searching MobyGames games: ' + error.message);
        }
    }
    
    displayMobygamesSearchResults(games) {
        const resultsContainer = document.getElementById('mobygamesSearchResults');
        
        if (!games || games.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><div class="alert alert-info">No games found in MobyGames database.</div></div>';
            return;
        }
        
        let html = '';
        games.forEach((game, index) => {
            const score = game.score ? ` (${(game.score * 100).toFixed(1)}% match)` : '';
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title">${game.title}${score}</h6>
                            <p class="card-text">
                                <small class="text-muted">
                                    <strong>ID:</strong> ${game.id}<br>
                                    <strong>System:</strong> ${game.system}
                                </small>
                            </p>
                        </div>
                        <div class="card-footer">
                            <button class="btn btn-danger btn-sm w-100" onclick="gameManager.selectMobygamesGame('${game.id}', '${game.title.replace(/'/g, "\\'")}')">
                                <i class="bi bi-check-circle me-1"></i>Select This Game
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
    }
    
    showMobygamesSearchError(message) {
        const errorContainer = document.getElementById('mobygamesSearchError');
        errorContainer.innerHTML = message;
        errorContainer.style.display = 'block';
    }
    
    selectMobygamesGame(gameId, gameTitle) {
        // Set the MobyGames ID in the edit modal
        document.getElementById('editMobygamesid').value = gameId;
        
        // Close the search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('mobygamesSearchModal'));
        if (modal) {
            modal.hide();
        }
        
        // Clear modal state
        this.currentModalContext = null;
        this.currentModalData = null;
        
        // Show success message
        this.showAlert(`MobyGames ID set to ${gameId} for "${gameTitle}"`, 'success');
    }
    
    async showSteamgridSearchModal(gameName, systemName) {
        // Set the game name in the editable input field
        document.getElementById('steamgridSearchGameNameInput').value = gameName;
        
        // Store system name for use in results display
        this.currentSteamgridSearchSystem = systemName;
        
        // Clear previous results
        document.getElementById('steamgridSearchResults').innerHTML = '';
        document.getElementById('steamgridSearchError').style.display = 'none';
        
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('steamgridSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        modal.show();
        
        // Focus on the input field
        document.getElementById('steamgridSearchGameNameInput').focus();
        
        // Show spinner
        document.getElementById('steamgridSearchSpinner').style.display = 'inline-block';
        
        try {
            // Perform initial search
            await this.performSteamgridSearch();
        } catch (error) {
            document.getElementById('steamgridSearchSpinner').style.display = 'none';
            this.showSteamgridSearchError('Error searching SteamGridDB games: ' + error.message);
        }
    }
    
    displaySteamgridSearchResults(games) {
        const resultsContainer = document.getElementById('steamgridSearchResults');
        
        if (!games || games.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><div class="alert alert-info">No games found in SteamGridDB database.</div></div>';
            return;
        }
        
        let html = '';
        games.forEach((game, index) => {
            const verified = game.verified ? 'Verified' : 'Unverified';
            const verifiedClass = game.verified ? 'bg-success' : 'bg-secondary';
            
            // Create placeholder image HTML (will be replaced when actual image loads)
            const imageHtml = `
                <div class="mb-2 text-center">
                    <div id="steamgrid-image-${game.id}" class="d-flex align-items-center justify-content-center" style="height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;">
                        <div class="text-muted">
                            <div class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></div>
                            <div class="small">Loading grid art...</div>
                        </div>
                    </div>
                </div>
            `;
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        ${imageHtml}
                        <div class="card-body">
                            <h6 class="card-title">${game.name}</h6>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">ID: ${game.id}</small>
                                <small class="badge ${verifiedClass}">${verified}</small>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">SteamGridDB</small>
                                <small class="text-muted">${game.types ? game.types.join(', ') : 'Unknown'}</small>
                            </div>
                        </div>
                        <div class="card-footer">
                            <button type="button" class="btn btn-secondary btn-sm w-100" onclick="gameManager.selectSteamgridGame(${game.id}, '${game.name.replace(/'/g, "\\'")}')">
                                <i class="bi bi-check-circle me-1"></i>Select This Game
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
        
        // Load grid images asynchronously for each game
        this.loadSteamgridImagesAsync(games);
    }
    
    async loadSteamgridImagesAsync(games) {
        // Load grid images for each game in parallel
        const imagePromises = games.map(game => this.loadSteamgridImageForGame(game.id));
        
        // Wait for all images to load (or fail)
        await Promise.allSettled(imagePromises);
    }
    
    async loadSteamgridImageForGame(steamgridId) {
        try {
            const response = await fetch('/api/steamgriddb/grid-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    steamgrid_id: steamgridId
                })
            });
            
            const result = await response.json();
            const imageContainer = document.getElementById(`steamgrid-image-${steamgridId}`);
            
            if (!imageContainer) {
                return; // Container might have been removed
            }
            
            if (response.ok && result.success && result.grid_image) {
                // Successfully loaded image - replace placeholder with actual image
                imageContainer.innerHTML = `
                    <img src="${result.grid_image}" class="img-fluid rounded" style="max-height: 200px; width: auto;" 
                         onerror="handleSteamgridImageError(this)" 
                         alt="Game grid art" loading="lazy">
                `;
            } else {
                // Failed to load image - show error state
                imageContainer.innerHTML = `
                    <div class="text-muted">
                        <i class="bi bi-image" style="font-size: 2rem;"></i>
                        <div class="small">No grid art available</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error(`Error loading grid image for SteamGridDB ID ${steamgridId}:`, error);
            
            // Show error state
            const imageContainer = document.getElementById(`steamgrid-image-${steamgridId}`);
            if (imageContainer) {
                imageContainer.innerHTML = `
                    <div class="text-muted">
                        <i class="bi bi-image" style="font-size: 2rem;"></i>
                        <div class="small">Failed to load image</div>
                    </div>
                `;
            }
        }
    }
    
    showSteamgridSearchError(message) {
        const errorContainer = document.getElementById('steamgridSearchError');
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    showSteamSearchError(message) {
        const errorContainer = document.getElementById('steamSearchError');
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    async selectSteamgridGame(steamgridId, gameName) {
        // Update the SteamGridDB ID field in the edit modal
        document.getElementById('editSteamgridid').value = steamgridId;
        
        // Close the SteamGridDB search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('steamgridSearchModal'));
        if (modal) {
            modal.hide();
        }
        
        // Clear modal state
        this.currentModalContext = null;
        this.currentModalData = null;
        
        // Update the game data and mark as modified
        if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            const game = this.games[this.editingGameIndex];
            game.steamgridid = steamgridId;
            this.markGameAsModified(game);
            
            this.showAlert(`SteamGridDB ID set to ${steamgridId} for "${gameName}". Remember to save changes when ready.`, 'success');
        } else {
            this.showAlert(`SteamGridDB ID set to ${steamgridId} for "${gameName}"`, 'success');
        }
    }

    async findBestMatchForSelectedOriginal() {
        // Original LaunchBox find best match functionality
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Finding Matches...';
            }

            // Show the modal with loading state
            this.showGlobalMatchModal();
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            // Use the original LaunchBox API endpoint
            const response = await fetch('/api/find-best-matches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                
                // Store the results as a Map with ROM path as key
                this.globalMatchResults = new Map();
                data.results.forEach(result => {
                    // Check if game_data exists and has a path
                    if (result.game_data && result.game_data.path) {
                        this.globalMatchResults.set(result.game_data.path, result);
                    } else {
                        console.error('🔧 DEBUG: Invalid result structure:', result);
                        // Fallback to game_path if available
                        if (result.game_path) {
                            this.globalMatchResults.set(result.game_path, result);
                        }
                    }
                });
                this.populateGlobalMatchTable('launchbox');
            } else {
                this.showGlobalMatchEmpty();
                this.showAlert('No matches found for the selected games', 'info');
            }
            
            } catch (error) {
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
            this.hideGlobalMatchModal();
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
    }

    async findBestMatchForSelectedMobygames() {
        // MobyGames find best match functionality with auto-selection
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Finding Matches...';
            }

            // Show the modal with loading state
            this.showGlobalMatchModal();
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            // Use the MobyGames API endpoint
            const response = await fetch('/api/find-best-matches-mobygames', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                
                // Store the results as a Map with ROM path as key
                this.globalMatchResults = new Map();
                data.results.forEach(result => {
                    // Check if game_data exists and has a path
                    if (result.game_data && result.game_data.path) {
                        this.globalMatchResults.set(result.game_data.path, result);
                    } else {
                        console.error('🔧 DEBUG: Invalid result structure:', result);
                        // Fallback to game_path if available
                        if (result.game_path) {
                            this.globalMatchResults.set(result.game_path, result);
                        }
                    }
                });
                this.populateGlobalMatchTable('mobygames');
        } else {
                this.showGlobalMatchEmpty();
                this.showAlert('No matches found for the selected games', 'info');
            }
            
        } catch (error) {
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
            this.hideGlobalMatchModal();
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
    }

    async findBestMatchForSelectedDatscrapper() {
        // DAT Scrapper find best match functionality with auto-selection
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Finding Matches...';
            }

            // Show the modal with loading state
            this.showGlobalMatchModal();
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            // Use the DAT Scrapper API endpoint
            const response = await fetch('/api/find-best-matches-datscrapper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                
                // Store the results as a Map with ROM path as key
                this.globalMatchResults = new Map();
                data.results.forEach(result => {
                    // Check if game_data exists and has a path
                    if (result.game_data && result.game_data.path) {
                        this.globalMatchResults.set(result.game_data.path, result);
                    } else {
                        console.error('🔧 DEBUG: Invalid result structure:', result);
                        // Fallback to game_path if available
                        if (result.game_path) {
                            this.globalMatchResults.set(result.game_path, result);
                        }
                    }
                });
                this.populateGlobalMatchTable('datscrapper');
        } else {
                this.showGlobalMatchEmpty();
                this.showAlert('No matches found for the selected games', 'info');
            }
            
        } catch (error) {
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
            this.hideGlobalMatchModal();
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
    }

    async findBestMatchForSelectedSteam() {
        // Steam find best match functionality with auto-selection
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Finding Matches...';
            }

            // Show the modal with loading state
            this.showGlobalMatchModal();
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            // Use the Steam API endpoint
            const response = await fetch('/api/find-best-matches-steam', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                
                // Store the results as a Map with ROM path as key
                this.globalMatchResults = new Map();
                data.results.forEach(result => {
                    // Check if game_data exists and has a path
                    if (result.game_data && result.game_data.path) {
                        this.globalMatchResults.set(result.game_data.path, result);
                    } else {
                        console.error('🔧 DEBUG: Invalid result structure:', result);
                        // Fallback to game_path if available
                        if (result.game_path) {
                            this.globalMatchResults.set(result.game_path, result);
                        }
                    }
                });
                this.populateGlobalMatchTable('steam');
            } else {
                this.showGlobalMatchEmpty();
                this.showAlert('No matches found for the selected games', 'info');
            }
            
        } catch (error) {
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
            this.hideGlobalMatchModal();
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
    }

    async findBestMatchForSelectedIgdb() {
        // IGDB find best match functionality with auto-selection
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Finding Matches...';
            }

            // Show the modal with loading state
            this.showGlobalMatchModal();
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            // Use the IGDB API endpoint
            const response = await fetch('/api/find-best-matches-igdb', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                
                // Store the results as a Map with ROM path as key
                this.globalMatchResults = new Map();
                data.results.forEach(result => {
                    // Check if game_data exists and has a path
                    if (result.game_data && result.game_data.path) {
                        this.globalMatchResults.set(result.game_data.path, result);
                    } else {
                        console.error('🔧 DEBUG: Invalid result structure:', result);
                        // Fallback to game_path if available
                        if (result.game_path) {
                            this.globalMatchResults.set(result.game_path, result);
                        }
                    }
                });
                this.populateGlobalMatchTable('igdb');
            } else {
                this.showGlobalMatchEmpty();
                this.showAlert('No matches found for the selected games', 'info');
            }
            
        } catch (error) {
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
            this.hideGlobalMatchModal();
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
    }

    async findBestMatchForSelected(databaseType = 'launchbox') {
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Finding Matches...';
            }

            // Show the modal with loading state
            this.showGlobalMatchModal();
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            // Determine API endpoint based on database type
            let apiEndpoint = '/api/find-best-matches';
            if (databaseType === 'mobygames') {
                apiEndpoint = '/api/find-best-matches-mobygames';
            } else if (databaseType === 'steam') {
                apiEndpoint = '/api/find-best-matches-steam';
            }
            
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                
                // Store the results as a Map with ROM path as key
                this.globalMatchResults = new Map();
                data.results.forEach(result => {
                    // Check if game_data exists and has a path
                    if (result.game_data && result.game_data.path) {
                        this.globalMatchResults.set(result.game_data.path, result);
                    } else {
                        console.error('🔧 DEBUG: Invalid result structure:', result);
                        // Fallback to game_path if available
                        if (result.game_path) {
                            this.globalMatchResults.set(result.game_path, result);
                        }
                    }
                });
                this.showGlobalMatchResultsModal(data.results, databaseType);
            } else {
                this.showGlobalMatchEmpty();
                this.showAlert('No matches found for the selected games', 'info');
            }
            
        } catch (error) {
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
            this.hideGlobalMatchModal();
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
    }

    showGlobalMatchModal() {
        const modal = new bootstrap.Modal(document.getElementById('globalMatchModal'));
        const progressDiv = document.getElementById('globalMatchProgress');
        const tableDiv = document.getElementById('globalMatchTable');
        const emptyDiv = document.getElementById('globalMatchEmpty');
        
        // Show loading state
        if (progressDiv) progressDiv.style.display = 'block';
        if (tableDiv) tableDiv.style.display = 'none';
        if (emptyDiv) emptyDiv.style.display = 'none';
        
        // Load algorithm preference before showing modal
        this.loadGlobalAlgorithmPreference();
        
        modal.show();
    }

    hideGlobalMatchModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('globalMatchModal'));
        if (modal) {
            modal.hide();
        }
    }

    showGlobalMatchEmpty() {
        const progressDiv = document.getElementById('globalMatchProgress');
        const tableDiv = document.getElementById('globalMatchTable');
        const emptyDiv = document.getElementById('globalMatchEmpty');
        
        if (progressDiv) progressDiv.style.display = 'none';
        if (tableDiv) tableDiv.style.display = 'none';
        if (emptyDiv) emptyDiv.style.display = 'block';
    }

    showGlobalMatchResultsModal(results, databaseType = 'launchbox') {
        // Hide the progress div and show the table
        const progressDiv = document.getElementById('globalMatchProgress');
        const tableDiv = document.getElementById('globalMatchTable');
        const emptyDiv = document.getElementById('globalMatchEmpty');
        
        if (progressDiv) progressDiv.style.display = 'none';
        if (tableDiv) tableDiv.style.display = 'block';
        if (emptyDiv) emptyDiv.style.display = 'none';
        
        // Clear existing content
        const tbody = document.getElementById('globalMatchTableBody');
        if (tbody) {
            tbody.innerHTML = '';
        }
        
        // Create rows for each result
        results.forEach((result, index) => {
            const row = this.createTextOnlyMatchRow(result, index, databaseType);
            if (tbody) {
                tbody.appendChild(row);
            }
        });
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('globalMatchModal'));
        modal.show();
    }
    
    createTextOnlyMatchRow(result, index, databaseType = 'launchbox') {
        const row = document.createElement('tr');
        row.style.height = '40px';
        
        const gameName = result.game_name || 'Unknown';
        const gamePath = result.game_path || '';
        
        // Get current ID and best match based on database type
        let currentId = 'None';
        let bestMatch = null;
        let allMatches = [];
        
        if (databaseType === 'launchbox') {
            currentId = result.existing_launchboxid || 'None';
            allMatches = result.top_matches || [];
            bestMatch = allMatches.length > 0 ? allMatches[0] : null;
        } else if (databaseType === 'mobygames') {
            currentId = result.existing_mobygamesid || 'None';
            bestMatch = result.best_match;
            allMatches = result.all_matches || [];
        } else if (databaseType === 'steam') {
            currentId = result.existing_steamid || 'None';
            bestMatch = result.best_match;
            allMatches = result.all_matches || [];
        } else if (databaseType === 'igdb') {
            currentId = result.existing_igdbid || 'None';
            bestMatch = result.best_match;
            allMatches = result.all_matches || [];
        }
        
        // Game name cell
        const nameCell = document.createElement('td');
        nameCell.style.padding = '6px 8px';
        nameCell.style.verticalAlign = 'middle';
        nameCell.style.fontSize = '0.75rem';
        nameCell.textContent = gameName;
        row.appendChild(nameCell);
        
        // Current ID cell
        const idCell = document.createElement('td');
        idCell.style.padding = '6px 8px';
        idCell.style.verticalAlign = 'middle';
        idCell.style.fontSize = '0.8rem';
        idCell.textContent = currentId;
        row.appendChild(idCell);
        
        // Best match dropdown cell
        const matchCell = document.createElement('td');
        matchCell.style.padding = '6px 8px';
        matchCell.style.verticalAlign = 'middle';
        
        const select = document.createElement('select');
        select.className = 'form-select form-select-sm';
        select.style.fontSize = '0.8rem';
        select.style.padding = '4px 6px';
        select.id = `globalMatchSelect_${index}`;
        
        // Add "No Match" option
        const noMatchOption = document.createElement('option');
        noMatchOption.value = '';
        noMatchOption.textContent = 'No Match';
        select.appendChild(noMatchOption);
        
        // Add match options
        if (allMatches && allMatches.length > 0) {
            allMatches.forEach((match, matchIndex) => {
                const option = document.createElement('option');
                
                if (databaseType === 'launchbox') {
                    option.value = match.database_id;
                    option.textContent = `${match.name} (${(match.score * 100).toFixed(1)}%)`;
                } else if (databaseType === 'mobygames') {
                    option.value = match.game_id;
                    option.textContent = `${match.name} (${(match.similarity_score * 100).toFixed(1)}%)`;
                } else if (databaseType === 'steam') {
                    option.value = match.appid;
                    option.textContent = `${match.name} (${(match.similarity_score * 100).toFixed(1)}%)`;
                } else if (databaseType === 'igdb') {
                    option.value = match.id;
                    option.textContent = `${match.name} (${(match.similarity_score * 100).toFixed(1)}%)`;
                }
                
                select.appendChild(option);
            });
        }
        
        matchCell.appendChild(select);
        row.appendChild(matchCell);
        
        // Action buttons cell
        const actionCell = document.createElement('td');
        actionCell.style.padding = '6px 8px';
        actionCell.style.verticalAlign = 'middle';
        actionCell.style.textAlign = 'center';
        
        const validateBtn = document.createElement('button');
        validateBtn.className = 'btn btn-primary btn-sm';
        validateBtn.style.fontSize = '0.7rem';
        validateBtn.style.padding = '2px 6px';
        validateBtn.innerHTML = '<i class="bi bi-check"></i>';
        validateBtn.title = 'Apply Match';
        validateBtn.onclick = async () => {
            console.log('Button clicked - originalIndex:', originalIndex, 'databaseType:', databaseType);
            try {
                await this.validateGlobalMatch(originalIndex, databaseType);
            } catch (error) {
                console.error('Error in button click handler:', error);
                alert('Error in button click: ' + error.message);
            }
        };
        
        actionCell.appendChild(validateBtn);
        row.appendChild(actionCell);
        
        return row;
    }
    
    async validateGlobalMatch(index, databaseType = 'launchbox') {
        const select = document.getElementById(`globalMatchSelect_${index}`);
        if (!select || !select.value) {
            this.showAlert('Please select a match first', 'warning');
            return;
        }

        // Get the game path from the row data attribute
        const row = select.closest('tr');
        const gamePath = row && row.dataset && row.dataset.gamePath;
        if (!gamePath) {
            this.showAlert('Game path not found', 'error');
            return;
        }

        // Get the result directly from the Map using game path as key
        const result = this.globalMatchResults.get(gamePath);
        if (!result) {
            this.showAlert('Game data not found', 'error');
            return;
        }
        
        const gameName = result.game_name;
        const selectedIndex = parseInt(select.value);
        
        // Get the actual ID from the selected match
        let matchId = '';
        if (databaseType === 'launchbox') {
            const topMatches = result.top_matches || [];
            if (selectedIndex >= 0 && selectedIndex < topMatches.length) {
                matchId = topMatches[selectedIndex].database_id;
            }
        } else if (databaseType === 'mobygames') {
            const allMatches = result.all_matches || [];
            if (allMatches.length === 0) {
                this.showAlert('No MobyGames matches available', 'error');
                return;
            }
            if (selectedIndex >= 0 && selectedIndex < allMatches.length && allMatches[selectedIndex]) {
                matchId = allMatches[selectedIndex].game_id;
            } else {
                this.showAlert(`Invalid MobyGames match selected. Index: ${selectedIndex}, Array length: ${allMatches.length}`, 'error');
                return;
            }
        } else if (databaseType === 'steam') {
            const allMatches = result.all_matches || [];
            if (allMatches.length === 0) {
                this.showAlert('No Steam matches available', 'error');
                return;
            }
            if (selectedIndex >= 0 && selectedIndex < allMatches.length && allMatches[selectedIndex]) {
                matchId = allMatches[selectedIndex].appid;
            } else {
                this.showAlert(`Invalid Steam match selected. Index: ${selectedIndex}, Array length: ${allMatches.length}`, 'error');
                return;
            }
        } else if (databaseType === 'igdb') {
            const allMatches = result.all_matches || [];
            if (allMatches.length === 0) {
                this.showAlert('No IGDB matches available', 'error');
                return;
            }
            if (selectedIndex >= 0 && selectedIndex < allMatches.length && allMatches[selectedIndex]) {
                matchId = allMatches[selectedIndex].id;
            } else {
                this.showAlert(`Invalid IGDB match selected. Index: ${selectedIndex}, Array length: ${allMatches.length}`, 'error');
                return;
            }
        }
        
        if (!matchId) {
            this.showAlert('Invalid match selected', 'error');
            return;
        }
        
        // Apply the match based on database type
        if (databaseType === 'launchbox') {
            await this.applyLaunchboxMatch(gamePath, matchId);
        } else if (databaseType === 'mobygames') {
            await this.applyMobygamesMatch(gamePath, matchId);
        } else if (databaseType === 'steam') {
            await this.applySteamMatch(gamePath, matchId);
        } else if (databaseType === 'igdb') {
            await this.applyIgdbMatch(gamePath, matchId);
        }
        
        // Remove the row from the table
        const tableRow = select.closest('tr');
        if (tableRow) {
            tableRow.remove();
        }

        // Remove from results Map using game path as key
        this.globalMatchResults.delete(gamePath);
        
        // Check if all games are processed
        if (this.globalMatchResults.size === 0) {
            this.hideGlobalMatchModal();
            this.showAlert('All matches have been processed!', 'success');
        }
    }
    
    async applyLaunchboxMatch(gamePath, launchboxId) {
        try {
            // Find the game in the grid using ROM path
            const game = this.games.find(g => g.path === gamePath);
            if (game) {
                game.launchboxid = launchboxId;
                
                // Mark game as modified
                this.markGameAsModified(game);
                
                // Save changes to backend directly
                await this.saveGameChanges();
                
                this.showAlert(`LaunchBox ID set to ${launchboxId} for "${game.name}"`, 'success');
            } else {
                this.showAlert(`Game with path "${gamePath}" not found`, 'error');
            }
        } catch (error) {
            console.error('Error in applyLaunchboxMatch:', error);
            this.showAlert(`Error saving LaunchBox ID: ${error.message}`, 'danger');
        }
    }
    
    async applyMobygamesMatch(gamePath, mobygamesId) {
        try {
            // Find the game in the grid using ROM path
            const game = this.games.find(g => g.path === gamePath);
            if (game) {
                game.mobygamesid = mobygamesId;
                
                // Mark game as modified
                this.markGameAsModified(game);
                
                // Save changes to backend directly
                await this.saveGameChanges();
                
                this.showAlert(`MobyGames ID set to ${mobygamesId} for "${game.name}"`, 'success');
            } else {
                this.showAlert(`Game with path "${gamePath}" not found`, 'error');
            }
        } catch (error) {
            console.error('Error in applyMobygamesMatch:', error);
            this.showAlert(`Error saving MobyGames ID: ${error.message}`, 'danger');
        }
    }
    
    async applySteamMatch(gamePath, steamId) {
        try {
            // Find the game in the grid using ROM path
            const game = this.games.find(g => g.path === gamePath);
            if (game) {
                game.steamid = steamId;
                
                // Mark game as modified
                this.markGameAsModified(game);
                
                // Save changes to backend directly
                await this.saveGameChanges();
                
                this.showAlert(`Steam ID set to ${steamId} for "${game.name}"`, 'success');
            } else {
                this.showAlert(`Game with path "${gamePath}" not found`, 'error');
            }
        } catch (error) {
            console.error('Error in applySteamMatch:', error);
            this.showAlert(`Error saving Steam ID: ${error.message}`, 'danger');
        }
    }

    async applyIgdbMatch(gamePath, igdbId) {
        try {
            // Find the game in the grid using ROM path
            const game = this.games.find(g => g.path === gamePath);
            if (game) {
                game.igdbid = igdbId;
                
                // Mark game as modified
                this.markGameAsModified(game);
                
                // Save changes to backend directly
                await this.saveGameChanges();
                
                this.showAlert(`IGDB ID set to ${igdbId} for "${game.name}"`, 'success');
            } else {
                this.showAlert(`Game with path "${gamePath}" not found`, 'error');
            }
        } catch (error) {
            console.error('Error in applyIgdbMatch:', error);
            this.showAlert(`Error saving IGDB ID: ${error.message}`, 'danger');
        }
    }

    populateGlobalMatchTable(databaseType = 'launchbox') {
        const progressDiv = document.getElementById('globalMatchProgress');
        const tableDiv = document.getElementById('globalMatchTable');
        const emptyDiv = document.getElementById('globalMatchEmpty');
        const tbody = document.getElementById('globalMatchTableBody');
        
        if (!this.globalMatchResults || this.globalMatchResults.size === 0) {
            this.showGlobalMatchEmpty();
            return;
        }
        
        // Hide loading, show table
        if (progressDiv) progressDiv.style.display = 'none';
        if (tableDiv) tableDiv.style.display = 'block';
        if (emptyDiv) emptyDiv.style.display = 'none';
        
        // Clear existing rows
        if (tbody) {
            tbody.innerHTML = '';
        }
        
        // Convert Map to array and sort by highest matching score
        const sortedResults = Array.from(this.globalMatchResults.values()).sort((a, b) => {
            let scoreA = 0, scoreB = 0;
            
            if (databaseType === 'launchbox') {
                scoreA = a.top_matches && a.top_matches.length > 0 ? a.top_matches[0].score : 0;
                scoreB = b.top_matches && b.top_matches.length > 0 ? b.top_matches[0].score : 0;
            } else if (databaseType === 'mobygames' || databaseType === 'steam' || databaseType === 'igdb') {
                // Use best_match for consistency
                scoreA = (a.best_match && a.best_match.similarity_score) ? a.best_match.similarity_score : 0;
                scoreB = (b.best_match && b.best_match.similarity_score) ? b.best_match.similarity_score : 0;
            }
            
            return scoreB - scoreA; // Sort descending (highest first)
        });
        
        // Create rows for each game (now sorted by score)
        sortedResults.forEach((result, index) => {
            const row = this.createGlobalMatchRow(result, index, result.game_data.path, databaseType);
            if (tbody) {
                tbody.appendChild(row);
            }
        });
    }

    createGlobalMatchRow(result, index, gamePath, databaseType = 'launchbox') {
        const row = document.createElement('tr');
        row.id = `globalMatchRow_${index}`;
        row.dataset.gamePath = gamePath; // Store game path as data attribute
        row.style.height = '40px'; // Compact row height
        
        const gameName = result.game_name || 'Unknown';
        
        // Get current ID and matches based on database type
        let currentId = 'None';
        let topMatches = [];
        
        if (databaseType === 'launchbox') {
            currentId = result.existing_launchboxid || 'None';
            topMatches = result.top_matches || [];
        } else if (databaseType === 'mobygames') {
            currentId = result.existing_mobygamesid || 'None';
            topMatches = result.all_matches || [];
        } else if (databaseType === 'steam') {
            currentId = result.existing_steamid || 'None';
            topMatches = result.all_matches || [];
        } else if (databaseType === 'igdb') {
            currentId = result.existing_igdbid || 'None';
            topMatches = result.all_matches || [];
        }
        
        // Get publisher or developer from game data if available
        const gameData = result.game_data || {};
        const publisher = gameData.publisher || '';
        const developer = gameData.developer || '';
        
        // Format game name with publisher or developer if available
        let displayName = gameName;
        if (publisher && publisher.trim()) {
            displayName = `${gameName} (${publisher})`;
        } else if (developer && developer.trim()) {
            displayName = `${gameName} (${developer})`;
        }
        
        // Game name cell
        const nameCell = document.createElement('td');
        nameCell.style.padding = '6px 8px';
        nameCell.style.verticalAlign = 'middle';
        nameCell.style.fontSize = '0.75rem';
        nameCell.textContent = displayName;
        row.appendChild(nameCell);
        
        // Current ID cell
        const idCell = document.createElement('td');
        idCell.style.padding = '6px 8px';
        idCell.style.verticalAlign = 'middle';
        idCell.style.fontSize = '0.8rem';
        idCell.textContent = currentId;
        row.appendChild(idCell);
        
        // Best match dropdown cell
        const matchCell = document.createElement('td');
        matchCell.style.padding = '6px 8px';
        matchCell.style.verticalAlign = 'middle';
        const select = document.createElement('select');
        select.className = 'form-select form-select-sm';
        select.style.fontSize = '0.8rem';
        select.style.padding = '4px 6px';
        select.id = `globalMatchSelect_${index}`;
        
        // Add match options (already sorted by score, highest first)
        topMatches.forEach((match, matchIndex) => {
            const option = document.createElement('option');
            option.value = matchIndex;
            
            let score, name, publisher, id;
            
            if (databaseType === 'launchbox') {
                score = (match.score * 100).toFixed(1);
                name = match.matched_name;
                publisher = match.publisher || 'Unknown Publisher';
                id = match.database_id;
            } else if (databaseType === 'steam') {
                score = (match.similarity_score * 100).toFixed(1);
                name = match.name;
                publisher = match.publisher || 'Unknown Publisher';
                id = match.appid;
            } else if (databaseType === 'mobygames') {
                score = (match.similarity_score * 100).toFixed(1);
                name = match.name;
                publisher = match.publisher || 'Unknown Publisher';
                id = match.game_id;
            } else if (databaseType === 'igdb') {
                score = (match.similarity_score * 100).toFixed(1);
                name = match.name;
                publisher = match.publisher || 'Unknown Publisher';
                id = match.id;
            }
            
            let optionText = `${score}%: ${name} (${publisher})`;
            
            // Limit text to 70 characters and add ... if truncated
            if (optionText.length > 70) {
                optionText = optionText.substring(0, 67) + '...';
            }
            
            option.textContent = optionText;
            option.dataset.score = databaseType === 'launchbox' ? match.score : match.similarity_score;
            
            // Set the correct data attribute based on database type
            if (databaseType === 'launchbox') {
                option.dataset.launchboxId = id;
            } else if (databaseType === 'mobygames') {
                option.dataset.gameId = id;
            } else if (databaseType === 'steam') {
                option.dataset.appId = id;
            }
            
            select.appendChild(option);
        });
        
        // Auto-select the first (highest scoring) match
        if (topMatches.length > 0) {
            select.value = '0'; // Select the first option (highest score)
        }
        
        matchCell.appendChild(select);
        row.appendChild(matchCell);
        
        // Actions cell
        const actionsCell = document.createElement('td');
        actionsCell.style.padding = '6px 8px';
        actionsCell.style.verticalAlign = 'middle';
        const validateBtn = document.createElement('button');
        validateBtn.className = 'btn btn-success btn-sm';
        validateBtn.style.fontSize = '0.75rem';
        validateBtn.style.padding = '4px 8px';
        validateBtn.innerHTML = '<i class="bi bi-check-lg"></i> Validate';
        validateBtn.disabled = false; // Always enabled since we auto-select
        validateBtn.onclick = async () => {
            try {
                await this.validateGlobalMatch(index, databaseType);
            } catch (error) {
                console.error('Error in button click handler:', error);
                alert('Error in button click: ' + error.message);
            }
        };
        
        actionsCell.appendChild(validateBtn);
        row.appendChild(actionsCell);
        
        // No change listener needed since validate button is always enabled
        
        return row;
    }

    async generate2DBoxForSelected() {
        try {
            if (!this.selectedGames || this.selectedGames.length === 0) {
                this.showAlert('Please select at least one game first', 'warning');
                return;
            }
            
            const button = document.getElementById('global2DBoxGeneratorBtn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Generating...';
            }

            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
            const response = await fetch('/api/generate-2d-box', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    selected_games: selectedGamePaths
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`2D box generation started for ${data.games_count} games.`, 'success');
                // Refresh the task grid to show the new task
                this.refreshTasks();
            } else {
                this.showAlert('Error starting 2D box generation: ' + (data.error || 'Unknown error'), 'danger');
            }
            
        } catch (error) {
            this.showAlert('Error starting 2D box generation: ' + error.message, 'danger');
        } finally {
            // Reset button state
            const button = document.getElementById('global2DBoxGeneratorBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-image"></i> 2D Box Generator';
            }
        }
    }

    openYoutubeDownloadModal() {
        if (!this.currentSystem) {
            this.showAlert('No system selected', 'error');
            return;
        }
        
        // Open the YouTube download modal
        const modal = new bootstrap.Modal(document.getElementById('youtubeDownloadModal'));
        modal.show();
    }

    async startYoutubeDownload() {
        if (!this.currentSystem) {
            this.showAlert('No system selected', 'error');
            return;
        }

        try {
            // Get form values
            const startTime = parseInt(document.getElementById('youtubeStartTime').value) || 0;
            const autoCrop = document.getElementById('youtubeAutoCrop').checked;
            const overwriteExisting = document.getElementById('youtubeOverwriteExisting').checked;
            const playlistIndex = parseInt(document.getElementById('youtubePlaylistIndex').value) || 1;

            // Determine which games to process
            const gamesToProcess = this.selectedGames.length > 0 ? this.selectedGames : this.games;
            
            // Filter games that have YouTube URLs or Steam Store URLs
            const gamesWithYoutube = gamesToProcess.filter(game => {
                const youtubeUrl = game.youtubeurl || '';
                const hasYoutube = youtubeUrl.trim() !== '' && youtubeUrl.toLowerCase().includes('youtube');
                const hasSteamStore = youtubeUrl.trim() !== '' && youtubeUrl.toLowerCase().includes('store.steampowered.com');
                const hasValidUrl = hasYoutube || hasSteamStore;
                return hasValidUrl;
            });

            if (gamesWithYoutube.length === 0) {
                this.showAlert('No games with YouTube or Steam Store URLs found to download', 'warning');
                return;
            }

            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('youtubeDownloadModal'));
            if (modal) {
                modal.hide();
            }

            // Switch to Task Management tab
            this.switchTab('task-management');

            // Create request body
            const requestBody = {
                selected_games: gamesWithYoutube.map(game => game.path),
                start_time: startTime,
                auto_crop: autoCrop,
                overwrite_existing: overwriteExisting,
                playlist_index: playlistIndex
            };

            // Make the API request
            const response = await fetch(`/api/youtube-download-batch/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.showAlert(`YouTube download batch task started for ${data.games_count} games.`, 'success');
                // Refresh the task grid to show the new task
                this.refreshTasks();
            } else {
                this.showAlert('Error starting YouTube download batch: ' + (data.error || 'Unknown error'), 'danger');
            }

        } catch (error) {
            this.showAlert('Error starting YouTube download batch: ' + error.message, 'danger');
        }
    }
    
    showNextBestMatchModal() {
        if (!this.pendingBestMatchResults || this.currentBestMatchIndex >= this.pendingBestMatchResults.length) {
            // All games processed
            this.pendingBestMatchResults = null;
            this.currentBestMatchIndex = 0;
            this.showAlert('All games have been processed', 'success');
            return;
        }
        
        const currentResult = this.pendingBestMatchResults[this.currentBestMatchIndex];
        const gameName = currentResult.game_name;
        const gamePath = currentResult.game_path || null; // Use game path if available
        const topMatches = currentResult.top_matches;

        // Show the modal with the current game's matches
        this.showPartialMatches(gameName, topMatches, 'global', gamePath);
    }
    
    moveToPrevGame() {
        if (this.pendingBestMatchResults && this.currentBestMatchIndex > 0) {
            this.currentBestMatchIndex--;
            const currentGame = this.pendingBestMatchResults[this.currentBestMatchIndex];
            
            // Ensure modal state is properly managed during navigation
            this.isModalOpen = true;
            const gamePath = currentGame.game_path || null; // Use game path if available
            this.showPartialMatches(currentGame.game_name, currentGame.top_matches, 'global', gamePath);
        }
    }
    
    moveToNextGame() {
        // Don't close the modal, just update the content
        // Move to next game
        this.currentBestMatchIndex++;
        
        // Ensure modal state is properly managed during navigation
        this.isModalOpen = true;
        
        // Show next game's matches immediately
        this.showNextBestMatchModal();
    }
    
    async checkSystemMapping(scraperType) {
        if (!this.currentSystem) return false;
        
        try {
            // Add cache-busting parameter to ensure fresh data
            const response = await fetch(`/api/systems?t=${Date.now()}`);
            const data = await response.json();
            
            if (data.success) {
                const systemConfig = data.systems[this.currentSystem];
                
                if (systemConfig) {
                    // Map frontend scraper types to backend field names
                    const fieldMapping = {
                        'launchbox': 'launchbox',
                        'screenscraper': 'screenscraper', 
                        'igdb': 'igdb',
                        'mobygames': 'mobygames'
                    };
                    
                    const fieldName = fieldMapping[scraperType];
                    if (fieldName) {
                        const value = systemConfig[fieldName];
                        // Check if the value exists and is not empty
                        // Handle both string and number values (IGDB and ScreenScraper use numeric IDs)
                        return value !== null && value !== undefined && value !== '' && 
                               (typeof value === 'number' || value.toString().trim() !== '');
                    }
                }
            }
            return false;
        } catch (error) {
            console.error('Error checking system mapping:', error);
            return false;
        }
    }

    async openSystemsConfigForCurrentSystem(scraperType) {
        // Open the dedicated scraper configuration modal
        this.openScraperConfigModal(scraperType);
    }

    async openScraperConfigModal(scraperType) {
        // Set the current system name
        document.getElementById('currentSystemName').textContent = this.currentSystem;
        
        // Load current mappings
        await this.loadCurrentSystemMappings();
        
        // Highlight the specific scraper field
        this.highlightScraperField(scraperType);
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('systemScraperConfigModal'));
        modal.show();
    }

    async loadCurrentSystemMappings() {
        try {
            // Load platform data for comboboxes
            const [platforms, screenscraperSystems, igdbPlatforms, mobygamesSystems, datscrapperFiles] = await Promise.all([
                this.loadLaunchBoxPlatforms(),
                this.loadScreenScraperSystems(),
                this.loadIgdbPlatforms(),
                this.loadMobygamesSystems(),
                this.loadDatscrapperFiles()
            ]);
            
            // Debug: Log what we got
            console.log('Platform data loaded:', {
                platforms: platforms,
                platformsType: typeof platforms,
                platformsIsArray: Array.isArray(platforms),
                platformsLength: platforms ? platforms.length : 'undefined'
            });
            
            // Populate LaunchBox combobox
            this.populateCombobox('launchboxMapping', platforms, 'platform');
            
            // Populate ScreenScraper combobox
            this.populateCombobox('screenscraperMapping', screenscraperSystems, 'system');
            
            // Populate IGDB combobox
            this.populateCombobox('igdbMapping', igdbPlatforms, 'igdb_platform');
            
            // Populate MobyGames combobox
            this.populateCombobox('mobygamesMapping', mobygamesSystems, 'system');
            
            // Populate DAT Scrapper combobox
            await this.populateDatscrapperMapping();
            
            // Load current system mappings
            const response = await fetch('/api/systems');
            const data = await response.json();
            
            if (data.success && data.systems[this.currentSystem]) {
                const systemConfig = data.systems[this.currentSystem];
                
                // Set selected values
                document.getElementById('launchboxMapping').value = systemConfig.launchbox || '';
                document.getElementById('igdbMapping').value = systemConfig.igdb || '';
                document.getElementById('mobygamesMapping').value = systemConfig.mobygames || '';
                document.getElementById('screenscraperMapping').value = systemConfig.screenscraper || '';
                document.getElementById('datscrapperMapping').value = systemConfig.dat_file || '';
                
                // Set extensions value
                const extensions = systemConfig.extensions || [];
                document.getElementById('extensionsMapping').value = extensions.join(', ');
            }
        } catch (error) {
            console.error('Error loading system mappings:', error);
            this.showAlert('Error loading current system mappings', 'danger');
        }
    }

    populateCombobox(selectId, data, type) {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Clear existing options except the first one
        select.innerHTML = select.querySelector('option').outerHTML;
        
        if (Array.isArray(data) && data.length > 0) {
            data.forEach(item => {
                const option = document.createElement('option');
                if (type === 'platform') {
                    // For LaunchBox platforms (simple strings)
                    option.value = item;
                    option.textContent = item;
                } else if (type === 'system') {
                    // For ScreenScraper and MobyGames systems (objects with id/name)
                    option.value = item.id || item;
                    option.textContent = item.name || item;
                } else if (type === 'igdb_platform') {
                    // For IGDB platforms (objects with id/name)
                    option.value = item.id;
                    option.textContent = item.name;
                }
                select.appendChild(option);
            });
        } else {
            // Add a "No data available" option
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No data available';
            option.disabled = true;
            select.appendChild(option);
        }
    }

    async populateDatscrapperMapping() {
        try {
            const response = await fetch('/api/datscrapper/files');
            const data = await response.json();
            
            const select = document.getElementById('datscrapperMapping');
            if (!select) return;
            
            // Clear existing options except the first one
            select.innerHTML = '<option value="">Select DAT file...</option>';
            
            if (data.success && data.files) {
                data.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.filename;
                    option.textContent = `${file.filename} (${(file.size / 1024).toFixed(1)} KB)`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading DAT files:', error);
        }
    }

    highlightScraperField(scraperType) {
        // Remove existing highlights
        const fields = ['launchboxMapping', 'igdbMapping', 'mobygamesMapping', 'screenscraperMapping', 'datscrapperMapping'];
        fields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.classList.remove('border-warning');
                field.style.backgroundColor = '';
                field.style.borderColor = '';
            }
        });
        
        // Highlight the specific scraper field
        const fieldMap = {
            'launchbox': 'launchboxMapping',
            'igdb': 'igdbMapping',
            'mobygames': 'mobygamesMapping',
            'screenscraper': 'screenscraperMapping',
            'datscrapper': 'datscrapperMapping'
        };
        
        const targetFieldId = fieldMap[scraperType];
        if (targetFieldId) {
            const targetField = document.getElementById(targetFieldId);
            if (targetField) {
                targetField.classList.add('border-warning');
                targetField.style.borderColor = '#ffc107';
                targetField.style.backgroundColor = '#fff3cd';
                targetField.focus();
            }
        }
    }
    
    async scrapLaunchbox() {
        if (!this.currentSystem) return;
        
        // Check if LaunchBox system mapping exists
        const hasMapping = await this.checkSystemMapping('launchbox');
        if (!hasMapping) {
            this.showAlert(`No LaunchBox system mapping configured for ${this.currentSystem}. Opening configuration...`, 'warning');
            await this.openSystemsConfigForCurrentSystem('launchbox');
            return;
        }
        
        try {
            // Check if scraping is already running
            const button = document.getElementById('scrapLaunchboxBtn');
            const isRunning = button.textContent.includes('Stop');
            
            if (isRunning) {
                // Stop scraping
                await this.stopScraping();
                return;
            }
            
            // Clear previous log history and reset tracking
            this.logHistory = [];
            this.lastProcessedGame = null;
            
            // Switch to Task Management tab to show task progress
            this.switchTab('task-management');
            
            // Determine scraping mode
            const isFullCollection = this.selectedGames.length === 0;
            const gamesToScrape = isFullCollection ? this.games : this.selectedGames;
            
            // Get force download setting
            const forceDownload = document.getElementById('forceDownloadImagesModal').checked;
            
            // Get overwrite text fields setting
            const overwriteTextFields = document.getElementById('overwriteTextFieldsLaunchbox').checked;
            
            // Get selected fields for LaunchBox scraping
            const selectedFields = await this.getSelectedLaunchboxFields();
            
            const requestBody = {
                selected_games: gamesToScrape.map(game => game.path),
                force_download: forceDownload,
                overwrite_text_fields: overwriteTextFields,
                selected_fields: selectedFields
            };
            
            const response = await fetch(`/api/scrap-launchbox/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (response.ok) {
                // Progress updates are now handled by the task panel

                // Show success message
                if (isFullCollection) {
                    this.showAlert(`Launchbox scraping started for entire collection (${gamesToScrape.length} games)`, 'success');
                } else {
                    this.showAlert(`Launchbox scraping started for ${gamesToScrape.length} selected game${gamesToScrape.length > 1 ? 's' : ''}`, 'success');
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Unknown error', 'danger');
            }
        } catch (error) {
            this.showAlert('Error starting Launchbox scraping', 'danger');
        }
    }
    
    async stopScraping() {
        try {
            const response = await fetch('/api/scrap-launchbox-stop', {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                this.showAlert(`Error stopping: ${errorData.error || 'Unknown error'}`, 'danger');
                return;
            }
            
            this.showAlert('Stop signal sent to scraping process...', 'info');
            
            
        } catch (error) {
            this.showAlert(`Error stopping: ${error.message}`, 'danger');
        }
    }

    

    async waitForTaskCompletion() {
        // Wait for task to complete by polling task status
        let attempts = 0;
        const maxAttempts = 60; // Wait up to 5 minutes
        
        while (attempts < maxAttempts) {
            try {
                const response = await fetch('/api/task/status-and-queue', {
                    headers: {
                        'Accept-Encoding': 'gzip, deflate' // Enable compression
                    }
                });
                if (response.ok) {
                    const data = await response.json();
                    const status = data.current_task;
                    if (status.status === 'completed' || status.status === 'error' || status.status === 'waiting_confirmation') {
                        return; // Task completed or waiting for confirmation
                    }
                }
            } catch (error) {
            }
            
            // Wait 5 seconds before next check
            await new Promise(resolve => setTimeout(resolve, 5000));
            attempts++;
        }
        
        throw new Error('Task did not complete within expected time');
    }

    showRomScanConfirmation(scanSummary) {
        const { new_roms, missing_roms, total_existing, total_rom_files, is_initial_import } = scanSummary;
        
        // Create modal HTML
        const modalId = 'romScanConfirmationModal';
        let modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${modalId}Label">ROM Scan Results</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6 class="text-success">Summary</h6>
                                    <ul class="list-unstyled">
                                        <li><strong>New ROMs found:</strong> <span class="badge bg-success">${new_roms.length}</span></li>
                                        <li><strong>Games with missing ROMs:</strong> <span class="badge bg-danger">${missing_roms.length}</span></li>
                                        <li><strong>Total existing games:</strong> <span class="badge bg-info">${total_existing}</span></li>
                                        <li><strong>Total ROM files:</strong> <span class="badge bg-primary">${total_rom_files}</span></li>
                                    </ul>
                                </div>
                                <div class="col-md-6">
                                    <h6 class="text-warning">Actions Required</h6>
                                    <div class="d-grid gap-2">`;
        
        // Show different buttons based on whether there are changes
        if (new_roms.length > 0 || missing_roms.length > 0) {
            modalHTML += `
                                        <button type="button" class="btn btn-success btn-sm" onclick="window.gameManager.confirmRomScan('proceed')" data-bs-dismiss="modal">
                                            <i class="fas fa-check"></i> Proceed with Changes
                                        </button>
                                        <button type="button" class="btn btn-secondary btn-sm" onclick="window.gameManager.confirmRomScan('cancel')" data-bs-dismiss="modal">
                                            <i class="fas fa-times"></i> Cancel
                                        </button>`;
        } else {
            modalHTML += `
                                        <button type="button" class="btn btn-success btn-sm" onclick="window.gameManager.confirmRomScan('proceed')" data-bs-dismiss="modal">
                                            <i class="fas fa-check"></i> Continue (No Changes)
                                        </button>
                                        <button type="button" class="btn btn-secondary btn-sm" onclick="window.gameManager.confirmRomScan('cancel')" data-bs-dismiss="modal">
                                            <i class="fas fa-times"></i> Cancel
                                        </button>`;
        }
        
        modalHTML += `
                                    </div>
                                </div>
                            </div>`;
        
        // Only show detailed game lists if it's not an initial import
        if (new_roms.length > 0 && !is_initial_import) {
            modalHTML += `
                            <hr>
                            <div class="mb-3">
                                <h6 class="text-success">New ROMs to Add</h6>
                                <div class="small text-muted">
                                    <div class="row">`;
            new_roms.slice(0, 10).forEach(rom => {
                modalHTML += `<div class="col-md-6">• ${rom}</div>`;
            });
            if (new_roms.length > 10) {
                modalHTML += `<div class="col-md-6">• ... and ${new_roms.length - 10} more</div>`;
            }
            modalHTML += `
                                </div>
                            </div>`;
        }
        
        // Only show detailed game lists if it's not an initial import
        if (missing_roms.length > 0 && !is_initial_import) {
            modalHTML += `
                            <hr>
                            <div class="mb-3">
                                <h6 class="text-danger">Games to Remove (Missing ROMs)</h6>
                                <div class="small text-muted">
                                    <div class="row">`;
            missing_roms.slice(0, 10).forEach(game => {
                modalHTML += `<div class="col-md-6">• ${game.name} <small class="text-muted">(${game.path})</small></div>`;
            });
            if (missing_roms.length > 10) {
                modalHTML += `<div class="col-md-6">• ... and ${missing_roms.length - 10} more</div>`;
            }
            modalHTML += `
                                </div>
                            </div>`;
        }
        
        // Only show warning about removing games if there are missing ROMs and it's not an initial import
        if (missing_roms.length > 0 && !is_initial_import) {
            modalHTML += `
                            <div class="alert alert-warning mt-3">
                                <i class="fas fa-exclamation-triangle"></i>
                                <strong>Warning:</strong> This action will remove ${missing_roms.length} games with missing ROM files from your gamelist.xml. This cannot be undone.
                            </div>`;
        }
        
        modalHTML += `
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>`;
        
        // Show different button text based on whether there are changes
        if (new_roms.length > 0 || missing_roms.length > 0) {
            modalHTML += `
                            <button type="button" class="btn btn-success" onclick="window.gameManager.confirmRomScan('proceed')" data-bs-dismiss="modal">
                                <i class="fas fa-check"></i> Proceed with Changes
                            </button>`;
        } else {
            modalHTML += `
                            <button type="button" class="btn btn-success" onclick="window.gameManager.confirmRomScan('proceed')" data-bs-dismiss="modal">
                                <i class="fas fa-check"></i> Continue (No Changes)
                            </button>`;
        }
        
        modalHTML += `
                        </div>
                    </div>
                </div>
            </div>`;
        
        // Remove existing modal if it exists
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();
        
        // Add event handler for modal close (cross button or ESC key)
        const modalElement = document.getElementById(modalId);
        
        // Remove any existing event listeners to prevent duplicates
        modalElement.removeEventListener('hidden.bs.modal', this.handleRomScanModalClose);
        
        // Create a bound handler function
        this.handleRomScanModalClose = () => {
            // Only cancel if no button was clicked (user closed with X or ESC)
            if (!this.romScanModalActionTaken) {
                this.confirmRomScan('cancel');
            }
            // Reset the flag for next time
            this.romScanModalActionTaken = false;
        };
        
        // Add the event listener
        modalElement.addEventListener('hidden.bs.modal', this.handleRomScanModalClose);
        
        // Reset the action flag
        this.romScanModalActionTaken = false;
    }

    async confirmRomScan(action) {
        try {
            // Set flag to indicate user has taken an action
            this.romScanModalActionTaken = true;
            
            // Use the ROM scan confirmation endpoint for both cancel and proceed actions
            const response = await fetch(`/api/rom-system/${this.currentSystem}/scan-roms-confirm`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    if (result.action_taken === 'completed') {
                        // Reload the system to get updated game list
                        await this.loadRomSystem(this.currentSystem);
                        this.showAlert(`ROM scan completed! Added ${result.new_games_added} new games, removed ${result.games_removed} games with missing ROMs.`, 'success');
                        
                        // Continue with media scan after ROM confirmation
                        await this.continueWithMediaScan();
                    } else if (result.action_taken === 'cancelled') {
                        this.showAlert('ROM scan cancelled.', 'info');
                        // Restore button state when cancelled
                        this.restoreScanButtonState();
                    }
                } else {
                    this.showAlert(result.error || 'Error confirming ROM scan', 'danger');
                    // Restore button state on error
                    this.restoreScanButtonState();
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Error confirming ROM scan', 'danger');
                // Restore button state on error
                this.restoreScanButtonState();
            }
        } catch (error) {
            this.showAlert('Error confirming ROM scan', 'danger');
            // Restore button state on error
            this.restoreScanButtonState();
        }
    }

    async continueWithMediaScan() {
        try {
            this.showAlert('Starting media scan...', 'info');
            
            // Wait a moment for any pending operations to complete
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Then scan media files
            const mediaResponse = await fetch(`/api/rom-system/${this.currentSystem}/scan-media`, {
                method: 'POST'
            });
            
            if (mediaResponse.ok) {
                const mediaResult = await mediaResponse.json();
                if (mediaResult.success) {
                    this.showAlert('Media scan completed successfully!', 'success');
                    
                    // Reload the current system to get updated data (uses efficient updates)
                    await this.loadRomSystem(this.currentSystem);
                    
                    // Ensure games count is updated
                    this.updateGamesCount();
                } else {
                    this.showAlert(mediaResult.error || 'Media scan failed', 'danger');
                }
            } else if (mediaResponse.status === 409) {
                // Task conflict - another task is running
                const errorData = await mediaResponse.json();
                if (errorData.queued) {
                    this.showAlert(`Task queued: ${errorData.queue_message}`, 'warning');
                } else {
                    this.showAlert(errorData.error || 'Task conflict - another task is running', 'danger');
                }
            } else {
                const errorData = await mediaResponse.json();
                this.showAlert(errorData.error || 'Media scan failed', 'danger');
            }
        } catch (error) {
            this.showAlert('Error during media scan: ' + error.message, 'danger');
        } finally {
            // Restore button state
            this.restoreScanButtonState();
        }
    }

    restoreScanButtonState() {
        const button = document.getElementById('unifiedScanBtn');
        if (button) {
            button.innerHTML = '<i class="bi bi-search"></i>';
            button.disabled = false;
        } else {
        }
    }

    async unifiedScan() {
        if (!this.currentSystem) return;
        
        let button = null;
        let originalText = '';
        
        try {
            // Show loading state
            button = document.getElementById('unifiedScanBtn');
            if (!button) {
                return;
            }
            
            originalText = button.innerHTML;
            button.innerHTML = '<i class="spinner-border spinner-border-sm"></i>';
            button.disabled = true;
            
            // Switch to Task Management tab to show task progress
            this.switchTab('task-management');
            
            // First, scan ROM files
            this.showAlert('Starting ROM scan...', 'info');
            const romResponse = await fetch(`/api/rom-system/${this.currentSystem}/scan-roms`, {
                method: 'POST'
            });
            
            if (romResponse.ok) {
                const romResult = await romResponse.json();
                if (romResult.success) {
                    this.showAlert('ROM scan started. Please wait for completion.', 'info');
                    
                    // Wait for task completion and get results
                    await this.waitForTaskCompletion();
                    
                    // Get scan results
                    const resultsResponse = await fetch(`/api/rom-system/${this.currentSystem}/scan-roms`);
                    if (resultsResponse.ok) {
                        const result = await resultsResponse.json();
                        if (result.success) {
                            if (result.action_taken === 'requires_confirmation') {
                                // Show confirmation popup for games with missing ROMs
                                this.showRomScanConfirmation(result.scan_summary);
                                // Don't continue to media scan - user needs to confirm first
                                // Restore button state immediately since we're waiting for user confirmation
                                this.restoreScanButtonState();
                                return;
                            } else {
                                // Reload the system to get updated game list
                                // Add a small delay to ensure gamelist.xml is written
                                await new Promise(resolve => setTimeout(resolve, 1000));
                                await this.loadRomSystem(this.currentSystem);
                                this.showAlert('ROM scan completed. Starting media scan...', 'success');
                            }
                            
                            // Continue with media scan after ROM scan
                            await this.continueWithMediaScan();
                        } else {
                            this.showAlert(result.error || 'Error getting ROM scan results', 'danger');
                        }
                    } else {
                        this.showAlert('Error getting ROM scan results', 'danger');
                    }
                } else {
                    this.showAlert(romResult.error || 'Error starting ROM scan', 'danger');
                }
            } else {
                const errorData = await romResponse.json();
                this.showAlert(errorData.error || 'Error starting ROM scan', 'danger');
            }
        } catch (error) {
            this.showAlert('Error during unified scan: ' + error.message, 'danger');
        } finally {
            // Restore button state only if it's still in loading state
            // (don't restore if already restored for confirmation case or media scan)
            if (button && originalText && button.disabled) {
                button.innerHTML = originalText;
                button.disabled = false;
            } else if (button && !button.disabled) {
                // Button is already enabled, ensure it has the correct text with icon
                this.restoreScanButtonState();
            }
        }
    }

    async saveGamelist() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }

        // Show the modal and load differences
        await this.showGamelistSaveModal();
    }

    async showGamelistSaveModal() {
        // Set system name in modal
        document.getElementById('gamelistSaveSystemName').textContent = this.currentSystem;
        document.getElementById('gamelistSaveSourcePath').textContent = this.currentSystem;
        document.getElementById('gamelistSaveDestPath').textContent = this.currentSystem;
        document.getElementById('gamelistSaveDestPath2').textContent = this.currentSystem;
        
        // Add event listener for orphan media checkbox
        const deleteOrphanMediasCheckbox = document.getElementById('deleteOrphanMedias');
        const orphanMediaWarning = document.getElementById('orphanMediaWarning');
        
        deleteOrphanMediasCheckbox.addEventListener('change', function() {
            if (this.checked) {
                orphanMediaWarning.style.display = 'block';
            } else {
                orphanMediaWarning.style.display = 'none';
            }
        });

        // Show loading state
        document.getElementById('gamelistSaveLoading').style.display = 'block';
        document.getElementById('gamelistSaveContent').style.display = 'none';

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('gamelistSaveModal'));
        modal.show();

        try {
            // Fetch differences
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist-diff`);
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.populateGamelistSaveModal(result);
                } else {
                    this.showGamelistSaveError(result.error || 'Failed to load differences');
                }
            } else {
                const errorData = await response.json();
                this.showGamelistSaveError(errorData.error || 'Failed to load differences');
            }
        } catch (error) {
            this.showGamelistSaveError('Error loading differences: ' + error.message);
        }
    }

    populateGamelistSaveModal(data) {
        // Hide loading, show content
        document.getElementById('gamelistSaveLoading').style.display = 'none';
        document.getElementById('gamelistSaveContent').style.display = 'block';

        // Update counts
        document.getElementById('gamesAddedCount').textContent = data.games_added;
        document.getElementById('gamesRemovedCount').textContent = data.games_removed;
        document.getElementById('mediaAddedCount').textContent = data.media_added;
        document.getElementById('mediaRemovedCount').textContent = data.media_removed;
        document.getElementById('totalGamesCount').textContent = data.total_games;
        document.getElementById('totalMediaCount').textContent = data.total_media;

        // Update game lists
        const addedList = document.getElementById('gamesAddedList');
        const removedList = document.getElementById('gamesRemovedList');

        if (data.games_added_list.length > 0) {
            addedList.innerHTML = data.games_added_list.map(game => 
                `<div class="mb-1"><strong>${game.name}</strong><br><small class="text-muted">${game.path}</small></div>`
            ).join('');
        } else {
            addedList.innerHTML = '<div class="text-muted">No games added</div>';
        }

        if (data.games_removed_list.length > 0) {
            removedList.innerHTML = data.games_removed_list.map(game => 
                `<div class="mb-1"><strong>${game.name}</strong><br><small class="text-muted">${game.path}</small></div>`
            ).join('');
        } else {
            removedList.innerHTML = '<div class="text-muted">No games removed</div>';
        }
    }

    showGamelistSaveError(errorMessage) {
        // Hide loading, show content with error
        document.getElementById('gamelistSaveLoading').style.display = 'none';
        document.getElementById('gamelistSaveContent').style.display = 'block';

        // Show error in all sections
        const errorHtml = `<div class="alert alert-danger">${errorMessage}</div>`;
        document.getElementById('gamesAddedList').innerHTML = errorHtml;
        document.getElementById('gamesRemovedList').innerHTML = errorHtml;
        
        // Disable save button
        document.getElementById('confirmGamelistSave').disabled = true;
    }

    async confirmGamelistSave() {
        const button = document.getElementById('confirmGamelistSave');
        const originalText = button.innerHTML;

        try {
            // Show loading state
            button.innerHTML = '<i class="spinner-border spinner-border-sm"></i>';
            button.disabled = true;

            // Get checkbox state
            const deleteOrphanMedias = document.getElementById('deleteOrphanMedias').checked;

            // Call the save API
            const response = await fetch(`/api/rom-system/${this.currentSystem}/save-gamelist`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    delete_orphan_medias: deleteOrphanMedias
                })
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert(result.message, 'success');
                    // Close the modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('gamelistSaveModal'));
                    modal.hide();
                } else {
                    this.showAlert(result.error || 'Failed to save gamelist', 'danger');
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Failed to save gamelist', 'danger');
            }
        } catch (error) {
            this.showAlert('Error saving gamelist: ' + error.message, 'danger');
        } finally {
            // Restore button state
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async showForceImportModal() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }

        // Set system name in modal
        document.getElementById('forceImportSystemName').textContent = this.currentSystem;
        document.getElementById('forceImportSystemName2').textContent = this.currentSystem;

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('forceImportGamelistModal'));
        modal.show();
    }

    async confirmForceImport() {
        const button = document.getElementById('confirmForceImportBtn');
        const originalText = button.innerHTML;

        try {
            // Show loading state
            button.innerHTML = '<i class="spinner-border spinner-border-sm"></i>';
            button.disabled = true;

            // Call the force import API
            const response = await fetch(`/api/rom-system/${this.currentSystem}/force-import-gamelist`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert(result.message, 'success');
                    // Close the modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('forceImportGamelistModal'));
                    modal.hide();
                    
                    // Reload the current system to reflect the imported data
                    await this.loadRomSystem(this.currentSystem);
                } else {
                    this.showAlert(result.error || 'Failed to force import gamelist', 'danger');
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Failed to force import gamelist', 'danger');
            }
        } catch (error) {
            this.showAlert('Error force importing gamelist: ' + error.message, 'danger');
        } finally {
            // Restore button state
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    clearImageCache() {
        // Add cache-busting parameter to all images on the page
        const images = document.querySelectorAll('img');
        let updatedCount = 0;
        
        images.forEach(img => {
            const src = img.src;
            if (src && !src.includes('?cache_bust=')) {
                // Add cache-busting parameter
                const separator = src.includes('?') ? '&' : '?';
                img.src = src + separator + 'cache_bust=' + Date.now();
                updatedCount++;
            }
        });
        
        // Also update any background images in CSS
        const elementsWithBgImages = document.querySelectorAll('[style*="background-image"]');
        elementsWithBgImages.forEach(element => {
            const style = element.getAttribute('style');
            if (style && style.includes('background-image') && !style.includes('cache_bust=')) {
                const urlMatch = style.match(/url\(['"]?([^'"]+)['"]?\)/);
                if (urlMatch) {
                    const url = urlMatch[1];
                    const separator = url.includes('?') ? '&' : '?';
                    const newUrl = url + separator + 'cache_bust=' + Date.now();
                    element.style.backgroundImage = style.replace(url, newUrl);
                    updatedCount++;
                }
            }
        });
        
        // Show success message
        this.showAlert(`Image cache cleared! Updated ${updatedCount} images.`, 'success');
        
        // If we have a grid, refresh it to reload all images
        if (this.gridApi) {
            this.gridApi.refreshCells({ force: true });
        }
    }

    async deleteGame(game) {
        // Show confirmation modal for single game deletion
        this.showSingleGameDeleteConfirmation(game);
    }

    showSingleGameDeleteConfirmation(game) {
        // Update the modal with the single game info
        document.getElementById('deleteGameCount').textContent = '1';
        
        // Store the game to delete
        this.gameToDelete = game;
        
        // Show the confirmation modal
        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        modal.show();
    }

    async confirmSingleGameDelete() {
        if (!this.gameToDelete) return;

        try {
            // Delete associated ROM and media files
            const deletedFiles = await this.deleteGameFiles(this.gameToDelete);
            
            // Remove from local array using ROM file path as unique identifier
            this.games = this.games.filter(g => g.path !== this.gameToDelete.path);
            
            // Update gamelist.xml to remove deleted game
            await this.updateGamelistAfterDeletion([this.gameToDelete.path]);
            
            // Refresh grid
            await this.refreshGridData();
            this.updateGamesCount();
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
            modal.hide();
            
            // Show success message
            const fileCount = deletedFiles.length;
            const message = `Successfully deleted game "${this.gameToDelete.name}" and ${fileCount} associated file(s)`;
            this.showAlert(message, 'success');

            // Clear the stored game
            this.gameToDelete = null;

        } catch (error) {
            this.showAlert('Error deleting game', 'danger');
        }
    }

    async deleteGameWithoutConfirmation(game) {
        try {
            // Delete associated ROM and media files
            const deletedFiles = await this.deleteGameFiles(game);
            
            // Remove from local array using ROM file path as unique identifier
            this.games = this.games.filter(g => g.path !== game.path);
            
            // Update gamelist.xml to remove deleted game
            await this.updateGamelistAfterDeletion([game.path]);
            
            // Refresh grid
            await this.refreshGridData();
            this.updateGamesCount();
            
            return deletedFiles;

        } catch (error) {
            this.showAlert('Error deleting game', 'danger');
            throw error;
        }
    }

    async saveGameChanges() {
        
        if (this.modifiedGames.size === 0) {
            this.showAlert('No changes to save', 'info');
            return;
        }

        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    games: this.games
                })
            });

            if (response.ok) {
                const result = await response.json();
                
                this.modifiedGames.clear();
                this.showAlert('Changes saved successfully!', 'success');
                
                // Refresh the grid data to show updated values and resort, respecting current filters
                if (this.duplicatesFilterActive) {
                    // If duplicates filter is active, just refresh the grid (don't reload all games)
                    await this.refreshGridData();
                } else {
                    // Normal refresh - reload all games
                await this.loadRomSystem(this.currentSystem);
                
                // Also refresh the grid cells to ensure proper display
                if (this.gridApi) {
                    this.gridApi.refreshCells();
                    }
                }
            } else {
                const errorText = await response.text();
                this.showAlert('Error saving changes', 'danger');
            }
        } catch (error) {
            this.showAlert('Error saving changes', 'danger');
        }
    }

    markGameAsModified(game) {
        
        if (game.id !== undefined && game.id !== null) {
            const beforeSize = this.modifiedGames.size;
            this.modifiedGames.add(game.id);
            const afterSize = this.modifiedGames.size;
        } else {
        }
    }

    clearFilters() {
        if (this.gridApi) {
            this.gridApi.setFilterModel(null);
        }
    }
    async showMediaPreview(game) {
        if (!game) return;

        // Check if media preview tab is currently active
        if (!this.isMediaPreviewTabActive()) {
            return;
        }

        // Prevent multiple simultaneous calls
        if (this.showingMediaPreview) {
            return;
        }
        this.showingMediaPreview = true;
        
        // Track the current game being shown in media preview
        this.currentMediaPreviewGame = game;

        // Clear any existing media selection when showing a new game's media
        this.clearMediaSelection();

        const mediaPreviewContent = document.getElementById('mediaPreviewContent');
        
        // Always show media preview content (no need to show/hide section)
        mediaPreviewContent.innerHTML = '';

        // Get media fields from config.json mappings (excluding video from preview)
        const mediaFields = await this.getMediaFieldsFromConfig();
        
        // Process each field only once
        const processedFields = new Set();
        mediaFields.forEach(field => {
            if (processedFields.has(field)) {
                return; // Skip duplicate fields
            }
            processedFields.add(field);
            
            const mediaItem = document.createElement('div');
            mediaItem.className = 'media-preview-item';
            
            if (game[field] && game[field].trim()) {
                // Media exists - show the actual media
                const mediaPath = game[field];
                
                if (field === 'video' || mediaPath.endsWith('.mp4')) {
                    // Add cache-busting parameter to force video refresh
                    const cacheBuster = new Date().getTime();
                    mediaItem.innerHTML = `
                        <div style="position: relative;">
                            <video width="450" height="450" controls style="object-fit: contain; background-color: #f8f9fa;">
                                <source src="/roms/${this.currentSystem}/${mediaPath}?v=${cacheBuster}" type="video/mp4">
                            </video>
                            <div class="media-replace-overlay" style="position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.7); color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; opacity: 0; transition: opacity 0.2s ease;">
                                <i class="bi bi-arrow-clockwise"></i>
                            </div>
                            <div class="media-delete-overlay" style="position: absolute; top: 4px; left: 4px; background: rgba(220,53,69,0.8); color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; opacity: 0; transition: opacity 0.2s ease; cursor: pointer;" title="Delete video">
                                <i class="bi bi-trash"></i>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                            <small class="text-center flex-grow-1">${field}</small>
                            <div class="d-flex gap-1">
                                <button class="btn btn-outline-success btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Multiscraper Download" onclick="gameManager.openMultiscraperMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-search"></i>
                                </button>
                                <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-download"></i>
                                </button>
                            </div>
                        </div>
                    `;
                    
                    // Add error handler for video
                    const video = mediaItem.querySelector('video');
                    video.addEventListener('error', () => {
                        this.showFileMissingPlaceholder(mediaItem, field, mediaPath, game);
                    });
                } else if (mediaPath.toLowerCase().endsWith('.pdf')) {
                    // PDF file - show PDF logo
                    mediaItem.innerHTML = `
                        <div style="position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 150px; height: 150px; background-color: #a1a1a1; border: 2px dashed #dee2e6; border-radius: 8px;">
                            <i class="bi bi-file-earmark-pdf" style="font-size: 48px; color: #dc3545; margin-bottom: 8px;"></i>
                            <small style="color: #6c757d; text-align: center;">PDF Document</small>
                            <div class="media-replace-overlay" style="position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.7); color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; opacity: 0; transition: opacity 0.2s ease;">
                                <i class="bi bi-arrow-clockwise"></i>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                            <small class="text-center flex-grow-1">${field}</small>
                            <div class="d-flex gap-1">
                                ${field === 'fanart' ? `
                                <button class="btn btn-outline-info btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Fanart" onclick="gameManager.openFanartSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                                    <i class="bi bi-image"></i>
                                </button>
                                <button class="btn btn-outline-secondary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Google Images Search" onclick="gameManager.openGoogleImagesSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-google"></i>
                                </button>
                                ` : ''}
                                ${field === 'marquee' ? `
                                <button class="btn btn-outline-warning btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Marquee" onclick="gameManager.openMarqueeSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                                    <i class="bi bi-badge-ad"></i>
                                </button>
                                ` : ''}
                                <button class="btn btn-outline-success btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Multiscraper Download" onclick="gameManager.openMultiscraperMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-search"></i>
                                </button>
                                <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-download"></i>
                                </button>
                            </div>
                        </div>
                    `;
                } else {
                    // Add cache-busting parameter to force image refresh
                    const cacheBuster = new Date().getTime();
                    mediaItem.innerHTML = `
                        <div style="position: relative;">
                            <img src="/roms/${this.currentSystem}/${mediaPath}?v=${cacheBuster}" alt="${field}" width="150" height="150" style="object-fit: contain; background-color: #a1a1a1;" oncontextmenu="gameManager.showImageContextMenu(event, this.parentElement.parentElement, ${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                            <div class="media-replace-overlay" style="position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.7); color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; opacity: 0; transition: opacity 0.2s ease;">
                                <i class="bi bi-arrow-clockwise"></i>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                            <small class="text-center flex-grow-1">${field}</small>
                            <div class="d-flex gap-1">
                                ${field === 'fanart' ? `
                                <button class="btn btn-outline-info btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Fanart" onclick="gameManager.openFanartSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                                    <i class="bi bi-image"></i>
                                </button>
                                <button class="btn btn-outline-secondary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Google Images Search" onclick="gameManager.openGoogleImagesSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-google"></i>
                                </button>
                                ` : ''}
                                ${field === 'marquee' ? `
                                <button class="btn btn-outline-warning btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Marquee" onclick="gameManager.openMarqueeSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                                    <i class="bi bi-badge-ad"></i>
                                </button>
                                ` : ''}
                                <button class="btn btn-outline-success btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Multiscraper Download" onclick="gameManager.openMultiscraperMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-search"></i>
                                </button>
                                <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                    <i class="bi bi-download"></i>
                                </button>
                            </div>
                        </div>
                    `;
                    
                    // Add error handler for image
                    const img = mediaItem.querySelector('img');
                    img.addEventListener('error', () => {
                        this.showFileMissingPlaceholder(mediaItem, field, mediaPath, game);
                    });
                }
                
                // Add click functionality for media selection
                mediaItem.addEventListener('click', () => this.selectMediaItem(mediaItem, field, game, mediaPath));
                
                // Add double-click functionality for uploading/replacing media
                mediaItem.addEventListener('dblclick', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.uploadMediaForGame(game, field);
                });
                
                // Add hover effects to show replace and delete overlays
                mediaItem.addEventListener('mouseenter', () => {
                    const replaceOverlay = mediaItem.querySelector('.media-replace-overlay');
                    const deleteOverlay = mediaItem.querySelector('.media-delete-overlay');
                    if (replaceOverlay) {
                        replaceOverlay.style.opacity = '1';
                    }
                    if (deleteOverlay) {
                        deleteOverlay.style.opacity = '1';
                    }
                });
                
                mediaItem.addEventListener('mouseleave', () => {
                    const replaceOverlay = mediaItem.querySelector('.media-replace-overlay');
                    const deleteOverlay = mediaItem.querySelector('.media-delete-overlay');
                    if (replaceOverlay) {
                        replaceOverlay.style.opacity = '0';
                    }
                    if (deleteOverlay) {
                        deleteOverlay.style.opacity = '0';
                    }
                });
                
                // Add delete button functionality for videos
                if (field === 'video' || mediaPath.endsWith('.mp4')) {
                    const deleteOverlay = mediaItem.querySelector('.media-delete-overlay');
                    if (deleteOverlay) {
                        deleteOverlay.addEventListener('click', (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            this.deleteVideoForGame(game, field);
                        });
                    }
                }
                
                mediaItem.style.cursor = 'pointer';
                mediaItem.title = `Click to select ${field}. Double-click to replace. Press Delete to remove.`;
            } else {
                // Media missing - show placeholder with upload functionality
                const placeholderSize = field === 'video' ? '450px' : '150px';
                const iconClass = field === 'video' ? 'bi-camera-video' : 'bi-cloud-upload';
                const uploadText = field === 'video' ? 'Double-click<br>to upload video' : 'Double-click<br>to upload';
                
                mediaItem.innerHTML = `
                    <div class="media-placeholder" style="width: ${placeholderSize}; height: ${placeholderSize}; background-color: #a1a1a1; border: 2px dashed #dee2e6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d; font-size: 0.8rem; text-align: center; cursor: pointer; transition: all 0.2s ease;">
                        <div>
                            <i class="bi ${iconClass}" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                            ${uploadText}
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                        <small class="text-center flex-grow-1">${field}</small>
                        <div class="d-flex gap-1">
                            ${field === 'fanart' ? `
                            <button class="btn btn-outline-info btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Fanart" onclick="gameManager.openFanartSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                                <i class="bi bi-image"></i>
                            </button>
                            <button class="btn btn-outline-secondary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Google Images Search" onclick="gameManager.openGoogleImagesSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                <i class="bi bi-google"></i>
                            </button>
                            ` : ''}
                            ${field === 'marquee' ? `
                            <button class="btn btn-outline-warning btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Marquee" onclick="gameManager.openMarqueeSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                                <i class="bi bi-badge-ad"></i>
                            </button>
                            ` : ''}
                            <button class="btn btn-outline-success btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Multiscraper Download" onclick="gameManager.openMultiscraperMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                <i class="bi bi-search"></i>
                            </button>
                            <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                <i class="bi bi-download"></i>
                            </button>
                        </div>
                    </div>
                `;
                
                // Add double-click functionality for uploading
                mediaItem.addEventListener('dblclick', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.uploadMediaForGame(game, field);
                });
                
                // Add hover effect
                mediaItem.addEventListener('mouseenter', () => {
                    mediaItem.querySelector('.media-placeholder').style.borderColor = '#0d6efd';
                    mediaItem.querySelector('.media-placeholder').style.backgroundColor = '#f8f9ff';
                });
                
                mediaItem.addEventListener('mouseleave', () => {
                    mediaItem.querySelector('.media-placeholder').style.borderColor = '#dee2e6';
                    mediaItem.querySelector('.media-placeholder').style.backgroundColor = '#616161';
                });
                
                mediaItem.style.cursor = 'pointer';
                mediaItem.title = `Double-click to upload ${field} media`;
            }
            
            mediaPreviewContent.appendChild(mediaItem);
        });
        
        // Reset the flag at the end
        this.showingMediaPreview = false;
    }

    showFileMissingPlaceholder(mediaItem, field, mediaPath, game) {
        // Replace the media content with a "file missing" placeholder
        const placeholderSize = field === 'video' ? '450px' : '150px';
        const iconClass = field === 'video' ? 'bi-exclamation-triangle' : 'bi-exclamation-triangle';
        
        mediaItem.innerHTML = `
            <div class="media-placeholder" style="width: ${placeholderSize}; height: ${placeholderSize}; background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #856404; font-size: 0.8rem; text-align: center; cursor: pointer; transition: all 0.2s ease;">
                <div>
                    <i class="bi ${iconClass}" style="font-size: 2rem; margin-bottom: 0.5rem; display: block; color: #ffc107;"></i>
                    <div style="font-weight: bold; margin-bottom: 0.25rem;">File Missing</div>
                    <div style="font-size: 0.7rem; opacity: 0.8;">${mediaPath}</div>
                </div>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                <small class="text-center flex-grow-1" style="color: #dc3545; font-weight: bold;">${field} (Missing)</small>
                <div class="d-flex gap-1">
                    ${field === 'fanart' ? `
                    <button class="btn btn-outline-info btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Search Fanart" onclick="gameManager.openFanartSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                        <i class="bi bi-image"></i>
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Google Images Search" onclick="gameManager.openGoogleImagesSearchModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                        <i class="bi bi-google"></i>
                    </button>
                    ` : ''}
                    <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                        <i class="bi bi-download"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Add double-click functionality for uploading replacement
        mediaItem.addEventListener('dblclick', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadMediaForGame(game, field);
        });
        
        // Add hover effect
        mediaItem.addEventListener('mouseenter', () => {
            const placeholder = mediaItem.querySelector('.media-placeholder');
            placeholder.style.borderColor = '#dc3545';
            placeholder.style.backgroundColor = '#f8d7da';
        });
        
        mediaItem.addEventListener('mouseleave', () => {
            const placeholder = mediaItem.querySelector('.media-placeholder');
            placeholder.style.borderColor = '#ffc107';
            placeholder.style.backgroundColor = '#fff3cd';
        });
        
        mediaItem.style.cursor = 'pointer';
        mediaItem.title = `File missing: ${mediaPath}. Double-click to upload replacement.`;
    }
    
    hideMediaPreview() {
        // Clear media preview content instead of hiding the section
        const mediaPreviewContent = document.getElementById('mediaPreviewContent');
        if (mediaPreviewContent) {
            mediaPreviewContent.innerHTML = '';
        }
        
        // Clear the current media preview game
        this.currentMediaPreviewGame = null;
    }
    
    selectMediaItem(mediaItem, field, game, mediaPath) {
        // Toggle selection for the clicked item
        if (mediaItem.classList.contains('selected')) {
            // If already selected, deselect it
            mediaItem.classList.remove('selected');
            // Remove from selectedMedia array
            this.selectedMedia = this.selectedMedia.filter(item => 
                !(item.field === field && item.game.id === game.id && item.mediaPath === mediaPath)
            );
        } else {
            // If not selected, select it
            mediaItem.classList.add('selected');
            // Add to selectedMedia array
            this.selectedMedia.push({ field, game, mediaPath });
        }

        // Update the selection display
        this.updateMediaSelectionDisplay();
    }
    
    selectEditModalMediaItem(mediaItem, field, game, mediaPath) {
        // Toggle selection for the clicked item in edit modal
        if (mediaItem.classList.contains('selected')) {
            // If already selected, deselect it
            mediaItem.classList.remove('selected');
            // Remove from selectedMedia array
            this.selectedMedia = this.selectedMedia.filter(item => 
                !(item.field === field && item.game.id === game.id && item.mediaPath === mediaPath)
            );
        } else {
            // If not selected, select it
            mediaItem.classList.add('selected');
            // Add to selectedMedia array
            this.selectedMedia.push({ field, game, mediaPath });
        }

        // Update the delete button state in edit modal
        this.updateEditModalDeleteButtonState();
    }
    
    updateEditModalDeleteButtonState() {
        const deleteButton = document.getElementById('deleteSelectedEditModalMedia');
        if (deleteButton) {
            deleteButton.disabled = this.selectedMedia.length === 0;
        }
    }
    
    initializeEditModalFindBestMatch() {
        const modalFindBestMatchBtn = document.getElementById('modalFindBestMatchBtn');
        if (modalFindBestMatchBtn) {
            modalFindBestMatchBtn.addEventListener('click', () => {
                this.showGameEditFindBestMatch();
            });
        }
        
        // Initialize algorithm selector and reload button
        this.initializeGameEditAlgorithmSelector();
    }
    
    initializeGameEditAlgorithmSelector() {
        // Load current algorithm preference
        this.loadGameEditAlgorithmPreference();
        
        // Add event listener for algorithm change (auto-reload)
        const algorithmSelect = document.getElementById('gameEditSimilarityAlgorithm');
        if (algorithmSelect) {
            algorithmSelect.addEventListener('change', () => {
                this.saveGameEditAlgorithmPreference();
                // Auto-reload matches when algorithm changes
                this.reloadGameEditMatches();
            });
        }
    }
    
    loadGameEditAlgorithmPreference() {
        // Load from cookie or use default
        const algorithm = this.getCookie('similarity_algorithm') || 'jaro_winkler';
        const algorithmSelect = document.getElementById('gameEditSimilarityAlgorithm');
        if (algorithmSelect) {
            algorithmSelect.value = algorithm;
        }
    }
    
    saveGameEditAlgorithmPreference() {
        const algorithmSelect = document.getElementById('gameEditSimilarityAlgorithm');
        if (algorithmSelect) {
            const algorithm = algorithmSelect.value;
            this.setCookie('similarity_algorithm', algorithm, 365); // 1 year
        }
    }
    
    async reloadGameEditMatches() {
        // Get current game data
        const gameName = document.getElementById('gameEditOriginalGameNameInput').value.trim();
        const systemName = this.currentGameData?.system || this.currentSystem;
        
        if (!gameName || !systemName) {
            this.showAlert('Unable to reload matches: missing game or system data', 'warning');
            return;
        }
        
        // Show loading spinner
        const loadingSpinner = document.getElementById('gameEditLoadingSpinner');
        const matchesList = document.getElementById('gameEditMatchesList');
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (matchesList) matchesList.innerHTML = '';
        
        try {
            // Fetch matches with current algorithm preference
            const response = await fetch('/api/get-top-matches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    game_name: gameName, 
                    system_name: systemName 
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide loading spinner
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            
            // Display the matches (pass data.matches, not data)
            if (data.success && data.matches) {
                // Get the current game path for reliable identification
                const currentGame = this.getCurrentEditingGame();
                const gamePath = currentGame ? currentGame.path : null;
                this.displayPartialMatchModal(gameName, data.matches, 'gameEdit', gamePath);
            } else {
                this.showAlert('Error reloading matches: ' + (data.error || 'Unknown error'), 'danger');
            }
            
            // Show success message
            this.showAlert('Matches reloaded with new similarity algorithm!', 'success');
            
        } catch (error) {
            this.showAlert('Failed to reload matches', 'danger');
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        }
    }
    
    // Global Find Best Match Algorithm Selector Functions
    initializeGlobalAlgorithmSelector() {
        // Load current algorithm preference
        this.loadGlobalAlgorithmPreference();
        
        // Add event listener for algorithm change (auto-reload)
        const algorithmSelect = document.getElementById('globalSimilarityAlgorithm');
        if (algorithmSelect) {
            algorithmSelect.addEventListener('change', () => {
                this.saveGlobalAlgorithmPreference();
                // Auto-reload matches when algorithm changes
                this.reloadGlobalMatches();
            });
        }
    }
    
    loadGlobalAlgorithmPreference() {
        // Load from cookie or use default
        const algorithm = this.getCookie('similarity_algorithm') || 'jaro_winkler';
        const algorithmSelect = document.getElementById('globalSimilarityAlgorithm');
        if (algorithmSelect) {
            algorithmSelect.value = algorithm;
        }
    }
    
    saveGlobalAlgorithmPreference() {
        const algorithmSelect = document.getElementById('globalSimilarityAlgorithm');
        if (algorithmSelect) {
            const algorithm = algorithmSelect.value;
            this.setCookie('similarity_algorithm', algorithm, 365); // 1 year
        }
    }
    
    async reloadGlobalMatches() {
        if (!this.selectedGames || this.selectedGames.length === 0) {
            this.showAlert('No games selected for reloading', 'warning');
            return;
        }
        
        // Show loading state
        const progressDiv = document.getElementById('globalMatchProgress');
        const tableDiv = document.getElementById('globalMatchTable');
        const emptyDiv = document.getElementById('globalMatchEmpty');
        
        if (progressDiv) progressDiv.style.display = 'block';
        if (tableDiv) tableDiv.style.display = 'none';
        if (emptyDiv) emptyDiv.style.display = 'none';
        
        try {
            
            // Re-run the find best match process
            await this.findBestMatchForSelected();
            
            // Show success message
            this.showAlert('Global matches reloaded with new similarity algorithm!', 'success');
            
        } catch (error) {
            this.showAlert('Failed to reload global matches', 'danger');
        }
    }
    
    initializeEditModalIgdbSearch() {
        const modalFindIgdbMatchBtn = document.getElementById('modalFindIgdbMatchBtn');
        if (modalFindIgdbMatchBtn) {
            modalFindIgdbMatchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Prevent rapid clicking
                if (this.igdbSearchInProgress) {
                    console.log('🔧 DEBUG: IGDB search button clicked but search already in progress');
                    return;
                }
                
                console.log('🔧 DEBUG: IGDB search button clicked');
                this.showGameEditIgdbSearch();
            });
        }
    }
    
    initializeEditModalScreenscraperSearch() {
        const modalFindScreenscraperMatchBtn = document.getElementById('modalFindScreenscraperMatchBtn');
        if (modalFindScreenscraperMatchBtn) {
            modalFindScreenscraperMatchBtn.addEventListener('click', () => {
                this.showGameEditScreenscraperSearch();
            });
        }
    }
    
    initializeEditModalSteamSearch() {
        const modalFindSteamMatchBtn = document.getElementById('modalFindSteamMatchBtn');
        if (modalFindSteamMatchBtn) {
            modalFindSteamMatchBtn.addEventListener('click', () => {
                this.showGameEditSteamSearch();
            });
        }
    }
    
    initializeEditModalSteamgridSearch() {
        const modalFindSteamgridMatchBtn = document.getElementById('modalFindSteamgridMatchBtn');
        if (modalFindSteamgridMatchBtn) {
            modalFindSteamgridMatchBtn.addEventListener('click', () => {
                this.showGameEditSteamgridSearch();
            });
        }
    }
    
    initializeEditModalMobygamesSearch() {
        const modalFindMobygamesMatchBtn = document.getElementById('modalFindMobygamesMatchBtn');
        if (modalFindMobygamesMatchBtn) {
            modalFindMobygamesMatchBtn.addEventListener('click', () => {
                this.showGameEditMobygamesSearch();
            });
        }
    }
    
    initializeEditModalYoutubePreview() {
        const modalPreviewYoutubeBtn = document.getElementById('modalPreviewYoutubeBtn');
        if (modalPreviewYoutubeBtn) {
            modalPreviewYoutubeBtn.addEventListener('click', () => {
                this.showGameEditYoutubePreview();
            });
        }
    }
    
    showGameEditYoutubePreview() {
        // Get the YouTube URL from the edit modal field
        const youtubeUrlField = document.getElementById('editYoutubeurl');
        if (!youtubeUrlField) {
            return;
        }
        
        const youtubeUrl = youtubeUrlField.value.trim();
        if (!youtubeUrl) {
            return;
        }
        
        // Validate that it's a YouTube URL
        if (!youtubeUrl.includes('youtube')) {
            return;
        }

        // Set flag to prevent YouTube search modal from reopening when player modal closes
        this.suppressYouTubeSearchReopen = true;
        
        // Create a mock video object for the player
        const video = {
            url: youtubeUrl,
            title: 'Game Video Preview',
            game: this.getCurrentEditingGame() || {}
        };
        
        // Store the current video for the player
        this.currentYouTubeVideo = video;
        
        // Show the YouTube player modal
        const playerModal = new bootstrap.Modal(document.getElementById('youtubePlayerModal'));
        playerModal.show();
        
        // Wait for modal to be fully visible before initializing player
        setTimeout(() => {
            // Initialize YouTube player
            this.initializeYouTubePlayer(youtubeUrl);
            
            // Initialize player controls
            this.initializePlayerControls();
            
        }, 300);
    }
    
    initializeDeleteVideoButton(game) {
        const deleteVideoBtn = document.getElementById('deleteVideoBtn');
        if (deleteVideoBtn) {
            // Check if game has any videos
            const videoFields = ['video', 'video_mp4', 'video_avi', 'video_mov', 'video_mkv'];
            const hasVideos = videoFields.some(field => game[field] && game[field].trim());
            
            // Enable/disable button based on whether videos exist
            deleteVideoBtn.disabled = !hasVideos;
            
            // Add click event listener
            deleteVideoBtn.addEventListener('click', () => {
                // Find the first video field that has content
                const videoField = videoFields.find(field => game[field] && game[field].trim());
                if (videoField) {
                    this.deleteVideoForGame(game, videoField);
                }
            });
        }
    }
    
    updateDeleteVideoButtonState(game) {
        const deleteVideoBtn = document.getElementById('deleteVideoBtn');
        if (deleteVideoBtn) {
            // Check if game has any videos
            const videoFields = ['video', 'video_mp4', 'video_avi', 'video_mov', 'video_mkv'];
            const hasVideos = videoFields.some(field => game[field] && game[field].trim());
            
            // Enable/disable button based on whether videos exist
            deleteVideoBtn.disabled = !hasVideos;
        }
    }
    
    initializeManualCropButton(game) {
        const manualCropBtn = document.getElementById('manualCropBtn');
        if (manualCropBtn) {
            // Check if game has any videos
            const videoFields = ['video', 'video_mp4', 'video_avi', 'video_mov', 'video_mkv'];
            const hasVideos = videoFields.some(field => game[field] && game[field].trim());
            
            // Enable/disable button based on whether videos exist
            manualCropBtn.disabled = !hasVideos;
            
            // Add click event listener (remove any existing ones first)
            if (manualCropBtn._manualCropHandler) {
                manualCropBtn.removeEventListener('click', manualCropBtn._manualCropHandler);
            }
            
            manualCropBtn._manualCropHandler = () => {
                this.openManualCropModal(game);
            };
            
            manualCropBtn.addEventListener('click', manualCropBtn._manualCropHandler);
        }
    }
    
    async openManualCropModal(game) {
        // Prevent multiple simultaneous calls
        if (this.isExtractingFrame) {
            return;
        }
        
        // Find the first video field that has content
        const videoFields = ['video', 'video_mp4', 'video_avi', 'video_mov', 'video_mkv'];
        const videoField = videoFields.find(field => game[field] && game[field].trim());
        
        if (!videoField) {
            this.showAlert('No video found for cropping', 'error');
            return;
        }
        
        const videoPath = game[videoField];
        
        // Convert relative path to absolute path
        let absoluteVideoPath = videoPath;
        if (videoPath.startsWith('./')) {
            // Construct absolute path from ROMS_FOLDER + system + relative path
            absoluteVideoPath = `/roms/${this.currentSystem}/${videoPath.substring(2)}`;
        }

        // Store current game and video info
        this.currentCropGame = game;
        this.currentCropVideoField = videoField;
        this.currentCropVideoPath = absoluteVideoPath;
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('videoCroppingModal'));
        modal.show();
        
        // Wait for modal to be fully shown before extracting frame
        const modalElement = document.getElementById('videoCroppingModal');
        modalElement.addEventListener('shown.bs.modal', () => {
            // Extract first frame and setup crop interface after modal is fully shown
            this.extractFirstFrameAndSetupCropper(absoluteVideoPath);
        }, { once: true }); // Use once: true to only run this once
        
        // Add cleanup when modal is hidden
        modalElement.addEventListener('hidden.bs.modal', () => {
            this.cleanupFrameImage();
        }, { once: true }); // Use once: true to only run this once
    }
    
    async extractFirstFrameAndSetupCropper(videoPath) {
        // Set flag to prevent duplicate calls
        this.isExtractingFrame = true;
        
        try {
            
            // Show loading state - find the container by looking for the card body
            const imageContainer = document.querySelector('#videoCroppingModal .card-body .text-center');
            if (imageContainer) {
                imageContainer.innerHTML = '<div class="text-center p-4"><i class="bi bi-hourglass-split"></i> Extracting first frame...</div>';
            }
            
            // Call API to extract first frame
            const response = await fetch('/api/extract-first-frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    video_path: videoPath
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Store the frame path for cleanup
                this.currentFramePath = result.frame_path;
                
                // Restore image element
                if (imageContainer) {
                    imageContainer.innerHTML = '<img id="cropImage" alt="Video Frame">';
                }
                const img = document.getElementById('cropImage');
                
                if (img) {
                    // Load image and setup Cropper.js
                    img.onload = () => {
                        // Wait for modal to be fully rendered before sizing
                        setTimeout(() => {
                            this.forceImageSize(img);
                            this.setupCropper(img);
                        }, 100);
                    };
                    img.src = `/roms/${result.frame_path}`;
                } else {
                    throw new Error('Failed to create image element');
                }
            } else {
                throw new Error(result.error || 'Failed to extract first frame');
            }
        } catch (error) {
            this.showAlert(`Error extracting first frame: ${error.message}`, 'error');
            
            // Reset container on error
            const imageContainer = document.querySelector('#videoCroppingModal .card-body .text-center');
            if (imageContainer) {
                imageContainer.innerHTML = '<div class="text-center p-4 text-muted">Failed to load video frame</div>';
            }
        } finally {
            // Reset flag to allow future calls
            this.isExtractingFrame = false;
        }
    }
    
    async cleanupFrameImage() {
        // Clean up the extracted frame image file
        if (this.currentFramePath) {
            try {
                
                const response = await fetch('/api/delete-frame-image', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        frame_path: this.currentFramePath
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                } else {
                }
            } catch (error) {
            } finally {
                // Clear the stored frame path
                this.currentFramePath = null;
            }
        }
        
        // Clean up cropper instance
        if (this.cropper) {
            this.cropper.destroy();
            this.cropper = null;
        }
        
        // Clean up resize listener
        if (this.imageResizeHandler) {
            window.removeEventListener('resize', this.imageResizeHandler);
            this.imageResizeHandler = null;
        }
        
        // Clear crop game data
        this.currentCropGame = null;
        this.currentCropVideoField = null;
        this.currentCropVideoPath = null;
    }
    forceImageSize(img) {
        // Calculate optimal size based on available space and image dimensions
        const container = img.parentElement;
        let containerWidth = container.clientWidth;
        let containerHeight = container.clientHeight;
        
        // Fallback if container dimensions are not available yet
        if (containerWidth === 0 || containerHeight === 0) {
            // Use modal dimensions as fallback
            const modal = document.getElementById('videoCroppingModal');
            if (modal) {
                const modalContent = modal.querySelector('.modal-content');
                if (modalContent) {
                    containerWidth = modalContent.clientWidth * 0.6; // Approximate 60% for image area
                    containerHeight = modalContent.clientHeight * 0.7; // Approximate 70% for image area
                }
            }
            
            // Final fallback to reasonable defaults
            if (containerWidth === 0) containerWidth = 800;
            if (containerHeight === 0) containerHeight = 600;
        }
        
        // Get natural image dimensions
        const naturalWidth = img.naturalWidth;
        const naturalHeight = img.naturalHeight;
        
        // Calculate aspect ratio
        const aspectRatio = naturalWidth / naturalHeight;
        
        // Calculate optimal dimensions
        let targetWidth, targetHeight;
        
        // Use container dimensions as base, but ensure minimum size
        const minWidth = 600;
        const minHeight = 400;
        const maxWidth = Math.min(containerWidth * 0.9, 1000);
        const maxHeight = Math.min(containerHeight * 0.8, 700);
        
        // Calculate size that fits within bounds while maintaining aspect ratio
        if (containerWidth / containerHeight > aspectRatio) {
            // Container is wider than image aspect ratio
            targetHeight = Math.max(minHeight, Math.min(maxHeight, containerHeight * 0.8));
            targetWidth = targetHeight * aspectRatio;
        } else {
            // Container is taller than image aspect ratio
            targetWidth = Math.max(minWidth, Math.min(maxWidth, containerWidth * 0.9));
            targetHeight = targetWidth / aspectRatio;
        }
        
        // Ensure we don't exceed maximum dimensions
        if (targetWidth > maxWidth) {
            targetWidth = maxWidth;
            targetHeight = targetWidth / aspectRatio;
        }
        if (targetHeight > maxHeight) {
            targetHeight = maxHeight;
            targetWidth = targetHeight * aspectRatio;
        }
        
        // Apply calculated dimensions
        img.style.width = `${Math.round(targetWidth)}px`;
        img.style.height = `${Math.round(targetHeight)}px`;
        img.style.objectFit = 'contain';
        img.style.display = 'block';
        
        // Trigger a reflow to ensure styles are applied
        img.offsetHeight;

    }
    
    setupCropper(image) {
        // Destroy existing cropper if any
        if (this.cropper) {
            this.cropper.destroy();
        }
        
        // Initialize Cropper.js with options
        this.cropper = new Cropper(image, {
            aspectRatio: 4 / 3, // Set 4:3 aspect ratio as default
            viewMode: 0, // Allow crop box to extend beyond the container
            dragMode: 'move', // Allow moving the crop box
            autoCropArea: 1.0, // Use full area initially, will be adjusted
            restore: false,
            guides: true,
            center: true,
            highlight: true,
            cropBoxMovable: true,
            cropBoxResizable: true,
            toggleDragModeOnDblclick: false,
            // Allow free resizing by not forcing aspect ratio
            checkCrossOrigin: false,
            background: true,
            modal: true,
            responsive: true, // Enable responsive for better adaptation
            checkOrientation: false,
            crop: (event) => {
                this.updateCropInfo();
            }
        });
        
        // Store original image dimensions for crop calculations
        this.originalImageWidth = image.naturalWidth;
        this.originalImageHeight = image.naturalHeight;
        
        // Set default crop area size with 4:3 ratio and height = image height
        this.setDefaultCropArea();
        
        // Setup event listeners
        this.setupCropperEventListeners();
        
        // Add window resize listener to recalculate image size
        this.setupImageResizeListener(image);
        
        // Update crop info display
        this.updateCropInfo();
    }
    
    setupImageResizeListener(image) {
        // Remove existing resize listener if any
        if (this.imageResizeHandler) {
            window.removeEventListener('resize', this.imageResizeHandler);
        }
        
        // Create new resize handler
        this.imageResizeHandler = () => {
            // Debounce resize events
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                this.forceImageSize(image);
                if (this.cropper) {
                    this.cropper.reset();
                }
            }, 100);
        };
        
        // Add resize listener
        window.addEventListener('resize', this.imageResizeHandler);
    }
    
    setDefaultCropArea() {
        if (!this.cropper) return;
        
        // Get the current image dimensions from the cropper
        const imageData = this.cropper.getImageData();
        const containerData = this.cropper.getContainerData();
        
        // Calculate the crop area with height = image height and 4:3 aspect ratio
        const imageHeight = imageData.height;
        const imageWidth = imageData.width;
        
        // Calculate crop height (full image height)
        const cropHeight = imageHeight;
        
        // Calculate crop width based on 4:3 aspect ratio
        const cropWidth = cropHeight * (4 / 3);
        
        // Calculate crop position (center horizontally)
        const cropX = Math.max(0, (imageWidth - cropWidth) / 2);
        const cropY = 0; // Start from top
        
        // Set the crop box dimensions
        this.cropper.setCropBoxData({
            left: cropX,
            top: cropY,
            width: cropWidth,
            height: cropHeight
        });
    }
    
    setupCropperEventListeners() {
        // Keep aspect ratio checkbox
        const keepAspectCheckbox = document.getElementById('keepAspectRatio');
        keepAspectCheckbox.addEventListener('change', (e) => {
            if (this.cropper) {
                if (e.target.checked) {
                    // Set aspect ratio to 4:3 (default video ratio)
                    this.cropper.setAspectRatio(4 / 3);
                } else {
                    // Free aspect ratio - allow free resizing
                    this.cropper.setAspectRatio(NaN);
                    // Enable free resizing by setting cropBoxResizable to true
                    this.cropper.setOptions({
                        cropBoxResizable: true,
                        cropBoxMovable: true
                    });
                }
            }
        });
        
        // Reset button
        const resetBtn = document.getElementById('resetCropBtn');
        resetBtn.addEventListener('click', () => {
            if (this.cropper) {
                this.cropper.reset();
                this.updateCropInfo();
            }
        });
        
        // Apply crop button
        const applyBtn = document.getElementById('applyCropBtn');
        applyBtn.addEventListener('click', () => {
            this.applyCropperCrop();
        });
    }
    
    updateCropInfo() {
        if (!this.cropper) return;
        
        const cropData = this.cropper.getData();
        const dimensions = document.getElementById('cropDimensions');
        const position = document.getElementById('cropPosition');
        
        if (dimensions) {
            const width = Math.round(cropData.width);
            const height = Math.round(cropData.height);
            dimensions.textContent = `${width} x ${height}`;
        }
        
        if (position) {
            position.textContent = `(${Math.round(cropData.x)}, ${Math.round(cropData.y)})`;
        }
    }
    
    applyCropperCrop() {
        if (!this.cropper || !this.currentCropGame) {
            this.showAlert('No crop area selected', 'error');
            return;
        }
        
        const cropData = this.cropper.getData();
        
        // Convert crop data to crop dimensions string (width:height:x:y)
        const width = Math.round(cropData.width);
        const height = Math.round(cropData.height);
        const x = Math.round(cropData.x);
        const y = Math.round(cropData.y);
        
        const cropDimensions = `${width}:${height}:${x}:${y}`;

        // Show waiting state
        this.showCropWaitingState();
        
        // Prepare request data
        const requestData = {
            video_path: this.currentCropVideoPath,
            crop_dimensions: cropDimensions,
            game_id: this.currentCropGame.id,
            system_name: this.currentSystem,
            rom_file: this.currentCropGame.path
        };

        // Call the manual crop API
        fetch('/api/apply-manual-crop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                this.showAlert('Video cropped successfully!', 'success');
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('videoCroppingModal'));
                modal.hide();
                // Refresh video preview
                this.showEditGameVideo(this.currentCropGame);
                // Cleanup will be handled by the modal hidden event
            } else {
                this.showAlert('Failed to crop video: ' + result.error, 'error');
                this.hideCropWaitingState();
            }
        })
        .catch(error => {
            this.showAlert('Error applying crop: ' + error.message, 'error');
            this.hideCropWaitingState();
        });
    }
    
    showCropWaitingState() {
        // Disable apply button and show waiting state
        const applyBtn = document.getElementById('applyCropBtn');
        if (applyBtn) {
            applyBtn.disabled = true;
            applyBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Processing...';
        }
        
        // Show waiting overlay on the crop image
        const imageContainer = document.querySelector('#videoCroppingModal .card-body .text-center');
        if (imageContainer) {
            const waitingOverlay = document.createElement('div');
            waitingOverlay.id = 'cropWaitingOverlay';
            waitingOverlay.className = 'position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
            waitingOverlay.style.cssText = 'background-color: rgba(0,0,0,0.7); z-index: 1000;';
            waitingOverlay.innerHTML = `
                <div class="text-center text-white">
                    <div class="spinner-border mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div>Processing crop...</div>
                </div>
            `;
            
            // Make container relative positioned
            imageContainer.style.position = 'relative';
            imageContainer.appendChild(waitingOverlay);
        }
    }
    
    hideCropWaitingState() {
        // Re-enable apply button
        const applyBtn = document.getElementById('applyCropBtn');
        if (applyBtn) {
            applyBtn.disabled = false;
            applyBtn.innerHTML = '<i class="bi bi-scissors me-1"></i>Apply Crop';
        }
        
        // Remove waiting overlay
        const waitingOverlay = document.getElementById('cropWaitingOverlay');
        if (waitingOverlay) {
            waitingOverlay.remove();
        }
    }
    
    handleTaskCompletion(data) {
        
        // Check if this is a manual crop task completion
        if (data.task_type === 'manual_crop' && data.success) {
            
            // Hide waiting state
            this.hideCropWaitingState();
            
            // Close the crop modal if it's open
            const modal = bootstrap.Modal.getInstance(document.getElementById('videoCroppingModal'));
            if (modal) {
                modal.hide();
                // Cleanup will be handled by the modal hidden event
            }
            
            // Refresh the video preview if we're editing a game
            if (this.currentCropGame && this.editingGameIndex >= 0) {
                // Reload the system to get updated game data
                this.loadRomSystem(this.currentSystem).then(() => {
                    // Refresh the video preview
                    this.showEditGameVideo(this.currentCropGame);
                });
            }
        }
        
        // Check if this is an IGDB scraping task completion
        if (data.task_type === 'igdb_scraping') {
            
            // Refresh the task grid to show updated task status
            this.refreshTaskGrid();
            
            // Refresh the gamelist grid if we're viewing the same system that was scraped
            // This applies to both successful completion and stopped tasks (since gamelist is saved in both cases)
            if (data.system_name && data.system_name === this.currentSystem) {
                
                // Add a delay to ensure gamelist.xml file write has completed
                setTimeout(() => {
                    this.loadRomSystem(this.currentSystem).then(() => {
                    }).catch((error) => {
                    });
                }, 1000); // 1000ms delay to ensure file write is complete
            } else {
            }
            
            // Show appropriate message based on success/stopped status
            if (data.success) {
                if (data.stopped) {
                    this.showAlert(data.message || 'IGDB scraping stopped by user (data saved)', 'success');
                } else {
                    this.showAlert(data.message || 'IGDB scraping completed successfully', 'success');
                }
            } else {
                this.showAlert(data.message || 'IGDB scraping failed', 'error');
            }
        }
        
        // Check if this is a ScreenScraper scraping task completion
        if (data.task_type === 'screenscraper_scraping') {
            
            // Refresh the task grid to show updated task status
            this.refreshTaskGrid();
            
            // Refresh the gamelist grid if we're viewing the same system that was scraped
            // This applies to both successful completion and stopped tasks (since gamelist is saved in both cases)
            if (data.system_name && data.system_name === this.currentSystem) {
                
                // Add a delay to ensure gamelist.xml file write has completed
                setTimeout(() => {
                    this.loadRomSystem(this.currentSystem).then(() => {
                    }).catch((error) => {
                    });
                }, 1000); // 1000ms delay to ensure file write is complete
            } else {
            }
            
            // Show appropriate message based on success/stopped status
            if (data.success) {
                if (data.stopped) {
                    this.showAlert(data.message || 'ScreenScraper scraping stopped by user (data saved)', 'success');
                } else {
                    this.showAlert(data.message || 'ScreenScraper scraping completed successfully', 'success');
                }
            } else {
                this.showAlert(data.message || 'ScreenScraper scraping failed', 'error');
            }
        }
        
        // Check if this is a Steam scraping task completion
        if (data.task_type === 'steam_scraping') {
            
            // Refresh the task grid to show updated task status
            this.refreshTaskGrid();
            
            // Refresh the gamelist grid if we're viewing the same system that was scraped
            if (data.system_name && data.system_name === this.currentSystem) {
                
                // Add a delay to ensure gamelist.xml file write has completed
                setTimeout(() => {
                    this.loadRomSystem(this.currentSystem).then(() => {
                        
                        // Refresh media preview if it's currently showing
                        if (this.mediaPreviewEnabled && this.currentMediaPreviewGame) {
                            const freshGame = this.games.find(g => g.path === this.currentMediaPreviewGame.path);
                            if (freshGame) {
                                this.currentMediaPreviewGame = freshGame;
                                this.showMediaPreview(this.currentMediaPreviewGame);
                            }
                        }
                    }).catch((error) => {
                    });
                }, 1000); // 1000ms delay to ensure file write is complete
            } else {
            }
            
            // Show appropriate message based on success/stopped status
            if (data.success) {
                if (data.stopped) {
                    this.showAlert(data.message || 'Steam scraping stopped by user (data saved)', 'success');
                } else {
                    this.showAlert(data.message || 'Steam scraping completed successfully', 'success');
                }
            } else {
                this.showAlert(data.message || 'Steam scraping failed', 'error');
            }
        }
    }
    
    async refreshTaskGrid() {
        try {
            const response = await fetch('/api/tasks', {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for task data
                }
            });
            if (response.ok) {
                const tasks = await response.json();
                this.displayTasksInGrid(tasks);
            } else {
            }
        } catch (error) {
        }
    }
    
    // Old crop interface functions removed - now using Cropper.js library

    initializeEditModalDeleteButton() {
        const deleteButton = document.getElementById('deleteSelectedEditModalMedia');
        if (deleteButton) {
            deleteButton.addEventListener('click', () => {
                this.deleteSelectedMedia();
            });
        }
    }
    
    initializeEditModalCleanup() {
        const editModal = document.getElementById('editGameModal');
        if (editModal) {
            const pauseAllVideos = () => {
                try {
                    editModal.querySelectorAll('video').forEach(v => {
                        try { v.pause(); v.currentTime = v.currentTime; } catch(e) {}
                    });
                } catch (e) {}
            };
            
            const cleanupModalState = () => {
                // Clear any media selection
                this.clearMediaSelection();
                // Reset any modal-specific state
                this.selectedMedia = [];
                // Clear any form data if needed
                const form = document.getElementById('editGameForm');
                if (form) { form.reset(); }
                
                // Force cleanup of modal state to prevent interface getting stuck
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
                
                // Remove any stuck modal backdrop
                document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                    backdrop.remove();
                });
                
                // Clear modal context
                this.currentModalContext = null;
                this.currentModalData = null;
            };
            
            editModal.addEventListener('hidden.bs.modal', () => {
                pauseAllVideos();
                cleanupModalState();
                
                // Additional cleanup to prevent interface getting stuck
                setTimeout(() => {
                    // Force cleanup of any remaining modal state
                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                    document.body.style.paddingRight = '';
                    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                        backdrop.remove();
                    });
                }, 50);
            });
            
            // Add focus management when modal is about to be hidden
            editModal.addEventListener('hide.bs.modal', () => {
                pauseAllVideos();
                const safeElement = document.querySelector('#gamesCount') || document.body;
                if (safeElement) { safeElement.focus(); }
                const focusedElement = editModal.querySelector(':focus');
                if (focusedElement) { focusedElement.blur(); }
            });
        }
    }
    
    initializeSearchModalCleanup() {
        // List of search modal IDs
        const searchModalIds = [
            'igdbSearchModal',
            'screenscraperSearchModal', 
            'steamSearchModal',
            'mobygamesSearchModal',
            'steamgridSearchModal'
        ];
        
        // Add cleanup event listeners for each search modal
        searchModalIds.forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.addEventListener('hidden.bs.modal', () => {
                    // Clear modal state when any search modal is closed
                    this.currentModalContext = null;
                    this.currentModalData = null;
                    
                    // Force cleanup of modal state to prevent interface getting stuck
                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                    document.body.style.paddingRight = '';
                    
                    // Remove any stuck modal backdrop
                    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                        backdrop.remove();
                    });
                });
            }
        });
    }
    
    initializeCacheConfigurationModal() {
        
        // Add event listener for opening cache modal
        const openCacheModal = document.getElementById('openCacheModal');
        if (openCacheModal) {
            openCacheModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openCacheConfigurationModal();
            });
        } else {
        }
        
        // Add event listener for opening LaunchBox modal
        const openLaunchboxModal = document.getElementById('openLaunchboxModal');
        if (openLaunchboxModal) {
            openLaunchboxModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openLaunchboxScrapPreferencesModal();
            });
        } else {
        }

        // Add event listener for opening IGDB modal
        const openIgdbModal = document.getElementById('openIgdbModal');
        if (openIgdbModal) {
            openIgdbModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openIgdbScrapPreferencesModal();
            });
        } else {
        }

        // Add event listener for opening Steam modal
        const openSteamModal = document.getElementById('openSteamModal');
        if (openSteamModal) {
            openSteamModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openSteamScrapPreferencesModal();
            });
        } else {
        }

        // Add event listener for opening SteamGridDB modal
        const openSteamGridDBModal = document.getElementById('openSteamGridDBModal');
        if (openSteamGridDBModal) {
            openSteamGridDBModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openSteamGridDBScrapPreferencesModal();
            });
        } else {
        }

        // Add event listener for opening ScreenScraper modal
        const openScreenscraperModal = document.getElementById('openScreenscraperModal');
        if (openScreenscraperModal) {
            openScreenscraperModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openScreenscraperScrapPreferencesModal();
            });
        } else {
        }
        
        // Add event listener for opening MobyGames modal
        const openMobygamesModal = document.getElementById('openMobygamesModal');
        if (openMobygamesModal) {
            openMobygamesModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openMobygamesScrapPreferencesModal();
            });
        }

        // Add event listener for opening DAT Scrapper modal
        const openDatscrapperModal = document.getElementById('openDatscrapperModal');
        if (openDatscrapperModal) {
            openDatscrapperModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openDatscrapperScrapPreferencesModal();
            });
        }

        // Add event listener for opening Systems modal
        const openSystemsModal = document.getElementById('openSystemsModal');
        if (openSystemsModal) {
            openSystemsModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openSystemsConfigurationModal();
            });
        } else {
        }

        // Add event listener for opening Remap Media Field modal
        const openRemapMediaFieldModal = document.getElementById('openRemapMediaFieldModal');
        if (openRemapMediaFieldModal) {
            openRemapMediaFieldModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openRemapMediaFieldModal();
            });
        } else {
        }

        // Add event listener for opening Move Medias modal
        const openMoveMediasModal = document.getElementById('openMoveMediasModal');
        if (openMoveMediasModal) {
            openMoveMediasModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openMoveMediasModal();
            });
        } else {
        }

        // Add event listener for opening Resize Medias modal
        const openResizeMediasModal = document.getElementById('openResizeMediasModal');
        if (openResizeMediasModal) {
            openResizeMediasModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openResizeMediasModal();
            });
        } else {
        }

        // Add event listener for Import Medias modal
        const openImportMediasModal = document.getElementById('openImportMediasModal');
        if (openImportMediasModal) {
            openImportMediasModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openImportMediasModal();
            });
        }

        // Add event listener for unified scraper config modal
        const openScraperConfigModal = document.getElementById('openScraperConfigModal');
        if (openScraperConfigModal) {
            openScraperConfigModal.addEventListener('click', (e) => {
                e.preventDefault();
                this.openScraperConfigurationModal();
            });
        } else {
        }

        // Add event listener for update metadata button
        const updateMetadataBtn = document.getElementById('updateMetadataBtn');
        if (updateMetadataBtn) {
            updateMetadataBtn.addEventListener('click', () => {
                this.updateMetadataXml();
            });
        } else {
        }
        
        // Add event listener for refresh MobyGames cache button
        const refreshMobygamesCacheBtn = document.getElementById('refreshMobygamesCacheBtn');
        if (refreshMobygamesCacheBtn) {
            refreshMobygamesCacheBtn.addEventListener('click', () => {
                this.refreshMobygamesCache();
            });
        }
        
        // Add event listener for refresh Steam cache button
        const refreshSteamCacheBtn = document.getElementById('refreshSteamCacheBtn');
        if (refreshSteamCacheBtn) {
            refreshSteamCacheBtn.addEventListener('click', () => {
                this.refreshSteamCache();
            });
        }

    }

    openCacheConfigurationModal() {
        // Load cache information before opening modal
        this.loadCacheInformation();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('cacheConfigurationModal'));
        modal.show();
    }
    
    async openLaunchboxScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadLaunchboxSettings();
        
        // Initialize dynamic field checkboxes from config
        await this.initializeLaunchboxFieldCheckboxes();
        
        // Load field settings AFTER checkboxes are created
        this.loadLaunchboxFieldSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('launchboxConfigurationModal'));
        modal.show();
    }
    loadLaunchboxSettings() {
        // Load saved settings from cookies
        const savedForceDownload = this.getCookie('forceDownloadImages');
        const savedOverwriteTextFields = this.getCookie('launchboxOverwriteTextFields');

        // Update modal checkboxes with saved values
        const forceDownloadCheckbox = document.getElementById('forceDownloadImagesModal');
        const overwriteTextFieldsCheckbox = document.getElementById('overwriteTextFieldsLaunchbox');
        
        if (forceDownloadCheckbox) {
            forceDownloadCheckbox.checked = savedForceDownload === 'true';
        }
        
        if (overwriteTextFieldsCheckbox) {
            if (savedOverwriteTextFields !== null) {
                overwriteTextFieldsCheckbox.checked = savedOverwriteTextFields === 'true';
            } else {
                // No saved value, set to default (unchecked)
                overwriteTextFieldsCheckbox.checked = false;
            }
        }
    }
    
    openIgdbScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadIgdbSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('igdbConfigurationModal'));
        modal.show();
    }
    
    loadIgdbSettings() {
        // Load saved settings from cookies
        const savedOverwriteTextFields = this.getCookie('overwriteTextFields');
        const savedOverwriteMediaFields = this.getCookie('overwriteMediaFields');
        
        // Update modal checkboxes with saved values
        const overwriteTextCheckbox = document.getElementById('overwriteTextFieldsModal');
        const overwriteMediaCheckbox = document.getElementById('overwriteMediaFieldsModal');
        
        if (overwriteTextCheckbox) {
            overwriteTextCheckbox.checked = savedOverwriteTextFields === 'true';
        }
        
        if (overwriteMediaCheckbox) {
            overwriteMediaCheckbox.checked = savedOverwriteMediaFields === 'true';
        }
        
        // Load field selection settings
        this.loadIgdbFieldSettings();
        
        // Load LaunchBox field selection settings
        this.loadLaunchboxFieldSettings();
    }
    
    async loadIgdbCredentialsStatus() {
        try {
            const response = await fetch('/api/igdb-credentials');
            if (response.ok) {
                const data = await response.json();
                this.updateIgdbCredentialsStatus(data);
            } else {
            }
        } catch (error) {
        }
    }
    
    updateIgdbCredentialsStatus(data) {
        const statusElement = document.getElementById('igdbCredentialsStatus');
        if (statusElement) {
            if (data.has_client_id && data.has_client_secret) {
                statusElement.innerHTML = '<i class="bi bi-check-circle text-success me-1"></i>Credentials configured';
                statusElement.className = 'text-success';
            } else {
                statusElement.innerHTML = '<i class="bi bi-exclamation-triangle text-warning me-1"></i>Credentials not configured';
                statusElement.className = 'text-warning';
            }
        }
    }
    
    async saveIgdbCredentials() {
        const clientId = document.getElementById('igdbClientId').value.trim();
        const clientSecret = document.getElementById('igdbClientSecret').value.trim();
        
        if (!clientId || !clientSecret) {
            alert('Please enter both Client ID and Client Secret');
            return;
        }
        
        try {
            const response = await fetch('/api/igdb-credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    client_id: clientId,
                    client_secret: clientSecret
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                alert('IGDB credentials saved successfully!');
                
                // Reload the credential values to show the saved values
                await this.loadIgdbCredentialsValues();
                
                // Update status
                await this.loadIgdbCredentialsStatus();
            } else {
                const error = await response.json();
                alert(`Failed to save credentials: ${error.error}`);
            }
        } catch (error) {
            alert('Error saving credentials. Please try again.');
        }
    }

    // Steam Configuration Functions
    openSteamScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadSteamSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('steamConfigurationModal'));
        modal.show();
    }
    
    loadSteamSettings() {
        // Load saved settings from cookies
        const savedOverwriteMediaFields = this.getCookie('overwriteMediaFieldsSteam');
        const savedOverwriteTextFields = this.getCookie('overwriteTextFieldsSteam');
        
        // Update modal checkboxes with saved values
        const overwriteMediaCheckbox = document.getElementById('overwriteMediaFieldsSteamModal');
        const overwriteTextCheckbox = document.getElementById('overwriteTextFieldsSteamModal');
        
        if (overwriteMediaCheckbox) {
            overwriteMediaCheckbox.checked = savedOverwriteMediaFields === 'true';
        }
        
        if (overwriteTextCheckbox) {
            overwriteTextCheckbox.checked = savedOverwriteTextFields === 'true';
        }
        
        // Load field selection settings
        this.loadSteamFieldSettings();
    }
    
    async loadSteamFieldSettings() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const textFields = Object.keys(config.steam?.mapping || {});
            const mediaFields = Object.keys(config.steam?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Populate media fields dynamically
            this.populateSteamMediaFields(mediaFields);
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const cookieName = `steamField_${field}`;
                const savedValue = this.getCookie(cookieName);
                // Convert field name to checkbox ID format: field -> Field
                let fieldId;
                if (field === 'youtubeurl') {
                    fieldId = 'YoutubeUrl'; // Special case for YouTube URL
                } else {
                    fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                }
                const checkboxId = `steamField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                
                if (checkbox) {
                    if (savedValue !== null) {
                        checkbox.checked = savedValue === 'true';
                    } else {
                        // Default to checked if no saved value
                        checkbox.checked = true;
                    }
                } else {
                }
            });
        } catch (error) {
        }
    }
    
    populateSteamMediaFields(mediaFields) {
        const container = document.getElementById('steamMediaFieldsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        mediaFields.forEach(field => {
            const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
            const checkboxId = `steamField${fieldId}`;
            
            const div = document.createElement('div');
            div.className = 'form-check mb-2';
            div.innerHTML = `
                <input class="form-check-input steam-field-checkbox" type="checkbox" id="${checkboxId}" data-field="${field}" checked>
                <label class="form-check-label" for="${checkboxId}">${field}</label>
            `;
            container.appendChild(div);
            
            // Attach event listener to the newly created checkbox
            const checkbox = document.getElementById(checkboxId);
            if (checkbox) {
                checkbox.addEventListener('change', async () => {
                    await this.saveSteamFieldSettings();
                });
            }
        });
    }
    
    async saveSteamFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const textFields = Object.keys(config.steam?.mapping || {});
            const mediaFields = Object.keys(config.steam?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Save field selections to cookies
            allFields.forEach(field => {
                // Convert field name to checkbox ID format: field -> Field
                let fieldId;
                if (field === 'youtubeurl') {
                    fieldId = 'YoutubeUrl'; // Special case for YouTube URL
                } else {
                    fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                }
                const checkboxId = `steamField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                const cookieName = `steamField_${field}`;
                
                if (checkbox) {
                    this.setCookie(cookieName, checkbox.checked);
                } else {
                }
            });
        } catch (error) {
        }
    }

    // SteamGridDB Configuration Functions
    openSteamGridDBScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadSteamGridDBSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('steamgriddbConfigurationModal'));
        modal.show();
    }
    
    loadSteamGridDBSettings() {
        // Load saved settings from cookies
        const savedOverwriteMediaFields = this.getCookie('overwriteMediaFieldsSteamGridDB');
        
        // Update modal checkboxes with saved values
        const overwriteMediaCheckbox = document.getElementById('overwriteMediaFieldsSteamGridDBModal');
        
        if (overwriteMediaCheckbox) {
            overwriteMediaCheckbox.checked = savedOverwriteMediaFields === 'true';
        }
        
        // Load field selection settings
        this.loadSteamGridDBFieldSettings();
    }
    
    async loadSteamGridDBFieldSettings() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const textFields = Object.keys(config.steamgriddb?.mapping || {});
            const mediaFields = Object.keys(config.steamgriddb?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Populate media fields dynamically
            this.populateSteamGridDBMediaFields(mediaFields);
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const cookieName = `steamgriddbField_${field}`;
                const savedValue = this.getCookie(cookieName);
                // Convert field name to checkbox ID format: field -> Field
                const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                const checkboxId = `steamgriddbField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                
                if (checkbox) {
                    if (savedValue !== null) {
                        checkbox.checked = savedValue === 'true';
                    } else {
                        // Default to checked if no saved value
                        checkbox.checked = true;
                    }
                } else {
                }
            });
        } catch (error) {
        }
    }
    
    populateSteamGridDBMediaFields(mediaFields) {
        const container = document.getElementById('steamgriddbMediaFieldsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        mediaFields.forEach(field => {
            const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
            const checkboxId = `steamgriddbField${fieldId}`;
            
            const div = document.createElement('div');
            div.className = 'form-check mb-2';
            div.innerHTML = `
                <input class="form-check-input steamgriddb-field-checkbox" type="checkbox" id="${checkboxId}" data-field="${field}" checked>
                <label class="form-check-label" for="${checkboxId}">${field}</label>
            `;
            container.appendChild(div);
            
            // Attach event listener to the newly created checkbox
            const checkbox = document.getElementById(checkboxId);
            if (checkbox) {
                checkbox.addEventListener('change', async () => {
                    await this.saveSteamGridDBFieldSettings();
                });
            }
        });
    }
    
    async saveSteamGridDBFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const textFields = Object.keys(config.steamgriddb?.mapping || {});
            const mediaFields = Object.keys(config.steamgriddb?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Save field selections to cookies
            allFields.forEach(field => {
                // Convert field name to checkbox ID format: field -> Field
                const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                const checkboxId = `steamgriddbField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                const cookieName = `steamgriddbField_${field}`;
                
                if (checkbox) {
                    this.setCookie(cookieName, checkbox.checked);
                } else {
                }
            });
        } catch (error) {
        }
    }

    // ScreenScraper Configuration Functions
    async openScreenscraperScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadScreenscraperSettings();
        
        // Initialize dynamic field checkboxes from config
        await this.initializeScreenscraperFieldCheckboxes();
        
        // Load field settings AFTER checkboxes are created
        this.loadScreenscraperFieldSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('screenscraperConfigurationModal'));
        modal.show();
    }
    
    async openMobygamesScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadMobygamesSettings();
        
        // Populate media fields
        await this.populateMobygamesMediaFields();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('mobygamesConfigurationModal'));
        modal.show();
    }
    
    async openDatscrapperScrapPreferencesModal() {
        // Load current settings before opening modal
        this.loadDatscrapperSettings();
        
        // Populate dynamic field checkboxes
        await this.populateDatscrapperFieldCheckboxes();
        
        // Initialize field checkboxes
        this.initializeDatscrapperFieldCheckboxes();
        
        // Add event listener for overwrite text fields checkbox
        const overwriteTextCheckbox = document.getElementById('overwriteTextFieldsDatscrapperModal');
        if (overwriteTextCheckbox) {
            overwriteTextCheckbox.addEventListener('change', (e) => {
                this.setCookie('overwriteTextFieldsDatscrapper', e.target.checked.toString(), 365);
            });
        }
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('datscrapperConfigurationModal'));
        modal.show();
    }
    
    loadDatscrapperSettings() {
        // Load saved settings from cookies
        const overwriteTextFields = this.getCookie('overwriteTextFieldsDatscrapper') === 'true';
        
        // Set checkbox states
        const overwriteTextCheckbox = document.getElementById('overwriteTextFieldsDatscrapperModal');
        
        if (overwriteTextCheckbox) {
            overwriteTextCheckbox.checked = overwriteTextFields;
        }
        
        // Load field settings
        this.loadDatscrapperFieldSettings();
    }
    
    loadDatscrapperFieldSettings() {
        // This function is no longer needed since populateDatscrapperFieldCheckboxes()
        // now handles individual cookie loading directly
        // The old 'selectedDatscrapperFields' cookie is deprecated
    }
    
    saveDatscrapperSettings() {
        // Save settings to cookies
        const overwriteTextFields = document.getElementById('overwriteTextFieldsDatscrapperModal')?.checked || false;
        
        this.setCookie('overwriteTextFieldsDatscrapper', overwriteTextFields.toString());
        
        // Field selections are now saved individually via event listeners
        // The old 'selectedDatscrapperFields' cookie is deprecated
    }
    
    async populateDatscrapperFieldCheckboxes() {
        try {
            // Get DAT scraper mappings from config
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const container = document.getElementById('datscrapperFieldCheckboxes');
            if (!container) return;
            
            // Clear existing checkboxes
            container.innerHTML = '';
            
            if (config.datscrapper && config.datscrapper.mapping) {
                const mappings = config.datscrapper.mapping;
                
                // Create a row for the checkboxes
                const row = document.createElement('div');
                row.className = 'row';
                
                // Get the mapped fields and create checkboxes
                Object.entries(mappings).forEach(([datField, gamelistField], index) => {
                    const col = document.createElement('div');
                    col.className = 'col-md-6';
                    
                    const checkboxId = `datscrapperField${gamelistField.charAt(0).toUpperCase() + gamelistField.slice(1)}`;
                    
                    // Check if this field should be checked based on cookie
                    const cookieName = `datscrapperField_${gamelistField}`;
                    const cookieValue = this.getCookie(cookieName);
                    const isChecked = cookieValue === 'true';
                    
                    // Debug logging for name field
                    if (gamelistField === 'name') {
                        console.log(`🔧 DEBUG: Name field - cookieName: ${cookieName}, cookieValue: ${cookieValue}, isChecked: ${isChecked}`);
                    }
                    
                    col.innerHTML = `
                        <div class="form-check mb-2">
                            <input class="form-check-input datscrapper-field-checkbox" type="checkbox" id="${checkboxId}" data-field="${gamelistField}" ${isChecked ? 'checked' : ''}>
                            <label class="form-check-label" for="${checkboxId}">${this.getFieldDisplayName(datField)} (${gamelistField})</label>
                        </div>
                    `;
                    
                    // Debug logging for name field - check state after creation
                    if (gamelistField === 'name') {
                        setTimeout(() => {
                            const checkbox = document.getElementById(checkboxId);
                            if (checkbox) {
                                console.log(`🔧 DEBUG: Name checkbox after creation - checked: ${checkbox.checked}, has checked attribute: ${checkbox.hasAttribute('checked')}`);
                            }
                        }, 100);
                    }
                    
                    row.appendChild(col);
                });
                
                container.appendChild(row);
            } else {
                container.innerHTML = '<div class="alert alert-warning">No DAT scraper field mappings found. Please configure field mappings in Scraper Configuration.</div>';
            }
        } catch (error) {
            console.error('Error populating DAT scraper field checkboxes:', error);
            const container = document.getElementById('datscrapperFieldCheckboxes');
            if (container) {
                container.innerHTML = '<div class="alert alert-danger">Error loading field mappings.</div>';
            }
        }
    }
    
    getFieldDisplayName(datField) {
        const fieldNames = {
            'description': 'Name',
            'year': 'Release Year',
            'manufacturer': 'Developer',
            'genre': 'Genre',
            'developer': 'Developer'
        };
        return fieldNames[datField] || datField.charAt(0).toUpperCase() + datField.slice(1);
    }
    
    loadMobygamesSettings() {
        // Load saved settings from cookies
        const overwriteTextFields = this.getCookie('overwriteTextFieldsMobygames') === 'true';
        const overwriteMediaFields = this.getCookie('overwriteMediaFieldsMobygames') === 'true';
        
        // Set checkbox states
        const overwriteTextFieldsCheckbox = document.getElementById('overwriteTextFieldsMobygamesModal');
        const overwriteMediaFieldsCheckbox = document.getElementById('overwriteMediaFieldsMobygamesModal');
        
        if (overwriteTextFieldsCheckbox) {
            overwriteTextFieldsCheckbox.checked = overwriteTextFields;
        }
        if (overwriteMediaFieldsCheckbox) {
            overwriteMediaFieldsCheckbox.checked = overwriteMediaFields;
        }
        
        // Add event listeners for immediate cookie saving
        if (overwriteTextFieldsCheckbox) {
            overwriteTextFieldsCheckbox.addEventListener('change', (e) => {
                this.setCookie('overwriteTextFieldsMobygames', e.target.checked.toString(), 365);
            });
        }
        if (overwriteMediaFieldsCheckbox) {
            overwriteMediaFieldsCheckbox.addEventListener('change', (e) => {
                this.setCookie('overwriteMediaFieldsMobygames', e.target.checked.toString(), 365);
            });
        }
        
        // Add event listeners for field selection
        this.initializeMobygamesFieldCheckboxes();
    }
    
    async populateMobygamesMediaFields() {
        try {
            // Get MobyGames field mappings from config
            const response = await fetch('/api/config');
            const config = await response.json();
            
            if (!config) {
                console.error('Failed to load config');
                return;
            }
            
            const imageTypeMappings = config.mobygames?.image_type_mappings || {};
            
            // Get the media fields container
            const mediaFieldsContainer = document.getElementById('mobygamesMediaFieldsContainer');
            
            // Clear existing media field checkboxes
            mediaFieldsContainer.innerHTML = '';
            
            // Add media field checkboxes dynamically
            Object.keys(imageTypeMappings).forEach(gamelistField => {
                const fieldId = gamelistField.replace(/[^a-zA-Z0-9]/g, '');
                const checkboxId = `mobygamesMediaField${fieldId}`;
                
                // Create checkbox container
                const checkboxContainer = document.createElement('div');
                checkboxContainer.className = 'form-check mb-2';
                
                // Get the MobyGames media types for this gamelist field
                const mobygamesTypes = imageTypeMappings[gamelistField];
                const mobygamesTypesText = Array.isArray(mobygamesTypes) ? mobygamesTypes.join(', ') : mobygamesTypes;
                
                checkboxContainer.innerHTML = `
                    <input class="form-check-input mobygames-media-field-checkbox" type="checkbox" id="${checkboxId}" data-gamelist-field="${gamelistField}" checked>
                    <label class="form-check-label" for="${checkboxId}">
                        ${gamelistField.charAt(0).toUpperCase() + gamelistField.slice(1)}
                        <small class="text-muted d-block">(${mobygamesTypesText})</small>
                    </label>
                `;
                
                mediaFieldsContainer.appendChild(checkboxContainer);
            });
            
            // Initialize media field checkboxes
            this.initializeMobygamesMediaFieldCheckboxes();
            
        } catch (error) {
            console.error('Error populating MobyGames media fields:', error);
        }
    }
    
    initializeMobygamesMediaFieldCheckboxes() {
        // Load saved media field selections from cookies
        const mediaFieldCheckboxes = document.querySelectorAll('.mobygames-media-field-checkbox');
        mediaFieldCheckboxes.forEach(checkbox => {
            const gamelistField = checkbox.dataset.gamelistField;
            const savedState = this.getCookie(`mobygamesMediaField_${gamelistField}`);
            if (savedState !== null) {
                checkbox.checked = savedState === 'true';
            }
            
            // Add event listeners for media field checkboxes
            checkbox.addEventListener('change', (e) => {
                // Save media field selection to cookies
                this.setCookie(`mobygamesMediaField_${gamelistField}`, e.target.checked.toString(), 365);
            });
        });
    }
    
    initializeMobygamesFieldCheckboxes() {
        // Load saved field selections from cookies
        const fieldCheckboxes = document.querySelectorAll('.mobygames-field-checkbox');
        fieldCheckboxes.forEach(checkbox => {
            const field = checkbox.dataset.field;
            const savedState = this.getCookie(`mobygamesField_${field}`);
            
            // If cookie exists, use its value; if not, default to checked for certain fields
            if (savedState !== null) {
                checkbox.checked = savedState === 'true';
            } else {
                // Default to checked for title, description, publisher, developer, moby_score, release_year, genres, and nbvotes
                const defaultCheckedFields = ['title', 'description', 'publisher', 'developer', 'moby_score', 'release_year', 'genres', 'nbvotes'];
                checkbox.checked = defaultCheckedFields.includes(field);
            }
            
            // Add event listeners for field checkboxes
            checkbox.addEventListener('change', (e) => {
                // Save field selection to cookies
                this.setCookie(`mobygamesField_${field}`, e.target.checked.toString(), 365);
            });
        });
        
        // Add select all/deselect all functionality
        const selectAllBtn = document.getElementById('selectAllMobygamesFields');
        const deselectAllBtn = document.getElementById('deselectAllMobygamesFields');
        
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                fieldCheckboxes.forEach(checkbox => {
                    checkbox.checked = true;
                    const field = checkbox.dataset.field;
                    this.setCookie(`mobygamesField_${field}`, 'true', 365);
                });
            });
        }
        
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', () => {
                fieldCheckboxes.forEach(checkbox => {
                    checkbox.checked = false;
                    const field = checkbox.dataset.field;
                    this.setCookie(`mobygamesField_${field}`, 'false', 365);
                });
            });
        }
        
        // Load saved field selections (duplicate code - keeping for compatibility)
        fieldCheckboxes.forEach(checkbox => {
            const field = checkbox.dataset.field;
            const saved = this.getCookie(`mobygamesField_${field}`);
            
            // If cookie exists, use its value; if not, default to checked for certain fields
            if (saved !== null) {
                checkbox.checked = saved === 'true';
            } else {
                // Default to checked for title, description, publisher, developer, moby_score, release_year, genres, and nbvotes
                const defaultCheckedFields = ['title', 'description', 'publisher', 'developer', 'moby_score', 'release_year', 'genres', 'nbvotes'];
                checkbox.checked = defaultCheckedFields.includes(field);
            }
        });
    }
    
    initializeDatscrapperFieldCheckboxes() {
        // Add event listeners for DAT Scrapper field checkboxes
        const fieldCheckboxes = document.querySelectorAll('.datscrapper-field-checkbox');
        
        fieldCheckboxes.forEach(checkbox => {
            const field = checkbox.dataset.field;
            
            // Debug logging for name field
            if (field === 'name') {
                console.log(`🔧 DEBUG: initializeDatscrapperFieldCheckboxes - name checkbox before: checked=${checkbox.checked}`);
            }
            
            // Add event listeners for field checkboxes
            checkbox.addEventListener('change', (e) => {
                // Save field selection to cookies
                this.setCookie(`datscrapperField_${field}`, e.target.checked.toString(), 365);
            });
            
            // Debug logging for name field after event listener
            if (field === 'name') {
                console.log(`🔧 DEBUG: initializeDatscrapperFieldCheckboxes - name checkbox after: checked=${checkbox.checked}`);
            }
        });
        
        // Add select all/deselect all functionality
        const selectAllBtn = document.getElementById('selectAllDatscrapperFields');
        const deselectAllBtn = document.getElementById('deselectAllDatscrapperFields');
        
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                fieldCheckboxes.forEach(checkbox => {
                    checkbox.checked = true;
                    const field = checkbox.dataset.field;
                    this.setCookie(`datscrapperField_${field}`, 'true', 365);
                });
            });
        }
        
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', () => {
                fieldCheckboxes.forEach(checkbox => {
                    checkbox.checked = false;
                    const field = checkbox.dataset.field;
                    this.setCookie(`datscrapperField_${field}`, 'false', 365);
                });
            });
        }
        
        // Note: Field selections are now loaded in populateDatscrapperFieldCheckboxes()
        // This function only handles event listeners
    }
    
    loadScreenscraperSettings() {
        // Load saved settings from cookies
        const overwriteTextFields = this.getCookie('overwriteTextFieldsScreenscraper') === 'true';
        const overwriteMediaFields = this.getCookie('overwriteMediaFieldsScreenscraper') === 'true';
        
        // Set checkbox states
        document.getElementById('overwriteTextFieldsScreenscraperModal').checked = overwriteTextFields;
        document.getElementById('overwriteMediaFieldsScreenscraperModal').checked = overwriteMediaFields;
        
        // Load field selection settings
        this.loadScreenscraperFieldSettings();
    }
    
    async loadScreenscraperCredentialsStatus() {
        try {
            const response = await fetch('/api/screenscraper-credentials');
            if (response.ok) {
                const data = await response.json();
                this.updateScreenscraperCredentialsStatus(data);
                this.loadScreenscraperCredentialsValues();
            } else {
            }
        } catch (error) {
        }
    }
    
    async loadScreenscraperCredentialsValues() {
        try {
            const response = await fetch('/api/screenscraper-credentials-values');
            if (response.ok) {
                const data = await response.json();
                // Populate the form fields with current values
                if (data.ssid) {
                    document.getElementById('screenscraperSsId').value = data.ssid;
                }
                if (data.sspassword) {
                    document.getElementById('screenscraperSsPassword').value = data.sspassword;
                }
            } else {
            }
        } catch (error) {
        }
    }
    
    async loadIgdbCredentialsValues() {
        try {
            const response = await fetch('/api/igdb-credentials-values');
            if (response.ok) {
                const data = await response.json();
                // Populate the form fields with current values
                if (data.client_id) {
                    document.getElementById('igdbClientId').value = data.client_id;
                }
                if (data.client_secret) {
                    document.getElementById('igdbClientSecret').value = data.client_secret;
                }
            } else {
            }
        } catch (error) {
        }
    }
    
    updateScreenscraperCredentialsStatus(data) {
        const statusElement = document.getElementById('screenscraperCredentialsStatus');
        if (data.configured) {
            statusElement.innerHTML = '<i class="bi bi-check-circle text-success me-1"></i>Credentials configured';
            statusElement.className = 'text-success';
        } else {
            statusElement.innerHTML = '<i class="bi bi-info-circle me-1"></i>No credentials configured';
            statusElement.className = 'text-muted';
        }
    }
    
    async saveScreenscraperCredentials() {
        const ssId = document.getElementById('screenscraperSsId').value.trim();
        const ssPassword = document.getElementById('screenscraperSsPassword').value.trim();
        
        if (!ssId || !ssPassword) {
            alert('Please enter all ScreenScraper credentials');
            return;
        }
        
        try {
            const response = await fetch('/api/screenscraper-credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    dev_id: 'djspirit',  // Use static developer credentials
                    dev_password: 'cUIYyyJaImL',  // Use static developer credentials
                    ss_id: ssId,
                    ss_password: ssPassword
                })
            });
            
            if (response.ok) {
                alert('ScreenScraper credentials saved successfully!');
                
                // Reload the credential values to show the saved values
                await this.loadScreenscraperCredentialsValues();
                
                // Update status
                await this.loadScreenscraperCredentialsStatus();
            } else {
                const error = await response.json();
                alert(`Failed to save credentials: ${error.error}`);
            }
        } catch (error) {
            alert('Error saving credentials. Please try again.');
        }
    }
    
    async loadIgdbFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get IGDB field mappings from config
            const textFields = Object.keys(config.igdb?.mapping || {});
            const mediaFields = Object.keys(config.igdb?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Populate media fields dynamically
            this.populateIgdbMediaFields(mediaFields);
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const cookieName = `igdbField_${field}`;
                const savedValue = this.getCookie(cookieName);
                // Convert field name to checkbox ID format: field -> Field
                const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                const checkboxId = `igdbField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);

                if (checkbox) {
                    // Default to checked if no saved value (first time)
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                } else {
                }
            });
        } catch (error) {
        }
    }
    
    populateIgdbMediaFields(mediaFields) {
        const container = document.getElementById('igdbMediaFieldsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        mediaFields.forEach(field => {
                const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                const checkboxId = `igdbField${fieldId}`;
            
            const div = document.createElement('div');
            div.className = 'form-check mb-2';
            div.innerHTML = `
                <input class="form-check-input igdb-field-checkbox" type="checkbox" id="${checkboxId}" data-field="${field}" checked>
                <label class="form-check-label" for="${checkboxId}">${field}</label>
            `;
            container.appendChild(div);
            
            // Attach event listener to the newly created checkbox
            const checkbox = document.getElementById(checkboxId);
            if (checkbox) {
                checkbox.addEventListener('change', async () => {
                    await this.saveIgdbFieldSettings();
                });
            }
        });
    }
    
    async saveIgdbFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get IGDB field mappings from config
            const textFields = Object.keys(config.igdb?.mapping || {});
            const mediaFields = Object.keys(config.igdb?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Save field selections to cookies
            allFields.forEach(field => {
                // Convert field name to checkbox ID format: field -> Field
                const fieldId = field.charAt(0).toUpperCase() + field.slice(1);
                const checkboxId = `igdbField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                const cookieName = `igdbField_${field}`;
                if (checkbox) {
                    this.setCookie(cookieName, checkbox.checked);
                } else {
                }
            });
        } catch (error) {
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'name', 'summary', 'developer', 'publisher', 'genre', 
                'rating', 'players', 'release_date', 'cover', 'screenshots', 'artworks', 'logos'
            ];
            
            fallbackFields.forEach(field => {
                // Convert field name to checkbox ID format: field_name -> FieldName
                const fieldId = field.split('_').map(word => 
                    word.charAt(0).toUpperCase() + word.slice(1)
                ).join('');
                const checkboxId = `igdbField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                if (checkbox) {
                    this.setCookie(`igdbField_${field}`, checkbox.checked);
                }
            });
        }
    }

    async loadScreenscraperFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get ScreenScraper field mappings from config
            // For text fields, use hardcoded field names since ScreenScraper doesn't have a text field mapping
            const textFields = ['name', 'description', 'developer', 'publisher', 'genre', 'rating', 'players', 'release_date'];
            const mediaFields = Object.keys(config.screenscraper?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const savedValue = this.getCookie(`screenscraperField_${field}`);
                // Convert field name to checkbox ID format: field_name -> FieldName
                const fieldId = field.split(/[-_]/).map(word => 
                    word.charAt(0).toUpperCase() + word.slice(1)
                ).join('');
                const checkboxId = `screenscraperField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);

                if (checkbox) {
                    // If cookie exists, use its value; if not, default to checked (first time)
                    checkbox.checked = savedValue === null ? true : savedValue === 'true';
                } else {
                }
            });
        } catch (error) {
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'name', 'description', 'developer', 'publisher', 'genre', 
                'rating', 'players', 'release_date', 'screenshot', 'titleshot', 
                'marquee', 'boxart', 'boxback', 'cartridge', 'fanart', 'video', 'manual', 'extra1'
            ];
            
            fallbackFields.forEach(field => {
                const savedValue = this.getCookie(`screenscraperField_${field}`);
                const checkbox = document.getElementById(`screenscraperField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                
                if (checkbox) {
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                }
            });
        }
    }
    
    async saveScreenscraperFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();

            // Get ScreenScraper field mappings from config
            // For text fields, use hardcoded field names since ScreenScraper doesn't have a text field mapping
            const textFields = ['name', 'description', 'developer', 'publisher', 'genre', 'rating', 'players', 'release_date'];
            const mediaFields = Object.keys(config.screenscraper?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Save field selections to cookies
            allFields.forEach(field => {
                // Convert field name to checkbox ID format: field_name -> FieldName
                const fieldId = field.split(/[-_]/).map(word => 
                    word.charAt(0).toUpperCase() + word.slice(1)
                ).join('');
                const checkboxId = `screenscraperField${fieldId}`;
                const checkbox = document.getElementById(checkboxId);
                if (checkbox) {
                    this.setCookie(`screenscraperField_${field}`, checkbox.checked);
                } else {
                }
            });
        } catch (error) {
        }
    }

    async getSelectedIgdbFields() {
        try {
            
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get IGDB field mappings from config
            const textFields = Object.keys(config.igdb?.mapping || {});
            const mediaFields = Object.keys(config.igdb?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];

            // If no fields found in config, use fallback
            if (allFields.length === 0) {
                const fallbackFields = [
                    'name', 'summary', 'developer', 'publisher', 'genre', 
                    'rating', 'players', 'release_date', 'cover', 'screenshots', 'artworks', 'logos'
                ];
                return fallbackFields;
            }
            
            // Read field selections directly from cookies (simplified approach)
            const selectedFields = [];
            let hasUncheckedInCookies = false;
            
            allFields.forEach(field => {
                const cookieName = `igdbField_${field}`;
                const cookieValue = this.getCookie(cookieName);
                
                if (cookieValue !== null) {
                    if (cookieValue === 'true') {
                        selectedFields.push(field);
                    } else {
                        hasUncheckedInCookies = true;
                    }
                } else {
                    selectedFields.push(field);
                }
            });

            // If we have some unchecked fields, return only the selected ones
            if (hasUncheckedInCookies) {
            return selectedFields;
            }
            
            // If all fields are selected (no unchecked fields), return all fields
            return allFields;
            
        } catch (error) {
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'name', 'summary', 'developer', 'publisher', 'genre', 
                'rating', 'players', 'release_date', 'cover', 'screenshots', 'artworks', 'logos'
            ];
            return fallbackFields;
        }
    }

    async initializeScreenscraperFieldCheckboxes() {
        
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get ScreenScraper field mappings from config
            const imageTypeMappings = config.screenscraper?.image_type_mappings || {};
            
            // Get the media fields container
            const mediaFieldsContainer = document.getElementById('screenscraperMediaFieldsContainer');
            
            // Clear existing media field checkboxes (keep the header)
            const existingMediaFields = mediaFieldsContainer.querySelectorAll('.form-check');
            existingMediaFields.forEach(checkbox => checkbox.remove());
            
            // Add media field checkboxes dynamically
            Object.keys(imageTypeMappings).forEach(gamelistField => {
                // Use gamelistField (gamelist field name) for checkbox ID to match save/load functions
                const fieldId = gamelistField.split(/[-_]/).map(word => 
                    word.charAt(0).toUpperCase() + word.slice(1)
                ).join('');
                const checkboxId = `screenscraperField${fieldId}`;
                
                // Create checkbox element
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check mb-2';
                checkboxDiv.innerHTML = `
                    <input class="form-check-input screenscraper-field-checkbox" type="checkbox" id="${checkboxId}" data-field="${gamelistField}" checked>
                    <label class="form-check-label" for="${checkboxId}">${gamelistField}</label>
                `;
                
                mediaFieldsContainer.appendChild(checkboxDiv);
            });
            
            // Add event listeners to new checkboxes
            mediaFieldsContainer.querySelectorAll('.screenscraper-field-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', async () => {
                    await this.saveScreenscraperFieldSettings();
                });
            });

        } catch (error) {
        }
    }
    async initializeLaunchboxFieldCheckboxes() {
        
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get LaunchBox field mappings from config
            const imageTypeMappings = config.launchbox?.image_type_mappings || {};
            
            // Get the media fields container
            const mediaFieldsContainer = document.getElementById('launchboxMediaFieldsContainer');
            
            // Clear existing media field checkboxes (keep the header)
            const existingMediaFields = mediaFieldsContainer.querySelectorAll('.form-check');
            existingMediaFields.forEach(checkbox => checkbox.remove());
            
            // Add media field checkboxes dynamically
            Object.keys(imageTypeMappings).forEach(launchboxField => {
                const fieldId = launchboxField.replace(/[^a-zA-Z0-9]/g, '');
                const checkboxId = `launchboxField${fieldId}`;
                
                // Create checkbox element
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check mb-2';
                checkboxDiv.innerHTML = `
                    <input class="form-check-input launchbox-field-checkbox" type="checkbox" id="${checkboxId}" data-field="${launchboxField}" checked>
                    <label class="form-check-label" for="${checkboxId}">${launchboxField}</label>
                `;
                
                mediaFieldsContainer.appendChild(checkboxDiv);
            });
            
            // Add event listeners to new checkboxes
            mediaFieldsContainer.querySelectorAll('.launchbox-field-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', async () => {
                    await this.saveLaunchboxFieldSettings();
                });
            });

        } catch (error) {
        }
    }

    formatFieldName(fieldName) {
        // Convert field names to human-readable format
        const nameMap = {
            'marquee': 'Marquee',
            'thumbnail': 'Thumbnail',
            'boxart': 'Box Art',
            'boxback': 'Box Back',
            'image': 'Screenshot',
            'titleshot': 'Title Shot',
            'manual': 'Manual',
            'video': 'Video',
            'fanart': 'Fan Art',
            'cartridge': 'Cartridge'
        };
        
        return nameMap[fieldName] || fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
    }

    async getSelectedScreenscraperFields() {
        
        // Fetch config to get dynamic field mappings
        const response = await fetch('/api/config');
        const config = await response.json();
        
        // Get ScreenScraper field mappings from config
        // ScreenScraper has image_type_mappings that map gamelist field names to arrays of ScreenScraper API field names
        // We need to use the KEYS (gamelist field names) for checkboxes, which match what the checkboxes use
        const mediaFields = Object.keys(config.screenscraper?.image_type_mappings || {});
        
        // For text fields, we need to use the hardcoded field names that match the HTML checkboxes
        // since ScreenScraper doesn't have a text field mapping in the config
        const textFields = ['name', 'description', 'developer', 'publisher', 'genre', 'rating', 'players', 'release_date'];
        
        const allFields = [...textFields, ...mediaFields];

        // Read field selections directly from cookies (simplified approach)
        const selectedFields = [];
        let hasUncheckedInCookies = false;
        
        allFields.forEach(field => {
            const cookieName = `screenscraperField_${field}`;
            const cookieValue = this.getCookie(cookieName);
            
            if (cookieValue !== null) {
                if (cookieValue === 'true') {
                selectedFields.push(field);
            } else {
                    hasUncheckedInCookies = true;
                }
            } else {
                selectedFields.push(field);
            }
        });

        // If we have some unchecked fields, return only the selected ones
        if (hasUncheckedInCookies) {
        return selectedFields;
        }
        
        // If all fields are selected (no unchecked fields), return all fields
        return allFields;
    }

    async getSelectedSteamFields() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get Steam field mappings from config
            const textFields = Object.keys(config.steam?.mapping || {});
            const mediaFields = Object.keys(config.steam?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Read field selections from cookies
            const selectedFields = [];
            allFields.forEach(field => {
                const cookieName = `steamField_${field}`;
                const cookieValue = this.getCookie(cookieName);
                
                // If no cookie or cookie is true, include the field
                if (cookieValue === null || cookieValue === 'true') {
                    selectedFields.push(field);
                }
            });
            
            return selectedFields;
        } catch (error) {
            return ['boxart', 'marquee', 'fanart', 'image'];
        }
    }

    async getSelectedSteamgriddbFields() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get SteamGridDB field mappings from config
            const textFields = Object.keys(config.steamgriddb?.mapping || {});
            const mediaFields = Object.keys(config.steamgriddb?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Read field selections from cookies
            const selectedFields = [];
            allFields.forEach(field => {
                const cookieName = `steamgriddbField_${field}`;
                const cookieValue = this.getCookie(cookieName);
                
                // If no cookie or cookie is true, include the field
                if (cookieValue === null || cookieValue === 'true') {
                    selectedFields.push(field);
                }
            });
            
            return selectedFields;
        } catch (error) {
            return ['boxart', 'marquee', 'fanart'];
        }
    }

    async loadLaunchboxFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get LaunchBox field mappings from config
            const textFields = Object.keys(config.launchbox?.mapping || {});
            const mediaFields = Object.keys(config.launchbox?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const savedValue = this.getCookie(`launchboxField_${field}`);
                const checkbox = document.getElementById(`launchboxField${field.replace(/[^a-zA-Z0-9]/g, '')}`);
                
                if (checkbox) {
                    // If cookie exists, use its value; if not, default to checked (first time)
                    checkbox.checked = savedValue === null ? true : savedValue === 'true';
                }
            });
        } catch (error) {
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'Name', 'Overview', 'Developer', 'Publisher', 'Genres', 
                'CommunityRating', 'MaxPlayers', 'Box - Front', 'Box - Back', 'Box - 3D',
                'Clear Logo', 'Screenshot - Game Title', 'Screenshot - Gameplay',
                'Fanart - Background', 'Cart - Front'
            ];
            
            fallbackFields.forEach(field => {
                const savedValue = this.getCookie(`launchboxField_${field}`);
                const checkbox = document.getElementById(`launchboxField${field.replace(/[^a-zA-Z0-9]/g, '')}`);
                
                if (checkbox) {
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                }
            });
        }
    }
    
    async saveLaunchboxFieldSettings() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get LaunchBox field mappings from config
            const textFields = Object.keys(config.launchbox?.mapping || {});
            const mediaFields = Object.keys(config.launchbox?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Save field selections to cookies
            allFields.forEach(field => {
                const checkbox = document.getElementById(`launchboxField${field.replace(/[^a-zA-Z0-9]/g, '')}`);
                if (checkbox) {
                    this.setCookie(`launchboxField_${field}`, checkbox.checked);
                }
            });
        } catch (error) {
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'Name', 'Overview', 'Developer', 'Publisher', 'Genres', 
                'CommunityRating', 'MaxPlayers', 'Box - Front', 'Box - Back', 'Box - 3D',
                'Clear Logo', 'Screenshot - Game Title', 'Screenshot - Gameplay',
                'Fanart - Background', 'Cart - Front'
            ];
            
            fallbackFields.forEach(field => {
                const checkbox = document.getElementById(`launchboxField${field.replace(/[^a-zA-Z0-9]/g, '')}`);
                if (checkbox) {
                    this.setCookie(`launchboxField_${field}`, checkbox.checked);
                }
            });
        }
    }
    
    async getSelectedLaunchboxFields() {
        try {
            
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get LaunchBox field mappings from config
            const textFields = Object.keys(config.launchbox?.mapping || {});
            const mediaFields = Object.keys(config.launchbox?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];

            // If no fields found in config, use fallback
            if (allFields.length === 0) {
                const fallbackFields = [
                    'Name', 'Overview', 'Developer', 'Publisher', 'Genres', 
                    'CommunityRating', 'MaxPlayers', 'Box - Front', 'Box - Back', 'Box - 3D',
                    'Clear Logo', 'Screenshot - Game Title', 'Screenshot - Gameplay',
                    'Fanart - Background', 'Cart - Front'
                ];
                return fallbackFields;
            }
            
            // Read field selections directly from cookies (simplified approach)
            const selectedFields = [];
            let hasUncheckedInCookies = false;
            
            allFields.forEach(field => {
                const cookieName = `launchboxField_${field}`;
                const cookieValue = this.getCookie(cookieName);
                
                if (cookieValue !== null) {
                    if (cookieValue === 'true') {
                        selectedFields.push(field);
                    } else {
                        hasUncheckedInCookies = true;
                    }
                } else {
                    selectedFields.push(field);
                }
            });

            // If we have some unchecked fields, return only the selected ones
            if (hasUncheckedInCookies) {
            return selectedFields;
            }
            
            // If all fields are selected (no unchecked fields), return all fields
            return allFields;
            
        } catch (error) {
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'Name', 'Overview', 'Developer', 'Publisher', 'Genres', 
                'CommunityRating', 'MaxPlayers', 'Box - Front', 'Box - Back', 'Box - 3D',
                'Clear Logo', 'Screenshot - Game Title', 'Screenshot - Gameplay',
                'Fanart - Background', 'Cart - Front'
            ];
            return fallbackFields;
        }
    }
    
    openSystemsConfigurationModal() {
        // Show loading state in modal body
        this.showSystemsModalLoadingState();
        
        // Open the modal immediately
        const modal = new bootstrap.Modal(document.getElementById('systemsConfigurationModal'));
        modal.show();
        
        // Load systems data asynchronously after modal is shown
        this.loadSystemsData();
    }

    async openRemapMediaFieldModal() {
        try {
            const modal = new bootstrap.Modal(document.getElementById('remapMediaFieldModal'));
            modal.show();
            
            // Load source fields (fields with media files from current gamelist)
            await this.loadSourceFields();
            
            // Load target fields (available media fields from configuration)
            await this.loadTargetFields();
            
            // Set up validation button
            this.setupRemapValidation();
            
        } catch (error) {
            console.error('Error opening remap media field modal:', error);
            this.showAlert('Error opening remap media field modal', 'danger');
        }
    }

    async loadSourceFields() {
        try {
            const response = await fetch('/api/remap-media-fields/source', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ system_name: this.currentSystem })
            });
            
            const data = await response.json();
            const sourceSelect = document.getElementById('sourceFieldSelect');
            
            if (data.success && data.fields) {
                sourceSelect.innerHTML = '<option value="">Select source field...</option>';
                data.fields.forEach(field => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = field;
                    sourceSelect.appendChild(option);
                });
            } else {
                sourceSelect.innerHTML = '<option value="">No media fields found</option>';
            }
        } catch (error) {
            console.error('Error loading source fields:', error);
            this.showAlert('Error loading source fields', 'danger');
        }
    }

    async loadTargetFields() {
        try {
            const response = await fetch('/api/remap-media-fields/target');
            const data = await response.json();
            const targetSelect = document.getElementById('targetFieldSelect');
            
            if (data.success && data.fields) {
                targetSelect.innerHTML = '<option value="">Select target field...</option>';
                data.fields.forEach(field => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = field;
                    targetSelect.appendChild(option);
                });
            } else {
                targetSelect.innerHTML = '<option value="">No target fields available</option>';
            }
        } catch (error) {
            console.error('Error loading target fields:', error);
            this.showAlert('Error loading target fields', 'danger');
        }
    }

    setupRemapValidation() {
        const sourceSelect = document.getElementById('sourceFieldSelect');
        const targetSelect = document.getElementById('targetFieldSelect');
        const validateBtn = document.getElementById('validateRemapBtn');
        
        const updateValidateButton = () => {
            const sourceValue = sourceSelect.value;
            const targetValue = targetSelect.value;
            validateBtn.disabled = !sourceValue || !targetValue || sourceValue === targetValue;
        };
        
        sourceSelect.addEventListener('change', updateValidateButton);
        targetSelect.addEventListener('change', updateValidateButton);
        
        // Add event listener for validate button
        validateBtn.addEventListener('click', () => this.validateRemap());
    }

    async validateRemap() {
        const sourceField = document.getElementById('sourceFieldSelect').value;
        const targetField = document.getElementById('targetFieldSelect').value;
        
        if (!sourceField || !targetField || sourceField === targetField) {
            this.showAlert('Please select different source and target fields', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/remap-media-fields/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    source_field: sourceField,
                    target_field: targetField
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Successfully remapped ${sourceField} to ${targetField}`, 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('remapMediaFieldModal'));
                modal.hide();
                
                // Refresh the grid to show changes
                await this.refreshGridData();
            } else {
                this.showAlert(data.error || 'Error remapping fields', 'danger');
            }
        } catch (error) {
            console.error('Error validating remap:', error);
            this.showAlert('Error validating remap', 'danger');
        }
    }

    async openMoveMediasModal() {
        try {
            const modal = new bootstrap.Modal(document.getElementById('moveMediasModal'));
            modal.show();
            
            // Reset UI state
            this.resetMoveMediasUI();
            
            // Load media fields from configuration
            await this.loadMoveMediasFields();
            
            // Set up validation button
            this.setupMoveMediasValidation();
            
        } catch (error) {
            console.error('Error opening move medias modal:', error);
            this.showAlert('Error opening move medias modal', 'danger');
        }
    }

    async loadMoveMediasFields() {
        try {
            const response = await fetch('/api/remap-media-fields/target');
            const data = await response.json();
            const mediaFieldSelect = document.getElementById('mediaFieldSelect');
            
            if (data.success && data.fields) {
                mediaFieldSelect.innerHTML = '<option value="">Select media field...</option>';
                data.fields.forEach(field => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = field;
                    mediaFieldSelect.appendChild(option);
                });
            } else {
                mediaFieldSelect.innerHTML = '<option value="">No media fields available</option>';
            }
        } catch (error) {
            console.error('Error loading move medias fields:', error);
            this.showAlert('Error loading media fields', 'danger');
        }
    }

    setupMoveMediasValidation() {
        const mediaFieldSelect = document.getElementById('mediaFieldSelect');
        const validateBtn = document.getElementById('validateMoveMediasBtn');
        const confirmBtn = document.getElementById('confirmMoveMediasBtn');
        
        const updateValidateButton = () => {
            const fieldValue = mediaFieldSelect.value;
            validateBtn.disabled = !fieldValue;
        };
        
        mediaFieldSelect.addEventListener('change', updateValidateButton);
        
        // Add event listener for validate button (dry-run)
        validateBtn.addEventListener('click', () => this.validateMoveMedias());
        
        // Add event listener for confirm button (actual move)
        confirmBtn.addEventListener('click', () => this.confirmMoveMedias());
    }

    async validateMoveMedias() {
        const mediaField = document.getElementById('mediaFieldSelect').value;
        
        if (!mediaField) {
            this.showAlert('Please select a media field', 'warning');
            return;
        }
        
        try {
            // Do a dry run to show what would happen
            const dryRunResponse = await fetch('/api/move-medias/dry-run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    media_field: mediaField
                })
            });
            
            const dryRunData = await dryRunResponse.json();
            
            if (dryRunData.success) {
                // Show dry-run results in modal
                this.showMoveMediasDryRunResults(dryRunData.results);
                
                // Store the media field for confirmation
                this.pendingMoveMediaField = mediaField;
                
                // Show confirm button and hide validate button
                document.getElementById('validateMoveMediasBtn').style.display = 'none';
                document.getElementById('confirmMoveMediasBtn').style.display = 'inline-block';
            } else {
                this.showAlert(dryRunData.error || 'Error in dry run', 'danger');
            }
        } catch (error) {
            console.error('Error in dry run:', error);
            this.showAlert('Error in dry run', 'danger');
        }
    }

    async confirmMoveMedias() {
        if (!this.pendingMoveMediaField) {
            this.showAlert('No pending move operation', 'warning');
            return;
        }
        
        try {
            // Proceed with actual move
            const response = await fetch('/api/move-medias/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    media_field: this.pendingMoveMediaField
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show actual results
                this.showMoveMediasResults(data.results);
                
                // Show close button and hide other buttons
                this.showMoveMediasCloseState();
                
                // Refresh the grid to show changes
                await this.refreshGridData();
            } else {
                // Handle conflicts or other errors
                if (data.conflicts && data.conflicts.length > 0) {
                    this.showMoveMediasConflicts(data.conflicts);
                } else {
                    this.showAlert(data.error || 'Error moving media files', 'danger');
                }
            }
        } catch (error) {
            console.error('Error executing move medias:', error);
            this.showAlert('Error moving media files', 'danger');
        }
    }
    
    resetMoveMediasUI() {
        // Reset button states to initial state
        document.getElementById('validateMoveMediasBtn').style.display = 'inline-block';
        document.getElementById('confirmMoveMediasBtn').style.display = 'none';
        document.getElementById('closeMoveMediasBtn').style.display = 'none';
        
        // Clear pending operation
        this.pendingMoveMediaField = null;
        
        // Hide error/results section
        const errorDiv = document.getElementById('moveMediasError');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
        
        // Reset media field selection
        const mediaFieldSelect = document.getElementById('mediaFieldSelect');
        if (mediaFieldSelect) {
            mediaFieldSelect.value = '';
        }
    }
    
    showMoveMediasCloseState() {
        // Hide all action buttons
        document.getElementById('validateMoveMediasBtn').style.display = 'none';
        document.getElementById('confirmMoveMediasBtn').style.display = 'none';
        
        // Show close button
        document.getElementById('closeMoveMediasBtn').style.display = 'inline-block';
        
        // Clear pending operation
        this.pendingMoveMediaField = null;
    }

    showMoveMediasConflicts(conflicts) {
        const errorDiv = document.getElementById('moveMediasError');
        const errorContent = document.getElementById('moveMediasErrorContent');
        
        let html = '<ul class="mb-0">';
        
        conflicts.forEach(conflict => {
            html += `
                <li>
                    <strong>${conflict.game_name}</strong>: ${conflict.filename}
                </li>
            `;
        });
        
        html += '</ul>';
        errorContent.innerHTML = html;
        errorDiv.style.display = 'block';
    }

    showMoveMediasDryRunResults(results) {
        const errorDiv = document.getElementById('moveMediasError');
        const errorContent = document.getElementById('moveMediasErrorContent');
        
        const summary = results.summary;
        let html = `
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                <strong>Dry Run Results</strong> - This is what would happen if you proceed:
                <div class="mt-2">
                    <span class="badge bg-primary me-2">Move: ${summary.would_move_count}</span>
                    <span class="badge bg-warning me-2">Skip: ${summary.would_skip_count}</span>
                    <span class="badge bg-danger">Clear: ${summary.would_clear_count}</span>
                </div>
            </div>
        `;
        html += '<div class="accordion" id="dryRunResultsAccordion">';
        
        // Would move files section
        if (results.would_move_files.length > 0) {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="wouldMoveFilesHeader">
                        <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#wouldMoveFiles" aria-expanded="true">
                            <i class="bi bi-arrow-right-circle-fill text-primary me-2"></i>
                            Would Move Files (${results.would_move_files.length})
                        </button>
                    </h2>
                    <div id="wouldMoveFiles" class="accordion-collapse collapse show" data-bs-parent="#dryRunResultsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
            `;
            
            results.would_move_files.forEach(file => {
                html += `
                    <div class="list-group-item list-group-item-primary">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-arrow-right text-primary me-2"></i>
                            <div>
                                <strong>${file.game_name}</strong><br>
                                <small class="text-muted">${file.old_path} → ${file.new_path}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div></div></div>';
        }
        
        // Would skip files section
        if (results.would_skip_files.length > 0) {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="wouldSkipFilesHeader">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#wouldSkipFiles">
                            <i class="bi bi-skip-forward-circle-fill text-warning me-2"></i>
                            Would Skip Files (${results.would_skip_files.length})
                        </button>
                    </h2>
                    <div id="wouldSkipFiles" class="accordion-collapse collapse" data-bs-parent="#dryRunResultsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
            `;
            
            results.would_skip_files.forEach(file => {
                html += `
                    <div class="list-group-item list-group-item-warning">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-skip-forward text-warning me-2"></i>
                            <div>
                                <strong>${file.game_name}</strong><br>
                                <small class="text-muted">${file.current_path}</small><br>
                                <small class="text-danger">Reason: ${file.reason}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div></div></div>';
        }
        
        // Would clear fields section
        if (results.would_clear_fields.length > 0) {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="wouldClearFieldsHeader">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#wouldClearFields">
                            <i class="bi bi-trash-circle-fill text-danger me-2"></i>
                            Would Clear Fields (${results.would_clear_fields.length})
                        </button>
                    </h2>
                    <div id="wouldClearFields" class="accordion-collapse collapse" data-bs-parent="#dryRunResultsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
            `;
            
            results.would_clear_fields.forEach(field => {
                html += `
                    <div class="list-group-item list-group-item-danger">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-trash text-danger me-2"></i>
                            <div>
                                <strong>${field.game_name}</strong><br>
                                <small class="text-muted">${field.old_path}</small><br>
                                <small class="text-danger">Reason: ${field.reason}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div></div></div>';
        }
        
        html += '</div>';
        errorContent.innerHTML = html;
        errorDiv.style.display = 'block';
    }

    showMoveMediasResults(results) {
        const errorDiv = document.getElementById('moveMediasError');
        const errorContent = document.getElementById('moveMediasErrorContent');
        
        const summary = results.summary;
        let html = `
            <div class="alert alert-success mb-3">
                <i class="bi bi-check-circle me-2"></i>
                <strong>Move Operation Completed!</strong>
                <div class="mt-2">
                    <span class="badge bg-success me-2">Moved: ${summary.moved_count}</span>
                    <span class="badge bg-warning me-2">Skipped: ${summary.unmoved_count}</span>
                    <span class="badge bg-danger">Cleared: ${summary.cleared_count}</span>
                </div>
            </div>
        `;
        html += '<div class="accordion" id="moveResultsAccordion">';
        
        // Moved files section
        if (results.moved_files.length > 0) {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="movedFilesHeader">
                        <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#movedFiles" aria-expanded="true">
                            <i class="bi bi-check-circle-fill text-success me-2"></i>
                            Moved Files (${results.moved_files.length})
                        </button>
                    </h2>
                    <div id="movedFiles" class="accordion-collapse collapse show" data-bs-parent="#moveResultsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
            `;
            
            results.moved_files.forEach(file => {
                html += `
                    <div class="list-group-item list-group-item-success">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-arrow-right text-success me-2"></i>
                            <div>
                                <strong>${file.game_name}</strong><br>
                                <small class="text-muted">${file.old_path} → ${file.new_path}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div></div></div>';
        }
        
        // Unmoved files section
        if (results.unmoved_files.length > 0) {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="unmovedFilesHeader">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#unmovedFiles">
                            <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>
                            Unmoved Files (${results.unmoved_files.length})
                        </button>
                    </h2>
                    <div id="unmovedFiles" class="accordion-collapse collapse" data-bs-parent="#moveResultsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
            `;
            
            results.unmoved_files.forEach(file => {
                html += `
                    <div class="list-group-item list-group-item-warning">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-exclamation-triangle text-warning me-2"></i>
                            <div>
                                <strong>${file.game_name}</strong><br>
                                <small class="text-muted">${file.current_path}</small><br>
                                <small class="text-danger">Reason: ${file.reason}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div></div></div>';
        }
        
        // Cleared fields section
        if (results.cleared_fields.length > 0) {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="clearedFieldsHeader">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#clearedFields">
                            <i class="bi bi-trash-fill text-danger me-2"></i>
                            Cleared Fields (${results.cleared_fields.length})
                        </button>
                    </h2>
                    <div id="clearedFields" class="accordion-collapse collapse" data-bs-parent="#moveResultsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
            `;
            
            results.cleared_fields.forEach(field => {
                html += `
                    <div class="list-group-item list-group-item-danger">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-trash text-danger me-2"></i>
                            <div>
                                <strong>${field.game_name}</strong><br>
                                <small class="text-muted">${field.old_path}</small><br>
                                <small class="text-danger">Reason: ${field.reason}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div></div></div>';
        }
        
        html += '</div>';
        errorContent.innerHTML = html;
        errorDiv.style.display = 'block';
    }

    // Resize Medias Methods
    async openResizeMediasModal() {
        try {
            const modal = new bootstrap.Modal(document.getElementById('resizeMediasModal'));
            modal.show();
            
            // Reset UI state
            this.resetResizeMediasUI();
            
            // Load media fields from configuration
            await this.loadResizeMediasFields();
            
        } catch (error) {
            console.error('Error opening resize medias modal:', error);
            this.showAlert('Error opening resize medias modal', 'danger');
        }
    }

    // Import Medias Methods
    async openImportMediasModal() {
        try {
            const modal = new bootstrap.Modal(document.getElementById('importMediasModal'));
            modal.show();
            
            // Reset UI state
            this.resetImportMediasUI();
            
            // Update current system name in modal
            document.getElementById('importCurrentSystemName').textContent = this.currentSystem || 'currentsystem';
            
            // Load source directories and target fields
            await this.loadImportMediasData();
            
        } catch (error) {
            console.error('Error opening import medias modal:', error);
            this.showAlert('Error opening import medias modal', 'danger');
        }
    }

    resetImportMediasUI() {
        // Reset form fields
        document.getElementById('importSourceDirectory').value = '';
        document.getElementById('importTargetField').value = '';
        document.getElementById('importOverwriteExisting').checked = false;
        
        // Clear dropdowns
        document.getElementById('importSourceDirectory').innerHTML = '<option value="">Select source directory...</option>';
        document.getElementById('importTargetField').innerHTML = '<option value="">Select target field...</option>';
    }

    async loadImportMediasData() {
        try {
            // Load source directories
            await this.loadImportSourceDirectories();
            
            // Load target media fields
            await this.loadImportTargetFields();
            
        } catch (error) {
            console.error('Error loading import medias data:', error);
            this.showAlert('Error loading import medias data', 'danger');
        }
    }

    async loadImportSourceDirectories() {
        try {
            const response = await fetch(`/api/import-medias/source-directories/${this.currentSystem}`);
            const data = await response.json();
            
            const select = document.getElementById('importSourceDirectory');
            select.innerHTML = '<option value="">Select source directory...</option>';
            
            if (data.directories && data.directories.length > 0) {
                data.directories.forEach(dir => {
                    const option = document.createElement('option');
                    option.value = dir;
                    option.textContent = dir;
                    select.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No source directories found';
                option.disabled = true;
                select.appendChild(option);
            }
            
        } catch (error) {
            console.error('Error loading source directories:', error);
            this.showAlert('Error loading source directories', 'danger');
        }
    }

    async loadImportTargetFields() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const select = document.getElementById('importTargetField');
            select.innerHTML = '<option value="">Select target field...</option>';
            
            if (config.media_fields) {
                Object.entries(config.media_fields).forEach(([field, info]) => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = `${field} (${info.description || field})`;
                    select.appendChild(option);
                });
            }
            
        } catch (error) {
            console.error('Error loading target fields:', error);
            this.showAlert('Error loading target fields', 'danger');
        }
    }

    async loadResizeMediasFields() {
        try {
            const response = await fetch('/api/remap-media-fields/target');
            const data = await response.json();
            const mediaFieldSelect = document.getElementById('resizeMediaFieldSelect');
            
            if (data.success && data.fields) {
                mediaFieldSelect.innerHTML = '<option value="">Select media field...</option><option value="all">All Media Fields</option>';
                data.fields.forEach(field => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = field;
                    mediaFieldSelect.appendChild(option);
                });
            } else {
                mediaFieldSelect.innerHTML = '<option value="">No media fields available</option>';
            }
        } catch (error) {
            console.error('Error loading resize medias fields:', error);
            this.showAlert('Error loading media fields', 'danger');
        }
    }

    resetResizeMediasUI() {
        // Reset media field selection
        const mediaFieldSelect = document.getElementById('resizeMediaFieldSelect');
        if (mediaFieldSelect) {
            mediaFieldSelect.value = '';
        }
        
        // Reset button states
        document.getElementById('startResizeMediasBtn').disabled = false;
    }

    async startResizeMedias() {
        const mediaField = document.getElementById('resizeMediaFieldSelect').value;
        
        if (!mediaField) {
            this.showAlert('Please select a media field', 'warning');
            return;
        }

        try {
            // Disable button to prevent multiple submissions
            document.getElementById('startResizeMediasBtn').disabled = true;

            // Start the resize task
            const response = await fetch('/api/resize-medias', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    media_field: mediaField,
                    system_name: this.currentSystem
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Resize task started successfully', 'success');
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('resizeMediasModal'));
                if (modal) {
                    modal.hide();
                }
            } else {
                this.showAlert(data.error || 'Error starting resize task', 'danger');
                this.resetResizeMediasUI();
            }
        } catch (error) {
            console.error('Error starting resize medias:', error);
            this.showAlert('Error starting resize task', 'danger');
            this.resetResizeMediasUI();
        }
    }

    async startImportMedias() {
        const sourceDirectory = document.getElementById('importSourceDirectory').value;
        const targetField = document.getElementById('importTargetField').value;
        const overwriteExisting = document.getElementById('importOverwriteExisting').checked;
        
        if (!sourceDirectory) {
            this.showAlert('Please select a source directory', 'warning');
            return;
        }
        
        if (!targetField) {
            this.showAlert('Please select a target media field', 'warning');
            return;
        }

        try {
            // Disable button to prevent multiple submissions
            document.getElementById('startImportMediasBtn').disabled = true;

            // Start the import task
            const response = await fetch('/api/import-medias', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    source_directory: sourceDirectory,
                    target_field: targetField,
                    overwrite_existing: overwriteExisting
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Import medias task started successfully', 'success');
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('importMediasModal'));
                if (modal) {
                    modal.hide();
                }
            } else {
                this.showAlert(data.error || 'Error starting import task', 'danger');
                this.resetImportMediasUI();
            }
        } catch (error) {
            console.error('Error starting import medias:', error);
            this.showAlert('Error starting import task', 'danger');
            this.resetImportMediasUI();
        } finally {
            // Re-enable button
            document.getElementById('startImportMediasBtn').disabled = false;
        }
    }

    
    showSystemsModalLoadingState() {
        const modalBody = document.querySelector('#systemsConfigurationModal .modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="d-flex align-items-center justify-content-center py-5">
                    <div class="text-center">
                        <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h6 class="text-muted">Loading systems configuration...</h6>
                        <p class="text-muted small mb-0">Please wait while we fetch the latest data</p>
                    </div>
                </div>
            `;
        }
    }

    async loadSystemsData() {
        try {
            const response = await fetch('/api/systems');
            const data = await response.json();
            
            if (data.success) {
                this.populateSystemsTable(data.systems);
            } else {
                this.showAlert('Failed to load systems data', 'danger');
                this.showSystemsModalErrorState();
            }
        } catch (error) {
            this.showAlert('Error loading systems data', 'danger');
            this.showSystemsModalErrorState();
        }
    }

    showSystemsModalErrorState() {
        const modalBody = document.querySelector('#systemsConfigurationModal .modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h6 class="alert-heading">
                        <i class="bi bi-exclamation-triangle me-2"></i>Error Loading Data
                    </h6>
                    <p class="mb-2">Failed to load systems configuration data. Please try again.</p>
                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="gameManager.loadSystemsData()">
                        <i class="bi bi-arrow-clockwise me-1"></i>Retry
                    </button>
                </div>
            `;
        }
    }

    restoreSystemsModalStructure() {
        const modalBody = document.querySelector('#systemsConfigurationModal .modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <div>
                    <h6>Configured Systems</h6>
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-success btn-sm" id="addMissingSystemsBtn">
                            <i class="bi bi-folder-plus me-1"></i>Add Missing Systems
                        </button>
                        <button type="button" class="btn btn-primary btn-sm" id="addSystemBtn">
                            <i class="bi bi-plus-circle me-1"></i>Add System
                        </button>
                        <button type="button" class="btn btn-outline-secondary btn-sm" id="refreshSystemsBtn">
                            <i class="bi bi-arrow-clockwise me-1"></i>Refresh
                        </button>
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-sm table-striped table-hover compact-table" id="systemsTable">
                        <thead>
                            <tr>
                                <th style="width: 10%">System</th>
                                <th style="width: 12%">Launchbox</th>
                                <th style="width: 12%">Screenscraper</th>
                                <th style="width: 12%">IGDB</th>
                                <th style="width: 12%">MobyGames</th>
                                <th style="width: 12%">DAT File</th>
                                <th style="width: 30%">Extensions</th>
                            </tr>
                        </thead>
                        <tbody id="systemsTableBody">
                            <!-- Systems will be populated here -->
                        </tbody>
                    </table>
                </div>
                <div class="text-muted small mt-2">
                    <i class="bi bi-info-circle me-1"></i>
                    <strong>Tip:</strong> Click on any field in the table to edit it directly. Changes are saved automatically when you click away or press Enter.
                </div>
            `;
        }
    }

    initializeSystemScraperConfigModal() {
        // Add event listener for save button
        const saveBtn = document.getElementById('saveScraperMappingsBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveScraperMappings());
        }
    }

    async saveScraperMappings() {
        const saveBtn = document.getElementById('saveScraperMappingsBtn');
        const originalText = saveBtn.innerHTML;
        
        try {
            // Show loading state
            saveBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-1"></i>Saving...';
            saveBtn.disabled = true;
            
            // Get form values
            const mappings = {
                launchbox: document.getElementById('launchboxMapping').value,
                igdb: document.getElementById('igdbMapping').value,
                mobygames: document.getElementById('mobygamesMapping').value,
                screenscraper: document.getElementById('screenscraperMapping').value,
                dat_file: document.getElementById('datscrapperMapping').value
            };
            
            // Get extensions value and convert to array
            const extensionsText = document.getElementById('extensionsMapping').value.trim();
            const extensions = extensionsText ? 
                extensionsText.split(',').map(ext => ext.trim()).filter(ext => ext) : [];
            
            // Update the system configuration
            const response = await fetch('/api/systems', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    system_name: this.currentSystem,
                    launchbox_platform: mappings.launchbox,
                    screenscraper_platform: mappings.screenscraper,
                    igdb_platform: mappings.igdb,
                    mobygames_platform: mappings.mobygames,
                    extensions: extensions
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert('Scraper mappings saved successfully!', 'success');
                    
                    // Close the modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('systemScraperConfigModal'));
                    modal.hide();
                } else {
                    this.showAlert(result.error || 'Failed to save mappings', 'danger');
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Failed to save mappings', 'danger');
            }
        } catch (error) {
            console.error('Error saving scraper mappings:', error);
            this.showAlert('Error saving scraper mappings: ' + error.message, 'danger');
        } finally {
            // Restore button state
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    }

    attachSystemsModalEventListeners() {
        // Add missing systems button
        const addMissingSystemsBtn = document.getElementById('addMissingSystemsBtn');
        if (addMissingSystemsBtn) {
            addMissingSystemsBtn.addEventListener('click', () => {
                this.showAddMissingSystemsModal();
            });
        }
        
        // Add system button
        const addSystemBtn = document.getElementById('addSystemBtn');
        if (addSystemBtn) {
            addSystemBtn.addEventListener('click', () => {
                this.showAddSystemPrompt();
            });
        }
        
        // Refresh button
        const refreshSystemsBtn = document.getElementById('refreshSystemsBtn');
        if (refreshSystemsBtn) {
            refreshSystemsBtn.addEventListener('click', () => {
                this.loadSystemsData();
            });
        }
        
        // Event delegation for dynamically created elements
        const systemsTable = document.getElementById('systemsTable');
        if (systemsTable) {
            // Handle platform field clicks
            systemsTable.addEventListener('click', (e) => {
                if (e.target.closest('.platform-field')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const field = e.target.closest('.platform-field');
                    const systemName = field.dataset.system;
                    const fieldType = field.dataset.field;
                    const platformType = field.dataset.type;
                    this.showPlatformSelector(systemName, fieldType, platformType, field);
                }
            });
            
            // Handle extensions input blur and enter
            systemsTable.addEventListener('blur', (e) => {
                if (e.target.classList.contains('extensions-input')) {
                    const systemName = e.target.dataset.system;
                    const value = e.target.value;
                    this.saveInlineField(systemName, 'extensions', value);
                }
            }, true);
            
            systemsTable.addEventListener('keypress', (e) => {
                if (e.target.classList.contains('extensions-input') && e.key === 'Enter') {
                    e.target.blur();
                }
            });
            
            // Handle delete button clicks
            systemsTable.addEventListener('click', (e) => {
                if (e.target.closest('.delete-system-btn')) {
                    const systemName = e.target.closest('.delete-system-btn').dataset.system;
                    this.deleteSystem(systemName);
                }
            });
        }
    }
    
    isSystemsConfigCacheValid() {
        if (!this.systemsConfigCache.lastUpdated) return false;
        const now = Date.now();
        return (now - this.systemsConfigCache.lastUpdated) < this.systemsConfigCache.cacheTimeout;
    }
    
    clearSystemsConfigCache() {
        this.systemsConfigCache.platforms = null;
        this.systemsConfigCache.screenscraperSystems = null;
        this.systemsConfigCache.igdbPlatforms = null;
        this.systemsConfigCache.mobygamesSystems = null;
        this.systemsConfigCache.lastUpdated = null;
        console.log('Cleared systems configuration cache');
    }
    
    async populateSystemsTable(systems) {
        // First, restore the original modal structure
        this.restoreSystemsModalStructure();
        
        // Reattach event listeners after restoring structure
        this.attachSystemsModalEventListeners();
        
        const tbody = document.getElementById('systemsTableBody');
        if (!tbody) return;
        
        // Check if we have valid cached data
        if (this.isSystemsConfigCacheValid() && 
            this.systemsConfigCache.platforms && 
            this.systemsConfigCache.screenscraperSystems && 
            this.systemsConfigCache.igdbPlatforms && 
            this.systemsConfigCache.mobygamesSystems &&
            this.systemsConfigCache.datscrapperFiles) {
            
            console.log('Using cached systems configuration data');
            // Load systems data for cached version
            fetch('/api/systems').then(response => response.json()).then(data => {
                if (data.success) {
                    this.populateSystemsTableWithData(
                        this.systemsConfigCache.platforms,
                        this.systemsConfigCache.screenscraperSystems,
                        this.systemsConfigCache.igdbPlatforms,
                        this.systemsConfigCache.mobygamesSystems,
                        this.systemsConfigCache.datscrapperFiles,
                        data.systems
                    );
                } else {
                    throw new Error('Failed to load systems data');
                }
            }).catch(error => {
                console.error('Error loading systems data for cached version:', error);
                // Fall back to loading fresh data
                this.loadSystemsData();
            });
            return;
        }
        
        // Show loading message while fetching platform data
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <div class="d-flex align-items-center justify-content-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <span>Loading platform data from ScreenScraper, IGDB, and MobyGames APIs...</span>
                    </div>
                </td>
            </tr>
        `;
        
        // Load LaunchBox platforms, ScreenScraper systems, IGDB platforms, and MobyGames systems for comboboxes
        let platforms = [], screenscraperSystems = [], igdbPlatforms = [], mobygamesSystems = [], datscrapperFiles = [];
        
        try {
            [platforms, screenscraperSystems, igdbPlatforms, mobygamesSystems, datscrapperFiles] = await Promise.all([
                this.loadLaunchBoxPlatforms(),
                this.loadScreenScraperSystems(),
                this.loadIgdbPlatforms(),
                this.loadMobygamesSystems(),
                this.loadDatscrapperFiles()
            ]);

            // Cache the results
            this.systemsConfigCache.platforms = platforms;
            this.systemsConfigCache.screenscraperSystems = screenscraperSystems;
            this.systemsConfigCache.igdbPlatforms = igdbPlatforms;
            this.systemsConfigCache.mobygamesSystems = mobygamesSystems;
            this.systemsConfigCache.datscrapperFiles = datscrapperFiles;
            this.systemsConfigCache.lastUpdated = Date.now();
            
            console.log('Cached systems configuration data');

        } catch (error) {
            // Show error message
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4">
                        <div class="alert alert-warning mb-0">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Error loading platform data. Some comboboxes may be empty.
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        // Load systems data and populate table
        this.loadSystemsData().then(() => {
            // Get systems data from the API
            return fetch('/api/systems').then(response => response.json());
        }).then(data => {
            if (data.success) {
                this.populateSystemsTableWithData(platforms, screenscraperSystems, igdbPlatforms, mobygamesSystems, datscrapperFiles, data.systems);
            } else {
                throw new Error('Failed to load systems data');
            }
        }).catch(error => {
            console.error('Error loading systems config:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4">
                        <div class="alert alert-warning mb-0">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Error loading systems configuration.
                        </div>
                    </td>
                </tr>
            `;
        });
    }
    
    populateSystemsTableWithData(platforms, screenscraperSystems, igdbPlatforms, mobygamesSystems, datscrapperFiles, systems) {
        const tbody = document.getElementById('systemsTableBody');
        if (!tbody) return;
        
        // Clear loading message and populate table
        tbody.innerHTML = '';
        
        // Debug: Log the types of the parameters
        console.log('populateSystemsTableWithData called with:', {
            platforms: typeof platforms, 
            platformsIsArray: Array.isArray(platforms),
            screenscraperSystems: typeof screenscraperSystems,
            screenscraperIsArray: Array.isArray(screenscraperSystems),
            igdbPlatforms: typeof igdbPlatforms,
            igdbIsArray: Array.isArray(igdbPlatforms),
            mobygamesSystems: typeof mobygamesSystems,
            mobygamesIsArray: Array.isArray(mobygamesSystems)
        });
        
        // Ensure platforms is an array
        const platformsArray = Array.isArray(platforms) ? platforms : [];
        const screenscraperArray = Array.isArray(screenscraperSystems) ? screenscraperSystems : [];
        const igdbArray = Array.isArray(igdbPlatforms) ? igdbPlatforms : [];
        const mobygamesArray = Array.isArray(mobygamesSystems) ? mobygamesSystems : [];
        
        // Use the systems data passed as parameter
        Object.entries(systems).forEach(([systemName, systemData]) => {
            const row = document.createElement('tr');
            
            // Helper function to get display name for platform values
            const getDisplayName = (value, type) => {
                if (!value) return 'Not set';
                
                switch (type) {
                    case 'launchbox':
                        return value;
                    case 'screenscraper':
                        const screenscraperSystem = screenscraperArray.find(s => s.id == value);
                        return screenscraperSystem ? screenscraperSystem.name : value;
                    case 'igdb':
                        const igdbPlatform = igdbArray.find(p => p.id == value);
                        return igdbPlatform ? igdbPlatform.name : value;
                    case 'mobygames':
                        return value;
                    default:
                        return value;
                }
            };
            
            row.innerHTML = `
                <td>
                    <div class="d-flex align-items-center justify-content-between">
                        <strong>${systemName}</strong>
                        <button class="btn btn-outline-danger btn-sm delete-system-btn" data-system="${systemName}" title="Delete System">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
                <td>
                    <div class="platform-field" 
                            data-system="${systemName}"
                         data-field="launchbox" 
                         data-type="launchbox"
                         style="cursor: pointer; padding: 0.375rem 0.75rem; border: 1px solid #ced4da; border-radius: 0.375rem; background-color: #fff; min-height: 38px; display: flex; align-items: center;"
                         title="Click to change LaunchBox platform">
                        <span class="platform-display">${getDisplayName(systemData.launchbox, 'launchbox')}</span>
                        <i class="bi bi-chevron-down ms-auto text-muted"></i>
                    </div>
                </td>
                <td>
                    <div class="platform-field" 
                            data-system="${systemName}"
                         data-field="screenscraper" 
                         data-type="screenscraper"
                         style="cursor: pointer; padding: 0.375rem 0.75rem; border: 1px solid #ced4da; border-radius: 0.375rem; background-color: #fff; min-height: 38px; display: flex; align-items: center;"
                         title="Click to change ScreenScraper platform">
                        <span class="platform-display">${getDisplayName(systemData.screenscraper, 'screenscraper')}</span>
                        <i class="bi bi-chevron-down ms-auto text-muted"></i>
                    </div>
                </td>
                <td>
                    <div class="platform-field" 
                            data-system="${systemName}"
                         data-field="igdb" 
                         data-type="igdb"
                         style="cursor: pointer; padding: 0.375rem 0.75rem; border: 1px solid #ced4da; border-radius: 0.375rem; background-color: #fff; min-height: 38px; display: flex; align-items: center;"
                         title="Click to change IGDB platform">
                        <span class="platform-display">${getDisplayName(systemData.igdb, 'igdb')}</span>
                        <i class="bi bi-chevron-down ms-auto text-muted"></i>
                    </div>
                </td>
                <td>
                    <div class="platform-field" 
                         data-system="${systemName}" 
                         data-field="mobygames" 
                         data-type="mobygames"
                         style="cursor: pointer; padding: 0.375rem 0.75rem; border: 1px solid #ced4da; border-radius: 0.375rem; background-color: #fff; min-height: 38px; display: flex; align-items: center;"
                         title="Click to change MobyGames platform">
                        <span class="platform-display">${getDisplayName(systemData.mobygames, 'mobygames')}</span>
                        <i class="bi bi-chevron-down ms-auto text-muted"></i>
                    </div>
                </td>
                <td>
                    <div class="platform-field" 
                         data-system="${systemName}" 
                         data-field="dat_file" 
                         data-type="datscrapper"
                         style="cursor: pointer; padding: 0.375rem 0.75rem; border: 1px solid #ced4da; border-radius: 0.375rem; background-color: #fff; min-height: 38px; display: flex; align-items: center;"
                         title="Click to change DAT file">
                        <span class="platform-display">${systemData.dat_file || 'Not set'}</span>
                        <i class="bi bi-chevron-down ms-auto text-muted"></i>
                    </div>
                </td>
                <td>
                    <input type="text" 
                           class="form-control form-control-sm extensions-input" 
                           value="${Array.isArray(systemData.extensions) ? systemData.extensions.join(', ') : ''}" 
                           placeholder="Extensions (comma-separated)"
                           data-system="${systemName}"
                           data-field="extensions">
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    async loadLaunchBoxPlatforms() {
        try {
            const response = await fetch('/api/launchbox-platforms');
            const data = await response.json();
            
            if (data.success) {
                return data.platforms;
            } else {
                return [];
            }
        } catch (error) {
            return [];
        }
    }
    
    async loadScreenScraperSystems() {
        try {
            const response = await fetch('/api/screenscraper-systems');
            const data = await response.json();
            if (data.systems) {
                return data.systems || [];
            } else {
                return [];
            }
        } catch (error) {
            return [];
        }
    }
    
    async loadIgdbPlatforms(retryCount = 0) {
        try {
            const response = await fetch('/api/igdb-platforms');
            
            if (!response.ok) {
                const errorText = await response.text();
                return [];
            }
            
            const data = await response.json();
            
            if (data.platforms) {
                
                // If platforms are empty but we have a message about cache creation, retry once
                if (data.platforms.length === 0 && data.message && data.message.includes('Cache will be created automatically') && retryCount === 0) {
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    return this.loadIgdbPlatforms(1); // Retry once
                }
                
                return data.platforms || [];
            } else {
                return [];
            }
        } catch (error) {
            return [];
        }
    }
    
    async loadMobygamesSystems() {
        try {
            const response = await fetch('/api/mobygames-systems');
            
            if (!response.ok) {
                return [];
            }
            
            const data = await response.json();
            
            if (data.success && data.systems) {
                // Sort systems alphabetically
                return data.systems.sort((a, b) => a.localeCompare(b));
            } else {
                return [];
            }
        } catch (error) {
            return [];
        }
    }
    
    async loadDatscrapperFiles() {
        try {
            const response = await fetch('/api/datscrapper/files');
            
            if (!response.ok) {
                return [];
            }
            
            const data = await response.json();
            
            if (data.success && data.files) {
                // Return file names sorted alphabetically
                return data.files.map(file => file.filename).sort((a, b) => a.localeCompare(b));
            } else {
                return [];
            }
        } catch (error) {
            return [];
        }
    }
    
    async showPlatformSelector(systemName, fieldType, platformType, fieldElement) {
        try {
            let options = [];
            let currentValue = '';
            
            // Get current value from the field
            const currentDisplay = fieldElement.querySelector('.platform-display').textContent;
            if (currentDisplay !== 'Not set') {
                currentValue = currentDisplay;
            }
            
            // Load options based on platform type
            switch (platformType) {
                case 'launchbox':
                    options = await this.loadLaunchBoxPlatforms();
                    break;
                case 'screenscraper':
                    options = await this.loadScreenScraperSystems();
                    break;
                case 'igdb':
                    options = await this.loadIgdbPlatforms();
                    break;
                case 'mobygames':
                    options = await this.loadMobygamesSystems();
                    break;
                case 'datscrapper':
                    options = await this.loadDatscrapperFiles();
                    break;
            }
            
            // Create and show dropdown
            this.showPlatformDropdown(fieldElement, options, currentValue, systemName, fieldType, platformType);
            
        } catch (error) {
            console.error('Error loading platform options:', error);
            this.showAlert('Error loading platform options', 'danger');
        }
    }
    
    showPlatformDropdown(fieldElement, options, currentValue, systemName, fieldType, platformType) {
        // Remove any existing dropdown
        const existingDropdown = document.querySelector('.platform-dropdown');
        if (existingDropdown) {
            existingDropdown.remove();
        }
        
        // Create dropdown container
        const dropdown = document.createElement('div');
        dropdown.className = 'platform-dropdown';
        dropdown.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #ced4da;
            border-radius: 0.375rem;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            z-index: 9999;
            max-height: 300px;
            overflow-y: auto;
            min-width: 250px;
        `;
        
        // Create options
        const optionsHtml = options.map(option => {
            let value, text, isSelected = false;
            
            switch (platformType) {
                case 'launchbox':
                    value = text = option;
                    isSelected = option === currentValue;
                    break;
                case 'screenscraper':
                    value = option.id;
                    text = option.name;
                    isSelected = option.name === currentValue;
                    break;
                case 'igdb':
                    value = option.id;
                    text = option.name;
                    isSelected = option.name === currentValue;
                    break;
                case 'mobygames':
                    value = text = option;
                    isSelected = option === currentValue;
                    break;
                case 'datscrapper':
                    value = text = option;
                    isSelected = option === currentValue;
                    break;
            }
            
            return `
                <div class="dropdown-option ${isSelected ? 'selected' : ''}" 
                     data-value="${value}" 
                     style="padding: 0.5rem 1rem; cursor: pointer; border-bottom: 1px solid #f8f9fa; ${isSelected ? 'background-color: #e3f2fd;' : ''}"
                     onmouseover="this.style.backgroundColor='#f8f9fa'" 
                     onmouseout="this.style.backgroundColor='${isSelected ? '#e3f2fd' : 'white'}'">
                    ${text}
                </div>
            `;
        }).join('');
        
        // Add "Clear" option
        const clearOption = `
            <div class="dropdown-option" 
                 data-value="" 
                 style="padding: 0.5rem 1rem; cursor: pointer; border-bottom: 1px solid #f8f9fa; color: #6c757d;"
                 onmouseover="this.style.backgroundColor='#f8f9fa'" 
                 onmouseout="this.style.backgroundColor='white'">
                <i class="bi bi-x-circle me-2"></i>Clear selection
            </div>
        `;
        
        dropdown.innerHTML = clearOption + optionsHtml;
        
        // Position dropdown
        const rect = fieldElement.getBoundingClientRect();
        dropdown.style.left = rect.left + 'px';
        dropdown.style.top = (rect.bottom + 2) + 'px';
        
        // Add to document
        document.body.appendChild(dropdown);
        
        // Handle option clicks
        dropdown.addEventListener('click', (e) => {
            const option = e.target.closest('.dropdown-option');
            if (option) {
                const value = option.dataset.value;
                const text = option.textContent.trim();
                
                // Update the field display
                const displaySpan = fieldElement.querySelector('.platform-display');
                displaySpan.textContent = value ? text : 'Not set';
                
                // Save the change
                this.saveInlineField(systemName, fieldType, value);
                
                // Remove dropdown
                dropdown.remove();
            }
        });
        
        // Close dropdown when clicking outside
        const closeDropdown = (e) => {
            if (!dropdown.contains(e.target) && !fieldElement.contains(e.target)) {
                dropdown.remove();
                document.removeEventListener('click', closeDropdown);
            }
        };
        
        // Add click listener immediately since we're preventing event bubbling
        document.addEventListener('click', closeDropdown);
    }
    
    async saveInlineField(systemName, field, value) {
        try {
            // Get current system data
            const response = await fetch('/api/systems');
            const data = await response.json();
            
            if (!data.success || !data.systems[systemName]) {
                this.showAlert('Failed to load system data', 'danger');
                return;
            }
            
            const currentSystem = data.systems[systemName];
            
            // Prepare update data
            let updateData = {
                system_name: systemName,
                launchbox_platform: currentSystem.launchbox || '',
                screenscraper_platform: currentSystem.screenscraper || '',
                igdb_platform: currentSystem.igdb || '',
                mobygames_platform: currentSystem.mobygames || '',
                dat_file: currentSystem.dat_file || '',
                extensions: Array.isArray(currentSystem.extensions) ? currentSystem.extensions : []
            };
            
            // Update the specific field
            if (field === 'launchbox') {
                updateData.launchbox_platform = value.trim();
            } else if (field === 'screenscraper') {
                updateData.screenscraper_platform = value.trim();
            } else if (field === 'igdb') {
                updateData.igdb_platform = value.trim();
            } else if (field === 'mobygames') {
                updateData.mobygames_platform = value.trim();
            } else if (field === 'dat_file') {
                updateData.dat_file = value.trim();
            } else if (field === 'extensions') {
                // Parse extensions from comma-separated string
                updateData.extensions = value.trim() ? 
                    value.split(',').map(ext => ext.trim()).filter(ext => ext) : [];
            }
            
            // Debug logging
            console.log('🔧 DEBUG: Frontend sending updateData:', updateData);
            console.log('🔧 DEBUG: Field being updated:', field, 'Value:', value);
            
            // Save the update
            const saveResponse = await fetch('/api/systems', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });
            
            const saveData = await saveResponse.json();
            
            if (saveData.success) {
                // Clear systems configuration cache since data changed
                this.clearSystemsConfigCache();
                
                // Show subtle success feedback
                const input = document.querySelector(`[data-system="${systemName}"][data-field="${field}"]`);
                if (input) {
                    input.classList.add('is-valid');
                    setTimeout(() => input.classList.remove('is-valid'), 1000);
                }
            } else {
                this.showAlert(`Failed to update ${field}: ${saveData.error}`, 'danger');
                // Reload data to revert changes
                this.loadSystemsData();
            }
        } catch (error) {
            this.showAlert('Error saving changes', 'danger');
            // Reload data to revert changes
            this.loadSystemsData();
        }
    }

    async deleteSystem(systemName) {
        if (!confirm(`Are you sure you want to delete the system "${systemName}"?`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/systems?system_name=${systemName}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('System deleted successfully', 'success');
                this.loadSystemsData(); // Reload the table
            } else {
                this.showAlert(`Failed to delete system: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error deleting system', 'danger');
        }
    }
    
    async showAddMissingSystemsModal() {
        try {
            // Fetch missing systems
            const response = await fetch('/api/systems/missing', {
                credentials: 'same-origin'
            });
            const data = await response.json();
            
            if (!data.success) {
                this.showAlert(data.error || 'Failed to load missing systems', 'danger');
                return;
            }
            
            const missingSystems = data.missing_systems || [];
            
            if (missingSystems.length === 0) {
                this.showAlert('No missing systems found. All systems in roms/ directory are already configured.', 'info');
                return;
            }
            
            // Create modal content
            const modalHtml = `
                <div class="modal fade" id="addMissingSystemsModal" tabindex="-1" aria-labelledby="addMissingSystemsModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addMissingSystemsModalLabel">
                                    <i class="bi bi-folder-plus me-2"></i>Add Missing Systems
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <p class="text-muted mb-3">
                                    The following systems were found in your <code>roms/</code> directory but are not configured yet:
                                </p>
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped">
                                        <thead>
                                            <tr>
                                                <th>
                                                    <input type="checkbox" id="selectAllMissing" class="form-check-input">
                                                </th>
                                                <th>System Name</th>
                                                <th>ROM Count</th>
                                                <th>Path</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${missingSystems.map(system => `
                                                <tr>
                                                    <td>
                                                        <input type="checkbox" class="form-check-input missing-system-checkbox" 
                                                               value="${system.name}" data-rom-count="${system.rom_count}">
                                                    </td>
                                                    <td><strong>${system.name}</strong></td>
                                                    <td>
                                                        <span class="badge ${system.rom_count > 0 ? 'bg-success' : 'bg-secondary'}">
                                                            ${system.rom_count} ROMs
                                                        </span>
                                                    </td>
                                                    <td><code>${system.path}</code></td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                                <div class="alert alert-info mt-3">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <strong>Note:</strong> Systems will be added with default empty configurations. 
                                    You can configure LaunchBox, ScreenScraper, and IGDB mappings after adding them.
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-success" id="addSelectedMissingSystems">
                                    <i class="bi bi-plus-circle me-1"></i>Add Selected Systems
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if it exists
            const existingModal = document.getElementById('addMissingSystemsModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add modal to DOM
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('addMissingSystemsModal'));
            modal.show();
            
            // Add event listeners
            this.setupMissingSystemsModalEvents();
            
        } catch (error) {
            this.showAlert('Error loading missing systems', 'danger');
        }
    }
    
    setupMissingSystemsModalEvents() {
        // Select all checkbox
        const selectAllCheckbox = document.getElementById('selectAllMissing');
        const systemCheckboxes = document.querySelectorAll('.missing-system-checkbox');
        
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                systemCheckboxes.forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                });
            });
        }
        
        // Add selected systems button
        const addSelectedBtn = document.getElementById('addSelectedMissingSystems');
        if (addSelectedBtn) {
            addSelectedBtn.addEventListener('click', () => {
                this.addSelectedMissingSystems();
            });
        }
        
        // Update select all checkbox when individual checkboxes change
        systemCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const checkedCount = document.querySelectorAll('.missing-system-checkbox:checked').length;
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = checkedCount === systemCheckboxes.length;
                    selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < systemCheckboxes.length;
                }
            });
        });
    }
    
    async addSelectedMissingSystems() {
        const selectedCheckboxes = document.querySelectorAll('.missing-system-checkbox:checked');
        const selectedSystems = Array.from(selectedCheckboxes).map(cb => cb.value);
        
        if (selectedSystems.length === 0) {
            this.showAlert('Please select at least one system to add', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/systems', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    system_names: selectedSystems
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(data.message, 'success');
                
                // Show details if there were any failures
                if (data.failed_systems && data.failed_systems.length > 0) {
                    const failedDetails = data.failed_systems.map(f => `${f.name}: ${f.error}`).join(', ');
                    this.showAlert(`Some systems failed to add: ${failedDetails}`, 'warning');
                }
                
                // Close modal and refresh systems data
                const modal = bootstrap.Modal.getInstance(document.getElementById('addMissingSystemsModal'));
                if (modal) {
                    modal.hide();
                }
                
                this.loadSystemsData();
            } else {
                this.showAlert(data.error || 'Failed to add systems', 'danger');
            }
        } catch (error) {
            this.showAlert('Error adding systems', 'danger');
        }
    }
    
    initializeSystemsModal() {
        // Add missing systems button
        const addMissingSystemsBtn = document.getElementById('addMissingSystemsBtn');
        if (addMissingSystemsBtn) {
            addMissingSystemsBtn.addEventListener('click', () => {
                this.showAddMissingSystemsModal();
            });
        }
        
        // Add system button
        const addSystemBtn = document.getElementById('addSystemBtn');
        if (addSystemBtn) {
            addSystemBtn.addEventListener('click', () => {
                this.showAddSystemPrompt();
            });
        }
        
        // Refresh button
        const refreshSystemsBtn = document.getElementById('refreshSystemsBtn');
        if (refreshSystemsBtn) {
            refreshSystemsBtn.addEventListener('click', () => {
                this.loadSystemsData();
            });
        }
        
        // Event delegation for dynamically created elements
        const systemsTable = document.getElementById('systemsTable');
        if (systemsTable) {
            // Handle platform field clicks
            systemsTable.addEventListener('click', (e) => {
                if (e.target.closest('.platform-field')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const field = e.target.closest('.platform-field');
                    const systemName = field.dataset.system;
                    const fieldType = field.dataset.field;
                    const platformType = field.dataset.type;
                    this.showPlatformSelector(systemName, fieldType, platformType, field);
                }
            });
            
            // Handle extensions input blur and enter
            systemsTable.addEventListener('blur', (e) => {
                if (e.target.classList.contains('extensions-input')) {
                    const systemName = e.target.dataset.system;
                    const value = e.target.value;
                    this.saveInlineField(systemName, 'extensions', value);
                }
            }, true);
            
            systemsTable.addEventListener('keypress', (e) => {
                if (e.target.classList.contains('extensions-input') && e.key === 'Enter') {
                    e.target.blur();
                }
            });
            
            // Handle delete button clicks
            systemsTable.addEventListener('click', (e) => {
                if (e.target.closest('.delete-system-btn')) {
                    const systemName = e.target.closest('.delete-system-btn').dataset.system;
                    this.deleteSystem(systemName);
                }
            });
        }
    }
    
    async showAddSystemPrompt() {
        const systemName = prompt('Enter system name (lowercase, no spaces):');
        if (!systemName || !systemName.trim()) {
            return;
        }
        
        const trimmedName = systemName.trim().toLowerCase();
        
        // Validate system name
        if (trimmedName.includes(' ') || !/^[a-z0-9]+$/.test(trimmedName)) {
            this.showAlert('System name must be lowercase letters and numbers only, no spaces', 'danger');
            return;
        }
        
        // Check if system already exists
        try {
            const response = await fetch('/api/systems');
            const data = await response.json();
            
            if (data.success && data.systems[trimmedName]) {
                this.showAlert('System already exists', 'danger');
                return;
            }
            
            // Add the new system with empty values
            const addResponse = await fetch('/api/systems', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    system_name: trimmedName,
                    launchbox_platform: '',
                    extensions: []
                })
            });
            
            const addData = await addResponse.json();
            
            if (addData.success) {
                this.showAlert('System added successfully', 'success');
                this.loadSystemsData(); // Reload the table
            } else {
                this.showAlert(`Failed to add system: ${addData.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error adding system', 'danger');
        }
    }
    
    async openScraperConfigurationModal() {
        const modalElement = document.getElementById('scraperConfigModal');
        const modal = new bootstrap.Modal(modalElement);
        
        // Load all data BEFORE showing the modal
        await this.loadMediaFieldsData();
        await this.loadLaunchboxMappingsData();
        await this.loadIgdbMappingsData();
        await this.loadScreenscraperMappingsData();
        await this.loadSteamMappingsData();
        await this.loadSteamgriddbMappingsData();
        await this.loadMobygamesMappingsData();
        await this.loadDatscrapperMappingsData();
        
        // Load credentials values for all services
        await this.loadScreenscraperCredentialsValues();
        await this.loadSteamgriddbCredentialsValues();
        
        modal.show();
        
        // Reset all tabs and activate the first tab (Media Fields)
        setTimeout(() => {
            // Remove active class from all tab buttons
            const allTabButtons = document.querySelectorAll('#scraperConfigTabs .nav-link');
            allTabButtons.forEach(button => {
                button.classList.remove('active');
                button.setAttribute('aria-selected', 'false');
            });
            
            // Remove active and show classes from all tab panes
            const allTabPanes = document.querySelectorAll('#scraperConfigTabContent .tab-pane');
            allTabPanes.forEach(pane => {
                pane.classList.remove('active', 'show');
            });
            
            // Activate the first tab (Media Fields)
            const firstTabButton = document.getElementById('media-fields-tab');
            const firstTabPane = document.getElementById('media-fields');
            
            if (firstTabButton && firstTabPane) {
                firstTabButton.classList.add('active');
                firstTabButton.setAttribute('aria-selected', 'true');
                firstTabPane.classList.add('active', 'show');
            }
        }, 100);
    }

    openMediaFieldsConfigurationModal() {
        // Load media fields data before opening modal
        this.loadMediaFieldsData();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('mediaFieldsConfigurationModal'));
        modal.show();
    }
    
    async loadMediaFieldsData() {
        try {
            const response = await fetch('/api/media-fields');
            const data = await response.json();
            
            if (data.success) {
                this.populateMediaFieldsTable(data.media_fields);
            } else {
                this.showAlert('Failed to load media fields data', 'danger');
            }
        } catch (error) {
            this.showAlert('Error loading media fields data', 'danger');
        }
    }
    
    async populateMediaFieldsTable(mediaFields) {
        const tbody = document.getElementById('mediaFieldsTableBody');
        if (!tbody) {
            return;
        }
        
        tbody.innerHTML = '';
        
        Object.entries(mediaFields).forEach(([fieldName, fieldConfig]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="field-name-display">${fieldName}</span>
                </td>
                <td>
                    <input type="text" class="form-control form-control-sm" 
                           data-field="directory" data-field-name="${fieldName}" 
                           value="${fieldConfig.directory || ''}" 
                           placeholder="e.g., boxarts">
                </td>
                <td>
                    <input type="text" class="form-control form-control-sm" 
                           data-field="extensions" data-field-name="${fieldName}" 
                           value="${Array.isArray(fieldConfig.extensions) ? fieldConfig.extensions.join(', ') : ''}" 
                           placeholder="e.g., .png, .jpg, .jpeg">
                </td>
                <td>
                    <input type="text" class="form-control form-control-sm" 
                           data-field="target_extension" data-field-name="${fieldName}" 
                           value="${fieldConfig.target_extension || ''}" 
                           placeholder="e.g., .png">
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm" 
                           data-field="width" data-field-name="${fieldName}" 
                           value="${fieldConfig.width || ''}" 
                           placeholder="0" min="0" step="1">
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm" 
                           data-field="height" data-field-name="${fieldName}" 
                           value="${fieldConfig.height || ''}" 
                           placeholder="0" min="0" step="1">
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" 
                            data-field-name="${fieldName}" 
                            onclick="gameManager.deleteMediaField('${fieldName}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Add event listeners for inline editing
        this.attachMediaFieldsInlineEditing();
    }
    
    attachMediaFieldsInlineEditing() {
        const tbody = document.getElementById('mediaFieldsTableBody');
        if (!tbody) return;
        
        // Event delegation for input changes
        tbody.addEventListener('blur', async (e) => {
            if (e.target.matches('input[data-field]')) {
                await this.saveMediaFieldInline(e.target);
            }
        }, true);
        
        tbody.addEventListener('keypress', async (e) => {
            if (e.target.matches('input[data-field]') && e.key === 'Enter') {
                e.target.blur();
            }
        });
    }
    async saveMediaFieldInline(input) {
        const fieldName = input.dataset.fieldName;
        const fieldType = input.dataset.field;
        const value = input.value.trim();
        
        try {
            let processedValue = value;
            
            // Process different field types
            if (fieldType === 'extensions') {
                processedValue = value ? value.split(',').map(ext => ext.trim()).filter(ext => ext) : [];
            } else if (fieldType === 'width' || fieldType === 'height') {
                // Convert to integer, use 0 if empty or invalid
                processedValue = value ? parseInt(value, 10) || 0 : 0;
            }
            
            const response = await fetch('/api/media-fields', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    field_name: fieldName,
                    field_type: fieldType,
                    value: processedValue
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
            } else {
                this.showAlert(`Failed to update ${fieldName}.${fieldType}: ${data.error}`, 'danger');
                // Reload data to revert changes
                this.loadMediaFieldsData();
            }
        } catch (error) {
            this.showAlert('Error saving changes', 'danger');
            // Reload data to revert changes
            this.loadMediaFieldsData();
        }
    }
    
    async deleteMediaField(fieldName) {
        if (!confirm(`Are you sure you want to delete the media field "${fieldName}"?`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/media-fields', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    field_name: fieldName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Media field "${fieldName}" deleted successfully`, 'success');
                this.loadMediaFieldsData(); // Reload the table
            } else {
                this.showAlert(`Failed to delete media field: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error deleting media field', 'danger');
        }
    }
    
    async addMediaField() {
        const fieldName = prompt('Enter the new media field name:');
        if (!fieldName || !fieldName.trim()) {
            return;
        }
        
        const trimmedFieldName = fieldName.trim();
        
        try {
            const response = await fetch('/api/media-fields', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    field_name: trimmedFieldName,
                    directory: '',
                    extensions: [],
                    target_extension: ''
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Media field "${trimmedFieldName}" added successfully`, 'success');
                this.loadMediaFieldsData(); // Reload the table
            } else {
                this.showAlert(`Failed to add media field: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error adding media field', 'danger');
        }
    }
    
    initializeMediaFieldsModal() {
        // Add media field button
        const addMediaFieldBtn = document.getElementById('addMediaFieldBtn');
        if (addMediaFieldBtn) {
            addMediaFieldBtn.addEventListener('click', () => {
                this.addMediaField();
            });
        }
        
        // Refresh button
        const refreshMediaFieldsBtn = document.getElementById('refreshMediaFieldsBtn');
        if (refreshMediaFieldsBtn) {
            refreshMediaFieldsBtn.addEventListener('click', () => {
                this.loadMediaFieldsData();
            });
        }
    }
    
    openLaunchboxConfigurationModal() {
        // Load launchbox mappings data before opening modal
        this.loadLaunchboxMappingsData();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('launchboxConfigModal'));
        modal.show();
    }
    
    async loadLaunchboxMappingsData() {
        try {
            const response = await fetch('/api/launchbox-mappings');
            const data = await response.json();
            
            if (data.success) {
                this.populateLaunchboxMappingsTable(data.launchbox_mappings, data.media_fields, data.launchbox_media_types);
            } else {
                this.showAlert('Failed to load launchbox mappings data', 'danger');
            }
        } catch (error) {
            this.showAlert('Error loading launchbox mappings data', 'danger');
        }
    }
    
    async populateLaunchboxMappingsTable(launchboxMappings, mediaFields, launchboxMediaTypes) {
        const tbody = document.getElementById('launchboxMappingsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Create rows for each media field
        Object.entries(launchboxMappings).forEach(([mediaField, launchboxTypes]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="media-field-display fw-bold">${mediaField}</span>
                </td>
                <td>
                    <div class="row g-2">
                        <div class="col-5">
                            <label class="form-label small fw-bold">Available Types</label>
                            <select class="form-select form-select-sm" multiple size="4" id="availableTypes_${mediaField}" style="overflow-y: auto; max-height: 120px; min-width: 300px;">
                                ${launchboxMediaTypes.filter(type => !launchboxTypes.includes(type)).map(type => 
                                    `<option value="${type}">${type}</option>`
                        ).join('')}
                    </select>
                        </div>
                        <div class="col-2 d-flex flex-column justify-content-center align-items-center">
                            <button type="button" class="btn btn-outline-primary btn-sm mb-1" onclick="gameManager.addLaunchboxType('${mediaField}')" title="Add selected type">
                                <i class="bi bi-chevron-right"></i>
                    </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="gameManager.removeLaunchboxType('${mediaField}')" title="Remove selected type">
                                <i class="bi bi-chevron-left"></i>
                            </button>
                        </div>
                        <div class="col-5">
                            <label class="form-label small fw-bold">Priority Order (Top = Highest)</label>
                            <div class="border rounded p-2" style="min-height: 100px; max-height: 150px; overflow-y: auto; min-width: 300px;" id="selectedTypes_${mediaField}">
                                ${launchboxTypes.map((type, index) => 
                                    `<div class="selected-type-item border rounded p-1 mb-1 d-flex justify-content-between align-items-center" data-type="${type}" style="cursor: move;">
                                        <span class="small">${type}</span>
                                        <button type="button" class="btn btn-outline-danger btn-sm" onclick="gameManager.removeSpecificLaunchboxType('${mediaField}', '${type}')" title="Remove">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                    <small class="text-muted">Drag items to reorder priority. First item has highest priority.</small>
                </td>
            `;
            tbody.appendChild(row);
            
            // Initialize drag and drop for this row
            this.initializeDragAndDrop(mediaField);
        });
    }
    
    async updateLaunchboxMapping(mediaField) {
        try {
            // Get selected types from the priority list
            const selectedTypesContainer = document.getElementById(`selectedTypes_${mediaField}`);
            const selectedTypes = Array.from(selectedTypesContainer.querySelectorAll('.selected-type-item'))
                .map(item => item.getAttribute('data-type'));
            
            const response = await fetch('/api/launchbox-mappings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    media_field: mediaField,
                    launchbox_types: selectedTypes
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Mapping updated: ${mediaField} → [${selectedTypes.join(', ')}]`, 'success');
            } else {
                this.showAlert(`Failed to update mapping: ${data.error}`, 'danger');
                // Reload data to revert changes
                this.loadLaunchboxMappingsData();
            }
        } catch (error) {
            this.showAlert('Error updating mapping', 'danger');
            // Reload data to revert changes
            this.loadLaunchboxMappingsData();
        }
    }
    
    addLaunchboxType(mediaField) {
        const availableSelect = document.getElementById(`availableTypes_${mediaField}`);
        const selectedTypesContainer = document.getElementById(`selectedTypes_${mediaField}`);
        
        const selectedOptions = Array.from(availableSelect.selectedOptions);
        
        selectedOptions.forEach(option => {
            const type = option.value;
            
            // Add to selected types container
            const typeItem = document.createElement('div');
            typeItem.className = 'selected-type-item border rounded p-1 mb-1 d-flex justify-content-between align-items-center';
            typeItem.setAttribute('data-type', type);
            typeItem.style.cursor = 'move';
            typeItem.innerHTML = `
                <span class="small">${type}</span>
                <button type="button" class="btn btn-outline-danger btn-sm" onclick="gameManager.removeSpecificLaunchboxType('${mediaField}', '${type}')" title="Remove">
                    <i class="bi bi-x"></i>
                </button>
            `;
            selectedTypesContainer.appendChild(typeItem);
            
            // Remove from available select
            option.remove();
        });
        
        // Re-initialize drag and drop
        this.initializeDragAndDrop(mediaField);
        
        // Update the mapping
        this.updateLaunchboxMapping(mediaField);
    }
    
    removeLaunchboxType(mediaField) {
        const selectedTypesContainer = document.getElementById(`selectedTypes_${mediaField}`);
        const availableSelect = document.getElementById(`availableTypes_${mediaField}`);
        
        // Find items with focused remove buttons (more compatible approach)
        const selectedItems = Array.from(selectedTypesContainer.querySelectorAll('.selected-type-item'))
            .filter(item => {
                const btn = item.querySelector('.btn');
                return btn && btn === document.activeElement;
            });
        
        selectedItems.forEach(item => {
            const type = item.getAttribute('data-type');
            
            // Add back to available select
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            availableSelect.appendChild(option);
            
            // Remove from selected types
            item.remove();
        });
        
        // Sort the available options alphabetically
        if (selectedItems.length > 0) {
            const options = Array.from(availableSelect.options);
            options.sort((a, b) => a.textContent.localeCompare(b.textContent));
            availableSelect.innerHTML = '';
            options.forEach(opt => availableSelect.appendChild(opt));
        }
        
        // Update the mapping
        this.updateLaunchboxMapping(mediaField);
    }
    
    removeSpecificLaunchboxType(mediaField, type) {
        const selectedTypesContainer = document.getElementById(`selectedTypes_${mediaField}`);
        const availableSelect = document.getElementById(`availableTypes_${mediaField}`);
        
        // Find and remove the specific item
        const item = selectedTypesContainer.querySelector(`[data-type="${type}"]`);
        if (item) {
            // Add back to available select
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            availableSelect.appendChild(option);
            
            // Sort the available options alphabetically
            const options = Array.from(availableSelect.options);
            options.sort((a, b) => a.textContent.localeCompare(b.textContent));
            availableSelect.innerHTML = '';
            options.forEach(opt => availableSelect.appendChild(opt));
            
            // Remove from selected types
            item.remove();
            
            // Update the mapping
            this.updateLaunchboxMapping(mediaField);
            
        }
    }
    
    initializeDragAndDrop(mediaField, scraperType = 'launchbox') {
        const selectedTypesContainer = document.getElementById(scraperType === 'screenscraper' ? `screenscraper_selectedTypes_${mediaField}` : `selectedTypes_${mediaField}`);
        if (!selectedTypesContainer) return;
        
        // Remove existing event listeners
        selectedTypesContainer.removeEventListener('dragover', this.handleDragOver);
        selectedTypesContainer.removeEventListener('dragleave', this.handleDragLeave);
        selectedTypesContainer.removeEventListener('drop', this.handleDrop);
        
        // Add new event listeners
        selectedTypesContainer.addEventListener('dragover', (e) => this.handleDragOver(e, mediaField));
        selectedTypesContainer.addEventListener('dragleave', (e) => this.handleDragLeave(e, mediaField));
        selectedTypesContainer.addEventListener('drop', (e) => this.handleDrop(e, mediaField, scraperType));
        
        // Make items draggable
        const items = selectedTypesContainer.querySelectorAll('.selected-type-item');
        items.forEach(item => {
            item.draggable = true;
            item.addEventListener('dragstart', (e) => this.handleDragStart(e, mediaField));
            item.addEventListener('dragend', (e) => {
                e.target.classList.remove('dragging');
                e.target.style.opacity = '1';
            });
        });
    }
    
    handleDragStart(e, mediaField) {
        e.dataTransfer.setData('text/plain', e.target.getAttribute('data-type'));
        e.target.classList.add('dragging');
        e.target.style.opacity = '0.5';
    }
    
    handleDragOver(e, mediaField) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const container = e.target.closest('#selectedTypes_' + mediaField) || e.target.closest('#screenscraper_selectedTypes_' + mediaField);
        if (container) {
            container.classList.add('drag-active');
        }
    }
    
    handleDragLeave(e, mediaField) {
        const container = e.target.closest('#selectedTypes_' + mediaField) || e.target.closest('#screenscraper_selectedTypes_' + mediaField);
        if (container && !container.contains(e.relatedTarget)) {
            container.classList.remove('drag-active');
        }
    }
    
    handleDrop(e, mediaField, scraperType = 'launchbox') {
        e.preventDefault();
        const draggedType = e.dataTransfer.getData('text/plain');
        const container = e.target.closest('#selectedTypes_' + mediaField) || e.target.closest('#screenscraper_selectedTypes_' + mediaField);
        
        if (container) {
            container.classList.remove('drag-active');
            
            const draggedElement = container.querySelector(`[data-type="${draggedType}"]`);
            
            if (draggedElement) {
                draggedElement.classList.remove('dragging');
                draggedElement.style.opacity = '1';
                
                // Find the drop target
                const afterElement = this.getDragAfterElement(container, e.clientY);
                
                if (afterElement == null) {
                    container.appendChild(draggedElement);
            } else {
                    container.insertBefore(draggedElement, afterElement);
                }
                
                // Update the mapping based on scraper type
                if (scraperType === 'screenscraper') {
                    this.saveScreenscraperMapping(mediaField);
                } else {
                    this.updateLaunchboxMapping(mediaField);
                }
            }
        }
    }
    
    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.selected-type-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    initializeLaunchboxConfigModal() {
        // Refresh mappings button
        const refreshLaunchboxMappingsBtn = document.getElementById('refreshLaunchboxMappingsBtn');
        if (refreshLaunchboxMappingsBtn) {
            refreshLaunchboxMappingsBtn.addEventListener('click', () => {
                this.loadLaunchboxMappingsData();
            });
        }
        
        // Refresh media types button
        const refreshLaunchboxMediaTypesBtn = document.getElementById('refreshLaunchboxMediaTypesBtn');
        if (refreshLaunchboxMediaTypesBtn) {
            refreshLaunchboxMediaTypesBtn.addEventListener('click', () => {
                this.refreshLaunchboxMediaTypes();
            });
        }
    }
    
    async refreshLaunchboxMediaTypes() {
        try {
            // Show loading state
            const btn = document.getElementById('refreshLaunchboxMediaTypesBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Refreshing...';
            btn.disabled = true;
            
            const response = await fetch('/api/launchbox-refresh-media-types', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(data.message, 'success');
                // Reload the mappings data to get updated media types
                this.loadLaunchboxMappingsData();
            } else {
                this.showAlert(`Failed to refresh media types: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error refreshing media types', 'danger');
        } finally {
            // Restore button state
            const btn = document.getElementById('refreshLaunchboxMediaTypesBtn');
            btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh Media Types';
            btn.disabled = false;
        }
    }
    
    openIgdbConfigurationModal() {
        // Load IGDB mappings data before opening modal
        this.loadIgdbMappingsData();
        
        // Load IGDB credentials
        this.loadIgdbCredentialsStatus();
        this.loadIgdbCredentialsValues();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('igdbConfigModal'));
        modal.show();
    }
    
    async loadIgdbMappingsData() {
        try {
            const response = await fetch('/api/igdb-mappings');
            const data = await response.json();
            
            if (data.success) {
                this.populateIgdbMappingsTable(data.igdb_mappings, data.media_fields, data.igdb_media_types);
            } else {
                this.showAlert('Failed to load IGDB mappings data', 'danger');
            }
            
            // Load IGDB credentials values
            await this.loadIgdbCredentialsValues();
        } catch (error) {
            this.showAlert('Error loading IGDB mappings data', 'danger');
        }
    }
    
    async populateIgdbMappingsTable(igdbMappings, mediaFields, igdbMediaTypes) {
        const tbody = document.getElementById('igdbMappingsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Create rows for all media fields, not just the ones that are mapped
        Object.keys(mediaFields).forEach(mediaField => {
            // Find which IGDB type maps to this media field
            // igdbMappings structure: { "boxart": "cover", "image": "screenshots", ... }
            const igdbType = igdbMappings[mediaField] || '';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="media-field-display">${mediaField}</span>
                </td>
                <td>
                    <select class="form-select form-select-sm" 
                            data-media-field="${mediaField}" 
                            onchange="gameManager.updateIgdbMapping(this.value, '${mediaField}')">
                        <option value="">-- Select IGDB Image Type --</option>
                        ${igdbMediaTypes.map(type => 
                            `<option value="${type}" ${type === igdbType ? 'selected' : ''}>${type}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    async updateIgdbMapping(igdbType, mediaField) {
        try {
            const response = await fetch('/api/igdb-mappings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    igdb_type: igdbType,
                    media_field: mediaField
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`IGDB mapping updated: ${mediaField} ← ${igdbType}`, 'success');
            } else {
                this.showAlert(`Failed to update IGDB mapping: ${data.error}`, 'danger');
                // Reload data to revert changes
                this.loadIgdbMappingsData();
            }
        } catch (error) {
            this.showAlert('Error updating IGDB mapping', 'danger');
            // Reload data to revert changes
            this.loadIgdbMappingsData();
        }
    }

    openScreenscraperConfigurationModal() {
        // Load ScreenScraper mappings data before opening modal
        this.loadScreenscraperMappingsData();
        
        // Load ScreenScraper credentials
        this.loadScreenscraperCredentialsStatus();
        this.loadScreenscraperCredentialsValues();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('screenscraperConfigModal'));
        modal.show();
    }
    
    async loadScreenscraperMappingsData() {
        try {
            const response = await fetch('/api/screenscraper-mappings');
            const data = await response.json();
            
            if (data.success) {
                this.populateScreenscraperMappingsTable(data.screenscraper_mappings, data.media_fields, data.screenscraper_media_types);
            } else {
                this.showAlert('Failed to load ScreenScraper mappings data', 'danger');
            }
        } catch (error) {
            this.showAlert('Error loading ScreenScraper mappings data', 'danger');
        }
    }
    
    async populateScreenscraperMappingsTable(screenscraperMappings, mediaFields, screenscraperMediaTypes) {
        const tbody = document.getElementById('screenscraperMappingsTableBody');
        if (!tbody) return;
        
        // Debug: Log the structure of screenscraperMediaTypes
        console.log('🔧 DEBUG: screenscraperMediaTypes structure:', screenscraperMediaTypes);
        console.log('🔧 DEBUG: First few items:', screenscraperMediaTypes.slice(0, 3));
        console.log('🔧 DEBUG: Type of first item:', typeof screenscraperMediaTypes[0]);
        console.log('🔧 DEBUG: Is array?', Array.isArray(screenscraperMediaTypes[0]));
        
        tbody.innerHTML = '';
        
        // Check if no media types are available
        if (!screenscraperMediaTypes || screenscraperMediaTypes.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="2" class="text-center text-muted py-4">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>No ScreenScraper media types available</strong><br>
                    <small>Please configure ScreenScraper credentials in the settings to load media types from the API.</small>
                </td>
            `;
            tbody.appendChild(row);
            return;
        }
        
        // Create rows for each media field
        Object.entries(screenscraperMappings).forEach(([mediaField, screenscraperTypes]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="media-field-display fw-bold">${mediaField}</span>
                </td>
                <td>
                    <div class="row g-2">
                        <div class="col-5">
                            <label class="form-label small fw-bold">Available Types</label>
                            <select class="form-select form-select-sm" multiple size="4" id="screenscraper_availableTypes_${mediaField}" style="overflow-y: auto; max-height: 120px; min-width: 300px;">
                                ${screenscraperMediaTypes.filter(([shortName, fullName]) => !screenscraperTypes.includes(shortName)).map(([shortName, fullName]) => 
                                    `<option value="${shortName}">${fullName}</option>`
                                ).join('')}
                    </select>
                        </div>
                        <div class="col-2 d-flex flex-column justify-content-center align-items-center">
                            <button type="button" class="btn btn-outline-primary btn-sm mb-1" onclick="gameManager.addScreenscraperType('${mediaField}')" title="Add selected type">
                                <i class="bi bi-chevron-right"></i>
                    </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="gameManager.removeScreenscraperType('${mediaField}')" title="Remove selected type">
                                <i class="bi bi-chevron-left"></i>
                            </button>
                        </div>
                        <div class="col-5">
                            <label class="form-label small fw-bold">Priority Order (Top = Highest)</label>
                            <div class="border rounded p-2" style="min-height: 100px; max-height: 150px; overflow-y: auto; min-width: 300px;" id="screenscraper_selectedTypes_${mediaField}">
                                ${screenscraperTypes.map((type, index) => {
                                    // Find the full name for this short name
                                    const mediaTypeInfo = screenscraperMediaTypes.find(([shortName, fullName]) => shortName === type);
                                    const displayName = mediaTypeInfo ? mediaTypeInfo[1] : type;
                                    return `<div class="selected-type-item border rounded p-1 mb-1 d-flex justify-content-between align-items-center" data-type="${type}" style="cursor: move;">
                                        <span class="small">${displayName}</span>
                                        <button type="button" class="btn btn-outline-danger btn-sm" onclick="gameManager.removeSpecificScreenscraperType('${mediaField}', '${type}')" title="Remove">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>`;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                    <small class="text-muted">Drag items to reorder priority. First item has highest priority.</small>
                </td>
            `;
            tbody.appendChild(row);
            
            // Initialize drag and drop for this row
            this.initializeDragAndDrop(mediaField, 'screenscraper');
        });
    }
    
    async updateScreenscraperMapping(screenscraperType, mediaField) {
        try {
            const response = await fetch('/api/screenscraper-mappings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    screenscraper_type: screenscraperType,
                    media_field: mediaField
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`ScreenScraper mapping updated: ${screenscraperType} → ${mediaField}`, 'success');
            } else {
                this.showAlert(`Failed to update ScreenScraper mapping: ${data.error}`, 'danger');
                // Reload data to revert changes
                this.loadScreenscraperMappingsData();
            }
        } catch (error) {
            this.showAlert('Error updating ScreenScraper mapping', 'danger');
            // Reload data to revert changes
            this.loadScreenscraperMappingsData();
        }
    }
    
    async resetScreenscraperMapping(screenscraperType) {
        if (!confirm(`Reset ScreenScraper mapping for "${screenscraperType}" to default?`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/screenscraper-mappings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    screenscraper_type: screenscraperType,
                    reset: true
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`ScreenScraper mapping reset for "${screenscraperType}"`, 'success');
                this.loadScreenscraperMappingsData(); // Reload the table
            } else {
                this.showAlert(`Failed to reset ScreenScraper mapping: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error resetting ScreenScraper mapping', 'danger');
        }
    }
    
    // ScreenScraper type management functions
    addScreenscraperType(mediaField) {
        const availableSelect = document.getElementById(`screenscraper_availableTypes_${mediaField}`);
        const selectedTypesContainer = document.getElementById(`screenscraper_selectedTypes_${mediaField}`);
        
        if (!availableSelect || !selectedTypesContainer) return;
        
        const selectedOptions = Array.from(availableSelect.selectedOptions);
        if (selectedOptions.length === 0) return;
        
        selectedOptions.forEach(option => {
            const type = option.value;
            const displayName = option.textContent; // This is the full name
            
            // Add to selected types container
            const typeDiv = document.createElement('div');
            typeDiv.className = 'selected-type-item border rounded p-1 mb-1 d-flex justify-content-between align-items-center';
            typeDiv.setAttribute('data-type', type);
            typeDiv.style.cursor = 'move';
            typeDiv.innerHTML = `
                <span class="small">${displayName}</span>
                <button type="button" class="btn btn-outline-danger btn-sm" onclick="gameManager.removeSpecificScreenscraperType('${mediaField}', '${type}')" title="Remove">
                    <i class="bi bi-x"></i>
                </button>
            `;
            selectedTypesContainer.appendChild(typeDiv);
            
            // Remove from available select
            option.remove();
        });
        
        // Re-initialize drag and drop
        this.initializeDragAndDrop(mediaField, 'screenscraper');
        
        // Save the updated mapping
        this.saveScreenscraperMapping(mediaField);
    }
    
    removeScreenscraperType(mediaField) {
        const selectedTypesContainer = document.getElementById(`screenscraper_selectedTypes_${mediaField}`);
        const availableSelect = document.getElementById(`screenscraper_availableTypes_${mediaField}`);
        
        if (!selectedTypesContainer || !availableSelect) return;
        
        // Find selected items (using document.activeElement for compatibility)
        const selectedItems = Array.from(selectedTypesContainer.children).filter(item => 
            item.classList.contains('selected-type-item')
        );
        
        if (selectedItems.length === 0) return;
        
        selectedItems.forEach(item => {
            const type = item.getAttribute('data-type');
            
            // Add back to available select
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            availableSelect.appendChild(option);
            
            // Remove from selected container
            item.remove();
        });
        
        // Sort the available options alphabetically
        const options = Array.from(availableSelect.options);
        options.sort((a, b) => a.textContent.localeCompare(b.textContent));
        availableSelect.innerHTML = '';
        options.forEach(opt => availableSelect.appendChild(opt));
        
        // Re-initialize drag and drop
        this.initializeDragAndDrop(mediaField, 'screenscraper');
        
        // Save the updated mapping
        this.saveScreenscraperMapping(mediaField);
    }
    
    removeSpecificScreenscraperType(mediaField, type) {
        const selectedTypesContainer = document.getElementById(`screenscraper_selectedTypes_${mediaField}`);
        const availableSelect = document.getElementById(`screenscraper_availableTypes_${mediaField}`);
        
        if (!selectedTypesContainer || !availableSelect) return;
        
        // Find and remove the specific type from selected container
        const typeItem = selectedTypesContainer.querySelector(`[data-type="${type}"]`);
        if (typeItem) {
            typeItem.remove();
        }
        
        // Add back to available select
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        availableSelect.appendChild(option);
        
        // Sort the available options alphabetically
        const options = Array.from(availableSelect.options);
        options.sort((a, b) => a.textContent.localeCompare(b.textContent));
        availableSelect.innerHTML = '';
        options.forEach(opt => availableSelect.appendChild(opt));
        
        // Re-initialize drag and drop
        this.initializeDragAndDrop(mediaField, 'screenscraper');
        
        // Save the updated mapping
        this.saveScreenscraperMapping(mediaField);
    }
    
    async saveScreenscraperMapping(mediaField) {
        const selectedTypesContainer = document.getElementById(`screenscraper_selectedTypes_${mediaField}`);
        if (!selectedTypesContainer) return;
        
        // Get all selected types in order
        const selectedTypes = Array.from(selectedTypesContainer.children)
            .filter(item => item.classList.contains('selected-type-item'))
            .map(item => item.getAttribute('data-type'));
        
        try {
            // Update the mapping via API
            const response = await fetch('/api/screenscraper-mappings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    media_field: mediaField,
                    screenscraper_types: selectedTypes
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
            } else {
                this.showAlert(`Failed to update ScreenScraper mapping: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error updating ScreenScraper mapping', 'danger');
        }
    }
    
    openSteamgriddbConfigurationModal() {
        // Load SteamGridDB mappings data before opening modal
        this.loadSteamgriddbMappingsData();
        
        // Load SteamGridDB credentials
        this.loadSteamgriddbCredentialsStatus();
        this.loadSteamgriddbCredentialsValues();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('steamgriddbConfigModal'));
        modal.show();
    }
    
    openSteamConfigurationModal() {
        // Load Steam mappings data before opening modal
        this.loadSteamMappingsData();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('steamConfigModal'));
        modal.show();
    }
    
    async loadSteamgriddbMappingsData() {
        try {
            const response = await fetch('/api/steamgriddb-mappings');
            const data = await response.json();
            
            if (data.success) {
                this.populateSteamgriddbMappingsTable(data.steamgriddb_mappings, data.media_fields, data.steamgriddb_media_types);
            } else {
                this.showAlert('Failed to load SteamGridDB mappings data', 'danger');
            }
        } catch (error) {
            this.showAlert('Error loading SteamGridDB mappings data', 'danger');
        }
    }
    
    async populateSteamgriddbMappingsTable(steamgriddbMappings, mediaFields, steamgriddbMediaTypes) {
        const tbody = document.getElementById('steamgriddbMappingsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Create rows for all media fields, not just the ones that are mapped
        Object.keys(mediaFields).forEach(mediaField => {
            // Find which SteamGridDB type maps to this media field
            // steamgriddbMappings structure: { "boxart": "grids", "marquee": "logos", ... }
            const steamgriddbType = steamgriddbMappings[mediaField] || '';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="media-field-display">${mediaField}</span>
                </td>
                <td>
                    <select class="form-select form-select-sm" 
                            data-media-field="${mediaField}" 
                            onchange="gameManager.updateSteamgriddbMapping(this.value, '${mediaField}')">
                        <option value="">-- Select SteamGridDB Image Type --</option>
                        ${steamgriddbMediaTypes.map(type => 
                            `<option value="${type}" ${type === steamgriddbType ? 'selected' : ''}>${type}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    async updateSteamgriddbMapping(steamgriddbType, mediaField) {
        try {
            const response = await fetch('/api/steamgriddb-mappings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    steamgriddb_type: steamgriddbType,
                    media_field: mediaField
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`SteamGridDB mapping updated: ${mediaField} ← ${steamgriddbType}`, 'success');
            } else {
                this.showAlert(`Failed to update SteamGridDB mapping: ${data.error}`, 'danger');
                // Reload data to revert changes
                this.loadSteamgriddbMappingsData();
            }
        } catch (error) {
            this.showAlert('Error updating SteamGridDB mapping', 'danger');
            // Reload data to revert changes
            this.loadSteamgriddbMappingsData();
        }
    }

    async loadSteamgriddbCredentialsStatus() {
        try {
            const response = await fetch('/api/steamgriddb-credentials');
            const data = await response.json();
            
            if (data.success) {
                const statusElement = document.getElementById('steamgriddbCredentialsStatus');
                if (statusElement) {
                    if (data.has_credentials) {
                        statusElement.innerHTML = `<span class="badge bg-success">API Key Configured (${data.api_key_length} chars)</span>`;
                    } else {
                        statusElement.innerHTML = '<span class="badge bg-warning">No API Key</span>';
                    }
                }
            }
        } catch (error) {
        }
    }
    
    async loadSteamgriddbCredentialsValues() {
        try {
            const response = await fetch('/api/steamgriddb-credentials');
            const data = await response.json();
            
            if (data.success) {
                const apiKeyInput = document.getElementById('steamgriddbApiKey');
                const helpText = document.getElementById('steamgriddbApiKeyHelp');
                
                if (apiKeyInput) {
                    if (data.has_credentials) {
                        // Fill with dots to show that credentials exist
                        const dots = '•'.repeat(Math.min(data.api_key_length, 20)); // Max 20 dots for display
                        apiKeyInput.value = dots;
                        apiKeyInput.placeholder = `API Key configured (${data.api_key_length} characters)`;
                        
                        // Show help text
                        if (helpText) {
                            helpText.style.display = 'block';
                        }
                    } else {
                        apiKeyInput.value = '';
                        apiKeyInput.placeholder = 'Enter your SteamGridDB API key';
                        
                        // Hide help text
                        if (helpText) {
                            helpText.style.display = 'none';
                        }
                    }
                }
            }
        } catch (error) {
        }
    }
    
    async saveSteamgriddbCredentials() {
        const apiKeyInput = document.getElementById('steamgriddbApiKey');
        if (!apiKeyInput) {
            this.showAlert('API key input not found', 'danger');
            return;
        }
        
        let apiKey = apiKeyInput.value.trim();
        
        // If the field contains only dots, it means the user hasn't entered a new key
        if (apiKey && apiKey.match(/^•+$/)) {
            this.showAlert('Please enter a new API key to update credentials', 'info');
            return;
        }
        
        if (!apiKey) {
            this.showAlert('Please enter an API key', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/steamgriddb-credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_key: apiKey
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('SteamGridDB credentials saved successfully', 'success');
                // Reload status and values to show dots
                this.loadSteamgriddbCredentialsStatus();
                this.loadSteamgriddbCredentialsValues();
            } else {
                this.showAlert(`Failed to save SteamGridDB credentials: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error saving SteamGridDB credentials', 'danger');
        }
    }
    
    initializeIgdbConfigModal() {
        // Refresh button
        const refreshIgdbMappingsBtn = document.getElementById('refreshIgdbMappingsBtn');
        if (refreshIgdbMappingsBtn) {
            refreshIgdbMappingsBtn.addEventListener('click', () => {
                this.loadIgdbMappingsData();
            });
        }
        
        // IGDB credentials save button
        const saveIgdbCredentialsBtn = document.getElementById('saveIgdbCredentialsBtn');
        if (saveIgdbCredentialsBtn) {
            saveIgdbCredentialsBtn.addEventListener('click', () => {
                this.saveIgdbCredentials();
            });
        }
    }
    
    initializeScreenscraperConfigModal() {
        // Refresh button
        const refreshScreenscraperMappingsBtn = document.getElementById('refreshScreenscraperMappingsBtn');
        if (refreshScreenscraperMappingsBtn) {
            refreshScreenscraperMappingsBtn.addEventListener('click', () => {
                this.loadScreenscraperMappingsData();
            });
        }
        
        // ScreenScraper credentials save button
        const saveScreenscraperCredentialsBtn = document.getElementById('saveScreenscraperCredentialsBtn');
        if (saveScreenscraperCredentialsBtn) {
            saveScreenscraperCredentialsBtn.addEventListener('click', () => {
                this.saveScreenscraperCredentials();
            });
        }
    }
    
    initializeMobygamesConfigModal() {
        // Refresh mappings button
        const refreshMobygamesMappingsBtn = document.getElementById('refreshMobygamesMappingsBtn');
        if (refreshMobygamesMappingsBtn) {
            refreshMobygamesMappingsBtn.addEventListener('click', () => {
                this.loadMobygamesMappingsData();
            });
        }
        
        // Load initial data
        this.loadMobygamesMappingsData();
    }
    
    async loadMobygamesMappingsData() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            if (config.mobygames && config.mobygames.mapping) {
                this.populateMobygamesMappingsTable(config.mobygames.mapping);
            } else {
                this.showAlert('Failed to load MobyGames mappings data', 'danger');
            }
        } catch (error) {
            this.showAlert('Error loading MobyGames mappings data', 'danger');
        }
    }
    
    populateMobygamesMappingsTable(mobygamesMappings) {
        const tbody = document.getElementById('mobygamesMappingsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Get available gamelist fields for the combobox
        const availableGamelistFields = [
            'name', 'desc', 'developer', 'publisher', 'genre', 'rating', 
            'releasedate', 'players', 'youtubeurl', 'nbvotes'
        ];
        
        // Create rows for each mapping
        Object.entries(mobygamesMappings).forEach(([mobygamesField, gamelistField]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="mobygames-field-display fw-bold">${mobygamesField}</span>
                </td>
                <td>
                    <select class="form-select form-select-sm" onchange="gameManager.updateMobygamesMapping('${mobygamesField}', this.value)">
                        <option value="">-- Select Gamelist Field --</option>
                        ${availableGamelistFields.map(field => 
                            `<option value="${field}" ${field === gamelistField ? 'selected' : ''}>${field}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    async updateMobygamesMapping(mobygamesField, gamelistField) {
        try {
            const response = await fetch('/api/config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: `mobygames.mapping.${mobygamesField}`,
                    value: gamelistField
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showAlert('MobyGames mapping updated successfully', 'success');
            } else {
                this.showAlert('Failed to update MobyGames mapping', 'danger');
            }
        } catch (error) {
            console.error('Error updating MobyGames mapping:', error);
            this.showAlert('Error updating MobyGames mapping', 'danger');
        }
    }
    
    
    async loadDatscrapperMappingsData() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            if (config.datscrapper && config.datscrapper.mapping) {
                this.populateDatscrapperMappingsTable(config.datscrapper.mapping);
            } else {
                this.showAlert('Failed to load DAT Scrapper mappings data', 'danger');
            }
        } catch (error) {
            this.showAlert('Error loading DAT Scrapper mappings data', 'danger');
        }
    }
    
    populateDatscrapperMappingsTable(datscrapperMappings) {
        const tbody = document.getElementById('datscrapperMappingsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Get available gamelist fields for the combobox
        const availableGamelistFields = [
            'name', 'desc', 'developer', 'publisher', 'genre', 'rating', 
            'releasedate', 'players', 'youtubeurl', 'nbvotes'
        ];
        
        // Create rows for each mapping
        Object.entries(datscrapperMappings).forEach(([datField, gamelistField]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="datscrapper-field-display fw-bold">${datField}</span>
                </td>
                <td>
                    <select class="form-select form-select-sm datscrapper-field-mapping" data-dat-field="${datField}">
                        <option value="">Select gamelist field...</option>
                        ${availableGamelistFields.map(field => 
                            `<option value="${field}" ${field === gamelistField ? 'selected' : ''}>${field}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Add event listeners for field mapping changes
        tbody.querySelectorAll('.datscrapper-field-mapping').forEach(select => {
            select.addEventListener('change', (e) => {
                const datField = e.target.dataset.datField;
                const gamelistField = e.target.value;
                
                // Save the mapping
                this.saveDatscrapperFieldMapping(datField, gamelistField);
            });
        });
    }
    
    async saveDatscrapperFieldMapping(datField, gamelistField) {
        try {
            const response = await fetch('/api/config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    'datscrapper.mapping': {
                        [datField]: gamelistField
                    }
                })
            });
            
            if (response.ok) {
                this.showAlert(`DAT Scrapper mapping saved: ${datField} → ${gamelistField}`, 'success');
            } else {
                this.showAlert('Failed to save DAT Scrapper mapping', 'danger');
            }
        } catch (error) {
            console.error('Error updating DAT Scrapper mapping:', error);
            this.showAlert('Error updating DAT Scrapper mapping', 'danger');
        }
    }
    
    initializeDatscrapperConfigModal() {
        // Refresh mappings button
        const refreshDatscrapperMappingsBtn = document.getElementById('refreshDatscrapperMappingsBtn');
        if (refreshDatscrapperMappingsBtn) {
            refreshDatscrapperMappingsBtn.addEventListener('click', () => {
                this.loadDatscrapperMappingsData();
            });
        }
        
        // Load initial data
        this.loadDatscrapperMappingsData();
    }
    
    initializeSteamgriddbConfigModal() {
        // Refresh button
        const refreshSteamgriddbMappingsBtn = document.getElementById('refreshSteamgriddbMappingsBtn');
        if (refreshSteamgriddbMappingsBtn) {
            refreshSteamgriddbMappingsBtn.addEventListener('click', () => {
                this.loadSteamgriddbMappingsData();
            });
        }
        
        // SteamGridDB credentials save button
        const saveSteamgriddbCredentialsBtn = document.getElementById('saveSteamgriddbCredentialsBtn');
        if (saveSteamgriddbCredentialsBtn) {
            saveSteamgriddbCredentialsBtn.addEventListener('click', () => {
                this.saveSteamgriddbCredentials();
            });
        }
        
        // Clear dots when user focuses on API key input
        const steamgriddbApiKeyInput = document.getElementById('steamgriddbApiKey');
        if (steamgriddbApiKeyInput) {
            steamgriddbApiKeyInput.addEventListener('focus', () => {
                if (steamgriddbApiKeyInput.value && steamgriddbApiKeyInput.value.match(/^•+$/)) {
                    steamgriddbApiKeyInput.value = '';
                }
            });
        }
    }
    
    initializeSteamConfigModal() {
        // Refresh button
        const refreshSteamMappingsBtn = document.getElementById('refreshSteamMappingsBtn');
        if (refreshSteamMappingsBtn) {
            refreshSteamMappingsBtn.addEventListener('click', () => {
                this.loadSteamMappingsData();
            });
        }

        // 2D Box Generator Configuration event listeners
        const open2DBoxGeneratorConfigBtn = document.getElementById('open2DBoxGeneratorConfigModal');
        if (open2DBoxGeneratorConfigBtn) {
            open2DBoxGeneratorConfigBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.open2DBoxGeneratorConfigModal();
            });
        }

        const saveBoxGeneratorConfigBtn = document.getElementById('saveBoxGeneratorConfigBtn');
        if (saveBoxGeneratorConfigBtn) {
            saveBoxGeneratorConfigBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.save2DBoxGeneratorConfig();
            });
        }

        const refreshBoxGeneratorConfigBtn = document.getElementById('refreshBoxGeneratorConfigBtn');
        if (refreshBoxGeneratorConfigBtn) {
            refreshBoxGeneratorConfigBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.load2DBoxGeneratorConfig();
            });
        }
    }
    
    async loadSteamMappingsData() {
        try {
            const response = await fetch('/api/steam-mappings');
            if (response.ok) {
                const data = await response.json();
                this.populateSteamMappingsTable(data.steam_mappings, data.media_fields, data.steam_media_types);
            } else {
            }
        } catch (error) {
        }
    }
    
    populateSteamMappingsTable(steamMappings, mediaFields, steamMediaTypes) {
        const tbody = document.getElementById('steamMappingsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Create rows for all media fields, not just the ones that are mapped
        Object.keys(mediaFields).forEach(mediaField => {
            // Find which Steam type maps to this media field
            // steamMappings structure: { "boxart": "capsule", "marquee": "logo", ... }
            const steamType = steamMappings[mediaField] || '';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="media-field-display">${mediaField}</span>
                </td>
                <td>
                    <select class="form-select form-select-sm" 
                            data-media-field="${mediaField}" 
                            onchange="gameManager.updateSteamMapping(this.value, '${mediaField}')">
                        <option value="">-- Select Steam Image Type --</option>
                        ${steamMediaTypes.map(type => 
                            `<option value="${type}" ${type === steamType ? 'selected' : ''}>${type}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    async updateSteamMapping(steamType, mediaField) {
        try {
            const response = await fetch('/api/steam-mappings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    steam_type: steamType,
                    media_field: mediaField
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert(`Steam mapping updated: ${mediaField} ← ${steamType}`, 'success');
                } else {
                    this.showAlert(`Failed to update Steam mapping: ${result.error}`, 'danger');
                }
            } else {
                this.showAlert('Failed to update Steam mapping', 'danger');
            }
        } catch (error) {
            this.showAlert('Error updating Steam mapping', 'danger');
        }
    }

    initializeAppConfigurationModal() {
        
        // Add event listener for opening the modal
        const openAppConfigBtn = document.getElementById('openAppConfigModal');
        if (openAppConfigBtn) {
            openAppConfigBtn.addEventListener('click', () => {
                this.openAppConfigurationModal();
            });
        }
        
        // Add event listener for saving configuration
        const saveAppConfigBtn = document.getElementById('saveAppConfigBtn');
        if (saveAppConfigBtn) {
            saveAppConfigBtn.addEventListener('click', () => {
                this.saveAppConfiguration();
            });
        }
        
    }
    
    openAppConfigurationModal() {
        
        // Load current configuration
        this.loadAppConfiguration();
        
        const modal = new bootstrap.Modal(document.getElementById('appConfigurationModal'));
        modal.show();
    }
    
    async loadAppConfiguration() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                const config = await response.json();
                
                // Populate form fields
                document.getElementById('romsRootDirectory').value = config.roms_root_directory || '';
                document.getElementById('serverHost').value = config.server?.host || '0.0.0.0';
                document.getElementById('serverPort').value = config.server?.port || 5000;
                document.getElementById('serverDebug').checked = config.server?.debug || false;
                
                document.getElementById('maxTasksToKeep').value = config.max_tasks_to_keep || 30;
                
                // Authentication settings
                document.getElementById('disableLocalAuth').checked = config.authentication?.disable_local_auth || false;
                
            } else {
            }
            
            // Load Discord credentials separately
            await this.loadDiscordCredentials();
        } catch (error) {
        }
    }
    
    async loadDatscrapperConfig() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                const config = await response.json();
                return config.scrappers?.datscrapper || {};
            }
        } catch (error) {
            console.error('Error loading DAT Scrapper configuration:', error);
        }
        return {};
    }
    
    async loadDiscordCredentials() {
        try {
            const response = await fetch('/api/discord-credentials');
            if (response.ok) {
                const discordConfig = await response.json();
                
                // Populate Discord form fields
                document.getElementById('discordClientId').value = discordConfig.client_id || '';
                document.getElementById('discordClientSecret').value = discordConfig.client_secret || '';
                document.getElementById('discordRedirectUri').value = discordConfig.redirect_uri || '';
                document.getElementById('discordBotToken').value = discordConfig.bot_token || '';
                document.getElementById('discordAutoCreate').checked = discordConfig.auto_create?.enabled || false;
                document.getElementById('discordGuildId').value = discordConfig.auto_create?.guild_id || '';
                document.getElementById('discordRoleName').value = discordConfig.auto_create?.role_name || '';
                
            } else {
            }
        } catch (error) {
        }
    }
    
    async saveAppConfiguration() {
        try {
            const configData = {
                roms_root_directory: document.getElementById('romsRootDirectory').value,
                server: {
                    host: document.getElementById('serverHost').value,
                    port: parseInt(document.getElementById('serverPort').value),
                    debug: document.getElementById('serverDebug').checked
                },
                max_tasks_to_keep: parseInt(document.getElementById('maxTasksToKeep').value),
                authentication: {
                    disable_local_auth: document.getElementById('disableLocalAuth').checked
                }
            };

            const response = await fetch('/api/config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(configData)
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Save Discord credentials separately
                await this.saveDiscordCredentials();
                
                // Show success message
                this.showToast('Configuration saved successfully! Server restart required for path changes.', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('appConfigurationModal'));
                modal.hide();
            } else {
                const error = await response.text();
                this.showToast('Failed to save configuration', 'error');
            }
        } catch (error) {
            this.showToast('Error saving configuration', 'error');
        }
    }
    
    async saveDiscordCredentials() {
        try {
            const discordData = {
                client_id: document.getElementById('discordClientId').value,
                client_secret: document.getElementById('discordClientSecret').value,
                redirect_uri: document.getElementById('discordRedirectUri').value,
                scope: 'identify email guilds guilds.members.read',
                bot_token: document.getElementById('discordBotToken').value,
                auto_create: {
                    enabled: document.getElementById('discordAutoCreate').checked,
                    guild_id: document.getElementById('discordGuildId').value,
                    role_name: document.getElementById('discordRoleName').value
                }
            };

            const response = await fetch('/api/discord-credentials', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(discordData)
            });
            
            if (response.ok) {
                const result = await response.json();
            } else {
                const error = await response.text();
                this.showToast('Failed to save Discord credentials', 'error');
            }
        } catch (error) {
            this.showToast('Error saving Discord credentials', 'error');
        }
    }
    
    initializeVideoConfigurationModal() {
        
        // Add event listener for opening the modal
        const openVideoConfigBtn = document.getElementById('openVideoConfigModal');
        if (openVideoConfigBtn) {
            openVideoConfigBtn.addEventListener('click', () => {
                this.openVideoConfigurationModal();
            });
        }
        
        // Add event listener for refresh button
        const refreshVideoConfigBtn = document.getElementById('refreshVideoConfigBtn');
        if (refreshVideoConfigBtn) {
            refreshVideoConfigBtn.addEventListener('click', () => {
                this.loadVideoConfiguration();
            });
        }
        
        // Add auto-save event listeners for form elements
        this.setupVideoConfigAutoSave();
    }
    
    setupVideoConfigAutoSave() {
        // Auto-save when resolution selection changes
        const resolutionSelect = document.getElementById('videoResolutionSelect');
        if (resolutionSelect) {
            resolutionSelect.addEventListener('change', () => {
                this.saveVideoConfiguration();
            });
        }
        
        // Auto-save when fade checkbox changes
        const fadeCheckbox = document.getElementById('enableFadeInFadeOut');
        if (fadeCheckbox) {
            fadeCheckbox.addEventListener('change', () => {
                this.saveVideoConfiguration();
            });
        }
        
        // Auto-save when CUDA checkbox changes
        const cudaCheckbox = document.getElementById('enableCuda');
        if (cudaCheckbox) {
            cudaCheckbox.addEventListener('change', () => {
                this.saveVideoConfiguration();
            });
        }
        
        // Auto-save when YouTube PO token checkbox changes
        const youtubePoTokenCheckbox = document.getElementById('enableYoutubePoToken');
        if (youtubePoTokenCheckbox) {
            youtubePoTokenCheckbox.addEventListener('change', () => {
                this.saveVideoConfiguration();
            });
        }
        
        // Auto-save when YouTube PO token provider URL changes
        const youtubePoTokenProvider = document.getElementById('youtubePoTokenProvider');
        if (youtubePoTokenProvider) {
            youtubePoTokenProvider.addEventListener('change', () => {
                this.saveVideoConfiguration();
            });
        }
        
        // Auto-save when YouTube skip cookie duration changes
        const youtubeSkipCookieDuration = document.getElementById('youtubeSkipCookieDuration');
        if (youtubeSkipCookieDuration) {
            youtubeSkipCookieDuration.addEventListener('change', () => {
                this.saveVideoConfiguration();
            });
        }

        // Save YouTube cookies button
        const saveCookieBtn = document.getElementById('saveYoutubeCookieBtn');
        if (saveCookieBtn) {
            saveCookieBtn.addEventListener('click', async () => {
                await this.saveYoutubeCookie();
            });
        }
        
        // YouTube API key management buttons
        const saveYoutubeApiKeyBtn = document.getElementById('saveYoutubeApiKeyBtn');
        if (saveYoutubeApiKeyBtn) {
            saveYoutubeApiKeyBtn.addEventListener('click', async () => {
                await this.saveYoutubeApiKey();
            });
        }
        
        const clearYoutubeApiKeyBtn = document.getElementById('clearYoutubeApiKeyBtn');
        if (clearYoutubeApiKeyBtn) {
            clearYoutubeApiKeyBtn.addEventListener('click', async () => {
                await this.clearYoutubeApiKey();
            });
        }
        
        const toggleYoutubeApiKeyVisibilityBtn = document.getElementById('toggleYoutubeApiKeyVisibility');
        if (toggleYoutubeApiKeyVisibilityBtn) {
            toggleYoutubeApiKeyVisibilityBtn.addEventListener('click', () => {
                this.toggleYoutubeApiKeyVisibility();
            });
        }
    }
    
    openVideoConfigurationModal() {
        
        // Load current configuration
        this.loadVideoConfiguration();
        
        const modal = new bootstrap.Modal(document.getElementById('videoConfigModal'));
        modal.show();
        
        // Ensure the first tab is properly activated when modal opens
        setTimeout(() => {
            const firstTab = document.getElementById('general-tab');
            const firstTabContent = document.getElementById('general');
            
            if (firstTab && firstTabContent) {
                // Remove active class from all tabs and content
                document.querySelectorAll('#videoConfigTabs .nav-link').forEach(tab => {
                    tab.classList.remove('active');
                    tab.setAttribute('aria-selected', 'false');
                });
                document.querySelectorAll('#videoConfigTabContent .tab-pane').forEach(content => {
                    content.classList.remove('show', 'active');
                });
                
                // Activate the first tab
                firstTab.classList.add('active');
                firstTab.setAttribute('aria-selected', 'true');
                firstTabContent.classList.add('show', 'active');
            }
        }, 100); // Small delay to ensure modal is fully rendered
    }
    
    async loadVideoConfiguration() {
        try {
            const response = await fetch('/api/video-config');
            if (response.ok) {
                const config = await response.json();
                
                // Populate resolution dropdown
                const resolutionSelect = document.getElementById('videoResolutionSelect');
                if (resolutionSelect) {
                    resolutionSelect.innerHTML = '';
                    
                    // Add options from available resolutions
                    Object.entries(config.available_resolutions).forEach(([value, label]) => {
                        const option = document.createElement('option');
                        option.value = value;
                        option.textContent = label;
                        if (value === config.force_video_resolution) {
                            option.selected = true;
                        }
                        resolutionSelect.appendChild(option);
                    });
                }
                
                // Update current setting display
                const currentResolution = document.getElementById('currentVideoResolution');
                if (currentResolution) {
                    const selectedResolution = config.force_video_resolution || 'No forced resolution (use original)';
                    currentResolution.innerHTML = `<span class="badge bg-primary">${selectedResolution}</span>`;
                }
                
                // Update fade setting checkbox
                const fadeCheckbox = document.getElementById('enableFadeInFadeOut');
                if (fadeCheckbox) {
                    fadeCheckbox.checked = config.enable_fadin_fadout || false;
                }
                
                // Update current fade setting display
                const currentFadeSetting = document.getElementById('currentFadeSetting');
                if (currentFadeSetting) {
                    const fadeStatus = config.enable_fadin_fadout ? 'Enabled' : 'Disabled';
                    const badgeClass = config.enable_fadin_fadout ? 'bg-success' : 'bg-secondary';
                    currentFadeSetting.innerHTML = `<span class="badge ${badgeClass}">${fadeStatus}</span>`;
                }
                
                // Update CUDA setting checkbox
                const cudaCheckbox = document.getElementById('enableCuda');
                if (cudaCheckbox) {
                    cudaCheckbox.checked = config.enable_cuda || false;
                }
                
                // Update current CUDA setting display
                const currentCudaSetting = document.getElementById('currentCudaSetting');
                if (currentCudaSetting) {
                    const cudaStatus = config.enable_cuda ? 'Enabled' : 'Disabled';
                    const badgeClass = config.enable_cuda ? 'bg-success' : 'bg-secondary';
                    currentCudaSetting.innerHTML = `<span class="badge ${badgeClass}">${cudaStatus}</span>`;
                }
                
                // Update YouTube PO token setting checkbox
                const youtubePoTokenCheckbox = document.getElementById('enableYoutubePoToken');
                if (youtubePoTokenCheckbox) {
                    youtubePoTokenCheckbox.checked = config.enable_youtube_po_token || false;
                }
                
                // Update current YouTube PO token setting display
                const currentYoutubePoTokenSetting = document.getElementById('currentYoutubePoTokenSetting');
                if (currentYoutubePoTokenSetting) {
                    const youtubePoTokenStatus = config.enable_youtube_po_token ? 'Enabled' : 'Disabled';
                    const badgeClass = config.enable_youtube_po_token ? 'bg-success' : 'bg-secondary';
                    currentYoutubePoTokenSetting.innerHTML = `<span class="badge ${badgeClass}">${youtubePoTokenStatus}</span>`;
                }
                
                // Update YouTube PO token provider input
                const youtubePoTokenProvider = document.getElementById('youtubePoTokenProvider');
                if (youtubePoTokenProvider) {
                    youtubePoTokenProvider.value = config.youtube_po_token_provider || 'http://127.0.0.1:4416';
                }
                
                // Update current YouTube PO token provider display
                const currentYoutubePoTokenProvider = document.getElementById('currentYoutubePoTokenProvider');
                if (currentYoutubePoTokenProvider) {
                    const providerUrl = config.youtube_po_token_provider || 'http://127.0.0.1:4416';
                    currentYoutubePoTokenProvider.innerHTML = `<span class="badge bg-info">${providerUrl}</span>`;
                }
                
                // Update YouTube skip cookie duration input
                const youtubeSkipCookieDuration = document.getElementById('youtubeSkipCookieDuration');
                if (youtubeSkipCookieDuration) {
                    youtubeSkipCookieDuration.value = config.youtube_skip_cookie_for_video_duration_bigger_than || 60;
                }
                
                // Update current YouTube skip cookie duration display
                const currentYoutubeSkipCookieDuration = document.getElementById('currentYoutubeSkipCookieDuration');
                if (currentYoutubeSkipCookieDuration) {
                    const duration = config.youtube_skip_cookie_for_video_duration_bigger_than || 60;
                    currentYoutubeSkipCookieDuration.innerHTML = `<span class="badge bg-info">${duration} minutes</span>`;
                }

                // Update YouTube cookie status
                const cookieStatus = document.getElementById('youtubeCookieStatus');
                if (cookieStatus) {
                    const exists = !!config.youtube_cookie_exists;
                    cookieStatus.innerHTML = exists ? '<span class="badge bg-success">Cookie file present</span>' : '<span class="badge bg-secondary">No cookie file</span>';
                }
                
                // Update YouTube API key status
                const youtubeApiKeyStatus = document.getElementById('youtubeApiKeyStatus');
                if (youtubeApiKeyStatus) {
                    const hasApiKey = !!config.youtube_api_key_exists;
                    const keyLength = config.youtube_api_key_length || 0;
                    if (hasApiKey) {
                        youtubeApiKeyStatus.innerHTML = `<span class="badge bg-success">Configured (${keyLength} chars)</span>`;
                    } else {
                        youtubeApiKeyStatus.innerHTML = '<span class="badge bg-secondary">Not configured</span>';
                    }
                }
                
            } else {
                this.showToast('Failed to load video configuration', 'error');
            }
        } catch (error) {
            this.showToast('Error loading video configuration', 'error');
        }
    }
    
    async saveVideoConfiguration() {
        try {
            const resolutionSelect = document.getElementById('videoResolutionSelect');
            const forceVideoResolution = resolutionSelect ? resolutionSelect.value : '';
            
            const fadeCheckbox = document.getElementById('enableFadeInFadeOut');
            const enableFadeInFadeOut = fadeCheckbox ? fadeCheckbox.checked : false;
            
            const cudaCheckbox = document.getElementById('enableCuda');
            const enableCuda = cudaCheckbox ? cudaCheckbox.checked : false;
            
            const youtubePoTokenCheckbox = document.getElementById('enableYoutubePoToken');
            const enableYoutubePoToken = youtubePoTokenCheckbox ? youtubePoTokenCheckbox.checked : false;
            
            const youtubePoTokenProvider = document.getElementById('youtubePoTokenProvider');
            const youtubePoTokenProviderUrl = youtubePoTokenProvider ? youtubePoTokenProvider.value : 'http://127.0.0.1:4416';
            
            const youtubeSkipCookieDuration = document.getElementById('youtubeSkipCookieDuration');
            const youtubeSkipCookieDurationValue = youtubeSkipCookieDuration ? parseInt(youtubeSkipCookieDuration.value) || 60 : 60;
            
            const configData = {
                force_video_resolution: forceVideoResolution,
                enable_fadin_fadout: enableFadeInFadeOut,
                enable_cuda: enableCuda,
                enable_youtube_po_token: enableYoutubePoToken,
                youtube_po_token_provider: youtubePoTokenProviderUrl,
                youtube_skip_cookie_for_video_duration_bigger_than: youtubeSkipCookieDurationValue
            };

            const response = await fetch('/api/video-config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(configData)
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Show success message
                this.showToast('Video configuration saved successfully!', 'success');
                
                // Update current setting display
                const currentResolution = document.getElementById('currentVideoResolution');
                if (currentResolution) {
                    const selectedResolution = forceVideoResolution || 'No forced resolution (use original)';
                    currentResolution.innerHTML = `<span class="badge bg-primary">${selectedResolution}</span>`;
                }
                
                // Update current fade setting display
                const currentFadeSetting = document.getElementById('currentFadeSetting');
                if (currentFadeSetting) {
                    const fadeStatus = enableFadeInFadeOut ? 'Enabled' : 'Disabled';
                    const badgeClass = enableFadeInFadeOut ? 'bg-success' : 'bg-secondary';
                    currentFadeSetting.innerHTML = `<span class="badge ${badgeClass}">${fadeStatus}</span>`;
                }
                
                // Don't close modal for auto-save, just show success message
                this.showToast('Video configuration saved automatically', 'success');
            } else {
                const error = await response.text();
                this.showToast('Failed to save video configuration', 'error');
            }
        } catch (error) {
            this.showToast('Error saving video configuration', 'error');
        }
    }

    async saveYoutubeCookie() {
        try {
            const textarea = document.getElementById('youtubeCookieTextarea');
            const content = textarea ? textarea.value : '';
            const resp = await fetch('/api/youtube-cookie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            if (!resp.ok) throw new Error(await resp.text());
            this.showToast('YouTube cookies saved', 'success');
            // Refresh header status
            const statusResp = await fetch('/api/youtube-cookie');
            if (statusResp.ok) {
                const s = await statusResp.json();
                const cookieStatus = document.getElementById('youtubeCookieStatus');
                if (cookieStatus) {
                    cookieStatus.innerHTML = s.exists ? '<span class="badge bg-success">Cookie file present</span>' : '<span class="badge bg-secondary">No cookie file</span>';
                }
            }
        } catch (e) {
            this.showToast('Failed to save YouTube cookie', 'error');
        }
    }
    
    async saveYoutubeApiKey() {
        try {
            const apiKeyInput = document.getElementById('youtubeApiKey');
            const apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';
            
            if (!apiKey) {
                this.showToast('Please enter a YouTube API key', 'error');
                return;
            }
            
            const response = await fetch('/api/youtube-credentials', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            });
            
            if (response.ok) {
                this.showToast('YouTube API key saved successfully!', 'success');
                // Refresh the API key status
                this.loadVideoConfiguration();
            } else {
                const error = await response.json();
                this.showToast(`Failed to save YouTube API key: ${error.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showToast('Error saving YouTube API key', 'error');
        }
    }
    
    async clearYoutubeApiKey() {
        try {
            const response = await fetch('/api/youtube-credentials', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.showToast('YouTube API key cleared successfully!', 'success');
                // Clear the input field
                const apiKeyInput = document.getElementById('youtubeApiKey');
                if (apiKeyInput) {
                    apiKeyInput.value = '';
                }
                // Refresh the API key status
                this.loadVideoConfiguration();
            } else {
                const error = await response.json();
                this.showToast(`Failed to clear YouTube API key: ${error.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showToast('Error clearing YouTube API key', 'error');
        }
    }
    
    toggleYoutubeApiKeyVisibility() {
        const apiKeyInput = document.getElementById('youtubeApiKey');
        const toggleIcon = document.getElementById('youtubeApiKeyToggleIcon');
        
        if (apiKeyInput && toggleIcon) {
            if (apiKeyInput.type === 'password') {
                apiKeyInput.type = 'text';
                toggleIcon.className = 'bi bi-eye-slash';
            } else {
                apiKeyInput.type = 'password';
                toggleIcon.className = 'bi bi-eye';
            }
        }
    }
    
    initializeChangePasswordModal() {
        
        // Add event listener for opening the modal
        const openChangePasswordBtn = document.getElementById('openChangePasswordModal');
        if (openChangePasswordBtn) {
            openChangePasswordBtn.addEventListener('click', () => {
                this.openChangePasswordModal();
            });
        }
        
        // Add event listener for save button
        const savePasswordBtn = document.getElementById('savePasswordBtn');
        if (savePasswordBtn) {
            savePasswordBtn.addEventListener('click', () => {
                this.savePassword();
            });
        }
    }
    
    openChangePasswordModal() {
        
        // Clear form
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
        
        const modal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
        modal.show();
    }
    
    async savePassword() {
        try {
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            // Validate form
            if (!currentPassword || !newPassword || !confirmPassword) {
                this.showToast('All fields are required', 'error');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                this.showToast('New passwords do not match', 'error');
                return;
            }
            
            if (newPassword.length < 6) {
                this.showToast('New password must be at least 6 characters long', 'error');
                return;
            }
            
            // Show loading state
            const saveBtn = document.getElementById('savePasswordBtn');
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Changing...';
            saveBtn.disabled = true;
            
            // Send request
            const response = await fetch('/api/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                    confirm_password: confirmPassword
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Password changed successfully', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('changePasswordModal'));
                modal.hide();
                
                // Clear form
                document.getElementById('currentPassword').value = '';
                document.getElementById('newPassword').value = '';
                document.getElementById('confirmPassword').value = '';
            } else {
                this.showToast(result.message || 'Failed to change password', 'error');
            }
            
        } catch (error) {
            this.showToast('Error changing password', 'error');
        } finally {
            // Restore button state
            const saveBtn = document.getElementById('savePasswordBtn');
            saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Change Password';
            saveBtn.disabled = false;
        }
    }
    
    async loadCacheInformation() {
        try {
            // Load metadata XML date and cache statistics
            const response = await fetch('/api/cache/metadata-info');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update metadata information
                    document.getElementById('metadataXmlDate').textContent = data.metadata_date || 'Unknown';
                    document.getElementById('metadataXmlDate').className = 'badge bg-success';
                    document.getElementById('cacheStatus').textContent = 'Available';
                    document.getElementById('cacheStatus').className = 'badge bg-success';
                    
                    // Update cache statistics
                    if (data.cache_stats) {
                        document.getElementById('cacheGamesCount').textContent = data.cache_stats.total_games.toLocaleString();
                        document.getElementById('cacheAltNamesCount').textContent = data.cache_stats.games_with_alternate_names.toLocaleString();
                        document.getElementById('cacheGameImagesCount').textContent = data.cache_stats.total_images.toLocaleString();
                    } else {
                    }
                } else {
                    document.getElementById('metadataXmlDate').textContent = 'Error';
                    document.getElementById('metadataXmlDate').className = 'badge bg-danger';
                    document.getElementById('cacheStatus').textContent = 'Error';
                    document.getElementById('cacheStatus').className = 'badge bg-danger';
                    
                    // Reset cache statistics on error
                    document.getElementById('cacheGamesCount').textContent = '-';
                    document.getElementById('cacheAltNamesCount').textContent = '-';
                    document.getElementById('cacheGameImagesCount').textContent = '-';
                }
            } else {
                document.getElementById('metadataXmlDate').textContent = 'Error';
                document.getElementById('metadataXmlDate').className = 'badge bg-danger';
                document.getElementById('cacheStatus').textContent = 'Error';
                document.getElementById('cacheStatus').className = 'badge bg-danger';
                
                // Reset cache statistics on error
                document.getElementById('cacheGamesCount').textContent = '-';
                document.getElementById('cacheAltNamesCount').textContent = '-';
                document.getElementById('cacheGameImagesCount').textContent = '-';
            }
            
            // Load MobyGames cache information
            await this.loadMobygamesCacheInformation();
            
            // Load Steam cache information
            await this.loadSteamCacheInformation();
            
        } catch (error) {
            console.error('Error loading cache information:', error);
            document.getElementById('metadataXmlDate').textContent = 'Error';
            document.getElementById('metadataXmlDate').className = 'badge bg-danger';
            document.getElementById('cacheStatus').textContent = 'Error';
            document.getElementById('cacheStatus').className = 'badge bg-danger';
            
            // Reset cache statistics on error
            document.getElementById('cacheGamesCount').textContent = '-';
            document.getElementById('cacheAltNamesCount').textContent = '-';
            document.getElementById('cacheGameImagesCount').textContent = '-';
        }
    }
    
    async loadMobygamesCacheInformation() {
        try {
            const response = await fetch('/api/cache/mobygames-info');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update MobyGames cache information
                    document.getElementById('mobygamesCacheDate').textContent = data.cache_date || 'Unknown';
                    document.getElementById('mobygamesCacheDate').className = 'badge bg-success';
                    document.getElementById('mobygamesCacheStatus').textContent = 'Available';
                    document.getElementById('mobygamesCacheStatus').className = 'badge bg-success';
                    
                    // Update cache statistics
                    if (data.cache_stats) {
                        document.getElementById('mobygamesEntriesCount').textContent = data.cache_stats.total_entries.toLocaleString();
                        document.getElementById('mobygamesPartitionsCount').textContent = data.cache_stats.partition_count.toLocaleString();
                        document.getElementById('mobygamesFileSize').textContent = this.formatFileSize(data.cache_stats.file_size);
                    }
                } else {
                    document.getElementById('mobygamesCacheDate').textContent = 'Not Found';
                    document.getElementById('mobygamesCacheDate').className = 'badge bg-warning';
                    document.getElementById('mobygamesCacheStatus').textContent = 'Not Available';
                    document.getElementById('mobygamesCacheStatus').className = 'badge bg-warning';
                    
                    // Reset cache statistics
                    document.getElementById('mobygamesEntriesCount').textContent = '-';
                    document.getElementById('mobygamesPartitionsCount').textContent = '-';
                    document.getElementById('mobygamesFileSize').textContent = '-';
                }
            } else {
                document.getElementById('mobygamesCacheDate').textContent = 'Error';
                document.getElementById('mobygamesCacheDate').className = 'badge bg-danger';
                document.getElementById('mobygamesCacheStatus').textContent = 'Error';
                document.getElementById('mobygamesCacheStatus').className = 'badge bg-danger';
                
                // Reset cache statistics
                document.getElementById('mobygamesEntriesCount').textContent = '-';
                document.getElementById('mobygamesPartitionsCount').textContent = '-';
                document.getElementById('mobygamesFileSize').textContent = '-';
            }
        } catch (error) {
            console.error('Error loading MobyGames cache information:', error);
            document.getElementById('mobygamesCacheDate').textContent = 'Error';
            document.getElementById('mobygamesCacheDate').className = 'badge bg-danger';
            document.getElementById('mobygamesCacheStatus').textContent = 'Error';
            document.getElementById('mobygamesCacheStatus').className = 'badge bg-danger';
            
            // Reset cache statistics
            document.getElementById('mobygamesEntriesCount').textContent = '-';
            document.getElementById('mobygamesPartitionsCount').textContent = '-';
            document.getElementById('mobygamesFileSize').textContent = '-';
        }
    }
    
    async loadSteamCacheInformation() {
        try {
            const response = await fetch('/api/cache/steam-info');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update Steam cache information
                    document.getElementById('steamCacheDate').textContent = data.cache_date || 'Unknown';
                    document.getElementById('steamCacheDate').className = 'badge bg-success';
                    document.getElementById('steamCacheStatus').textContent = 'Available';
                    document.getElementById('steamCacheStatus').className = 'badge bg-success';
                    
                    // Update cache statistics
                    if (data.cache_stats) {
                        document.getElementById('steamEntriesCount').textContent = data.cache_stats.total_entries.toLocaleString();
                        document.getElementById('steamPartitionsCount').textContent = data.cache_stats.partition_count.toLocaleString();
                        document.getElementById('steamFileSize').textContent = this.formatFileSize(data.cache_stats.file_size);
                    }
                } else {
                    document.getElementById('steamCacheDate').textContent = 'Not Found';
                    document.getElementById('steamCacheDate').className = 'badge bg-warning';
                    document.getElementById('steamCacheStatus').textContent = 'Not Available';
                    document.getElementById('steamCacheStatus').className = 'badge bg-warning';
                    
                    // Reset cache statistics
                    document.getElementById('steamEntriesCount').textContent = '-';
                    document.getElementById('steamPartitionsCount').textContent = '-';
                    document.getElementById('steamFileSize').textContent = '-';
                }
            } else {
                document.getElementById('steamCacheDate').textContent = 'Error';
                document.getElementById('steamCacheDate').className = 'badge bg-danger';
                document.getElementById('steamCacheStatus').textContent = 'Error';
                document.getElementById('steamCacheStatus').className = 'badge bg-danger';
                
                // Reset cache statistics
                document.getElementById('steamEntriesCount').textContent = '-';
                document.getElementById('steamPartitionsCount').textContent = '-';
                document.getElementById('steamFileSize').textContent = '-';
            }
        } catch (error) {
            console.error('Error loading Steam cache information:', error);
            document.getElementById('steamCacheDate').textContent = 'Error';
            document.getElementById('steamCacheDate').className = 'badge bg-danger';
            document.getElementById('steamCacheStatus').textContent = 'Error';
            document.getElementById('steamCacheStatus').className = 'badge bg-danger';
            
            // Reset cache statistics
            document.getElementById('steamEntriesCount').textContent = '-';
            document.getElementById('steamPartitionsCount').textContent = '-';
            document.getElementById('steamFileSize').textContent = '-';
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async updateMetadataXml() {
        const updateBtn = document.getElementById('updateMetadataBtn');
        const originalText = updateBtn.innerHTML;
        
        try {
            // Show loading state
            updateBtn.disabled = true;
            updateBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Updating...';
            
            // Start the update process
            const response = await fetch('/api/cache/update-metadata', { method: 'POST' });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert('Metadata.xml updated successfully!', 'success');
                                // Automatically refresh the cache after successful metadata update
            // Refresh cache information display
                    this.loadCacheInformation();
                } else {
                    this.showAlert(`Failed to update metadata: ${result.error}`, 'danger');
                }
            } else {
                const error = await response.json();
                this.showAlert(`Failed to update metadata: ${error.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error updating metadata: ' + error.message, 'danger');
        } finally {
            // Restore button state
            updateBtn.disabled = false;
            updateBtn.innerHTML = originalText;
        }
    }
    
    async refreshMobygamesCache() {
        const refreshBtn = document.getElementById('refreshMobygamesCacheBtn');
        const originalText = refreshBtn.innerHTML;
        
        try {
            // Show loading state
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Refreshing...';
            
            // Start the refresh process
            const response = await fetch('/api/cache/refresh-mobygames', { method: 'POST' });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert('MobyGames cache refreshed successfully!', 'success');
                    // Refresh cache information display
                    await this.loadMobygamesCacheInformation();
                } else {
                    this.showAlert(`Failed to refresh MobyGames cache: ${result.error}`, 'danger');
                }
            } else {
                const error = await response.json();
                this.showAlert(`Failed to refresh MobyGames cache: ${error.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error refreshing MobyGames cache: ' + error.message, 'danger');
        } finally {
            // Restore button state
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = originalText;
        }
    }
    
    async refreshSteamCache() {
        const refreshBtn = document.getElementById('refreshSteamCacheBtn');
        const originalText = refreshBtn.innerHTML;
        
        try {
            // Show loading state with more detailed message
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Downloading & Refreshing...';
            
            // Start the refresh process
            const response = await fetch('/api/cache/refresh-steam', { method: 'POST' });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showAlert(`Steam cache refreshed successfully! ${result.message}`, 'success');
                    // Refresh cache information display
                    await this.loadSteamCacheInformation();
                } else {
                    this.showAlert(`Failed to refresh Steam cache: ${result.error}`, 'danger');
                }
            } else {
                const error = await response.json();
                this.showAlert(`Failed to refresh Steam cache: ${error.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Error refreshing Steam cache: ' + error.message, 'danger');
        } finally {
            // Restore button state
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = originalText;
        }
    }
    
    openEditModalForSelectedRow() {
        // Get the currently selected row
        const selectedRows = this.gridApi.getSelectedRows();
        
        if (selectedRows.length === 0) {
            this.showAlert('No row selected. Please select a game first.', 'warning');
            return;
        }
        
        if (selectedRows.length > 1) {
            this.showAlert('Multiple rows selected. Please select only one game to edit.', 'warning');
            return;
        }
        
        // Open edit modal for the selected game
        const selectedGame = selectedRows[0];
        this.editGame(selectedGame);
    }
    
    deleteSelectedMedia() {
        if (!this.selectedMedia || this.selectedMedia.length === 0) {
            this.showAlert('No media selected for deletion', 'warning');
            return;
        }
        
        // Show confirmation dialog for multiple items
        const itemCount = this.selectedMedia.length;
        const itemText = itemCount === 1 ? 'item' : 'items';
        const confirmMessage = `Are you sure you want to delete ${itemCount} media ${itemText}?\n\nThis will remove both the files and the entries from gamelist.xml.`;
        
        if (confirm(confirmMessage)) {
            this.performMultipleMediaDeletion();
        }
    }
    async performMultipleMediaDeletion() {
        try {
            const totalItems = this.selectedMedia.length;
            let successCount = 0;
            let errorCount = 0;
            
            // Group media deletions by game to avoid race conditions
            const deletionsByGame = new Map();
            for (const { field, game, mediaPath } of this.selectedMedia) {
                const gameKey = game.path; // Use ROM path as unique key
                if (!deletionsByGame.has(gameKey)) {
                    deletionsByGame.set(gameKey, { game, fields: [] });
                }
                deletionsByGame.get(gameKey).fields.push(field);
            }
            
            // Process each game's media deletions using batch endpoint
            for (const [gameKey, { game, fields }] of deletionsByGame) {
                try {
                    // Use batch deletion endpoint for all fields of this game
                    const deleteResponse = await fetch(`/api/rom-system/${this.currentSystem}/game/delete-media-batch`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            media_fields: fields,
                            rom_path: game.path
                        })
                    });
                    
                    if (deleteResponse.ok) {
                        const result = await deleteResponse.json();
                        if (result.success) {
                            // Update the game object in the main games array
                            const gameIndex = this.games.findIndex(g => g.path === game.path);
                            if (gameIndex !== -1) {
                                // Clear all deleted fields
                                for (const field of result.deleted_fields) {
                                    this.games[gameIndex][field] = '';
                                }
                            }
                            successCount += result.deleted_fields.length;
                            errorCount += result.failed_fields.length;
                            
                            // Log any failed fields
                            if (result.failed_fields.length > 0) {
                            }
                        } else {
                            errorCount += fields.length;
                        }
                    } else {
                        const error = await deleteResponse.json();
                        errorCount += fields.length;
                    }
                } catch (error) {
                    errorCount += fields.length;
                }
            }
            
            // Refresh the grid and media preview after all deletions
            if (successCount > 0) {
                // Refresh the grid and media preview
                this.gridApi.refreshCells();
                if (this.selectedMedia.length > 0) {
                    // Show preview for the first selected game using updated game object
                    const firstGame = this.selectedMedia[0].game;
                    const updatedGame = this.games.find(g => g.path === firstGame.path);
                    if (updatedGame) {
                        // Add a small delay to ensure gamelist is fully updated
                        setTimeout(() => {
                            this.showMediaPreview(updatedGame);
                        }, 100);
                    }
                }
                
                // Refresh edit modal if it's open
                const editModal = document.getElementById('editGameModal');
                if (editModal && editModal.classList.contains('show')) {
                    // Get the currently edited game using the stored ROM path
                    if (this.editingGamePath) {
                        const currentGame = this.games.find(g => g.path === this.editingGamePath);
                        if (currentGame) {
                            // Add a small delay to ensure gamelist is fully updated
                            setTimeout(() => {
                                this.showEditGameMedia(currentGame);
                            }, 100);
                        }
                    }
                }
            }
            
            // Clear selection
            this.selectedMedia = [];
            document.querySelectorAll('.media-preview-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Show result message
            if (errorCount === 0) {
                this.showAlert(`${successCount} media item(s) deleted successfully`, 'success');
            } else if (successCount === 0) {
                this.showAlert(`Failed to delete ${errorCount} media item(s)`, 'error');
            } else {
                this.showAlert(`${successCount} media item(s) deleted, ${errorCount} failed`, 'warning');
            }
            
        } catch (error) {
            this.showAlert('Error during media deletion process', 'error');
        }
    }
    
    async performMediaDeletion(field, game, mediaPath) {
        try {
            // Delete the file first
            const deleteResponse = await fetch('/api/delete-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_path: `roms/${this.currentSystem}/${mediaPath}`
                })
            });
            
            if (deleteResponse.ok) {
                // Set the media field to empty string instead of deleting it
                game[field] = '';
                
                // Mark the game as modified
                this.markGameAsModified(game);
                
                // Update the gamelist.xml
                await this.updateGamelistAfterMediaDeletion(game);
                
                // Refresh the grid and media preview
                this.gridApi.refreshCells();
                this.showMediaPreview(game);
                
                // Clear selection
                this.selectedMedia = [];
                document.querySelectorAll('.media-preview-item').forEach(item => {
                    item.classList.remove('selected');
                });
                
                this.showAlert(`${field} media deleted successfully`, 'success');
            } else {
                const error = await deleteResponse.json();
                this.showAlert(`Failed to delete file: ${error.error}`, 'error');
            }
        } catch (error) {
            this.showAlert('Error deleting media file', 'error');
        }
    }
    
    async updateGamelistAfterMediaDeletion(game) {
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    games: this.games,
                    delete_rom_paths: [] // No games deleted, just media updated
                })
            });
            
            if (response.ok) {
            } else {
            }
        } catch (error) {
        }
    }
    
    async deleteSelectedThumbnails() {
        if (!this.selectedThumbnails || this.selectedThumbnails.length === 0) {
            this.showAlert('No thumbnails selected for deletion', 'warning');
            return;
        }
        
        const count = this.selectedThumbnails.length;
        const confirmMessage = `Are you sure you want to delete ${count} selected thumbnail${count > 1 ? 's' : ''}?`;
        
        if (!confirm(confirmMessage)) {
            return;
        }
        
        try {
            // Prepare file paths for batch deletion
            const filePaths = this.selectedThumbnails.map(thumb => 
                `roms/${this.currentSystem}/${thumb.mediaPath}`
            );
            
            // Make single batch delete call
            const deleteResponse = await fetch('/api/delete-files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_paths: filePaths
                })
            });
            
            if (!deleteResponse.ok) {
                const error = await deleteResponse.json();
                this.showAlert(`Failed to delete thumbnails: ${error.error}`, 'error');
                return;
            }
            
            const result = await deleteResponse.json();
            
            if (!result.success) {
                this.showAlert(`Failed to delete ${result.failed_count} thumbnail${result.failed_count > 1 ? 's' : ''}`, 'error');
                return;
            }
            
            // Group thumbnails by game for updating game objects
            const thumbnailsByGame = {};
            this.selectedThumbnails.forEach(thumb => {
                if (!thumbnailsByGame[thumb.gamePath]) {
                    thumbnailsByGame[thumb.gamePath] = [];
                }
                thumbnailsByGame[thumb.gamePath].push(thumb);
            });
            
            // Update game objects and remove thumbnail elements
            for (const gamePath in thumbnailsByGame) {
                const game = this.games.find(g => g.path === gamePath);
                if (!game) continue;
                
                const gameThumbnails = thumbnailsByGame[gamePath];
                
                for (const thumb of gameThumbnails) {
                    // Clear the media field
                    game[thumb.fieldName] = '';
                    
                    // Mark the game as modified
                    this.markGameAsModified(game);
                    
                    // Remove the thumbnail element
                    const thumbnailElement = document.getElementById(thumb.thumbnailId);
                    if (thumbnailElement) {
                        thumbnailElement.remove();
                    }
                }
                
                // Update gamelist for this game
                await this.updateGamelistAfterMediaDeletion(game);
            }
            
            // Clear selection
            this.selectedThumbnails = [];
            
            // Refresh the grid
            this.gridApi.refreshCells();
            
            this.showAlert(`${count} thumbnail${count > 1 ? 's' : ''} deleted successfully`, 'success');
            
        } catch (error) {
            this.showAlert('Error deleting thumbnails', 'error');
        }
    }
    
    clearMediaSelection() {
        this.selectedMedia = [];
        document.querySelectorAll('.media-preview-item').forEach(item => {
            item.classList.remove('selected');
        });
        this.updateMediaSelectionDisplay();
        this.updateEditModalDeleteButtonState();
    }
    
    clearThumbnailSelection() {
        this.selectedThumbnails = [];
        document.querySelectorAll('.thumbnail-image').forEach(thumb => {
            thumb.classList.remove('selected');
            const checkbox = thumb.querySelector('.thumbnail-checkbox-input');
            if (checkbox) checkbox.checked = false;
        });
        this.updateThumbnailSelectionDisplay();
    }

    updateMediaSelectionDisplay() {
        // Function kept for future use but no longer displays selection info
        // Multiple selection functionality remains intact
    }

    updateGamesCount() {
        // Update the games count display to show both total and selection
        // Always call updateSelectionDisplay to ensure it's up to date
        this.updateSelectionDisplay();
        
        // Update duplicates button state if filter is active
        if (this.duplicatesFilterActive && this.gridApi) {
            const currentRowCount = this.gridApi.getDisplayedRowCount();
            const totalGames = this.games.length;
            if (currentRowCount !== totalGames) {
                // Grid is filtered, update button to show count
                const duplicatesBtn = document.getElementById('showDuplicatesBtn');
                if (duplicatesBtn) {
                    duplicatesBtn.innerHTML = `<i class="bi bi-dup"></i> Hide Duplicates (${currentRowCount})`;
                }
            }
        }
    }
    
    updateSelectionDisplay() {
        const selectedCount = this.selectedGames ? this.selectedGames.length : 0;
        // Use displayed row count from grid instead of total games count
        const displayedCount = this.gridApi ? this.gridApi.getDisplayedRowCount() : (this.games ? this.games.length : 0);
        
        // Update the games count to show selection
        const gamesCountElement = document.getElementById('gamesCount');
        if (gamesCountElement) {
            const beforeText = gamesCountElement.textContent;
            if (selectedCount > 0) {
                const newText = `${selectedCount}/${displayedCount}`;
                gamesCountElement.textContent = newText;
                gamesCountElement.className = 'fw-bold';
                gamesCountElement.style.color = '#ffffff';
                gamesCountElement.style.fontWeight = 'bold';

            } else {
                gamesCountElement.textContent = displayedCount;
                gamesCountElement.className = '';
                gamesCountElement.style.color = '';
                gamesCountElement.style.fontWeight = '';

            }
        }
        
        // Update scrap button state
        const scrapButton = document.getElementById('scrapLaunchboxBtn');
        if (scrapButton) {
            // Always keep the same text and styling
            scrapButton.disabled = false;
            scrapButton.innerHTML = '<i class="bi bi-database-fill"></i> Launchbox Scrap';
            scrapButton.className = 'btn btn-primary btn-sm ms-2';
            
            // Update tooltip based on selection
            if (selectedCount > 0) {
                scrapButton.title = `Scrap ${selectedCount} selected game${selectedCount > 1 ? 's' : ''}`;
            } else {
                scrapButton.title = `Scrap entire collection (${displayedCount} games)`;
            }
        }
    }
    
    updateDeleteButtonState() {
        const deleteBtn = document.getElementById('deleteSelectedBtn');
        if (deleteBtn) {
            deleteBtn.disabled = this.selectedGames.length === 0;
        }
    }
    
    updateFindBestMatchButtonState() {
        const findBestMatchBtn = document.getElementById('globalFindBestMatchBtn');
        if (findBestMatchBtn) {
            findBestMatchBtn.disabled = this.selectedGames.length === 0;
        }
    }
    
    update2DBoxGeneratorButtonState() {
        const boxGeneratorBtn = document.getElementById('global2DBoxGeneratorBtn');
        if (boxGeneratorBtn) {
            boxGeneratorBtn.disabled = this.selectedGames.length === 0;
        }
    }
    
    updateYoutubeDownloadButtonState() {
        const youtubeDownloadBtn = document.getElementById('globalYoutubeDownloadBtn');
        if (youtubeDownloadBtn) {
            youtubeDownloadBtn.disabled = this.selectedGames.length === 0;
        }
    }

    async toggleHiddenFilter() {
        const hiddenBtn = document.getElementById('showHiddenBtn');
        if (!hiddenBtn) return;

        if (this.hiddenFilterActive) {
            // Turn off hidden filter
            this.hiddenFilterActive = false;
            hiddenBtn.classList.remove('btn-info');
            hiddenBtn.classList.add('btn-outline-info');
            hiddenBtn.innerHTML = '<i class="bi bi-eye-slash"></i> Show Hidden';
            
            // Restore original games data with proper filtering
            await this.updateGameGridData(this.games);
            this.showToast('Hidden filter disabled - showing all games', 'info');
        } else {
            // Turn on hidden filter - show ALL games (including hidden ones)
            this.hiddenFilterActive = true;
            hiddenBtn.classList.remove('btn-outline-info');
            hiddenBtn.classList.add('btn-info');
            hiddenBtn.innerHTML = '<i class="bi bi-eye"></i> Hide Hidden';
            
            // Force complete refresh to show all games (including hidden ones)
            this.gridApi.setGridOption('rowData', [...this.games]);
            
            const hiddenGames = this.findHiddenGames();
            if (hiddenGames.length > 0) {
                this.showToast(`Showing all games including ${hiddenGames.length} hidden games`, 'info');
            } else {
                this.showToast('No hidden games found', 'info');
            }
        }
    }

    async toggleDuplicatesFilter() {
        const duplicatesBtn = document.getElementById('showDuplicatesBtn');
        if (!duplicatesBtn) return;

        if (this.duplicatesFilterActive) {
            // Turn off duplicates filter
            this.duplicatesFilterActive = false;
            duplicatesBtn.classList.remove('btn-warning');
            duplicatesBtn.classList.add('btn-outline-warning');
            duplicatesBtn.innerHTML = '<i class="bi bi-dup"></i> Show Duplicates';
            
            // Restore original games data
            this.gridApi.setGridOption('rowData', this.games);
            this.showToast('Duplicates filter disabled - showing all games', 'info');
        } else {
            // Turn on duplicates filter
            this.duplicatesFilterActive = true;
            duplicatesBtn.classList.remove('btn-outline-warning');
            duplicatesBtn.classList.add('btn-warning');
            duplicatesBtn.innerHTML = '<i class="bi bi-dup"></i> Hide Duplicates';
            
            // Filter to show only duplicates
            const duplicateGames = this.findDuplicateGames();
            await this.updateGameGridData(duplicateGames);
            
            if (duplicateGames.length > 0) {
                this.showToast(`Found ${duplicateGames.length} games with duplicates`, 'warning');
            } else {
                this.showToast('No duplicate games found', 'info');
            }
        }
    }

    findDuplicateGames() {
        const duplicates = [];
        const seenNames = new Map();
        const seenLaunchboxIds = new Map();
        const seenIgdbIds = new Map();
        const seenScreenscraperIds = new Map();
        const seenSteamIds = new Map();
        const seenSteamgridIds = new Map();
        
        // First pass: collect all names and IDs
        this.games.forEach(game => {
            const name = game.name?.toLowerCase().trim();
            const launchboxId = game.launchboxid ? game.launchboxid.toString().trim() : null;
            const igdbId = game.igdbid ? game.igdbid.toString().trim() : null;
            const screenscraperId = game.screenscraperid ? game.screenscraperid.toString().trim() : null;
            const steamId = game.steamid ? game.steamid.toString().trim() : null;
            const steamgridId = game.steamgridid ? game.steamgridid.toString().trim() : null;
            
            if (name) {
                if (!seenNames.has(name)) {
                    seenNames.set(name, []);
                }
                seenNames.get(name).push(game);
            }
            
            if (launchboxId && launchboxId !== '0') {
                if (!seenLaunchboxIds.has(launchboxId)) {
                    seenLaunchboxIds.set(launchboxId, []);
                }
                seenLaunchboxIds.get(launchboxId).push(game);
            }
            
            if (igdbId && igdbId !== '0') {
                if (!seenIgdbIds.has(igdbId)) {
                    seenIgdbIds.set(igdbId, []);
                }
                seenIgdbIds.get(igdbId).push(game);
            }
            
            if (screenscraperId && screenscraperId !== '0') {
                if (!seenScreenscraperIds.has(screenscraperId)) {
                    seenScreenscraperIds.set(screenscraperId, []);
                }
                seenScreenscraperIds.get(screenscraperId).push(game);
            }
            
            if (steamId && steamId !== '0') {
                if (!seenSteamIds.has(steamId)) {
                    seenSteamIds.set(steamId, []);
                }
                seenSteamIds.get(steamId).push(game);
            }
            
            if (steamgridId && steamgridId !== '0') {
                if (!seenSteamgridIds.has(steamgridId)) {
                    seenSteamgridIds.set(steamgridId, []);
                }
                seenSteamgridIds.get(steamgridId).push(game);
            }
        });
        
        // Second pass: find duplicates
        seenNames.forEach((games, name) => {
            if (games.length > 1) {
                duplicates.push(...games);
            }
        });
        
        seenLaunchboxIds.forEach((games, launchboxId) => {
            if (games.length > 1) {
                // Only add games that aren't already in duplicates array
                games.forEach(game => {
                    if (!duplicates.some(dup => dup.id === game.id)) {
                        duplicates.push(game);
                    }
                });
            }
        });
        
        seenIgdbIds.forEach((games, igdbId) => {
            if (games.length > 1) {
                // Only add games that aren't already in duplicates array
                games.forEach(game => {
                    if (!duplicates.some(dup => dup.id === game.id)) {
                        duplicates.push(game);
                    }
                });
            }
        });
        
        seenScreenscraperIds.forEach((games, screenscraperId) => {
            if (games.length > 1) {
                // Only add games that aren't already in duplicates array
                games.forEach(game => {
                    if (!duplicates.some(dup => dup.id === game.id)) {
                        duplicates.push(game);
                    }
                });
            }
        });
        
        seenSteamIds.forEach((games, steamId) => {
            if (games.length > 1) {
                // Only add games that aren't already in duplicates array
                games.forEach(game => {
                    if (!duplicates.some(dup => dup.id === game.id)) {
                        duplicates.push(game);
                    }
                });
            }
        });
        
        seenSteamgridIds.forEach((games, steamgridId) => {
            if (games.length > 1) {
                // Only add games that aren't already in duplicates array
                games.forEach(game => {
                    if (!duplicates.some(dup => dup.id === game.id)) {
                        duplicates.push(game);
                    }
                });
            }
        });
        
        return duplicates;
    }

    findHiddenGames() {
        return this.games.filter(game => game.hidden === 'true');
    }

    async refreshHiddenFilter() {
        console.log('refreshHiddenFilter called, hiddenFilterActive:', this.hiddenFilterActive);
        // Refresh the hidden filter to show updated hidden games
        if (this.hiddenFilterActive) {
            console.log('Refreshing hidden filter with', this.games.length, 'total games');
            // Show all games (including newly hidden ones)
            await this.updateGameGridData(this.games);
            
            const hiddenGames = this.findHiddenGames();
            console.log('Found', hiddenGames.length, 'hidden games');
            if (hiddenGames.length > 0) {
                this.showToast(`Showing all games including ${hiddenGames.length} hidden games`, 'info');
            }
        }
    }

    async resetDuplicatesFilter() {
        // Reset duplicates filter state and button appearance
        this.duplicatesFilterActive = false;
        const duplicatesBtn = document.getElementById('showDuplicatesBtn');
        if (duplicatesBtn) {
            duplicatesBtn.classList.remove('btn-warning');
            duplicatesBtn.classList.add('btn-outline-warning');
            duplicatesBtn.innerHTML = '<i class="bi bi-dup"></i> Show Duplicates';
        }
        
        // Restore original data efficiently
        await this.updateGameGridData(this.games);
    }

    async resetHiddenFilter() {
        // Reset hidden filter state and button appearance
        this.hiddenFilterActive = false;
        const hiddenBtn = document.getElementById('showHiddenBtn');
        if (hiddenBtn) {
            hiddenBtn.classList.remove('btn-info');
            hiddenBtn.classList.add('btn-outline-info');
            hiddenBtn.innerHTML = '<i class="bi bi-eye-slash"></i> Show Hidden';
        }
        
        // Restore original data efficiently - this will now filter out hidden games
        await this.updateGameGridData(this.games);
    }
    
    async deleteGameFiles(game) {
        const deletedFiles = [];

        try {
            // Construct the proper ROM path that includes system directory
            if (game.path && game.path.trim() && this.currentSystem) {
                // game.path is just the filename, we need to construct the full relative path
                const fullRomPath = `${this.currentSystem}/${game.path}`;
                // Return the full ROM path so it can be passed to updateGamelistAfterDeletion
                return [fullRomPath];
            } else {
                if (!this.currentSystem) {
                }
                if (!game.path || !game.path.trim()) {
                }
                return [];
            }
            
        } catch (error) {
            return [];
        }
    }
    
    async updateGamelistAfterDeletion(deletedGameRomPaths) {
        try {
            
            // Use the current system from the class instance
            if (!this.currentSystem) {
                return;
            }
            
            const requestBody = {
                games: this.games,
                delete_rom_paths: deletedGameRomPaths
            };
            deletedGameRomPaths.forEach((path, index) => {
            });
            
            // Send request to update gamelist.xml
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });
            
                           if (response.ok) {
                   const result = await response.json();
                   
                   // Log file deletion results
                   if (result.deleted_files && result.deleted_files.length > 0) {
                       result.deleted_files.forEach(file => {
                       });
                   }
                   
                   if (result.failed_deletions && result.failed_deletions.length > 0) {
                       result.failed_deletions.forEach(failed => {
                       });
                   }
                   
                   // Show summary to user
                   if (result.deleted_count > 0) {
                       const successCount = result.deleted_files ? result.deleted_files.length : 0;
                       const failCount = result.failed_deletions ? result.failed_deletions.length : 0;
                   }
               } else {
                   const errorText = await response.text();
               }
            
        } catch (error) {
        }
    }
    
    syncNavigationIndex(game) {
        // Find the index of the game in the games array and update navigation index
        const index = this.games.findIndex(g => g.id === game.id);
        if (index !== -1) {
            this.currentNavigationIndex = index;
        }
    }
    
    navigateAndPreviewRow(direction) {
        if (!this.gridApi) return;
        
        try {
            const displayedCount = this.gridApi.getDisplayedRowCount();
            if (displayedCount <= 0) return;

            // Clamp current index to displayed range; if invalid, try selected row or 0
            let currentIndex = typeof this.currentNavigationIndex === 'number' ? this.currentNavigationIndex : 0;
            if (currentIndex < 0 || currentIndex >= displayedCount) {
                const sel = this.gridApi.getSelectedNodes();
                currentIndex = (sel && sel.length > 0) ? sel[0].rowIndex : 0;
            }

            let targetIndex = currentIndex;
            if (direction === 'up') {
                // Clamp at first displayed row
                targetIndex = Math.max(0, currentIndex - 1);
            } else if (direction === 'down') {
                // Clamp at last displayed row
                targetIndex = Math.min(displayedCount - 1, currentIndex + 1);
            } else if (direction === 'first') {
                targetIndex = 0;
            } else if (direction === 'last') {
                targetIndex = displayedCount - 1;
            }

            // If no movement (already at boundary), do nothing
            if (targetIndex === currentIndex && (direction === 'up' || direction === 'down')) {
                return;
            }

            const node = this.gridApi.getDisplayedRowAtIndex(targetIndex);
            if (!node || !node.data) return;

            // Update tracked index to displayed index
            this.currentNavigationIndex = targetIndex;

            // Ensure the target row is visible in the viewport
            this.gridApi.ensureIndexVisible(targetIndex, 'middle');

            // Show media preview for the navigated game (without selecting it)
            this.showMediaPreview(node.data);

            // Briefly highlight the navigated row for visual feedback
            this.highlightNavigatedRow(targetIndex);

        } catch (error) {
        }
    }
    
    highlightNavigatedRow(rowIndex) {
        try {
            // Get the row element using the correct AG Grid method
            const rowNode = this.gridApi.getDisplayedRowAtIndex(rowIndex);
            if (rowNode && rowNode.element) {
                // Add highlight class
                rowNode.element.classList.add('navigated-row-highlight');
                
                // Remove highlight after animation
                setTimeout(() => {
                    if (rowNode.element) {
                        rowNode.element.classList.remove('navigated-row-highlight');
                    }
                }, 300);
            }
        } catch (error) {
        }
    }
    
    updateForceImportMenuState() {
        const forceImportItem = document.getElementById('forceImportGamelistBtn');
        if (forceImportItem) {
            if (this.currentSystem) {
                // Enable the menu item
                forceImportItem.style.pointerEvents = 'auto';
                forceImportItem.style.opacity = '1';
                forceImportItem.classList.remove('disabled');
            } else {
                // Disable the menu item
                forceImportItem.style.pointerEvents = 'none';
                forceImportItem.style.opacity = '0.5';
                forceImportItem.classList.add('disabled');
            }
        }
    }
    
    enableButtons() {
        document.getElementById('unifiedScanBtn').disabled = false;
        document.getElementById('saveGamelistBtn').disabled = false;
        
        // Update force import menu item state
        this.updateForceImportMenuState();

        document.getElementById('scrapLaunchboxBtn').disabled = false; // Allow full collection scraping
        document.getElementById('scrapIgdbBtn').disabled = false; // Allow IGDB scraping
        document.getElementById('scrapSteamBtn').disabled = false; // Allow Steam scraping
        document.getElementById('scrapSteamgriddbBtn').disabled = false; // Allow SteamGridDB scraping
        
        const screenscraperBtn = document.getElementById('scrapScreenscraperBtn');
        if (screenscraperBtn) {
            screenscraperBtn.disabled = false; // Allow ScreenScraper scraping
        } else {
        }
        
        const mobygamesBtn = document.getElementById('scrapMobygamesBtn');
        if (mobygamesBtn) {
            mobygamesBtn.disabled = false; // Allow MobyGames scraping
        }

        const datscrapperBtn = document.getElementById('scrapDatscrapperBtn');
        if (datscrapperBtn) {
            datscrapperBtn.disabled = false; // Allow DAT Scrapper scraping
        }

        // Update selection display
        this.updateSelectionDisplay();
        
        // Update delete button state
        this.updateDeleteButtonState();
        
        // Update other button states
        this.updateFindBestMatchButtonState();
        this.update2DBoxGeneratorButtonState();
        this.updateYoutubeDownloadButtonState();
    }

    showAlert(message, type = 'info') {
        // Create a simple alert notification
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    async scrapIgdb() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }
        
        // Check if IGDB system mapping exists
        const hasMapping = await this.checkSystemMapping('igdb');
        if (!hasMapping) {
            this.showAlert(`No IGDB system mapping configured for ${this.currentSystem}. Opening configuration...`, 'warning');
            await this.openSystemsConfigForCurrentSystem('igdb');
            return;
        }
        
        try {
            const button = document.getElementById('scrapIgdbBtn');
            const originalText = button.innerHTML;
            
            // Show loading state
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
            button.disabled = true;
            
            // Determine scraping mode
            const isFullCollection = this.selectedGames.length === 0;
            const gamesToScrape = isFullCollection ? this.games : this.selectedGames;
            
            this.showAlert('Starting IGDB scraping...', 'info');
            
            // Get selected fields for IGDB scraping
            let selectedFields;
            try {
                selectedFields = await this.getSelectedIgdbFields();
            } catch (error) {
                selectedFields = []; // Fallback to empty array
            }
            
            const response = await fetch(`/api/scrap-igdb/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selected_games: gamesToScrape.map(game => game.path),
                    selected_fields: selectedFields
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showAlert(`✅ ${result.message}`, 'success');
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Error: ${result.error || 'Unknown error'}`, 'danger');
            }
            
        } catch (error) {
            this.showAlert(`❌ Error starting IGDB scraping: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapIgdbBtn');
            button.innerHTML = '<i class="bi bi-globe"></i> IGDB Scrap';
            button.disabled = false;
        }
    }

    async scrapSteam() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }
        
        try {
            const button = document.getElementById('scrapSteamBtn');
            const originalText = button.innerHTML;
            
            // Show loading state
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
            button.disabled = true;
            
            // Determine scraping mode
            const isFullCollection = this.selectedGames.length === 0;
            const gamesToScrape = isFullCollection ? this.games : this.selectedGames;
            
            this.showAlert('Starting Steam scraping...', 'info');
            
            // Get selected fields for Steam scraping
            const selectedFields = await this.getSelectedSteamFields();
            
            const response = await fetch(`/api/scrap-steam/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                selected_games: gamesToScrape.map(game => game.path),
                selected_fields: selectedFields
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showAlert(`✅ ${result.message}`, 'success');
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Error: ${result.error || 'Unknown error'}`, 'danger');
            }
            
        } catch (error) {
            this.showAlert(`❌ Error starting Steam scraping: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapSteamBtn');
            button.innerHTML = '<i class="bi bi-steam"></i> Steam Scrap';
            button.disabled = false;
        }
    }

    async scrapSteamgriddb() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }
        
        try {
            const button = document.getElementById('scrapSteamgriddbBtn');
            const originalText = button.innerHTML;
            
            // Show loading state
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
            button.disabled = true;
            
            // Determine scraping mode
            const isFullCollection = this.selectedGames.length === 0;
            const gamesToScrape = isFullCollection ? this.games : this.selectedGames;
            
            this.showAlert('Starting SteamGridDB scraping...', 'info');
            
            // Get selected fields for SteamGridDB scraping
            const selectedFields = await this.getSelectedSteamgriddbFields();
            
            const response = await fetch(`/api/scrap-steamgriddb/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selected_games: gamesToScrape.map(game => game.path),
                    selected_fields: selectedFields
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showAlert(`✅ ${result.message}`, 'success');
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Error: ${result.error || 'Unknown error'}`, 'danger');
            }
            
        } catch (error) {
            this.showAlert(`❌ Error starting SteamGridDB scraping: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapSteamgriddbBtn');
            button.innerHTML = '<i class="bi bi-grid-3x3-gap"></i> SteamGridDB Scrap';
            button.disabled = false;
        }
    }

    async scrapScreenscraper() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }
        
        // Check if ScreenScraper system mapping exists
        const hasMapping = await this.checkSystemMapping('screenscraper');
        if (!hasMapping) {
            this.showAlert(`No ScreenScraper system mapping configured for ${this.currentSystem}. Opening configuration...`, 'warning');
            await this.openSystemsConfigForCurrentSystem('screenscraper');
            return;
        }
        
        try {
            const button = document.getElementById('scrapScreenscraperBtn');
            const originalText = button.innerHTML;
            
            // Show loading state
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
            button.disabled = true;
            
            // Determine scraping mode
            const isFullCollection = this.selectedGames.length === 0;
            const gamesToScrape = isFullCollection ? this.games : this.selectedGames;
            
            this.showAlert('Starting ScreenScraper task...', 'info');
            
            // Get selected fields
            const selectedFields = await this.getSelectedScreenscraperFields();
            
            const requestBody = {
                selected_games: gamesToScrape.map(game => game.path),
                selected_fields: selectedFields
            };
            
            const response = await fetch(`/api/scrap-screenscraper/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showAlert(`✅ ${result.message}`, 'success');
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Error: ${result.error || 'Unknown error'}`, 'danger');
            }
            
        } catch (error) {
            this.showAlert(`❌ Error starting ScreenScraper task: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapScreenscraperBtn');
            button.innerHTML = '<i class="bi bi-search"></i> ScreenScraper';
            button.disabled = false;
        }
    }

    async getSelectedMobygamesFields() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get MobyGames field mappings from config
            const textFields = Object.keys(config.mobygames?.mapping || {});
            const mediaFields = Object.keys(config.mobygames?.image_type_mappings || {});

            // Read field selections directly from cookies
            const selectedTextFields = [];
            const selectedMediaFields = [];
            let hasUncheckedTextFields = false;
            let hasUncheckedMediaFields = false;
            
            // Check text fields
            textFields.forEach(field => {
                const cookieName = `mobygamesField_${field}`;
                const cookieValue = this.getCookie(cookieName);
                
                if (cookieValue !== null) {
                    if (cookieValue === 'true') {
                        selectedTextFields.push(field);
                    } else {
                        hasUncheckedTextFields = true;
                    }
                } else {
                    selectedTextFields.push(field);
                }
            });
            
            // Check media fields
            mediaFields.forEach(field => {
                const cookieName = `mobygamesMediaField_${field}`;
                const cookieValue = this.getCookie(cookieName);
                
                if (cookieValue !== null) {
                    if (cookieValue === 'true') {
                        selectedMediaFields.push(field);
                    } else {
                        hasUncheckedMediaFields = true;
                    }
                } else {
                    selectedMediaFields.push(field);
                }
            });

            // If we have some unchecked fields, return only the selected ones
            if (hasUncheckedTextFields) {
                // Return only selected text fields, all media fields
                return {
                    selected_text_fields: selectedTextFields,
                    selected_media_fields: hasUncheckedMediaFields ? selectedMediaFields : mediaFields
                };
            }
            
            if (hasUncheckedMediaFields) {
                // Return all text fields, only selected media fields
                return {
                    selected_text_fields: textFields,
                    selected_media_fields: selectedMediaFields
                };
            }
            
            // If all fields are selected (no unchecked fields), return all fields
            return {
                selected_text_fields: textFields,
                selected_media_fields: mediaFields
            };
        } catch (error) {
            console.error('Error getting selected MobyGames fields:', error);
            return {
                selected_text_fields: [],
                selected_media_fields: []
            };
        }
    }

    async getSelectedDatscrapperFields() {
        try {
            // Fetch config to get dynamic field mappings
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Get DAT Scrapper field mappings from config
            const mapping = config.datscrapper?.mapping || {};
            const datFields = Object.keys(mapping);
            const gamelistFields = Object.values(mapping);

            // Read field selections directly from cookies
            const selectedGamelistFields = [];
            let hasUncheckedTextFields = false;
            
            // Check text fields - cookies store gamelist field names
            gamelistFields.forEach(gamelistField => {
                const cookieName = `datscrapperField_${gamelistField}`;
                const cookieValue = this.getCookie(cookieName);
                
                if (cookieValue !== null) {
                    if (cookieValue === 'true') {
                        selectedGamelistFields.push(gamelistField);
                    } else {
                        hasUncheckedTextFields = true;
                    }
                } else {
                    // No cookie exists - treat as unchecked
                    hasUncheckedTextFields = true;
                }
            });

            // If we have some unchecked fields, return only the selected ones
            if (hasUncheckedTextFields) {
                return {
                    selected_text_fields: selectedGamelistFields
                };
            }
            
            // If all fields are selected (no unchecked fields), return all fields
            return {
                selected_text_fields: gamelistFields
            };
        } catch (error) {
            console.error('Error getting selected DAT Scrapper fields:', error);
            return {
                selected_text_fields: []
            };
        }
    }

    async scrapMobygames() {
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
            return;
        }
        
        // Check if MobyGames system mapping exists
        const hasMapping = await this.checkSystemMapping('mobygames');
        if (!hasMapping) {
            this.showAlert(`No MobyGames system mapping configured for ${this.currentSystem}. Opening configuration...`, 'warning');
            await this.openSystemsConfigForCurrentSystem('mobygames');
            return;
        }
        
        try {
            const button = document.getElementById('scrapMobygamesBtn');
            const originalText = button.innerHTML;
            
            // Show loading state
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
            button.disabled = true;
            
            // Get selected games
            const selectedGames = this.gridApi.getSelectedRows().map(row => row.path);
            
            // Get selected fields from cookies (like other scrapers)
            const fieldSelections = await this.getSelectedMobygamesFields();
            
            // Get overwrite settings from cookies
            const overwriteTextFields = this.getCookie('overwriteTextFieldsMobygames') === 'true';
            const overwriteMediaFields = this.getCookie('overwriteMediaFieldsMobygames') === 'true';
            
            const response = await fetch(`/api/scrap-mobygames/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    selected_games: selectedGames,
                    selected_text_fields: fieldSelections.selected_text_fields,
                    selected_media_fields: fieldSelections.selected_media_fields,
                    overwrite_text_fields: overwriteTextFields,
                    overwrite_media_fields: overwriteMediaFields
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(`✅ MobyGames task started for ${this.currentSystem}`, 'success');
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Failed to start MobyGames task: ${result.error}`, 'danger');
            }
            
        } catch (error) {
            this.showAlert(`❌ Error starting MobyGames task: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapMobygamesBtn');
            button.innerHTML = '<i class="bi bi-database"></i> MobyGames';
            button.disabled = false;
        }
    }

    async scrapDatscrapper() {
        if (!this.currentSystem) {
            this.showAlert('❌ Please select a system first', 'warning');
            return;
        }

        // Check if DAT file is configured for this system
        const response = await fetch('/api/systems');
        const data = await response.json();
        
        if (!data.success) {
            this.showAlert('❌ Failed to load systems configuration', 'danger');
            return;
        }
        
        const systemConfig = data.systems[this.currentSystem];
        
        if (!systemConfig || !systemConfig.dat_file) {
            this.showAlert('❌ No DAT file configured for this system. Please configure it in Systems Configuration.', 'warning');
            await this.openSystemsConfigForCurrentSystem('datscrapper');
            return;
        }
        
        try {
            const button = document.getElementById('scrapDatscrapperBtn');
            const originalText = button.innerHTML;
            
            // Show loading state
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
            button.disabled = true;
            
            // Get selected games
            const selectedGames = this.selectedGames.map(game => game.path);
            
            // Get selected fields for DAT Scrapper scraping
            const fieldSelections = await this.getSelectedDatscrapperFields();
            
            // Get overwrite settings from cookies
            const overwriteTextFields = this.getCookie('overwriteTextFieldsDatscrapper') === 'true';
            const overwriteMediaFields = this.getCookie('overwriteMediaFieldsDatscrapper') === 'true';
            
            const response = await fetch(`/api/scrap-datscrapper/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selected_games: selectedGames,
                    selected_text_fields: fieldSelections.selected_text_fields,
                    selected_media_fields: [],
                    overwrite_text_fields: overwriteTextFields,
                    overwrite_media_fields: overwriteMediaFields
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(`✅ DAT Scrapper task started for ${this.currentSystem}`, 'success');
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Failed to start DAT Scrapper task: ${result.error}`, 'danger');
            }
            
        } catch (error) {
            this.showAlert(`❌ Error starting DAT Scrapper task: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapDatscrapperBtn');
            button.innerHTML = '<i class="bi bi-file-earmark-code"></i> DAT Scrapper';
            button.disabled = false;
        }
    }

    showInlineEditNotification(field, oldValue, newValue) {
        // Create a small, subtle notification for inline edits
        const notificationDiv = document.createElement('div');
        notificationDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
        notificationDiv.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 250px; max-width: 350px; font-size: 0.9em;';
        
        const fieldName = field.charAt(0).toUpperCase() + field.slice(1);
        const message = `${fieldName} updated: "${oldValue || 'empty'}" → "${newValue || 'empty'}"`;
        
        notificationDiv.innerHTML = `
            <i class="bi bi-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notificationDiv);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notificationDiv.parentNode) {
                notificationDiv.remove();
            }
        }, 3000);
    }

    showColumnChangeNotification(message) {
        // Create a small, subtle notification for column changes
        const notificationDiv = document.createElement('div');
        notificationDiv.className = 'alert alert-info alert-dismissible fade show position-fixed';
        notificationDiv.style.cssText = 'top: 120px; right: 20px; z-index: 9999; min-width: 250px; max-width: 350px; font-size: 0.8em;';
        
        notificationDiv.innerHTML = `
            <i class="bi bi-columns-gap me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notificationDiv);
        
        // Auto-remove after 2 seconds (shorter for column changes)
        setTimeout(() => {
            if (notificationDiv.parentNode) {
                notificationDiv.remove();
            }
        }, 2000);
    }

    toggleColumnsPanel() {
        const panel = document.getElementById('customColumnsPanel');
        const button = document.getElementById('toggleColumnsPanelBtn');
        
        if (panel.style.display === 'none') {
            // Show the panel
            panel.style.display = 'block';
            button.innerHTML = '<i class="bi bi-columns-gap"></i>';
            button.className = 'btn btn-primary btn-sm';
            
            // Generate column checkboxes if not already done
            if (document.getElementById('columnsCheckboxes').children.length === 0) {
                this.generateColumnCheckboxes();
            }
        } else {
            // Hide the panel
            panel.style.display = 'none';
            button.innerHTML = '<i class="bi bi-columns-gap"></i>';
            button.className = 'btn btn-outline-primary btn-sm';
        }
    }

    async toggleThumbnailView() {
        this.thumbnailViewEnabled = !this.thumbnailViewEnabled;
        const button = document.getElementById('thumbnailViewBtn');
        const gridDiv = document.getElementById('gamesGrid');
        
        if (this.thumbnailViewEnabled) {
            // Enable thumbnail view
            button.innerHTML = '<i class="bi bi-list"></i>';
            button.className = 'btn btn-primary btn-sm';
            gridDiv.classList.add('thumbnail-view');
            this.refreshGridWithThumbnailView();
        } else {
            // Disable thumbnail view
            button.innerHTML = '<i class="bi bi-grid-3x3-gap"></i>';
            button.className = 'btn btn-outline-primary btn-sm';
            gridDiv.classList.remove('thumbnail-view');
            this.clearThumbnailSelection(); // Clear any existing selection
            await this.refreshGridWithNormalView();
        }
    }

    getMediaFieldsForThumbnail() {
        // Return all media fields from config (excluding video and manual as requested)
        // Use cached fields if available, otherwise use fallback
        if (this.mediaFieldsCache && Array.isArray(this.mediaFieldsCache)) {
            return this.mediaFieldsCache.filter(field => field !== 'manual');
        }
        
        // Fallback to default media fields (excluding manual)
        return ['marquee', 'boxart', 'image', 'cartridge', 'fanart', 'titleshot', 'boxback', 'thumbnail'];
    }

    refreshGridWithThumbnailView() {
        if (!this.gridApi) return;
        
        // Get all media fields from config (excluding video as requested)
        const mediaFields = this.getMediaFieldsForThumbnail();
        
        // Create thumbnail column definitions
        const thumbnailColumns = [
            { 
                headerName: '', 
                field: 'checkbox', 
                width: 50, 
                checkboxSelection: true, 
                headerCheckboxSelection: true,
                pinned: 'left',
                resizable: false,
                sortable: false,
                filter: false
            },
            { 
                field: 'name', 
                headerName: 'Name', 
                editable: true, 
                sortable: true, 
                filter: true, 
                resizable: true, 
                flex: 2,
                cellStyle: { 
                    fontWeight: 'bold',
                    backgroundColor: '#f8f9fa'
                }
            }
        ];
        
        // Add media columns with thumbnail renderers
        mediaFields.forEach(fieldName => {
            const headerName = fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
            thumbnailColumns.push({
                field: fieldName,
                headerName: headerName,
                width: 120,
                resizable: true,
                sortable: false,
                filter: false,
                cellRenderer: this.createThumbnailRenderer(fieldName)
            });
        });
        
        // Update column definitions
        this.gridApi.setGridOption('columnDefs', thumbnailColumns);
        
        // Set row height for thumbnail view (140px image + 20px padding)
        this.gridApi.setGridOption('rowHeight', 160);
        
        // Setup lazy loading immediately and after delays
        this.setupLazyLoading();
        setTimeout(() => {
            this.setupLazyLoading();
        }, 100);
        setTimeout(() => {
            this.setupLazyLoading();
        }, 500);
        setTimeout(() => {
            this.setupLazyLoading();
        }, 1000);
    }

    async refreshGridWithNormalView() {
        if (!this.gridApi) return;
        
        // Reset row height to default
        this.gridApi.setGridOption('rowHeight', 25);
        
        // Restore original column definitions by reinitializing the grid
        await this.initializeGrid();
        
        // Ensure the grid has the current game data after reinitialization
        if (this.games && this.games.length > 0) {
            await this.refreshGridData();
        }
    }

    createThumbnailRenderer(fieldName) {
        return (params) => {
            if (!params.data || !params.data[fieldName]) {
                return '<div class="thumbnail-image">No image</div>';
            }
            
            const imagePath = params.data[fieldName];
            let imageUrl = imagePath.startsWith('./') ? imagePath.substring(2) : imagePath;
            
            // Add system path if not already present
            if (this.currentSystem && !imageUrl.startsWith(`roms/${this.currentSystem}/`)) {
                imageUrl = `roms/${this.currentSystem}/${imageUrl}`;
            }
            
            // Create a unique ID for this thumbnail
            const thumbnailId = `thumb_${fieldName}_${params.data.path || Math.random().toString(36).substr(2, 9)}`;
            
            // Try loading the image directly first
            const img = new Image();
            img.onload = () => {
                const container = document.getElementById(thumbnailId);
                if (container) {
                    container.innerHTML = `
                        <div class="thumbnail-checkbox">
                            <input type="checkbox" class="thumbnail-checkbox-input" onclick="event.stopPropagation(); gameManager.selectThumbnail('${thumbnailId}', '${fieldName}', '${params.data.path}', '${imagePath}', event);" />
                        </div>
                        <img src="${imageUrl}" alt="${fieldName}" 
                            onmouseenter="gameManager.showThumbnailHover(event, '${imageUrl}', '${fieldName}')" 
                            onmouseleave="gameManager.hideThumbnailHover()" />
                    `;
                    container.classList.remove('thumbnail-loading');
                }
            };
            img.onerror = () => {
                const container = document.getElementById(thumbnailId);
                if (container) {
                    container.innerHTML = 'Error';
                    container.classList.remove('thumbnail-loading');
                }
            };
            img.src = imageUrl;
            
            return `
                <div id="${thumbnailId}" class="thumbnail-image thumbnail-loading" data-src="${imageUrl}" data-field="${fieldName}" 
                     data-game-path="${params.data.path}" data-media-path="${imagePath}"
                     onmouseenter="gameManager.showThumbnailHover(event, '${imageUrl}', '${fieldName}')" 
                     onmouseleave="gameManager.hideThumbnailHover()"
                     onclick="gameManager.selectThumbnail('${thumbnailId}', '${fieldName}', '${params.data.path}', '${imagePath}', event)">
                    <div class="thumbnail-checkbox">
                        <input type="checkbox" class="thumbnail-checkbox-input" onclick="event.stopPropagation(); gameManager.selectThumbnail('${thumbnailId}', '${fieldName}', '${params.data.path}', '${imagePath}', event);" />
                    </div>
                    Loading...
                </div>
            `;
        };
    }

    setupLazyLoading() {
        if (!this.gridApi) return;

        // Clear any existing observer
        if (this.lazyLoadingObserver) {
            this.lazyLoadingObserver.disconnect();
        }
        
        // Use a simpler approach - load all visible images immediately
        // and use a MutationObserver to watch for new cells
        this.loadVisibleThumbnails();
        
        // Watch for new cells being added to the grid
        const gridContainer = document.getElementById('gamesGrid');
        if (gridContainer) {
            this.lazyLoadingObserver = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                const thumbnailContainers = node.querySelectorAll ? 
                                    node.querySelectorAll('.thumbnail-image[data-src]') : [];
                                thumbnailContainers.forEach(container => {
                                    this.loadThumbnailImage(container, 
                                        container.getAttribute('data-src'), 
                                        container.getAttribute('data-field'));
                                });
                            }
                        });
                    }
                });
            });
            
            this.lazyLoadingObserver.observe(gridContainer, {
                childList: true,
                subtree: true
            });
        }
    }
    
    loadVisibleThumbnails() {
        const thumbnailContainers = document.querySelectorAll('.thumbnail-image[data-src]');
        
        thumbnailContainers.forEach(container => {
            const src = container.getAttribute('data-src');
            const field = container.getAttribute('data-field');
            if (src && !container.querySelector('img')) {
                this.loadThumbnailImage(container, src, field);
            }
        });
    }

    loadThumbnailImage(container, src, field) {
        
        // Check if already loaded
        if (container.querySelector('img')) {
            return;
        }
        
        const img = new Image();
        img.onload = () => {
            container.innerHTML = `<img src="${src}" alt="${field}" 
                onmouseenter="gameManager.showThumbnailHover(event, '${src}', '${field}')" 
                onmouseleave="gameManager.hideThumbnailHover()" />`;
            container.classList.remove('thumbnail-loading');
        };
        img.onerror = (error) => {
            container.innerHTML = 'Error';
            container.classList.remove('thumbnail-loading');
        };
        img.src = src;
    }

    showThumbnailHover(event, imageUrl, fieldName) {
        // Remove any existing tooltip
        this.hideThumbnailHover();
        
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'thumbnail-hover-tooltip';
        tooltip.id = 'thumbnail-hover-tooltip';
        
        // Create image element
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = fieldName;
        img.onerror = () => {
            tooltip.innerHTML = `<div style="padding: 20px; text-align: center; color: #6c757d;">No image available</div>`;
        };
        
        tooltip.appendChild(img);
        document.body.appendChild(tooltip);
        
        // Position tooltip near mouse cursor
        const rect = event.target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        let left = rect.right + 10;
        let top = rect.top;
        
        // Adjust if tooltip would go off screen
        if (left + tooltipRect.width > window.innerWidth) {
            left = rect.left - tooltipRect.width - 10;
        }
        if (top + tooltipRect.height > window.innerHeight) {
            top = window.innerHeight - tooltipRect.height - 10;
        }
        if (top < 0) {
            top = 10;
        }
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }

    hideThumbnailHover() {
        const tooltip = document.getElementById('thumbnail-hover-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }
    
    selectThumbnail(thumbnailId, fieldName, gamePath, mediaPath, event) {
        // Prevent row selection when clicking on thumbnails
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        const thumbnail = document.getElementById(thumbnailId);
        if (!thumbnail) return;
        
        const isSelected = thumbnail.classList.contains('selected');
        const checkbox = thumbnail.querySelector('.thumbnail-checkbox-input');
        
        if (isSelected) {
            // Deselect
            thumbnail.classList.remove('selected');
            if (checkbox) checkbox.checked = false;
            
            // Remove from selectedThumbnails array
            this.selectedThumbnails = this.selectedThumbnails.filter(item => 
                !(item.thumbnailId === thumbnailId)
            );
        } else {
            // Select
            thumbnail.classList.add('selected');
            if (checkbox) checkbox.checked = true;
            
            // Add to selectedThumbnails array
            this.selectedThumbnails.push({
                thumbnailId,
                fieldName,
                gamePath,
                mediaPath,
                game: this.games.find(g => g.path === gamePath)
            });
        }
        
        // Update selection display
        this.updateThumbnailSelectionDisplay();
    }
    
    updateThumbnailSelectionDisplay() {
        // Update any selection counter or UI elements
        const selectionCount = this.selectedThumbnails.length;
        // No UI elements to update since buttons were removed
    }

    generateColumnCheckboxes() {
        if (!this.gridApi) return;
        
        const columnsCheckboxes = document.getElementById('columnsCheckboxes');
        columnsCheckboxes.innerHTML = '';
        
        // Get all column definitions
        const columnDefs = this.gridApi.getColumnDefs();
        
        columnDefs.forEach(colDef => {
            if (colDef.field && colDef.field !== 'checkbox') { // Skip checkbox column
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check';
                
                const checkbox = document.createElement('input');
                checkbox.className = 'form-check-input';
                checkbox.type = 'checkbox';
                checkbox.id = `col_${colDef.field}`;
                checkbox.checked = !colDef.hide;
                
                checkbox.addEventListener('change', (e) => {
                    this.toggleColumn(colDef.field, e.target.checked);
                });
                
                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = `col_${colDef.field}`;
                label.textContent = colDef.headerName || colDef.field;
                
                checkboxDiv.appendChild(checkbox);
                checkboxDiv.appendChild(label);
                columnsCheckboxes.appendChild(checkboxDiv);
            }
        });

    }

    toggleColumn(field, visible) {
        
        if (!this.gridApi) {
            return;
        }
        
        const column = this.gridApi.getColumn(field);
        
        if (column) {
            this.gridApi.setColumnVisible(field, visible);
            
            this.saveColumnState();
            
            // Show brief feedback that the change was saved
            const columnName = column.getColDef().headerName || field;
            this.showColumnChangeNotification(`${columnName} ${visible ? 'shown' : 'hidden'} - saved to preferences`);
        } else {
        }
    }
    showAllColumns() {
        if (!this.gridApi) return;
        
        const columnDefs = this.gridApi.getColumnDefs();
        columnDefs.forEach(colDef => {
            if (colDef.field && colDef.field !== 'checkbox') {
                this.gridApi.setColumnVisible(colDef.field, true);
            }
        });
        
        // Update checkboxes
        this.generateColumnCheckboxes();
        
        // Save the new state to cookies
        this.saveColumnState();
    }

    hideAllColumns() {
        if (!this.gridApi) return;
        
        const columnDefs = this.gridApi.getColumnDefs();
        columnDefs.forEach(colDef => {
            if (colDef.field && colDef.field !== 'checkbox') {
                this.gridApi.setColumnVisible(colDef.field, false);
            }
        });
        
        // Update checkboxes
        this.generateColumnCheckboxes();
        
        // Save the new state to cookies
        this.saveColumnState();
    }

    resetColumns() {
        if (!this.gridApi) return;
        
        // Show all columns by default
        this.showAllColumns();
        
        // Reset column order to default
        const columnDefs = this.gridApi.getColumnDefs();
        const columnIds = columnDefs.map(col => col.field).filter(field => field && field !== 'checkbox');
        this.gridApi.setColumnOrder(columnIds);
        
        // Clear saved column state
        this.setCookie('columnState', '');
    }

    saveColumnState() {
        if (!this.gridApi) return;

        const columnState = {};
        const columnDefs = this.gridApi.getColumnDefs();
        
        // Get all visible columns in their current order
        const allColumns = this.gridApi.getAllDisplayedColumns();
        const columnOrder = allColumns.map(col => col.getColId());
        
        columnDefs.forEach(colDef => {
            if (colDef.field && colDef.field !== 'checkbox') {
                const column = this.gridApi.getColumn(colDef.field);
                if (column) {
                    const isVisible = column.isVisible();
                    const orderIndex = columnOrder.indexOf(colDef.field);
                    
                    columnState[colDef.field] = {
                        visible: isVisible,
                        order: orderIndex
                    };
                }
            }
        });
        
        const cookieValue = JSON.stringify(columnState);
        
        this.setCookie('columnState', cookieValue);
        
        // Verify cookie was set
        const savedCookie = this.getCookie('columnState');
    }

    loadColumnState() {
        if (!this.gridApi) return;
        
        const savedState = this.getCookie('columnState');
        if (savedState) {
            try {
                const columnState = JSON.parse(savedState);
                
                Object.keys(columnState).forEach(field => {
                    const state = columnState[field];
                    if (state.visible !== undefined) {
                        this.gridApi.setColumnVisible(field, state.visible);
                    }
                });
                
                // Update checkboxes if panel is open
                if (document.getElementById('customColumnsPanel').style.display !== 'none') {
                    this.generateColumnCheckboxes();
                }
            } catch (error) {
            }
        }
        
        // Add event listeners for search modals
        this.initializeSearchModalEventListeners();
    }
    
    initializeSearchModalEventListeners() {
        // IGDB Search Modal
        const igdbSearchButton = document.getElementById('igdbSearchButton');
        const igdbSearchInput = document.getElementById('igdbSearchGameNameInput');
        if (igdbSearchButton && igdbSearchInput) {
            igdbSearchButton.addEventListener('click', () => {
                this.performIgdbSearch();
            });
            igdbSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performIgdbSearch();
                }
            });
        }
        
        // MobyGames Search Modal
        const mobygamesSearchButton = document.getElementById('mobygamesSearchButton');
        const mobygamesSearchInput = document.getElementById('mobygamesSearchGameNameInput');
        if (mobygamesSearchButton && mobygamesSearchInput) {
            mobygamesSearchButton.addEventListener('click', () => {
                this.performMobygamesSearch();
            });
            mobygamesSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performMobygamesSearch();
                }
            });
        }
        
        // ScreenScraper Search Modal
        const screenscraperSearchButton = document.getElementById('screenscraperSearchButton');
        const screenscraperSearchInput = document.getElementById('screenscraperSearchGameNameInput');
        if (screenscraperSearchButton && screenscraperSearchInput) {
            screenscraperSearchButton.addEventListener('click', () => {
                this.performScreenscraperSearch();
            });
            screenscraperSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performScreenscraperSearch();
                }
            });
        }
        
        // SteamGridDB Search Modal
        const steamgridSearchButton = document.getElementById('steamgridSearchButton');
        const steamgridSearchInput = document.getElementById('steamgridSearchGameNameInput');
        if (steamgridSearchButton && steamgridSearchInput) {
            steamgridSearchButton.addEventListener('click', () => {
                this.performSteamgridSearch();
            });
            steamgridSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSteamgridSearch();
                }
            });
        }
        
        // Steam Search Modal
        const steamSearchButton = document.getElementById('steamSearchButton');
        const steamSearchInput = document.getElementById('steamSearchGameNameInput');
        if (steamSearchButton && steamSearchInput) {
            steamSearchButton.addEventListener('click', () => {
                this.performSteamSearch();
            });
            steamSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSteamSearch();
                }
            });
        }
        
        // LaunchBox Find Best Match Modal
        const gameEditSearchButton = document.getElementById('gameEditSearchButton');
        const gameEditSearchInput = document.getElementById('gameEditOriginalGameNameInput');
        if (gameEditSearchButton && gameEditSearchInput) {
            gameEditSearchButton.addEventListener('click', () => {
                this.performLaunchboxSearch();
            });
            gameEditSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performLaunchboxSearch();
                }
            });
        }
    }

    async loadState() {
        const savedSystem = this.getCookie('selectedSystem');
        const savedMediaPreview = this.getCookie('mediaPreviewEnabled');
        const savedPartialMatchModal = this.getCookie('enablePartialMatchModal');
        const savedForceDownload = this.getCookie('forceDownloadImages');
        const savedOverwriteTextFields = this.getCookie('launchboxOverwriteTextFields');
        
        // Load available systems first and wait for them to be populated
        await this.loadAvailableSystems();
        
        if (savedSystem) {
            // Set the dropdown value after systems are loaded
            const systemSelect = document.getElementById('systemSelect');
            if (systemSelect) {
                systemSelect.value = savedSystem;
                // Actually load the saved system instead of just setting the dropdown
                this.loadRomSystem(savedSystem);
            }
        }
        
        // Media preview is now always enabled (no checkbox needed)
        this.mediaPreviewEnabled = true;
        
        // Load partial match modal checkbox state (in LaunchBox Configuration modal)
        if (savedPartialMatchModal !== null) {
            const partialMatchCheckbox = document.getElementById('enablePartialMatchModalModal');
            if (partialMatchCheckbox) {
                partialMatchCheckbox.checked = savedPartialMatchModal === 'true';
            }
        }
        
        // Load force download checkbox state (in LaunchBox Configuration modal)
        if (savedForceDownload !== null) {
            const forceDownloadCheckbox = document.getElementById('forceDownloadImagesModal');
            if (forceDownloadCheckbox) {
                forceDownloadCheckbox.checked = savedForceDownload === 'true';
            }
        }
        
        // Load overwrite text fields checkbox state (in LaunchBox Configuration modal)
        const overwriteTextFieldsCheckbox = document.getElementById('overwriteTextFieldsLaunchbox');
        if (overwriteTextFieldsCheckbox) {
            if (savedOverwriteTextFields !== null) {
                overwriteTextFieldsCheckbox.checked = savedOverwriteTextFields === 'true';
            } else {
                // No saved value, set to default (unchecked)
                overwriteTextFieldsCheckbox.checked = false;
            }
        }
    }

    setCookie(name, value) {
        // For large values (like AG Grid state), use localStorage instead of cookies
        if (name === 'mainGridState' || name === 'taskGridState') {
            try {
                localStorage.setItem(name, value);
                return;
            } catch (error) {
                // Fallback to cookie if localStorage fails
            }
        }
        
        // Debug logging for LaunchBox overwrite text fields
        if (name === 'launchboxOverwriteTextFields') {
        }
        
        // Ensure value is not undefined or null
        if (value === undefined || value === null) {
            value = '';
        }
        
        // Convert to string if it's not already
        const stringValue = String(value);
        
        // Check cookie size limits
        const encodedValue = encodeURIComponent(stringValue);
        
        if (encodedValue.length > 4000) {
        }
        
        // Set the cookie with proper encoding
        document.cookie = `${name}=${encodedValue}; path=/; max-age=31536000`;
    }

    getCookie(name) {
        // For large values (like AG Grid state), check localStorage first
        if (name === 'mainGridState' || name === 'taskGridState') {
            try {
                const localValue = localStorage.getItem(name);
                if (localValue) {
                    return localValue;
                }
            } catch (error) {
            }
        }
        
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            const cookieValue = parts.pop().split(';').shift();
            if (cookieValue) {
                try {
                    return decodeURIComponent(cookieValue);
                } catch (e) {
                    return cookieValue; // Return raw value if decoding fails
                }
            }
        }
        return null;
    }

    async showPartialMatches(gameName, preloadedMatches = null, modalType = 'global', gamePath = null) {
        try {
            
            // Set modal as open for state management
            this.isModalOpen = true;
            
            if (preloadedMatches) {
                // Use pre-loaded matches (from multi-game selection)
                // Show the modal first, then populate content
                this.showModalWithLoading(gameName, modalType);
                document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
                this.displayPartialMatchModal(gameName, preloadedMatches, modalType, gamePath);
            } else {
                // Fetch matches from API (single game mode)
                this.showModalWithLoading(gameName, modalType);
                
                const systemName = modalType === 'gameEdit' ? this.currentModalData.system : this.currentSystem;
                const response = await fetch('/api/get-top-matches', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ game_name: gameName, system_name: systemName })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // Hide loading spinner and display matches
                    document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
                    this.displayPartialMatchModal(gameName, data.matches, modalType, gamePath);
                } else {
                    // Hide loading spinner and show error
                    document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
                    this.showAlert('Error getting matches: ' + data.error, 'danger');
                    // Reset modal state on error
                    this.isModalOpen = false;
                }
            }
        } catch (error) {
            // Hide loading spinner and show error
            document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
            this.showAlert('Error getting matches: ' + error.message, 'danger');
            // Reset modal state on error
            this.isModalOpen = false;
        }
    }

    showModalWithLoading(gameName, modalType = 'global') {
        
        // Set original game name
        if (modalType === 'gameEdit') {
            document.getElementById('gameEditOriginalGameNameInput').value = gameName;
        } else {
            document.getElementById('globalOriginalGameName').textContent = gameName;
        }
        
        // Show progress if processing multiple games (only for global modal)
        if (modalType === 'global' && this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1) {
            const progressText = `Game ${this.currentBestMatchIndex + 1} of ${this.pendingBestMatchResults.length}`;
            const progressElement = document.getElementById('globalModalProgress');
            if (progressElement) {
                progressElement.textContent = progressText;
                progressElement.style.display = 'block';
            }
        }
        
        // Clear previous content
        const matchesListId = modalType === 'gameEdit' ? 'gameEditMatchesList' : 'globalMatchesList';
        document.getElementById(matchesListId).innerHTML = '';
        
        // Show loading spinner
        const loadingSpinnerId = modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner';
        document.getElementById(loadingSpinnerId).style.display = 'block';
        
        // Show the modal
        const modalId = modalType === 'gameEdit' ? 'gameEditMatchModal' : 'globalMatchModal';
        const modalElement = document.getElementById(modalId);
        if (!modalElement) {
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        
        // Only add event listener once
        if (!this.modalEventListenersAdded) {
            modalElement.addEventListener('hidden.bs.modal', () => {
                
                // Check if we're in multi-game mode and this is not the last game
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1 && this.currentBestMatchIndex < this.pendingBestMatchResults.length - 1) {
                    return;
                }
                
                // If we're on the last game or single game, allow normal modal closure
                
                // Force reset all state to prevent UI from getting stuck
                this.resetUIState();
                
            });
            this.modalEventListenersAdded = true;
        }
        
        // Ensure the cancel button works by adding a direct click handler
        const cancelBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
        if (cancelBtn) {
            // Remove any existing click handlers to prevent duplicates
            cancelBtn.replaceWith(cancelBtn.cloneNode(true));
            const freshCancelBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
            freshCancelBtn.addEventListener('click', () => {
                modal.hide();
            });
        }
        
        // Show the modal
        modal.show();
        
        // Add direct event listener to close button to ensure state is reset
        const closeBtn = modalElement.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.isModalOpen = false;
                this.resetUIState();
            });
        }
        
    }

    displayPartialMatchModal(originalGameName, matches, modalType = 'global', originalGamePath = null) {
        
        // Show/hide navigation buttons based on modal type and whether we're processing multiple games
        if (modalType === 'global') {
            const nextGameBtn = document.getElementById('globalNextGameBtn');
            const prevGameBtn = document.getElementById('globalPrevGameBtn');
            
            if (nextGameBtn) {
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1 && this.currentBestMatchIndex < this.pendingBestMatchResults.length - 1) {
                    nextGameBtn.style.display = 'inline-block';
                    nextGameBtn.onclick = () => this.moveToNextGame();
                } else {
                    nextGameBtn.style.display = 'none';
                    if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1) {
                    } else {
                    }
                }
            }
            
            if (prevGameBtn) {
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1 && this.currentBestMatchIndex > 0) {
                    prevGameBtn.style.display = 'inline-block';
                    prevGameBtn.onclick = () => this.moveToPrevGame();
                } else {
                    prevGameBtn.style.display = 'none';
                }
            }
        }
        
        // Find the original game data to display details
        // Use path (unique identifier) - no fallback to name as names are not unique
        const originalGame = originalGamePath ? 
            this.games.find(game => game.path === originalGamePath) : null;
        
        // Set element IDs based on modal type
        const publisherId = modalType === 'gameEdit' ? 'gameEditOriginalGamePublisher' : 'globalOriginalGamePublisher';
        const developerId = modalType === 'gameEdit' ? 'gameEditOriginalGameDeveloper' : 'globalOriginalGameDeveloper';
        const romFileId = modalType === 'gameEdit' ? 'gameEditOriginalGameRomFile' : 'globalOriginalGameRomFile';
        const releaseDateId = modalType === 'gameEdit' ? 'gameEditOriginalGameReleaseDate' : 'globalOriginalGameReleaseDate';
        
        if (originalGame) {
            // Populate original game details
            document.getElementById(publisherId).textContent = originalGame.publisher || 'N/A';
            document.getElementById(developerId).textContent = originalGame.developer || 'N/A';
            document.getElementById(romFileId).textContent = originalGame.path || 'N/A';
            
            // Try to extract release date from various fields
            let releaseDate = 'N/A';
            if (originalGame.releaseDate) {
                releaseDate = originalGame.releaseDate;
            } else if (originalGame.date) {
                releaseDate = originalGame.date;
            } else if (originalGame.year) {
                releaseDate = originalGame.year;
            }
            document.getElementById(releaseDateId).textContent = releaseDate;
        } else {
            // Clear fields if game not found
            document.getElementById(publisherId).textContent = 'N/A';
            document.getElementById(developerId).textContent = 'N/A';
            document.getElementById(romFileId).textContent = 'N/A';
            document.getElementById(releaseDateId).textContent = 'N/A';
        }
        
        // Store for later use
        this.currentMatches = matches;
        this.currentOriginalGameName = originalGameName;
        this.currentOriginalGamePath = originalGamePath;
        this.selectedMatchIndex = -1;
        
        // Clear previous matches
        const matchesListId = modalType === 'gameEdit' ? 'gameEditMatchesList' : 'globalMatchesList';
        const matchesList = document.getElementById(matchesListId);
        matchesList.innerHTML = '';
        
        // Generate match cards (async)
        this.createMatchCards(matches, matchesList);
        
        // Apply button is no longer needed - using double-click instead
        
    }

    createMatchCards(matches, matchesList) {
        // Create match cards synchronously
        for (let i = 0; i < matches.length; i++) {
            const matchCard = this.createMatchCard(matches[i], i);
            matchesList.appendChild(matchCard);
        }
    }

    createMatchCard(match, index) {
        
        const scoreClass = match.score >= 0.9 ? 'bg-success' : 
                          match.score >= 0.7 ? 'bg-warning' : 'bg-danger';
        
        const matchTypeIcon = match.match_type === 'alternate' ? 
            '<i class="bi bi-arrow-repeat text-info" title="Matched via alternate name"></i>' : 
            '<i class="bi bi-check-circle text-success" title="Matched via main name"></i>';
        
        // Use box image URL directly from backend
        let boxImageHtml = '';
        if (match.box_image_url) {
            boxImageHtml = `
                <div class="mb-2 text-center">
                    <img src="${match.box_image_url}" class="img-fluid rounded" style="max-height: 200px; width: auto;" 
                         onerror="handleLaunchboxImageError(this)" 
                         onload="" 
                         alt="Game box art" loading="lazy">
                </div>
            `;
        } else {
            boxImageHtml = `
                <div class="mb-2 text-center">
                    <div class="d-flex align-items-center justify-content-center" style="height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;">
                        <div class="text-muted">
                            <i class="bi bi-image" style="font-size: 2rem;"></i>
                            <div class="small">No box art available</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        const card = document.createElement('div');
        card.className = 'col-md-6 mb-3';
        card.innerHTML = `
            <div class="card match-card" data-match-index="${index}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">${match.matched_name}</h6>
                    <div>
                        ${matchTypeIcon}
                        <span class="badge ${scoreClass}">${(match.score * 100).toFixed(1)}%</span>
                    </div>
                </div>
                ${boxImageHtml}
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p class="card-text">
                                <strong>Main Name:</strong> ${match.name || 'N/A'}<br>
                                <strong>Developer:</strong> ${match.developer || 'N/A'}<br>
                                <strong>Publisher:</strong> ${match.publisher || 'N/A'}<br>
                                <strong>Genre:</strong> ${match.genre || 'N/A'}
                            </p>
                        </div>
                        <div class="col-md-6">
                            <p class="card-text">
                                <strong>Rating:</strong> ${match.rating || 'N/A'}<br>
                                <strong>Players:</strong> ${match.players || 'N/A'}<br>
                                <strong>Database ID:</strong> ${match.database_id || 'N/A'}
                            </p>
                        </div>
                    </div>
                    ${match.overview ? `<p class="card-text"><strong>Description:</strong> ${match.overview.substring(0, 200)}${match.overview.length > 200 ? '...' : ''}</p>` : ''}
                </div>
            </div>
        `;
        
        // Add click handler for match selection (visual feedback only)
        card.addEventListener('click', (e) => {
            // Remove previous selection
            document.querySelectorAll('.match-card').forEach(c => c.classList.remove('selected'));
            
            // Mark as selected
            card.classList.add('selected');
            this.selectedMatchIndex = index;
            
        });
        
        // Add double-click handler to apply the match
        card.addEventListener('dblclick', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // Set the selected match
            this.selectedMatchIndex = index;
            
            // Apply the match directly
            this.applySelectedMatch(this.currentModalContext || 'global');
            
        });
        
        return card;
    }

    async applySelectedMatch(modalType = 'global') {
        
        if (this.selectedMatchIndex === -1) {
            return;
        }
        
        if (!this.currentMatches || !Array.isArray(this.currentMatches)) {
            this.showAlert('Error: No matches available', 'danger');
            return;
        }
        
        if (this.selectedMatchIndex >= this.currentMatches.length) {
            this.showAlert('Error: Invalid match selection', 'danger');
            return;
        }
        
        const selectedMatch = this.currentMatches[this.selectedMatchIndex];
        const originalGameName = this.currentOriginalGameName;

        try {
            // Check if we're in multi-game mode
            if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1) {
                // Check if this is the last game
                if (this.currentBestMatchIndex >= this.pendingBestMatchResults.length - 1) {
                    // Last game - apply match and close modal
                    await this.applyRegularMatch(selectedMatch, originalGameName, true, modalType, this.currentOriginalGamePath);
                    
                    // Reset multi-game state
                    this.pendingBestMatchResults = null;
                    this.currentBestMatchIndex = 0;
                    
                    // Force refresh the UI state and reset any stuck state
                    setTimeout(() => {
                        this.refreshGameGrid();
                        this.resetUIState();
                        
                        // Force close the modal and clean up any remaining state
                        const modalElement = document.getElementById('partialMatchModal');
                        if (modalElement) {
                            const modal = bootstrap.Modal.getInstance(modalElement);
                            if (modal) {
                                modal.hide();
                            }
                            // Remove any backdrop or modal-related classes
                            modalElement.classList.remove('show');
                            document.body.classList.remove('modal-open');
                            const backdrop = document.querySelector('.modal-backdrop');
                            if (backdrop) {
                                backdrop.remove();
                            }
                        }
                    }, 100);
                } else {
                    // Not the last game - apply match and move to next
                    await this.applyRegularMatch(selectedMatch, originalGameName, false, modalType, this.currentOriginalGamePath);
                    this.moveToNextGame();
                }
            } else {
                // Single game mode - close modal normally
                await this.applyRegularMatch(selectedMatch, originalGameName, true, modalType, this.currentOriginalGamePath);
            }
            
        } catch (error) {
            this.showAlert('Error applying match: ' + error.message, 'danger');
        }
    }
    
    
    async applyRegularMatch(selectedMatch, originalGameName, closeModal = true, modalType = 'global', originalGamePath = null) {
        try {
            let gameIndex;
            
            // Find the game in our data
            if (modalType === 'gameEdit' && this.editingGameIndex >= 0) {
                // Use editingGameIndex for game edit modal (more reliable than name)
                gameIndex = this.editingGameIndex;
                if (gameIndex >= this.games.length) {
                    this.showAlert('Game index out of bounds', 'danger');
                    return;
                }
            } else {
                // Use path search for other contexts (scraping, etc.) - path is unique identifier
                if (originalGamePath) {
                    // Use path (unique identifier)
                    gameIndex = this.games.findIndex(game => game.path === originalGamePath);
                } else {
                    // No fallback to name - path is required for reliable identification
                    this.showAlert('Game path not provided - cannot identify game reliably', 'danger');
                    return;
                }
                if (gameIndex === -1) {
                    this.showAlert('Original game not found', 'danger');
                    return;
                }
            }
            
            // Update game data with selected match
            const originalGame = this.games[gameIndex];
            const updatedGame = { ...originalGame };
            
            // Apply fields from the match
            if (modalType === 'gameEdit') {
                // When called from game edit modal, only update launchboxid
                if (selectedMatch.database_id) updatedGame.launchboxid = selectedMatch.database_id;
            } else {
                // When called from other contexts (scraping, etc.), update all fields
                if (selectedMatch.name) updatedGame.name = selectedMatch.name;
                if (selectedMatch.overview) updatedGame.desc = selectedMatch.overview;
                if (selectedMatch.developer) updatedGame.developer = selectedMatch.developer;
                if (selectedMatch.publisher) updatedGame.publisher = selectedMatch.publisher;
                if (selectedMatch.genre) updatedGame.genre = selectedMatch.genre;
                if (selectedMatch.rating) updatedGame.rating = selectedMatch.rating;
                if (selectedMatch.players) updatedGame.players = selectedMatch.players;
                if (selectedMatch.database_id) updatedGame.launchboxid = selectedMatch.database_id;
            }
            
            // Update the games array
            this.games[gameIndex] = updatedGame;
            
            // Mark game as modified
            this.markGameAsModified(updatedGame);
            
            // Save changes to backend directly
            await this.saveGameChanges();
            
            // Refresh grid, respecting current filters
            await this.refreshGridData();
            
            // Update edit modal fields if it's open
            this.updateEditModalFields(updatedGame);
            
            // Auto-save changes to server
            try {
                await this.saveGameChanges();
            } catch (error) {
                this.showAlert('Warning: Changes applied but auto-save failed. Please save manually.', 'warning');
            }
            
            // Handle modal closing based on modal type
            if (modalType === 'gameEdit') {
                // For game edit modal, close and return to edit modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('gameEditMatchModal'));
                modal.hide();
                
                // Show success message
                this.showAlert(`Successfully updated "${originalGameName}" with match data and saved to server`, 'success');
            } else {
                // For global modal, check if there are more games
                if (this.pendingBestMatchResults && this.currentBestMatchIndex < this.pendingBestMatchResults.length - 1) {
                    // Move to next game
                    this.moveToNextGame();
                    this.showAlert(`Successfully updated "${originalGameName}" with match data and saved to server`, 'success');
                } else {
                    // Last game, close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('globalMatchModal'));
                    modal.hide();
                    
                    // Show success message
                    this.showAlert(`Successfully updated "${originalGameName}" with match data and saved to server`, 'success');
                }
            }
            
        } catch (error) {
            this.showAlert('Error applying regular match: ' + error.message, 'danger');
        }
    }
    updateEditModalFields(updatedGame) {
        // Check if edit modal is currently open
        const editModal = document.getElementById('editGameModal');
        if (editModal && editModal.classList.contains('show')) {
            // Update form fields with new data
            const nameField = document.getElementById('editName');
            const descField = document.getElementById('editDescription');
            const genreField = document.getElementById('editGenre');
            const developerField = document.getElementById('editDeveloper');
            const publisherField = document.getElementById('editPublisher');
            const ratingField = document.getElementById('editRating');
            const playersField = document.getElementById('editPlayers');
            const launchboxIdField = document.getElementById('editLaunchboxId');
            const youtubeurlField = document.getElementById('editYoutubeurl');
            
            if (nameField && updatedGame.name) nameField.value = updatedGame.name;
            if (descField && updatedGame.desc) descField.value = updatedGame.desc;
            if (genreField && updatedGame.genre) genreField.value = updatedGame.genre;
            if (developerField && updatedGame.developer) developerField.value = updatedGame.developer;
            if (publisherField && updatedGame.publisher) publisherField.value = updatedGame.publisher;
            if (ratingField && updatedGame.rating) ratingField.value = updatedGame.rating;
            if (playersField && updatedGame.players) playersField.value = updatedGame.players;
            if (launchboxIdField && updatedGame.launchboxid) launchboxIdField.value = updatedGame.launchboxid;
            if (youtubeurlField && updatedGame.youtubeurl) youtubeurlField.value = updatedGame.youtubeurl;
            
        }
    }

    async loadAvailableSystems() {
        console.log('loadAvailableSystems called');
        try {
            console.log('Fetching from /api/rom-systems...');
            const response = await fetch('/api/rom-systems', {
                credentials: 'same-origin'
            });
            console.log('Response status:', response.status);
            if (response.ok) {
                const systems = await response.json();
                console.log('Systems received:', systems);
                this.populateSystemDropdown(systems);
            } else {
                console.error('Response not ok:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error loading available systems:', error);
        }
    }

    populateSystemDropdown(systems) {
        console.log('populateSystemDropdown called with:', systems);
        // Store systems data
        this.allSystems = systems || [];
        this.selectedSystem = null;
        console.log('Stored systems:', this.allSystems.length);
        
        // Update Select2 with new systems
        this.updateSelect2Options();
    }
    
    initializeSelect2() {
        const selectElement = document.getElementById('systemSelect');
        
        if (!selectElement) {
            return;
        }

        // Check if jQuery and Select2 are available
        if (typeof $ === 'undefined' || typeof $.fn.select2 === 'undefined') {
            console.warn('jQuery or Select2 not available, retrying in 100ms...');
            setTimeout(() => this.initializeSelect2(), 100);
            return;
        }

        // Initialize Select2
        this.select2Instance = $(selectElement).select2({
            placeholder: 'Select System...',
            allowClear: true,
            width: '300px',
            dropdownAutoWidth: true,
            language: {
                noResults: function() {
                    return "No systems found";
                }
            }
        });
        
        // Handle selection change
        $(selectElement).on('select2:select', (e) => {
            const value = e.params.data.id;
            if (value) {
                const system = this.allSystems.find(s => s.name === value);
                if (system) {
                    this.selectSystem(system);
                }
            }
        });
        
        // Handle clearing selection
        $(selectElement).on('select2:clear', () => {
            this.selectedSystem = null;
            localStorage.removeItem('selectedSystem');
        });
        
    }
    
    updateSelect2Options() {
        console.log('updateSelect2Options called, select2Instance:', this.select2Instance);
        
        // Check if jQuery and Select2 are available
        if (typeof $ === 'undefined' || typeof $.fn.select2 === 'undefined') {
            console.warn('jQuery or Select2 not available in updateSelect2Options, retrying in 100ms...');
            setTimeout(() => this.updateSelect2Options(), 100);
            return;
        }
        
        if (!this.select2Instance) {
            console.log('Select2 instance not found, trying to initialize...');
            this.initializeSelect2();
            if (!this.select2Instance) {
                console.error('Failed to initialize Select2');
                return;
            }
        }

        const selectElement = document.getElementById('systemSelect');
        console.log('Select element found:', selectElement);
        
        // Clear existing options
        $(selectElement).empty();
        $(selectElement).append('<option value="">Select System...</option>');
        
        // Add system options grouped by ROM count
        if (this.allSystems && this.allSystems.length > 0) {
            // Sort systems: those with ROMs first, then those without
            const systemsWithRoms = this.allSystems.filter(system => system.rom_count > 0);
            const systemsWithoutRoms = this.allSystems.filter(system => system.rom_count === 0);
            
            // Add systems with ROMs group
            if (systemsWithRoms.length > 0) {
                $(selectElement).append('<optgroup label="Systems with ROMs">');
                systemsWithRoms.forEach(system => {
                    $(selectElement).append(`<option value="${system.name}">${system.name} (${system.rom_count} games)</option>`);
                });
                $(selectElement).append('</optgroup>');
            }
            
            // Add systems without ROMs group
            if (systemsWithoutRoms.length > 0) {
                $(selectElement).append('<optgroup label="Empty Systems">');
                systemsWithoutRoms.forEach(system => {
                    $(selectElement).append(`<option value="${system.name}">${system.name} (${system.rom_count} games)</option>`);
                });
                $(selectElement).append('</optgroup>');
            }
        }
        
        // Restore previously selected system
        const savedSystem = localStorage.getItem('selectedSystem');
        if (savedSystem) {
            // Check if the saved system exists in the current systems list
            const systemExists = this.allSystems.some(system => system.name === savedSystem);
            if (systemExists) {
                $(selectElement).val(savedSystem).trigger('change');
                // Find and set the selected system object
                const system = this.allSystems.find(s => s.name === savedSystem);
                if (system) {
                    this.selectedSystem = system;
                }
            } else {
                // Clear saved system if it no longer exists
                localStorage.removeItem('selectedSystem');
            }
        }
        
        // Trigger change to update Select2
        $(selectElement).trigger('change');
    }
    
    selectSystem(system) {
        this.selectedSystem = system;
        
        // Save the selected system to localStorage
        if (system) {
            localStorage.setItem('selectedSystem', system.name);
        } else {
            localStorage.removeItem('selectedSystem');
        }
        
        // Dispatch custom event for system selection
        const event = new CustomEvent('systemSelected', {
            detail: { system: system }
        });
        document.dispatchEvent(event);
    }

    focusFirstRow() {
        // Focus on the first row of the grid
        if (this.gridApi && this.games && this.games.length > 0) {
            try {
                // Get the first row node
                const firstRowNode = this.gridApi.getRowNode(0);
                if (firstRowNode) {
                    // Select the first row
                    this.gridApi.setRowNodeExpanded(firstRowNode, true);
                    this.gridApi.selectNode(firstRowNode);
                    
                    // Ensure the first row is visible
                    this.gridApi.ensureIndexVisible(0);
                    
                    // Focus on the first cell of the first row
                    this.gridApi.setFocusedCell(0, 'name');
                    
                }
            } catch (error) {
            }
        }
    }

    // YouTube Download Methods
    initializeYouTubeDownload(game) {
        const youtubeBtn = document.getElementById('youtubeDownloadBtn');
        if (youtubeBtn) {
            // Remove existing event listeners
            const newBtn = youtubeBtn.cloneNode(true);
            youtubeBtn.parentNode.replaceChild(newBtn, youtubeBtn);
            
            // Add event listener
            newBtn.addEventListener('click', () => {
                this.openYouTubeSearchModal(game);
            });
        }
    }

    openYouTubeSearchModal(game) {
        // Store the current game for YouTube operations
        this.currentYouTubeGame = game;

        // Set game name for search
        document.getElementById('youtubeGameName').textContent = game.name;
        
        // Pre-fill search input with game name and system name
        const searchQuery = `${game.name} ${this.currentSystem}`;
        document.getElementById('youtubeSearchInput').value = searchQuery;
        
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('youtubeSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        modal.show();
        
        // Initialize search functionality
        this.initializeYouTubeSearch();
        
        // Automatically trigger search when modal is shown
        const modalElement = document.getElementById('youtubeSearchModal');
        modalElement.addEventListener('shown.bs.modal', () => {
            this.performYouTubeSearch();
        }, { once: true }); // Use once: true to only trigger once

    }

    initializeYouTubeSearch() {
        const searchBtn = document.getElementById('youtubeSearchBtn');
        const searchInput = document.getElementById('youtubeSearchInput');
        
        if (searchBtn && !searchBtn.hasAttribute('data-listener-attached')) {
            searchBtn.addEventListener('click', () => {
                this.performYouTubeSearch();
            });
            searchBtn.setAttribute('data-listener-attached', 'true');
        }
        
        if (searchInput && !searchInput.hasAttribute('data-listener-attached')) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performYouTubeSearch();
                }
            });
            searchInput.setAttribute('data-listener-attached', 'true');
        }
    }

    async performYouTubeSearch() {
        const query = document.getElementById('youtubeSearchInput').value.trim();
        if (!query) {
            return;
        }
        
        // Show loading state
        this.showYouTubeLoading(true);
        this.showYouTubeResults(false);
        this.showYouTubeNoResults(false);
        
        try {
            const response = await fetch('/api/youtube/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayYouTubeResults(data.results);
            } else {
                throw new Error('Search failed');
            }
        } catch (error) {
            this.showYouTubeNoResults(true);
        } finally {
            this.showYouTubeLoading(false);
        }
    }

    showYouTubeLoading(show) {
        const loading = document.getElementById('youtubeSearchLoading');
        const results = document.getElementById('youtubeSearchResults');
        
        if (show) {
            loading.classList.remove('d-none');
            results.classList.add('d-none');
        } else {
            loading.classList.add('d-none');
            results.classList.remove('d-none');
        }
    }

    showYouTubeResults(show) {
        const results = document.getElementById('youtubeSearchResults');
        if (show) {
            results.classList.remove('d-none');
        } else {
            results.classList.add('d-none');
        }
    }

    showYouTubeNoResults(show) {
        const noResults = document.getElementById('youtubeNoResults');
        if (show) {
            noResults.classList.remove('d-none');
        } else {
            noResults.classList.add('d-none');
        }
    }

    displayYouTubeResults(results) {
        const container = document.getElementById('youtubeSearchResults');
        container.innerHTML = '';
        
        if (!results || results.length === 0) {
            this.showYouTubeNoResults(true);
            return;
        }
        
        this.showYouTubeResults(true);
        this.showYouTubeNoResults(false);
        
        results.forEach(video => {
            const videoCard = this.createYouTubeVideoCard(video);
            container.appendChild(videoCard);
        });
    }

    createYouTubeVideoCard(video) {
        const card = document.createElement('div');
        card.className = 'col-md-6 col-lg-4';
        
        // Create the card structure
        const cardDiv = document.createElement('div');
        cardDiv.className = 'card youtube-video-card';
        cardDiv.setAttribute('data-video-id', video.id);
        cardDiv.setAttribute('data-video-url', video.url);
        
        // Create the image element
        const img = document.createElement('img');
        img.src = video.thumbnail;
        img.className = 'youtube-video-thumbnail';
        img.alt = video.title;
        
        // Handle image error with a cleaner approach
        img.onerror = function() {
            this.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.style.cssText = 'height:120px;display:flex;align-items:center;justify-content:center;background:#f8f9fa;border-radius:8px 8px 0 0;color:#6c757d;';
            placeholder.innerHTML = '<i class="bi bi-image" style="font-size:2rem;margin-right:0.5rem;"></i>';
            this.parentNode.insertBefore(placeholder, this.nextSibling);
        };
        
        // Create the info container
        const infoDiv = document.createElement('div');
        infoDiv.className = 'youtube-video-info';
        
        // Create title
        const titleDiv = document.createElement('div');
        titleDiv.className = 'youtube-video-title';
        titleDiv.textContent = video.title;
        
        // Create meta container
        const metaDiv = document.createElement('div');
        metaDiv.className = 'youtube-video-meta';
        
        // Create duration
        const durationDiv = document.createElement('div');
        durationDiv.className = 'youtube-video-duration';
        durationDiv.innerHTML = `<i class="bi bi-clock"></i> ${video.duration}`;
        
        // Create views
        const viewsDiv = document.createElement('div');
        viewsDiv.className = 'youtube-video-views';
        viewsDiv.innerHTML = `<i class="bi bi-eye"></i> ${video.view_count || 'Unknown views'}`;
        
        // Create channel
        const channelDiv = document.createElement('div');
        channelDiv.className = 'youtube-video-channel';
        channelDiv.innerHTML = `<i class="bi bi-person-circle"></i> ${video.channel}`;
        
        // Create published time
        const publishedDiv = document.createElement('div');
        publishedDiv.className = 'youtube-video-published';
        publishedDiv.innerHTML = `<i class="bi bi-calendar3"></i> ${video.published_time || 'Unknown date'}`;
        
        // Assemble the structure
        metaDiv.appendChild(durationDiv);
        metaDiv.appendChild(viewsDiv);
        metaDiv.appendChild(channelDiv);
        metaDiv.appendChild(publishedDiv);
        
        infoDiv.appendChild(titleDiv);
        infoDiv.appendChild(metaDiv);
        
        cardDiv.appendChild(img);
        cardDiv.appendChild(infoDiv);
        
        card.appendChild(cardDiv);
        
        // Add click event to open video player
        card.addEventListener('click', () => {
            this.openYouTubePlayerModal(video);
        });
        
        return card;
    }

    openYouTubePlayerModal(video) {
        
        // Close search modal
        const searchModal = bootstrap.Modal.getInstance(document.getElementById('youtubeSearchModal'));
        if (searchModal) {
            searchModal.hide();
        }
        
        // Set video information
        document.getElementById('youtubeVideoTitle').textContent = video.title;
        document.getElementById('youtubeVideoDuration').textContent = `Duration: ${video.duration}`;
        document.getElementById('youtubeVideoChannel').textContent = `Channel: ${video.channel}`;
        
        // Store video data and game context for download
        this.currentYouTubeVideo = {
            ...video,
            game: this.currentYouTubeGame  // Use the stored game object
        };
        
        // Show player modal
        const playerModal = new bootstrap.Modal(document.getElementById('youtubePlayerModal'));
        playerModal.show();
        
        // Wait for modal to be fully visible before initializing player
        setTimeout(() => {
            // Initialize YouTube player
            this.initializeYouTubePlayer(video.url);
            
            // Initialize player controls
            this.initializePlayerControls();
            
        }, 300);
    }

    getCurrentEditingGame() {
        // Get the currently editing game from the edit modal
        if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            return this.games[this.editingGameIndex];
        }
        return null;
    }

    getRomBasename(romPath) {
        // Extract ROM filename without any extension
        if (!romPath) return 'game';
        const filename = romPath.split('/').pop() || romPath.split('\\').pop();
        return filename.replace(/\.[^.]*$/, ''); // Remove any file extension
    }

    initializeYouTubePlayer(videoUrl) {
        // Extract video ID from URL
        const videoId = this.extractYouTubeVideoId(videoUrl);
        if (!videoId) {
            this.showPlayerError('Invalid YouTube URL');
            return;
        }

        // Wait for YouTube IFrame API to be ready
        if (typeof YT === 'undefined' || !YT.Player) {
            this.waitForYouTubeAPI(() => {
                this.createYouTubePlayer(videoId);
            });
        } else {
            this.createYouTubePlayer(videoId);
        }
    }

    waitForYouTubeAPI(callback) {
        // Check if YouTube API is already loaded
        if (typeof YT !== 'undefined' && YT.Player) {
            callback();
            return;
        }
        
        // Wait for YouTube API to load
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max wait
        
        const checkAPI = () => {
            attempts++;
            if (typeof YT !== 'undefined' && YT.Player) {
                callback();
            } else if (attempts < maxAttempts) {
                setTimeout(checkAPI, 100);
            } else {
                this.showPlayerError('YouTube API failed to load');
            }
        };
        
        checkAPI();
    }

    createYouTubePlayer(videoId) {
        try {
            // Clear the player container first
            const playerContainer = document.getElementById('youtubePlayer');
            if (playerContainer) {
                playerContainer.innerHTML = '';
            }

            this.youtubePlayer = new YT.Player('youtubePlayer', {
                height: '100%',
                width: '100%',
                videoId: videoId,
                playerVars: {
                    'playsinline': 1,
                    'controls': 1,
                    'modestbranding': 1,
                    'rel': 0,
                    'origin': window.location.origin
                },
                events: {
                    'onReady': (event) => {
                        // Auto-play the video
                        event.target.playVideo();
                    },
                    'onStateChange': (event) => {
                        // Update current time display
                        if (event.data === YT.PlayerState.PLAYING) {
                            this.updateCurrentTimeDisplay();
                        } else if (event.data === YT.PlayerState.PAUSED || 
                                   event.data === YT.PlayerState.ENDED || 
                                   event.data === YT.PlayerState.STOPPED) {
                            // Clear interval when video is paused, ended, or stopped
                            if (this.currentTimeInterval) {
                                clearInterval(this.currentTimeInterval);
                                this.currentTimeInterval = null;
                            }
                        }
                    },
                    'onError': (event) => {
                        this.showPlayerError('Video playback error: ' + event.data);
                    }
                }
            });

        } catch (error) {
            this.showPlayerError('Failed to create video player');
        }
    }

    showPlayerError(message) {
        const playerContainer = document.getElementById('youtubePlayer');
        if (playerContainer) {
            playerContainer.innerHTML = `
                <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; color: #6c757d;">
                    <div style="text-align: center;">
                        <i class="bi bi-exclamation-triangle" style="font-size: 2rem; margin-bottom: 0.5rem; display: block; color: #dc3545;"></i>
                        <div style="font-weight: bold; margin-bottom: 0.5rem;">Video Player Error</div>
                        <div style="font-size: 0.9rem;">${message}</div>
                    </div>
                </div>
            `;
        }
    }

    extractYouTubeVideoId(url) {
        
        // Handle different YouTube URL formats
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
            /youtube\.com\/watch\?.*v=([^&\n?#]+)/,
            /youtu\.be\/([^?\n]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match && match[1]) {
                const videoId = match[1];
                return videoId;
            }
        }
        
        return null;
    }

    initializePlayerControls() {
        const getTimeBtn = document.getElementById('getCurrentTimeBtn');
        if (getTimeBtn && !getTimeBtn.hasAttribute('data-listener-attached')) {
            getTimeBtn.addEventListener('click', () => {
                this.getCurrentPlayerTime();
            });
            getTimeBtn.setAttribute('data-listener-attached', 'true');
        }
        const downloadBtn = document.getElementById('downloadVideoBtn');
        if (downloadBtn && !downloadBtn.hasAttribute('data-listener-attached')) {
            downloadBtn.addEventListener('click', () => {
                this.downloadYouTubeVideo();
            });
            downloadBtn.setAttribute('data-listener-attached', 'true');
        } else if (!downloadBtn) {
        }
        // Add modal close event listener to cleanup player
        const playerModal = document.getElementById('youtubePlayerModal');
        if (playerModal) {
            // Stop player as soon as modal starts hiding
            playerModal.addEventListener('hide.bs.modal', () => {
                if (this.youtubePlayer && this.youtubePlayer.stopVideo) {
                    try { this.youtubePlayer.stopVideo(); } catch (e) {}
                }
            });
            playerModal.addEventListener('hidden.bs.modal', () => {
                this.cleanupYouTubePlayer();
            });
        }
    }

    cleanupYouTubePlayer() {
        if (this.youtubePlayer && this.youtubePlayer.destroy) {
            try {
                this.youtubePlayer.destroy();
            } catch (error) {
            }
        }
        
        if (this.currentTimeInterval) {
            clearInterval(this.currentTimeInterval);
            this.currentTimeInterval = null;
        }
        
        this.youtubePlayer = null;
        
        // Return to the YouTube search results modal unless suppressed (e.g., during download)
        if (!this.suppressYouTubeSearchReopen) {
            this.returnToYouTubeSearchModal();
        }
        
        // Reset the suppression flag for next time
        this.suppressYouTubeSearchReopen = false;
    }
    
    returnToYouTubeSearchModal() {
        // Clean up any existing backdrops before opening new modal
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Show the YouTube search modal again
        const searchModal = new bootstrap.Modal(document.getElementById('youtubeSearchModal'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        searchModal.show();
    }

    getCurrentPlayerTime() {
        if (this.youtubePlayer && this.youtubePlayer.getCurrentTime) {
            const currentTime = Math.floor(this.youtubePlayer.getCurrentTime());
            document.getElementById('startTimeInput').value = currentTime;
        }
    }

    async autoSearchAndDownload() {
        
        // Get the current game from the edit modal
        const gameName = document.getElementById('editName').value;
        
        if (!gameName) {
            this.showAlert('No game selected', 'error');
            return;
        }
        
        // Create a mock game object for the search
        const game = {
            name: gameName,
            id: this.currentGameId
        };
        
        // Close the current modal and open YouTube search
        const editModal = document.getElementById('editGameModal');
        if (editModal) {
            const modal = bootstrap.Modal.getInstance(editModal);
            if (modal) {
                modal.hide();
            }
        }
        
        // Wait a bit for modal to close, then open YouTube search
        setTimeout(() => {
            this.openYouTubeSearchModal(game);
            // Search will be automatically triggered by the modal's shown.bs.modal event
        }, 300);
    }

    async downloadYouTubeVideo() {
        // Suppress reopening of YouTube search while we transition to tasks
        this.suppressYouTubeSearchReopen = true;
        
        // Stop YouTube player if it's running
        if (this.youtubePlayer && this.youtubePlayer.stopVideo) {
            try {
                this.youtubePlayer.stopVideo();
            } catch (e) {
            }
        }
        
        // Clean up YouTube player resources
        this.cleanupYouTubePlayer();
        
        // Force close all modals first - before any async operations
        try {
            const modalElements = [
                document.getElementById('youtubePlayerModal'),
                document.getElementById('youtubeSearchModal'),
                document.getElementById('editGameModal')
            ];
            modalElements.forEach(modal => {
                if (modal) {
                    modal.classList.remove('show');
                    modal.style.display = 'none';
                    modal.setAttribute('aria-hidden', 'true');
                }
            });
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        } catch (e) {
        }
        
        const startTime = parseInt(document.getElementById('startTimeInput').value) || 0;
        
        if (!this.currentYouTubeVideo) {
            this.showAlert('Missing video information', 'error');
            return;
        }
        
        // Get the current game from the YouTube player modal context
        // We'll use the game that was passed when opening the player modal

        let currentGame = null;
        
        // Try to get game from currentYouTubeVideo first
        if (this.currentYouTubeVideo.game) {
            currentGame = this.currentYouTubeVideo.game;

        }
        // Fallback to currentYouTubeGame
        else if (this.currentYouTubeGame) {
            currentGame = this.currentYouTubeGame;

        }
        // Last resort: try to get from edit modal
        else if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            currentGame = this.games[this.editingGameIndex];

        }
        
        if (!currentGame) {

            this.showAlert('No game context found for YouTube download', 'error');
            return;
        }
        
                                // currentGame object available for debugging if needed
        
        if (!currentGame) {
            this.showAlert('No game selected', 'error');
            return;
        }

        // Check if system is loaded
        if (!this.currentSystem) {
            this.showAlert('No system selected', 'error');
            return;
        }
        
        const romBasename = this.getRomBasename(currentGame.path);
        const outputFilename = `${romBasename}.mp4`;
        
        // Update the YouTube URL field in the game object and edit modal
        if (this.currentYouTubeVideo.url) {
            
            // Update the game object
            currentGame.youtubeurl = this.currentYouTubeVideo.url;
            
            // Update the edit modal field if it's open
            const editModal = document.getElementById('editGameModal');
            if (editModal && editModal.classList.contains('show')) {
                const youtubeurlField = document.getElementById('editYoutubeurl');
                if (youtubeurlField) {
                    youtubeurlField.value = this.currentYouTubeVideo.url;
                }
            }
            
            // Mark the game as modified so changes can be saved
            this.markGameAsModified(currentGame);
            
            // Auto-save the YouTube URL change to gamelist.xml
            try {
                await this.saveGameChanges();
            } catch (error) {
                console.warn('Failed to auto-save YouTube URL change:', error);
            }
        }
        
        // Debug logging

        // Get auto crop setting from checkbox
        const autoCropCheckbox = document.getElementById('autoCropCheckbox');
        const autoCrop = autoCropCheckbox ? autoCropCheckbox.checked : false;
        
        // Create the request body
        const requestBody = {
            video_url: this.currentYouTubeVideo.url,
            start_time: startTime,
            output_filename: outputFilename,
            system_name: this.currentSystem,
            rom_file: currentGame.path,  // Pass the ROM file path directly
            auto_crop: autoCrop  // Include auto crop setting
        };
        
        try {
            const response = await fetch('/api/youtube/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showAlert(`Video download started! ${data.message}`, 'success');
                
                // Ensure suppression remains true until after switching tab
                this.suppressYouTubeSearchReopen = true;
                
                // Switch to task management tab to show download progress
                this.switchToTaskManagementTab();
                
                // After switching, allow reopening in future flows
                setTimeout(() => { this.suppressYouTubeSearchReopen = false; }, 1000);
            } else {
                const errorData = await response.json();
                this.showAlert(`Download failed: ${errorData.error}`, 'error');
                this.suppressYouTubeSearchReopen = false;
            }
        } catch (error) {
            this.showAlert('Download failed: Network error', 'error');
        }
    }
    updateCurrentTimeDisplay() {
        // Update current time display every second while playing
        if (this.currentTimeInterval) {
            clearInterval(this.currentTimeInterval);
        }
        
        this.currentTimeInterval = setInterval(() => {
            if (this.youtubePlayer && this.youtubePlayer.getCurrentTime) {
                const currentTime = Math.floor(this.youtubePlayer.getCurrentTime());
                
                // Auto-update the start time input field
                const startTimeInput = document.getElementById('startTimeInput');
                if (startTimeInput) {
                    startTimeInput.value = currentTime;
                }
            }
        }, 1000);
    }

    // Check for completed YouTube download tasks and refresh grid if needed
    async checkForCompletedYouTubeTasks() {
        if (!this.currentSystem) return;
        try {
            const resp = await fetch('/api/tasks', {
                headers: {
                    'Accept-Encoding': 'gzip, deflate' // Enable compression for task data
                }
            });
            const tasksMap = await resp.json();
            const tasksArray = tasksMap && typeof tasksMap === 'object' ? Object.values(tasksMap) : [];
            const hasCompleted = tasksArray.some(task => task.type === 'youtube_download' && task.status === 'completed');
            const hasGamelistUpdate = tasksArray.some(task => task.type === 'youtube_download' && task.status === 'completed' && Array.isArray(task.progress) && task.progress.some(p => typeof p === 'string' && p.includes('Gamelist.xml updated successfully')));
            if (hasCompleted) {
                await this.loadRomSystem(this.currentSystem);
                if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
                    const currentGame = this.games[this.editingGameIndex];
                    this.showEditGameVideo(currentGame);
                }
            }
        } catch (e) {
        }
    }

    // 2D Box Generator Configuration Functions
    open2DBoxGeneratorConfigModal() {
        this.load2DBoxGeneratorConfig();
        const modal = new bootstrap.Modal(document.getElementById('2DBoxGeneratorConfigModal'));
        modal.show();
    }

    async load2DBoxGeneratorConfig() {
        try {
            // Load media fields from config
            const response = await fetch('/api/config');
            const config = await response.json();
            
            if (response.ok) {
                const mediaFields = config.media_fields || {};
                const boxGeneratorConfig = config['2dboxgenerator'] || {};
                const currentField = boxGeneratorConfig.media_field || 'thumbnail';
                const sourceFields = boxGeneratorConfig.source_fields || {
                    'titlescreen': 'titleshot',
                    'gameplay': 'image',
                    'logo': 'marquee'
                };
                
                // Populate the target media field combobox
                const targetSelect = document.getElementById('boxGeneratorMediaField');
                targetSelect.innerHTML = '';
                
                Object.keys(mediaFields).forEach(field => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = field;
                    if (field === currentField) {
                        option.selected = true;
                    }
                    targetSelect.appendChild(option);
                });
                
                // Populate the source field comboboxes
                const populateSourceField = (selectId, currentValue) => {
                    const select = document.getElementById(selectId);
                    select.innerHTML = '';
                    
                    Object.keys(mediaFields).forEach(field => {
                        const option = document.createElement('option');
                        option.value = field;
                        option.textContent = field;
                        if (field === currentValue) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                };
                
                populateSourceField('boxGeneratorTitlescreenField', sourceFields.titlescreen);
                populateSourceField('boxGeneratorGameplayField', sourceFields.gameplay);
                populateSourceField('boxGeneratorLogoField', sourceFields.logo);
                
                // Update current setting display
                const currentFieldDisplay = document.getElementById('currentBoxGeneratorField');
                currentFieldDisplay.innerHTML = `<span class="badge bg-primary">${currentField}</span>`;
            } else {
                this.showAlert('Error loading configuration', 'error');
            }
        } catch (error) {
            this.showAlert('Error loading configuration', 'error');
        }
    }

    async save2DBoxGeneratorConfig() {
        try {
            const selectedField = document.getElementById('boxGeneratorMediaField').value;
            const titlescreenField = document.getElementById('boxGeneratorTitlescreenField').value;
            const gameplayField = document.getElementById('boxGeneratorGameplayField').value;
            const logoField = document.getElementById('boxGeneratorLogoField').value;
            
            if (!selectedField) {
                this.showAlert('Please select a target media field', 'warning');
                return;
            }
            
            if (!titlescreenField || !gameplayField || !logoField) {
                this.showAlert('Please select all source media fields', 'warning');
                return;
            }
            
            const response = await fetch('/api/config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    '2dboxgenerator': {
                        'media_field': selectedField,
                        'source_fields': {
                            'titlescreen': titlescreenField,
                            'gameplay': gameplayField,
                            'logo': logoField
                        }
                    }
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showAlert('2D Box Generator configuration saved successfully!', 'success');
                
                // Update current setting display
                const currentFieldDisplay = document.getElementById('currentBoxGeneratorField');
                currentFieldDisplay.innerHTML = `<span class="badge bg-primary">${selectedField}</span>`;
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('2DBoxGeneratorConfigModal'));
                modal.hide();
            } else {
                this.showAlert(`Error saving configuration: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showAlert('Error saving configuration', 'error');
        }
    }

    // Favorite and Kidgame Functions
    toggleFavorite() {
        const favoriteIcon = document.getElementById('editFavorite');
        if (favoriteIcon.classList.contains('bi-star-fill')) {
            // Currently favorite, remove it
            favoriteIcon.className = 'bi bi-star text-muted';
            favoriteIcon.style.fontSize = '1.5rem';
            favoriteIcon.style.cursor = 'pointer';
            favoriteIcon.style.transition = 'all 0.2s ease';
            favoriteIcon.title = 'Click to add to favorites';
        } else {
            // Not favorite, make it favorite
            favoriteIcon.className = 'bi bi-star-fill text-warning';
            favoriteIcon.style.fontSize = '1.5rem';
            favoriteIcon.style.cursor = 'pointer';
            favoriteIcon.style.transition = 'all 0.2s ease';
            favoriteIcon.title = 'Click to remove from favorites';
        }
    }

    isFavoriteStarActive() {
        const favoriteStar = document.getElementById('editFavorite');
        if (favoriteStar) {
            return favoriteStar.classList.contains('bi-star-fill');
        }
        return false;
    }

    toggleKidgame() {
        const kidgameIcon = document.getElementById('editKidgame');
        if (kidgameIcon.classList.contains('bi-emoji-smile-fill')) {
            // Currently kid game, remove it
            kidgameIcon.className = 'bi bi-emoji-smile text-muted';
            kidgameIcon.style.fontSize = '1.5rem';
            kidgameIcon.style.cursor = 'pointer';
            kidgameIcon.style.transition = 'all 0.2s ease';
            kidgameIcon.title = 'Click to mark as kid game';
        } else {
            // Not kid game, make it kid game
            kidgameIcon.className = 'bi bi-emoji-smile-fill text-success';
            kidgameIcon.style.fontSize = '1.5rem';
            kidgameIcon.style.cursor = 'pointer';
            kidgameIcon.style.transition = 'all 0.2s ease';
            kidgameIcon.title = 'Click to remove kid game mark';
        }
    }

    isKidgameActive() {
        const kidgameIcon = document.getElementById('editKidgame');
        if (kidgameIcon) {
            return kidgameIcon.classList.contains('bi-emoji-smile-fill');
        }
        return false;
    }


    // Fanart Search Functions
    async openFanartSearchModal(game) {
        const modal = new bootstrap.Modal(document.getElementById('fanartSearchModal'));
        
        // Pre-fill the game name
        document.getElementById('fanartGameName').value = game.name || '';
        
        // Set the current system for the search
        this.currentFanartSearchGame = game;
        this.currentFanartSearchSystem = this.currentSystem;
        
        // Populate fanart scrapers dropdown
        await this.populateFanartScrapersDropdown();
        
        // Show the modal
        modal.show();
    }

    async populateFanartScrapersDropdown() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data) {
                const select = document.getElementById('fanartScraper');
                // Clear existing options except "All Scrapers"
                select.innerHTML = '<option value="all">All Scrapers</option>';
                
                // Add scrapers that have fanart mapping
                Object.keys(data).forEach(scraperName => {
                    const scraperConfig = data[scraperName];
                    // Check if this is a scraper config (has image_type_mappings)
                    if (scraperConfig && typeof scraperConfig === 'object' && scraperConfig.image_type_mappings) {
                        const imageMappings = scraperConfig.image_type_mappings || {};
                        
                        if ('fanart' in imageMappings) {
                            const option = document.createElement('option');
                            option.value = scraperName;
                            option.textContent = scraperName.charAt(0).toUpperCase() + scraperName.slice(1);
                            select.appendChild(option);
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Error loading fanart scrapers:', error);
        }
    }

    async performFanartSearch() {
        const gameName = document.getElementById('fanartGameName').value.trim();
        const scraper = document.getElementById('fanartScraper').value;
        const directMatch = document.getElementById('fanartDirectMatch').checked;
        
        if (!gameName) {
            this.showAlert('Please enter a game name', 'warning');
            return;
        }

        // Show loading state
        document.getElementById('fanartSearchLoading').style.display = 'block';
        document.getElementById('fanartSearchResults').style.display = 'none';

        try {
            const response = await fetch('/api/fanart-search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_name: gameName,
                    system_name: this.currentFanartSearchSystem,
                    scraper: scraper,
                    direct_match: directMatch
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displayFanartSearchResults(result.results);
            } else {
                this.showAlert(`Error searching fanart: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showAlert('Error searching fanart', 'error');
        } finally {
            document.getElementById('fanartSearchLoading').style.display = 'none';
        }
    }

    displayFanartSearchResults(results) {
        const container = document.getElementById('fanartResultsContainer');
        container.innerHTML = '';

        if (results.length === 0) {
            container.innerHTML = '<div class="col-12"><p class="text-muted">No fanart found.</p></div>';
            document.getElementById('fanartSearchResults').style.display = 'block';
            return;
        }

        results.forEach(result => {
            // Create a separate card for each fanart image
            if (result.fanart_urls && result.fanart_urls.length > 0) {
                result.fanart_urls.forEach((url, index) => {
                    const resultCard = document.createElement('div');
                    resultCard.className = 'col-md-4 mb-3';
                    
                    resultCard.innerHTML = `
                        <div class="card">
                            <div class="card-body">
                                <img src="${url}" class="img-fluid rounded mb-2" style="width: 100%; height: 200px; object-fit: cover;" 
                                     alt="Fanart" onerror="this.style.display='none'">
                                <h6 class="card-title">${result.game_name}</h6>
                                <p class="card-text">
                                    <small class="text-muted">
                                        <strong>Scraper:</strong> ${result.scraper}<br>
                                        <strong>System:</strong> ${result.platform || 'Unknown'}<br>
                                        <strong>Similarity:</strong> ${(result.similarity_score * 100).toFixed(1)}%
                                    </small>
                                </p>
                                <div class="d-grid gap-2">
                                    <button class="btn btn-primary btn-sm" onclick="gameManager.downloadSingleFanartImage('${url}', ${JSON.stringify(result).replace(/"/g, '&quot;')}, ${JSON.stringify(this.currentFanartSearchGame).replace(/"/g, '&quot;')})">
                                        <i class="bi bi-download me-1"></i>Download This Fanart
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    container.appendChild(resultCard);
                });
            }
        });

        document.getElementById('fanartSearchResults').style.display = 'block';
    }

    async downloadSingleFanartImage(fanartUrl, fanartResult, game) {
        try {
            const response = await fetch('/api/download-multiscraper-media', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_name: game.name,
                    system_name: this.currentFanartSearchSystem,
                    media_type: 'fanart',
                    media_url: fanartUrl
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showAlert('Fanart downloaded successfully!', 'success');
                
                // Close the fanart search modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('fanartSearchModal'));
                modal.hide();
                
                // Refresh the media preview
                this.showMediaPreview(game);
            } else {
                this.showAlert(`Error downloading fanart: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showAlert('Error downloading fanart', 'error');
        }
    }

    // Google Images Search Functions
    async openGoogleImagesSearchModal(game, mediaType = 'fanart') {
        const modal = new bootstrap.Modal(document.getElementById('googleImagesSearchModal'));
        
        // Pre-fill the game name
        document.getElementById('googleImagesGameName').value = game.name || '';
        
        // Set the current system and media type for the search
        this.currentGoogleImagesSearchGame = game;
        this.currentGoogleImagesSearchSystem = this.currentSystem;
        this.currentGoogleImagesSearchMediaType = mediaType;
        
        // Show the modal
        modal.show();
    }


    async downloadGoogleImage(imageUrl, imageTitle) {
        if (!this.currentGoogleImagesSearchGame || !this.currentGoogleImagesSearchSystem) {
            this.showAlert('No game selected for download', 'error');
            return;
        }

        try {
            this.showAlert('Getting full-size image and downloading...', 'info');
            
            const response = await fetch('/api/download-media-from-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_url: imageUrl,
                    game_name: this.currentGoogleImagesSearchGame.name,
                    system_name: this.currentGoogleImagesSearchSystem,
                    media_type: this.currentGoogleImagesSearchMediaType || 'fanart'
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Full-size image downloaded successfully!', 'success');
                
                // Refresh the game grid to reflect gamelist changes
                this.refreshGameGrid();
                
                // Refresh the media preview to show the new image
                this.showMediaPreview(this.currentGoogleImagesSearchGame);
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('googleImagesSearchModal'));
                if (modal) {
                    modal.hide();
                }
            } else {
                this.showAlert(`Error downloading image: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error downloading Google image:', error);
            this.showAlert('Error downloading image', 'error');
        }
    }

    openGoogleImagesInNewTab() {
        const gameName = document.getElementById('googleImagesGameName').value.trim();
        const aspectRatio = document.getElementById('googleImagesAspectRatio').value;
        
        if (!gameName) {
            this.showAlert('Please enter a game name', 'warning');
            return;
        }

        // Build Google Images search URL
        const searchQuery = encodeURIComponent(gameName);
        let searchUrl = `https://www.google.com/search?q=${searchQuery}&tbm=isch`;
        
        // Add aspect ratio filter if selected
        if (aspectRatio) {
            let filterParam = '';
            switch (aspectRatio) {
                case 'panoramic':
                    filterParam = 'xw';
                    break;
                case 'wide':
                    filterParam = 'w';
                    break;
                case 'portrait':
                    filterParam = 'h';
                    break;
                case 'square':
                    filterParam = 's';
                    break;
            }
            if (filterParam) {
                searchUrl += `&imgar=${filterParam}`;
            }
        }
        
        window.open(searchUrl, '_blank');
    }

    async downloadDirectImageUrl() {
        const imageUrl = document.getElementById('googleImagesDirectUrl').value.trim();
        
        if (!imageUrl) {
            this.showAlert('Please enter an image URL', 'error');
            return;
        }
        
        // Basic URL validation
        if (!imageUrl.startsWith('http://') && !imageUrl.startsWith('https://') && !imageUrl.startsWith('data:image/')) {
            this.showAlert('Please enter a valid image URL (http://, https://, or data:image/)', 'error');
            return;
        }
        
        if (!this.currentGoogleImagesSearchGame || !this.currentGoogleImagesSearchSystem) {
            this.showAlert('No game selected for download', 'error');
            return;
        }

        try {
            this.showAlert('Downloading image from URL...', 'info');
            
            const response = await fetch('/api/download-media-from-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_url: imageUrl,
                    game_name: this.currentGoogleImagesSearchGame.name,
                    system_name: this.currentGoogleImagesSearchSystem,
                    media_type: this.currentGoogleImagesSearchMediaType || 'fanart'
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Image downloaded successfully!', 'success');
                
                // Clear the URL field
                document.getElementById('googleImagesDirectUrl').value = '';
                
                // Refresh the game grid to reflect gamelist changes
                this.refreshGameGrid();
                
                // Refresh the media preview to show the new image
                this.showMediaPreview(this.currentGoogleImagesSearchGame);
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('googleImagesSearchModal'));
                if (modal) {
                    modal.hide();
                }
            } else {
                this.showAlert(`Error downloading image: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error downloading image from URL:', error);
            this.showAlert('Error downloading image', 'error');
        }
    }

    // Marquee Search Functions
    async openMarqueeSearchModal(game) {
        const modal = new bootstrap.Modal(document.getElementById('marqueeSearchModal'));
        
        // Pre-fill the game name
        document.getElementById('marqueeGameName').value = game.name || '';
        
        // Set the current system for the search
        this.currentMarqueeSearchGame = game;
        this.currentMarqueeSearchSystem = this.currentSystem;
        
        // Populate marquee scrapers dropdown
        await this.populateMarqueeScrapersDropdown();
        
        // Clear previous results
        document.getElementById('marqueeSearchResults').style.display = 'none';
        document.getElementById('marqueeResultsContainer').innerHTML = '';
        
        // Show the modal
        modal.show();
    }

    async populateMarqueeScrapersDropdown() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data) {
                const select = document.getElementById('marqueeScraper');
                // Clear existing options except "All Scrapers"
                select.innerHTML = '<option value="all">All Scrapers</option>';
                
                // Add scrapers that have marquee mapping
                Object.keys(data).forEach(scraperName => {
                    const scraperConfig = data[scraperName];
                    // Check if this is a scraper config (has image_type_mappings)
                    if (scraperConfig && typeof scraperConfig === 'object' && scraperConfig.image_type_mappings) {
                        const imageMappings = scraperConfig.image_type_mappings || {};
                        
                        if ('marquee' in imageMappings) {
                            const option = document.createElement('option');
                            option.value = scraperName;
                            option.textContent = scraperName.charAt(0).toUpperCase() + scraperName.slice(1);
                            select.appendChild(option);
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Error populating marquee scrapers dropdown:', error);
        }
    }

    async performMarqueeSearch() {
        const gameName = document.getElementById('marqueeGameName').value.trim();
        const selectedScraper = document.getElementById('marqueeScraper').value;
        const directMatch = document.getElementById('marqueeDirectMatch').checked;
        
        if (!gameName) {
            this.showAlert('Please enter a game name', 'warning');
            return;
        }
        
        // Show loading
        document.getElementById('marqueeSearchLoading').style.display = 'block';
        document.getElementById('marqueeSearchResults').style.display = 'none';
        
        try {
            const response = await fetch('/api/marquee-search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_name: gameName,
                    system_name: this.currentMarqueeSearchSystem,
                    scraper: selectedScraper,
                    direct_match: directMatch
                })
            });
            
            const result = await response.json();
            
            // Hide loading
            document.getElementById('marqueeSearchLoading').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displayMarqueeSearchResults(result.results);
            } else {
                this.showAlert(`Error searching marquee: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            document.getElementById('marqueeSearchLoading').style.display = 'none';
            this.showAlert('Error searching marquee', 'error');
        }
    }

    displayMarqueeSearchResults(results) {
        const container = document.getElementById('marqueeResultsContainer');
        container.innerHTML = '';
        
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-info">No marquee found.</div></div>';
            document.getElementById('marqueeSearchResults').style.display = 'block';
            return;
        }
        
        results.forEach(result => {
            if (result.marquee_urls && result.marquee_urls.length > 0) {
                result.marquee_urls.forEach(url => {
                    const resultCard = document.createElement('div');
                    resultCard.className = 'col-md-4 col-lg-3 mb-3';
                    resultCard.innerHTML = `
                        <div class="card h-100">
                            <div class="card-img-top-container" style="height: 200px; overflow: hidden; background-color: #f8f9fa;">
                                <img src="${url}" class="card-img-top" style="object-fit: contain; height: 100%; width: 100%;" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                                <div class="d-flex align-items-center justify-content-center h-100" style="display: none;">
                                    <div class="text-muted text-center">
                                        <i class="bi bi-image" style="font-size: 2rem;"></i>
                                        <div class="small">Image not available</div>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body d-flex flex-column">
                                <h6 class="card-title">${result.game_name || 'Unknown Game'}</h6>
                                <p class="card-text small text-muted flex-grow-1">
                                    <strong>Scraper:</strong> ${result.scraper || 'Unknown'}<br>
                                    <strong>System:</strong> ${result.platform || 'Unknown'}<br>
                                    <strong>Similarity:</strong> ${(result.similarity_score * 100).toFixed(1)}%
                                </p>
                                <div class="d-grid gap-2">
                                    <button class="btn btn-primary btn-sm" onclick="gameManager.downloadSingleMarqueeImage('${url}', ${JSON.stringify(result).replace(/"/g, '&quot;')}, ${JSON.stringify(this.currentMarqueeSearchGame).replace(/"/g, '&quot;')})">
                                        <i class="bi bi-download me-1"></i>Download This Marquee
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    container.appendChild(resultCard);
                });
            }
        });

        document.getElementById('marqueeSearchResults').style.display = 'block';
    }

    async downloadSingleMarqueeImage(marqueeUrl, marqueeResult, game) {
        try {
            const response = await fetch('/api/download-multiscraper-media', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_name: game.name,
                    system_name: this.currentMarqueeSearchSystem,
                    media_type: 'marquee',
                    media_url: marqueeUrl
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showAlert('Marquee downloaded successfully!', 'success');
                
                // Close the marquee search modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('marqueeSearchModal'));
                modal.hide();
                
                // Refresh the media preview
                this.showMediaPreview(game);
            } else {
                this.showAlert(`Error downloading marquee: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showAlert('Error downloading marquee', 'error');
        }
    }
    
    async testIgdbConnection() {
        const clientId = document.getElementById('igdbClientId').value.trim();
        const clientSecret = document.getElementById('igdbClientSecret').value.trim();
        
        if (!clientId || !clientSecret) {
            this.showAlert('Please enter both Client ID and Client Secret', 'warning');
            return;
        }
        
        // Disable button and show loading state
        const testBtn = document.getElementById('testIgdbConnectionBtn');
        const originalText = testBtn.innerHTML;
        testBtn.disabled = true;
        testBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Testing...';
        
        try {
            const response = await fetch('/api/test-igdb-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    client_id: clientId,
                    client_secret: clientSecret
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.showAlert('IGDB connection test successful!', 'success');
            } else {
                this.showAlert(`IGDB connection test failed: ${data.error || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            this.showAlert(`IGDB connection test failed: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            testBtn.disabled = false;
            testBtn.innerHTML = originalText;
        }
    }
    
    async testScreenscraperConnection() {
        const ssId = document.getElementById('screenscraperSsId').value.trim();
        const ssPassword = document.getElementById('screenscraperSsPassword').value.trim();
        
        if (!ssId || !ssPassword) {
            this.showAlert('Please enter both SS ID and SS Password', 'warning');
            return;
        }
        
        // Disable button and show loading state
        const testBtn = document.getElementById('testScreenscraperConnectionBtn');
        const originalText = testBtn.innerHTML;
        testBtn.disabled = true;
        testBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Testing...';
        
        try {
            const response = await fetch('/api/test-screenscraper-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ss_id: ssId,
                    ss_password: ssPassword
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.showAlert('ScreenScraper connection test successful!', 'success');
            } else {
                this.showAlert(`ScreenScraper connection test failed: ${data.error || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            this.showAlert(`ScreenScraper connection test failed: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            testBtn.disabled = false;
            testBtn.innerHTML = originalText;
        }
    }
    
    async testSteamgriddbConnection() {
        // Check if we have credentials configured
        const apiKeyInput = document.getElementById('steamgriddbApiKey');
        const apiKey = apiKeyInput.value.trim();
        
        // If the field contains dots, it means credentials are configured but hidden
        if (apiKey.includes('•')) {
            // Get the real API key from the backend
            try {
                const response = await fetch('/api/steamgriddb-credentials?include_key=true');
                const data = await response.json();
                
                if (data.success && data.has_credentials && data.api_key) {
                    // Use the real API key from the backend
                    await this.testSteamgriddbConnectionWithKey(data.api_key);
                } else {
                    this.showAlert('No API key configured. Please enter your API key first.', 'warning');
                }
            } catch (error) {
                this.showAlert('Error retrieving API key. Please enter your API key manually.', 'warning');
            }
        } else if (!apiKey) {
            this.showAlert('Please enter API Key', 'warning');
            return;
        } else {
            // Use the manually entered API key
            await this.testSteamgriddbConnectionWithKey(apiKey);
        }
    }
    
    async testSteamgriddbConnectionWithKey(apiKey) {
        // Disable button and show loading state
        const testBtn = document.getElementById('testSteamgriddbConnectionBtn');
        const originalText = testBtn.innerHTML;
        testBtn.disabled = true;
        testBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Testing...';
        
        try {
            const response = await fetch('/api/test-steamgriddb-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_key: apiKey
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.showAlert('SteamGridDB connection test successful!', 'success');
            } else {
                this.showAlert(`SteamGridDB connection test failed: ${data.error || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            this.showAlert(`SteamGridDB connection test failed: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            testBtn.disabled = false;
            testBtn.innerHTML = originalText;
        }
    }
    
    // Image Context Menu and Rotation Methods
    initializeImageContextMenu() {
        // Hide context menu when clicking elsewhere
        document.addEventListener('click', (e) => {
            const contextMenu = document.getElementById('imageContextMenu');
            if (contextMenu && !contextMenu.contains(e.target)) {
                contextMenu.style.display = 'none';
            }
        });
        
        // Prevent context menu on right-click elsewhere
        document.addEventListener('contextmenu', (e) => {
            const contextMenu = document.getElementById('imageContextMenu');
            if (contextMenu && !contextMenu.contains(e.target)) {
                contextMenu.style.display = 'none';
            }
        });
    }
    
    showImageContextMenu(event, imageElement, game, field) {
        event.preventDefault();
        event.stopPropagation();
        
        const contextMenu = document.getElementById('imageContextMenu');
        if (!contextMenu) return;
        
        // Store current image info for rotation
        this.currentRotatingImage = {
            element: imageElement,
            game: game,
            field: field
        };
        
        // Position the context menu
        const x = event.clientX;
        const y = event.clientY;
        
        contextMenu.style.left = x + 'px';
        contextMenu.style.top = y + 'px';
        contextMenu.style.display = 'block';
        
        // Adjust position if menu goes off screen
        const rect = contextMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            contextMenu.style.left = (x - rect.width) + 'px';
        }
        if (rect.bottom > window.innerHeight) {
            contextMenu.style.top = (y - rect.height) + 'px';
        }
    }
    
    rotateImage(direction) {
        if (!this.currentRotatingImage) return;
        
        const { element, game, field } = this.currentRotatingImage;
        const img = element.querySelector('img');
        if (!img) return;
        
        // Add rotating class for smooth transition
        img.classList.add('rotating-image');
        
        // Get current rotation
        let currentRotation = 0;
        if (img.classList.contains('rotate-90')) currentRotation = 90;
        else if (img.classList.contains('rotate-180')) currentRotation = 180;
        else if (img.classList.contains('rotate-270')) currentRotation = 270;
        
        // Calculate new rotation
        let newRotation;
        if (direction === 'left') {
            newRotation = (currentRotation - 90 + 360) % 360;
        } else {
            newRotation = (currentRotation + 90) % 360;
        }
        
        // Remove old rotation classes
        img.classList.remove('rotate-90', 'rotate-180', 'rotate-270');
        
        // Add new rotation class
        if (newRotation === 90) {
            img.classList.add('rotate-90');
        } else if (newRotation === 180) {
            img.classList.add('rotate-180');
        } else if (newRotation === 270) {
            img.classList.add('rotate-270');
        }
        
        // Hide context menu
        const contextMenu = document.getElementById('imageContextMenu');
        if (contextMenu) {
            contextMenu.style.display = 'none';
        }
        
        // Show success message
        this.showAlert(`Image rotated ${direction === 'left' ? 'left' : 'right'}`, 'success');
    }
}

// Handle Steam image loading with fallback
function handleSteamImageError(img, fallbackUrl) {
    
    // Prevent infinite loop
    if (img.onerror === null) {
        return;
    }
    
    // If we have a fallback URL, try it
    if (fallbackUrl && fallbackUrl.trim() !== '') {
        img.onerror = null; // Prevent infinite loop
        img.src = fallbackUrl;
        return;
    }
    
    // If no fallback or fallback also failed, show placeholder
    img.onerror = null;
    img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDIwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0xMDAgMTUwTDEyMCAxNzBIMTAwVjE1MFoiIGZpbGw9IiNEOUQ5RDkiLz4KPHBhdGggZD0iTTEwMCAxNTBMMTgwIDEzMEgxMDBWMTUwWiIgZmlsbD0iI0Q5RDlEOSIvPgo8dGV4dCB4PSIxMDAiIHk9IjIwMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzk5OTk5OSIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0Ij5JbWFnZSBub3QgZm91bmQ8L3RleHQ+Cjwvc3ZnPgo=';
    img.alt = 'Image not found';
}

// Handle ScreenScraper image loading errors
function handleScreenscraperImageError(img) {
    
    // Prevent infinite loop
    if (img.onerror === null) {
        return;
    }
    
    // Show placeholder
    img.onerror = null;
    img.style.display = 'none';
    
    // Create placeholder div
    const placeholder = document.createElement('div');
    placeholder.className = 'd-flex align-items-center justify-content-center';
    placeholder.style.cssText = 'height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;';
    placeholder.innerHTML = `
        <div class="text-muted">
            <i class="bi bi-image" style="font-size: 2rem;"></i>
            <div class="small">Box art not available</div>
        </div>
    `;
    
    // Replace the image with placeholder
    img.parentNode.replaceChild(placeholder, img);
}

// Handle SteamGridDB image loading errors
function handleSteamgridImageError(img) {
    
    // Prevent infinite loop
    if (img.onerror === null) {
        return;
    }
    
    // Show placeholder
    img.onerror = null;
    img.style.display = 'none';
    
    // Create placeholder div
    const placeholder = document.createElement('div');
    placeholder.className = 'd-flex align-items-center justify-content-center';
    placeholder.style.cssText = 'height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;';
    placeholder.innerHTML = `
        <div class="text-muted">
            <i class="bi bi-image" style="font-size: 2rem;"></i>
            <div class="small">Grid art not available</div>
        </div>
    `;
    
    // Replace the image with placeholder
    img.parentNode.replaceChild(placeholder, img);
}

// Handle LaunchBox image loading errors
function handleLaunchboxImageError(img) {
    
    // Prevent infinite loop
    if (img.onerror === null) {
        return;
    }
    
    // Show placeholder
    img.onerror = null;
    img.style.display = 'none';
    
    // Create placeholder div
    const placeholder = document.createElement('div');
    placeholder.className = 'd-flex align-items-center justify-content-center';
    placeholder.style.cssText = 'height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;';
    placeholder.innerHTML = `
        <div class="text-muted">
            <i class="bi bi-image" style="font-size: 2rem;"></i>
            <div class="small">Box art not available</div>
        </div>
    `;
    
    // Replace the image with placeholder
    img.parentNode.replaceChild(placeholder, img);
}

// Handle Steam image loading errors
function handleSteamImageError(imgElement) {
    // Prevent infinite loop
    if (imgElement.onerror === null) {
        return;
    }
    
    // Create placeholder div
    const placeholder = document.createElement('div');
    placeholder.className = 'd-flex align-items-center justify-content-center';
    placeholder.style.cssText = 'height: 200px; background-color: #f8f9fa; border-radius: 0.375rem;';
    placeholder.innerHTML = `
        <div class="text-muted">
            <i class="bi bi-image" style="font-size: 2rem;"></i>
            <div class="small">No capsule art available</div>
        </div>
    `;
    
    // Replace the image with placeholder
    imgElement.parentNode.replaceChild(placeholder, imgElement);
}

// Fanart Search Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Fanart search form submission
    const fanartSearchForm = document.getElementById('fanartSearchForm');
    if (fanartSearchForm) {
        fanartSearchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (window.gameManager) {
                window.gameManager.performFanartSearch();
            }
        });
    }
});

// Google Images Search Event Listeners
document.addEventListener('DOMContentLoaded', () => {
});

// Marquee Search Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Marquee search form submission
    const marqueeSearchForm = document.getElementById('marqueeSearchForm');
    if (marqueeSearchForm) {
        marqueeSearchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (window.gameManager) {
                window.gameManager.performMarqueeSearch();
            }
        });
    }
});

// Initialize the game manager when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.gameManager = new GameCollectionManager();
});