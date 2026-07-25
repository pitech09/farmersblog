// farmersblog - Frontend JavaScript

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

    // Comment form submission
    const commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function (e) {
            e.preventDefault();
            submitComment(this);
        });
    }
});

// Toggle read more for long captions
function toggleReadMore(link) {
    var preview = link.parentElement.querySelector('.caption-preview');
    var full = link.parentElement.querySelector('.caption-full');
    if (full.classList.contains('d-none')) {
        preview.classList.add('d-none');
        full.classList.remove('d-none');
        link.textContent = 'show less';
    } else {
        preview.classList.remove('d-none');
        full.classList.add('d-none');
        link.textContent = 'read more';
    }
}

// Clear media preview
function clearMediaPreview() {
    document.getElementById('media').value = '';
    document.getElementById('mediaPreview').classList.add('d-none');
    document.getElementById('uploadArea').classList.remove('d-none');
    document.getElementById('previewContainer').innerHTML = '';
}

// Toggle like (AJAX)
function toggleLike(button) {
    const postId = button.dataset.postId;
    const icon = button.querySelector('i');
    const countSpan = button.querySelector('.like-count');

    fetch('/posts/' + postId + '/like', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
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
        window.location.reload();
    });
}

// Toggle follow (AJAX)
function toggleFollow(button) {
    const username = button.dataset.username;
    const icon = button.querySelector('i');
    const textSpan = document.getElementById('followText');
    const countSpan = document.getElementById('followerCount');

    fetch('/user/' + username + '/follow', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(function (response) { return response.json(); })
    .then(function (data) {
        if (data.error) {
            console.error(data.error);
            return;
        }
        if (data.following) {
            icon.className = 'bi bi-person-check me-1';
            textSpan.textContent = 'Following';
            button.className = 'btn btn-outline-secondary rounded-pill px-4';
        } else {
            icon.className = 'bi bi-person-plus me-1';
            textSpan.textContent = 'Follow';
            button.className = 'btn btn-primary rounded-pill px-4';
        }
        if (countSpan) {
            countSpan.textContent = data.follower_count;
        }
    })
    .catch(function (error) {
        console.error('Error toggling follow:', error);
        window.location.reload();
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
            'X-Requested-With': 'XMLHttpRequest'
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
        window.location.reload();
    });
}

// Submit comment (AJAX)
function submitComment(form) {
    const postId = form.dataset.postId;
    const input = document.getElementById('comment-input');
    const text = input.value.trim();

    if (!text) return;

    var formData = new FormData();
    formData.append('text', text);

    fetch('/posts/' + postId + '/comment', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
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
            return;
        }

        // Append new comment to list
        const commentList = document.getElementById('comment-list');
        const newComment = document.createElement('div');
        newComment.className = 'd-flex gap-3 mb-3 comment-item';
        newComment.innerHTML =
            '<div class="rounded-circle bg-secondary bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 36px; height: 36px;">' +
                '<i class="bi bi-person-fill text-secondary small"></i>' +
            '</div>' +
            '<div class="bg-light rounded-4 px-3 py-2 flex-grow-1">' +
                '<strong class="d-block small">' + data.author + '</strong>' +
                '<p class="mb-0">' + data.text + '</p>' +
                '<small class="text-muted">' + data.created_at + '</small>' +
            '</div>';
        commentList.appendChild(newComment);

        // Clear input
        input.value = '';

        // Update comment count on the page if present
        const commentHeader = document.querySelector('h5.fw-semibold.mb-3');
        if (commentHeader) {
            var match = commentHeader.textContent.match(/\((\d+)\)/);
            var count = match ? parseInt(match[1]) + 1 : 1;
            commentHeader.innerHTML = '<i class="bi bi-chat me-2"></i>Comments (' + count + ')';
        }
    })
    .catch(function (error) {
        console.error('Error submitting comment:', error);
        window.location.reload();
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