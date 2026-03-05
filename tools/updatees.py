import re

html_path = 'templates/index.html'

with open(html_path, 'r') as f:
    text = f.read()

merge_modal = """
    <!-- Merge ROMs Modal -->
    <div class="modal fade" id="mergeRomsModal" tabindex="-1" aria-labelledby="mergeRomsModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="mergeRomsModalLabel">Merge ROMs</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Select the target ROM. The metadata and media from the other selected ROMs will be copied to this target ROM, and the other ROM files will be deleted.</p>
                    <div class="mb-3">
                        <label for="targetRomSelect" class="form-label">Target ROM</label>
                        <select class="form-select" id="targetRomSelect">
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="confirmMergeRomsBtn">Merge ROMs</button>
                </div>
            </div>
        </div>
    </div>
"""

if 'id="mergeRomsModal"' not in text:
    text = text.replace('    <div class="modal fade" id="editGameModal"', merge_modal + '\n    <div class="modal fade" id="editGameModal"')
    with open(html_path, 'w') as f:
        f.write(text)
    print("Modal successfully added.")
else:
    print("Modal already exists.")
