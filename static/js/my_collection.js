// Page-specific JavaScript for the My Collection page

// Initialize the page
function initMyCollectionPage(config) {
    const { isAuthenticated } = config;
    
    // Set as global variable for common.js to access
    window.isAuthenticated = isAuthenticated;
    
    let currentCursor = null;
    
    const postsContainer = document.getElementById('postsContainer');
    const pagination = document.getElementById('pagination');
    
    async function loadCollection(cursor = null, append = false) {
        showLoading(append);
        
        const queryParams = new URLSearchParams();
        queryParams.append('limit', '10');
        if (cursor) queryParams.append('cursor', cursor);
        
        try {
            const response = await fetch(`/api/v1/me/collection?${queryParams.toString()}`);
            
            if (response.status === 401) {
                // User is not authenticated, redirect to login
                window.location.href = '/login/?next=/me/collection/';
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Render posts
            if (data.posts && data.posts.length > 0) {
                if (append) {
                    // Append new posts to existing ones
                    const postsHTML = data.posts.map(post => renderPost(post, { showLanguageInfo: true })).join('');
                    postsContainer.insertAdjacentHTML('beforeend', postsHTML);
                    // Embed posts after rendering
                    data.posts.forEach(post => {
                        embedPost(post);
                    });
                } else {
                    // Replace all posts (initial load)
                    postsContainer.innerHTML = data.posts.map(post => renderPost(post, { showLanguageInfo: true })).join('');
                    // Embed posts after rendering
                    data.posts.forEach(post => {
                        embedPost(post);
                    });
                }
                // Attach engagement click handlers
                attachEngagementHandlers();
                attachExplanationHandlers();
                attachPostPermalinkHandlers();
            } else {
                if (!append) {
                    // Show empty state
                    postsContainer.innerHTML = `
                        <div class="post-card" style="text-align: center; padding: 40px;">
                            <p style="font-size: 1.1em; color: #4a5568; margin-bottom: 10px;">
                                ${t('You haven\'t added anything to your collection yet.')}
                            </p>
                            <p style="color: #718096;">
                                ${t('Click Helpful on a post to save it here.')}
                            </p>
                        </div>
                    `;
                }
            }
            
            // Handle pagination
            currentCursor = data.meta.next_cursor || null;
            if (data.meta.has_more && currentCursor) {
                pagination.innerHTML = `
                    <button class="btn" onclick="loadNextPage()">${t('Load More')}</button>
                `;
                pagination.style.display = 'block';
            } else {
                pagination.style.display = 'none';
            }
            
            hideLoading();
        } catch (err) {
            showError(`${t('Error loading collection:')} ${err.message}`);
        }
    }
    
    function loadNextPage() {
        // Track analytics event for load more click
        trackAnalyticsEvent('load_more_click', {
            page_cursor: currentCursor || null,
            page_type: 'my_collection'
        });
        
        loadCollection(currentCursor, true); // true = append mode
    }
    
    // Set up error handler for engagement submission (don't reload on error)
    setEngagementErrorHandler({
        on401: () => {
            window.location.href = '/login/?next=/me/collection/';
        },
        onError: (err) => {
            // On error, don't refresh - just log the error
            // The UI will stay in the optimistic state, and will be corrected on next page load
        }
    });
    
    // Set up unauthenticated handler (redirect to login)
    setEngagementUnauthenticatedHandler(() => {
        window.location.href = '/login/?next=/me/collection/';
    });
    
    // Make functions available globally for onclick handlers
    window.loadNextPage = loadNextPage;
    
    // Load initial collection items on page load
    window.addEventListener('DOMContentLoaded', () => {
        // Track page landing event
        trackAnalyticsEvent('page_landing', {
            path: window.location.pathname
        });
        
        loadCollection();
        initUserMenu();
    });
}
