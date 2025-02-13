    // Add title overlays to all photo items
    document.querySelectorAll('.gallery-item').forEach(item => {
        const img = item.querySelector('img');
        const title = img.dataset.title;
        
        const titleOverlay = document.createElement('div');
        titleOverlay.className = 'title-overlay';
        titleOverlay.textContent = title;
        item.appendChild(titleOverlay);
    });
    
    // Open lightbox when an image is clicked
    document.querySelectorAll('.photo-item img, .gallery-item img').forEach(image => {
        image.addEventListener('click', () => {
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
            overlay.style.zIndex = '999'; // Below the lightbox but above everything else

            const lightbox = document.createElement('div');
            lightbox.className = 'lightbox';
            lightbox.innerHTML = `<img src="${image.src}" alt="Recipe Image">`;
            lightbox.style.zIndex = '1000'; // Ensure lightbox is on top of overlay

            const info = document.createElement('div');
            info.className = 'lightbox-info';
            info.innerHTML = `<p>Click anywhere outside the photo to exit.</p>`
            info.style.zIndex = '1001';

            document.body.appendChild(overlay);
            document.body.appendChild(lightbox);
            document.body.appendChild(info);

            document.body.style.overflow = 'hidden'; // Prevent scrolling

            // Close lightbox when clicked on overlay or lightbox
            const closeLightbox = () => {
                overlay.remove();
                lightbox.remove();
                info.remove();
                document.body.style.overflow = ''; // Restore scrolling
            };

            overlay.addEventListener('click', closeLightbox);
            lightbox.addEventListener('click', closeLightbox);
            info.addEventListener('click', closeLightbox)
        });
    });

    // Adjust color values
    document.addEventListener('DOMContentLoaded', (event) => {
        function updateValue(elementId, valueId) {
            const slider = document.getElementById(elementId);
            const valueDisplay = document.getElementById(valueId);
            
            if (slider && valueDisplay) { // Check if both elements exist
                slider.addEventListener('input', function() {
                    valueDisplay.textContent = this.value;
                });
            }
        }
        
        updateValue('prep_time', 'prep_time_value');
        updateValue('cook_time', 'cook_time_value');
    });

    // Clear search filters and reload the page
    function clearSearch() {
        document.getElementById('search-form').reset();
        // Redirect to the search page without any parameters to clear all filters
        window.location.href = "/";
    }

    // Modal Flash Messages
    document.addEventListener('DOMContentLoaded', function() {
        const flashModals = document.querySelectorAll('.flash-modal');
        
        flashModals.forEach(modal => {
            // Show the modal
            setTimeout(() => {
                modal.style.opacity = '1';
                modal.classList.add('show');
            }, 100);
    
            // Auto-hide after 3 seconds
            setTimeout(() => {
                modal.style.opacity = '0';
                setTimeout(() => {
                    modal.remove();
                }, 300); // Wait for fade-out transition to complete
            }, 3000);
    
            // Close button functionality
            const closeButton = modal.querySelector('.flash-close');
            closeButton.addEventListener('click', () => {
                modal.style.opacity = '0';
                setTimeout(() => {
                    modal.remove();
                }, 300);
            });
        });
    });