with open("static/js/app.js", "r") as f:
    js = f.read()

merge_link = """                <a class="dropdown-item" href="#" onclick="gameManager.fillSortnameForSelected()">
                    <i class="bi bi-sort-alpha-down"></i> Fill SortName
                </a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item" href="#" onclick="gameManager.showMergeRomsModal()">
                    <i class="bi bi-arrows-collapse"></i> Merge Selected ROMs
                </a>"""

if 'gameManager.showMergeRomsModal()' not in js:
    js = js.replace('                <a class="dropdown-item" href="#" onclick="gameManager.fillSortnameForSelected()">\n                    <i class="bi bi-sort-alpha-down"></i> Fill SortName\n                </a>', merge_link)

merge_func = """    showMergeRomsModal() {
        const selectedGames = this.gridApi.getSelectedRows();
        if (selectedGames.length < 2) {
            this.showAlert('Please select at least two games to merge.', 'warning');
            return;
        }

        const modalEl = document.getElementById('mergeRomsModal');
        if (!modalEl) {
            console.error('mergeRomsModal not found in DOM');
            return;
        }

        const targetSelect = document.getElementById('targetRomSelect');
        targetSelect.innerHTML = '';
        
        selectedGames.forEach(g => {
            const option = document.createElement('option');
            option.value = g.path;
            option.textContent = `${g.name} (${g.path})`;
            targetSelect.appendChild(option);
        });

        const bestInitialTarget = [...selectedGames].find(g => !g.image);
        if (bestInitialTarget) {
            targetSelect.value = bestInitialTarget.path;
        }

        const confirmBtn = document.getElementById('confirmMergeRomsBtn');
        
        // Remove old listener to avoid firing multiple times
        const newBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
        
        newBtn.addEventListener('click', () => {
            const targetPath = targetSelect.value;
            const sourcePaths = selectedGames.map(g => g.path).filter(p => p !== targetPath);
            
            const bsModal = bootstrap.Modal.getInstance(modalEl);
            if (bsModal) bsModal.hide();
            
            this.mergeRoms(targetPath, sourcePaths);
        });

        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();
    }

    async mergeRoms(targetPath, sourcePaths) {
        if (!this.currentSystem) {
             this.showAlert('Please select a system first.', 'warning');
             return;
        }
        
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/games/merge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    target_rom_path: targetPath,
                    source_rom_paths: sourcePaths
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Merged successfully! ${data.deleted_count} ROM(s) were deleted and merged.`, 'success');
                // The backend triggers an SSE event `gamelist_updated`, which will naturally reload the grid
            } else {
                this.showAlert(data.error || 'Failed to merge ROMs', 'danger');
            }
        } catch (error) {
            console.error('Error merging ROMs:', error);
            this.showAlert('An error occurred while merging ROMs', 'danger');
        }
    }
"""

if 'showMergeRomsModal()' not in js:
    js = js.replace('    async deleteSelectedGames() {', merge_func + '    async deleteSelectedGames() {')
    with open("static/js/app.js", "w") as f:
        f.write(js)
    print("Injected showMergeRomsModal and mergeRoms to static/js/app.js")
else:
    print("merge logic is already in app.js!")

