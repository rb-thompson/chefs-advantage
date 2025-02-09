    // Open lightbox when an image is clicked
    document.querySelectorAll('.photo-item img').forEach(image => {
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

            document.body.appendChild(overlay);
            document.body.appendChild(lightbox);

            document.body.style.overflow = 'hidden'; // Prevent scrolling

            // Close lightbox when clicked on overlay or lightbox
            const closeLightbox = () => {
                overlay.remove();
                lightbox.remove();
                document.body.style.overflow = ''; // Restore scrolling
            };

            overlay.addEventListener('click', closeLightbox);
            lightbox.addEventListener('click', closeLightbox);
        });
    });


    // Adjust color values
    document.addEventListener('DOMContentLoaded', (event) => {
        function updateValue(elementId, valueId) {
            const slider = document.getElementById(elementId);
            const valueDisplay = document.getElementById(valueId);
            
            slider.addEventListener('input', function() {
                valueDisplay.textContent = this.value;
            });
        }
        
        updateValue('prep_time', 'prep_time_value');
        updateValue('cook_time', 'cook_time_value');
    });