/**
 * Helios Timezone Display Utility
 * Uses built-in browser Intl API for timezone conversion
 */

(function() {
  'use strict';

  // Formatters using browser's built-in Intl API
  const utcFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  const localFormatter = new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  /**
   * Get timezone name/abbreviation using Intl API
   */
  function getLocalTimezoneName() {
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZoneName: 'short'
    });
    const parts = formatter.formatToParts(new Date());
    const tzPart = parts.find(part => part.type === 'timeZoneName');
    return tzPart ? tzPart.value : 'Local';
  }

  /**
   * Convert a UTC timestamp element to show both UTC and local time
   */
  function convertTimestamp(element) {
    const utcDateStr = element.getAttribute('data-utc-time') || element.textContent.trim();

    // Skip if already converted
    if (element.classList.contains('tz-converted')) {
      return;
    }

    // Parse datetime - assume UTC if no timezone specified
    const date = new Date(utcDateStr + ' UTC');

    if (isNaN(date.getTime())) {
      // Try without ' UTC' suffix
      const altDate = new Date(utcDateStr);
      if (isNaN(altDate.getTime())) {
        console.warn('Could not parse datetime:', utcDateStr);
        return;
      }
      date.setTime(altDate.getTime());
    }

    // Format using browser's Intl API
    const utcFormatted = utcFormatter.format(date);
    const localFormatted = localFormatter.format(date);
    const localTz = getLocalTimezoneName();

    // Check if user is in UTC timezone
    const sameAsUTC = date.getTimezoneOffset() === 0;

    // Create the display
    const container = document.createElement('span');
    container.className = 'tz-display';

    if (sameAsUTC) {
      // If browser is in UTC, just show UTC
      container.innerHTML = `<strong>${utcFormatted} UTC</strong>`;
    } else {
      // Show both UTC and local
      container.innerHTML = `
        <span class="tz-utc" title="Universal Coordinated Time">${utcFormatted} UTC</span>
        <span class="tz-separator"> / </span>
        <span class="tz-local" title="Your local timezone">${localFormatted} ${localTz}</span>
      `;
    }

    // Replace element content
    element.innerHTML = '';
    element.appendChild(container);
    element.classList.add('tz-converted');
  }

  /**
   * Update datetime-local input helper text
   */
  function updateDateTimeInputHelper(input) {
    const value = input.value;
    if (!value) return;

    // Parse the datetime-local value (format: YYYY-MM-DDTHH:MM)
    const date = new Date(value + ':00Z'); // Add seconds and Z for UTC

    if (isNaN(date.getTime())) {
      return;
    }

    // Get or create helper element
    let helper = input.nextElementSibling;
    if (!helper || !helper.classList.contains('tz-input-helper')) {
      helper = document.createElement('div');
      helper.className = 'tz-input-helper';
      input.parentNode.insertBefore(helper, input.nextSibling);
    }

    // Format using browser's Intl API
    const utcFormatted = utcFormatter.format(date);
    const localFormatted = localFormatter.format(date);
    const localTz = getLocalTimezoneName();

    // Check if user is in UTC timezone
    const sameAsUTC = date.getTimezoneOffset() === 0;

    if (sameAsUTC) {
      helper.innerHTML = `<small>This time is: <strong>${utcFormatted} UTC</strong></small>`;
    } else {
      helper.innerHTML = `<small>This time is: <strong>${utcFormatted} UTC</strong> / <strong>${localFormatted} ${localTz}</strong></small>`;
    }
  }

  /**
   * Initialize timezone conversion on page load
   */
  function initTimezoneDisplay() {
    // Convert all elements with data-utc-time attribute
    const elements = document.querySelectorAll('[data-utc-time]');
    elements.forEach(convertTimestamp);

    // Add event listeners to datetime-local inputs
    const datetimeInputs = document.querySelectorAll('input[type="datetime-local"]');
    datetimeInputs.forEach(input => {
      // Update helper on input change
      input.addEventListener('change', function() {
        updateDateTimeInputHelper(this);
      });

      // Update helper on page load if there's a value
      if (input.value) {
        updateDateTimeInputHelper(input);
      }
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTimezoneDisplay);
  } else {
    initTimezoneDisplay();
  }
})();
