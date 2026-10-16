# Hướng dẫn Triển khai & Sử dụng Mello MCP Server

Tài liệu này hướng dẫn cách triển khai **Mello MCP Server** cho hai mô hình:
1. **Triển khai tập trung (Multi-user Remote Server)**: Dựng 1 server dùng chung cho cả công ty/team (tương tự Atlassian MCP), mỗi người dùng tự xác thực bằng Personal Access Token (`mello_pat_...`) của riêng mình.
2. **Chạy cá nhân trên máy local (`stdio`)**: Mỗi lập trình viên tự cài và chạy trực tiếp trên máy cá nhân.

---

## 1. Chuẩn bị Personal Access Token (`mello_pat_...`)

Mỗi người dùng cần tự tạo token trên giao diện Mello:
1. Đăng nhập vào **Mello** (`https://mello.mezon.vn`).
2. Vào phần **Developer / API Tokens** trong cài đặt tài khoản.
3. Tạo token mới với các quyền:
   - `read`: Xem workspace, board, column, ticket, comment, lịch sử, tìm kiếm.
   - `write`: Tạo/sửa/xóa/di chuyển ticket, board, column, checklist, label, comment, webhook, GitHub link.
4. Lưu lại chuỗi token có dạng `mello_pat_xxxxxxxxxxxxxxxxx`.

---

## 2. Triển khai Server Tập trung (Multi-User / Shared Server)

Trong mô hình này, quản trị viên (DevOps) triển khai một instance `mello-mcp-server` duy nhất.
- **Tuyệt đối không đặt `MELLO_API_KEY`** trong biến môi trường của server để tránh việc người dùng quên truyền token lại vô tình dùng chung quyền của token mặc định.
- Server tự động cô lập phiên làm việc (session) và gắn token theo từng kết nối của từng user (có cơ chế tự động giải phóng bộ nhớ LRU + TTL).

### Cách 2.1: Triển khai bằng Docker Compose (Khuyên dùng)

Tại thư mục gốc của repository:

```bash
# Khởi chạy ở chế độ SSE (mặc định, tương thích rộng nhất với Cursor, Claude, Windsurf...)
docker compose up -d --build
```

Hoặc nếu muốn chạy chế độ `streamable-http`:

```bash
MCP_TRANSPORT=streamable-http docker compose up -d --build
```

Kiểm tra log của container:

```bash
docker compose logs -f mello-mcp-server
```

### Cách 2.2: Triển khai bằng Docker thuần

```bash
# 1. Build image
docker build -t mello-mcp-server:latest .

# 2. Chạy container (Multi-user SSE mode trên cổng 8000)
docker run -d \
  --name mello-mcp-server \
  --restart unless-stopped \
  -p 8000:8000 \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MELLO_BASE_URL=https://mello.mezon.vn/api/v1 \
  mello-mcp-server:latest
```

### Cách 2.3: Chạy trực tiếp bằng `uv` / `systemd` trên Linux Server

```bash
# Cài đặt dependencies
uv sync --extra mcp

# Chạy server
uv run mello-mcp-server --transport sse --host 0.0.0.0 --port 8000
```

Ví dụ cấu hình file `/etc/systemd/system/mello-mcp.service`:

```ini
[Unit]
Description=Mello Multi-User MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mello-python-sdk
Environment="MCP_TRANSPORT=sse"
Environment="MCP_HOST=127.0.0.1"
Environment="MCP_PORT=8000"
Environment="MELLO_BASE_URL=https://mello.mezon.vn/api/v1"
ExecStart=/usr/local/bin/uv run mello-mcp-server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 3. Cấu hình Reverse Proxy (Nginx / Caddy) cho SSE & Streamable HTTP

> **Lưu ý quan trọng:** Giao thức MCP qua SSE giữ kết nối HTTP mở lâu dài và đẩy dữ liệu theo thời gian thực. Nếu đặt sau Nginx, bạn **bắt buộc phải tắt `proxy_buffering`** và giữ nguyên các header xác thực (`Authorization`, `X-Mello-Api-Key`, `Mcp-Session-Id`).

### Cấu hình Nginx mẫu (`/etc/nginx/conf.d/mcp.example.com.conf`)

```nginx
server {
    listen 443 ssl http2;
    server_name mcp-mello.yourcompany.com;

    # Cấu hình SSL chứng chỉ của bạn
    ssl_certificate     /etc/letsencrypt/live/mcp-mello.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp-mello.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # Giữ kết nối cho SSE / Streamable HTTP
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Chuyển tiếp các header xác thực & session của MCP
        proxy_set_header Authorization $http_authorization;
        proxy_set_header X-Mello-Api-Key $http_x_mello_api_key;
        proxy_set_header Mcp-Session-Id $http_mcp_session_id;

        # TẮT buffering để gói tin SSE trả về ngay lập tức
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;

        # Tăng timeout cho các phiên làm việc dài
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

---

## 4. Hướng dẫn Người dùng Kết nối vào MCP Server Tập trung

Sau khi server đã chạy tại `https://mcp-mello.yourcompany.com` (hoặc `http://<ip-server>:8000`), mỗi thành viên trong công ty chỉ cần thêm cấu hình sau vào công cụ AI của mình.

### Phương thức 1: Truyền Token qua HTTP Header (Khuyên dùng)

Phù hợp với **Cursor**, **Windsurf**, **Claude Code**, **VS Code Copilot / Cline**.

```json
{
  "mcpServers": {
    "mello": {
      "url": "https://mcp-mello.yourcompany.com/sse",
      "headers": {
        "Authorization": "Bearer mello_pat_YOUR_PERSONAL_TOKEN"
      }
    }
  }
}
```

*(Hoặc có thể dùng header `"X-Mello-Api-Key": "mello_pat_YOUR_PERSONAL_TOKEN"`).*

### Phương thức 2: Truyền Token qua Query Parameter trên URL

Dành cho các MCP client chỉ cho phép nhập duy nhất một đường dẫn URL mà không có mục cấu hình `headers`:

```json
{
  "mcpServers": {
    "mello": {
      "url": "https://mcp-mello.yourcompany.com/sse?api_key=mello_pat_YOUR_PERSONAL_TOKEN"
    }
  }
}
```

### Phương thức 3: Nhập Token trực tiếp trong khung Chat (`set_api_key`)

Nếu kết nối vào URL gốc `https://mcp-mello.yourcompany.com/sse` không kèm token, người dùng chỉ cần nhắn với AI ở đầu cuộc hội thoại:
> *"Hãy gọi tool `set_api_key` với token `mello_pat_...` của tôi"*

Mello MCP Server sẽ tự động lưu token đó cho riêng phiên chat hiện tại của người dùng.

---

## 5. Hướng dẫn Chạy Cá nhân trên Máy Local (`stdio` mode)

Nếu không muốn qua server tập trung, từng lập trình viên có thể chạy trực tiếp qua `stdio`:

```json
{
  "mcpServers": {
    "mello": {
      "command": "uvx",
      "args": ["--from", "mello-sdk[mcp]", "mello-mcp-server"],
      "env": {
        "MELLO_API_KEY": "mello_pat_YOUR_PERSONAL_TOKEN",
        "MELLO_BASE_URL": "https://mello.mezon.vn/api/v1"
      }
    }
  }
}
```

---

## 6. Bảng Biến Môi trường (Environment Variables)

| Biến môi trường | Mặc định | Mô tả |
| :--- | :--- | :--- |
| `MCP_TRANSPORT` | `stdio` (`sse` trong Docker Compose) | Giao thức chạy: `stdio`, `sse`, hoặc `streamable-http`. |
| `MCP_HOST` | `127.0.0.1` (`0.0.0.0` trong Docker) | Địa chỉ IP lắng nghe khi chạy `sse` hoặc `streamable-http`. |
| `MCP_PORT` | `8000` | Cổng lắng nghe HTTP. |
| `MELLO_BASE_URL` | `https://mello.mezon.vn/api/v1` | URL gốc trỏ tới Mello Public API `/v1`. |
| `MELLO_TIMEOUT` | `30` | Thời gian chờ (giây) cho mỗi request gọi sang Mello backend. |
| `MELLO_API_KEY` | *(Trống)* | Token mặc định. **Nên để trống** khi triển khai server dùng chung cho nhiều người. |

---

## 7. Danh sách các Tool MCP Hỗ trợ

| Nhóm | Các Tool cung cấp |
| :--- | :--- |
| **Session & User** | `set_api_key`, `get_current_user` |
| **Workspaces** | `list_workspaces`, `list_workspace_members`, `list_workspace_boards`, `search_tickets` |
| **Boards & Columns** | `create_board`, `get_board`, `update_board`, `delete_board`, `list_board_columns`, `create_column`, `reorder_columns`, `update_column`, `list_board_tickets` |
| **Labels** | `list_board_labels`, `create_label`, `update_label`, `delete_label`, `attach_label_to_ticket`, `detach_label_from_ticket` |
| **Tickets** | `create_ticket`, `get_ticket`, `update_ticket`, `delete_ticket`, `move_ticket`, `get_ticket_history` |
| **Comments** | `list_ticket_comments`, `add_ticket_comment` |
| **Checklists** | `create_checklist`, `update_checklist`, `delete_checklist`, `create_checklist_item`, `update_checklist_item`, `delete_checklist_item` |
| **Webhooks** | `list_webhooks`, `create_webhook`, `update_webhook`, `delete_webhook`, `list_webhook_deliveries`, `redeliver_webhook_event` |
| **GitHub** | `list_github_installations`, `list_github_repositories`, `list_board_github_repositories`, `replace_board_github_repositories`, `delete_github_installation`, `search_github_objects`, `create_ticket_github_link`, `delete_ticket_github_link` |
