from __future__ import annotations


def render_index_html(token: str, host_label: str) -> str:
    """Render the responsive, zero-dependency mobile web UI."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>lantransfer</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0ea5e9;
      --success: #22c55e;
      --danger: #ef4444;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 16px;
      max-width: 640px;
      margin: 0 auto;
      line-height: 1.5;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }}
    header h1 {{ font-size: 1.35rem; letter-spacing: -0.02em; }}
    .badge {{
      font-size: 0.75rem;
      background: #0c4a6e;
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 600;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .card h2 {{
      font-size: 1rem;
      margin-bottom: 12px;
      color: var(--accent);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .dropzone {{
      border: 2px dashed var(--border);
      border-radius: 12px;
      padding: 24px 14px;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.2s, background 0.2s;
    }}
    .dropzone.dragover {{
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.08);
    }}
    .dropzone p {{ color: var(--muted); font-size: 0.92rem; margin-top: 6px; }}
    .btn {{
      display: inline-block;
      background: var(--accent);
      color: #082f49;
      border: none;
      border-radius: 9px;
      padding: 9px 15px;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      text-decoration: none;
    }}
    .btn:active {{ transform: scale(0.98); }}
    .btn-sm {{ padding: 6px 11px; font-size: 0.8rem; }}
    .btn-ghost {{
      background: transparent;
      color: var(--accent);
      border: 1px solid var(--border);
    }}
    .list {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
    .item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      background: rgba(15, 23, 42, 0.55);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
    }}
    .item-info {{ min-width: 0; flex: 1; }}
    .item-name {{
      font-size: 0.92rem;
      font-weight: 500;
      word-break: break-all;
    }}
    .item-meta {{ font-size: 0.78rem; color: var(--muted); }}
    .empty {{ color: var(--muted); font-size: 0.88rem; }}
    .progress-wrap {{
      margin-top: 12px;
      display: none;
    }}
    .progress-bar-bg {{
      width: 100%;
      height: 8px;
      background: #0f172a;
      border-radius: 999px;
      overflow: hidden;
      margin-top: 6px;
    }}
    .progress-bar {{
      height: 100%;
      width: 0%;
      background: var(--success);
      transition: width 0.1s linear;
    }}
    textarea {{
      width: 100%;
      background: #0f172a;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      font-family: inherit;
      font-size: 0.92rem;
      resize: vertical;
      min-height: 70px;
      margin-bottom: 10px;
    }}
    .note-text {{
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.9rem;
    }}
    #status {{
      font-size: 0.84rem;
      color: var(--muted);
      margin-top: 8px;
      min-height: 1.2em;
    }}
  </style>
</head>
<body>
  <header>
    <h1>lantransfer</h1>
    <span class="badge">{host_label}</span>
  </header>

  <section class="card">
    <h2>
      <span>From PC (Download)</span>
      <button class="btn btn-sm btn-ghost" onclick="loadState()">Refresh</button>
    </h2>
    <ul id="pc-files" class="list">
      <li class="empty">Loading...</li>
    </ul>
  </section>

  <section class="card">
    <h2><span>Send to PC (Upload)</span></h2>
    <div id="dropzone" class="dropzone" onclick="document.getElementById('file-input').click()">
      <span class="btn">Choose Files or Photos</span>
      <p>Tap to pick files or drag &amp; drop here</p>
    </div>
    <input id="file-input" type="file" multiple style="display:none" />
    <div id="progress-wrap" class="progress-wrap">
      <div id="progress-label" class="item-meta">Uploading...</div>
      <div class="progress-bar-bg"><div id="progress-bar" class="progress-bar"></div></div>
    </div>
    <div id="status"></div>
  </section>

  <section class="card">
    <h2><span>Shared Text &amp; Links</span></h2>
    <textarea id="note-input" placeholder="Paste a link, code snippet, or note to send to PC..."></textarea>
    <button class="btn" onclick="sendNote()">Send Text</button>
    <ul id="notes-list" class="list" style="margin-top: 12px;"></ul>
  </section>

  <script>
    const TOKEN = {token!r};

    function formatBytes(bytes) {{
      if (bytes === 0) return "0 B";
      const units = ["B", "KB", "MB", "GB"];
      const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
      return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + " " + units[i];
    }}

    function escapeHtml(str) {{
      return str.replace(/[&<>"']/g, c => ({{
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }}[c]));
    }}

    function copyText(text, btn) {{
      const done = () => {{
        const orig = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = orig, 1200);
      }};
      if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
      }} else {{
        fallbackCopy(text, done);
      }}
    }}

    function fallbackCopy(text, onDone) {{
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {{ document.execCommand("copy"); }} catch (e) {{}}
      document.body.removeChild(ta);
      onDone();
    }}

    async function loadState() {{
      try {{
        const res = await fetch(`/api/state?token=${{encodeURIComponent(TOKEN)}}`);
        if (!res.ok) return;
        const data = await res.json();

        const fileList = document.getElementById("pc-files");
        if (!data.shared_files.length) {{
          fileList.innerHTML = '<li class="empty">No files shared from PC yet.</li>';
        }} else {{
          fileList.innerHTML = data.shared_files.map(f => `
            <li class="item">
              <div class="item-info">
                <div class="item-name">${{escapeHtml(f.name)}}</div>
                <div class="item-meta">${{f.is_dir ? "Folder (ZIP)" : formatBytes(f.size)}}</div>
              </div>
              <a class="btn btn-sm" href="/download/${{encodeURIComponent(f.id)}}?token=${{encodeURIComponent(TOKEN)}}">Download</a>
            </li>
          `).join("");
        }}

        const notesList = document.getElementById("notes-list");
        if (!data.notes.length) {{
          notesList.innerHTML = '<li class="empty">No shared notes yet.</li>';
        }} else {{
          notesList.innerHTML = data.notes.slice().reverse().map((n, idx) => `
            <li class="item">
              <div class="item-info">
                <div class="item-meta">${{escapeHtml(n.sender)}} · ${{escapeHtml(n.time)}}</div>
                <div class="note-text" id="note-${{idx}}">${{escapeHtml(n.text)}}</div>
              </div>
              <button class="btn btn-sm btn-ghost" onclick="copyText(document.getElementById('note-${{idx}}').textContent, this)">Copy</button>
            </li>
          `).join("");
        }}
      }} catch (err) {{
        console.error(err);
      }}
    }}

    function uploadSingleFile(file, index, total) {{
      return new Promise((resolve, reject) => {{
        const xhr = new XMLHttpRequest();
        const url = `/api/upload?token=${{encodeURIComponent(TOKEN)}}&filename=${{encodeURIComponent(file.name)}}`;
        xhr.open("POST", url, true);
        xhr.setRequestHeader("Content-Type", "application/octet-stream");

        xhr.upload.onprogress = (e) => {{
          if (e.lengthComputable) {{
            const pct = Math.round((e.loaded / e.total) * 100);
            document.getElementById("progress-bar").style.width = pct + "%";
            document.getElementById("progress-label").textContent =
              `Uploading (${{index + 1}}/${{total}}): ${{file.name}} — ${{pct}}%`;
          }}
        }};

        xhr.onload = () => {{
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error(xhr.responseText || "Upload failed"));
        }};
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.send(file);
      }});
    }}

    async function handleFiles(files) {{
      if (!files || !files.length) return;
      const wrap = document.getElementById("progress-wrap");
      const status = document.getElementById("status");
      wrap.style.display = "block";
      status.textContent = "";

      let uploaded = 0;
      for (let i = 0; i < files.length; i++) {{
        try {{
          await uploadSingleFile(files[i], i, files.length);
          uploaded++;
        }} catch (err) {{
          status.textContent = `Error uploading ${{files[i].name}}: ${{err.message}}`;
        }}
      }}

      wrap.style.display = "none";
      document.getElementById("progress-bar").style.width = "0%";
      if (uploaded > 0) {{
        status.textContent = `Sent ${{uploaded}} file(s) to PC.`;
      }}
      document.getElementById("file-input").value = "";
    }}

    async function sendNote() {{
      const input = document.getElementById("note-input");
      const text = input.value.trim();
      if (!text) return;
      const res = await fetch(`/api/note?token=${{encodeURIComponent(TOKEN)}}`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ text }})
      }});
      if (res.ok) {{
        input.value = "";
        loadState();
      }}
    }}

    const fileInput = document.getElementById("file-input");
    fileInput.addEventListener("change", (e) => handleFiles(e.target.files));

    const dropzone = document.getElementById("dropzone");
    dropzone.addEventListener("dragover", (e) => {{ e.preventDefault(); dropzone.classList.add("dragover"); }});
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {{
      e.preventDefault();
      dropzone.classList.remove("dragover");
      handleFiles(e.dataTransfer.files);
    }});

    loadState();
    setInterval(loadState, 5000);
  </script>
</body>
</html>
"""
