// Common JavaScript functions for Jokelingo

// Initialize global authentication status (will be set by page-specific scripts)
// Default to false to handle cases where it's accessed before initialization
if (typeof window.isAuthenticated === 'undefined') {
    window.isAuthenticated = false;
}

// Language code to display name mapping (fallback English names)
const LANGUAGE_NAMES = {
    'es': 'Spanish',
    'fr': 'French',
    'ko': 'Korean',
    'en': 'English',
    'zh-hant': 'Traditional Chinese',
};

// Make it globally accessible
window.LANGUAGE_NAMES = LANGUAGE_NAMES;

// Translation helper function
function t(key) {
    // Return translated string if available, otherwise return the key
    return (window.i18n && window.i18n[key]) || key;
}

// Get translated language name for a language code
function getLanguageName(languageCode) {
    const englishName = LANGUAGE_NAMES[languageCode];
    if (!englishName) {
        return languageCode; // Fallback to code if not found
    }
    // Return translated name if available, otherwise return English name
    return t(englishName) || englishName;
}

// Make it globally accessible
window.getLanguageName = getLanguageName;

// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Debounce timers for each post
const debounceTimers = {};
const pendingRequests = {};

// Analytics tracking function
function trackAnalyticsEvent(eventType, metadata = null) {
    const payload = {
        event_type: eventType
    };
    if (metadata) {
        payload.metadata = metadata;
    }
    
    const payloadStr = JSON.stringify(payload);
    
    // Build headers - include CSRF token if available (needed for authenticated users)
    const headers = {
        'Content-Type': 'application/json',
    };
    if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
    }
    
    // Use fetch with keepalive (sendBeacon doesn't support custom headers like CSRF token)
    fetch('/api/v1/analytics/events', {
        method: 'POST',
        headers: headers,
        body: payloadStr,
        keepalive: true
    }).catch(err => {
        // Silently fail - analytics are best-effort
        console.debug('Analytics event failed:', err);
    });
}

function showLoading(append = false) {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const postsContainer = document.getElementById('postsContainer');
    const pagination = document.getElementById('pagination');
    
    if (loading) loading.style.display = 'block';
    if (error) error.style.display = 'none';
    if (!append && postsContainer) {
        postsContainer.innerHTML = '';
    }
    if (pagination) pagination.style.display = 'none';
}

function hideLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'none';
}

function showError(message) {
    const error = document.getElementById('error');
    const loading = document.getElementById('loading');
    if (error) {
        error.textContent = message;
        error.style.display = 'block';
    }
    if (loading) loading.style.display = 'none';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString([], {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// Render post function - can be customized per page
function renderPost(post, options = {}) {
    // Get my_engagement_type, default to "none" if not present (only set for authenticated users)
    const myEngagementType = post.my_engagement_type || "none";
    
    // Determine active classes
    const helpfulActive = myEngagementType === "helpful" ? " active" : "";
    const confusingActive = myEngagementType === "confusing" ? " active" : "";
    
    // Build author line - can be customized
    let authorLine = `${t('By')} <strong>${post.author.display_name}</strong> • ${formatDate(post.created_at)}`;
    if (options.showLanguageInfo && post.languages) {
        authorLine = `${getLanguageName(post.languages.source_language_code)} → ${getLanguageName(post.languages.target_language_code)} • ${authorLine}`;
    }
    
    return `
        <div class="post-card" data-post-id="${post.id}">
            <div class="post-embed" id="embed-${post.id}">
                <div class="embed-loading">${t('Loading embedded post...')}</div>
            </div>
            <div class="post-contribution">
                ${post.contribution?.translation?.text ? `
                    <h4>${t('Translation')}</h4>
                    <div class="translation">${post.contribution.translation.text}</div>
                ` : ''}
                ${post.contribution?.explanation?.text ? `
                    <h4>${t('Why is it funny?')}</h4>
                    <details class="explanation-toggle">
                        <summary>${t('click me')}</summary>
                        <div class="explanation">${post.contribution.explanation.text}</div>
                    </details>
                ` : ''}
                <div class="post-engagement">
                    <div class="engagement-item helpful${helpfulActive} clickable" data-engagement-type="helpful" data-post-id="${post.id}">
                        <span>👍</span>
                        <span class="engagement-count">${post.engagement.helpful}</span> <span class="engagement-label">${t('helpful')}</span>
                    </div>
                    <div class="engagement-item confusing${confusingActive} clickable" data-engagement-type="confusing" data-post-id="${post.id}">
                        <span>😕</span>
                        <span class="engagement-count">${post.engagement.confusing}</span> <span class="engagement-label">${t('confusing')}</span>
                    </div>
                </div>
            </div>
            <div class="post-author">
                ${authorLine}
            </div>
        </div>
    `;
}

function embedPost(post) {
    const embedContainer = document.getElementById(`embed-${post.id}`);
    if (!embedContainer) return;
    
    const provider = post.source.provider.toLowerCase();
    const url = post.source.canonical_url;
    
    const loadingDiv = embedContainer.querySelector('.embed-loading');

    function waitForEmbedReady(wrapper, isReady) {
        let settled = false;
        let observer = null;

        wrapper.style.visibility = 'hidden';
        wrapper.style.pointerEvents = 'none';

        function revealEmbed() {
            if (settled || !isReady()) {
                return false;
            }

            settled = true;
            if (observer) observer.disconnect();

            wrapper.style.visibility = '';
            wrapper.style.pointerEvents = '';
            if (loadingDiv) {
                loadingDiv.remove();
            }
            return true;
        }

        function watchIframeLoads(root) {
            if (!root || root.nodeType !== Node.ELEMENT_NODE) return;

            if (root.tagName === 'IFRAME') {
                root.addEventListener('load', revealEmbed, { once: true });
            }

            root.querySelectorAll('iframe').forEach((iframe) => {
                iframe.addEventListener('load', revealEmbed, { once: true });
            });
        }

        observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    watchIframeLoads(node);
                });
            });
            revealEmbed();
        });

        observer.observe(wrapper, {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true,
        });

        watchIframeLoads(wrapper);
        requestAnimationFrame(revealEmbed);
    }
    
    if (provider === 'reddit') {
        // Reddit embed using official embed script
        const wrapper = document.createElement('div');
        wrapper.className = 'embed-wrapper';
        wrapper.style.textAlign = 'center';
        wrapper.style.width = '100%';
        
        // Create a blockquote element that Reddit's embed script will process
        const blockquote = document.createElement('blockquote');
        blockquote.className = 'reddit-embed';
        blockquote.setAttribute('data-embed-theme', 'light');
        blockquote.setAttribute('data-embed-height', '600');
        
        const link = document.createElement('a');
        link.href = url;
        link.textContent = url;
        blockquote.appendChild(link);
        
        wrapper.appendChild(blockquote);
        embedContainer.appendChild(wrapper);

        waitForEmbedReady(wrapper, () => Boolean(wrapper.querySelector('iframe')));
        
        // Load Reddit embed script if not already loaded
        const existingScript = document.querySelector('script[src*="embed.reddit.com/widgets.js"]');
        if (!existingScript) {
            const script = document.createElement('script');
            script.src = 'https://embed.reddit.com/widgets.js';
            script.async = true;
            script.charset = 'UTF-8';
            document.body.appendChild(script);
        } else {
            // Script already loaded - Reddit's embed script needs to process new embeds
            // Reddit's embed script processes embeds on initial page load,
            // but doesn't automatically process new embeds added dynamically.
            // Solution: Add a new script instance to trigger processing of new embeds.
            // Reddit's script will process all .reddit-embed elements when it loads,
            // including the new one we just added.
            
            // Create a new script instance - Reddit's script can handle multiple instances
            // and will process all unprocessed .reddit-embed elements
            const newScript = document.createElement('script');
            newScript.src = 'https://embed.reddit.com/widgets.js';
            newScript.async = true;
            newScript.charset = 'UTF-8';
            newScript.setAttribute('data-reddit-embed-helper', 'true');
            // Append the new script - it will process the new embed
            document.body.appendChild(newScript);
        }
    } else if (provider === 'instagram') {
        // Instagram embed using blockquote (works with their embed.js)
        const wrapper = document.createElement('div');
        wrapper.className = 'embed-wrapper';
        wrapper.style.textAlign = 'center';
        wrapper.style.width = '100%';
        const blockquote = document.createElement('blockquote');
        blockquote.className = 'instagram-media';
        blockquote.setAttribute('data-instgrm-captioned', '');
        blockquote.setAttribute('data-instgrm-permalink', url);
        blockquote.setAttribute('data-instgrm-version', '14');
        blockquote.style.background = '#FFF';
        blockquote.style.border = '0';
        blockquote.style.borderRadius = '3px';
        blockquote.style.margin = '0 auto';
        blockquote.style.padding = '0';
        blockquote.style.display = 'block';
        
        wrapper.appendChild(blockquote);
        embedContainer.appendChild(wrapper);

        waitForEmbedReady(wrapper, () => {
            const instagramIframe = wrapper.querySelector('iframe') || blockquote.querySelector('iframe');
            const hasContent = blockquote.children.length > 0 && blockquote.innerHTML.length > 200;
            return Boolean(instagramIframe || hasContent);
        });
        
        // Load Instagram embed script if not already loaded
        if (!window.instgrm) {
            const script = document.createElement('script');
            script.src = 'https://www.instagram.com/embed.js';
            script.async = true;
            document.body.appendChild(script);
        } else {
            window.instgrm.Embeds.process();
        }
    } else if (provider === 'twitter') {
        // Twitter embed using blockquote (works with their widgets.js)
        const wrapper = document.createElement('div');
        wrapper.className = 'embed-wrapper';
        wrapper.style.textAlign = 'center';
        wrapper.style.width = '100%';
        const blockquote = document.createElement('blockquote');
        blockquote.className = 'twitter-tweet';
        blockquote.setAttribute('data-theme', 'light');
        const link = document.createElement('a');
        link.href = url;
        blockquote.appendChild(link);
        
        wrapper.appendChild(blockquote);
        embedContainer.appendChild(wrapper);

        waitForEmbedReady(wrapper, () => {
            const twitterIframe = wrapper.querySelector('iframe') || blockquote.querySelector('iframe');
            const twitterRendered = wrapper.querySelector('.twitter-tweet-rendered') || blockquote.querySelector('.twitter-tweet-rendered');
            const hasContent = blockquote.innerHTML.length > link.outerHTML.length + 50;
            return Boolean(twitterIframe || twitterRendered || hasContent);
        });
        
        // Load Twitter embed script if not already loaded
        if (!window.twttr) {
            const script = document.createElement('script');
            script.src = 'https://platform.twitter.com/widgets.js';
            script.async = true;
            script.charset = 'utf-8';
            script.id = 'twitter-wjs';
            script.onload = () => {
                if (window.twttr && window.twttr.widgets) {
                    window.twttr.widgets.load();
                }
            };
            document.body.appendChild(script);
        } else {
            window.twttr.widgets.load();
        }
    } else if (provider === 'imgur') {
        // Imgur embed using blockquote (works with their embed.js)
        const wrapper = document.createElement('div');
        wrapper.className = 'embed-wrapper';
        wrapper.style.textAlign = 'center';
        wrapper.style.width = '100%';
        
        // Extract image ID from URL - get the last part after last hyphen or slash
        const pathname = new URL(url).pathname;
        const imageId = pathname.split('/').pop().split('-').pop();
        
        const blockquote = document.createElement('blockquote');
        blockquote.className = 'imgur-embed-pub';
        blockquote.setAttribute('lang', 'en');
        blockquote.setAttribute('data-id', imageId);
        const link = document.createElement('a');
        link.href = url;
        link.textContent = 'View on Imgur';
        blockquote.appendChild(link);
        
        wrapper.appendChild(blockquote);
        embedContainer.appendChild(wrapper);

        waitForEmbedReady(wrapper, () => Boolean(wrapper.querySelector('iframe')));
        
        // Load Imgur embed script if not already loaded
        if (!document.querySelector('script[src*="s.imgur.com/min/embed.js"]')) {
            const script = document.createElement('script');
            script.src = 'https://s.imgur.com/min/embed.js';
            script.async = true;
            document.body.appendChild(script);
        }
    } else if (provider === 'facebook') {
        // Facebook embed using fb-post div (works with their SDK)
        const wrapper = document.createElement('div');
        wrapper.className = 'embed-wrapper';
        wrapper.style.textAlign = 'center';
        wrapper.style.width = '100%';
        
        const fbPost = document.createElement('div');
        fbPost.className = 'fb-post';
        fbPost.setAttribute('data-href', url);
        fbPost.setAttribute('data-width', '500');
        fbPost.setAttribute('data-show-text', 'true');
        
        wrapper.appendChild(fbPost);
        embedContainer.appendChild(wrapper);

        waitForEmbedReady(wrapper, () => {
            const fbIframe = wrapper.querySelector('iframe');
            const hasContent = fbPost.children.length > 0 && fbPost.innerHTML.length > 200;
            return Boolean(fbIframe || hasContent);
        });
        
        // Load Facebook SDK if not already loaded
        if (!window.FB) {
            // Load Facebook SDK script
            const script = document.createElement('script');
            script.src = 'https://connect.facebook.net/en_US/sdk.js#xfbml=1&version=v24.0';
            script.async = true;
            script.defer = true;
            script.crossOrigin = 'anonymous';
            script.onload = () => {
                if (window.FB) {
                    window.FB.XFBML.parse(wrapper);
                }
            };
            document.body.appendChild(script);
        } else {
            // SDK already loaded - parse new embed
            window.FB.XFBML.parse(wrapper);
        }
    } else {
        // Fallback: show link
        if (loadingDiv) {
            loadingDiv.className = 'embed-error';
            loadingDiv.innerHTML = `Embedding not available for ${provider}. <a href="${url}" target="_blank" rel="noopener noreferrer">View original post</a>`;
        }
    }
}

// Get current engagement state for a post from DOM
function getPostEngagementState(postId) {
    const postCard = document.querySelector(`[data-post-id="${postId}"]`);
    if (!postCard) return "none";
    
    const helpfulItem = postCard.querySelector('.engagement-item.helpful');
    const confusingItem = postCard.querySelector('.engagement-item.confusing');
    
    if (helpfulItem && helpfulItem.classList.contains('active')) {
        return "helpful";
    } else if (confusingItem && confusingItem.classList.contains('active')) {
        return "confusing";
    }
    return "none";
}

// Update UI optimistically
function updateEngagementUI(postId, newType) {
    const postCard = document.querySelector(`[data-post-id="${postId}"]`);
    if (!postCard) return;
    
    const helpfulItem = postCard.querySelector('.engagement-item.helpful');
    const confusingItem = postCard.querySelector('.engagement-item.confusing');
    const helpfulCount = postCard.querySelector('.engagement-item.helpful .engagement-count');
    const confusingCount = postCard.querySelector('.engagement-item.confusing .engagement-count');
    
    const currentType = getPostEngagementState(postId);
    
    // Remove active states
    helpfulItem.classList.remove('active');
    confusingItem.classList.remove('active');
    
    // Calculate count changes
    let helpfulDelta = 0;
    let confusingDelta = 0;
    
    // Remove old engagement
    if (currentType === "helpful") {
        helpfulDelta = -1;
    } else if (currentType === "confusing") {
        confusingDelta = -1;
    }
    
    // Add new engagement
    if (newType === "helpful") {
        helpfulItem.classList.add('active');
        helpfulDelta += 1;
    } else if (newType === "confusing") {
        confusingItem.classList.add('active');
        confusingDelta += 1;
    }
    
    // Update counts optimistically
    if (helpfulCount) {
        const currentCount = parseInt(helpfulCount.textContent) || 0;
        const newCount = Math.max(0, currentCount + helpfulDelta);
        helpfulCount.textContent = newCount;
    }
    
    if (confusingCount) {
        const currentCount = parseInt(confusingCount.textContent) || 0;
        const newCount = Math.max(0, currentCount + confusingDelta);
        confusingCount.textContent = newCount;
    }
}

// Send engagement to backend
// onError callback can be provided to customize error handling
async function submitEngagement(postId, engagementType, onError = null) {
    // Cancel any pending request for this post
    if (pendingRequests[postId]) {
        pendingRequests[postId].abort();
    }
    
    // Create new abort controller
    const controller = new AbortController();
    pendingRequests[postId] = controller;
    
    try {
        const response = await fetch(`/api/v1/posts/${postId}/engagement`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({
                engagement_type: engagementType
            }),
            signal: controller.signal
        });
        
        if (response.status === 401) {
            // User is not authenticated
            if (onError && onError.on401) {
                onError.on401();
            } else {
                window.location.reload();
            }
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Success - no need to do anything, UI is already updated optimistically
    } catch (err) {
        if (err.name === 'AbortError') {
            // Request was cancelled, ignore
            return;
        }
        console.error('Error submitting engagement:', err);
        if (onError && onError.onError) {
            onError.onError(err);
        }
    } finally {
        delete pendingRequests[postId];
    }
}

// Handle engagement click with debouncing
function handleEngagementClick(event) {
    const item = event.currentTarget;
    
    // Check if user is authenticated (check global variable, default to false if not set)
    if (!window.isAuthenticated) {
        // Track analytics event for anonymous user engagement click
        const postId = item.dataset.postId;
        const engagementType = item.dataset.engagementType;
        if (postId && engagementType) {
            trackAnalyticsEvent('engagement_click_anon', {
                post_id: postId,
                engagement_type: engagementType
            });
        }
        
        // Call custom handler or default behavior
        if (engagementUnauthenticatedHandler) {
            engagementUnauthenticatedHandler();
        } else {
            // Default: show login modal if available, otherwise reload
            const loginModal = document.getElementById('loginModal');
            if (loginModal) {
                loginModal.classList.add('show');
            } else {
                window.location.reload();
            }
        }
        return;
    }
    
    const postId = item.dataset.postId;
    const engagementType = item.dataset.engagementType;
    
    // Get current state
    const currentType = getPostEngagementState(postId);
    
    // Determine new state based on toggle logic
    let newType;
    if (engagementType === "helpful") {
        if (currentType === "helpful") {
            newType = "none"; // Toggle off
        } else {
            newType = "helpful"; // Toggle on or switch from confusing
        }
    } else if (engagementType === "confusing") {
        if (currentType === "confusing") {
            newType = "none"; // Toggle off
        } else {
            newType = "confusing"; // Toggle on or switch from helpful
        }
    }
    
    // Update UI immediately (optimistic update)
    updateEngagementUI(postId, newType);
    
    // Clear existing debounce timer for this post
    if (debounceTimers[postId]) {
        clearTimeout(debounceTimers[postId]);
    }
    
    // Set new debounce timer (2 seconds)
    debounceTimers[postId] = setTimeout(() => {
        submitEngagement(postId, newType, engagementErrorHandler);
        delete debounceTimers[postId];
    }, 2000);
}

// Store callbacks for engagement handling
let engagementErrorHandler = null;
let engagementUnauthenticatedHandler = null;

// Set error handler for engagement submission
function setEngagementErrorHandler(handler) {
    engagementErrorHandler = handler;
}

// Set unauthenticated handler for engagement clicks
function setEngagementUnauthenticatedHandler(handler) {
    engagementUnauthenticatedHandler = handler;
}

// Attach click handlers to engagement items
function attachEngagementHandlers() {
    const engagementItems = document.querySelectorAll('.engagement-item.clickable');
    engagementItems.forEach(item => {
        // Remove existing listeners by cloning
        const newItem = item.cloneNode(true);
        item.parentNode.replaceChild(newItem, item);
        // Add click listener
        newItem.addEventListener('click', handleEngagementClick);
    });
}

// User menu dropdown functionality
function initUserMenu() {
    const trigger = document.getElementById('userMenuTrigger');
    const dropdown = document.getElementById('userMenuDropdown');
    
    if (!trigger || !dropdown) return;
    
    // Toggle dropdown on click
    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
}
