// Test script to verify status-and-queue API optimization
// This can be run in the browser console to test the size reduction

console.log('Testing status-and-queue API optimization...');

// Test the optimized endpoint
fetch('/api/task/status-and-queue')
    .then(response => response.json())
    .then(data => {
        console.log('✅ Optimized API Response:', data);
        
        // Check if data and progress fields are excluded from tasks
        const tasks = data.all_tasks || {};
        const taskIds = Object.keys(tasks);
        
        if (taskIds.length > 0) {
            const firstTask = tasks[taskIds[0]];
            console.log('📋 First task structure:', firstTask);
            
            // Check if heavy fields are excluded
            const hasData = firstTask.hasOwnProperty('data');
            const hasProgress = firstTask.hasOwnProperty('progress');
            
            console.log(`🔍 Heavy fields check:`);
            console.log(`  - Has 'data' field: ${hasData} (should be minimal)`);
            console.log(`  - Has 'progress' field: ${hasProgress} (should be false)`);
            
            if (hasData) {
                console.log(`  - Data content:`, firstTask.data);
            }
            
            // Test fetching full task details
            if (firstTask.id) {
                console.log('🔍 Testing full task details fetch...');
                fetch(`/api/tasks/${firstTask.id}`)
                    .then(response => response.json())
                    .then(fullTask => {
                        console.log('📋 Full task details:', fullTask);
                        console.log(`  - Has 'data' field: ${fullTask.hasOwnProperty('data')}`);
                        console.log(`  - Has 'progress' field: ${fullTask.hasOwnProperty('progress')}`);
                        console.log(`  - Data content:`, fullTask.data);
                    })
                    .catch(error => {
                        console.error('❌ Error fetching full task details:', error);
                    });
            }
        } else {
            console.log('ℹ️ No tasks found to test');
        }
    })
    .catch(error => {
        console.error('❌ Error testing optimized API:', error);
    });

// Test task log modal opening
console.log('🔍 To test task log modal optimization:');
console.log('1. Open a task log modal by clicking on a task in the grid');
console.log('2. Check the network tab to see the /api/tasks/{id} call');
console.log('3. Verify that full task details (including data and progress) are fetched');
