// Test script to verify task refresh debouncing
// This can be run in the browser console to test the debouncing mechanism

console.log('Testing task refresh debouncing...');

// Simulate rapid calls to refreshTasks
const manager = window.gameCollectionManager;
if (manager) {
    console.log('Found GameCollectionManager instance');
    
    // Test 1: Call refreshTasks multiple times rapidly
    console.log('Test 1: Rapid calls to refreshTasks');
    manager.refreshTasks();
    manager.refreshTasks();
    manager.refreshTasks();
    
    // Wait a bit and test again
    setTimeout(() => {
        console.log('Test 2: More rapid calls after delay');
        manager.refreshTasks();
        manager.refreshTasks();
        manager.refreshTasks();
    }, 2000);
    
    // Test 3: Check the flag state
    setTimeout(() => {
        console.log('Test 3: Checking flag state');
        console.log('isRefreshingTasks:', manager.isRefreshingTasks);
        console.log('taskRefreshTimeout:', manager.taskRefreshTimeout);
    }, 1000);
    
} else {
    console.log('GameCollectionManager not found. Make sure the page is loaded.');
}
