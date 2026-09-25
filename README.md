# WebDAV Anime Extension for Aniyomi

A flexible and powerful WebDAV extension for Aniyomi (and compatible forks like Anikku) that allows you to stream your own self-hosted anime and video libraries directly from any WebDAV server (like rclone, Caddy, Nextcloud, etc.).

## Features

- **Multi-Instance Support**: Provides 3 independent WebDAV servers by default, allowing you to connect to multiple different paths or servers simultaneously. Configurable up to 10 instances!
- **Dual Scanning Modes**:
  - **Structured Mode**: Designed for neatly organized libraries (`Series Name / Episode 1.mp4`).
  - **Flattened Mode**: Recursively scans all subfolders to find every video. Great for pointing to generic `Downloads` or `Movies` directories.
- **Smart Root Detection**: Orphan videos (videos not inside any folder) at your base URL are automatically grouped into a special `(Root)` entry so nothing is lost.
- **Metadata Support**: Reads `details.json` and `episodes.json` for rich metadata, but also gracefully falls back to displaying file sizes and upload dates directly from the WebDAV server if no metadata files are provided.
- **Shallow Search**: Instantly filters your root folders via the search bar without hammering your cloud server with heavy recursive search queries.

## How to Install

1. Download the latest `apk` file from the [Releases](../../releases) page or the Actions tab.
2. Install the APK on your Android device.
3. Open your Aniyomi/Anikku app and navigate to **Browse > Extensions**.
4. You will see **WebDAV Server 1**, **WebDAV Server 2**, etc., under the installed extensions list.

## Configuration

1. Tap on the gear icon next to one of the WebDAV extensions to open its settings.
2. Enter your **WebDAV Server URL** (e.g., `http://192.168.1.145:8081/localanime/`). Make sure it ends with a slash `/`.
3. Enter your **Username** and **Password** if your server requires authentication.
4. Select your preferred **Folder Mode**:
   - `Structured`: Only reads videos directly inside each series folder.
   - `Flattened`: Reads all videos in the folder and all sub-folders.
5. (Optional) Toggle metadata display options like File Size, Date, and Scanlator.
6. (Optional) To increase the number of available WebDAV servers, change the **Total Server Instances (Global)** setting and **restart your app**.

## Metadata Format (Optional)

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
