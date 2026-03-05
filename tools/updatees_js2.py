import re

path="static/js/app.js"
with open(path, "r") as f:
    text = f.read()

# First replace the HTML in showContextMenu
old_link = """                <a class="dropdown-item" href="#" onclick="gameManager.fillSortnameForSelected()">
                    <i class="bi bi-sort-alpha-down"></i> Fill SortName
                </a>
                <div class="dropdown-divider"></div>"""

new_link = """                <a class="dropdown-item" href="#" onclick="gameManager.fillSortnameForSelected()">
                    <i class="bi bi-sort-alpha-down"></i> Fill SortName
                </a>
                <a class="dropdown-item" href="#" onclick="gameManager.showMergeRomsModal()">
                    <i class="bi bi-arrows-collapse"></i> Merge Selected ROMs
                </a>
                <div class="dropdown-divider"></div>"""

if 'gameManager.showMergeRomsModal()' not in text:
    text = text.replace(old_link, new_link)

# Next replace deleteSelectedGames to include merge
old_delete_func = """    async deleteSelectedGames() {
        const selectedGames = this.gridApi.getSelectedRows();
        if (selectedGames.length === 0) {
            this.showAlert('No games selected.', 'warning');
            return;
        }

        this.showDeleteConfirmation(selectedGames);
    }"""

merge_func_addition = """
    showMergeRomsModal() {
        const selectedGames = this.gridApi ? this.gridApi.getSelectedRows() : [];
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
            const safeName = g.name ? g.name.replace(/</g, "&lt;").replace(/>/g, "&gt;") : "Unknown";
            option.textContent = `${safeName} (${g.path})`;
            targetSelect.appendChild(option);
        });

        // Try to default to a game without an image
        const bestInitialTarget = [...selectedGames].reverse().find(g => !g.image) || selectedGames[0];
        targetSelect.value = bestInitialTarget.path;

        const confirmBtn = document.getElementById('confirmMergeRomsBtn');
        
        // Remove old listeners
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

        if (!targetPath || sourcePaths.length === 0) return;

        this.showLoading('Merging ROMs...');
        
        try {
            const response = await fetch(`/api/rom-system/${this.currentSystem}/games/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_rom_path: targetPath, source_rom_paths: sourcePaths })
            });

            const data = await response.json();
            this.hideLoading();
            
            if (data.success) {
                this.showAlert(`Merged successfully! ${data.deleted_count} ROM(s) were merged and deleted.`, 'success');
                // The backend triggers an SSE event `gamelist_updated`, reloading the grid
            } else {
                this.showAlert(data.error || 'Failed to merge ROMs', 'danger');
            }
        } catch (error) {
            this.hideLoading();
            console.error('Error merging ROMs:', error);
            this.showAlert('An error occurred while merging ROMs', 'danger');
        }
    }
"""

if 'showMergeRomsModal()' not in text:
    text = text.replace(old_delete_func, old_delete_func + "\n" + merge_func_addition)
    with open(path, "w") as f:
        f.write(text)
    print("JS successfully updated.")
else:
    print("JS changes already applied.")

