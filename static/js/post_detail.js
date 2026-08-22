function initPostDetailPage(config) {
    const { isAuthenticated, shortCode } = config;
    window.isAuthenticated = isAuthenticated;

    const postsContainer = document.getElementById('postsContainer');

    setEngagementErrorHandler({
        on401: () => {
            window.location.href = `/login/?next=${encodeURIComponent(window.location.pathname)}`;
        },
        onError: () => {
            window.location.reload();
        },
    });
    setEngagementUnauthenticatedHandler(() => {
        window.location.href = `/login/?next=${encodeURIComponent(window.location.pathname)}`;
    });

    async function loadPost() {
        showLoading();
        try {
            const response = await fetch(`/api/v1/posts/by-code/${encodeURIComponent(shortCode)}`);
            if (response.status === 404) {
                throw new Error(t('Post not found.'));
            }
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const post = await response.json();
            const sourceLanguageCode = post.languages.source_language_code;
            const targetLanguageCode = post.languages.target_language_code;
            const feedPath = `/${sourceLanguageCode}/${targetLanguageCode}/`;
            const feedLabel = `${getLanguageName(sourceLanguageCode)} → ${getLanguageName(targetLanguageCode)}`;

            postsContainer.innerHTML = renderPost(post, { linkToPermalink: false });
            const postAuthor = postsContainer.querySelector('.post-author');
            postAuthor.insertAdjacentHTML(
                'beforeend',
                ` <span aria-hidden="true">•</span> <a class="single-post-feed-link" href="${feedPath}">${feedLabel}</a>`
            );
            embedPost(post);
            attachEngagementHandlers();
            attachExplanationHandlers();
            hideLoading();
        } catch (error) {
            showError(`${t('Error loading post:')} ${error.message}`);
        }
    }

    window.addEventListener('DOMContentLoaded', () => {
        trackAnalyticsEvent('page_landing', { path: window.location.pathname });
        loadPost();
        initUserMenu();
    });
}
