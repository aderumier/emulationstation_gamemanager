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
        this.pendingBestMatchResults = null;
        this.currentBestMatchIndex = 0;
        this.duplicatesFilterActive = false; // Track duplicates filter state
        this.currentNavigationIndex = 0; // Track current navigation position
        this.eventSource = null;
        this.logHistory = [];
        this.lastProcessedGame = null;
        this.lastClickedColumn = null; // Track which column was last clicked for double-click behavior
        
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
        
        // Task panel resizing
        this.taskPanelResizing = false;
        this.taskPanelStartHeight = 0;
        this.taskPanelStartY = 0;
        
        // WebSocket for real-time updates
        this.socket = null;
        
        // Media mappings cache
        this.mediaMappingsCache = null;
        
        this.initializeEventListeners();
        this.loadState();
        this.checkExistingTask();
        
        // Initialize media mappings cache (don't await to avoid blocking constructor)
        this.initializeMediaMappingsCache();
        

        
        // Initialize task grid
        console.log('Constructor: About to call initializeTaskGrid');
        this.initializeTaskGrid();
        console.log('Constructor: Finished calling initializeTaskGrid');
        
        // Start auto-refresh for tasks since panel is always visible
        this.startTaskAutoRefresh();
        
        // Initialize Bootstrap tabs for the combined panel
        this.initializeTabs();
        
        // Initialize edit modal delete button
        this.initializeEditModalDeleteButton();
        
        // Add event listener for edit modal cleanup when closed
        this.initializeEditModalCleanup();
        
        // Initialize cache configuration modal
        this.initializeCacheConfigurationModal();
        
        // Initialize systems configuration modal
        this.initializeSystemsModal();
        
        // Initialize application configuration modal
        this.initializeAppConfigurationModal();
        
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
            console.log(`🧹 Cleaning up stale room memberships for: ${this.currentSystem}`);
            // The WebSocket will handle the actual cleanup when it connects
        }
    }

    initializeTabs() {
        // Initialize Bootstrap tabs for the combined panel
        try {
            console.log('Initializing tabs...');
            
            // Get the tab elements
            const mediaPreviewTab = document.getElementById('media-preview-tab');
            const taskManagementTab = document.getElementById('task-management-tab');
            const mediaPreviewContent = document.getElementById('media-preview-content');
            const taskManagementContent = document.getElementById('task-management-content');
            
            console.log('Tab elements found:', {
                mediaPreviewTab: !!mediaPreviewTab,
                taskManagementTab: !!taskManagementTab,
                mediaPreviewContent: !!mediaPreviewContent,
                taskManagementContent: !!taskManagementContent
            });
            
            if (mediaPreviewTab && taskManagementTab && mediaPreviewContent && taskManagementContent) {
                // Add click event listeners for manual tab switching
                mediaPreviewTab.addEventListener('click', () => {
                    console.log('Media preview tab clicked');
                    this.switchTab('media-preview');
                });
                
                taskManagementTab.addEventListener('click', () => {
                    console.log('Task management tab clicked');
                    this.switchTab('task-management');
                });
                
                // Set initial tab state
                this.switchTab('media-preview');
                
                console.log('Tabs initialized successfully');
            } else {
                console.warn('Some tab elements not found:', {
                    mediaPreviewTab: !!mediaPreviewTab,
                    taskManagementTab: !!taskManagementTab,
                    mediaPreviewContent: !!mediaPreviewContent,
                    taskManagementContent: !!taskManagementContent
                });
            }
        } catch (error) {
            console.error('Error initializing tabs:', error);
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
        } else if (tabName === 'task-management') {
            document.getElementById('task-management-tab').classList.add('active');
            document.getElementById('task-management-content').classList.add('show', 'active');
        }
    }



    async checkTaskQueue() {
        // Check the current task queue status
        try {
            const response = await fetch('/api/task/queue');
            if (response.ok) {
                const queueStatus = await response.json();
                return queueStatus;
            }
        } catch (error) {
            console.error('Error checking task queue:', error);
        }
        return null;
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
        try {
            const response = await fetch('/api/tasks');
            if (response.ok) {
                let tasks = await response.json();
                // Reconstruct missing fields from log history after restart (only once)
                if (!this.historyLoaded) {
                    try {
                        const needsHistory = Object.values(tasks).some(t => !t?.data?.system_name || (!t.total_steps && !t.progress_percentage));
                        if (needsHistory) {
                            const histResp = await fetch('/api/tasks/history');
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
                        console.warn('Task history reconstruction failed:', e);
                        this.historyLoaded = true; // Mark as loaded even on error to avoid retries
                    }
                }
                this.displayTasksInGrid(tasks);
                // Check for completed tasks that need grid refresh
                this.checkForGridRefresh(tasks);
            } else {
                console.error('Failed to fetch tasks');
            }
        } catch (error) {
            console.error('Error refreshing tasks:', error);
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
                console.log(`Auto-refreshing grid for completed ${task.type} task: ${taskId}`);
                console.log(`Task was for system: ${task.data.system_name}, current user system: ${this.currentSystem}`);
                
                // Only refresh if the user is currently viewing the same system
                if (this.currentSystem === task.data.system_name) {
                    console.log(`✅ User is viewing the same system (${this.currentSystem}), refreshing grid`);
                    
                    // Mark this task as processed
                    this.processedGridRefreshTasks.add(taskId);
                    
                    // Refresh the grid for this system
                    await this.loadRomSystem(task.data.system_name);
                    
                    // No need for additional refresh since loadRomSystem now uses efficient updates
                    console.log('Main grid refreshed after task completion');
                    // Acknowledge refresh so future sessions don't re-trigger
                    try {
                        await fetch(`/api/tasks/${taskId}/ack-refresh`, { method: 'POST' });
                    } catch (e) {
                        console.warn('Failed to ack grid refresh for task', taskId, e);
                    }
                } else {
                    console.log(`⏭️  User is viewing different system (${this.currentSystem}), skipping grid refresh for ${task.data.system_name}`);
                    
                    // Mark this task as processed to avoid checking it again
                    this.processedGridRefreshTasks.add(taskId);
                    // Still clear the flag so it doesn't spam when reopening
                    try {
                        await fetch(`/api/tasks/${taskId}/ack-refresh`, { method: 'POST' });
                    } catch (e) {
                        console.warn('Failed to ack grid refresh (skipped) for task', taskId, e);
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

        // Sort tasks: running first, then by start time (newest first)
        gridData.sort((a, b) => {
            if (a.status === 'running' && b.status !== 'running') return -1;
            if (a.status !== 'running' && b.status === 'running') return 1;
            return (b.data.start_time || 0) - (a.data.start_time || 0);
        });

        // Check if this is the first load or if we need to add/remove rows
        const currentRowCount = this.taskGridApi.getDisplayedRowCount();
        const newRowCount = gridData.length;
        
        // If row count changed significantly or it's the first load, use setRowData
        if (currentRowCount === 0 || Math.abs(currentRowCount - newRowCount) > 2) {
            this.taskGridApi.setRowData(gridData);
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
        // Efficiently update task grid using refreshCells instead of setRowData
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
            // If we have structural changes, fall back to setRowData
            this.taskGridApi.setRowData(newGridData);
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
        // Efficiently update game grid using refreshCells instead of setRowData
        if (!this.gridApi || newGames === null || newGames === undefined) return;
        
        console.log('updateGameGridData called with:', newGames.length, 'games');
        
        // Deduplicate input by path to avoid duplicate node ids
        const newDataMap = new Map();
        newGames.forEach(game => {
            if (game && game.path) {
                newDataMap.set(game.path, game);
            }
        });
        const dedupedGames = Array.from(newDataMap.values());
        
        // Check if this is the first load or if we need to add/remove rows
        const currentRowCount = this.gridApi.getDisplayedRowCount();
        const newRowCount = dedupedGames.length;
        
        // If row count changed significantly, it's the first load, or we're clearing the grid, use setRowData
        if (currentRowCount === 0 || Math.abs(currentRowCount - newRowCount) > 5 || newRowCount === 0) {
            console.log('Using setRowData for significant change or empty grid. Current:', currentRowCount, 'New:', newRowCount);
            this.gridApi.setRowData(dedupedGames);
            // Update our stored data
            this.currentGameData.clear();
            dedupedGames.forEach(game => {
                this.currentGameData.set(game.path, game);
            });
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
            // If we have structural changes, fall back to setRowData
            this.gridApi.setRowData(dedupedGames);
            this.currentGameData = newDataMap;
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
            oldGame.launchboxid !== newGame.launchboxid
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
                    return `<span class="task-status-badge ${status}">${this.getTaskStatusText(status)}</span>`;
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
                    let buttons = '';
                    
                    if (status === 'running') {
                        buttons = `<button class="btn btn-outline-warning btn-sm" onclick="window.gameManager.stopTask('${taskId}')">
                            <i class="bi bi-stop-circle"></i> Stop
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
                console.log('Column moved, saving state...');
                this.saveGridState();
            },
            onColumnResized: () => {
                console.log('Column resized, saving state...');
                this.saveGridState();
            },
            onSortChanged: () => {
                console.log('Sort changed, saving state...');
                this.saveGridState();
            },
            onFilterChanged: () => {
                console.log('Filter changed, saving state...');
                this.saveGridState();
            },
            onColumnVisible: () => {
                console.log('Column visibility changed, saving state...');
                this.saveGridState();
            },
            onColumnPinned: () => {
                console.log('Column pinned, saving state...');
                this.saveGridState();
            },
            // Additional events for better state capture
            onGridReady: () => {
                console.log('Grid ready event fired');
                setTimeout(() => this.restoreGridState(), 500);
            }
        };

        // Create the grid
        this.taskGridApi = agGrid.createGrid(taskGridElement, gridOptions);
        
        // Set the height after grid creation
        console.log('initializeTaskGrid: Setting height after grid creation');
        const savedHeight = this.getCookie('taskPanelHeight');
        if (savedHeight) {
            const height = parseInt(savedHeight);
            if (height >= 160 && height <= 800) {
                taskGridElement.style.height = height + 'px';
                console.log('initializeTaskGrid: Set saved height:', height);
            }
        } else {
            taskGridElement.style.height = '160px';
            console.log('initializeTaskGrid: Set default height: 160px');
        }
        
        // Wait for grid to be ready before restoring state
        this.taskGridApi.addEventListener('gridReady', () => {
            console.log('Task grid ready, restoring state...');
            this.restoreGridState();
        });
        
        // Also try to restore state after a short delay as fallback
        setTimeout(() => {
            if (this.taskGridApi && this.taskGridApi.isGridReady && this.taskGridApi.isGridReady()) {
                console.log('Task grid ready (delayed check), restoring state...');
                this.restoreGridState();
            } else {
                console.log('Task grid not ready yet (delayed check)');
            }
        }, 1000);
        
        // Additional fallback for task grid
        setTimeout(() => {
            console.log('Task grid fallback restore attempt...');
            this.restoreGridState();
        }, 2000);
        
        // Fallback: Enable state saving after a timeout even if restore fails
        setTimeout(() => {
            if (!this.stateSavingEnabled) {
                console.log('Fallback: Enabling state saving for task grid after timeout');
                this.stateSavingEnabled = true;
            }
        }, 3000);
    }
    
    saveGridState() {
        if (!this.taskGridApi) {
            console.log('saveGridState: taskGridApi not available');
            return;
        }
        
        if (!this.stateSavingEnabled) {
            console.log('saveGridState: State saving disabled during initialization');
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
            
            console.log('Task grid state saved successfully');
            
        } catch (error) {
            console.error('Error saving grid state:', error);
        }
    }
    
        restoreGridState() {
        if (!this.taskGridApi) {
            console.log('restoreGridState: taskGridApi not available');
            return;
        }
        
        try {
            const savedState = this.getCookie('taskGridState');
            if (!savedState) {
                console.log('restoreGridState: No saved state found');
            } else {
                const state = JSON.parse(savedState);
                
                // Restore column state using proper AG Grid API
                if (state.columnState && state.columnState.length > 0) {
                    const success = this.taskGridApi.applyColumnState({
                        state: state.columnState
                    });
                    
                    if (success) {
                        console.log('Task grid state restored successfully');
                    } else {
                        console.log('Task grid state restoration failed');
                    }
                }
            }
            
            // Always enable state saving after restoration attempt (whether successful or not)
            this.stateSavingEnabled = true;
            
        } catch (error) {
            console.error('Error restoring grid state:', error);
            // Even on error, enable state saving so the grid can work
            this.stateSavingEnabled = true;
        }
    }
    

    

    

    
    saveMainGridState() {
        if (!this.gridApi) {
            console.log('saveMainGridState: gridApi not available');
            return;
        }
        
        if (!this.stateSavingEnabled) {
            console.log('saveMainGridState: State saving disabled during initialization');
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
            
            console.log('Main grid state saved successfully');
            
        } catch (error) {
            console.error('Error saving main grid state:', error);
        }
    }
    
        restoreMainGridState() {
        if (!this.gridApi) {
            console.log('restoreMainGridState: gridApi not available');
            return;
        }
        
        try {
            const savedState = this.getCookie('mainGridState');
            
            if (!savedState) {
                console.log('restoreMainGridState: No saved state found');
            } else {
                const state = JSON.parse(savedState);
                
                // Restore column state using proper AG Grid API
                if (state.columnState && state.columnState.length > 0) {
                    const success = this.gridApi.applyColumnState({
                        state: state.columnState
                    });
                    
                    if (success) {
                        console.log('Main grid state restored successfully');
                    } else {
                        console.log('Main grid state restoration failed');
                    }
                }
            }
            
            // Always enable state saving after restoration attempt (whether successful or not)
            this.stateSavingEnabled = true;
            
        } catch (error) {
            console.error('Error restoring main grid state:', error);
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
            'queued': 'Queue'
        };
        return statusTexts[status] || status;
    }

    async showTaskLog(taskId) {
        try {
            // Get task details first to check if it's running
            const task = this.getTaskById(taskId);
            if (!task) {
                console.error('Task not found');
                return;
            }

            // If task is running, use streaming endpoint for live updates
            if (task.status === 'running') {
                this.displayTaskLogModal(taskId, '');
                this.startLiveLogStream(taskId);
            } else {
                // For completed tasks, fetch static log
                const response = await fetch(`/api/tasks/${taskId}/log`);
                if (response.ok) {
                    const data = await response.json();
                    this.displayTaskLogModal(taskId, data.log);
                } else {
                    console.error('Failed to fetch task log');
                }
            }
        } catch (error) {
            console.error('Error fetching task log:', error);
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
                    console.error('Log stream error:', data.error);
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
                console.error('Error parsing log stream data:', error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('Log stream error:', error);
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
            const response = await fetch(`/api/tasks/${taskId}/stop`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showToast(result.message || 'Task stopped successfully', 'success');
                
                // Refresh the task list to show updated status
                this.refreshTasks();
                // Avoid an immediate manual grid reload here; rely on WebSocket/system update
                // to perform a single, authoritative refresh and prevent duplicate updates.
            } else {
                const errorData = await response.json();
                this.showToast(errorData.error || 'Failed to stop task', 'error');
            }
        } catch (error) {
            console.error('Error stopping task:', error);
            this.showToast('Error stopping task', 'error');
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
        // Auto-refresh tasks every second
        if (!this.taskRefreshInterval) {
            this.taskRefreshInterval = setInterval(() => {
                this.refreshTasks();
                // Removed extra per-second YouTube completion check to avoid constant reloads
            }, 1000);
        }
    }

    stopTaskAutoRefresh() {
        if (this.taskRefreshInterval) {
            clearInterval(this.taskRefreshInterval);
            this.taskRefreshInterval = null;
        }
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
            document.body.removeChild(toast);
        });
    }

    initializeEventListeners() {
        // System selection
        document.getElementById('systemSelect').addEventListener('change', (e) => {
            this.loadRomSystem(e.target.value);
        });

        // Button event listeners
        document.getElementById('unifiedScanBtn').addEventListener('click', () => this.unifiedScan());
        document.getElementById('saveGamelistBtn').addEventListener('click', () => this.saveGamelist());
        document.getElementById('confirmGamelistSave').addEventListener('click', () => this.confirmGamelistSave());

        document.getElementById('scrapLaunchboxBtn').addEventListener('click', () => this.scrapLaunchbox());
        document.getElementById('scrapIgdbBtn').addEventListener('click', () => this.scrapIgdb());
        const screenscraperBtn = document.getElementById('scrapScreenscraperBtn');
        console.log('Looking for ScreenScraper button during initialization...');
        console.log('Button found:', screenscraperBtn);
        if (screenscraperBtn) {
            screenscraperBtn.addEventListener('click', () => {
                console.log('ScreenScraper button clicked');
                this.scrapScreenscraper();
            });
            console.log('ScreenScraper button event listener added');
            
        } else {
            console.error('ScreenScraper button not found during event listener setup!');
        }
        document.getElementById('globalFindBestMatchBtn').addEventListener('click', () => this.findBestMatchForSelected());
        document.getElementById('global2DBoxGeneratorBtn').addEventListener('click', () => this.generate2DBoxForSelected());
        document.getElementById('globalYoutubeDownloadBtn').addEventListener('click', () => this.openYoutubeDownloadModal());
        document.getElementById('startYoutubeDownloadBtn').addEventListener('click', () => this.startYoutubeDownload());
        

        
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

        document.getElementById('clearFiltersBtn').addEventListener('click', async () => await this.clearAllFilters());
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
                console.log('🔧 DEBUG: LaunchBox overwrite text fields checkbox changed:', e.target.checked);
                this.setCookie('launchboxOverwriteTextFields', e.target.checked);
                console.log('🔧 DEBUG: Cookie saved, verifying...', this.getCookie('launchboxOverwriteTextFields'));
            });
        } else {
            console.warn('🔧 DEBUG: overwriteTextFieldsLaunchbox element not found when setting up event listener');
        }

        // Grid selection change - handled by grid API listener

        // Delete selected games button
        document.getElementById('deleteSelectedBtn').addEventListener('click', () => this.showDeleteConfirmation());
        
        // Show duplicates button
        document.getElementById('showDuplicatesBtn').addEventListener('click', () => this.toggleDuplicatesFilter());
        
        // Confirm delete button
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => this.deleteSelectedGames());
        

        
        // Add global keyboard event listener for delete key and arrow navigation
        document.addEventListener('keydown', (event) => {
            // Handle Delete key with priority: media deletion first, then game deletion
            if (event.key === 'Delete') {
                // If media is selected, delete media (regardless of focus)
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
            console.log('Initializing WebSocket...');
            
            // Check if Socket.IO is available
            if (typeof io === 'undefined') {
                console.error('Socket.IO not loaded yet, retrying...');
                setTimeout(() => this.initializeWebSocket(), 500);
                return;
            }
            
            // Initialize Socket.IO connection
            this.socket = io();
            console.log('Socket.IO instance created');
            
            // Connection events
            this.socket.on('connect', () => {
                console.log('WebSocket connected');
                this.showToast('Connected to real-time updates', 'success');
            });
            
            this.socket.on('disconnect', () => {
                console.log('WebSocket disconnected');
                this.showToast('Disconnected from real-time updates', 'warning');
            });
            
            // System update events
            this.socket.on('system_updated', (data) => {
                console.log('System update received:', data);
                this.handleSystemUpdate(data);
            });
            
            // Join system room when system is loaded
            this.socket.on('connected', (data) => {
                console.log('WebSocket connected:', data);
                if (this.currentSystem) {
                    this.socket.emit('join_system', { system: this.currentSystem });
                }
            });
            
            // Task completion events
            this.socket.on('task_completed', (data) => {
                console.log('Task completed:', data);
                this.handleTaskCompletion(data);
            });
            
            // Add cleanup on page unload
            window.addEventListener('beforeunload', () => {
                if (this.socket && this.currentSystem) {
                    console.log(`🧹 Cleaning up WebSocket room: ${this.currentSystem}`);
                    this.socket.emit('leave_system', { system: this.currentSystem });
                }
            });
            
            console.log('WebSocket initialization completed');
            
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            // Retry after a delay
            setTimeout(() => this.initializeWebSocket(), 1000);
        }
    }
    
    handleSystemUpdate(data) {
        const { system, action, data: updateData } = data;
        
        console.log(`🔔 Received system update: ${action} for system ${system}, current system: ${this.currentSystem}`);
        
        // Only process updates for the current system
        if (system !== this.currentSystem) {
            console.log(`⚠️  Ignoring update for system ${system} - current system is ${this.currentSystem}`);
            return;
        }
        
        console.log(`✅ Processing update for current system: ${system}`);
        
        switch (action) {
            case 'gamelist_updated':
                console.log('Gamelist updated, refreshing grid...');
                // Show more specific message based on what actually changed
                if (updateData.updated_count > 0) {
                    this.showToast(`Scraping completed: ${updateData.updated_count} games updated`, 'success');
                } else {
                    this.showToast(`Gamelist refreshed: ${updateData.games_count} total games`, 'info');
                }
                // For gamelist updates, fetch fresh data to ensure consistency
                this.refreshGameGridWithData();
                break;
                
            case 'games_deleted':
                console.log('Games deleted, refreshing grid...');
                this.showToast(`Deleted ${updateData.deleted_files.length} files`, 'info');
                // For deletions, we need to fetch the updated data first
                this.syncGameData();
                break;
                
            case 'game_updated':
                console.log('Game updated, refreshing grid...');
                this.showToast(`Game updated: ${updateData.game_name}`, 'info');
                // For game updates, we need to fetch the latest data to sync properly
                this.syncGameData();
                break;
                
            default:
                console.log('Unknown system update action:', action);
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
        this.currentScrapingRequest = null;
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
        
        console.log('UI state reset completed');
    }
    
    async refreshGameGridWithData() {
        if (!this.currentSystem || !this.gridApi) return;
        
        try {
            console.log('Refreshing game grid with fresh data...');
            
            // Fetch the latest gamelist data
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`);
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
                    
                    // Use AG Grid's setRowData to efficiently update the grid
                    // This will preserve selection and scroll position
                    this.gridApi.setRowData(this.games);
                    // Keep our current game map in sync to ensure diff updates work later
                    this.currentGameData = new Map();
                    this.games.forEach(game => this.currentGameData.set(game.path, game));
                    
                    console.log('Game grid refreshed with fresh data');
                }
            }
        } catch (error) {
            console.error('Error refreshing game grid with data:', error);
            // Fallback to regular refresh if fetch fails
            this.refreshGameGrid();
        }
    }
    
    async syncGameData() {
        if (!this.currentSystem || !this.gridApi) return;
        
        try {
            console.log('Syncing game data for real-time update...');
            
            // Fetch the latest gamelist data
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`);
            if (response.ok) {
                const result = await response.json();
                
                if (result.success && result.games) {
                    // Update the local games array
                    this.games = result.games;
                    
                    // Use AG Grid's setRowData to efficiently update the grid
                    // This will preserve selection and scroll position
                    this.gridApi.setRowData(this.games);
                    
                    console.log('Game data synced successfully');
                }
            }
        } catch (error) {
            console.error('Error syncing game data:', error);
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
            this.gridApi.setRowData(this.games);
            
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
            console.log(`Deleted games: ${gameNames}`);
            console.log(`Deleted ROM files: ${gameRomPaths.join(', ')}`);
            console.log(`Deleted files: ${deletedFiles.join(', ')}`);
            
        } catch (error) {
            console.error('Error deleting games:', error);
            this.showToast('Error deleting games', 'error');
        }
    }
    

    
    async checkExistingTask() {
        // Check if there's an existing task running when the page loads
        try {
            const response = await fetch('/api/task/status');
            if (response.ok) {
                const task = await response.json();
                if (task.status === 'running') {
                    console.log('Found existing running task:', task);
                    this.displayExistingTask(task);
                } else if (task.status === 'completed' || task.status === 'error') {
                    console.log('Found completed task:', task);
                    this.displayCompletedTask(task);
                }
            }
        } catch (error) {
            console.log('No existing task found or error checking:', error);
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
        
        console.log('Loading ROM system:', systemName);
        console.log('Modified games before loading:', Array.from(this.modifiedGames));
        
        // Store previous system for cleanup
        const previousSystem = this.currentSystem;
        
        // Update current system
        this.currentSystem = systemName;
        this.setCookie('selectedSystem', systemName);
        
        // Leave previous system room if different
        if (this.socket && previousSystem && previousSystem !== systemName) {
            console.log(`🔄 Leaving previous system room: ${previousSystem}`);
            this.socket.emit('leave_system', { system: previousSystem });
        }
        
        // Join WebSocket room for this system
        if (this.socket) {
            console.log(`🔄 Joining system room: ${systemName}`);
            this.socket.emit('join_system', { system: systemName });
        }
        
        // Clear selection when changing systems
        if (this.gridApi) {
            this.gridApi.deselectAll();
        }
        this.selectedGames = [];
        
        // Reset duplicates filter when changing systems
        if (this.duplicatesFilterActive) {
            await this.resetDuplicatesFilter();
        }
        
        this.updateSelectionDisplay();
        
        try {
            const response = await fetch(`/api/rom-system/${systemName}/gamelist`);
            if (response.ok) {
                const data = await response.json();
                this.games = data.games || [];
                console.log('Loaded games:', this.games.length);
                console.log('First game sample:', this.games[0]);
                
                // Only initialize grid if it doesn't exist yet
                if (!this.gridApi) {
                    await this.initializeGrid();
                }
                
                this.updateGamesCount();
                console.log('About to call enableButtons for system:', systemName);
                this.enableButtons();
                
                // Set the row data directly for client-side row model
                if (this.gridApi) {
                    // Use efficient update method instead of setRowData
                    await this.updateGameGridData(this.games);
                    // Load saved column state
                    this.loadColumnState();
                }
                
                // Media preview is now always enabled
                this.mediaPreviewEnabled = true;
                
                // Reset navigation index to start when loading new system
                this.currentNavigationIndex = 0;
                console.log('Navigation index reset to 0 for new system');
            }
        } catch (error) {
            console.error('Error loading ROM system:', error);
        }
    }

    async initializeGrid() {
        const gridDiv = document.getElementById('gamesGrid');
        gridDiv.innerHTML = '';

        // Wait for media mappings cache to be ready
        let attempts = 0;
        while (!this.mediaMappingsCache && attempts < 50) { // Wait up to 5 seconds
            console.log('Waiting for media mappings cache to be ready...');
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (!this.mediaMappingsCache) {
            console.warn('Media mappings cache not ready after 5 seconds, using fallback values');
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
                },
                { 
                    field: 'image', 
                    headerName: 'Image', 
                    editable: false, 
                    sortable: true, 
                    filter: true, 
                    resizable: true, 
                    flex: 1, 
                    cellRenderer: this.mediaCellRenderer
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
            suppressFilterResetOnNewData: false,
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
            // State persistence event handlers
            onColumnMoved: () => {
                console.log('Main grid: Column moved, saving state...');
                this.saveMainGridState();
            },
            onColumnResized: () => {
                console.log('Main grid: Column resized, saving state...');
                this.saveMainGridState();
            },
            onSortChanged: () => {
                console.log('Main grid: Sort changed, saving state...');
                this.saveMainGridState();
            },
            onFilterChanged: () => {
                console.log('Main grid: Filter changed, saving state...');
                this.saveMainGridState();
            },
            onColumnVisible: () => {
                console.log('Main grid: Column visibility changed, saving state...');
                this.saveMainGridState();
            },
            onColumnPinned: () => {
                console.log('Main grid: Column pinned, saving state...');
                this.saveMainGridState();
            }
        };

        // Create the grid using the new createGrid method
        this.gridApi = agGrid.createGrid(gridDiv, gridOptions);
        
        // Apply custom CSS class to prevent theme conflicts with popups
        gridDiv.classList.add('game-grid-container');
        
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
            console.log('Cell value changed:', event);
            console.log('Field:', event.colDef.field);
            console.log('Old value:', event.oldValue);
            console.log('New value:', event.newValue);
            console.log('Game:', event.data);
            
            // Mark the game as modified when inline editing occurs
            if (event.data && event.colDef.field) {
                this.markGameAsModified(event.data);
                
                // Show a small notification that the change was made
                this.showInlineEditNotification(event.colDef.field, event.oldValue, event.newValue);
            }
        });

        // Add cell editing started event listener
        this.gridApi.addEventListener('cellEditingStarted', (event) => {
            console.log('Cell editing started:', event);
        });

        // Add cell editing stopped event listener
        this.gridApi.addEventListener('cellEditingStopped', (event) => {
            console.log('Cell editing stopped:', event);
        });
        
        // State persistence events are now handled in gridOptions
        
        // Restore main grid state after initialization
        setTimeout(() => {
            console.log('Main grid initialization complete, attempting to restore state...');
            this.restoreMainGridState();
        }, 500);
        
        // Fallback: Enable state saving after a timeout even if restore fails
        setTimeout(() => {
            if (!this.stateSavingEnabled) {
                console.log('Fallback: Enabling state saving for main grid after timeout');
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

        // Add right-click context menu
        this.gridApi.addEventListener('cellContextMenu', (event) => {
            this.showContextMenu(event);
        });

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
            // Use efficient update method instead of setRowData
            await this.updateGameGridData(this.games);
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
            
            console.log('All filters cleared');
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
        event.preventDefault();
        
        const game = event.data;
        const contextMenu = document.createElement('div');
        contextMenu.className = 'dropdown-menu show position-fixed';
        contextMenu.style.cssText = `top: ${event.event.clientY}px; left: ${event.event.clientX}px; z-index: 1000;`;
        
        contextMenu.innerHTML = `
            <a class="dropdown-item" href="#" onclick="gameManager.editGame(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                <i class="bi bi-pencil"></i> Edit
            </a>
            <a class="dropdown-item" href="#" onclick="gameManager.scanGameMedia(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                <i class="bi bi-search"></i> Scan Media
            </a>
            <a class="dropdown-item" href="#" onclick="gameManager.deleteGame(${JSON.stringify(game).replace(/"/g, '&quot;')})">
                <i class="bi bi-trash"></i> Delete
            </a>
        `;
        
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
        await this.populateEditModal(game);
        
        const modal = new bootstrap.Modal(document.getElementById('editGameModal'));
        modal.show();
    }

    async editGameWithPreviewTab(game) {
        this.editingGamePath = game.path; // Store ROM path as identifier
        await this.populateEditModal(game);
        
        const modal = new bootstrap.Modal(document.getElementById('editGameModal'));
        modal.show();
        
        // Wait for modal to be fully visible, then switch to preview tab
        setTimeout(() => {
            this.switchToPreviewTab();
        }, 100);
    }

    async populateEditModal(game) {
        // Clear all fields first to ensure no residual data
        document.getElementById('editName').value = '';
        document.getElementById('editPath').value = '';
        document.getElementById('editDescription').value = '';
        document.getElementById('editGenre').value = '';
        document.getElementById('editDeveloper').value = '';
        document.getElementById('editPublisher').value = '';
        document.getElementById('editRating').value = '';
        document.getElementById('editPlayers').value = '';
        document.getElementById('editLaunchboxId').value = '';
        document.getElementById('editIgdbId').value = '';
        document.getElementById('editScreenscraperId').value = '';
        document.getElementById('editYoutubeurl').value = '';
        
        // Now populate with game data
        document.getElementById('editName').value = game.name || '';
        document.getElementById('editPath').value = game.path || '';
        document.getElementById('editDescription').value = game.desc || '';
        document.getElementById('editGenre').value = game.genre || '';
        document.getElementById('editDeveloper').value = game.developer || '';
        document.getElementById('editPublisher').value = game.publisher || '';
        document.getElementById('editRating').value = game.rating || '';
        document.getElementById('editPlayers').value = game.players || '';
        document.getElementById('editLaunchboxId').value = game.launchboxid || '';
        document.getElementById('editIgdbId').value = game.igdbid || '';
        document.getElementById('editScreenscraperId').value = game.screenscraperid || '';
        document.getElementById('editYoutubeurl').value = game.youtubeurl || '';
        
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
                    this.showPartialMatches(gameName);
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
        // Use cached mappings if available
        if (this.mediaMappingsCache) {
            // Get unique gamelist field names from mappings, excluding video
            const mediaFields = [...new Set(Object.values(this.mediaMappingsCache))];
            return mediaFields.filter(field => field !== 'video');
        }
        
        // If not cached, use fallback values
        console.warn('Media mappings not cached yet, using fallback values');
        return this.getFallbackMediaFields();
    }
    
    getFallbackMediaFields() {
        // Fallback media fields if API is unavailable
        return [...new Set(["marquee", "boxart", "thumbnail", "screenshot", "cartridge", "fanart", "titleshot", "manual", "boxback", "extra1"])];
    }
    
    async getMediaMappings() {
        // Use cached mappings if available
        if (this.mediaMappingsCache) {
            return this.mediaMappingsCache;
        }
        
        // If not cached, use fallback values
        console.warn('Media mappings not cached yet, using fallback values');
        return this.getFallbackMediaMappings();
    }
    
    getFallbackMediaMappings() {
        // Fallback media mappings if API is unavailable
        return {
            "marquee": "marquee",
            "boxart": "boxart", 
            "thumbnails": "thumbnail",
            "screenshots": "screenshot",
            "cartridges": "cartridge",
            "fanarts": "fanart",
            "titles": "titleshot",
            "manuals": "manual",
            "boxback": "boxback",
            "box2d": "extra1"
        };
    }
    
    async initializeMediaMappingsCache() {
        // Fetch media mappings once when the application starts
        try {
            console.log('Initializing media mappings cache...');
            const response = await fetch('/api/media-mappings');
            const data = await response.json();
            
            if (data.success) {
                this.mediaMappingsCache = data.mappings;
                console.log('Media mappings cache initialized successfully:', this.mediaMappingsCache);
            } else {
                console.error('Failed to fetch media mappings:', data.error);
                this.mediaMappingsCache = this.getFallbackMediaMappings();
                console.log('Using fallback media mappings');
            }
        } catch (error) {
            console.error('Error fetching media mappings:', error);
            this.mediaMappingsCache = this.getFallbackMediaMappings();
            console.log('Using fallback media mappings due to error');
        }
    }
    
    async generateDynamicMediaColumns() {
        // Get media mappings from cache
        const mediaMappings = await this.getMediaMappings();
        
        // Generate column definitions for each media type
        const mediaColumns = [];
        
        for (const [mediaType, fieldName] of Object.entries(mediaMappings)) {
            // Skip 'videos' since we already have a static 'video' column
            if (mediaType === 'videos') {
                continue;
            }
            
            // Create a human-readable header name
            const headerName = this.formatHeaderName(mediaType);
            
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
    
    formatHeaderName(mediaType) {
        // Convert media type to human-readable header name
        const nameMap = {
            'marquee': 'Marquee',
            'boxart': 'Box Art',
            'thumbnails': 'Thumbnail',
            'screenshots': 'Screenshot',
            'cartridges': 'Cartridge',
            'fanarts': 'Fan Art',
            'titles': 'Title Shot',
            'manuals': 'Manual',
            'boxback': 'Box Back',
            'box2d': 'Box 2D',
            'wheels': 'Wheel'
        };
        
        return nameMap[mediaType] || mediaType.charAt(0).toUpperCase() + mediaType.slice(1);
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
            mediaItem.style.cssText = 'width: calc(20% - 6.4px); min-width: 180px; height: 200px; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #dee2e6; border-radius: 8px; background-color: #f8f9fa; transition: all 0.2s ease;';
            
            if (game[field] && game[field].trim()) {
                // Display actual media file
                const img = document.createElement('img');
                // Fix image URL by adding roms/<system>/ prefix if missing
                // Use the current system that was set when loading the games
                let imagePath = game[field];
                if (imagePath && !imagePath.startsWith('roms/')) {
                    imagePath = `roms/${this.currentSystem}/${imagePath}`;
                }
                img.src = imagePath;
                img.alt = `${field} for ${game.name}`;
                img.title = `${field}: ${game[field]}\nDouble-click to upload new media\nClick to select for deletion`;
                img.style.cssText = 'width: calc(100% - 20px); height: 140px; object-fit: contain; cursor: pointer; border-radius: 4px;';
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
                        <div class="media-placeholder" style="width: calc(100% - 20px); height: 140px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 2px dashed #dee2e6; border-radius: 4px; background-color: #f8f9fa;" ondblclick="if (!gameManager.uploadInProgress) { gameManager.uploadMediaForGame(gameManager.games.find(g => g.id === ${game.id}), '${field}'); } else { gameManager.showAlert('Upload in progress. Please wait...', 'warning'); }" title="Double-click to upload media">
                            <div style="text-align: center; color: #6c757d;">
                                <i class="bi bi-image" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                                Double-click<br>to upload
                            </div>
                        </div>
                        <small class="d-block text-center mt-1" style="font-size: 0.7rem; color: #6c757d;">${field}</small>
                    `;
                };
                mediaItem.appendChild(img);
                
                // Filename display removed - no longer showing ROM path text under game image
                
                // Add field label
                const fieldLabel = document.createElement('small');
                fieldLabel.className = 'd-block text-center mt-1';
                fieldLabel.textContent = field;
                fieldLabel.style.cssText = 'font-size: 0.7rem; color: #6c757d;';
                mediaItem.appendChild(fieldLabel);
                
                // Add LaunchBox download button
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'btn btn-outline-primary btn-sm mt-1';
                downloadBtn.style.cssText = 'font-size: 0.6rem; padding: 2px 6px;';
                downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
                downloadBtn.title = 'Download from LaunchBox';
                downloadBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.openLaunchBoxMediaModal(game, field);
                };
                mediaItem.appendChild(downloadBtn);
            } else {
                // Display placeholder for missing media
                mediaItem.innerHTML = `
                    <div class="media-placeholder" style="width: calc(100% - 20px); height: 140px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 2px dashed #dee2e6; border-radius: 4px; background-color: #f8f9fa;" ondblclick="if (!gameManager.uploadInProgress) { gameManager.uploadMediaForGame(gameManager.games.find(g => g.id === ${game.id}), '${field}'); } else { gameManager.showAlert('Upload in progress. Please wait...', 'warning'); }" title="Double-click to upload media">
                        <div style="text-align: center; color: #6c757d;">
                            <i class="bi bi-image" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                            Double-click<br>to upload
                        </div>
                    </div>
                    <small class="d-block text-center mt-1" style="font-size: 0.7rem; color: #6c757d;">${field}</small>
                    <button class="btn btn-outline-primary btn-sm mt-1" style="font-size: 0.6rem; padding: 2px 6px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                        <i class="bi bi-download"></i>
                    </button>
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
            console.log('LaunchBox modal closed, refreshing media preview if needed');
            if (this.currentMediaPreviewGame && this.currentMediaPreviewGame.path === game.path) {
                console.log('Refreshing media preview after LaunchBox modal close');
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
                throw new Error(`HTTP error! status: ${response.status}`);
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
            console.error('Error fetching LaunchBox media:', error);
            contentDiv.innerHTML = '<div class="col-12"><div class="alert alert-danger">Error loading media from LaunchBox: ' + error.message + '</div></div>';
            progressDiv.style.display = 'none';
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
                    media_type: mediaType,
                    media_url: mediaData.url,
                    region: mediaData.region,
                    system_name: this.currentSystem
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
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
                        console.log('Refreshing media preview after LaunchBox download');
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
            console.error('Error downloading media:', error);
            const progressDiv = document.getElementById('launchboxMediaProgress');
            progressDiv.textContent = 'Error: ' + error.message;
            progressDiv.className = 'text-danger mt-1';
        }
    }
    
    showEditGameVideo(game) {
        const videoContent = document.getElementById('editGameVideoContent');
        if (!videoContent) return;
        
        console.log('showEditGameVideo called for game:', game.name);
        console.log('Game video field:', game.video);
        
        // Clear existing content
        videoContent.innerHTML = '';
        
        // Define video fields to display
        const videoFields = ['video', 'video_mp4', 'video_avi', 'video_mov', 'video_mkv'];
        
        videoFields.forEach(field => {
            console.log(`Checking field ${field}:`, game[field]);
            if (game[field] && game[field].trim()) {
                console.log(`Creating video player for field ${field} with path: ${game[field]}`);
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
                console.log('Video field:', field, 'Original path:', videoPath, 'Current system:', this.currentSystem);
                if (videoPath && !videoPath.startsWith('roms/')) {
                    videoPath = `roms/${this.currentSystem}/${videoPath}`;
                    console.log('Constructed video path:', videoPath);
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
        
        console.log('fixImagePath input:', imagePath);
        
        // If the path already starts with 'roms/', return as is
        if (imagePath.startsWith('roms/')) {
            console.log('Path already has roms/ prefix, returning:', imagePath);
            return imagePath;
        }
        
        // Get current system from URL
        const currentSystem = this.getCurrentRomSystem();
        console.log('Current system:', currentSystem);
        
        if (!currentSystem) {
            console.log('No current system found, returning original path:', imagePath);
            return imagePath;
        }
        
        // Add the missing prefix
        const fullPath = `roms/${currentSystem}/${imagePath}`;
        console.log('Constructed full path:', fullPath);
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
                    console.error('Error uploading media:', error);
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
            console.error('Error deleting video:', error);
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
                    console.log('Upload successful:', result);
                    console.log('Looking for game with ROM path:', romPath);
                    console.log('Available games paths:', this.games.slice(0, 5).map(g => g.path));
                    
                    // Update the game object with new media path
                    const game = this.games.find(g => g.path === romPath);
                    if (game) {
                        console.log('Before update - game[mediaField]:', game[mediaField]);
                        game[mediaField] = result.media_path;
                        console.log('After update - game[mediaField]:', game[mediaField]);
                        console.log('Result media_path:', result.media_path);
                        
                        this.markGameAsModified(game);
                        
                        // Refresh the main grid to show updated media
                        this.gridApi.refreshCells();
                        
                        // If the edit modal is open, refresh the media display
                        const editModal = document.getElementById('editGameModal');
                        if (editModal && editModal.classList.contains('show')) {
                            console.log('Refreshing edit modal media display');
                            this.showEditGameMedia(game);
                            
                            // If it's a video upload, also refresh the video preview tab
                            if (mediaField === 'video') {
                                console.log('Refreshing video preview tab after video upload');
                                this.showEditGameVideo(game);
                            }
                        }
                        
                        // If media preview is showing for this game, refresh it
                        if (this.mediaPreviewEnabled && this.currentMediaPreviewGame && 
                            this.currentMediaPreviewGame.path === game.path) {
                            console.log('Refreshing media preview after upload');
                            // Add a longer delay to ensure gamelist is fully updated and processed
                            setTimeout(() => {
                                console.log('Actually refreshing media preview now...');
                                this.showMediaPreview(game);
                            }, 1000);
                        }
                        
                        // Show success message with file info
                        const successMessage = isVideo 
                            ? `Video uploaded successfully! (${fileSize} MB)` 
                            : `${mediaField} uploaded successfully! (${fileSize} MB)`;
                        this.showAlert(successMessage, 'success');
                    } else {
                        console.error('Game not found for ID:', gameId);
                    }
                } else {
                    this.showAlert(`Failed to upload ${mediaField}: ${result.error}`, 'error');
                }
            } else {
                this.showAlert(`Failed to upload ${mediaField}`, 'error');
            }
        } catch (error) {
            console.error('Error in handleMediaUpload:', error);
            this.showAlert(`Error uploading ${mediaField}`, 'error');
        }
    }
    
    async saveGameChangesFromModal() {
        if (!this.editingGamePath) return;

        const game = this.games.find(g => g.path === this.editingGamePath);
        if (!game) {
            console.error('Game not found for path:', this.editingGamePath);
            this.showAlert('Error: Game not found. Please close and reopen the edit modal.', 'error');
            return;
        }
        console.log('Saving changes for game:', game);
        console.log('Game path:', this.editingGamePath);
        
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
        game.igdbid = document.getElementById('editIgdbId').value;
        game.screenscraperid = document.getElementById('editScreenscraperId').value;
        game.youtubeurl = document.getElementById('editYoutubeurl').value;

        console.log('Updated game object:', game);
        
        // Detect which fields changed
        const changedFields = [];
        if (originalGame.name !== game.name) changedFields.push('name');
        if (originalGame.desc !== game.desc) changedFields.push('desc');
        if (originalGame.genre !== game.genre) changedFields.push('genre');
        if (originalGame.developer !== game.developer) changedFields.push('developer');
        if (originalGame.publisher !== game.publisher) changedFields.push('publisher');
        if (originalGame.rating !== game.rating) changedFields.push('rating');
        if (originalGame.players !== game.players) changedFields.push('players');
        if (originalGame.youtubeurl !== game.youtubeurl) changedFields.push('youtubeurl');
        
        console.log('Changed fields:', changedFields);
        
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
                        changed_fields: changedFields
                    }]
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Save response:', result);
                
                // Clear modified games since they're now saved
                this.modifiedGames.clear();
                
                this.showAlert('Changes saved directly to gamelist.xml!', 'success');
                
                // Refresh the grid to show updated values
                this.gridApi.refreshCells();
                
                // Move focus away from modal before hiding it
                const safeElement = document.querySelector('#gamesCount') || document.body;
                if (safeElement) {
                    safeElement.focus();
                }
                
                const modal = bootstrap.Modal.getInstance(document.getElementById('editGameModal'));
                modal.hide();
            } else {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                this.showAlert('Error saving changes to gamelist.xml', 'danger');
            }
        } catch (error) {
            console.error('Error saving changes:', error);
            this.showAlert('Error saving changes to gamelist.xml', 'danger');
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
            console.error('Error scanning game media:', error);
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
        this.currentGameData = {
            name: gameName,
            system: systemName
        };
        
        // Show the game edit match modal
        this.showPartialMatches(gameName, null, 'gameEdit');
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
        const response = await fetch('/api/config');
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
        this.currentGameData = {
            name: gameName,
            system: systemName,
            igdbPlatform: igdbPlatform
        };
        
        // Show the IGDB search modal
        this.showIgdbSearchModal(gameName, igdbPlatform, systemName);
    }
    
    async showIgdbSearchModal(gameName, platformNameOrId, systemName) {
        // Set the game name in the modal
        document.getElementById('igdbSearchGameName').textContent = gameName;
        
        // Store system name for use in results display
        this.currentIgdbSearchSystem = systemName;
        
        // Clear previous results
        document.getElementById('igdbSearchResults').innerHTML = '';
        document.getElementById('igdbSearchError').style.display = 'none';
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('igdbSearchModal'));
        modal.show();
        
        // Show spinner
        document.getElementById('igdbSearchSpinner').style.display = 'inline-block';
        
        try {
            // Search for games in IGDB
            const response = await fetch('/api/igdb/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_name: gameName,
                    platform_id: platformNameOrId,
                    limit: 10
                })
            });
            
            const result = await response.json();
            
            // Hide spinner
            document.getElementById('igdbSearchSpinner').style.display = 'none';
            
            if (response.ok && result.success) {
                this.displayIgdbSearchResults(result.games);
            } else {
                this.showIgdbSearchError(result.error || 'Failed to search IGDB games');
            }
            
        } catch (error) {
            console.error('Error searching IGDB games:', error);
            document.getElementById('igdbSearchSpinner').style.display = 'none';
            this.showIgdbSearchError('Error searching IGDB games: ' + error.message);
        }
    }
    
    displayIgdbSearchResults(games) {
        const resultsContainer = document.getElementById('igdbSearchResults');
        
        if (!games || games.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><div class="alert alert-info">No games found in IGDB database.</div></div>';
            return;
        }
        
        let html = '';
        games.forEach((game, index) => {
            const rating = game.rating ? Math.round(game.rating) : 'N/A';
            const summary = game.summary ? (game.summary.length > 200 ? game.summary.substring(0, 200) + '...' : game.summary) : 'No description available';
            
            // Get platform names from IGDB data
            const platformNames = game.platforms && game.platforms.length > 0 
                ? game.platforms.map(p => p.name).join(', ') 
                : 'Unknown Platform';
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title">${game.name}</h6>
                            <p class="card-text small text-muted">${summary}</p>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">Rating: ${rating}/100</small>
                                <small class="text-muted">ID: ${game.id}</small>
                            </div>
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
    
    selectIgdbGame(igdbId, gameName) {
        // Update the IGDB ID field in the edit modal
        document.getElementById('editIgdbId').value = igdbId;
        
        // Close the IGDB search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('igdbSearchModal'));
        if (modal) {
            modal.hide();
        }
        
        // Show success message
        this.showAlert(`IGDB ID set to ${igdbId} for "${gameName}"`, 'success');
        
        // Mark the game as modified
        if (this.editingGameIndex >= 0 && this.editingGameIndex < this.games.length) {
            const game = this.games[this.editingGameIndex];
            this.modifiedGames.add(game.id);
        }
    }

    async findBestMatchForSelected() {
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
            
            console.log('Finding best matches for selected games:', this.selectedGames.length);
            
            // Get the paths of selected games
            const selectedGamePaths = this.selectedGames.map(game => game.path);
            
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
                console.log('Found matches for games:', data.results.length);
                
                // Store the results for processing
                this.pendingBestMatchResults = data.results;
                this.currentBestMatchIndex = 0;
                this.currentModalContext = 'global';
                
                // Show the first game's matches
                this.showNextBestMatchModal();
            } else {
                this.showAlert('No matches found for the selected games', 'info');
            }
            
        } catch (error) {
            console.error('Error finding best matches:', error);
            this.showAlert('Error finding best matches: ' + error.message, 'danger');
        } finally {
            // Reset button state
            const button = document.getElementById('globalFindBestMatchBtn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-search"></i> Find Best Match';
            }
        }
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
            
            console.log('Generating 2D boxes for selected games:', this.selectedGames.length);
            
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
            console.error('Error starting 2D box generation:', error);
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

            // Determine which games to process
            const gamesToProcess = this.selectedGames.length > 0 ? this.selectedGames : this.games;
            
            // Filter games that have YouTube URLs
            const gamesWithYoutube = gamesToProcess.filter(game => {
                const youtubeUrl = game.youtubeurl || '';
                const hasYoutube = youtubeUrl.trim() !== '' && youtubeUrl.toLowerCase().includes('youtube');
                console.log('🎥 DEBUG: Checking game:', game.name, 'Path:', game.path, 'YouTube URL:', youtubeUrl, 'Has YouTube:', hasYoutube);
                return hasYoutube;
            });

            console.log('🎥 DEBUG: Games with YouTube URLs found:', gamesWithYoutube.length);
            console.log('🎥 DEBUG: Games with YouTube:', gamesWithYoutube.map(g => ({ name: g.name, path: g.path, youtubeurl: g.youtubeurl })));

            if (gamesWithYoutube.length === 0) {
                this.showAlert('No games with YouTube URLs found to download', 'warning');
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
                overwrite_existing: overwriteExisting
            };

            console.log('Starting YouTube download batch task:', requestBody);

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
            console.error('Error starting YouTube download batch:', error);
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
        const topMatches = currentResult.top_matches;
        
        console.log(`Showing matches for game ${this.currentBestMatchIndex + 1}/${this.pendingBestMatchResults.length}: ${gameName}`);
        
        // Show the modal with the current game's matches
        this.showPartialMatches(gameName, topMatches, 'global');
    }
    
    moveToPrevGame() {
        if (this.pendingBestMatchResults && this.currentBestMatchIndex > 0) {
            this.currentBestMatchIndex--;
            const currentGame = this.pendingBestMatchResults[this.currentBestMatchIndex];
            console.log('Moving to previous game:', currentGame);
            console.log('Top matches available:', currentGame.top_matches);
            
            // Ensure modal state is properly managed during navigation
            this.isModalOpen = true;
            this.showPartialMatches(currentGame.game_name, currentGame.top_matches, 'global');
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
    
    async scrapLaunchbox() {
        if (!this.currentSystem) return;
        
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
            console.log('🔧 DEBUG: overwriteTextFields checkbox checked:', overwriteTextFields);
            
            // Get selected fields for LaunchBox scraping
            const selectedFields = await this.getSelectedLaunchboxFields();
            
            const requestBody = {
                selected_games: gamesToScrape.map(game => game.path),
                force_download: forceDownload,
                overwrite_text_fields: overwriteTextFields,
                selected_fields: selectedFields
            };
            console.log('DEBUG: JavaScript - Request body:', requestBody);
            
            const response = await fetch(`/api/scrap-launchbox/${this.currentSystem}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (response.ok) {
                // Progress updates are now handled by the task panel
                
                console.log('Scraping started successfully');
                
                // Show success message
                if (isFullCollection) {
                    this.showAlert(`Launchbox scraping started for entire collection (${gamesToScrape.length} games)`, 'success');
                } else {
                    this.showAlert(`Launchbox scraping started for ${gamesToScrape.length} selected game${gamesToScrape.length > 1 ? 's' : ''}`, 'success');
                }
            } else if (response.status === 409) {
                // Task conflict - another task is running
                const errorData = await response.json();
                if (errorData.queued) {
                    this.showAlert(`Task queued: ${errorData.queue_message}`, 'warning');
                } else {
                    this.showAlert(errorData.error || 'Task conflict - another task is running', 'danger');
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Unknown error', 'danger');
            }
        } catch (error) {
            console.error('Error starting Launchbox scraping:', error);
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
            
            // Stop partial match polling
            this.stopPartialMatchPolling();
            
        } catch (error) {
            console.error('Error stopping scraping:', error);
            this.showAlert(`Error stopping: ${error.message}`, 'danger');
        }
    }


    
    startPartialMatchPolling() {
        console.log('Starting partial match polling...');
        
        // Clear any existing interval
        if (this.partialMatchPollingInterval) {
            clearInterval(this.partialMatchPollingInterval);
        }
        
        // Poll every 2 seconds for partial match requests
        this.partialMatchPollingInterval = setInterval(async () => {
            try {
                // Don't poll if a modal is already open
                if (this.isModalOpen) {
                    console.log('Modal already open, skipping poll...');
                    return;
                }
                
                console.log('Polling for partial match requests...');
                const response = await fetch('/api/check-partial-match-requests');
                if (response.ok) {
                    const data = await response.json();
                    console.log('Partial match response:', data);
                    if (data.has_request) {
                        console.log('Found partial match request:', data.request);
                        // Show the partial match modal for this request
                        this.showPartialMatchFromScraping(data.request);
                    } else {
                        console.log('No partial match requests found');
                    }
                } else {
                    console.log('Partial match request failed:', response.status);
                }
            } catch (error) {
                console.error('Error checking partial match requests:', error);
            }
        }, 2000);
        
        console.log('Partial match polling started with interval:', this.partialMatchPollingInterval);
    }
    
    stopPartialMatchPolling() {
        if (this.partialMatchPollingInterval) {
            clearInterval(this.partialMatchPollingInterval);
            this.partialMatchPollingInterval = null;
        }
    }
    
    showPartialMatchFromScraping(requestData) {
        console.log('showPartialMatchFromScraping called with:', requestData);
        
        // Convert top_matches to the format expected by the modal
        const matches = [];
        if (requestData.top_matches && Array.isArray(requestData.top_matches)) {
            requestData.top_matches.forEach(matchData => {
                const match = {
                    game: matchData,
                    score: matchData.score || 0,
                    match_type: matchData.match_type || requestData.match_source,
                    matched_name: matchData.matched_name || matchData.name || 'Unknown',
                    database_id: matchData.database_id || matchData.DatabaseID || '',
                    name: matchData.name || matchData.Name || '',
                    overview: matchData.overview || matchData.Overview || '',
                    developer: matchData.developer || matchData.Developer || '',
                    publisher: matchData.publisher || matchData.Publisher || '',
                    genre: matchData.genre || matchData.Genre || '',
                    rating: matchData.rating || matchData.Rating || '',
                    players: matchData.players || matchData.Players || ''
                };
                matches.push(match);
            });
        } else {
            // Fallback to single match if top_matches not available
            const match = {
                game: requestData.best_match,
                score: requestData.score,
                match_type: requestData.match_source,
                matched_name: requestData.matched_name,
                database_id: requestData.best_match.DatabaseID || '',
                name: requestData.best_match.Name || '',
                overview: requestData.best_match.Overview || '',
                developer: requestData.best_match.Developer || '',
                publisher: requestData.best_match.Publisher || '',
                genre: requestData.best_match.Genre || '',
                rating: requestData.best_match.Rating || '',
                players: requestData.best_match.Players || ''
            };
            matches.push(match);
        }
        
        console.log(`Created ${matches.length} match objects for modal`);
        
        // Show the modal with all the match data
        this.displayScraperPartialMatchModal(requestData.game_name, matches);
        
        // Store the request data for when user applies the match
        this.currentScrapingRequest = requestData;
        
        console.log('Modal should now be displayed with multiple matches');
    }

    displayScraperPartialMatchModal(originalGameName, matches) {
        console.log('displayScraperPartialMatchModal called with:', originalGameName, matches);
        
        // Set original game name
        document.getElementById('originalGameName').textContent = originalGameName;
        
        // Find the original game data to display details
        const originalGame = this.games.find(game => game.name === originalGameName);
        if (originalGame) {
            // Populate original game details
            document.getElementById('originalGamePublisher').textContent = originalGame.publisher || 'N/A';
            document.getElementById('originalGameDeveloper').textContent = originalGame.developer || 'N/A';
            document.getElementById('originalGameRomFile').textContent = originalGame.path || 'N/A';
            
            // Try to extract release date from various fields
            let releaseDate = 'N/A';
            if (originalGame.releaseDate) {
                releaseDate = originalGame.releaseDate;
            } else if (originalGame.date) {
                releaseDate = originalGame.date;
            } else if (originalGame.year) {
                releaseDate = originalGame.year;
            }
            document.getElementById('originalGameReleaseDate').textContent = releaseDate;
        } else {
            // Clear fields if game not found
            document.getElementById('originalGamePublisher').textContent = 'N/A';
            document.getElementById('originalGameDeveloper').textContent = 'N/A';
            document.getElementById('originalGameRomFile').textContent = 'N/A';
            document.getElementById('originalGameReleaseDate').textContent = 'N/A';
        }
        
        // Store for later use
        this.currentMatches = matches;
        this.currentOriginalGameName = originalGameName;
        this.selectedMatchIndex = -1;
        
        // Clear previous matches
        const matchesList = document.getElementById('matchesList');
        matchesList.innerHTML = '';
        
        // Generate match cards
        matches.forEach((match, index) => {
            const matchCard = this.createMatchCard(match, index);
            matchesList.appendChild(matchCard);
        });
        
        // Enable the apply button
        document.getElementById('applySelectedMatch').disabled = true;
        
        // Add event listener for apply button
        const applyBtn = document.getElementById('applySelectedMatch');
        applyBtn.onclick = () => this.applySelectedMatch();
        
        console.log('Modal content populated, now showing modal...');
        
        // Check if modal element exists
        const modalElement = document.getElementById('partialMatchModal');
        if (!modalElement) {
            console.error('Modal element not found!');
            return;
        }
        console.log('Modal element found:', modalElement);
        
        // Create modal instance
        const modal = new bootstrap.Modal(modalElement);
        
        // Only add event listener once
        if (!this.modalEventListenersAdded) {
            modalElement.addEventListener('hidden.bs.modal', () => {
                console.log('Modal hidden event triggered');
                
                // Check if we're in multi-game mode and this is not the last game
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1 && this.currentBestMatchIndex < this.pendingBestMatchResults.length - 1) {
                    console.log('Multi-game mode active, not resetting state');
                    return;
                }
                
                // If we're on the last game or single game, allow normal modal closure
                console.log('Last game or single game - allowing modal closure');
                
                // Force reset all state to prevent UI from getting stuck
                this.resetUIState();
                
                console.log('Modal closed, state reset, polling resumed');
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
                console.log('Cancel button clicked - manually hiding modal');
                modal.hide();
            });
        }
        
        // Set modal as open
        this.isModalOpen = true;
        console.log('Modal marked as open, polling paused');
        
        // Show the modal
        modal.show();
        
        console.log('Modal.show() called with event listeners attached');
    }
    














    

    async waitForTaskCompletion() {
        // Wait for task to complete by polling task status
        let attempts = 0;
        const maxAttempts = 60; // Wait up to 5 minutes
        
        while (attempts < maxAttempts) {
            try {
                const response = await fetch('/api/task/status');
                if (response.ok) {
                    const status = await response.json();
                    if (status.status === 'completed' || status.status === 'error') {
                        return; // Task completed
                    }
                }
            } catch (error) {
                console.error('Error checking task status:', error);
            }
            
            // Wait 5 seconds before next check
            await new Promise(resolve => setTimeout(resolve, 5000));
            attempts++;
        }
        
        throw new Error('Task did not complete within expected time');
    }

    showRomScanConfirmation(scanSummary) {
        const { new_roms, missing_roms, total_existing, total_rom_files } = scanSummary;
        
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
                                    <div class="d-grid gap-2">
                                        <button type="button" class="btn btn-success btn-sm" onclick="window.gameManager.confirmRomScan('proceed')" data-bs-dismiss="modal">
                                            <i class="fas fa-check"></i> Proceed with Changes
                                        </button>
                                        <button type="button" class="btn btn-secondary btn-sm" onclick="window.gameManager.confirmRomScan('cancel')" data-bs-dismiss="modal">
                                            <i class="fas fa-times"></i> Cancel
                                        </button>
                                    </div>
                                </div>
                            </div>`;
        
        if (new_roms.length > 0) {
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
        
        if (missing_roms.length > 0) {
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
        
        modalHTML += `
                            <div class="alert alert-warning mt-3">
                                <i class="fas fa-exclamation-triangle"></i>
                                <strong>Warning:</strong> This action will remove ${missing_roms.length} games with missing ROM files from your gamelist.xml. This cannot be undone.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-success" onclick="window.gameManager.confirmRomScan('proceed')" data-bs-dismiss="modal">
                                <i class="fas fa-check"></i> Proceed with Changes
                            </button>
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
    }

    async confirmRomScan(action) {
        try {
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
                    } else if (result.action_taken === 'cancelled') {
                        this.showAlert('ROM scan cancelled.', 'info');
                    }
                } else {
                    this.showAlert(result.error || 'Error confirming ROM scan', 'danger');
                }
            } else {
                const errorData = await response.json();
                this.showAlert(errorData.error || 'Error confirming ROM scan', 'danger');
            }
        } catch (error) {
            console.error('Error confirming ROM scan:', error);
            this.showAlert('Error confirming ROM scan', 'danger');
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
                console.error('Unified scan button not found');
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
                            } else {
                                // Reload the system to get updated game list
                                await this.loadRomSystem(this.currentSystem);
                                this.showAlert('ROM scan completed. Starting media scan...', 'success');
                            }
                            
                            // Always run media scan after ROM scan (regardless of confirmation status)
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
                                    
                                    console.log('Unified scan completed:', { rom: result, media: mediaResult });
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
            console.error('Error during unified scan:', error);
            this.showAlert('Error during unified scan: ' + error.message, 'danger');
        } finally {
            // Restore button state
            if (button && originalText) {
                button.innerHTML = originalText;
                button.disabled = false;
                console.log('Button state restored');
            } else {
                console.error('Could not restore button state - button or originalText not available');
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
            console.error('Error loading gamelist differences:', error);
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

            // Call the save API
            const response = await fetch(`/api/rom-system/${this.currentSystem}/save-gamelist`, {
                method: 'POST'
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
            console.error('Error saving gamelist:', error);
            this.showAlert('Error saving gamelist: ' + error.message, 'danger');
        } finally {
            // Restore button state
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async deleteGame(game) {
        if (!confirm(`Are you sure you want to delete "${game.name}" (ROM: ${game.path})"?`)) return;

        try {
            // Delete associated ROM and media files
            const deletedFiles = await this.deleteGameFiles(game);
            
            // Remove from local array using ROM file path as unique identifier
            this.games = this.games.filter(g => g.path !== game.path);
            
            // Update gamelist.xml to remove deleted game
            await this.updateGamelistAfterDeletion([game.path]);
            
            // Refresh grid
            this.gridApi.setRowData(this.games);
            this.updateGamesCount();
            
            // Show success message
            const fileCount = deletedFiles.length;
            const message = `Successfully deleted game "${game.name}" and ${fileCount} associated file(s)`;
            this.showAlert(message, 'success');
            
            console.log(`Deleted game: ${game.name} (ROM: ${game.path})`);
            console.log(`Deleted files: ${deletedFiles.join(', ')}`);
            
        } catch (error) {
            console.error('Error deleting game:', error);
            this.showAlert('Error deleting game', 'danger');
        }
    }

    async saveGameChanges() {
        console.log('saveGameChanges called');
        console.log('Modified games size:', this.modifiedGames.size);
        console.log('Modified games:', Array.from(this.modifiedGames));
        console.log('Current system:', this.currentSystem);
        
        if (this.modifiedGames.size === 0) {
            this.showAlert('No changes to save', 'info');
            return;
        }

        try {
            console.log('Sending PUT request to save changes...');
            const response = await fetch(`/api/rom-system/${this.currentSystem}/gamelist`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    games: this.games
                })
            });
            
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);
            
            if (response.ok) {
                const result = await response.json();
                console.log('Save response:', result);
                
                this.modifiedGames.clear();
                this.showAlert('Changes saved successfully!', 'success');
                
                // Refresh the grid data to show updated values and resort
                await this.loadRomSystem(this.currentSystem);
                
                // Also refresh the grid cells to ensure proper display
                if (this.gridApi) {
                    this.gridApi.refreshCells();
                    console.log('Grid refreshed after saving changes');
                }
            } else {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                this.showAlert('Error saving changes', 'danger');
            }
        } catch (error) {
            console.error('Error saving changes:', error);
            this.showAlert('Error saving changes', 'danger');
        }
    }

    markGameAsModified(game) {
        console.log('Marking game as modified:', game);
        console.log('Game ID:', game.id);
        console.log('Game ID type:', typeof game.id);
        
        if (game.id !== undefined && game.id !== null) {
            const beforeSize = this.modifiedGames.size;
            this.modifiedGames.add(game.id);
            const afterSize = this.modifiedGames.size;
            console.log('Modified games set size before:', beforeSize, 'after:', afterSize);
            console.log('Modified games contents:', Array.from(this.modifiedGames));
        } else {
            console.error('Game has no ID:', game);
        }
    }



    clearFilters() {
        if (this.gridApi) {
            this.gridApi.setFilterModel(null);
        }
    }

    async showMediaPreview(game) {
        if (!game) return;

        // Prevent multiple simultaneous calls
        if (this.showingMediaPreview) {
            console.log('Media preview already in progress, skipping...');
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
        console.log('Media preview fields:', mediaFields);
        console.log('Media mappings cache:', this.mediaMappingsCache);
        
        // Process each field only once
        const processedFields = new Set();
        mediaFields.forEach(field => {
            if (processedFields.has(field)) {
                console.warn('Duplicate field detected:', field);
                return; // Skip duplicate fields
            }
            processedFields.add(field);
            
            const mediaItem = document.createElement('div');
            mediaItem.className = 'media-preview-item';
            
            if (game[field] && game[field].trim()) {
                // Media exists - show the actual media
                const mediaPath = game[field];
                
                if (field === 'video' || mediaPath.endsWith('.mp4')) {
                    mediaItem.innerHTML = `
                        <div style="position: relative;">
                            <video width="450" height="450" controls style="object-fit: contain; background-color: #f8f9fa;">
                                <source src="/roms/${this.currentSystem}/${mediaPath}" type="video/mp4">
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
                            <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px; margin-left: 5px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                <i class="bi bi-download"></i>
                            </button>
                        </div>
                    `;
                    
                    // Add error handler for video
                    const video = mediaItem.querySelector('video');
                    video.addEventListener('error', () => {
                        this.showFileMissingPlaceholder(mediaItem, field, mediaPath, game);
                    });
                } else {
                    mediaItem.innerHTML = `
                        <div style="position: relative;">
                            <img src="/roms/${this.currentSystem}/${mediaPath}" alt="${field}" width="150" height="150" style="object-fit: contain; background-color: #f8f9fa;">
                            <div class="media-replace-overlay" style="position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.7); color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; opacity: 0; transition: opacity 0.2s ease;">
                                <i class="bi bi-arrow-clockwise"></i>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                            <small class="text-center flex-grow-1">${field}</small>
                            <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px; margin-left: 5px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                                <i class="bi bi-download"></i>
                            </button>
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
                    <div class="media-placeholder" style="width: ${placeholderSize}; height: ${placeholderSize}; background-color: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d; font-size: 0.8rem; text-align: center; cursor: pointer; transition: all 0.2s ease;">
                        <div>
                            <i class="bi ${iconClass}" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                            ${uploadText}
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mt-2" style="width: 100%; padding: 0 5px;">
                        <small class="text-center flex-grow-1">${field}</small>
                        <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px; margin-left: 5px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                            <i class="bi bi-download"></i>
                        </button>
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
                    mediaItem.querySelector('.media-placeholder').style.backgroundColor = '#f8f9fa';
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
                <button class="btn btn-outline-primary btn-sm" style="font-size: 0.6rem; padding: 1px 4px; margin-left: 5px;" title="Download from LaunchBox" onclick="gameManager.openLaunchBoxMediaModal(${JSON.stringify(game).replace(/"/g, '&quot;')}, '${field}')">
                    <i class="bi bi-download"></i>
                </button>
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
        
        console.log(`Selected media: ${field} for game ${game.name}. Total selected: ${this.selectedMedia.length}`);
        
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
        
        console.log(`Selected edit modal media: ${field} for game ${game.name}. Total selected: ${this.selectedMedia.length}`);
        
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
    }
    
    initializeEditModalIgdbSearch() {
        const modalFindIgdbMatchBtn = document.getElementById('modalFindIgdbMatchBtn');
        if (modalFindIgdbMatchBtn) {
            modalFindIgdbMatchBtn.addEventListener('click', () => {
                this.showGameEditIgdbSearch();
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
            console.error('YouTube URL field not found');
            return;
        }
        
        const youtubeUrl = youtubeUrlField.value.trim();
        if (!youtubeUrl) {
            console.log('YouTube URL is empty, doing nothing');
            return;
        }
        
        // Validate that it's a YouTube URL
        if (!youtubeUrl.includes('youtube')) {
            console.log('URL does not contain "youtube", doing nothing');
            return;
        }
        
        console.log('Opening YouTube preview for URL:', youtubeUrl);
        
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
                console.log('Manual crop button clicked for game:', game.name);
                this.openManualCropModal(game);
            };
            
            manualCropBtn.addEventListener('click', manualCropBtn._manualCropHandler);
        }
    }
    
    async openManualCropModal(game) {
        // Prevent multiple simultaneous calls
        if (this.isExtractingFrame) {
            console.log('Frame extraction already in progress, ignoring duplicate call');
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
        console.log('Opening manual crop modal for video:', videoPath);
        
        // Convert relative path to absolute path
        let absoluteVideoPath = videoPath;
        if (videoPath.startsWith('./')) {
            // Construct absolute path from ROMS_FOLDER + system + relative path
            absoluteVideoPath = `/roms/${this.currentSystem}/${videoPath.substring(2)}`;
        }
        
        console.log('Absolute video path:', absoluteVideoPath);
        
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
            console.log('Starting frame extraction for:', videoPath);
            
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
            console.error('Error extracting first frame:', error);
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
                console.log('Cleaning up frame image:', this.currentFramePath);
                console.log('Sending delete request with frame_path:', this.currentFramePath);
                
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
                    console.log('Frame image cleaned up successfully');
                } else {
                    console.warn('Failed to cleanup frame image:', result.error);
                }
            } catch (error) {
                console.error('Error cleaning up frame image:', error);
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
            console.log('Container dimensions not ready, using fallback sizing');
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
        
        console.log('Calculated image size:', {
            containerWidth,
            containerHeight,
            naturalWidth,
            naturalHeight,
            aspectRatio,
            targetWidth: Math.round(targetWidth),
            targetHeight: Math.round(targetHeight),
            fallbackUsed: containerWidth === 800 && containerHeight === 600
        });
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
        
        console.log('Applying crop with dimensions:', cropDimensions);
        console.log('Current crop game:', this.currentCropGame);
        console.log('Current system:', this.currentSystem);
        console.log('Current crop video path:', this.currentCropVideoPath);
        
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
        
        console.log('Sending request data:', requestData);
        
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
            console.error('Error applying crop:', error);
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
        console.log('Task completion received:', data);
        
        // Check if this is a manual crop task completion
        if (data.task_type === 'manual_crop' && data.success) {
            console.log('Manual crop task completed successfully');
            
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
            console.log('IGDB scraping task completed:', data);
            console.log('Current system:', this.currentSystem);
            console.log('Task system name:', data.system_name);
            console.log('Task success:', data.success);
            console.log('Task stopped:', data.stopped);
            
            // Refresh the task grid to show updated task status
            this.refreshTaskGrid();
            
            // Refresh the gamelist grid if we're viewing the same system that was scraped
            // This applies to both successful completion and stopped tasks (since gamelist is saved in both cases)
            if (data.system_name && data.system_name === this.currentSystem) {
                console.log('✅ System names match - refreshing gamelist grid for system:', data.system_name);
                console.log('🔄 About to call loadRomSystem...');
                
                // Add a delay to ensure gamelist.xml file write has completed
                setTimeout(() => {
                    this.loadRomSystem(this.currentSystem).then(() => {
                        console.log('✅ Gamelist grid refreshed after IGDB task completion');
                    }).catch((error) => {
                        console.error('❌ Error refreshing gamelist grid:', error);
                    });
                }, 1000); // 1000ms delay to ensure file write is complete
            } else {
                console.log('❌ System names do not match - skipping gamelist refresh');
                console.log('  - Current system:', this.currentSystem);
                console.log('  - Task system:', data.system_name);
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
            console.log('ScreenScraper scraping task completed:', data);
            console.log('Current system:', this.currentSystem);
            console.log('Task system name:', data.system_name);
            console.log('Task success:', data.success);
            console.log('Task stopped:', data.stopped);
            
            // Refresh the task grid to show updated task status
            this.refreshTaskGrid();
            
            // Refresh the gamelist grid if we're viewing the same system that was scraped
            // This applies to both successful completion and stopped tasks (since gamelist is saved in both cases)
            if (data.system_name && data.system_name === this.currentSystem) {
                console.log('✅ System names match - refreshing gamelist grid for system:', data.system_name);
                console.log('🔄 About to call loadRomSystem...');
                
                // Add a delay to ensure gamelist.xml file write has completed
                setTimeout(() => {
                    this.loadRomSystem(this.currentSystem).then(() => {
                        console.log('✅ Gamelist grid refreshed after ScreenScraper task completion');
                    }).catch((error) => {
                        console.error('❌ Error refreshing gamelist grid:', error);
                    });
                }, 1000); // 1000ms delay to ensure file write is complete
            } else {
                console.log('❌ System names do not match - skipping gamelist refresh');
                console.log('  - Current system:', this.currentSystem);
                console.log('  - Task system:', data.system_name);
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
    }
    
    async refreshTaskGrid() {
        try {
            console.log('Refreshing task grid...');
            const response = await fetch('/api/tasks');
            if (response.ok) {
                const tasks = await response.json();
                this.displayTasksInGrid(tasks);
                console.log('Task grid refreshed successfully');
            } else {
                console.error('Failed to fetch tasks for grid refresh');
            }
        } catch (error) {
            console.error('Error refreshing task grid:', error);
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
            editModal.addEventListener('hidden.bs.modal', () => {
                console.log('Edit modal closed, cleaning up...');
                pauseAllVideos();
                // Clear any media selection
                this.clearMediaSelection();
                // Reset any modal-specific state
                this.selectedMedia = [];
                // Clear any form data if needed
                const form = document.getElementById('editGameForm');
                if (form) { form.reset(); }
                console.log('Edit modal cleanup completed');
            });
            // Add focus management when modal is about to be hidden
            editModal.addEventListener('hide.bs.modal', () => {
                console.log('Edit modal hiding, managing focus...');
                pauseAllVideos();
                const safeElement = document.querySelector('#gamesCount') || document.body;
                if (safeElement) { safeElement.focus(); }
                const focusedElement = editModal.querySelector(':focus');
                if (focusedElement) { focusedElement.blur(); }
            });
        }
    }
    
    initializeCacheConfigurationModal() {
        console.log('Initializing cache configuration modal...');
        
        // Add event listener for opening cache modal
        const openCacheModal = document.getElementById('openCacheModal');
        if (openCacheModal) {
            console.log('Found openCacheModal element, adding click listener');
            openCacheModal.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Cache modal link clicked');
                this.openCacheConfigurationModal();
            });
        } else {
            console.warn('openCacheModal element not found');
        }
        
        // Add event listener for opening LaunchBox modal
        const openLaunchboxModal = document.getElementById('openLaunchboxModal');
        if (openLaunchboxModal) {
            console.log('Found openLaunchboxModal element, adding click listener');
            openLaunchboxModal.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('LaunchBox modal link clicked');
                this.openLaunchboxConfigurationModal();
            });
        } else {
            console.warn('openLaunchboxModal element not found');
        }

        // Add event listener for opening IGDB modal
        const openIgdbModal = document.getElementById('openIgdbModal');
        if (openIgdbModal) {
            console.log('Found openIgdbModal element, adding click listener');
            openIgdbModal.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('IGDB modal link clicked');
                this.openIgdbConfigurationModal();
            });
        } else {
            console.warn('openIgdbModal element not found');
        }

        // Add event listener for opening ScreenScraper modal
        const openScreenscraperModal = document.getElementById('openScreenscraperModal');
        if (openScreenscraperModal) {
            console.log('Found openScreenscraperModal element, adding click listener');
            openScreenscraperModal.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('ScreenScraper modal link clicked');
                this.openScreenscraperConfigurationModal();
            });
        } else {
            console.warn('openScreenscraperModal element not found');
        }

        // Add event listener for opening Systems modal
        const openSystemsModal = document.getElementById('openSystemsModal');
        if (openSystemsModal) {
            console.log('Found openSystemsModal element, adding click listener');
            openSystemsModal.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Systems modal link clicked');
                this.openSystemsConfigurationModal();
            });
        } else {
            console.warn('openSystemsModal element not found');
        }

        
        // Add event listener for update metadata button
        const updateMetadataBtn = document.getElementById('updateMetadataBtn');
        if (updateMetadataBtn) {
            console.log('Found updateMetadataBtn element, adding click listener');
            updateMetadataBtn.addEventListener('click', () => {
                console.log('Update metadata button clicked');
                this.updateMetadataXml();
            });
        } else {
            console.warn('updateMetadataBtn element not found');
        }
        

    }
    

    
    openCacheConfigurationModal() {
        // Load cache information before opening modal
        this.loadCacheInformation();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('cacheConfigurationModal'));
        modal.show();
    }
    
    openLaunchboxConfigurationModal() {
        // Load current settings before opening modal
        this.loadLaunchboxSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('launchboxConfigurationModal'));
        modal.show();
    }
    
    loadLaunchboxSettings() {
        // Load saved settings from cookies
        const savedForceDownload = this.getCookie('forceDownloadImages');
        const savedOverwriteTextFields = this.getCookie('launchboxOverwriteTextFields');
        
        console.log('🔧 DEBUG: loadLaunchboxSettings - savedForceDownload:', savedForceDownload);
        console.log('🔧 DEBUG: loadLaunchboxSettings - savedOverwriteTextFields:', savedOverwriteTextFields);
        
        // Update modal checkboxes with saved values
        const forceDownloadCheckbox = document.getElementById('forceDownloadImagesModal');
        const overwriteTextFieldsCheckbox = document.getElementById('overwriteTextFieldsLaunchbox');
        
        if (forceDownloadCheckbox) {
            forceDownloadCheckbox.checked = savedForceDownload === 'true';
        }
        
        if (overwriteTextFieldsCheckbox) {
            if (savedOverwriteTextFields !== null) {
                overwriteTextFieldsCheckbox.checked = savedOverwriteTextFields === 'true';
                console.log('🔧 DEBUG: loadLaunchboxSettings - Setting overwriteTextFields checkbox to:', savedOverwriteTextFields === 'true', '(saved value:', savedOverwriteTextFields, ')');
            } else {
                // No saved value, set to default (unchecked)
                overwriteTextFieldsCheckbox.checked = false;
                console.log('🔧 DEBUG: loadLaunchboxSettings - No saved value, setting overwriteTextFields checkbox to default (false)');
            }
        }
    }
    
    openIgdbConfigurationModal() {
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
                console.error('Failed to load IGDB credentials status');
            }
        } catch (error) {
            console.error('Error loading IGDB credentials status:', error);
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
            console.error('Error saving IGDB credentials:', error);
            alert('Error saving credentials. Please try again.');
        }
    }

    // ScreenScraper Configuration Functions
    openScreenscraperConfigurationModal() {
        // Load current settings before opening modal
        this.loadScreenscraperSettings();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('screenscraperConfigurationModal'));
        modal.show();
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
                console.error('Failed to load ScreenScraper credentials status');
            }
        } catch (error) {
            console.error('Error loading ScreenScraper credentials status:', error);
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
                console.error('Failed to load ScreenScraper credentials values');
            }
        } catch (error) {
            console.error('Error loading ScreenScraper credentials values:', error);
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
                console.error('Failed to load IGDB credentials values');
            }
        } catch (error) {
            console.error('Error loading IGDB credentials values:', error);
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
            console.error('Error saving ScreenScraper credentials:', error);
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
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const savedValue = this.getCookie(`igdbField_${field}`);
                const checkbox = document.getElementById(`igdbField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                
                if (checkbox) {
                    // Default to checked if no saved value (first time)
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                }
            });
        } catch (error) {
            console.error('Error loading IGDB field settings:', error);
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'name', 'summary', 'developer', 'publisher', 'genre', 
                'rating', 'players', 'release_date', 'youtubeurl', 'cover', 'screenshots', 'artworks', 'logos'
            ];
            
            fallbackFields.forEach(field => {
                const savedValue = this.getCookie(`igdbField_${field}`);
                const checkbox = document.getElementById(`igdbField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                
                if (checkbox) {
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                }
            });
        }
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
                const checkbox = document.getElementById(`igdbField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                if (checkbox) {
                    this.setCookie(`igdbField_${field}`, checkbox.checked);
                }
            });
        } catch (error) {
            console.error('Error saving IGDB field settings:', error);
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'name', 'summary', 'developer', 'publisher', 'genre', 
                'rating', 'players', 'release_date', 'cover', 'screenshots', 'artworks', 'logos'
            ];
            
            fallbackFields.forEach(field => {
                const checkbox = document.getElementById(`igdbField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
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
            const textFields = Object.keys(config.screenscraper?.mapping || {});
            const mediaFields = Object.keys(config.screenscraper?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Load saved field selections from cookies
            allFields.forEach(field => {
                const savedValue = this.getCookie(`screenscraperField_${field}`);
                const checkbox = document.getElementById(`screenscraperField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                
                if (checkbox) {
                    // Default to checked if no saved value (first time)
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                }
            });
        } catch (error) {
            console.error('Error loading ScreenScraper field settings:', error);
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
            const textFields = Object.keys(config.screenscraper?.mapping || {});
            const mediaFields = Object.keys(config.screenscraper?.image_type_mappings || {});
            const allFields = [...textFields, ...mediaFields];
            
            // Save field selections to cookies
            allFields.forEach(field => {
                const checkbox = document.getElementById(`screenscraperField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                if (checkbox) {
                    this.setCookie(`screenscraperField_${field}`, checkbox.checked);
                }
            });
        } catch (error) {
            console.error('Error saving ScreenScraper field settings:', error);
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
            
            const selectedFields = [];
            allFields.forEach(field => {
                const checkbox = document.getElementById(`igdbField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                if (checkbox && checkbox.checked) {
                    selectedFields.push(field);
                }
            });
            
            return selectedFields;
        } catch (error) {
            console.error('Error getting selected IGDB fields:', error);
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'name', 'summary', 'developer', 'publisher', 'genre', 
                'rating', 'players', 'release_date', 'cover', 'screenshots', 'artworks', 'logos'
            ];
            
            const selectedFields = [];
            fallbackFields.forEach(field => {
                const checkbox = document.getElementById(`igdbField${field.charAt(0).toUpperCase() + field.slice(1).replace('_', '')}`);
                if (checkbox && checkbox.checked) {
                    selectedFields.push(field);
                }
            });
            
            return selectedFields;
        }
    }

    async getSelectedScreenscraperFields() {
        console.log('🔍 Starting ScreenScraper field selection...');
        
        // Fetch config to get dynamic field mappings
        const response = await fetch('/api/config');
        const config = await response.json();
        console.log('📋 Full config received:', config);
        console.log('📋 ScreenScraper config:', config.screenscraper);
        
        // Get ScreenScraper field mappings from config
        // ScreenScraper has image_type_mappings that map API field names to gamelist field names
        // We need to use the VALUES (gamelist field names) not the KEYS (API field names)
        const mediaFields = Object.values(config.screenscraper?.image_type_mappings || {});
        
        // For text fields, we need to use the hardcoded field names that match the HTML checkboxes
        // since ScreenScraper doesn't have a text field mapping in the config
        const textFields = ['name', 'description', 'developer', 'publisher', 'genre', 'rating', 'players', 'release_date'];
        
        const allFields = [...textFields, ...mediaFields];
        
        console.log('📝 Text fields from config:', textFields);
        console.log('🖼️ Media fields from config:', mediaFields);
        console.log('📋 All fields combined:', allFields);
        
        const selectedFields = [];
        
        allFields.forEach(field => {
            // Convert field name to checkbox ID format: field_name -> FieldName
            const fieldId = field.split('_').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join('');
            const checkboxId = `screenscraperField${fieldId}`;
            const checkbox = document.getElementById(checkboxId);
            
            console.log(`🔍 Field: "${field}" -> Checkbox ID: "${checkboxId}" -> Element found: ${!!checkbox} -> Checked: ${checkbox?.checked}`);
            
            if (checkbox && checkbox.checked) {
                selectedFields.push(field);
                console.log(`✅ Added field: "${field}"`);
            } else if (!checkbox) {
                console.log(`❌ Checkbox not found for field: "${field}" (ID: "${checkboxId}")`);
            } else {
                console.log(`⏸️ Field "${field}" not checked`);
            }
        });
        
        console.log('🎯 Final selected fields:', selectedFields);
        console.log('🎯 Selected fields count:', selectedFields.length);
        
        // Debug: Check all ScreenScraper checkboxes in the DOM
        console.log('🔍 Debug: Checking all ScreenScraper checkboxes in DOM...');
        const allCheckboxes = document.querySelectorAll('input[class*="screenscraper-field-checkbox"]');
        console.log('🔍 Found checkboxes:', allCheckboxes.length);
        allCheckboxes.forEach(checkbox => {
            console.log(`🔍 Checkbox ID: "${checkbox.id}" -> Checked: ${checkbox.checked}`);
        });
        
        return selectedFields;
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
                    // Default to checked if no saved value (first time)
                    checkbox.checked = savedValue === 'true' || savedValue === null;
                }
            });
        } catch (error) {
            console.error('Error loading LaunchBox field settings:', error);
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
            console.error('Error saving LaunchBox field settings:', error);
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
            
            const selectedFields = [];
            allFields.forEach(field => {
                const checkbox = document.getElementById(`launchboxField${field.replace(/[^a-zA-Z0-9]/g, '')}`);
                if (checkbox && checkbox.checked) {
                    selectedFields.push(field);
                }
            });
            
            return selectedFields;
        } catch (error) {
            console.error('Error getting selected LaunchBox fields:', error);
            // Fallback to hardcoded fields if config fetch fails
            const fallbackFields = [
                'Name', 'Overview', 'Developer', 'Publisher', 'Genres', 
                'CommunityRating', 'MaxPlayers', 'Box - Front', 'Box - Back', 'Box - 3D',
                'Clear Logo', 'Screenshot - Game Title', 'Screenshot - Gameplay',
                'Fanart - Background', 'Cart - Front'
            ];
            
            const selectedFields = [];
            fallbackFields.forEach(field => {
                const checkbox = document.getElementById(`launchboxField${field.replace(/[^a-zA-Z0-9]/g, '')}`);
                if (checkbox && checkbox.checked) {
                    selectedFields.push(field);
                }
            });
            
            return selectedFields;
        }
    }
    
    openSystemsConfigurationModal() {
        // Load systems data before opening modal
        this.loadSystemsData();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('systemsConfigurationModal'));
        modal.show();
    }
    
    async loadSystemsData() {
        try {
            const response = await fetch('/api/systems');
            const data = await response.json();
            
            if (data.success) {
                this.populateSystemsTable(data.systems);
            } else {
                console.error('Failed to load systems:', data.error);
                this.showAlert('Failed to load systems data', 'danger');
            }
        } catch (error) {
            console.error('Error loading systems:', error);
            this.showAlert('Error loading systems data', 'danger');
        }
    }
    
    async populateSystemsTable(systems) {
        const tbody = document.getElementById('systemsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Load LaunchBox platforms for combobox
        const platforms = await this.loadLaunchBoxPlatforms();
        
        Object.entries(systems).forEach(([systemName, systemData]) => {
            const row = document.createElement('tr');
            
            // Create platform combobox options
            const platformOptions = platforms.map(platform => 
                `<option value="${platform}" ${platform === systemData.launchbox ? 'selected' : ''}>${platform}</option>`
            ).join('');
            
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
                    <select class="form-select form-select-sm platform-select" 
                            data-system="${systemName}"
                            data-field="launchbox">
                        <option value="">Select Platform...</option>
                        ${platformOptions}
                    </select>
                </td>
                <td>
                    <input type="text" 
                           class="form-control form-control-sm extensions-input" 
                           value="${Array.isArray(systemData.extensions) ? systemData.extensions.join(', ') : ''}" 
                           placeholder="Extensions (comma-separated)"
                           data-system="${systemName}"
                           data-field="extensions">
                </td>
                <td></td>
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
                console.error('Failed to load LaunchBox platforms:', data.error);
                return [];
            }
        } catch (error) {
            console.error('Error loading LaunchBox platforms:', error);
            return [];
        }
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
                extensions: Array.isArray(currentSystem.extensions) ? currentSystem.extensions : []
            };
            
            // Update the specific field
            if (field === 'launchbox') {
                updateData.launchbox_platform = value.trim();
            } else if (field === 'extensions') {
                // Parse extensions from comma-separated string
                updateData.extensions = value.trim() ? 
                    value.split(',').map(ext => ext.trim()).filter(ext => ext) : [];
            }
            
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
            console.error('Error saving inline field:', error);
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
            console.error('Error deleting system:', error);
            this.showAlert('Error deleting system', 'danger');
        }
    }
    
    initializeSystemsModal() {
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
            // Handle platform select changes
            systemsTable.addEventListener('change', (e) => {
                if (e.target.classList.contains('platform-select')) {
                    const systemName = e.target.dataset.system;
                    const value = e.target.value;
                    this.saveInlineField(systemName, 'launchbox', value);
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
            console.error('Error adding system:', error);
            this.showAlert('Error adding system', 'danger');
        }
    }
    
    initializeAppConfigurationModal() {
        console.log('Initializing application configuration modal...');
        
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
        
        // Add event listener for IGDB credentials save button
        const saveIgdbCredentialsBtn = document.getElementById('saveIgdbCredentialsBtn');
        if (saveIgdbCredentialsBtn) {
            saveIgdbCredentialsBtn.addEventListener('click', () => {
                this.saveIgdbCredentials();
            });
        }
        
        // Add event listener for ScreenScraper credentials save button
        const saveScreenscraperCredentialsBtn = document.getElementById('saveScreenscraperCredentialsBtn');
        if (saveScreenscraperCredentialsBtn) {
            saveScreenscraperCredentialsBtn.addEventListener('click', () => {
                this.saveScreenscraperCredentials();
            });
        }
    }
    
    openAppConfigurationModal() {
        console.log('Opening application configuration modal...');
        
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
                
                // Load ScreenScraper credentials
                await this.loadScreenscraperCredentialsStatus();
                await this.loadScreenscraperCredentialsValues();
                
                // Load IGDB credentials
                await this.loadIgdbCredentialsStatus();
                await this.loadIgdbCredentialsValues();
                
                console.log('Configuration loaded:', config);
            } else {
                console.error('Failed to load configuration');
            }
        } catch (error) {
            console.error('Error loading configuration:', error);
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
                max_tasks_to_keep: parseInt(document.getElementById('maxTasksToKeep').value)
            };
            
            console.log('Saving configuration:', configData);
            
            const response = await fetch('/api/config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(configData)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Configuration saved:', result);
                
                // Show success message
                this.showToast('Configuration saved successfully! Server restart required for path changes.', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('appConfigurationModal'));
                modal.hide();
            } else {
                const error = await response.text();
                console.error('Failed to save configuration:', error);
                this.showToast('Failed to save configuration', 'error');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showToast('Error saving configuration', 'error');
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
                        console.log('Cache stats received:', data.cache_stats);
                        document.getElementById('cacheGamesCount').textContent = data.cache_stats.games_count.toLocaleString();
                        document.getElementById('cacheAltNamesCount').textContent = data.cache_stats.alt_names_count.toLocaleString();
                        document.getElementById('cacheGameImagesCount').textContent = data.cache_stats.game_images_count.toLocaleString();
                    } else {
                        console.warn('No cache_stats in response:', data);
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
            console.log('Metadata updated successfully, refreshing cache...');
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
            console.error('Error updating metadata:', error);
            this.showAlert('Error updating metadata: ' + error.message, 'danger');
        } finally {
            // Restore button state
            updateBtn.disabled = false;
            updateBtn.innerHTML = originalText;
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
                                console.warn(`Some fields failed to delete for ${game.name}:`, result.failed_fields);
                            }
                        } else {
                            console.error(`Failed to delete media for ${game.name}:`, result.error);
                            errorCount += fields.length;
                        }
                    } else {
                        const error = await deleteResponse.json();
                        console.error(`Failed to delete media for ${game.name}:`, error.error);
                        errorCount += fields.length;
                    }
                } catch (error) {
                    console.error(`Error deleting media for ${game.name}:`, error);
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
            console.error('Error during multiple media deletion:', error);
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
            console.error('Error deleting media:', error);
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
                console.log('Gamelist.xml updated after media deletion');
            } else {
                console.warn('Failed to update gamelist.xml after media deletion');
            }
        } catch (error) {
            console.error('Error updating gamelist after media deletion:', error);
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
        const totalCount = this.games ? this.games.length : 0;
        
        // Update the games count to show selection
        const gamesCountElement = document.getElementById('gamesCount');
        if (gamesCountElement) {
            const beforeText = gamesCountElement.textContent;
            if (selectedCount > 0) {
                const newText = `${selectedCount}/${totalCount}`;
                gamesCountElement.textContent = newText;
                gamesCountElement.className = 'fw-bold';
                gamesCountElement.style.color = '#ffffff';
                gamesCountElement.style.fontWeight = 'bold';

            } else {
                gamesCountElement.textContent = totalCount;
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
                scrapButton.title = `Scrap entire collection (${totalCount} games)`;
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
            this.gridApi.setRowData(this.games);
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
        
        // First pass: collect all names and launchbox IDs
        this.games.forEach(game => {
            const name = game.name?.toLowerCase().trim();
            const launchboxId = game.launchboxid?.trim();
            
            if (name) {
                if (!seenNames.has(name)) {
                    seenNames.set(name, []);
                }
                seenNames.get(name).push(game);
            }
            
            if (launchboxId) {
                if (!seenLaunchboxIds.has(launchboxId)) {
                    seenLaunchboxIds.set(launchboxId, []);
                }
                seenLaunchboxIds.get(launchboxId).push(game);
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
        
        return duplicates;
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
    
    async deleteGameFiles(game) {
        const deletedFiles = [];
        
        console.log('deleteGameFiles called for game:', game);
        console.log('Game path:', game.path);
        console.log('Current system:', this.currentSystem);
        
        try {
            // Construct the proper ROM path that includes system directory
            if (game.path && game.path.trim() && this.currentSystem) {
                // game.path is just the filename, we need to construct the full relative path
                const fullRomPath = `${this.currentSystem}/${game.path}`;
                console.log('Constructed ROM file path for deletion:', fullRomPath);
                console.log('Returning array with path:', [fullRomPath]);
                // Return the full ROM path so it can be passed to updateGamelistAfterDeletion
                return [fullRomPath];
            } else {
                if (!this.currentSystem) {
                    console.warn('No current system found for ROM path construction');
                }
                if (!game.path || !game.path.trim()) {
                    console.warn('No ROM path found for game:', game);
                }
                return [];
            }
            
        } catch (error) {
            console.error('Error in deleteGameFiles:', error);
            return [];
        }
    }
    
    async updateGamelistAfterDeletion(deletedGameRomPaths) {
        try {
            console.log('updateGamelistAfterDeletion called with:', deletedGameRomPaths);
            console.log('Current system:', this.currentSystem);
            console.log('Games array length:', this.games.length);
            
            // Use the current system from the class instance
            if (!this.currentSystem) {
                console.warn('No ROM system found for gamelist update');
                return;
            }
            
            const requestBody = {
                games: this.games,
                delete_rom_paths: deletedGameRomPaths
            };
            console.log('Request body:', requestBody);
            console.log('delete_rom_paths array:', deletedGameRomPaths);
            console.log('Each path in delete_rom_paths:');
            deletedGameRomPaths.forEach((path, index) => {
                console.log(`  [${index}]: "${path}"`);
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
                   console.log('Gamelist.xml updated after deletion');
                   const result = await response.json();
                   console.log('Update result:', result);
                   
                   // Log file deletion results
                   if (result.deleted_files && result.deleted_files.length > 0) {
                       console.log('Successfully deleted files:', result.deleted_files);
                       result.deleted_files.forEach(file => {
                           console.log(`✅ ${file}`);
                       });
                   }
                   
                   if (result.failed_deletions && result.failed_deletions.length > 0) {
                       console.warn('Failed to delete some files:', result.failed_deletions);
                       result.failed_deletions.forEach(failed => {
                           console.warn(`❌ ${failed.path}: ${failed.error}`);
                       });
                   }
                   
                   // Show summary to user
                   if (result.deleted_count > 0) {
                       const successCount = result.deleted_files ? result.deleted_files.length : 0;
                       const failCount = result.failed_deletions ? result.failed_deletions.length : 0;
                       console.log(`🎯 Deletion summary: ${successCount} files deleted, ${failCount} failed`);
                   }
               } else {
                   console.warn('Failed to update gamelist.xml after deletion');
                   const errorText = await response.text();
                   console.warn('Error response:', errorText);
               }
            
        } catch (error) {
            console.error('Error updating gamelist after deletion:', error);
        }
    }
    
    syncNavigationIndex(game) {
        // Find the index of the game in the games array and update navigation index
        const index = this.games.findIndex(g => g.id === game.id);
        if (index !== -1) {
            this.currentNavigationIndex = index;
            console.log(`Navigation index synced to row ${index}: ${game.name}`);
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

            console.log(`Navigated ${direction} to displayed row ${targetIndex}: ${node.data.name} (media preview only)`);
        } catch (error) {
            console.error('Error navigating rows:', error);
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
            console.warn('Could not highlight navigated row:', error);
        }
    }

    enableButtons() {
        console.log('enableButtons called');
        document.getElementById('unifiedScanBtn').disabled = false;
        document.getElementById('saveGamelistBtn').disabled = false;

        document.getElementById('scrapLaunchboxBtn').disabled = false; // Allow full collection scraping
        document.getElementById('scrapIgdbBtn').disabled = false; // Allow IGDB scraping
        
        const screenscraperBtn = document.getElementById('scrapScreenscraperBtn');
        if (screenscraperBtn) {
            screenscraperBtn.disabled = false; // Allow ScreenScraper scraping
            console.log('ScreenScraper button enabled');
        } else {
            console.error('ScreenScraper button not found!');
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
            const selectedFields = await this.getSelectedIgdbFields();
            
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
                console.log('IGDB scraping started:', result);
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Error: ${result.error || 'Unknown error'}`, 'danger');
                console.error('IGDB scraping failed:', result);
            }
            
        } catch (error) {
            console.error('Error starting IGDB scraping:', error);
            this.showAlert(`❌ Error starting IGDB scraping: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapIgdbBtn');
            button.innerHTML = '<i class="bi bi-globe"></i> IGDB Scrap';
            button.disabled = false;
        }
    }

    async scrapScreenscraper() {
        console.log('scrapScreenscraper method called');
        console.log('Current system:', this.currentSystem);
        
        if (!this.currentSystem) {
            this.showAlert('Please select a system first', 'warning');
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
            console.log('🔍 Getting selected ScreenScraper fields...');
            const selectedFields = await this.getSelectedScreenscraperFields();
            console.log('📤 Selected ScreenScraper fields to send:', selectedFields);
            console.log('📤 Selected fields type:', typeof selectedFields);
            console.log('📤 Selected fields length:', selectedFields?.length);
            
            const requestBody = {
                selected_games: gamesToScrape.map(game => game.path),
                selected_fields: selectedFields
            };
            console.log('📤 Full request body:', requestBody);
            
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
                console.log('ScreenScraper task started:', result);
                
                // Refresh tasks to show the new task
                this.refreshTasks();
            } else {
                this.showAlert(`❌ Error: ${result.error || 'Unknown error'}`, 'danger');
                console.error('ScreenScraper task failed:', result);
            }
            
        } catch (error) {
            console.error('Error starting ScreenScraper task:', error);
            this.showAlert(`❌ Error starting ScreenScraper task: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            const button = document.getElementById('scrapScreenscraperBtn');
            button.innerHTML = '<i class="bi bi-search"></i> ScreenScraper';
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
        console.log(`toggleColumn called: field=${field}, visible=${visible}`);
        
        if (!this.gridApi) {
            console.log('No gridApi available');
            return;
        }
        
        const column = this.gridApi.getColumn(field);
        console.log(`Column object for ${field}:`, column);
        
        if (column) {
            console.log(`Setting column ${field} visibility to ${visible}`);
            this.gridApi.setColumnVisible(field, visible);
            
            console.log('Calling saveColumnState...');
            this.saveColumnState();
            
            // Show brief feedback that the change was saved
            const columnName = column.getColDef().headerName || field;
            this.showColumnChangeNotification(`${columnName} ${visible ? 'shown' : 'hidden'} - saved to preferences`);
        } else {
            console.log(`Column ${field} not found`);
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
        
        console.log('saveColumnState called');
        
        const columnState = {};
        const columnDefs = this.gridApi.getColumnDefs();
        console.log('Column definitions:', columnDefs);
        
        // Get all visible columns in their current order
        const allColumns = this.gridApi.getAllDisplayedColumns();
        const columnOrder = allColumns.map(col => col.getColId());
        console.log('All displayed columns:', allColumns);
        console.log('Column order:', columnOrder);
        
        columnDefs.forEach(colDef => {
            if (colDef.field && colDef.field !== 'checkbox') {
                const column = this.gridApi.getColumn(colDef.field);
                console.log(`Processing column ${colDef.field}:`, column);
                if (column) {
                    const isVisible = column.isVisible();
                    const orderIndex = columnOrder.indexOf(colDef.field);
                    console.log(`Column ${colDef.field}: visible=${isVisible}, order=${orderIndex}`);
                    
                    columnState[colDef.field] = {
                        visible: isVisible,
                        order: orderIndex
                    };
                }
            }
        });
        
        const cookieValue = JSON.stringify(columnState);
        console.log('Final column state object:', columnState);
        console.log('Cookie value to be set:', cookieValue);
        
        this.setCookie('columnState', cookieValue);
        
        // Verify cookie was set
        const savedCookie = this.getCookie('columnState');
        console.log('Cookie after setting:', savedCookie);
        console.log('Cookie verification:', savedCookie === cookieValue ? 'SUCCESS' : 'FAILED');
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
                console.error('Error loading column state:', error);
            }
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
                console.log('🔧 DEBUG: loadState - Setting overwriteTextFields checkbox to:', savedOverwriteTextFields === 'true', '(saved value:', savedOverwriteTextFields, ')');
            } else {
                // No saved value, set to default (unchecked)
                overwriteTextFieldsCheckbox.checked = false;
                console.log('🔧 DEBUG: loadState - No saved value, setting overwriteTextFields checkbox to default (false)');
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
                console.error(`setCookie: localStorage error for ${name}:`, error);
                // Fallback to cookie if localStorage fails
            }
        }
        
        // Debug logging for LaunchBox overwrite text fields
        if (name === 'launchboxOverwriteTextFields') {
            console.log(`🔧 DEBUG: setCookie called for ${name} with value:`, value, '(type:', typeof value, ')');
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
            console.warn(`setCookie: WARNING - Cookie ${name} is very large (${encodedValue.length} chars). Some browsers limit cookies to 4KB.`);
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
                console.error(`getCookie: localStorage error for ${name}:`, error);
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
                    console.log(`getCookie: Error decoding ${name}:`, e);
                    return cookieValue; // Return raw value if decoding fails
                }
            }
        }
        return null;
    }

    async showPartialMatches(gameName, preloadedMatches = null, modalType = 'global') {
        try {
            console.log('Showing partial matches for:', gameName);
            
            // Set modal as open for state management
            this.isModalOpen = true;
            console.log('Modal marked as open, polling paused');
            
            if (preloadedMatches) {
                // Use pre-loaded matches (from multi-game selection)
                console.log('Using pre-loaded matches:', preloadedMatches.length);
                console.log('Preloaded matches data:', preloadedMatches);
                // Show the modal first, then populate content
                this.showModalWithLoading(gameName, modalType);
                document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
                this.displayPartialMatchModal(gameName, preloadedMatches, modalType);
            } else {
                // Fetch matches from API (single game mode)
                this.showModalWithLoading(gameName, modalType);
                
                const systemName = modalType === 'gameEdit' ? this.currentGameData.system : this.currentSystem;
                const response = await fetch('/api/get-top-matches', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ game_name: gameName, system_name: systemName })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                console.log('Top matches received:', data);
                
                if (data.success) {
                    // Hide loading spinner and display matches
                    document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
                    this.displayPartialMatchModal(gameName, data.matches, modalType);
                } else {
                    // Hide loading spinner and show error
                    document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
                    this.showAlert('Error getting matches: ' + data.error, 'danger');
                    // Reset modal state on error
                    this.isModalOpen = false;
                }
            }
        } catch (error) {
            console.error('Error getting top matches:', error);
            // Hide loading spinner and show error
            document.getElementById(modalType === 'gameEdit' ? 'gameEditLoadingSpinner' : 'globalLoadingSpinner').style.display = 'none';
            this.showAlert('Error getting matches: ' + error.message, 'danger');
            // Reset modal state on error
            this.isModalOpen = false;
        }
    }

    showModalWithLoading(gameName, modalType = 'global') {
        console.log('Showing modal with loading state for:', gameName, 'modalType:', modalType);
        
        // Set original game name
        const gameNameElementId = modalType === 'gameEdit' ? 'gameEditOriginalGameName' : 'globalOriginalGameName';
        document.getElementById(gameNameElementId).textContent = gameName;
        
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
            console.error('Modal element not found!');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        
        // Only add event listener once
        if (!this.modalEventListenersAdded) {
            modalElement.addEventListener('hidden.bs.modal', () => {
                console.log('Modal hidden event triggered');
                
                // Check if we're in multi-game mode and this is not the last game
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1 && this.currentBestMatchIndex < this.pendingBestMatchResults.length - 1) {
                    console.log('Multi-game mode active, not resetting state');
                    return;
                }
                
                // If we're on the last game or single game, allow normal modal closure
                console.log('Last game or single game - allowing modal closure');
                
                // Force reset all state to prevent UI from getting stuck
                this.resetUIState();
                
                console.log('Modal closed, state reset, polling resumed');
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
                console.log('Cancel button clicked - manually hiding modal');
                modal.hide();
            });
        }
        
        // Show the modal
        modal.show();
        
        // Add direct event listener to close button to ensure state is reset
        const closeBtn = modalElement.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                console.log('Close button (X) clicked - resetting modal state');
                this.isModalOpen = false;
                this.resetUIState();
            });
        }
        
        console.log('Modal shown with loading state');
    }

    displayPartialMatchModal(originalGameName, matches, modalType = 'global') {
        console.log('displayPartialMatchModal called with:', originalGameName, matches);
        
        // Show/hide navigation buttons based on modal type and whether we're processing multiple games
        if (modalType === 'global') {
            const nextGameBtn = document.getElementById('globalNextGameBtn');
            const prevGameBtn = document.getElementById('globalPrevGameBtn');
            
            if (nextGameBtn) {
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1 && this.currentBestMatchIndex < this.pendingBestMatchResults.length - 1) {
                    nextGameBtn.style.display = 'inline-block';
                    nextGameBtn.onclick = () => this.moveToNextGame();
                    console.log(`Game ${this.currentBestMatchIndex + 1} of ${this.pendingBestMatchResults.length} - Next Game button visible`);
                } else {
                    nextGameBtn.style.display = 'none';
                    if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1) {
                        console.log(`Game ${this.currentBestMatchIndex + 1} of ${this.pendingBestMatchResults.length} - Last game, Next Game button hidden`);
                    } else {
                        console.log('Single game mode - Next Game button hidden');
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
        const originalGame = this.games.find(game => game.name === originalGameName);
        
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
        this.selectedMatchIndex = -1;
        
        // Clear previous matches
        const matchesListId = modalType === 'gameEdit' ? 'gameEditMatchesList' : 'globalMatchesList';
        const matchesList = document.getElementById(matchesListId);
        matchesList.innerHTML = '';
        
        // Generate match cards
        matches.forEach((match, index) => {
            const matchCard = this.createMatchCard(match, index);
            matchesList.appendChild(matchCard);
        });
        
        // Apply button is no longer needed - using double-click instead
        
        console.log('Modal content populated with matches');
    }

    createMatchCard(match, index) {
        console.log('createMatchCard called with:', match, index);
        
        const scoreClass = match.score >= 0.9 ? 'bg-success' : 
                          match.score >= 0.7 ? 'bg-warning' : 'bg-danger';
        
        const matchTypeIcon = match.match_type === 'alternate' ? 
            '<i class="bi bi-arrow-repeat text-info" title="Matched via alternate name"></i>' : 
            '<i class="bi bi-check-circle text-success" title="Matched via main name"></i>';
        
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
            
            console.log('Match selected:', index, 'Match data:', match);
        });
        
        // Add double-click handler to apply the match
        card.addEventListener('dblclick', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // Set the selected match
            this.selectedMatchIndex = index;
            
            // Apply the match directly
            this.applySelectedMatch(this.currentModalContext || 'global');
            
            console.log('Match double-clicked and applied:', index, 'Match data:', match);
        });
        
        console.log('Match card created:', card);
        return card;
    }

    async applySelectedMatch(modalType = 'global') {
        console.log('applySelectedMatch called with selectedMatchIndex:', this.selectedMatchIndex);
        console.log('currentMatches:', this.currentMatches);
        console.log('currentOriginalGameName:', this.currentOriginalGameName);
        
        if (this.selectedMatchIndex === -1) {
            console.log('No match selected, returning');
            return;
        }
        
        if (!this.currentMatches || !Array.isArray(this.currentMatches)) {
            console.error('currentMatches is not an array:', this.currentMatches);
            this.showAlert('Error: No matches available', 'danger');
            return;
        }
        
        if (this.selectedMatchIndex >= this.currentMatches.length) {
            console.error('selectedMatchIndex out of bounds:', this.selectedMatchIndex, 'vs', this.currentMatches.length);
            this.showAlert('Error: Invalid match selection', 'danger');
            return;
        }
        
        const selectedMatch = this.currentMatches[this.selectedMatchIndex];
        const originalGameName = this.currentOriginalGameName;
        
        console.log('Applying match:', selectedMatch, 'to game:', originalGameName);
        
        try {
            // Check if this is a partial match from scraping
            if (this.currentScrapingRequest) {
                // Apply partial match from scraping queue
                await this.applyPartialMatchFromScraping(selectedMatch, originalGameName);
            } else {
                // Check if we're in multi-game mode
                if (this.pendingBestMatchResults && this.pendingBestMatchResults.length > 1) {
                    // Check if this is the last game
                    if (this.currentBestMatchIndex >= this.pendingBestMatchResults.length - 1) {
                        // Last game - apply match and close modal
                        console.log('Last game in multi-game mode - closing modal after apply');
                        await this.applyRegularMatch(selectedMatch, originalGameName, true, modalType);
                        
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
                        console.log('Not the last game - moving to next game');
                        await this.applyRegularMatch(selectedMatch, originalGameName, false, modalType);
                        this.moveToNextGame();
                    }
                } else {
                    // Single game mode - close modal normally
                    await this.applyRegularMatch(selectedMatch, originalGameName, true, modalType);
                }
            }
            
        } catch (error) {
            console.error('Error applying match:', error);
            this.showAlert('Error applying match: ' + error.message, 'danger');
        }
    }
    
    async applyPartialMatchFromScraping(selectedMatch, originalGameName) {
        try {
            const requestData = this.currentScrapingRequest;
            
            // Prepare match data for the API
            const matchData = {};
            if (selectedMatch.name) matchData.name = selectedMatch.name;
            if (selectedMatch.overview) matchData.desc = selectedMatch.overview;
            if (selectedMatch.developer) matchData.developer = selectedMatch.developer;
            if (selectedMatch.publisher) matchData.publisher = selectedMatch.publisher;
            if (selectedMatch.genre) matchData.genre = selectedMatch.genre;
            if (selectedMatch.rating) matchData.rating = selectedMatch.rating;
            if (selectedMatch.players) matchData.players = selectedMatch.players;
            if (selectedMatch.database_id) matchData.launchboxid = selectedMatch.database_id;
            
            // Send to backend API
            const response = await fetch('/api/apply-partial-match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    game_name: originalGameName,
                    match_data: matchData,
                    system_name: requestData.system_name
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.success) {
                // Update local game data
                const gameIndex = this.games.findIndex(game => game.name === originalGameName);
                if (gameIndex !== -1) {
                    const originalGame = this.games[gameIndex];
                    const updatedGame = { ...originalGame };
                    
                    // Apply fields from the match
                    if (selectedMatch.name) updatedGame.name = selectedMatch.name;
                    if (selectedMatch.overview) updatedGame.desc = selectedMatch.overview;
                    if (selectedMatch.developer) updatedGame.developer = selectedMatch.developer;
                    if (selectedMatch.publisher) updatedGame.publisher = selectedMatch.publisher;
                    if (selectedMatch.genre) updatedGame.genre = selectedMatch.genre;
                    if (selectedMatch.rating) updatedGame.rating = selectedMatch.rating;
                    if (selectedMatch.players) updatedGame.players = selectedMatch.players;
                    if (selectedMatch.database_id) updatedGame.launchboxid = selectedMatch.database_id;
                    
                    // Update the games array
                    this.games[gameIndex] = updatedGame;
                    
                    // Mark game as modified
                    this.markGameAsModified(updatedGame);
                    
                    // Refresh grid to show updated data
                    this.refreshGridData();
                    
                    console.log('Grid refreshed with updated game data');
                }
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('partialMatchModal'));
                modal.hide();
                
                // Show success message
                this.showAlert(`Successfully applied partial match for "${originalGameName}" during scraping`, 'success');
                
                // Clear the current scraping request
                this.currentScrapingRequest = null;
            } else {
                throw new Error(result.error || 'Unknown error');
            }
            
        } catch (error) {
            console.error('Error applying partial match from scraping:', error);
            this.showAlert('Error applying partial match: ' + error.message, 'danger');
        }
    }
    
    async applyRegularMatch(selectedMatch, originalGameName, closeModal = true, modalType = 'global') {
        try {
            // Find the game in our data
            const gameIndex = this.games.findIndex(game => game.name === originalGameName);
            if (gameIndex === -1) {
                this.showAlert('Original game not found', 'danger');
                return;
            }
            
            // Update game data with selected match
            const originalGame = this.games[gameIndex];
            const updatedGame = { ...originalGame };
            
            // Apply fields from the match
            if (selectedMatch.name) updatedGame.name = selectedMatch.name;
            if (selectedMatch.overview) updatedGame.desc = selectedMatch.overview;
            if (selectedMatch.developer) updatedGame.developer = selectedMatch.developer;
            if (selectedMatch.publisher) updatedGame.publisher = selectedMatch.publisher;
            if (selectedMatch.genre) updatedGame.genre = selectedMatch.genre;
            if (selectedMatch.rating) updatedGame.rating = selectedMatch.rating;
            if (selectedMatch.players) updatedGame.players = selectedMatch.players;
            if (selectedMatch.database_id) updatedGame.launchboxid = selectedMatch.database_id;
            
            // Update the games array
            this.games[gameIndex] = updatedGame;
            
            // Mark game as modified
            this.markGameAsModified(updatedGame);
            
            // Refresh grid
            this.refreshGridData();
            
            // Update edit modal fields if it's open
            this.updateEditModalFields(updatedGame);
            
            // Auto-save changes to server
            try {
                await this.saveGameChanges();
                console.log('Auto-saved changes after applying match');
            } catch (error) {
                console.error('Error auto-saving changes:', error);
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
            console.error('Error applying regular match:', error);
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
            
            console.log('Edit modal fields updated with match data');
        }
    }

    async loadAvailableSystems() {
        console.log('loadAvailableSystems called');
        try {
            console.log('Fetching from /api/rom-systems...');
            const response = await fetch('/api/rom-systems');
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
        const systemSelect = document.getElementById('systemSelect');
        console.log('systemSelect element:', systemSelect);
        
        if (!systemSelect) {
            console.error('systemSelect element not found!');
            return;
        }
        
        // Clear existing options except the first placeholder
        while (systemSelect.children.length > 1) {
            systemSelect.removeChild(systemSelect.lastChild);
        }
        
        // Add system options
        systems.forEach(system => {
            const option = document.createElement('option');
            option.value = system.name;
            option.textContent = `${system.name} (${system.rom_count} games)`;
            systemSelect.appendChild(option);
            console.log('Added option:', system.name);
        });
        
        console.log(`Loaded ${systems.length} systems into dropdown`);
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
                    
                    console.log('Focused on first row');
                }
            } catch (error) {
                console.warn('Could not focus on first row:', error);
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
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('youtubeSearchModal'));
        modal.show();
        
        // Initialize search functionality
        this.initializeYouTubeSearch();
        
        // Automatically trigger search when modal is shown
        const modalElement = document.getElementById('youtubeSearchModal');
        modalElement.addEventListener('shown.bs.modal', () => {
            console.log('YouTube search modal shown - triggering automatic search');
            this.performYouTubeSearch();
        }, { once: true }); // Use once: true to only trigger once

    }

    initializeYouTubeSearch() {
        const searchBtn = document.getElementById('youtubeSearchBtn');
        const searchInput = document.getElementById('youtubeSearchInput');
        
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                this.performYouTubeSearch();
            });
        }
        
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performYouTubeSearch();
                }
            });
        }
    }

    async performYouTubeSearch() {
        console.log('performYouTubeSearch: Starting search');
        const query = document.getElementById('youtubeSearchInput').value.trim();
        console.log('performYouTubeSearch: Search query:', query);
        if (!query) {
            console.log('performYouTubeSearch: No query, returning');
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
            console.error('YouTube search error:', error);
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
            console.error('Invalid YouTube URL:', videoUrl);
            this.showPlayerError('Invalid YouTube URL');
            return;
        }
        
        console.log('Initializing YouTube player with video ID:', videoId);
        
        // Wait for YouTube IFrame API to be ready
        if (typeof YT === 'undefined' || !YT.Player) {
            console.log('YouTube IFrame API not ready, waiting...');
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
                console.log('YouTube API ready after', attempts * 100, 'ms');
                callback();
            } else if (attempts < maxAttempts) {
                setTimeout(checkAPI, 100);
            } else {
                console.error('YouTube API failed to load after 5 seconds');
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
            
            console.log('Creating YouTube player for video:', videoId);
            
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
                        console.log('YouTube player ready');
                        // Auto-play the video
                        event.target.playVideo();
                    },
                    'onStateChange': (event) => {
                        console.log('Player state changed:', event.data);
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
                        console.error('YouTube player error:', event.data);
                        this.showPlayerError('Video playback error: ' + event.data);
                    }
                }
            });
            
            console.log('YouTube player created successfully');
            
        } catch (error) {
            console.error('Error creating YouTube player:', error);
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
        console.log('Extracting video ID from URL:', url);
        
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
                console.log('Extracted video ID:', videoId);
                return videoId;
            }
        }
        
        console.error('Could not extract video ID from URL:', url);
        return null;
    }

    initializePlayerControls() {
        const getTimeBtn = document.getElementById('getCurrentTimeBtn');
        if (getTimeBtn) {
            getTimeBtn.addEventListener('click', () => {
                this.getCurrentPlayerTime();
            });
        }
        const downloadBtn = document.getElementById('downloadVideoBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                console.log('Download button clicked - triggering downloadYouTubeVideo');
                this.downloadYouTubeVideo();
            });
        } else {
            console.error('Download button not found!');
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
                console.log('YouTube player destroyed');
            } catch (error) {
                console.warn('Error destroying YouTube player:', error);
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
        // Show the YouTube search modal again
        const searchModal = new bootstrap.Modal(document.getElementById('youtubeSearchModal'));
        searchModal.show();
    }

    getCurrentPlayerTime() {
        if (this.youtubePlayer && this.youtubePlayer.getCurrentTime) {
            const currentTime = Math.floor(this.youtubePlayer.getCurrentTime());
            document.getElementById('startTimeInput').value = currentTime;
        }
    }

    async autoSearchAndDownload() {
        console.log('autoSearchAndDownload: Starting auto-search process');
        
        // Get the current game from the edit modal
        const gameName = document.getElementById('editName').value;
        console.log('autoSearchAndDownload: Game name:', gameName);
        
        if (!gameName) {
            this.showAlert('No game selected', 'error');
            return;
        }
        
        // Create a mock game object for the search
        const game = {
            name: gameName,
            id: this.currentGameId
        };
        console.log('autoSearchAndDownload: Created game object:', game);
        
        // Close the current modal and open YouTube search
        const editModal = document.getElementById('editGameModal');
        if (editModal) {
            const modal = bootstrap.Modal.getInstance(editModal);
            if (modal) {
                console.log('autoSearchAndDownload: Closing edit modal');
                modal.hide();
            }
        }
        
        // Wait a bit for modal to close, then open YouTube search
        setTimeout(() => {
            console.log('autoSearchAndDownload: Opening YouTube search modal');
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
                console.log('YouTube player stopped for download');
            } catch (e) {
                console.error('Error stopping YouTube player:', e);
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
            console.error('Error pre-closing modals:', e);
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
            console.log('Updating YouTube URL field with:', this.currentYouTubeVideo.url);
            
            // Update the game object
            currentGame.youtubeurl = this.currentYouTubeVideo.url;
            
            // Update the edit modal field if it's open
            const editModal = document.getElementById('editGameModal');
            if (editModal && editModal.classList.contains('show')) {
                const youtubeurlField = document.getElementById('editYoutubeurl');
                if (youtubeurlField) {
                    youtubeurlField.value = this.currentYouTubeVideo.url;
                    console.log('Updated YouTube URL field in edit modal');
                }
            }
            
            // Mark the game as modified so changes can be saved
            this.markGameAsModified(currentGame);
        }
        
        // Debug logging
        console.log('Download parameters:', {
            video_url: this.currentYouTubeVideo.url,
            start_time: startTime,
            output_filename: outputFilename,
            system_name: this.currentSystem,
            rom_file: currentGame.path
        });
        
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
            console.error('Download error:', error);
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
            const resp = await fetch('/api/tasks');
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
            console.error('Error checking for completed YouTube tasks:', e);
        }
    }
}

// Initialize the game manager when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.gameManager = new GameCollectionManager();
});
