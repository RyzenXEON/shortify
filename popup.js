document.addEventListener('DOMContentLoaded', function() {
  const urlInput = document.getElementById('urlInput');
  const shortenButton = document.getElementById('shortenButton');
  const shortUrlResultDiv = document.getElementById('shortUrlResult');
  const shortUrlLink = document.getElementById('shortUrlLink');
  const copyButton = document.getElementById('copyButton');
  const statusMessageDiv = document.getElementById('statusMessage');

  // Function to update status message div
  function updateStatus(message, type = 'info') {
    statusMessageDiv.textContent = message;
    statusMessageDiv.className = ''; // Clear previous classes
    statusMessageDiv.classList.add('hidden'); // Start hidden
    statusMessageDiv.classList.add('status-' + type); // Add type class
    statusMessageDiv.classList.remove('hidden'); // Show
  }

  function clearStatus() {
    statusMessageDiv.textContent = '';
    statusMessageDiv.className = 'hidden'; // Hide and clear classes
  }

  function showResult(shortUrl) {
    shortUrlLink.href = shortUrl;
    shortUrlLink.textContent = shortUrl;
    shortUrlResultDiv.classList.remove('hidden');
  }

  function hideResult() {
    shortUrlResultDiv.classList.add('hidden');
    shortUrlLink.href = '#';
    shortUrlLink.textContent = '';
     copyButton.textContent = 'Copy'; // Reset copy button text
  }


  // Get the current tab's URL and populate the input
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    if (tabs && tabs[0] && tabs[0].url) {
      // Avoid pre-filling chrome:// or about: URLs
      if (!tabs[0].url.startsWith('chrome://') && !tabs[0].url.startsWith('about:')) {
          urlInput.value = tabs[0].url;
      }
    }
  });

  shortenButton.addEventListener('click', async () => {
    const longUrl = urlInput.value.trim();
    clearStatus();
    hideResult(); // Hide previous results

    if (!longUrl) {
      updateStatus('Please enter a URL.', 'error');
      return;
    }

    // Basic URL validation
    try {
        new URL(longUrl);
    } catch (e) {
        updateStatus('Please enter a valid URL.', 'error');
        return;
    }


    // Call your API Gateway endpoint
    const apiUrl = 'https://thexeon.tech/shorten'; // REPLACE WITH YOUR DOMAIN URL

    shortenButton.disabled = true; // Disable button while processing
    updateStatus('Shortening...', 'info');

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ long_url: longUrl })
      });

      if (!response.ok) {
        // Attempt to read error from body, fallback to status text
        let errorDetail = response.statusText;
        try {
             const errorData = await response.json();
             if (errorData && errorData.error) {
                 errorDetail = errorData.error;
             } else {
                 errorDetail = JSON.stringify(errorData); // Show raw body if not expected format
             }
        } catch (e) {
            // If body is not JSON, just use status text
            console.error("Failed to parse error body:", e);
        }
        throw new Error(`API Error (${response.status}): ${errorDetail}`);
      }

      const data = await response.json();
      const shortUrl = data.short_url;

      showResult(shortUrl);
      updateStatus('URL shortened successfully!', 'success');

    } catch (error) {
      console.error('Shortening failed:', error);
      updateStatus(`Error: ${error.message}`, 'error');

    } finally {
       shortenButton.disabled = false; // Always re-enable button
    }
  });

  // Add copy functionality
  copyButton.addEventListener('click', () => {
    const textToCopy = shortUrlLink.textContent;
    if (textToCopy) {
         navigator.clipboard.writeText(textToCopy).then(() => {
           // Optional: Provide visual feedback that text was copied
           copyButton.textContent = 'Copied!';
           setTimeout(() => {
             copyButton.textContent = 'Copy'; // Reset text
           }, 2000);
         }).catch(err => {
           console.error('Failed to copy:', err);
           // Optionally show a temporary status message here
         });
    }
  });

});