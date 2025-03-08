// Simple live reload script to refresh the page when changes are detected
(function() {
    const CHECK_INTERVAL = 2000; // Check every 2 seconds
    let lastModified = Date.now();
    
    // Function to check if any of the files have changed
    function checkForChanges() {
        // Create a unique timestamp to prevent caching
        const timestamp = Date.now();
        
        // Make a HEAD request to the current page
        fetch(window.location.href + '?t=' + timestamp, { method: 'HEAD' })
            .then(response => {
                const lastModifiedHeader = response.headers.get('Last-Modified');
                if (lastModifiedHeader) {
                    const newLastModified = new Date(lastModifiedHeader).getTime();
                    
                    // If the file has been modified since we last checked, reload the page
                    if (lastModified && newLastModified > lastModified) {
                        console.log('Changes detected, reloading page...');
                        window.location.reload();
                    }
                    
                    lastModified = newLastModified;
                }
            })
            .catch(error => {
                console.error('Error checking for changes:', error);
            });
    }
    
    // Start checking for changes periodically
    setInterval(checkForChanges, CHECK_INTERVAL);
    
    console.log('Live reload activated');
})(); 