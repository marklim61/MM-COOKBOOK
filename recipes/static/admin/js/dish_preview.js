document.addEventListener('DOMContentLoaded', function() {              // Wait for the DOM to load
    const imageInput = document.getElementById('id_image');             // Get the image input
    const livePreview = document.getElementById('live-preview');        // Get the live preview
    
    if (imageInput && livePreview) {                                    // If both elements exist
        imageInput.addEventListener('change', function(e) {             // When the image input changes
            const file = e.target.files[0];                             // Get the selected file    
            if (file) {                                                 // If a file is selected
                // Modern approach using object URLs (no FileReader needed)
                livePreview.src = URL.createObjectURL(file);            // Set the source of the live preview
                livePreview.style.display = 'block';                    // Show the live preview
                
                // Clean up memory when preview is replaced
                livePreview.onload = function() {                       // When the live preview is loaded
                    URL.revokeObjectURL(this.src);                      // Revoke the object URL
                }
            }
        });
    }
});