/**
 * Helios Timezone Display Utility
 * Automatically converts UTC timestamps to show both UTC and local timezone
 */

(function() {
  'use strict';

  /**
   * Format a date in a human-readable way
   */
  function formatDateTime(date) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const year = date.getFullYear();
    const month = months[date.getMonth()];
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}`;
  }

  /**
   * Get timezone abbreviation
   */
  function getTimezoneAbbr(date) {
    const tzString = date.toString();
    const tzMatch = tzString.match(/\(([^)]+)\)$/);
    if (tzMatch && tzMatch[1]) {
      // Return the timezone abbreviation from the string
      const tz = tzMatch[1];
      // Try to create abbreviation from timezone name
      const abbr = tz.split(' ').map(word => word[0]).join('');
      return abbr || 'Local';
    }

    // Fallback: get offset
    const offset = -date.getTimezoneOffset();
    const hours = Math.floor(Math.abs(offset) / 60);
    const minutes = Math.abs(offset) % 60;
    const sign = offset >= 0 ? '+' : '-';
    return `UTC${sign}${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }

  /**
   * Parse various datetime formats
   */
  function parseDateTime(dateStr) {
    // Remove any existing timezone indicators
    dateStr = dateStr.trim();

    // Try to parse ISO format or common formats
    // Formats to handle:
    // - "2024-03-15 14:30" (no timezone, assume UTC)
    // - "2024-03-15T14:30" (ISO format, no timezone, assume UTC)
    // - "2024-Mar-15 14:30"
    // - "March 15, 2024, 2:30 p.m."

    // First, try standard Date parsing
    let date = new Date(dateStr + ' UTC');

    // If invalid, try without UTC suffix (in case it already has timezone)
    if (isNaN(date.getTime())) {
      date = new Date(dateStr);
    }

    return date;
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

    const utcDate = parseDateTime(utcDateStr);

    if (isNaN(utcDate.getTime())) {
      console.warn('Could not parse datetime:', utcDateStr);
      return;
    }

    // Format both times
    const utcFormatted = formatDateTime(new Date(utcDate.toISOString().replace('Z', '')));
    const localDate = new Date(utcDate);
    const localFormatted = formatDateTime(localDate);
    const localTz = getTimezoneAbbr(localDate);

    // Check if UTC and local are the same
    const sameAsUTC = utcDate.getTimezoneOffset() === 0;

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
        <span class="tz-local" title="Your local timezone: ${localTz}">${localFormatted} ${localTz}</span>
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
    const utcDate = new Date(value + ':00Z'); // Add seconds and Z for UTC

    if (isNaN(utcDate.getTime())) {
      return;
    }

    // Get or create helper element
    let helper = input.nextElementSibling;
    if (!helper || !helper.classList.contains('tz-input-helper')) {
      helper = document.createElement('div');
      helper.className = 'tz-input-helper';
      input.parentNode.insertBefore(helper, input.nextSibling);
    }

    // Format both times
    const utcFormatted = formatDateTime(new Date(utcDate.toISOString().replace('Z', '')));
    const localDate = new Date(utcDate);
    const localFormatted = formatDateTime(localDate);
    const localTz = getTimezoneAbbr(localDate);

    // Check if UTC and local are the same
    const sameAsUTC = utcDate.getTimezoneOffset() === 0;

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
