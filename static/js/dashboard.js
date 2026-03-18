// Utility functions for dashboard

function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

function truncate(str, len = 50) {
  if (!str) return '';
  str = String(str);
  return str.length > len ? str.substring(0, len) + '...' : str;
}

function isUrl(str) {
  if (!str) return false;
  return String(str).startsWith('http://') || String(str).startsWith('https://');
}

function isImageUrl(str) {
  if (!str || !isUrl(str)) return false;
  const url = String(str).toLowerCase();
  return url.match(/\.(jpg|jpeg|png|gif|webp|svg|bmp)(\?|$)/i) !== null;
}

function isImageField(key) {
  const k = key.toLowerCase();
  return k === 'image_url' || k === 'image' || k === 'img_url' || k === 'thumbnail' || k === 'photo' || k === 'picture';
}

function toCellText(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (_) {
      return String(value);
    }
  }
  return String(value);
}

function collectRawTableColumns(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return [];
  }

  const normalizedItems = items.map((item) => {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      return item;
    }
    return { value: item };
  });

  const allKeys = [];
  for (const item of normalizedItems) {
    for (const key of Object.keys(item)) {
      if (!allKeys.includes(key)) {
        allKeys.push(key);
      }
    }
  }

  const priority = ['image_url', 'image', 'thumbnail', 'title', 'price', 'url', 'company', 'location', 'source'];
  const orderedKeys = priority.filter(k => allKeys.includes(k));
  orderedKeys.push(...allKeys.filter(k => !priority.includes(k)));
  return orderedKeys;
}

function renderProductsTable(items) {
  if (!items || items.length === 0) {
    return '<p class="meta">No products found.</p>';
  }

  let html = `<table>
    <thead>
      <tr>
        <th>Image</th>
        <th>Title</th>
        <th>Price</th>
        <th>Source</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody>`;

  for (const item of items) {
    const imageUrl = item.image_url || '';
    const imageHtml = imageUrl
      ? `<img class="thumb" src="${escapeHtml(imageUrl)}" alt="" onerror="this.style.display='none'">`
      : '-';

    const linkHtml = item.url
      ? `<a href="${escapeHtml(item.url)}" target="_blank">View</a>`
      : '-';

    html += `<tr>
      <td>${imageHtml}</td>
      <td>${escapeHtml(truncate(item.title, 60))}</td>
      <td>${escapeHtml(item.price || '-')}</td>
      <td>${escapeHtml(item.source || '-')}</td>
      <td>${linkHtml}</td>
    </tr>`;
  }

  html += '</tbody></table>';
  return html;
}

function renderJobsTable(items) {
  if (!items || items.length === 0) {
    return '<p class="meta">No jobs found.</p>';
  }

  let html = `<table>
    <thead>
      <tr>
        <th>Title</th>
        <th>Company</th>
        <th>Location</th>
        <th>Source</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody>`;

  for (const item of items) {
    const linkHtml = item.url
      ? `<a href="${escapeHtml(item.url)}" target="_blank">View</a>`
      : '-';

    html += `<tr>
      <td>${escapeHtml(truncate(item.title, 60))}</td>
      <td>${escapeHtml(item.company || '-')}</td>
      <td>${escapeHtml(item.location || '-')}</td>
      <td>${escapeHtml(item.source || '-')}</td>
      <td>${linkHtml}</td>
    </tr>`;
  }

  html += '</tbody></table>';
  return html;
}

function renderRawDataTable(items) {
  if (!items || items.length === 0) {
    return '<p class="meta">No items to display.</p>';
  }

  const normalizedItems = items.map((item) => {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      return item;
    }
    return { value: item };
  });
  const orderedKeys = collectRawTableColumns(normalizedItems);

  let html = '<table><thead><tr>';
  for (const key of orderedKeys) {
    html += `<th>${escapeHtml(key)}</th>`;
  }
  html += '</tr></thead><tbody>';

  for (const item of normalizedItems) {
    html += '<tr>';
    for (const key of orderedKeys) {
      const val = item[key];
      const textVal = toCellText(val);

      // Check if this is an image field or an image URL
      if (isImageField(key) && textVal && isUrl(textVal)) {
        html += `<td><img class="thumb" src="${escapeHtml(textVal)}" alt="" onerror="this.style.display='none'"></td>`;
      } else if (key === 'url' && textVal) {
        html += `<td><a href="${escapeHtml(textVal)}" target="_blank">View</a></td>`;
      } else if (isImageUrl(textVal)) {
        // If it looks like an image URL, show as image
        html += `<td><img class="thumb" src="${escapeHtml(textVal)}" alt="" onerror="this.style.display='none'"></td>`;
      } else if (isUrl(textVal)) {
        // Other URLs - make clickable
        html += `<td><a href="${escapeHtml(textVal)}" target="_blank">${escapeHtml(truncate(textVal, 40))}</a></td>`;
      } else {
        html += `<td>${escapeHtml(truncate(textVal, 100))}</td>`;
      }
    }
    html += '</tr>';
  }

  html += '</tbody></table>';
  return html;
}
