// Page-specific JavaScript for index.html (feed page)

// Initialize the page
function initIndexPage(config) {
    const {
        isAuthenticated,
        sourceLanguageCode,
        targetLanguageCode
    } = config;
    
    // Set as global variable for common.js to access
    window.isAuthenticated = isAuthenticated;
    
    // Set header badge immediately (runs before DOMContentLoaded)
    function setHeaderBadge() {
        const sourceName = window.LANGUAGE_NAMES[sourceLanguageCode] || sourceLanguageCode;
        const targetName = window.LANGUAGE_NAMES[targetLanguageCode] || targetLanguageCode;
        const headerBadge = document.getElementById('headerBadge');
        if (headerBadge) {
            headerBadge.textContent = `${sourceName} → ${targetName}`;
        }
    }
    
    // Set header badge immediately if DOM is ready, otherwise wait for it
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setHeaderBadge);
    } else {
        setHeaderBadge();
    }
    
    let currentCursor = null;
    let currentParams = {};
    
    const postsContainer = document.getElementById('postsContainer');
    const pagination = document.getElementById('pagination');
    
    async function loadFeed(params = {}, cursor = null, append = false) {
        showLoading(append);
        
        const queryParams = new URLSearchParams();
        if (params.limit) queryParams.append('limit', params.limit);
        if (params.source_language_code) queryParams.append('source_language_code', params.source_language_code);
        if (params.target_language_code) queryParams.append('target_language_code', params.target_language_code);
        if (cursor) queryParams.append('cursor', cursor);
        
        try {
            const response = await fetch(`/api/v1/feed?${queryParams.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Render posts
            if (data.posts && data.posts.length > 0) {
                if (append) {
                    // Append new posts to existing ones
                    const postsHTML = data.posts.map(post => renderPost(post, {})).join('');
                    postsContainer.insertAdjacentHTML('beforeend', postsHTML);
                    // Embed posts after rendering
                    data.posts.forEach(post => {
                        embedPost(post);
                    });
                } else {
                    // Replace all posts (initial load)
                    postsContainer.innerHTML = data.posts.map(post => renderPost(post, {})).join('');
                    // Embed posts after rendering
                    data.posts.forEach(post => {
                        embedPost(post);
                    });
                }
                // Attach engagement click handlers
                attachEngagementHandlers();
            } else {
                if (!append) {
                    postsContainer.innerHTML = '<div class="post-card"><p>No posts found.</p></div>';
                }
            }
            
            // Handle pagination
            currentCursor = data.meta.next_cursor || null;
            if (data.meta.has_more && currentCursor) {
                pagination.innerHTML = `
                    <button class="btn" onclick="loadNextPage()">Load More</button>
                `;
                pagination.style.display = 'block';
            } else {
                pagination.style.display = 'none';
            }
            
            hideLoading();
        } catch (err) {
            showError(`Error loading feed: ${err.message}`);
        }
    }
    
    function loadNextPage() {
        // Track analytics event for load more click
        trackAnalyticsEvent('load_more_click', {
            page_cursor: currentCursor || null,
            source_language_code: currentParams.source_language_code || null,
            target_language_code: currentParams.target_language_code || null
        });
        
        loadFeed(currentParams, currentCursor, true); // true = append mode
    }
    
    // Set up error handler for engagement submission (reload feed on error)
    setEngagementErrorHandler({
        onError: (err) => {
            loadFeed(currentParams, currentCursor, false);
        }
    });
    
    // Set up unauthenticated handler (show login modal)
    setEngagementUnauthenticatedHandler(() => {
        const loginModal = document.getElementById('loginModal');
        if (loginModal) {
            loginModal.classList.add('show');
        }
    });
    
    // Make functions available globally for onclick handlers
    window.loadFeed = loadFeed;
    window.loadNextPage = loadNextPage;
    
    // Login modal functionality
    function initLoginModal() {
        const loginBtn = document.getElementById('loginBtn');
        const loginModal = document.getElementById('loginModal');
        const closeModal = document.getElementById('closeModal');
        
        if (!loginBtn || !loginModal) return;
        
        // Helper function to close modal and track analytics
        function closeLoginModal() {
            if (loginModal.classList.contains('show')) {
                loginModal.classList.remove('show');
                // Track analytics event for closing login modal (only for anonymous users)
                if (!window.isAuthenticated) {
                    trackAnalyticsEvent('login_modal_close');
                }
            }
        }
        
        // Open modal when login button is clicked
        loginBtn.addEventListener('click', () => {
            // Track analytics event for top-right login button click (only for anonymous users)
            if (!window.isAuthenticated) {
                trackAnalyticsEvent('login_click_topright_anon');
            }
            loginModal.classList.add('show');
        });
        
        // Close modal when close button is clicked
        if (closeModal) {
            closeModal.addEventListener('click', closeLoginModal);
        }
        
        // Close modal when clicking outside the modal content
        loginModal.addEventListener('click', (e) => {
            if (e.target === loginModal) {
                closeLoginModal();
            }
        });
        
        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && loginModal.classList.contains('show')) {
                closeLoginModal();
            }
        });
    }
    
    // Language menu dropdown functionality
    function initLanguageMenu() {
        const trigger = document.getElementById('headerBadge');
        const dropdown = document.getElementById('languageMenuDropdown');
        
        if (!trigger || !dropdown) return;
        
        // Toggle dropdown on click
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const wasShown = dropdown.classList.contains('show');
            dropdown.classList.toggle('show');
            
            // Track analytics event when dropdown is expanded (not when closed)
            if (!wasShown && dropdown.classList.contains('show')) {
                trackAnalyticsEvent('language_menu_expand');
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    }
    
    // Load initial feed on page load
    window.addEventListener('DOMContentLoaded', () => {
        // Track page landing event
        trackAnalyticsEvent('page_landing', {
            path: window.location.pathname
        });
        
        currentParams = {
            limit: '10',
            source_language_code: sourceLanguageCode,
            target_language_code: targetLanguageCode,
        };
        window.currentParams = currentParams;
        
        loadFeed(currentParams);
        initUserMenu();
        initLoginModal();
        initLanguageMenu();
    });
}
