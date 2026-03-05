import re

with open('templates/index.html', 'r') as f:
    html_content = f.read()

merge_modal_html = """
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
                            <!-- Options will be populated by JS -->
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

# Insert modal before editGameModal
if 'id="mergeRomsModal"' not in html_content:
    html_content = html_content.replace('    <div class="modal fade" id="editGameModal" tabindex="-1">', merge_modal_html + '    <div class="modal fade" id="editGameModal" tabindex="-1">')
    with open('templates/index.html', 'w') as f:
        f.write(html_content)
    print("Inserted mergeRomsModal in index.html")
else:
    print("mergeRomsModal already exists in index.html")

