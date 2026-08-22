function initCreatePostPage(config) {
    const supportedPairs = new Set([
        'es:en',
        'fr:en',
        'ja:en',
        'ko:en',
        'ja:zh-hant',
        'ko:zh-hant',
        'es:zh-hant',
    ]);

    const form = document.getElementById('createPostForm');
    const sourceRawUrlInput = document.getElementById('sourceRawUrl');
    const sourceLanguageSelect = document.getElementById('sourceLanguageCode');
    const targetLanguageSelect = document.getElementById('targetLanguageCode');
    const translationTextarea = document.getElementById('translationText');
    const explanationTextarea = document.getElementById('explanationText');
    const sourceStatus = document.getElementById('sourceStatus');
    const pairStatus = document.getElementById('pairStatus');
    const publishBtn = document.getElementById('publishBtn');
    const publishError = document.getElementById('publishError');
    const publishSuccess = document.getElementById('publishSuccess');
    const previewContainer = document.getElementById('previewContainer');
    const previewEmpty = document.getElementById('previewEmpty');
    const previewContributionFields = document.getElementById('previewContributionFields');

    let previewTimeout = null;
    let currentPreviewSourceUrl = null;
    let currentPreviewSourceProvider = null;

    window.isAuthenticated = true;

    sourceLanguageSelect.value = config.sourceLanguageCode;
    targetLanguageSelect.value = config.targetLanguageCode;

    function escapePreviewHtml(value) {
        if (value === null || value === undefined) {
            return '';
        }

        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderPreviewPost(post) {
        const authorDisplayName = escapePreviewHtml(post.author?.display_name || 'Anonymous');
        const languageLine = `${getLanguageName(post.languages.source_language_code)} → ${getLanguageName(post.languages.target_language_code)}`;
        const authorLine = `${languageLine} • ${t('By')} <strong>${authorDisplayName}</strong> • ${formatDate(post.created_at)}`;

        return `
            <div class="post-card" data-post-id="${post.id}">
                <div class="post-embed" id="embed-${post.id}">
                    <div class="embed-loading">${t('Loading embedded post...')}</div>
                </div>
                <div class="post-contribution"></div>
                <div class="post-author">
                    ${authorLine}
                </div>
            </div>
        `;
    }

    function getFeedPath() {
        return `/${sourceLanguageSelect.value}/${targetLanguageSelect.value}/`;
    }

    function detectSourceProvider(urlValue) {
        try {
            const parsed = new URL(urlValue);
            let hostname = parsed.hostname.toLowerCase();

            if (hostname.startsWith('www.')) {
                hostname = hostname.slice(4);
            }
            if (hostname.startsWith('m.')) {
                hostname = hostname.slice(2);
            }

            const providers = {
                reddit: ['reddit.com', 'redd.it'],
                instagram: ['instagram.com'],
                twitter: ['twitter.com', 'x.com'],
                imgur: ['imgur.com'],
                facebook: ['facebook.com', 'fb.watch'],
            };

            for (const [provider, domains] of Object.entries(providers)) {
                for (const domain of domains) {
                    if (hostname === domain || hostname.endsWith(`.${domain}`)) {
                        return provider;
                    }
                }
            }
        } catch (err) {
            return null;
        }

        return null;
    }

    function getPairKey() {
        return `${sourceLanguageSelect.value}:${targetLanguageSelect.value}`;
    }

    function isPairSupported() {
        return supportedPairs.has(getPairKey());
    }

    function updatePairStatus() {
        if (isPairSupported()) {
            pairStatus.textContent = '';
            pairStatus.className = 'field-status';
        } else {
            pairStatus.textContent = t('That language pair is not supported yet.');
            pairStatus.className = 'field-status is-invalid';
        }
    }

    function updateSourceStatus() {
        const urlValue = sourceRawUrlInput.value.trim();
        const provider = detectSourceProvider(urlValue);

        if (!urlValue) {
            sourceStatus.textContent = '';
            sourceStatus.className = 'field-status';
            return null;
        }

        if (provider) {
            sourceStatus.textContent = '';
            sourceStatus.className = 'field-status';
            return provider;
        }

        sourceStatus.textContent = t('Only Reddit, Instagram, X/Twitter, Imgur, and Facebook URLs are supported right now.');
        sourceStatus.className = 'field-status is-invalid';
        return null;
    }

    function buildPreviewPost(provider) {
        return {
            id: 'preview-post',
            created_at: new Date().toISOString(),
            languages: {
                source_language_code: sourceLanguageSelect.value,
                target_language_code: targetLanguageSelect.value,
            },
            source: {
                raw_url: sourceRawUrlInput.value.trim(),
                canonical_url: sourceRawUrlInput.value.trim(),
                provider: provider,
            },
            contribution: {
                translation: {
                    text: translationTextarea.value.trim(),
                },
                explanation: {
                    text: explanationTextarea.value.trim(),
                },
            },
            author: {
                id: config.authorId,
                display_name: config.authorDisplayName || 'Anonymous',
            },
        };
    }

    function clearPreview() {
        previewContainer.innerHTML = '';
        previewContainer.style.display = 'none';
        previewEmpty.style.display = 'block';
        previewContributionFields.style.display = 'none';
        currentPreviewSourceUrl = null;
        currentPreviewSourceProvider = null;
    }

    function mountContributionFields() {
        const postCard = previewContainer.querySelector('.post-card');
        if (!postCard) {
            return;
        }

        const contribution = postCard.querySelector('.post-contribution');
        if (!contribution) {
            return;
        }

        previewContributionFields.style.display = 'grid';
        contribution.innerHTML = '';
        contribution.appendChild(previewContributionFields);
    }

    function renderPreview() {
        const provider = updateSourceStatus();
        updatePairStatus();

        const hasMinimumContent = Boolean(provider && isPairSupported());
        if (!hasMinimumContent) {
            clearPreview();
            return;
        }

        const previewPost = buildPreviewPost(provider);
        const nextSourceUrl = previewPost.source.canonical_url;
        const shouldRemountPreview =
            !previewContainer.querySelector('.post-card');
        const shouldRemountEmbed =
            shouldRemountPreview ||
            currentPreviewSourceUrl !== nextSourceUrl ||
            currentPreviewSourceProvider !== provider;

        if (shouldRemountPreview) {
            previewContainer.innerHTML = renderPreviewPost(previewPost);
            previewContainer.style.display = 'grid';
            previewEmpty.style.display = 'none';
            mountContributionFields();
        } else {
            const postCard = previewContainer.querySelector('.post-card');
            const authorDisplayName = escapePreviewHtml(previewPost.author?.display_name || 'Anonymous');
            const languageLine = `${getLanguageName(previewPost.languages.source_language_code)} → ${getLanguageName(previewPost.languages.target_language_code)}`;
            const authorLine = `${languageLine} • ${t('By')} <strong>${authorDisplayName}</strong> • ${formatDate(previewPost.created_at)}`;
            const postAuthor = postCard?.querySelector('.post-author');

            previewContainer.style.display = 'grid';
            previewEmpty.style.display = 'none';
            if (postAuthor) {
                postAuthor.innerHTML = authorLine;
            }
            mountContributionFields();
        }

        if (shouldRemountEmbed) {
            const embedContainer = previewContainer.querySelector(`#embed-${previewPost.id}`);
            if (embedContainer) {
                embedContainer.innerHTML = `<div class="embed-loading">${t('Loading embedded post...')}</div>`;
            }
            embedPost(previewPost);
            currentPreviewSourceUrl = nextSourceUrl;
            currentPreviewSourceProvider = provider;
        }
    }

    function schedulePreviewRender() {
        if (previewTimeout) {
            clearTimeout(previewTimeout);
        }
        previewTimeout = setTimeout(renderPreview, 250);
    }

    function resetMessages() {
        publishError.style.display = 'none';
        publishError.textContent = '';
        publishSuccess.style.display = 'none';
        publishSuccess.innerHTML = '';
    }

    function resetDraftFields(options = {}) {
        const { clearMessages = true } = options;
        form.reset();
        sourceRawUrlInput.value = '';
        translationTextarea.value = '';
        explanationTextarea.value = '';
        sourceLanguageSelect.value = config.sourceLanguageCode;
        targetLanguageSelect.value = config.targetLanguageCode;
        updatePairStatus();
        updateSourceStatus();
        clearPreview();
        if (clearMessages) {
            resetMessages();
        }
    }

    function validateContributionFields() {
        const hasTranslation = Boolean(translationTextarea.value.trim());
        const hasExplanation = Boolean(explanationTextarea.value.trim());

        if (!hasTranslation && !hasExplanation) {
            return t('Either translation or explanation is required.');
        }

        return null;
    }

    async function handleSubmit(event) {
        event.preventDefault();
        resetMessages();

        const provider = updateSourceStatus();
        updatePairStatus();

        if (!provider) {
            publishError.textContent = t('Only Reddit, Instagram, X/Twitter, Imgur, and Facebook URLs are supported right now.');
            publishError.style.display = 'block';
            return;
        }

        if (!isPairSupported()) {
            publishError.textContent = t('That language pair is not supported yet.');
            publishError.style.display = 'block';
            return;
        }

        const contributionError = validateContributionFields();
        if (contributionError) {
            publishError.textContent = contributionError;
            publishError.style.display = 'block';
            return;
        }

        publishBtn.disabled = true;
        publishBtn.textContent = t('Publishing...');

        try {
            const response = await fetch('/api/v1/posts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    source_raw_url: sourceRawUrlInput.value.trim(),
                    source_language_code: sourceLanguageSelect.value,
                    target_language_code: targetLanguageSelect.value,
                    translation_text: translationTextarea.value.trim(),
                    explanation_text: explanationTextarea.value.trim(),
                }),
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json().catch(() => ({}));

            trackAnalyticsEvent('publish_success', {
                post_id: data.id || null,
                source_language_code: sourceLanguageSelect.value,
                target_language_code: targetLanguageSelect.value,
            });

            window.location.assign(data.permalink);
        } catch (err) {
            publishError.textContent = err.message;
            publishError.style.display = 'block';
        } finally {
            publishBtn.disabled = false;
            publishBtn.textContent = t('Publish Post');
        }
    }

    [sourceRawUrlInput, sourceLanguageSelect, targetLanguageSelect].forEach((field) => {
        field.addEventListener('input', schedulePreviewRender);
    });

    form.addEventListener('submit', handleSubmit);

    function initializePage() {
        resetDraftFields();
        trackAnalyticsEvent('create_post_open', {
            path: window.location.pathname,
            source_language_code: sourceLanguageSelect.value,
            target_language_code: targetLanguageSelect.value,
        });
        initUserMenu();
    }

    window.addEventListener('DOMContentLoaded', initializePage);
    window.addEventListener('pageshow', resetDraftFields);
}
