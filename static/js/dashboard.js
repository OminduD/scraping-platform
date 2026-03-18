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

  // Collect all unique keys
  const allKeys = [];
  for (const item of items) {
    for (const key of Object.keys(item)) {
      if (!allKeys.includes(key)) {
        allKeys.push(key);
      }
    }
  }

  // Prioritize common fields
  const priority = ['image_url', 'title', 'price', 'url', 'company', 'location', 'source'];
  const orderedKeys = priority.filter(k => allKeys.includes(k));
  orderedKeys.push(...allKeys.filter(k => !priority.includes(k)));

  let html = '<table><thead><tr>';
  for (const key of orderedKeys) {
    html += `<th>${escapeHtml(key)}</th>`;
  }
  html += '</tr></thead><tbody>';

  for (const item of items) {
    html += '<tr>';
    for (const key of orderedKeys) {
      const val = item[key];

      if (key === 'image_url' && val) {
        html += `<td><img class="thumb" src="${escapeHtml(val)}" alt="" onerror="this.style.display='none'"></td>`;
      } else if (key === 'url' && val) {
        html += `<td><a href="${escapeHtml(val)}" target="_blank">View</a></td>`;
      } else if (isUrl(val)) {
        html += `<td><a href="${escapeHtml(val)}" target="_blank">${escapeHtml(truncate(val, 40))}</a></td>`;
      } else {
        html += `<td>${escapeHtml(truncate(val, 100))}</td>`;
      }
    }
    html += '</tr>';
  }

  html += '</tbody></table>';
  return html;
}
