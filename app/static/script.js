// farmersblog - Frontend JavaScript

// CSRF token helper
const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

// Initialize Bootstrap tooltips
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
});

// Toggle read more for long captions (delegated event listener)
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('caption-toggle')) {
        const container = e.target.closest('.caption-container');
        const preview = container.querySelector('.caption-preview');
        const full = container.querySelector('.caption-full');
        const btn = e.target;
        if (btn.dataset.action === 'expand') {
            preview.classList.add('d-none');
            full.classList.remove('d-none');
            btn.textContent = ' show less';
            btn.dataset.action = 'collapse';
        } else {
            preview.classList.remove('d-none');
            full.classList.add('d-none');
            btn.textContent = '...see more';
            btn.dataset.action = 'expand';
        }
    }
});

// Clear media preview
function clearMediaPreview() {
    document.getElementById('media').value = '';
    document.getElementById('mediaPreview').classList.add('d-none');
    document.getElementById('uploadArea').classList.remove('d-none');
    document.getElementById('previewContainer').innerHTML = '';
}

// ============================================================
// OPTIMISTIC UI: Toggle like (AJAX) with immediate UI update
// ============================================================
function toggleLike(button) {
    const postId = button.dataset.postId;
    const icon = button.querySelector('i');
    const countSpan = button.querySelector('.like-count');

    // Cache the original state before making changes
    const wasLiked = icon.classList.contains('bi-heart-fill');
    const originalCount = parseInt(countSpan.textContent) || 0;

    // --- OPTIMISTIC UPDATE: Apply changes immediately ---
    if (wasLiked) {
        icon.className = 'bi bi-heart';
        button.classList.remove('liked');
        countSpan.textContent = originalCount - 1;
    } else {
        icon.className = 'bi bi-heart-fill';
        button.classList.add('liked');
        countSpan.textContent = originalCount + 1;
    }

    // Add a small scale pulse animation
    button.style.transition = 'transform 0.15s ease';
    button.style.transform = 'scale(1.3)';
    setTimeout(function() {
        button.style.transform = 'scale(1)';
    }, 150);

    // --- SEND AJAX REQUEST ---
    fetch('/posts/' + postId + '/like', {
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
        if (!response.ok) {
            throw new Error('Server returned ' + response.status);
        }
        return response.json();
    })
    .then(function (data) {
        if (!data) return;
        // Update with server-confirmed values
        if (data.liked) {
            icon.className = 'bi bi-heart-fill';
            button.classList.add('liked');
        } else {
            icon.className = 'bi bi-heart';
            button.classList.remove('liked');
        }
        countSpan.textContent = data.like_count;
    })
    .catch(function (error) {
        console.error('Error toggling like:', error);
        // --- REVERT on failure ---
        if (wasLiked) {
            icon.className = 'bi bi-heart-fill';
            button.classList.add('liked');
            countSpan.textContent = originalCount;
        } else {
            icon.className = 'bi bi-heart';
            button.classList.remove('liked');
            countSpan.textContent = originalCount;
        }
        showFlashMessage('Failed to like. Try again.', 'danger');
    });
}

// ============================================================
// OPTIMISTIC UI: Submit comment (AJAX) with immediate append
// ============================================================
function submitComment(form) {
    const postId = form.dataset.postId;
    const input = document.getElementById('comment-input');
    const text = input.value.trim();

    if (!text) return;

    // Get current username from the page (fallback to 'You')
    const currentUsername = document.querySelector('meta[name="current-username"]');
    const username = currentUsername ? currentUsername.getAttribute('content') : 'You';

    // --- OPTIMISTIC UPDATE: Append comment immediately ---
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

    // Clear input immediately
    input.value = '';

    // Update comment count optimistically
    const commentHeader = document.querySelector('h5.fw-semibold.mb-3');
    let originalCount = 0;
    if (commentHeader) {
        var match = commentHeader.textContent.match(/\((\d+)\)/);
        originalCount = match ? parseInt(match[1]) : 0;
        commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + (originalCount + 1) + ')';
    }

    // --- SEND AJAX REQUEST ---
    var formData = new FormData();
    formData.append('text', text);

    fetch('/posts/' + postId + '/comment', {
        method: 'POST',
        body: formData,
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
        if (!response.ok) {
            throw new Error('Server returned ' + response.status);
        }
        return response.json();
    })
    .then(function (data) {
        if (!data) return;
        if (data.error) {
            throw new Error(data.error);
        }

        // --- SUCCESS: Replace optimistic comment with real one ---
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

        // Update comment count with server data if available
        if (commentHeader && data.comment_count !== undefined) {
            commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + data.comment_count + ')';
        }
    })
    .catch(function (error) {
        console.error('Error submitting comment:', error);
        // --- FAILURE: Remove the optimistic comment ---
        const tempComment = document.getElementById(tempId);
        if (tempComment) {
            tempComment.remove();
        }
        // Revert comment count
        if (commentHeader) {
            commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + originalCount + ')';
        }
        showFlashMessage('Failed to post comment. Try again.', 'danger');
    });
}

// ============================================================
// Helper: Show a temporary flash message
// ============================================================
function showFlashMessage(message, category) {
    // Remove any existing flash messages
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

    // Auto-dismiss after 4 seconds
    setTimeout(function() {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 4000);
}

// ============================================================
// Helper: Escape HTML to prevent XSS
// ============================================================
function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Toggle follow (AJAX)
function toggleFollow(button) {
    const username = button.dataset.username;
    const icon = button.querySelector('i');
    const textSpan = button.querySelector('span') || document.getElementById('followText');
    const countSpan = document.getElementById('followerCount');

    fetch('/user/' + username + '/follow', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(function (response) { return response.json(); })
    .then(function (data) {
        if (data.error) {
            console.error(data.error);
            return;
        }
        if (data.following) {
            if (icon) { icon.className = 'bi bi-person-check me-1'; }
            if (textSpan) textSpan.textContent = 'Following';
            button.className = 'btn btn-outline-secondary rounded-pill px-4';
        } else {
            if (icon) { icon.className = 'bi bi-person-plus me-1'; }
            if (textSpan) textSpan.textContent = 'Follow';
            button.className = 'btn btn-primary rounded-pill px-4';
        }
        if (countSpan) {
            countSpan.textContent = data.follower_count;
        }
    })
    .catch(function (error) {
        console.error('Error toggling follow:', error);
        showFlashMessage('Failed to update follow status. Try again.', 'danger');
    });
}

// Toggle group join (AJAX)
function toggleGroupJoin(button) {
    const groupName = button.dataset.groupName;
    const icon = button.querySelector('i');
    const textSpan = document.getElementById('joinText');
    const countSpan = document.getElementById('memberCount');

    fetch('/groups/' + encodeURIComponent(groupName) + '/join', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(function (response) { return response.json(); })
    .then(function (data) {
        if (data.joined) {
            icon.className = 'bi bi-person-check me-1';
            textSpan.textContent = 'Joined';
            button.className = 'btn btn-outline-secondary rounded-pill px-4';
        } else {
            icon.className = 'bi bi-person-plus me-1';
            textSpan.textContent = 'Join';
            button.className = 'btn btn-primary rounded-pill px-4';
        }
        if (countSpan) {
            countSpan.textContent = data.member_count;
        }
    })
    .catch(function (error) {
        console.error('Error toggling group join:', error);
        showFlashMessage('Failed to update group membership. Try again.', 'danger');
    });
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
        const date = new Date(utc);
        if (isNaN(date.getTime())) return;
        let formatted;
        try {
            formatted = date.toLocaleString('en-US', {
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
// ============================================================
// Notification sound polling (Web Audio API)
// ============================================================
function playNotificationSound() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();

        function beep(freq, startTime, duration) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.25, startTime);
            gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(startTime);
            osc.stop(startTime + duration);
        }

        const now = ctx.currentTime;
        beep(880, now, 0.12);
        beep(1047, now + 0.14, 0.12);
    } catch (e) {
        console.error('Error playing notification sound:', e);
    }
}

function startNotificationPolling() {
    let lastNotificationCount = null;
    const csrf = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const isAuthenticated = document.querySelector('meta[name="current-username"]') !== null;

    if (!isAuthenticated) return;

    function poll() {
        fetch('/notifications/unread-count', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrf
            }
        })
        .then(function (response) { return response.json(); })
        .then(function (data) {
            const count = typeof data.count === 'number' ? data.count : 0;
            if (lastNotificationCount === null) {
                lastNotificationCount = count;
                return;
            }
            if (count > lastNotificationCount) {
                playNotificationSound();
            }
            lastNotificationCount = count;
        })
        .catch(function (error) {
            console.error('Notification polling error:', error);
        });
    }

    poll();
    setInterval(poll, 10000);
}

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
            // Redirect to home page after successful deletion
            window.location.href = '/';
        }
    })
    .catch(function (error) {
        console.error('Error deleting post:', error);
        showFlashMessage('Failed to delete post. Try again.', 'danger');
    });
}