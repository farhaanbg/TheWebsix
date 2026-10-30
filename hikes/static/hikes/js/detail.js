(() => {
    const main = document.getElementById('trail-main-photo');
    const caption = document.getElementById('trail-photo-caption');
    const photos = Array.from(document.querySelectorAll('[data-gallery-photo]'));
    const select = (photo) => {
        main.src = photo.href;
        main.alt = photo.dataset.caption;
        caption.textContent = `Photo ${photos.indexOf(photo) + 1} of ${photos.length}: ${photo.dataset.caption}`;
        photos.forEach(item => {
            item.classList.toggle('is-active', item === photo);
            if (item === photo) item.setAttribute('aria-current', 'true');
            else item.removeAttribute('aria-current');
        });
    };
    photos.forEach((photo, index) => {
        photo.addEventListener('click', event => { event.preventDefault(); select(photo); });
        photo.addEventListener('keydown', event => {
            let next;
            if (event.key === 'ArrowRight') next = (index + 1) % photos.length;
            if (event.key === 'ArrowLeft') next = (index - 1 + photos.length) % photos.length;
            if (event.key === 'Home') next = 0;
            if (event.key === 'End') next = photos.length - 1;
            if (next !== undefined) { event.preventDefault(); select(photos[next]); photos[next].focus(); }
        });
    });
    const share = document.getElementById('trail-share');
    if (share) {
        share.hidden = false;
        share.addEventListener('click', async () => {
            const status = document.getElementById('trail-share-status');
            try {
                if (navigator.share) await navigator.share({ title: document.title, url: location.href });
                else if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(location.href);
                    status.textContent = 'Link copied.';
                } else status.textContent = `Share this link: ${location.href}`;
            } catch (error) {
                if (error.name !== 'AbortError') status.textContent = `Share this link: ${location.href}`;
            }
        });
    }
})();
