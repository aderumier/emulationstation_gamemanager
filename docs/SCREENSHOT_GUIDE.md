# Screenshot Guide for Documentation

This guide lists all screenshots needed for the documentation and provides recommendations for capturing them.

## Screenshot Requirements

### Image Format
- **Format**: PNG or JPG
- **Recommended Size**: 1920x1080 or larger (maintain aspect ratio)
- **Quality**: High quality, clear text
- **File Naming**: Use kebab-case (e.g., `main-interface.png`)

### Preparation
1. Use a clean, organized game collection for screenshots
2. Ensure consistent UI theme (light mode for most, dark mode for dark mode section)
3. Hide personal information if needed
4. Use clear, descriptive game names

## Required Screenshots

### Main Interface (Priority: High)

#### main-interface.png
- Full application window
- Game grid with multiple games visible
- Media preview pane visible
- Clear view of navigation bar

#### navigation-bar.png
- Close-up of navigation bar
- All menus visible
- Dropdown menus can be closed or open (choose clearest)

#### game-grid-view.png
- Game grid in default view
- Multiple columns visible
- Some games selected
- Clear column headers

#### media-preview.png
- Media preview pane
- Multiple media items visible
- Hover tooltip if possible (or separate screenshot)
- Action buttons visible

#### task-management.png
- Task management panel
- At least one active task showing progress
- Task history visible

### Features (Priority: High)

#### edit-game-modal.png
- Game edit modal open
- All three tabs visible or main tab (Game Information)
- Form fields populated
- Save/Cancel buttons visible

#### edit-game-modal-media.png
- Media Files tab in edit modal
- Multiple media items
- Upload/Delete buttons visible

#### edit-game-modal-video.png
- Video Preview tab
- Video player visible
- All video action buttons (Take Screenshot, Upload Video, etc.)

#### manual-scrap.png
- Manual scrap modal
- Search results visible
- Multiple scraper results
- Preview thumbnails

#### multiscraper-download.png
- Multiscraper results
- Grid of media options
- Region/resolution info visible
- Download buttons

#### youtube-integration.png
- YouTube preview modal
- Video player embedded
- Start time selector
- Download button
- Auto-crop checkbox

#### youtube-download.png
- YouTube download in progress
- Or completed download result
- Video linked in game

#### launchbox-media-download.png
- LaunchBox media download modal
- Media options grid
- Preview images
- Download interface

#### remap-media-fields.png
- Remap Media Fields modal
- Source/target dropdowns
- Confirmation button

#### clean-missing-media.png
- Clean Missing Media Fields modal
- Field selection dropdown
- Warning message
- Cleanup button

#### video-screenshot.png
- Screenshot preview modal
- Captured screenshot displayed
- Field selection dropdown
- Validate button

#### image-rotation.png
- Context menu on image
- Rotate options visible
- Or image being rotated

### Configuration (Priority: Medium)

#### configuration.png
- Configuration modal overview
- Or main configuration menu

#### app-configuration.png
- Application Configuration tab
- ROMs directory setting
- Server settings visible

#### scraper-configuration.png
- Scraper Configuration modal
- Media fields tab visible
- Or LaunchBox/IGDB tabs

#### video-configuration.png
- Video Configuration modal
- All settings visible
- YouTube API key field (can be masked)

#### systems-configuration.png
- Systems Configuration modal
- List of systems
- System details visible

#### gui-preferences.png
- GUI Preferences modal
- Dark mode toggle
- Media card color picker
- Other preferences visible

#### 2d-box-generator.png
- 2D Box Generator configuration
- Settings and layout options

### Authentication (Priority: Medium)

#### login-screen.png
- Login page
- Username/password fields
- Login button
- Discord login button if enabled

#### user-management.png
- User Management interface
- List of users
- User roles visible
- Add/Edit buttons

#### discord-login.png
- Discord OAuth flow
- Or Discord login button on login screen

### Advanced Features (Priority: Medium)

#### thumbnail-view.png
- Thumbnail grid view
- Large game cards
- Media thumbnails visible

#### dark-mode-interface.png
- Application in dark mode
- All UI elements visible
- Game grid in dark theme

#### task-queue.png
- Task management with multiple tasks
- Progress bars visible
- Different task statuses

#### search-filter.png
- Search bar active
- Filter dropdowns
- Filtered results visible

#### batch-operations.png
- Multiple games selected
- Batch operation menu
- Or bulk action in progress

### Deployment (Priority: Low)

#### docker-setup.png
- Docker Compose file
- Or docker run command
- Container running status

#### nginx-setup.png
- Nginx configuration file
- Or nginx status page

#### features-overview.png
- Feature comparison table
- Or visual feature list
- Can be a diagram/infographic

## Screenshot Capture Tips

### Browser Tools
- **Chrome DevTools**: Use device toolbar for consistent sizing
- **Full Page Screenshots**: Use browser extensions for full-page captures
- **Element Screenshots**: Right-click → Inspect → Screenshot node

### Recommended Tools
- **Windows**: Snipping Tool, ShareX, Greenshot
- **Linux**: Flameshot, Spectacle, Shutter
- **macOS**: Screenshot utility, Skitch

### Best Practices
1. **Use consistent browser zoom level** (100% recommended)
2. **Hide browser bookmarks/address bar** if possible
3. **Use clean, professional game names** for demos
4. **Remove any personal/sensitive information**
5. **Ensure good contrast** for text readability
6. **Capture at peak clarity** (after all elements load)

### Editing
- Crop to remove unnecessary UI elements
- Add subtle annotations if helpful (arrows, highlights)
- Maintain original aspect ratio
- Ensure file size is reasonable (< 2MB recommended)

## Screenshot Organization

Place all screenshots in: `docs/images/`

### File Naming Convention
- Use kebab-case: `feature-name.png`
- Be descriptive: `youtube-preview-modal.png` not `youtube.png`
- Group related: `edit-modal-info.png`, `edit-modal-media.png`

## Status Tracking

Mark screenshots as you capture them:

- [ ] main-interface.png
- [ ] navigation-bar.png
- [ ] game-grid-view.png
- [ ] media-preview.png
- [ ] task-management.png
- [ ] edit-game-modal.png
- [ ] edit-game-modal-media.png
- [ ] edit-game-modal-video.png
- [ ] manual-scrap.png
- [ ] multiscraper-download.png
- [ ] youtube-integration.png
- [ ] youtube-download.png
- [ ] launchbox-media-download.png
- [ ] remap-media-fields.png
- [ ] clean-missing-media.png
- [ ] video-screenshot.png
- [ ] image-rotation.png
- [ ] configuration.png
- [ ] app-configuration.png
- [ ] scraper-configuration.png
- [ ] video-configuration.png
- [ ] systems-configuration.png
- [ ] gui-preferences.png
- [ ] 2d-box-generator.png
- [ ] login-screen.png
- [ ] user-management.png
- [ ] discord-login.png
- [ ] thumbnail-view.png
- [ ] dark-mode-interface.png
- [ ] task-queue.png
- [ ] search-filter.png
- [ ] batch-operations.png
- [ ] docker-setup.png
- [ ] nginx-setup.png
- [ ] features-overview.png

## Additional Notes

- Screenshots can be updated as UI evolves
- Consider adding alt text descriptions
- Some screenshots may need to be composite images (multiple states)
- Animated GIFs can be useful for workflows (optional)

