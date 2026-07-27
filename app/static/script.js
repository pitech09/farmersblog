// farmersblog - Frontend JavaScript

// CSRF token helper
const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

// ============================================================
// OPTIMISTIC FETCH: Central helper for all optimistic UI actions
// ============================================================
function optimisticFetch(url, options, onRevert) {
    options = options || {};
    options.headers = options.headers || {};
    options.headers['X-Requested-With'] = 'XMLHttpRequest';
    options.headers['X-CSRFToken'] = csrfToken;

    return fetch(url, options)
        .then(function (response) {
            if (response.redirected) {
                window.location.href = response.url;
                return Promise.reject(new Error('Redirect'));
            }
            if (!response.ok) {
                throw new Error('Server returned ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            if (data && data.error) {
                throw new Error(data.error);
            }
            return data;
        })
        .catch(function (error) {
            if (error.message === 'Redirect') return;
            console.error('Optimistic action failed:', error);
            if (typeof onRevert === 'function') onRevert();
            throw error;
        });
}

// ============================================================
// Initialize Bootstrap tooltips
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });

    // Media preview on create post page
    const mediaInput = document.getElementById('media');
    if (mediaInput) {
        mediaInput.addEventListener('change', function (e) {
            const files = e.target.files;
            if (files.length > 0) {
                const container = document.getElementById('previewContainer');
                container.innerHTML = '';
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const reader = new FileReader();
                    const col = document.createElement('div');
                    col.className = 'col-4 col-md-3';
                    reader.onload = function (e) {
                        if (file.type.startsWith('video/')) {
                            col.innerHTML = '<div class="card border-0 rounded-3 overflow-hidden" style="aspect-ratio: 1;">' +
                                '<video class="w-100 h-100" style="object-fit: cover;" muted>' +
                                '<source src="' + e.target.result + '" type="' + file.type + '">' +
                                '</video>' +
                                '<div class="position-absolute top-50 start-50 translate-middle">' +
                                '<i class="bi bi-play-circle-fill text-white" style="font-size: 2rem; opacity: 0.8;"></i>' +
                                '</div></div>';
                        } else {
                            col.innerHTML = '<div class="card border-0 rounded-3 overflow-hidden" style="aspect-ratio: 1;">' +
                                '<img src="' + e.target.result + '" class="w-100 h-100" style="object-fit: cover;" alt="Preview">' +
                                '</div>';
                        }
                        container.appendChild(col);
                    };
                    reader.readAsDataURL(file);
                }
                document.getElementById('mediaPreview').classList.remove('d-none');
                document.getElementById('uploadArea').classList.add('d-none');
            }
        });
    }

    // Comment form submission (delegated to handle dynamic forms)
    document.addEventListener('submit', function (e) {
        if (e.target && e.target.id === 'comment-form') {
            e.preventDefault();
            submitComment(e.target);
        }
    });

    // Like button delegation
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="like"]')) {
            const btn = e.target.closest('[data-action="like"]');
            toggleLike(btn);
        }
    });

    // Follow button delegation
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="follow"]')) {
            const btn = e.target.closest('[data-action="follow"]');
            toggleFollow(btn);
        }
    });

    // Group join button delegation
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="group-join"]')) {
            const btn = e.target.closest('[data-action="group-join"]');
            toggleGroupJoin(btn);
        }
    });

    // Notification mark-as-read delegation (dropdown + page)
    document.addEventListener('click', function(e) {
        const markReadBtn = e.target.closest('.mark-read-btn');
        if (markReadBtn) {
            e.preventDefault();
            e.stopPropagation();
            const id = markReadBtn.dataset.id;
            const row = markReadBtn.closest('.list-group-item, .dropdown-item');
            markNotificationRead(row, id);
        }
    });

    // Mark all as read delegation
    document.addEventListener('click', function(e) {
        if (e.target.closest('#markAllReadBtn')) {
            markAllNotificationsRead();
        }
    });
});

// ============================================================
// OPTIMISTIC UI: Toggle like
// ============================================================
function toggleLike(button) {
    const postId = button.dataset.postId;
    const icon = button.querySelector('i');
    const countSpan = button.querySelector('.like-count');

    if (!icon || !countSpan) return;

    const wasLiked = icon.classList.contains('bi-heart-fill');
    const originalCount = parseInt(countSpan.textContent) || 0;

    function revert() {
        if (wasLiked) {
            icon.className = 'bi bi-heart-fill';
            button.classList.add('liked');
            countSpan.textContent = originalCount;
        } else {
            icon.className = 'bi bi-heart';
            button.classList.remove('liked');
            countSpan.textContent = originalCount;
        }
        showFlashMessage('Failed to update like. Please try again.', 'danger');
    }

    // Optimistic update
    if (wasLiked) {
        icon.className = 'bi bi-heart';
        button.classList.remove('liked');
        countSpan.textContent = originalCount - 1;
    } else {
        icon.className = 'bi bi-heart-fill';
        button.classList.add('liked');
        countSpan.textContent = originalCount + 1;
    }

    // Pulse animation
    button.style.transition = 'transform 0.15s ease';
    button.style.transform = 'scale(1.3)';
    setTimeout(function() {
        button.style.transform = 'scale(1)';
    }, 150);

    optimisticFetch('/posts/' + postId + '/like', { method: 'POST' }, revert)
    .then(function(data) {
        // Sync with server state
        if (data.liked) {
            icon.className = 'bi bi-heart-fill';
            button.classList.add('liked');
        } else {
            icon.className = 'bi bi-heart';
            button.classList.remove('liked');
        }
        countSpan.textContent = data.like_count;
    });
}

// ============================================================
// OPTIMISTIC UI: Toggle follow
// ============================================================
function toggleFollow(button) {
    const username = button.dataset.username;
    const icon = button.querySelector('i');
    const textSpan = button.querySelector('span');
    const countSpan = document.getElementById('followerCount');

    if (!icon || !textSpan) return;

    const wasFollowing = button.classList.contains('btn-outline-secondary');
    const originalText = textSpan.textContent;

    function revert() {
        if (wasFollowing) {
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-primary');
            textSpan.textContent = 'Following';
            icon.className = 'bi bi-person-check me-1';
        } else {
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-secondary');
            textSpan.textContent = 'Follow';
            icon.className = 'bi bi-person-plus me-1';
        }
        showFlashMessage('Failed to update follow status. Try again.', 'danger');
    }

    // Optimistic update
    if (wasFollowing) {
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-primary');
        textSpan.textContent = 'Follow';
        icon.className = 'bi bi-person-plus me-1';
    } else {
        button.classList.remove('btn-primary');
        button.classList.add('btn-outline-secondary');
        textSpan.textContent = 'Following';
        icon.className = 'bi bi-person-check me-1';
    }

    optimisticFetch('/user/' + encodeURIComponent(username) + '/follow', { method: 'POST' }, revert)
    .then(function(data) {
        if (data.following) {
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-secondary');
            textSpan.textContent = 'Following';
            icon.className = 'bi bi-person-check me-1';
        } else {
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-primary');
            textSpan.textContent = 'Follow';
            icon.className = 'bi bi-person-plus me-1';
        }
        if (countSpan) {
            countSpan.textContent = data.follower_count;
        }
    });
}

// ============================================================
// OPTIMISTIC UI: Submit comment
// ============================================================
function submitComment(form) {
    const postId = form.dataset.postId;
    const input = document.getElementById('comment-input');
    const text = input.value.trim();

    if (!text) return;

    const currentUsernameMeta = document.querySelector('meta[name="current-username"]');
    const username = currentUsernameMeta ? currentUsernameMeta.getAttribute('content') : 'You';

    const commentList = document.getElementById('comment-list');
    const tempId = 'temp-' + Date.now();
    const optimisticComment = document.createElement('div');
    optimisticComment.className = 'd-flex gap-3 mb-3 comment-item optimistic-comment';
    optimisticComment.id = tempId;
    optimisticComment.style.opacity = '0.6';
    optimisticComment.innerHTML =
        '<div class="rounded-circle bg-secondary bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 36px; height: 36px;">' +
            '<i class="bi bi-person-fill text-secondary small"></i>' +
        '</div>' +
        '<div class="bg-light rounded-4 px-3 py-2 flex-grow-1">' +
            '<strong class="d-block small">' + escapeHtml(username) + '</strong>' +
            '<p class="mb-0">' + escapeHtml(text) + '</p>' +
            '<small class="text-muted">Sending...</small>' +
        '</div>';
    commentList.appendChild(optimisticComment);

    input.value = '';

    const commentHeader = document.querySelector('h5.fw-semibold.mb-3');
    let originalCount = 0;
    if (commentHeader) {
        var match = commentHeader.textContent.match(/\((\d+)\)/);
        originalCount = match ? parseInt(match[1]) : 0;
        commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + (originalCount + 1) + ')';
    }

    var formData = new FormData();
    formData.append('text', text);

    function revertComment() {
        const tempComment = document.getElementById(tempId);
        if (tempComment) tempComment.remove();
        if (commentHeader) {
            commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + originalCount + ')';
        }
        showFlashMessage('Failed to post comment. Try again.', 'danger');
    }

    optimisticFetch('/posts/' + postId + '/comment', {
        method: 'POST',
        body: formData
    }, revertComment)
    .then(function(data) {
        const tempComment = document.getElementById(tempId);
        if (tempComment) {
            tempComment.style.opacity = '1';
            tempComment.innerHTML =
                '<div class="rounded-circle bg-secondary bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 36px; height: 36px;">' +
                    '<i class="bi bi-person-fill text-secondary small"></i>' +
                '</div>' +
                '<div class="bg-light rounded-4 px-3 py-2 flex-grow-1">' +
                    '<strong class="d-block small">' + escapeHtml(data.author) + '</strong>' +
                    '<p class="mb-0">' + escapeHtml(data.text) + '</p>' +
                    '<small class="text-muted">' + data.created_at + '</small>' +
                '</div>';
            tempComment.removeAttribute('id');
        }
        if (commentHeader && data.comment_count !== undefined) {
            commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + data.comment_count + ')';
        }
    });
}

// ============================================================
// OPTIMISTIC UI: Send message
// ============================================================
function sendMessage(form, input, sendButton, recipientUsername) {
    var originalHTML = sendButton.innerHTML;
    sendButton.disabled = true;
    sendButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Sending';

    const body = input.value.trim();
    if (!body) {
        sendButton.disabled = false;
        sendButton.innerHTML = originalHTML;
        return;
    }

    function showError(msg) {
        showFlashMessage(msg || 'Failed to send message. Try again.', 'danger');
    }

    const tempId = 'temp-msg-' + Date.now();
    const chat = document.getElementById('chatMessages');
    const emptyChat = document.getElementById('emptyChat');
    if (emptyChat) emptyChat.remove();

    const tempMsg = document.createElement('div');
    tempMsg.className = 'd-flex mb-3 justify-content-end optimistic-message';
    tempMsg.id = tempId;
    tempMsg.style.opacity = '0.7';
    var timestamp = new Date().toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
    tempMsg.innerHTML = '<div class="bg-primary text-white rounded-4 px-3 py-2" style="max-width: 75%;">' +
        '<p class="mb-0">' + escapeHtml(body) + '</p>' +
        '<small class="text-white-50 d-block text-end mt-1" style="font-size: 0.7rem;">Sending...</small>' +
        '</div>';
    chat.appendChild(tempMsg);
    chat.scrollTop = chat.scrollHeight;
    input.value = '';

    optimisticFetch('/messages/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            recipient_username: recipientUsername,
            body: body
        })
    }, function() {
        const el = document.getElementById(tempId);
        if (el) el.remove();
        sendButton.disabled = false;
        sendButton.innerHTML = originalHTML;
        showError();
    })
    .then(function(data) {
        const el = document.getElementById(tempId);
        if (el) {
            el.style.opacity = '1';
            el.innerHTML = '<div class="bg-primary text-white rounded-4 px-3 py-2" style="max-width: 75%;">' +
                '<p class="mb-0">' + escapeHtml(data.body) + '</p>' +
                '<small class="text-white-50 d-block text-end mt-1" style="font-size: 0.7rem;">' + data.timestamp + '</small>' +
                '</div>';
            el.removeAttribute('id');
        }
        sendButton.disabled = false;
        sendButton.innerHTML = originalHTML;
        input.value = '';
    })
    .catch(function() {
        sendButton.disabled = false;
        sendButton.innerHTML = originalHTML;
    });
}

// ============================================================
// OPTIMISTIC UI: Toggle group join
// ============================================================
function toggleGroupJoin(button) {
    const groupName = button.dataset.groupName;
    const icon = button.querySelector('i');
    let textSpan = button.querySelector('span');
    if (!textSpan) textSpan = document.getElementById('joinText');
    const card = button.closest('.card');
    let countSpan = card ? card.querySelector('.member-count') : null;
    if (!countSpan) countSpan = document.getElementById('memberCount');

    if (!icon || !textSpan) return;

    const wasJoined = button.classList.contains('btn-outline-secondary');
    const originalText = textSpan.textContent;

    function revert() {
        if (wasJoined) {
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-secondary');
            textSpan.textContent = 'Leave';
            icon.className = 'bi bi-person-check me-1';
        } else {
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-primary');
            textSpan.textContent = 'Join';
            icon.className = 'bi bi-person-plus me-1';
        }
        showFlashMessage('Failed to update group membership. Try again.', 'danger');
    }

    // Optimistic update
    if (wasJoined) {
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-primary');
        textSpan.textContent = 'Join';
        icon.className = 'bi bi-person-plus me-1';
    } else {
        button.classList.remove('btn-primary');
        button.classList.add('btn-outline-secondary');
        textSpan.textContent = 'Leave';
        icon.className = 'bi bi-person-check me-1';
    }

    optimisticFetch('/groups/' + encodeURIComponent(groupName) + '/join', { method: 'POST' }, revert)
    .then(function(data) {
        if (data.joined) {
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-secondary');
            textSpan.textContent = 'Leave';
            icon.className = 'bi bi-person-check me-1';
        } else {
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-primary');
            textSpan.textContent = 'Join';
            icon.className = 'bi bi-person-plus me-1';
        }
        if (countSpan) {
            countSpan.textContent = data.member_count;
        }
    });
}

// ============================================================
// OPTIMISTIC UI: Mark single notification as read
// ============================================================
function markNotificationRead(el, notificationId) {
    if (!el) return;

    const savedClass = el.className;
    const markReadBtns = el.querySelectorAll('.mark-read-btn');
    const originalBadgeText = document.getElementById('notificationBadge') ? document.getElementById('notificationBadge').textContent : '0';

    function revert() {
        el.className = savedClass;
        markReadBtns.forEach(function(btn) { btn.style.display = ''; });
        const badge = document.getElementById('notificationBadge');
        if (badge) badge.textContent = originalBadgeText;
        showFlashMessage('Failed to mark notification as read.', 'danger');
    }

    // Optimistic update
    if (el.classList.contains('notification-unread')) {
        el.classList.remove('notification-unread');
    }
    markReadBtns.forEach(function(btn) { btn.remove(); });

    optimisticFetch('/notifications/' + notificationId + '/read', { method: 'POST' }, revert)
    .then(function(data) {
        if (data.success) {
            updateNotificationCount();
        }
    });
}

// ============================================================
// OPTIMISTIC UI: Mark all notifications as read
// ============================================================
function markAllNotificationsRead() {
    const rows = document.querySelectorAll('.notification-unread');
    const buttons = document.querySelectorAll('.mark-read-btn');
    const markAllBtn = document.getElementById('markAllReadBtn');
    const originalBadgeText = document.getElementById('notificationBadge') ? document.getElementById('notificationBadge').textContent : '0';

    function revert() {
        rows.forEach(function(row) { row.classList.add('notification-unread'); });
        buttons.forEach(function(btn) { btn.style.display = ''; });
        if (markAllBtn) markAllBtn.style.display = '';
        const badge = document.getElementById('notificationBadge');
        if (badge) badge.textContent = originalBadgeText;
        showFlashMessage('Failed to mark all notifications as read.', 'danger');
    }

    // Optimistic update
    rows.forEach(function(row) { row.classList.remove('notification-unread'); });
    buttons.forEach(function(btn) { btn.remove(); });
    if (markAllBtn) markAllBtn.remove();

    optimisticFetch('/notifications/mark-all-read', { method: 'POST' }, revert)
    .then(function(data) {
        if (data.success) {
            updateNotificationCount();
        }
    });
}

// ============================================================
// Update the unread notification count badge
// ============================================================
function updateNotificationCount() {
    optimisticFetch('/notifications/unread-count', { method: 'GET' })
    .then(function(data) {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            badge.textContent = data.count;
            badge.style.display = data.count > 0 ? 'inline' : 'none';
        }
    });
}

// ============================================================
// Helper: Show a temporary flash message
// ============================================================
function showFlashMessage(message, category) {
    var existing = document.querySelector('.flash-message-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.className = 'flash-message-toast alert alert-' + category + ' alert-dismissible fade show rounded-4 shadow-sm';
    toast.style.position = 'fixed';
    toast.style.top = '70px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.zIndex = '9999';
    toast.style.maxWidth = '400px';
    toast.innerHTML = message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    document.body.appendChild(toast);

    setTimeout(function() {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
}

// ============================================================
// Helper: Escape HTML to prevent XSS
// ============================================================
function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Share post (copy link to clipboard)
function sharePost(postId) {
    var url = window.location.origin + '/post/' + postId;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
            showShareToast();
        }).catch(function () {
            fallbackCopy(url);
        });
    } else {
        fallbackCopy(url);
    }
}

function fallbackCopy(text) {
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showShareToast();
    } catch (e) {
        console.error('Copy failed:', e);
    }
    document.body.removeChild(textarea);
}

function showShareToast() {
    var toastEl = document.getElementById('shareToast');
    if (toastEl) {
        var toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}

// ============================================================
// Convert UTC timestamps to local time
// ============================================================
function convertLocalTimes() {
    const elements = document.querySelectorAll('.local-time');
    elements.forEach(function(el) {
        const utc = el.getAttribute('data-utc');
        if (!utc) return;
        const date = new Date(utc + 'Z');
        if (isNaN(date.getTime())) return;
        let formatted;
        try {
            formatted = date.toLocaleString('en-ZA', {
                timeZone: 'Africa/Johannesburg',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        } catch (e) {
            formatted = date.toLocaleString();
        }
        el.textContent = formatted;
    });
}

document.addEventListener('DOMContentLoaded', function () {
    convertLocalTimes();
});

// Delete post (AJAX) - owner only
function deletePost(postId) {
    if (!confirm('Are you sure you want to delete this post?')) {
        return;
    }

    fetch('/posts/' + postId + '/delete', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(function (response) {
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }
        return response.json();
    })
    .then(function (data) {
        if (!data) return;
        if (data.error) {
            console.error(data.error);
            alert(data.error);
            return;
        }
        if (data.success) {
            window.location.href = '/';
        }
    })
    .catch(function (error) {
        console.error('Error deleting post:', error);
        showFlashMessage('Failed to delete post. Try again.', 'danger');
    });
}