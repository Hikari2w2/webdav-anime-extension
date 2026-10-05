# WebDAV Anime Extension for Aniyomi & Anikku

A flexible and powerful WebDAV extension for Aniyomi (and compatible forks like Anikku) that allows you to stream your own self-hosted anime and video libraries directly from any WebDAV server (like rclone, Caddy, Nextcloud, etc.).

## 📦 How to Install (Repository)

The easiest way to install and keep the extension updated is by adding this repository directly to your app.

### **[👉 Add Repository to Aniyomi / Anikku](aniyomi://add-repo?url=https%3A%2F%2Fraw.githubusercontent.com%2FHikari2w2%2Fwebdav-anime-extension%2Frepo%2Findex.min.json)**

*If the button above doesn't work, manually copy and paste the following URL into your app's Extensions > Settings > Extension repos:*
```text
https://raw.githubusercontent.com/Hikari2w2/webdav-anime-extension/repo/index.min.json
```

**⚠️ Important:** Make sure that the **"All"** (Todos) language filter is enabled in your extensions tab, as this extension is categorized under "all languages".

## ✨ Features

- **Multi-Instance Support**: Provides 3 independent WebDAV servers by default, allowing you to connect to multiple different paths or servers simultaneously. Configurable up to 10 instances!
- **Dual Scanning Modes**:
  - **Structured Mode**: Designed for neatly organized libraries (`Series Name / Episode 1.mp4`).
  - **Flattened Mode**: Recursively scans all subfolders to find every video. Great for pointing to generic `Downloads` or `Movies` directories.
- **Smart Root Detection**: Orphan videos (videos not inside any folder) at your base URL are automatically grouped into a special `(Root)` entry so nothing is lost.
- **Metadata Support**: Reads `details.json` and `episodes.json` for rich metadata, but also gracefully falls back to displaying file sizes and upload dates directly from the WebDAV server if no metadata files are provided.
- **Shallow Search**: Instantly filters your root folders via the search bar without hammering your cloud server with heavy recursive search queries.

## ⚙️ Configuration

1. Install the extension and navigate to **Browse > Anime Extensions**.
2. Tap on the gear icon next to one of the WebDAV extensions to open its settings.
3. Enter your **WebDAV Server URL** (e.g., `http://192.168.1.145:8081/localanime/`). Make sure it ends with a slash `/`.
4. Enter your **Username** and **Password** if your server requires authentication.
5. Select your preferred **Folder Mode**:
   - `Structured`: Only reads videos directly inside each series folder.
   - `Flattened`: Reads all videos in the folder and all sub-folders.
6. (Optional) Toggle metadata display options like File Size, Date, and Scanlator.
7. (Optional) To increase the number of available WebDAV servers, change the **Total Server Instances (Global)** setting and **restart your app**.

## 📝 Metadata Format (Optional)

If you want rich metadata, you can place a `details.json` and `cover.jpg` inside your series folder.

**details.json example:**
```json
{
  "title": "Tamon's B-Side",
  "author": "Yuki Shiwasu",
  "artist": "Yuki Shiwasu",
  "description": "A great story...",
  "genre": ["Comedy", "Romance"],
  "status": 1
}
```
